# ===================================================================
# backend/services/vision_system.py
# VISION SYSTEM v6.0 - MULTI-CAMERA PIPELINE ORCHESTRATOR
# - Suporte real a múltiplas câmeras com comportamento independente
# - Filtro de classes por câmera
# - Inferência centralizada
# - Tracking aplicado apenas sobre classes permitidas
# - Stream MJPEG contínuo
# - Contador de detecções únicas por dia
# - CONTRATO FECHADO COM A API (track_state, fps, status)
# ===================================================================

import threading
import time
import logging
from collections import deque
from typing import Dict, Generator, Optional, List, Set
import cv2
import numpy as np
from datetime import datetime

from backend.services.camera_worker import CameraWorker
from backend.services.inference_worker import InferenceWorker
from backend.services.tracking_worker import TrackingWorker
from config import settings

logger = logging.getLogger("vision_system")

# ===================================================================
# FPS Meter
# ===================================================================
class FPSMeter:
    """High-performance sliding-window FPS meter (thread-safe)."""

    def __init__(self, window: int = 50):
        self.window = window
        self.timestamps = deque(maxlen=window)
        self._lock = threading.Lock()

    def tick(self) -> float:
        now = time.time()
        with self._lock:
            self.timestamps.append(now)
            if len(self.timestamps) < 2:
                return 0.0
            dt = self.timestamps[-1] - self.timestamps[0]
            return (len(self.timestamps) - 1) / dt if dt > 0 else 0.0

    def average(self) -> float:
        with self._lock:
            if len(self.timestamps) < 2:
                return 0.0
            dt = self.timestamps[-1] - self.timestamps[0]
            return (len(self.timestamps) - 1) / dt if dt > 0 else 0.0

    def reset(self) -> None:
        with self._lock:
            self.timestamps.clear()


# ===================================================================
# Camera Context
# ===================================================================
class CameraContext:
    """
    Encapsula o contexto operacional de uma câmera:
    - Worker de captura
    - Classes permitidas para inferência/tracking
    - Estado de tracking independente
    """
    def __init__(self, source, allowed_classes: Optional[List[int]] = None):
        self.camera = CameraWorker(source=source)
        self.allowed_classes = allowed_classes
        self.track_state: Dict = {}


