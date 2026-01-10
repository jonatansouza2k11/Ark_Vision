import threading
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("tracking_worker")


class TrackingWorker:
    """
    TrackingWorker
    -------------------------------------------------------------
    Responsável por manter estado de tracking entre frames.
    Implementação leve, thread-safe e extensível.
    """

    def __init__(self):
        self.state: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

        # TTL simples para objetos desaparecidos (segundos)
        self._ttl_seconds = 2.0

        logger.info("🧭 TrackingWorker initialized")

    # ============================================================
    # LIFECYCLE
    # ============================================================
    def start(self):
        logger.info("🧭 TrackingWorker started")

    def stop(self):
        with self._lock:
            self.state.clear()
        logger.info("🧭 TrackingWorker stopped")

    # ============================================================
    # TRACKING CORE
    # ============================================================
    def update(self, detections):
        """
        Atualiza estado de tracking com base nas detecções YOLO.
        Mantém contrato simples esperado pela API:
        {
            id: {
                "status": "IN" | "OUT",
                "last_seen": timestamp
            }
        }
        """
        now = time.time()

        if detections is None:
            return self.state

        with self._lock:
            # ------------------------------------------------------
            # Processa detecções YOLO (forma genérica)
            # ------------------------------------------------------
            try:
                for result in detections:
                    if not hasattr(result, "boxes"):
                        continue

                    for box in result.boxes:
                        # ID sintético simples (hash estável)
                        track_id = hash(box.xyxy[0].tolist()) % 10_000_000

                        self.state[track_id] = {
                            "status": "IN",
                            "last_seen": now
                        }

            except Exception as e:
                logger.error(f"❌ Tracking update error: {e}")

            # ------------------------------------------------------
            # Aging / cleanup
            # ------------------------------------------------------
            if now - self._last_cleanup > 1.0:
                expired = [
                    tid for tid, data in self.state.items()
                    if now - data["last_seen"] > self._ttl_seconds
                ]

                for tid in expired:
                    self.state[tid]["status"] = "OUT"

                self._last_cleanup = now

            # Retorna snapshot seguro
            return dict(self.state)
