# ===================================================================
# backend/services/metrics.py
# FINAL v4.7
# - FPSMeter thread-safe
# - Mantém API existente
# - Compatível com VisionSystem e múltiplos workers
# ===================================================================

import time
from collections import deque
import threading


class FPSMeter:
    """
    High-performance FPS calculator.
    Thread-safe, mantém média móvel de FPS.
    Compatível com múltiplos workers e pipeline industrial.
    """
    def __init__(self, window: int = 50):
        self.window = window
        self.timestamps = deque(maxlen=window)
        self._lock = threading.Lock()
        self.current_fps: float = 0.0
        self.avg_fps: float = 0.0

    def tick(self) -> float:
        """
        Registrar um novo frame e atualizar FPS atual e médio.
        """
        now = time.time()
        with self._lock:
            self.timestamps.append(now)
            if len(self.timestamps) > 1:
                delta = now - self.timestamps[-2]
                self.current_fps = 1.0 / delta if delta > 0 else 0.0
            if len(self.timestamps) > 2:
                total = self.timestamps[-1] - self.timestamps[0]
                self.avg_fps = (len(self.timestamps) - 1) / total if total > 0 else 0.0
            return self.current_fps

    def average(self) -> float:
        """
        Retorna FPS médio da janela.
        """
        with self._lock:
            return self.avg_fps

    def reset(self) -> None:
        """
        Limpa histórico de timestamps e reseta métricas.
        """
        with self._lock:
            self.timestamps.clear()
            self.current_fps = 0.0
            self.avg_fps = 0.0
