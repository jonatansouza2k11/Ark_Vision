# ===================================================================
# backend/services/inference_worker.py
# InferenceWorker v6.1 - GPU-Safe Governed Lifecycle (Industrial Grade)
# ===================================================================

import threading
import logging
import gc
import numpy as np
import torch
from ultralytics import YOLO
from backend.config import settings

logger = logging.getLogger("inference_worker")


class InferenceWorker:
    """
    Motor de inferência YOLO.

    Garantias:
    - Thread-safe
    - Warm-up único por processo
    - Idempotente
    - Sem reentrada CUDA
    - Governança por ciclo lógico, não por frame
    - Fallback automático GPU → CPU
    """

    def __init__(self):
        self.device = (
            0 if settings.USE_GPU and torch.cuda.is_available() else "cpu"
        )

        self._lock = threading.Lock()
        self._started = False
        self._warmed = False

        self.model = YOLO(settings.YOLO_MODEL_PATH, task="detect")

        logger.info(f"🧠 YOLO model loaded (device={self.device})")

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    def start(self) -> None:
        with self._lock:
            if self._started:
                return

            if not self._warmed:
                try:
                    dummy = np.zeros(
                        (settings.CAM_HEIGHT, settings.CAM_WIDTH, 3),
                        dtype=np.uint8,
                    )

                    self.model(
                        dummy,
                        conf=settings.YOLO_CONF_THRESHOLD,
                        device=self.device,
                        verbose=False,
                    )

                    self._warmed = True
                    logger.info(f"🔥 YOLO warm-up completed on {self.device}")

                except Exception as e:
                    logger.error(f"❌ YOLO warm-up failed on {self.device}: {e}")

                    # Fallback automático
                    if self.device != "cpu":
                        logger.warning("🔄 Falling back to CPU")
                        self.device = "cpu"

                        self.model(
                            dummy,
                            conf=settings.YOLO_CONF_THRESHOLD,
                            device="cpu",
                            verbose=False,
                        )

                        self._warmed = True
                        logger.info("🔥 YOLO warm-up completed on CPU")
                    else:
                        raise

                finally:
                    del dummy
                    self._post_cycle_cleanup()

            self._started = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return

            self._started = False
            self._post_cycle_cleanup()
            logger.info("🧠 InferenceWorker stopped (logical cycle)")

    def _post_cycle_cleanup(self):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    # ==================================================================
    # INFERENCE
    # ==================================================================

    def run(self, frame):
        if frame is None:
            return None

        if not self._started:
            self.start()

        with self._lock:
            try:
                return self.model(
                    frame,
                    conf=settings.YOLO_CONF_THRESHOLD,      
                    iou=settings.YOLO_IOU_THRESHOLD,        
                    imgsz=settings.YOLO_IMG_SIZE,           
                    max_det=settings.YOLO_MAX_DETECTIONS,   
                    device=self.device,
                    verbose=False,
                )
            except Exception as e:
                logger.error(f"❌ Inference failure on {self.device}: {e}")

                # Invalida apenas o ciclo lógico
                self._started = False
                self._post_cycle_cleanup()

                # Tentar CPU automaticamente
                if self.device != "cpu":
                    logger.warning("🔄 Switching to CPU after inference failure")
                    self.device = "cpu"
                    return self.run(frame)

                raise
