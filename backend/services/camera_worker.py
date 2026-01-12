# ===================================================================
# backend/services/camera_worker.py
# CameraWorker v5.1 - Memory Governed Edition
# ===================================================================

import cv2
import threading
import time
import logging
import gc
from typing import Optional, Any
from config import settings

logger = logging.getLogger("camera_worker")


class CameraWorker:
    def __init__(self, source: Any = None, name: Optional[str] = None):
        self.source = source if source is not None else settings.video_source_parsed
        self.name = name or f"camera-{self.source}"

        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False

        self._frame: Optional[Any] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        self._target_fps = max(1, int(settings.CAM_FPS))
        self._frame_interval = 1.0 / self._target_fps

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    def start(self) -> None:
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            raise RuntimeError(f"❌ Failed to open video source: {self.source}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, settings.CAM_FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.running = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f"CameraWorker[{self.name}]",
            daemon=True
        )
        self._thread.start()

        logger.info(f"📷 CameraWorker started ({self.name} | source={self.source})")

    def stop(self) -> None:
        self.running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        with self._lock:
            self._frame = None

        gc.collect()
        logger.info(f"📷 CameraWorker stopped ({self.name})")

    # ==================================================================
    # INTERNAL LOOP
    # ==================================================================

    def _loop(self) -> None:
        next_frame_time = time.perf_counter()

        while self.running:
            now = time.perf_counter()

            if now < next_frame_time:
                time.sleep(0.001)
                continue

            next_frame_time = now + self._frame_interval

            if not self.cap:
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()

            if not ret:
                logger.warning(f"⚠️ Camera read failed ({self.name}), retrying...")
                time.sleep(0.05)
                continue

            with self._lock:
                self._frame = frame

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    def get_frame(self):
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def encode_mjpeg(self, frame) -> Optional[bytes]:
        try:
            ret, jpeg = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY]
            )

            if not ret:
                return None

            return (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )

        except Exception as e:
            logger.error(f"❌ MJPEG encode error ({self.name}): {e}")
            return None
