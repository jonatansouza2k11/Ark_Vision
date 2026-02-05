# backend/runtime/tracking/simple_tracker.py

from typing import Dict, Any, List
import numpy as np

from .base_tracker import BaseTracker, Detection, TrackState


class SimpleDetectionTracker(BaseTracker):
    """
    Tracker mínimo: não mantém histórico entre frames.
    Usa o índice da detecção como track_id, replicando o comportamento atual
    do VisionSystem antes de introduzirmos tracking/ReID de verdade.
    """

    def update(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        timestamp: float,
    ) -> TrackState:
        track_state: TrackState = {}

        for idx, det in enumerate(detections):
            # Opcional: aplicar filtro de classes aqui se quiser
            class_id = int(det.get("class_id", -1))
            if self.classes_filter and class_id not in self.classes_filter:
                continue

            track_state[idx] = det

        return track_state
