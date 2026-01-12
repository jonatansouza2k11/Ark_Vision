# ===================================================================
# backend/services/inference_worker.py
# InferenceWorker v6.0 - GPU-Safe Governed Lifecycle
# ===================================================================

import threading
import logging
import gc
import numpy as np
import torch
from ultralytics import YOLO
from config import settings

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
    """

    def __init__(self):
        self.device = 0 if settings.USE_GPU else "cpu"
        self.model = YOLO(settings.YOLO_MODEL_PATH)

        self._lock = threading.Lock()
        self._started = False
        self._warmed = False
        self.model = YOLO(settings.YOLO_MODEL_PATH, task="detect")

        logger.info("🧠 YOLO model loaded (InferenceWorker)")

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
                    logger.info("🔥 YOLO warm-up completed (one-time)")

                except Exception as e:
                    logger.error(f"❌ YOLO warm-up failed: {e}")
                    raise
                finally:
                    del dummy
                    gc.collect()

            self._started = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return

            self._started = False
            gc.collect()
            logger.info("🧠 InferenceWorker stopped (logical cycle)")

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
                    device=self.device,
                    verbose=False,
                )
            except Exception:
                # Falha crítica invalida apenas o ciclo lógico
                self._started = False
                gc.collect()
                raise
