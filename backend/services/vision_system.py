# ===================================================================
# backend/services/vision_system.py
# VISION SYSTEM v7.2 - MEMORY-SAFE MULTI-CAMERA ORCHESTRATOR (GOVERNED)
# ===================================================================

import threading
import time
import logging
import gc
from collections import deque
from typing import Dict, Generator, Optional, List, Set
import cv2
import numpy as np
from datetime import datetime

from backend.services.camera_worker import CameraWorker
from backend.services.inference_worker import InferenceWorker
from backend.services.tracking_worker import TrackingWorker
from backend.config import settings

logger = logging.getLogger("vision_system")


class FPSMeter:
    def __init__(self, window: int = 50):
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


class CameraContext:
    def __init__(self, source, allowed_classes: Optional[List[int]] = None):
        self.camera = CameraWorker(source=source)
        self.allowed_classes = allowed_classes
        self.track_state: Dict = {}
        self.last_frame: Optional[np.ndarray] = None


class VisionSystem:
    TARGET_FPS = getattr(settings, "STREAM_TARGET_FPS", 15)

    def __init__(self, camera_configs: Optional[List[dict]] = None):
        self.stream_active = False
        self.paused = False

        self.fps_meter = FPSMeter(window=50)
        self.current_fps = 0.0
        self.avg_fps = 0.0

        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        self.track_state: Dict = {}

        # Governed detection metrics
        self._unique_detections: Set[int] = set()
        self._detection_count_today = 0
        self._last_reset_date = datetime.now()

        camera_configs = camera_configs or [{"source": 0, "classes": [0]}]
        self.contexts: List[CameraContext] = [
            CameraContext(cfg["source"], cfg.get("classes"))
            for cfg in camera_configs
        ]

        self.inference = InferenceWorker()
        self.tracker = TrackingWorker()

        self._frame_interval = 1.0 / max(1, self.TARGET_FPS)

        logger.info("VisionSystem initialized with %d cameras", len(self.contexts))

    # ===================================================================
    # STREAM CONTROL
    # ===================================================================

    def start_live(self) -> None:
        with self._lock:
            if self.stream_active:
                return

            self._stop_event.clear()

            for ctx in self.contexts:
                ctx.camera.start()
                ctx.track_state.clear()
                ctx.last_frame = None

            self.inference.start()
            self.stream_active = True
            self.paused = False
            self.fps_meter.reset()

            logger.info("▶️ VisionSystem started")

    def stop_live(self) -> None:
        with self._lock:
            if not self.stream_active:
                return

            self._stop_event.set()

            for ctx in self.contexts:
                ctx.camera.stop()
                ctx.track_state.clear()
                ctx.last_frame = None

            self.inference.stop()
            self.track_state = {}
            self.stream_active = False
            self.paused = False

            gc.collect()
            logger.info("⏹️ VisionSystem stopped")

    # ===================================================================
    # FRAME GENERATOR
    # ===================================================================

    def generate_frames(self) -> Generator[bytes, None, None]:
        placeholder = self._create_placeholder_frame("No Camera Feed")
        logger.info("🎬 Frame generator started")

        try:
            while self.stream_active and not self._stop_event.is_set():
                for ctx in self.contexts:
                    if not self.stream_active or self._stop_event.is_set():
                        return

                    start = time.time()
                    #frame = ctx.camera.get_frame() or placeholder.copy()
                    frame = ctx.camera.get_frame()
                    frame = frame if frame is not None else placeholder.copy()


                    detections = self.inference.run(frame)
                    frame = self._draw_detections(frame, detections)

                    with self._lock:
                        ctx.track_state = self.tracker.update(detections)
                        self.track_state = ctx.track_state

                        # ---- CONTABILIZA DETECÇÕES ÚNICAS ----
                        today = datetime.now().date()
                        if today != self._last_reset_date.date():
                            self._unique_detections.clear()
                            self._detection_count_today = 0
                            self._last_reset_date = datetime.now()

                        for obj_id in ctx.track_state.keys():
                            if obj_id not in self._unique_detections:
                                self._unique_detections.add(obj_id)
                                self._detection_count_today += 1

                    self.current_fps = self.fps_meter.tick()
                    self.avg_fps = self.fps_meter.average()

                    mjpeg = ctx.camera.encode_mjpeg(frame)
                    if mjpeg:
                        yield mjpeg

                    del frame, detections

                    elapsed = time.time() - start
                    sleep_time = self._frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        finally:
            logger.info("🛑 Frame generator stopped")
            gc.collect()

    # ===================================================================
    # RENDERING
    # ===================================================================

    @staticmethod
    def _draw_detections(frame, results):
        """
        Renderiza bounding boxes no frame.

        Mantém o VisionSystem desacoplado do YOLO:
        - Não assume formato interno além da API pública
        - Funciona com múltiplos modelos no futuro
        """
        if results is None:
            return frame

        try:
            # Ultralytics retorna uma lista de Results
            r = results[0]
            if hasattr(r, "plot"):
                return r.plot()
        except Exception:
            pass

        return frame


    # ===================================================================
    # PLACEHOLDER
    # ===================================================================

    @staticmethod
    def _create_placeholder_frame(message: str) -> np.ndarray:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            message,
            (20, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
        return frame

    # ===================================================================
    # METRICS API CONTRACT
    # ===================================================================

    def get_detection_count(self) -> int:
        """
        Retorna o número de pessoas únicas detectadas no dia.
        Compatível com o contrato exigido pela API.
        """
        with self._lock:
            today = datetime.now().date()
            if today != self._last_reset_date.date():
                self._unique_detections.clear()
                self._detection_count_today = 0
                self._last_reset_date = datetime.now()

            return int(self._detection_count_today)
