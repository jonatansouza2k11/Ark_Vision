# ===================================================================
# backend/services/inference_worker.py
# InferenceWorker v5.0 - Pure Detection Engine
# -------------------------------------------------------------------
# Responsabilidade:
# - Carregar o modelo YOLO
# - Aquecer o modelo (warm-up)
# - Executar inferência pura
# - Ser thread-safe
#
# NÃO FAZ:
# - Tracking
# - Regras de negócio
# - Filtro por câmera
# - Stream
# - Anotações visuais
# ===================================================================

import threading
import logging
import numpy as np
from ultralytics import YOLO
from config import settings

logger = logging.getLogger("inference_worker")


class InferenceWorker:
    """
    InferenceWorker
    ------------------------------------------------------------------
    Motor de inferência YOLO.

    Características:
    - Thread-safe
    - Warm-up automático
    - Inferência pura
    - Stateless (não mantém contexto)
    """

    def __init__(self):
        self.device = 0 if settings.USE_GPU else "cpu"
        self.model = YOLO(settings.YOLO_MODEL_PATH)

        self._lock = threading.Lock()
        self._started = False

        logger.info("🧠 YOLO model loaded (InferenceWorker)")

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    def start(self) -> None:
        """
        Realiza warm-up do modelo para evitar latência no primeiro frame real.
        """
        if self._started:
            return

        try:
            dummy = np.zeros(
                (settings.CAM_HEIGHT, settings.CAM_WIDTH, 3),
                dtype=np.uint8,
            )

            with self._lock:
                self.model(
                    dummy,
                    conf=settings.YOLO_CONF_THRESHOLD,
                    device=self.device,
                    verbose=False,
                )

            self._started = True
            logger.info("🔥 YOLO warm-up completed")

        except Exception as e:
            logger.error(f"❌ YOLO warm-up failed: {e}")
            raise

    def stop(self) -> None:
        self._started = False
        logger.info("🧠 InferenceWorker stopped")

    # ==================================================================
    # INFERENCE
    # ==================================================================

    def run(self, frame):
        """
        Executa inferência pura em um frame.

        Retorna:
            results (Ultralytics format) ou None
        """
        if frame is None:
            return None

        if not self._started:
            self.start()

        with self._lock:
            results = self.model(
                frame,
                conf=settings.YOLO_CONF_THRESHOLD,
                device=self.device,
                verbose=False,
            )

        return results
