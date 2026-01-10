# ===================================================================
# backend/services/vision_system.py
# VISION SYSTEM v5.0 - SENIOR READY
# - Multi-cameras
# - Async MJPEG streaming
# - Robust Tracking
# - FPS metrics
# - Placeholder frame on camera failure
# - Thread-safe
# - Ready for FastAPI StreamingResponse
# ===================================================================

import threading
import time
import logging
from collections import deque
from typing import Dict, Generator, Optional, List
import cv2
import numpy as np

from backend.services.camera_worker import CameraWorker
from backend.services.inference_worker import InferenceWorker
from backend.services.tracking_worker import TrackingWorker

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
# VisionSystem
# ===================================================================
class VisionSystem:
    """
    Central orchestrator for multi-camera computer vision pipelines:
    Camera -> Inference -> Tracking -> MJPEG Stream
    """
    def __init__(self, camera_sources: Optional[List[int]] = None):
        self.stream_active: bool = False
        self.paused: bool = False

        self.track_state: Dict = {}
        self.fps_meter = FPSMeter(window=50)
        self.current_fps: float = 0.0
        self.avg_fps: float = 0.0

        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        # Initialize camera workers
        self.cameras: List[CameraWorker] = []
        camera_sources = camera_sources or [0]  # default camera 0
        for src in camera_sources:
            cam_worker = CameraWorker()
            cam_worker.cap = src
            self.cameras.append(cam_worker)

        self.inference = InferenceWorker()
        self.tracker = TrackingWorker()

        logger.info("✅ VisionSystem initialized with %d cameras", len(self.cameras))

    # ===================================================================
    # STREAM CONTROL
    # ===================================================================
    def is_live(self) -> bool:
        return self.stream_active

    def start_live(self) -> None:
        with self._lock:
            if self.stream_active:
                logger.debug("VisionSystem already running")
                return

            self._stop_event.clear()
            for cam in self.cameras:
                cam.start()

            self.stream_active = True
            self.paused = False
            self.fps_meter.reset()
            self.current_fps = 0.0
            self.avg_fps = 0.0
            logger.info("▶️ VisionSystem stream started")

    def stop_live(self) -> None:
        with self._lock:
            if not self.stream_active:
                logger.debug("VisionSystem already stopped")
                return

            self._stop_event.set()
            for cam in self.cameras:
                try:
                    cam.stop()
                except Exception as e:
                    logger.warning(f"Camera stop warning: {e}")

            self.stream_active = False
            self.paused = False
            logger.info("⏹️ VisionSystem stream stopped")

    def toggle_pause(self) -> bool:
        with self._lock:
            self.paused = not self.paused
            logger.info(f"⏸️ VisionSystem paused={self.paused}")
            return self.paused

    # ===================================================================
    # FRAME GENERATOR (MJPEG) - Async Multi-Camera
    # ===================================================================
    def generate_frames(self) -> Generator[bytes, None, None]:
        """
        MJPEG frame generator for FastAPI StreamingResponse
        - Produces placeholder if frame lost
        - Handles multi-camera round-robin
        """
        logger.info("🎬 VisionSystem frame generator started")

        placeholder_frame = self._create_placeholder_frame("No Camera Feed")

        while not self._stop_event.is_set():
            if not self.stream_active or self.paused:
                time.sleep(0.01)
                continue

            try:
                for cam in self.cameras:
                    frame = cam.get_frame()
                    if frame is None:
                        logger.warning(f"⚠️ Camera {cam.cap} lost frame, sending placeholder...")
                        frame = placeholder_frame

                    # ----------------------------
                    # INFERENCE
                    # ----------------------------
                    detections = self.inference.run(frame)

                    # ----------------------------
                    # TRACKING
                    # ----------------------------
                    with self._lock:
                        self.track_state = self.tracker.update(detections)

                    # ----------------------------
                    # FPS METRICS
                    # ----------------------------
                    fps_now = self.fps_meter.tick()
                    self.current_fps = fps_now
                    self.avg_fps = self.fps_meter.average()

                    # ----------------------------
                    # MJPEG ENCODE
                    # ----------------------------
                    mjpeg = cam.encode_mjpeg(frame)
                    if mjpeg:
                        yield mjpeg

            except Exception as e:
                logger.error(f"❌ Vision pipeline error: {e}")
                time.sleep(0.01)

        logger.info("🛑 Frame generator stopped")

    # ===================================================================
    # PLACEHOLDER FRAME
    # ===================================================================
    @staticmethod
    def _create_placeholder_frame(message: str = "No Feed") -> np.ndarray:
        """Creates a static placeholder frame with a message"""
        width, height = 640, 480
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(frame, message, (20, height // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 0, 255), 2, cv2.LINE_AA)
        return frame