# ===================================================================
# VisionSystem
# ===================================================================
class VisionSystem:
    """
    Orquestrador central do pipeline:
    Camera -> Inference -> Class Filter -> Tracking -> Render -> MJPEG

    Este objeto é o *single source of truth* para a API.
    """

    COCO_CLASSES = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
        'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
        'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
        'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
        'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
        'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
        'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
        'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
        'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
        'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
    ]

    def __init__(self, camera_configs: Optional[List[dict]] = None):
        # ---- CONTRATO COM API ----
        self.stream_active: bool = False
        self.paused: bool = False
        self.track_state: Dict = {}        # <- agregado global
        self.current_fps: float = 0.0
        self.avg_fps: float = 0.0

        self.fps_meter = FPSMeter(window=50)

        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        # Contador diário
        self._unique_detections: Set[int] = set()
        self._detection_count_today = 0
        self._last_reset_date = datetime.now()

        # Configuração de câmeras
        # [
        #   {"source": 0, "classes": [0]},
        #   {"source": "rtsp://...", "classes": [2, 3]}
        # ]
        camera_configs = camera_configs or [{"source": 0, "classes": [0]}]

        self.contexts: List[CameraContext] = []
        for cfg in camera_configs:
            ctx = CameraContext(
                source=cfg["source"],
                allowed_classes=cfg.get("classes")
            )
            self.contexts.append(ctx)

        self.inference = InferenceWorker()
        self.tracker = TrackingWorker()

        logger.info("VisionSystem initialized with %d cameras", len(self.contexts))

    # ===================================================================
    # DAILY COUNTER
    # ===================================================================
    def _check_reset_daily_counter(self):
        now = datetime.now()
        if now.date() > self._last_reset_date.date():
            with self._lock:
                self._unique_detections.clear()
                self._detection_count_today = 0
                self._last_reset_date = now
                logger.info("🔄 Daily detection counter reset")

    def _update_detection_count(self, track_state: Dict):
        self._check_reset_daily_counter()
        with self._lock:
            for track_id, data in track_state.items():
                if track_id not in self._unique_detections and data.get("status") == "IN":
                    self._unique_detections.add(track_id)
                    self._detection_count_today += 1

    def get_detection_count(self) -> int:
        self._check_reset_daily_counter()
        with self._lock:
            return self._detection_count_today

    # ===================================================================
    # STREAM CONTROL
    # ===================================================================
    def is_live(self) -> bool:
        return self.stream_active

    def start_live(self) -> None:
        with self._lock:
            if self.stream_active:
                return

            self._stop_event.clear()
            for ctx in self.contexts:
                ctx.camera.start()

            self.stream_active = True
            self.paused = False
            self.fps_meter.reset()
            self.current_fps = 0.0
            self.avg_fps = 0.0
            logger.info("▶️ VisionSystem started")

    def stop_live(self) -> None:
        with self._lock:
            if not self.stream_active:
                return

            self._stop_event.set()
            for ctx in self.contexts:
                ctx.camera.stop()

            self.stream_active = False
            self.paused = False
            logger.info("⏹️ VisionSystem stopped")

    # ===================================================================
    # FILTER
    # ===================================================================
    def _filter_detections(self, detections, allowed_classes):
        if not detections or not allowed_classes:
            return detections

        filtered = []
        for result in detections:
            if not hasattr(result, "boxes") or len(result.boxes) == 0:
                continue

            keep = []
            for i, cls in enumerate(result.boxes.cls):
                if int(cls) in allowed_classes:
                    keep.append(i)

            if keep:
                result.boxes = result.boxes[keep]
                filtered.append(result)

        return filtered

    # ===================================================================
    # RENDER
    # ===================================================================
    def _draw_detections(self, frame: np.ndarray, detections) -> np.ndarray:
        if detections is None:
            return frame

        for result in detections:
            if not hasattr(result, "boxes"):
                continue

            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])

                name = self.COCO_CLASSES[cls_id] if cls_id < len(self.COCO_CLASSES) else str(cls_id)
                color = (0, 0, 255) if cls_id == 0 else (255, 0, 0)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"{name} {conf:.2f}",
                    (x1, max(20, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                    cv2.LINE_AA
                )

        return frame

    # ===================================================================
    # FRAME GENERATOR
    # ===================================================================
    def generate_frames(self) -> Generator[bytes, None, None]:
        placeholder = self._create_placeholder_frame("No Camera Feed")
        logger.info("🎬 Frame generator started")

        while not self._stop_event.is_set():
            if not self.stream_active or self.paused:
                time.sleep(0.01)
                continue

            aggregated_state: Dict = {}

            for idx, ctx in enumerate(self.contexts):
                frame = ctx.camera.get_frame()
                if frame is None:
                    frame = placeholder.copy()

                detections = self.inference.run(frame)
                detections = self._filter_detections(detections, ctx.allowed_classes)

                frame = self._draw_detections(frame, detections)

                with self._lock:
                    ctx.track_state = self.tracker.update(detections)
                    self._update_detection_count(ctx.track_state)

                    # agrega com namespace por câmera
                    for k, v in ctx.track_state.items():
                        aggregated_state[f"cam{idx}:{k}"] = v

                self.current_fps = self.fps_meter.tick()
                self.avg_fps = self.fps_meter.average()

                mjpeg = ctx.camera.encode_mjpeg(frame)
                if mjpeg:
                    yield mjpeg

            # estado global visível para a API
            with self._lock:
                self.track_state = aggregated_state

        logger.info("🛑 Frame generator stopped")

    # ===================================================================
    # PLACEHOLDER
    # ===================================================================
    @staticmethod
    def _create_placeholder_frame(message: str) -> np.ndarray:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, message, (20, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame
