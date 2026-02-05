"""
Capacity Mode Handler
Alerta quando capacidade máxima é atingida ou aproximada.
"""

import logging
from datetime import datetime
from typing import Dict

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState
from application.zone.modes.common.timers import should_send_alert

logger = logging.getLogger(__name__)


class CapacityModeHandler(BaseModeHandler):
    """
    Capacity mode: Alerta quando aproximando/excedendo capacidade máxima.
    
    Lógica:
    - max_capacity: Capacidade máxima da zona
    - alert_percentage: % da capacidade que dispara alerta (default: 100%)
    - full_timeout: Tempo mínimo acima do threshold antes de alertar
    
    Estados:
    - NORMAL: Abaixo do threshold
    - PENDING: Acima do threshold mas aguardando confirmação
    - WARNING: >= alert_threshold mas < max_capacity (confirmado)
    - CRITICAL: >= max_capacity (confirmado)
    """
    
    def process(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float
    ) -> Dict:
        """
        Processa zona em modo capacity.
        
        Args:
            zone: Configuração da zona (dict do DB)
            state: Estado runtime da zona
            track_state: Estado de tracking {track_id: {bbox, class_id, ...}}
            current_time: Timestamp atual (Unix)
        
        Returns:
            Dict com métricas da zona
        """
        metadata = zone.get("metadata", {})
        max_capacity = metadata.get("max_capacity", 50)
        alert_percentage = metadata.get("alert_percentage", 100)
        count = state.object_count
        now = datetime.fromtimestamp(current_time)
        
        # Calcular threshold de alerta
        alert_threshold = int(max_capacity * (alert_percentage / 100))
        capacity_timeout = zone.get("full_timeout", 10.0)
        
        # Determinar status
        if count >= alert_threshold:
            if state.full_since is None:
                state.full_since = now
            
            elapsed = (now - state.full_since).total_seconds()
            
            if elapsed >= capacity_timeout:
                # ✅ Confirmado após timeout
                if count >= max_capacity:
                    new_status = "CRITICAL"
                else:
                    new_status = "WARNING"
                alert = True
            else:
                # ⏳ Aguardando confirmação
                new_status = "PENDING"
                alert = False
        else:
            # ✅ Abaixo do threshold
            if state.full_since is not None and state.status in ["WARNING", "CRITICAL", "PENDING"]:
                logger.info(
                    f"📉 Zone '{zone['name']}' saiu do alerta: "
                    f"{state.status} → NORMAL ({count}/{max_capacity})"
                )
            
            state.full_since = None
            new_status = "NORMAL"
            alert = False
        
        # Email cooldown
        email_cooldown = zone.get("email_cooldown", 600.0)
        can_alert = should_send_alert(alert, state.last_alert_time, email_cooldown, now)
        
        if alert and can_alert:
            state.last_alert_time = now
        
        # Log mudanças de status
        if new_status != state.status:
            logger.info(
                f"📊 Zone '{zone['name']}': "
                f"{state.status} → {new_status} ({count}/{max_capacity} = {round(count/max_capacity*100)}%)"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "capacity",
            "count": count,
            "max_capacity": max_capacity,
            "occupancy_percent": round((count / max_capacity) * 100, 1) if max_capacity > 0 else 0,
            "status": new_status,
            "alert": alert and can_alert,
            "alert_message": (
                f"Capacidade: {count}/{max_capacity} ({round(count/max_capacity*100)}%)"
                if alert else None
            ),
        }
