# ===================================================================
# backend/services/inference_worker.py
# INFERENCE WORKER v4.9 - DETECÇÃO SIMPLES
# ===================================================================

import cv2
import threading
import logging
import numpy as np
from ultralytics import YOLO
from config import settings

logger = logging.getLogger("inference_worker")


class InferenceWorker:
    """
    InferenceWorker v4.9
    ✅ DETECÇÃO SIMPLES (sem tracking nativo)
    ✅ COM FILTRO DE CLASSES
    """

    def __init__(self):
        self.device = 0 if settings.USE_GPU else "cpu"
        self.model = YOLO(settings.YOLO_MODEL_PATH)
        self._lock = threading.Lock()
        self._started = False
        
        self.classes = settings.YOLO_CLASSES
        
        if self.classes:
            class_names = ', '.join(settings.yolo_classes_names)
            logger.info(f"🧠 YOLO model loaded - Filtering classes: {class_names}")
        else:
            logger.info("🧠 YOLO model loaded - Detecting ALL 80 COCO classes")

    def start(self):
        if self._started:
            return

        try:
            dummy = np.zeros(
                (settings.CAM_HEIGHT, settings.CAM_WIDTH, 3),
                dtype=np.uint8
            )

            with self._lock:
                # ✅ DETECÇÃO SIMPLES (SEM TRACKING)
                self.model(
                    dummy,
                    conf=settings.YOLO_CONF_THRESHOLD,
                    device=self.device,
                    classes=self.classes,
                    verbose=False
                )

            self._started = True
            logger.info("🔥 YOLO warm-up completed")

        except Exception as e:
            logger.error(f"❌ YOLO warm-up failed: {e}")
            raise

    def stop(self):
        self._started = False
        logger.info("🧠 YOLO worker stopped")

    def run(self, frame):
        """
        ✅ DETECÇÃO SIMPLES (retorna apenas boxes)
        """
        if frame is None:
            return None

        if not self._started:
            self.start()

        with self._lock:
            # ✅ DETECÇÃO SIMPLES
            results = self.model(
                frame,
                conf=settings.YOLO_CONF_THRESHOLD,
                device=self.device,
                classes=self.classes,
                verbose=False
            )

        return results

    def encode_jpeg(self, frame) -> bytes:
        ret, jpeg = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY],
        )
        
        if not ret:
            return b""

        return (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg.tobytes()
            + b"\r\n"
        )
