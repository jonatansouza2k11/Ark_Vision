import cv2
import threading
import time
import logging
import gc
from typing import Optional, Any, Callable
import numpy as np

from backend.core.config.config import settings
from backend.runtime.workers.metrics import FPSMeter

logger = logging.getLogger("camera_worker")


class CameraWorker:
    """
    Low-level camera frame capture worker.
    """

    def __init__(
        self,
        camera_id: int,
        source: Any,
        name: Optional[str] = None,
        metrics_callback: Optional[Callable[[dict], None]] = None,
    ):
        self.camera_id = camera_id
        self.source = source
        self.name = name or f"camera-{camera_id}"
        self.metrics_callback = metrics_callback
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        
        self._target_fps = max(1, int(settings.STREAM_TARGET_FPS))
        self._frame_interval = 1.0 / self._target_fps
        
        # FPS tracking
        self.fps_meter = FPSMeter(window=50)
        self.last_metrics_update: float = 0.0

        logger.info(f"📷 CameraWorker created: {self.name} (FPS: {self._target_fps})")

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def start(self) -> None:
        if self.running:
            logger.warning(f"⚠️ {self.name} already running")
            return

        import platform

        if isinstance(self.source, int):
            if platform.system() == "Windows":
                # Tenta DSHOW primeiro, fallback automático
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    logger.warning(f"⚠️ {self.name}: DSHOW failed, falling back to default backend")
                    self.cap = cv2.VideoCapture(self.source)
            else:
                self.cap = cv2.VideoCapture(self.source)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"❌ Failed to open source: {self.source} ({self.name})")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, settings.STREAM_TARGET_FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logger.info(f"✅ {self.name} started")

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                logger.error(f"❌ Error releasing capture for {self.name}: {e}")
            self.cap = None

        with self._lock:
            self._frame = None

        gc.collect()
        logger.info(f"✅ {self.name} stopped and cleaned up")

    # ========================================================================
    # CAPTURE LOOP
    # ========================================================================

    def _capture_loop(self) -> None:
        next_frame_time = time.perf_counter()
        consecutive_errors = 0
        max_errors = 10

        while self.running:
            try:
                now = time.perf_counter()
                if now < next_frame_time:
                    time.sleep(0.001)
                    continue

                next_frame_time = now + self._frame_interval

                if not self.cap:
                    time.sleep(0.05)
                    continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        logger.error(f"❌ {self.name}: Too many capture errors, stopping")
                        self.running = False
                        break
                    time.sleep(0.1)
                    continue

                consecutive_errors = 0

                # ✅ NOVO: Aplicar flip horizontal na origem (se configurado no .env)
                if settings.FLIP_HORIZONTAL:
                    frame = cv2.flip(frame, 1)

                if frame.shape[1] != settings.CAM_WIDTH or frame.shape[0] != settings.CAM_HEIGHT:
                    frame = cv2.resize(frame, (settings.CAM_WIDTH, settings.CAM_HEIGHT))

                with self._lock:
                    self._frame = frame

                # Atualizar FPS usando o FPSMeter existente
                self.fps_meter.tick()
                self._propagate_metrics(now)

            except cv2.error as e:
                logger.error(f"❌ {self.name}: OpenCV error: {e}")
                consecutive_errors += 1
                gc.collect()
                time.sleep(0.2)

                if consecutive_errors >= max_errors:
                    logger.critical(f"🧨 {self.name}: Camera worker aborted due to memory errors")
                    self.running = False
                    break

            except Exception as e:
                logger.exception(f"❌ {self.name}: Unexpected error in capture loop: {e}")
                self.running = False
                break


    def _propagate_metrics(self, timestamp: float) -> None:
        """
        Propaga métricas de FPS para o CameraContext a cada 1 segundo.
        """
        if timestamp - self.last_metrics_update >= 1.0:
            self.last_metrics_update = timestamp
            if self.metrics_callback:
                metrics = self.fps_meter.snapshot()
                self.metrics_callback(
                    {
                        "fps_current": metrics["current_fps"],
                        "fps_avg": metrics["avg_fps"],
                    }
                )


    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame is None:
                return None
            return np.ascontiguousarray(self._frame)

    def encode_mjpeg(self, frame: Any) -> Optional[bytes]:
        try:
            ret, jpeg = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY]
            )
            if not ret:
                logger.warning(f"⚠️ {self.name}: JPEG encode failed")
                return None
            return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        except Exception as e:
            logger.error(f"❌ {self.name}: MJPEG encode error: {e}")
            return None

    @property
    def is_running(self) -> bool:
        return self.running

    @property
    def has_frame(self) -> bool:
        with self._lock:
            return self._frame is not None
