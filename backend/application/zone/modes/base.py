from typing import Protocol, Dict, Any, Tuple, Optional
from datetime import datetime
import numpy as np

from backend.runtime.workers.zone_processor import ZoneState

class ZoneModeHandler(Protocol):
    """Interface para handlers de modo de zona."""
    
    def process(
        self,
        zone: Dict[str, Any],
        state: 'ZoneState',  # Import do processor.py
        track_state: Dict[int, Dict],
        frame_shape: Tuple[int, int],
        now: datetime
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Processa uma zona segundo as regras do modo.
        
        Returns:
            (metrics, updated_metadata)
            - metrics: payload de métricas para API/frontend
            - updated_metadata: dict para persistir no DB (só counting precisa)
        """
        ...
