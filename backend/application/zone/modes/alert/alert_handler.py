"""
Alert Mode Handler

Alerta imediato quando threshold é excedido.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState
from application.zone.modes.common.timers import should_send_alert

logger = logging.getLogger(__name__)


class AlertModeHandler(BaseModeHandler):
    """
    Alert mode: Alerta imediato quando threshold excedido.

    Lógica:
    - full_threshold: Pessoas >= X → ALERTA
    - full_timeout: Tempo mínimo acima do threshold antes de alertar

    Estados:
    - NORMAL: Abaixo do threshold
    - PENDING: Acima do threshold mas aguardando confirmação
    - ALERT: Threshold excedido (confirmado)
    """

    def process(
        self,
        zone: Dict[str, Any],
        state: ZoneState,
        track_state: Dict[int, Dict[str, Any]],
        current_time: float,
    ) -> Dict[str, Any]:
        """
        Processa zona em modo alert.

        Args:
            zone: Configuração da zona.
            state: Estado runtime.
            track_state: Estado de tracking da zona (por track_id).
            current_time: Timestamp atual (epoch, segundos).

        Returns:
            Dict com métricas/estado da zona (compatível com ZoneMetrics.to_dict()).
        """
        count = state.object_count

        full_threshold = zone.get("full_threshold", 1)
        full_timeout = float(zone.get("full_timeout", 10.0))
        email_cooldown = float(zone.get("email_cooldown", 120.0))

        now = datetime.fromtimestamp(current_time)

        # --------------------------------------------------------------
        # Avaliação de estado (NORMAL / PENDING / ALERT)
        # --------------------------------------------------------------
        if count >= full_threshold:
            if state.full_since is None:
                # Primeira vez acima do threshold
                state.full_since = now

            elapsed = (now - state.full_since).total_seconds()
            if elapsed >= full_timeout:
                new_status = "ALERT"
                alert = True
            else:
                new_status = "PENDING"
                alert = False
        else:
            # Voltou a ficar abaixo do threshold
            state.full_since = None
            new_status = "NORMAL"
            alert = False

        # --------------------------------------------------------------
        # Cooldown para disparo de alerta (e‑mail / notificação)
        # --------------------------------------------------------------
        can_alert = should_send_alert(
            alert=alert,
            last_alert_time=state.last_alert_time,
            cooldown_seconds=email_cooldown,
            now=now,
        )

        if alert and can_alert:
            state.last_alert_time = now

        # Log apenas em mudança de status
        if new_status != state.status:
            logger.warning(
                "🚨 Zone '%s': %s → %s (%d pessoas)",
                zone.get("name"),
                state.status,
                new_status,
                count,
            )

        state.status = new_status

        # --------------------------------------------------------------
        # Coleta de ids de track locais/global para downstream (ReID, etc.)
        # --------------------------------------------------------------
        active_track_ids = list(track_state.keys()) if track_state else []
        active_global_ids = [
            t.get("global_id")
            for t in (track_state or {}).values()
            if isinstance(t, dict) and t.get("global_id") is not None
        ]

        # --------------------------------------------------------------
        # Payload de métricas (usado por ZoneProcessorV3 → ZoneAlertHandler)
        # --------------------------------------------------------------
        metrics: Dict[str, Any] = {
            "zone_id": state.zone_id,
            "zone_name": zone.get("name"),
            "zonename": zone.get("name"),  # compat legado
            "mode": "alert",
            "count": count,
            "status": new_status,
            "alert": bool(alert and can_alert),
            "alert_message": (
                f"ALERTA: {count} pessoas na zona" if alert and can_alert else None
            ),
            "metadata": zone.get("metadata") or {},
            "activetrackids": active_track_ids,
            "activeglobalids": active_global_ids,
            "full_threshold": full_threshold,
            "full_timeout": full_timeout,
            "email_cooldown": email_cooldown,
            "last_alert_time": state.last_alert_time.isoformat()
            if state.last_alert_time
            else None,
            "full_since": state.full_since.isoformat() if state.full_since else None,
            "timestamp": current_time,
        }

        return metrics
