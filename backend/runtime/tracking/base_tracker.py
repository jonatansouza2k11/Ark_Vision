# backend/runtime/tracking/base_tracker.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np

Detection = Dict[str, Any]       # {"bbox": [...], "class_id": int, "confidence": float}
TrackState = Dict[int, Dict[str, Any]]  # {track_id: detection-like dict}


class BaseTracker(ABC):
    """
    Contrato de tracker para o Ark Vision.

    Entrada: frame + lista de detecções YOLO do frame atual.
    Saída: track_state compatível com ZoneProcessorV3:
        {
            track_id: {
                "bbox": [x1, y1, x2, y2],
                "class_id": int,
                "confidence": float,
                ...  # campos extras futuros (ex.: embedding, camera_id, etc.)
            },
            ...
        }
    """

    def __init__(
        self,
        camera_id: int,
        classes_filter: Optional[List[int]] = None,
    ) -> None:
        self.camera_id = camera_id
        self.classes_filter = classes_filter or []

    @abstractmethod
    def update(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        timestamp: float,
    ) -> TrackState:
        """
        Atualiza o estado de tracking e retorna o track_state do frame atual.
        """
        raise NotImplementedError

    def close(self) -> None:
        """
        Hook opcional para liberar recursos (modelos de ReID, trackers externos, etc.).
        Implementações concretas podem sobrescrever se necessário.
        """
        pass
