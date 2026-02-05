"""
Queue Mode Handler

Gerencia filas: tamanho, tempo de espera e “abandono” (quem sai da fila).
"""

import logging
from datetime import datetime
from typing import Dict, Set

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState
from application.zone.modes.common.timers import should_send_alert

logger = logging.getLogger(__name__)


class QueueModeHandler(BaseModeHandler):
    """
    Queue mode: monitora comprimento da fila e tempos de espera.

    Lógica (toda configurável via metadata da zona):
    - max_queue_length: Comprimento de fila “desejado” (capacidade alvo)
    - warning_queue_length: A partir desse tamanho, status WARNING
    - critical_queue_length: A partir desse tamanho, status CRITICAL
    - max_wait_warning: Tempo médio de espera para WARNING (segundos)
    - max_wait_critical: Tempo máximo de espera para CRITICAL (segundos)

    Estados:
    - QUEUE_NORMAL: fila dentro de limites
    - QUEUE_WARNING: fila alta ou espera alta
    - QUEUE_CRITICAL: fila crítica (comprimento ou espera)
    """

    def process(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float,
    ) -> Dict:
        """
        Processa zona em modo queue.

        Args:
            zone: Configuração da zona (dict do DB)
            state: Estado runtime da zona
            track_state: Estado de tracking (não usado aqui, usamos apenas objects_inside)
            current_time: Timestamp atual (Unix)

        Returns:
            Dict com métricas da fila
        """
        # Objetos atuais na fila (track_ids que estão dentro da zona)
        current_objects: Set[int] = set(state.objects_inside)

        metadata = zone.get("metadata", {}) or {}

        # Configurações de fila com defaults seguros
        max_queue_length = int(metadata.get("max_queue_length", 10))
        warning_queue_length = int(
            metadata.get("warning_queue_length", max_queue_length)
        )
        critical_queue_length = int(
            metadata.get("critical_queue_length", max_queue_length)
        )

        max_wait_warning = float(metadata.get("max_wait_warning", 120.0))  # 2 min
        max_wait_critical = float(metadata.get("max_wait_critical", 300.0))  # 5 min

        now = datetime.fromtimestamp(current_time)

        # ------------------------------------------------------------------ #
        # Estado dinâmico específico de fila (anexado em runtime)
        # ------------------------------------------------------------------ #
        if not hasattr(state, "queue_join_times"):
            # track_id -> datetime de entrada na fila
            state.queue_join_times = {}

        if not hasattr(state, "queue_last_inside"):
            # track_ids presentes no frame anterior
            state.queue_last_inside = set()

        if not hasattr(state, "queue_abandon_count"):
            # quantas pessoas saíram da fila (atendidas ou desistentes)
            state.queue_abandon_count = 0

        if not hasattr(state, "queue_abandon_total_wait"):
            # soma dos tempos de espera de quem saiu
            state.queue_abandon_total_wait = 0.0

        if not hasattr(state, "queue_last_abandon_wait"):
            # tempo de espera do último que saiu
            state.queue_last_abandon_wait = 0.0

        join_times: Dict[int, datetime] = state.queue_join_times
        prev_inside: Set[int] = set(state.queue_last_inside)

        # ------------------------------------------------------------------ #
        # 1) Processar saídas da fila (quem não está mais dentro da zona)
        # ------------------------------------------------------------------ #
        left_ids = prev_inside - current_objects
        for track_id in left_ids:
            joined_at = join_times.pop(track_id, None)
            if joined_at is not None:
                waited = max(0.0, (now - joined_at).total_seconds())
                state.queue_abandon_count += 1
                state.queue_abandon_total_wait += waited
                state.queue_last_abandon_wait = waited

        # ------------------------------------------------------------------ #
        # 2) Registrar novas entradas na fila
        # ------------------------------------------------------------------ #
        joined_now = current_objects - prev_inside
        for track_id in joined_now:
            # Mantém join_time mais antigo se já existia (segurança)
            if track_id not in join_times:
                join_times[track_id] = now

        # ------------------------------------------------------------------ #
        # 3) Atualizar referência de quem está dentro
        # ------------------------------------------------------------------ #
        state.queue_last_inside = set(current_objects)

        # ------------------------------------------------------------------ #
        # 4) Calcular métricas de espera
        # ------------------------------------------------------------------ #
        wait_times = [
            max(0.0, (now - t).total_seconds())
            for tid, t in join_times.items()
            if tid in current_objects
        ]

        queue_length = len(current_objects)
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0
        max_wait = max(wait_times) if wait_times else 0.0

        abandon_count = state.queue_abandon_count
        abandon_avg_wait = (
            state.queue_abandon_total_wait / abandon_count
            if abandon_count > 0
            else 0.0
        )

        # ------------------------------------------------------------------ #
        # 5) Determinar status da fila
        # ------------------------------------------------------------------ #
        status = "QUEUE_NORMAL"
        alert = False

        # Critérios de severidade
        is_len_critical = (
            critical_queue_length > 0
            and queue_length >= critical_queue_length
        )
        is_len_warning = (
            warning_queue_length > 0
            and queue_length >= warning_queue_length
        )
        is_wait_critical = max_wait >= max_wait_critical > 0
        is_wait_warning = avg_wait >= max_wait_warning > 0

        if is_len_critical or is_wait_critical:
            status = "QUEUE_CRITICAL"
            alert = True
        elif is_len_warning or is_wait_warning:
            status = "QUEUE_WARNING"
            alert = True

        # ------------------------------------------------------------------ #
        # 6) Cooldown de alerta (mesmo padrão dos outros modos)
        # ------------------------------------------------------------------ #
        email_cooldown = zone.get("email_cooldown", 600.0)
        can_alert = should_send_alert(alert, state.last_alert_time, email_cooldown, now)

        if alert and can_alert:
            state.last_alert_time = now

        if status != state.status:
            logger.info(
                f"🧾 Queue Zone '{zone['name']}': {state.status} → {status} "
                f"(len={queue_length}, avg_wait={int(avg_wait)}s, "
                f"max_wait={int(max_wait)}s)"
            )

        state.status = status

        # Mensagem de alerta simples
        alert_message = None
        if alert:
            if status == "QUEUE_CRITICAL":
                alert_message = (
                    f"Fila crítica: {queue_length} pessoas, "
                    f"espera máxima {int(max_wait)}s"
                )
            else:
                alert_message = (
                    f"Fila alta: {queue_length} pessoas, "
                    f"espera média {int(avg_wait)}s"
                )

        # ------------------------------------------------------------------ #
        # Retorno para API/frontend
        # ------------------------------------------------------------------ #
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "queue",
            "count": queue_length,
            "status": status,
            "alert": alert and can_alert,
            "alert_message": alert_message,
            # KPIs de fila
            "queue_length": queue_length,
            "avg_wait_time": avg_wait,
            "max_wait_time": max_wait,
            # “abandono” (quem saiu da fila)
            "abandon_count": abandon_count,
            "abandon_avg_wait": abandon_avg_wait,
            "last_abandon_wait": state.queue_last_abandon_wait,
        }
