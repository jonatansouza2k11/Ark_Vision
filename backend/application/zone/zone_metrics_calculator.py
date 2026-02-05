"""
Use Case: Calcular métricas de zona

Responsabilidade: Aplicar lógica de modo
(occupancy, counting, capacity, alert, tracking, queue)
"""

from dataclasses import dataclass
from typing import Dict, Any, Set
from datetime import datetime
import logging

from backend.core.domain.entities import Zone
from backend.core.domain.entities.zones import ZoneMode

logger = logging.getLogger(__name__)


@dataclass
class ZoneMetrics:
    """DTO de métricas de zona."""

    zone_id: int
    zone_name: str
    mode: str
    count: int
    status: str
    alert: bool
    alert_message: str | None = None
    metadata: Dict[str, Any] | None = None

    # Identificação por track/local-id e por global_id (ReID)
    active_track_ids: Set[int] | None = None
    active_global_ids: Set[int] | None = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa para API/DB.

        As chaves de `metadata` são mescladas na raiz do dict
        para facilitar consumo no frontend.
        """
        data: Dict[str, Any] = {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "mode": self.mode,
            "count": self.count,
            "status": self.status,
            "alert": self.alert,
            "alert_message": self.alert_message,
        }

        if self.active_track_ids is not None:
            data["active_track_ids"] = list(self.active_track_ids)

        if self.active_global_ids is not None:
            data["active_global_ids"] = list(self.active_global_ids)

        if self.metadata:
            data.update(self.metadata)

        return data


class ZoneMetricsCalculator:
    """
    Calcula métricas de zona baseado em modo.
    Responsabilidade: Lógica pura de negócio (sem I/O, sem OpenCV)
    """

    def calculate(
        self,
        zone: Zone,
        objects_inside: Set[int],
        current_time: float,
        global_ids_inside: Set[int] | None = None,
    ) -> ZoneMetrics:
        """
        Calcula métricas para uma zona.

        Args:
            zone: Zona com config + state
            objects_inside: Set de track_ids dentro da zona
            current_time: Timestamp atual (epoch)
            global_ids_inside: Set de global_ids correspondentes (opcional)

        Returns:
            ZoneMetrics com status, alert, etc.
        """
        # Atualiza estado base
        zone.state.object_count = len(objects_inside)
        zone.state.objects_inside = set(objects_inside)

        # Opcional: persistir também os global_ids no state, se fornecidos
        if global_ids_inside is not None:
            # Atributo dinâmico em ZoneRuntimeState, para inspeção posterior
            zone.state.global_ids_inside = set(global_ids_inside)

        # Delega para processador de modo específico
        if zone.config.mode == ZoneMode.OCCUPANCY:
            return self._process_occupancy(zone, current_time, objects_inside, global_ids_inside)
        elif zone.config.mode == ZoneMode.COUNTING:
            return self._process_counting(zone, current_time, objects_inside, global_ids_inside)
        elif zone.config.mode == ZoneMode.CAPACITY:
            return self._process_capacity(zone, current_time, objects_inside, global_ids_inside)
        elif zone.config.mode == ZoneMode.ALERT:
            return self._process_alert(zone, current_time, objects_inside, global_ids_inside)
        elif zone.config.mode == ZoneMode.TRACKING:
            return self._process_tracking(zone, current_time, objects_inside, global_ids_inside)
        elif zone.config.mode == ZoneMode.QUEUE:
            return self._process_queue(zone, current_time, objects_inside, global_ids_inside)
        else:
            return self._process_generic(zone, current_time, objects_inside, global_ids_inside)

    # ----------------------------------------------------------------------
    # OCCUPANCY
    # ----------------------------------------------------------------------

    def _process_occupancy(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo occupancy: EMPTY / OCCUPIED / FULL"""
        count = zone.state.object_count
        config = zone.config
        state = zone.state

        # Determinar status raw
        if count <= config.empty_threshold:
            raw_status = "EMPTY"
        elif count >= config.full_threshold:
            raw_status = "FULL"
        else:
            raw_status = "OCCUPIED"

        # Atualizar timers
        if raw_status == "EMPTY":
            if state.empty_since == 0.0:
                state.empty_since = now
            state.full_since = 0.0
        elif raw_status == "FULL":
            if state.full_since == 0.0:
                state.full_since = now
            state.empty_since = 0.0
        else:
            state.empty_since = 0.0
            state.full_since = 0.0

        # Verificar timeouts
        alert = False
        alert_message = None
        confirmed_status = raw_status

        if raw_status == "EMPTY" and state.empty_since > 0:
            elapsed = now - state.empty_since
            if elapsed >= config.empty_timeout:
                alert = True
                alert_message = f"Zona vazia por {int(elapsed)}s"
                confirmed_status = "EMPTY"
            else:
                confirmed_status = "EMPTY_PENDING"

        if raw_status == "FULL" and state.full_since > 0:
            elapsed = now - state.full_since
            if elapsed >= config.full_timeout:
                alert = True
                alert_message = f"Zona cheia por {int(elapsed)}s"
                confirmed_status = "FULL"
            else:
                confirmed_status = "FULL_PENDING"

        # Email cooldown
        can_alert = True
        if alert and state.last_alert_time > 0:
            elapsed = now - state.last_alert_time
            can_alert = elapsed >= config.email_cooldown

        if alert and can_alert:
            state.last_alert_time = now

        # Log mudanças
        if confirmed_status != state.status:
            logger.info(
                f"🏢 Zone '{config.name}': "
                f"{state.status} → {confirmed_status} ({count} objetos)"
            )

        state.status = confirmed_status

        return ZoneMetrics(
            zone_id=config.zone_id,
            zone_name=config.name,
            mode=config.mode.value,
            count=count,
            status=confirmed_status,
            alert=alert and can_alert,
            alert_message=alert_message,
            metadata={
                "empty_duration": (
                    now - state.empty_since
                    if state.empty_since > 0 and confirmed_status == "EMPTY_PENDING"
                    else 0
                ),
                "full_duration": (
                    now - state.full_since
                    if state.full_since > 0 and confirmed_status == "FULL_PENDING"
                    else 0
                ),
            },
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # CAPACITY
    # ----------------------------------------------------------------------

    def _process_capacity(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo capacity: Alerta quando aproxima/excede capacidade máxima"""
        count = zone.state.object_count
        config = zone.config
        state = zone.state

        meta_cfg = config.metadata or {}
        max_capacity = int(meta_cfg.get("max_capacity", 50))
        alert_percentage = float(meta_cfg.get("alert_percentage", 100))
        alert_threshold = int(max_capacity * (alert_percentage / 100.0))

        if count >= alert_threshold:
            if state.full_since == 0.0:
                state.full_since = now

            elapsed = now - state.full_since
            if elapsed >= config.full_timeout:
                if count >= max_capacity:
                    new_status = "CRITICAL"
                else:
                    new_status = "WARNING"
                alert = True
            else:
                new_status = "PENDING"
                alert = False
        else:
            if state.full_since > 0.0 and state.status in ["WARNING", "CRITICAL", "PENDING"]:
                logger.info(
                    f"📉 Zone '{config.name}' saiu do alerta: "
                    f"{state.status} → NORMAL ({count}/{max_capacity})"
                )
            state.full_since = 0.0
            new_status = "NORMAL"
            alert = False

        # Email cooldown
        can_alert = True
        if alert and state.last_alert_time > 0:
            elapsed = now - state.last_alert_time
            can_alert = elapsed >= config.email_cooldown

        if alert and can_alert:
            state.last_alert_time = now

        if new_status != state.status:
            logger.info(
                f"📊 Zone '{config.name}': "
                f"{state.status} → {new_status} "
                f"({count}/{max_capacity} = {round(count / max_capacity * 100)}%)"
            )

        state.status = new_status

        occupancy_percent = round((count / max_capacity) * 100.0, 1) if max_capacity > 0 else 0.0

        return ZoneMetrics(
            zone_id=config.zone_id,
            zone_name=config.name,
            mode=config.mode.value,
            count=count,
            status=new_status,
            alert=alert and can_alert,
            alert_message=(
                f"Capacidade: {count}/{max_capacity} "
                f"({round(count / max_capacity * 100)}%)"
                if alert
                else None
            ),
            metadata={
                "max_capacity": max_capacity,
                "occupancy_percent": occupancy_percent,
            },
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # COUNTING
    # ----------------------------------------------------------------------

    def _process_counting(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo counting: Conta entradas/saídas usando ZoneState e metadata"""
        state = zone.state
        config = zone.config

        current_inside: Set[int] = set(state.objects_inside)
        prev_inside: Set[int] = getattr(state, "counting_last_inside", set())

        # Config de metadata (governança via DB)
        meta_cfg = config.metadata or {}

        # Normaliza reset_interval: aceita string legada ("daily") ou segundos
        raw_reset = meta_cfg.get("reset_interval", 0.0)
        if isinstance(raw_reset, str):
            mapping = {
                "none": 0.0,
                "off": 0.0,
                "hourly": 3600.0,
                "daily": 86400.0,
                "weekly": 7 * 86400.0,
                "monthly": 30 * 86400.0,
            }
            reset_interval = mapping.get(raw_reset.lower(), 0.0)
        else:
            try:
                reset_interval = float(raw_reset)
            except (TypeError, ValueError):
                reset_interval = 0.0

        direction = meta_cfg.get("count_direction", "both")
        if direction not in ("in", "out", "both"):
            direction = "both"

        # Inicializar campos se ainda não existem (para compatibilidade)
        if not hasattr(state, "counting_in"):
            state.counting_in = int(meta_cfg.get("count_in", 0))
        if not hasattr(state, "counting_out"):
            state.counting_out = int(meta_cfg.get("count_out", 0))
        if not hasattr(state, "counting_last_reset"):
            state.counting_last_reset = 0.0
        if not hasattr(state, "counting_last_inside"):
            state.counting_last_inside = set(prev_inside)

        # Reset por intervalo
        if reset_interval > 0 and state.counting_last_reset > 0:
            elapsed_reset = now - state.counting_last_reset
            if elapsed_reset >= reset_interval:
                state.counting_in = 0
                state.counting_out = 0
                state.counting_last_reset = now

        # Entradas e saídas (transições)
        entered = current_inside - prev_inside
        exited = prev_inside - current_inside

        if direction in ("in", "both"):
            state.counting_in += len(entered)
        if direction in ("out", "both"):
            state.counting_out += len(exited)

        # Atualiza referência e last_reset inicial
        state.counting_last_inside = set(current_inside)
        if state.counting_last_reset == 0.0:
            state.counting_last_reset = now

        # Status simples de feedback visual
        new_status = "COUNTING" if state.object_count > 0 else "IDLE"
        if new_status != state.status:
            logger.info(
                f"🔢 Zone '{config.name}': "
                f"IN={state.counting_in}, OUT={state.counting_out}, "
                f"saldo={state.counting_in - state.counting_out}"
            )

        state.status = new_status

        metadata = {
            "count_in": state.counting_in,
            "count_out": state.counting_out,
            "count_direction": direction,
            "reset_interval": reset_interval,
            "last_reset": state.counting_last_reset,
        }

        return ZoneMetrics(
            zone_id=config.zone_id,
            zone_name=config.name,
            mode=config.mode.value,
            count=state.object_count,
            status=new_status,
            alert=False,
            alert_message=None,
            metadata=metadata,
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # ALERT
    # ----------------------------------------------------------------------

    def _process_alert(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo alert: Alerta imediato quando threshold excedido"""
        count = zone.state.object_count
        config = zone.config
        state = zone.state

        if count >= config.full_threshold:
            if state.full_since == 0.0:
                state.full_since = now

            elapsed = now - state.full_since
            if elapsed >= config.full_timeout:
                new_status = "ALERT"
                alert = True
            else:
                new_status = "PENDING"
                alert = False
        else:
            state.full_since = 0.0
            new_status = "NORMAL"
            alert = False

        can_alert = True
        if alert and state.last_alert_time > 0:
            elapsed = now - state.last_alert_time
            can_alert = elapsed >= config.email_cooldown

        if alert and can_alert:
            state.last_alert_time = now

        if new_status != state.status:
            logger.warning(
                f"🚨 Zone {config.name}: "
                f"{state.status} → {new_status} ({count} objetos)"
            )

        state.status = new_status

        return ZoneMetrics(
            zone_id=config.zone_id,
            zone_name=config.name,
            mode=config.mode.value,
            count=count,
            status=new_status,
            alert=alert and can_alert,
            alert_message=(f"ALERTA: {count} objetos na zona" if alert else None),
            metadata=None,
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # TRACKING
    # ----------------------------------------------------------------------

    def _process_tracking(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo tracking: Rastreamento simples de presença"""
        count = zone.state.object_count
        new_status = "TRACKING" if count > 0 else "IDLE"

        if new_status != zone.state.status:
            logger.info(
                f"🎯 Zone {zone.config.name}: tracking {count} object(s)"
            )

        zone.state.status = new_status

        metadata = {
            "tracked_ids": list(zone.state.objects_inside),
        }

        return ZoneMetrics(
            zone_id=zone.config.zone_id,
            zone_name=zone.config.name,
            mode=zone.config.mode.value,
            count=count,
            status=new_status,
            alert=False,
            alert_message=None,
            metadata=metadata,
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # QUEUE
    # ----------------------------------------------------------------------

    def _process_queue(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """
        Modo queue: monitora comprimento da fila e tempos de espera.

        KPIs:
        - queue_length → tamanho atual da fila (deteções dentro da zona)
        - avg_wait_time → tempo médio de espera dos que estão na fila
        - max_wait_time → maior tempo de espera atual
        - abandon_count → quantos saíram da fila (atendidos/abandono)
        - abandon_avg_wait → tempo médio de espera de quem saiu
        - last_abandon_wait → tempo de espera do último que saiu

        Implementação v2:
        - Usa histerese de entrada/saída para reduzir ruído de tracking
        - Mantém o mesmo contrato de metadata e chaves de saída
        """
        config = zone.config
        state = zone.state

        # Objetos atuais na fila (track_ids dentro da zona)
        current_objects: Set[int] = set(state.objects_inside)

        # Configurações de fila via metadata
        meta = config.metadata or {}
        max_queue_length = int(meta.get("max_queue_length", 10))
        warning_queue_length = int(meta.get("warning_queue_length", max_queue_length))
        critical_queue_length = int(meta.get("critical_queue_length", max_queue_length))

        # SLA de espera (segundos)
        max_wait_warning = float(meta.get("max_wait_warning", 120.0))  # 2 min
        max_wait_critical = float(meta.get("max_wait_critical", 300.0))  # 5 min

        # Histerese de entrada/saída (segundos)
        join_confirm_time = float(meta.get("queue_join_confirm_time", 1.0))
        leave_grace_time = float(meta.get("queue_leave_grace_time", 2.0))

        # Estado dinâmico específico de fila
        if not hasattr(state, "queue_join_times"):
            state.queue_join_times = {}
        if not hasattr(state, "queue_last_inside"):
            state.queue_last_inside = set()
        if not hasattr(state, "queue_abandon_count"):
            state.queue_abandon_count = 0
        if not hasattr(state, "queue_abandon_total_wait"):
            state.queue_abandon_total_wait = 0.0
        if not hasattr(state, "queue_last_abandon_wait"):
            state.queue_last_abandon_wait = 0.0
        if not hasattr(state, "queue_warning_since"):
            state.queue_warning_since = 0.0
        if not hasattr(state, "queue_critical_since"):
            state.queue_critical_since = 0.0
        if not hasattr(state, "queue_last_seen"):
            state.queue_last_seen = {}
        if not hasattr(state, "queue_pending_join"):
            state.queue_pending_join = {}
        if not hasattr(state, "queue_missing_since"):
            state.queue_missing_since = {}

        join_times: Dict[int, float] = state.queue_join_times
        prev_inside: Set[int] = set(state.queue_last_inside)
        last_seen: Dict[int, float] = state.queue_last_seen
        pending_join: Dict[int, float] = state.queue_pending_join
        missing_since: Dict[int, float] = state.queue_missing_since

        # 1) Atualizar observação / histerese de entrada
        for track_id in current_objects:
            last_seen[track_id] = now

        newly_missing = prev_inside - current_objects
        for track_id in newly_missing:
            if track_id not in missing_since:
                missing_since[track_id] = now

        for track_id in list(missing_since.keys()):
            if track_id in current_objects:
                missing_since.pop(track_id, None)

        for track_id in current_objects:
            if track_id in join_times:
                continue
            first_seen = pending_join.get(track_id)
            if first_seen is None:
                pending_join[track_id] = now
            else:
                if now - first_seen >= join_confirm_time:
                    join_times[track_id] = first_seen
                    pending_join.pop(track_id, None)

        for track_id in list(pending_join.keys()):
            if track_id not in current_objects:
                pending_join.pop(track_id, None)

        # 2) Determinar saídas definitivas (após grace)
        left_ids: Set[int] = set()
        for track_id, missing_at in list(missing_since.items()):
            if now - missing_at >= leave_grace_time:
                left_ids.add(track_id)
                missing_since.pop(track_id, None)

        for track_id in left_ids:
            joined_at = join_times.pop(track_id, None)
            if joined_at is not None:
                waited = max(0.0, now - joined_at)
                state.queue_abandon_count += 1
                state.queue_abandon_total_wait += waited
                state.queue_last_abandon_wait = waited

            last_seen.pop(track_id, None)

        # 3) Atualizar referência de quem está dentro neste frame
        state.queue_last_inside = set(current_objects)

        # 4) Calcular métricas de espera (apenas para quem tem join_time)
        wait_times = [
            max(0.0, now - t)
            for tid, t in join_times.items()
            if tid in current_objects
        ]

        queue_length = len(current_objects)
        avg_wait = (sum(wait_times) / len(wait_times)) if wait_times else 0.0
        max_wait = max(wait_times) if wait_times else 0.0

        abandon_count = state.queue_abandon_count
        abandon_avg_wait = (
            state.queue_abandon_total_wait / abandon_count
            if abandon_count > 0
            else 0.0
        )

        # 5) Determinar status da fila (quantidade + tempo)
        status = "QUEUE_NORMAL"
        alert = False

        reached_warning_len = (
            warning_queue_length > 0 and queue_length >= warning_queue_length
        )
        reached_critical_len = (
            critical_queue_length > 0 and queue_length >= critical_queue_length
        )

        has_warning_time = max_wait_warning > 0.0
        has_critical_time = max_wait_critical > 0.0

        if reached_critical_len:
            if state.queue_critical_since == 0.0:
                state.queue_critical_since = now
        else:
            state.queue_critical_since = 0.0

        if reached_warning_len:
            if state.queue_warning_since == 0.0:
                state.queue_warning_since = now
        else:
            state.queue_warning_since = 0.0

        elapsed_critical = (
            now - state.queue_critical_since
            if state.queue_critical_since > 0.0
            else 0.0
        )
        elapsed_warning = (
            now - state.queue_warning_since
            if state.queue_warning_since > 0.0
            else 0.0
        )

        if reached_critical_len:
            if has_critical_time:
                if elapsed_critical >= max_wait_critical:
                    status = "QUEUE_CRITICAL"
                    alert = True
            else:
                status = "QUEUE_CRITICAL"
                alert = True

        if status != "QUEUE_CRITICAL" and reached_warning_len:
            if has_warning_time:
                if elapsed_warning >= max_wait_warning:
                    status = "QUEUE_WARNING"
                    alert = True
            else:
                status = "QUEUE_WARNING"
                alert = True

        if status != state.status:
            logger.info(
                "Queue Zone '%s': %s → %s | len=%d, avg_wait=%ds, max_wait=%ds",
                config.name,
                state.status,
                status,
                queue_length,
                int(avg_wait),
                int(max_wait),
            )

        state.status = status

        can_alert = True
        if alert and state.last_alert_time > 0:
            elapsed = now - state.last_alert_time
            can_alert = elapsed >= config.email_cooldown

        if alert and can_alert:
            state.last_alert_time = now

        alert_message = None
        if alert:
            if status == "QUEUE_CRITICAL":
                alert_message = (
                    f"Fila crítica: {queue_length} pessoas, "
                    f"espera máxima {int(max_wait)}s"
                )
            elif status == "QUEUE_WARNING":
                alert_message = (
                    f"Fila alta: {queue_length} pessoas, "
                    f"espera média {int(avg_wait)}s"
                )

        return ZoneMetrics(
            zone_id=config.zone_id,
            zone_name=config.name,
            mode=config.mode.value,
            count=queue_length,
            status=status,
            alert=alert and can_alert,
            alert_message=alert_message,
            metadata={
                "queue_length": queue_length,
                "avg_wait_time": avg_wait,
                "max_wait_time": max_wait,
                "abandon_count": abandon_count,
                "abandon_avg_wait": abandon_avg_wait,
                "last_abandon_wait": state.queue_last_abandon_wait,
                "max_queue_length": max_queue_length,
                "warning_queue_length": warning_queue_length,
                "critical_queue_length": critical_queue_length,
                "max_wait_warning": max_wait_warning,
                "max_wait_critical": max_wait_critical,
            },
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )

    # ----------------------------------------------------------------------
    # GENÉRICO / LEGADO
    # ----------------------------------------------------------------------

    def _process_generic(
        self,
        zone: Zone,
        now: float,
        objects_inside: Set[int],
        global_ids_inside: Set[int] | None,
    ) -> ZoneMetrics:
        """Modo genérico/legado"""
        count = zone.state.object_count

        if count >= zone.config.full_threshold:
            new_status = "FULL"
        elif count > 0:
            new_status = "OCCUPIED"
        else:
            new_status = "EMPTY"

        zone.state.status = new_status

        return ZoneMetrics(
            zone_id=zone.config.zone_id,
            zone_name=zone.config.name,
            mode=zone.config.mode.value,
            count=count,
            status=new_status,
            alert=False,
            alert_message=None,
            metadata=None,
            active_track_ids=set(objects_inside),
            active_global_ids=set(global_ids_inside) if global_ids_inside is not None else None,
        )
