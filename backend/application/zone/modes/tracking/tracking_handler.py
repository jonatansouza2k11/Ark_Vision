"""
Tracking Mode Handler
Rastreamento simples de presença (sem thresholds).
"""

import logging
from typing import Dict

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState

logger = logging.getLogger(__name__)


class TrackingModeHandler(BaseModeHandler):
    """
    Tracking mode: Rastreamento simples de IDs presentes.
    
    Lógica:
    - Rastreia IDs únicos que passam pela zona
    - Não aplica thresholds ou timeouts
    
    Estados:
    - TRACKING: Objetos presentes
    - IDLE: Zona vazia
    """
    
    def process(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float
    ) -> Dict:
        """
        Processa zona em modo tracking.
        
        Args:
            zone: Configuração da zona
            state: Estado runtime
            track_state: Estado de tracking
            current_time: Timestamp atual (Unix)
        
        Returns:
            Dict com métricas
        """
        count = state.object_count
        new_status = "TRACKING" if count > 0 else "IDLE"
        
        if new_status != state.status:
            logger.info(f"🎯 Zone '{zone['name']}': tracking {count} object(s)")
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "tracking",
            "count": count,
            "tracked_ids": list(state.objects_inside),
            "status": new_status,
            "alert": False,
        }
