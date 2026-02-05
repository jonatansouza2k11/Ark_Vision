"""
Occupancy Mode Handler
Detecta estados EMPTY / OCCUPIED / FULL com timeouts de confirmação.
"""

import logging
from datetime import datetime
from typing import Dict

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState
from application.zone.modes.common.timers import should_send_alert

logger = logging.getLogger(__name__)


class OccupancyModeHandler(BaseModeHandler):
    """
    Occupancy mode: Detecta estados de ocupação com confirmação temporal.
    
    Lógica:
    - empty_threshold: Pessoas <= X → EMPTY
    - full_threshold: Pessoas >= Y → FULL
    - empty_timeout: Tempo mínimo vazia antes de alertar
    - full_timeout: Tempo mínimo cheia antes de alertar
    
    Estados:
    - EMPTY: Zona vazia (confirmado após timeout)
    - EMPTY_PENDING: Vazia mas aguardando confirmação
    - OCCUPIED: Ocupada (estado intermediário)
    - FULL: Zona cheia (confirmado após timeout)
    - FULL_PENDING: Cheia mas aguardando confirmação
    """
    
    def process(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float
    ) -> Dict:
        """
        Processa zona em modo occupancy.
        
        Args:
            zone: Configuração da zona
            state: Estado runtime
            track_state: Estado de tracking
            current_time: Timestamp atual (Unix)
        
        Returns:
            Dict com métricas
        """
        count = state.object_count
        empty_threshold = zone.get("empty_threshold", 0)
        full_threshold = zone.get("full_threshold", 3)
        empty_timeout = zone.get("empty_timeout", 5.0)
        full_timeout = zone.get("full_timeout", 10.0)
        email_cooldown = zone.get("email_cooldown", 600.0)
        
        now = datetime.fromtimestamp(current_time)
        
        # Determinar status RAW (baseado em threshold)
        if count <= empty_threshold:
            raw_status = "EMPTY"
        elif count >= full_threshold:
            raw_status = "FULL"
        else:
            raw_status = "OCCUPIED"
        
        # Atualizar timers
        if raw_status == "EMPTY":
            if state.empty_since is None:
                state.empty_since = now
            state.full_since = None
        elif raw_status == "FULL":
            if state.full_since is None:
                state.full_since = now
            state.empty_since = None
        else:
            # OCCUPIED - reseta timers
            state.empty_since = None
            state.full_since = None
        
        # Verificar confirmação (após timeout)
        alert = False
        alert_message = None
        confirmed_status = raw_status
        
        if raw_status == "EMPTY" and state.empty_since:
            elapsed = (now - state.empty_since).total_seconds()
            if elapsed >= empty_timeout:
                # ✅ Confirmado
                alert = True
                alert_message = f"Zona vazia por {int(elapsed)}s"
                confirmed_status = "EMPTY"
            else:
                # ⏳ Aguardando
                confirmed_status = "EMPTY_PENDING"
                alert = False
        
        if raw_status == "FULL" and state.full_since:
            elapsed = (now - state.full_since).total_seconds()
            if elapsed >= full_timeout:
                # ✅ Confirmado
                alert = True
                alert_message = f"Zona cheia por {int(elapsed)}s"
                confirmed_status = "FULL"
            else:
                # ⏳ Aguardando
                confirmed_status = "FULL_PENDING"
                alert = False
        
        # Email cooldown
        can_alert = should_send_alert(alert, state.last_alert_time, email_cooldown, now)
        
        if alert and can_alert:
            state.last_alert_time = now
        
        # Log mudanças de status
        if confirmed_status != state.status:
            elapsed_info = ""
            if state.empty_since:
                elapsed_info = f" (vazia há {int((now - state.empty_since).total_seconds())}s)"
            elif state.full_since:
                elapsed_info = f" (cheia há {int((now - state.full_since).total_seconds())}s)"
            
            logger.info(
                f"🏢 Zone '{zone['name']}': "
                f"{state.status} → {confirmed_status} ({count} pessoas){elapsed_info}"
            )
        
        state.status = confirmed_status
        
        # Calcular durações para frontend
        empty_duration = 0
        full_duration = 0
        
        if state.empty_since and confirmed_status == "EMPTY_PENDING":
            empty_duration = (now - state.empty_since).total_seconds()
        
        if state.full_since and confirmed_status == "FULL_PENDING":
            full_duration = (now - state.full_since).total_seconds()
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "occupancy",
            "count": count,
            "status": confirmed_status,
            "alert": alert and can_alert,
            "alert_message": alert_message,
            "empty_duration": empty_duration,
            "full_duration": full_duration,
        }
