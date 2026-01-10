# ===================================================================
# backend/services/tracking_worker.py
# TrackingWorker v5.0 - IoU Based Tracker
# -------------------------------------------------------------------
# Responsabilidade:
# - Receber detecções YOLO
# - Manter IDs estáveis
# - Associar objetos via IoU
# - Gerenciar expiração (TTL)
#
# NÃO FAZ:
# - Inferência
# - Regras de negócio
# - Filtro por câmera
# - Stream
# ===================================================================

import threading
import time
import logging
from typing import Dict, Any, Tuple

from config import settings

logger = logging.getLogger("tracking_worker")


class TrackingWorker:
    """
    TrackingWorker
    ------------------------------------------------------------------
    Rastreador baseado em IoU.
    Mantém estado mínimo e IDs estáveis.
    """

    def __init__(self):
        self.state: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        self._next_id = 1
        self._last_cleanup = time.time()

        self._iou_threshold = settings.TRACKING_IOU_THRESHOLD
        self._ttl_seconds = settings.TRACKING_TTL_SECONDS

        logger.info("🧭 TrackingWorker initialized (IoU)")

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    def start(self) -> None:
        logger.info("🧭 TrackingWorker started")

    def stop(self) -> None:
        with self._lock:
            self.state.clear()
            self._next_id = 1
        logger.info("🧭 TrackingWorker stopped")

    # ==================================================================
    # CORE
    # ==================================================================

    @staticmethod
    def _compute_iou(box1: Tuple, box2: Tuple) -> float:
        """
        Calcula Intersection over Union entre duas boxes.
        box = (x1, y1, x2, y2)
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)

        union_area = box1_area + box2_area - inter_area
        if union_area <= 0:
            return 0.0

        return inter_area / union_area

    def update(self, detections):
        """
        Recebe resultados YOLO e atualiza estado de tracking.
        Retorna snapshot do estado atual.
        """
        now = time.time()

        if detections is None:
            return dict(self.state)

        with self._lock:
            try:
                current_boxes = []

                for result in detections:
                    if not hasattr(result, "boxes"):
                        continue

                    for box in result.boxes:
                        xyxy = box.xyxy[0]
                        if hasattr(xyxy, "cpu"):
                            xyxy = xyxy.cpu().numpy()
                        current_boxes.append(tuple(xyxy))

                matched_ids = set()

                for current_box in current_boxes:
                    best_iou = 0.0
                    best_id = None

                    for track_id, track_data in self.state.items():
                        if "bbox" not in track_data:
                            continue

                        iou = self._compute_iou(current_box, track_data["bbox"])
                        if iou > best_iou and iou >= self._iou_threshold:
                            best_iou = iou
                            best_id = track_id

                    if best_id is not None:
                        self.state[best_id]["bbox"] = current_box
                        self.state[best_id]["last_seen"] = now
                        self.state[best_id]["status"] = "IN"
                        matched_ids.add(best_id)
                    else:
                        new_id = self._next_id
                        self._next_id += 1

                        self.state[new_id] = {
                            "bbox": current_box,
                            "status": "IN",
                            "last_seen": now,
                        }
                        matched_ids.add(new_id)

                for track_id in list(self.state.keys()):
                    if track_id not in matched_ids:
                        if now - self.state[track_id]["last_seen"] > self._ttl_seconds:
                            self.state[track_id]["status"] = "OUT"

                # Cleanup periódico
                if now - self._last_cleanup > 5.0:
                    expired = [
                        tid for tid, data in self.state.items()
                        if now - data["last_seen"] > self._ttl_seconds * 3
                    ]
                    for tid in expired:
                        del self.state[tid]
                    self._last_cleanup = now

            except Exception as e:
                logger.error(f"❌ Tracking update error: {e}", exc_info=True)

            return dict(self.state)
