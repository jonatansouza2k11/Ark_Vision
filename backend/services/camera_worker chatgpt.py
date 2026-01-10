import cv2
import threading
import time
import logging
from typing import Optional

from config import settings

logger = logging.getLogger("camera_worker")


class CameraWorker:
    """
    CameraWorker
    ------------------------------------------------------------------
    Responsável exclusivamente pela captura de frames.
    Estratégia: latest-frame-only (zero backlog, baixa latência)
    """

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False

        self._frame: Optional[any] = None
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

        self.cap = cv2.VideoCapture(settings.video_source_parsed)

        # Defensive check
        if not self.cap.isOpened():
            raise RuntimeError("❌ Failed to open video source")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, settings.CAM_FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # critical for latency

        self.running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="CameraWorkerThread",
            daemon=True
        )
        self._thread.start()

        logger.info("📷 CameraWorker started")

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
        self._frame = None

        logger.info("📷 CameraWorker stopped")

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
                time.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if not ret:
                logger.warning("⚠️ Camera read failed, retrying...")
                time.sleep(0.05)
                continue

            # Latest-frame-wins (atomic swap)
            with self._lock:
                self._frame = frame

    # ==================================================================
    # PUBLIC API
    # ==================================================================
    def get_frame(self):
        """
        Retorna cópia defensiva do último frame válido
        """
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def encode_mjpeg(self, frame) -> Optional[bytes]:
        """
        Encode frame para MJPEG (boundary incluído)
        Contrato esperado pelo StreamingResponse
        """
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
                b"Content-Type: image/jpeg\r\n\r\n" +
                jpeg.tobytes() +
                b"\r\n"
            )
        except Exception as e:
            logger.error(f"❌ MJPEG encode error: {e}")
            return None
