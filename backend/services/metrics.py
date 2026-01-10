# ===================================================================
# backend/services/metrics.py
# FPSMeter v5.0
# -------------------------------------------------------------------
# Responsabilidade:
# - Medir FPS instantâneo
# - Calcular média móvel
# - Ser thread-safe
#
# NÃO FAZ:
# - Stream
# - Inferência
# - Tracking
# - Regras de negócio
# ===================================================================

import time
import threading
from collections import deque


class FPSMeter:
    """
    FPSMeter
    ------------------------------------------------------------------
    Medidor de FPS de alto desempenho.
    Projetado para pipelines industriais com múltiplos workers.
    """

    def __init__(self, window: int = 60):
        self.window = max(2, int(window))
        self.timestamps = deque(maxlen=self.window)
        self._lock = threading.Lock()

        self.current_fps: float = 0.0
        self.avg_fps: float = 0.0

    # ==================================================================
    # CORE
    # ==================================================================

    def tick(self) -> float:
        """
        Registra um novo frame processado.
        Atualiza FPS atual e médio.
        Retorna FPS instantâneo.
        """
        now = time.perf_counter()

        with self._lock:
            self.timestamps.append(now)

            if len(self.timestamps) >= 2:
                delta = self.timestamps[-1] - self.timestamps[-2]
                self.current_fps = 1.0 / delta if delta > 0 else 0.0

            if len(self.timestamps) >= 3:
                total = self.timestamps[-1] - self.timestamps[0]
                self.avg_fps = (len(self.timestamps) - 1) / total if total > 0 else 0.0

            return self.current_fps

    def average(self) -> float:
        """
        Retorna FPS médio da janela.
        """
        with self._lock:
            return float(self.avg_fps)

    def snapshot(self) -> dict:
        """
        Retorna métricas prontas para API / observabilidade.
        """
        with self._lock:
            return {
                "current_fps": round(self.current_fps, 2),
                "avg_fps": round(self.avg_fps, 2),
                "window": self.window,
            }

    def reset(self) -> None:
        """
        Reseta completamente o histórico.
        """
        with self._lock:
            self.timestamps.clear()
            self.current_fps = 0.0
            self.avg_fps = 0.0
