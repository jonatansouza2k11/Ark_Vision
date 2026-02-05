# ===================================================================
# backend/yolo.py
# YOLO / VisionSystem Facade (Governed Singleton)
# ===================================================================

from typing import Optional
import threading
from backend.runtime.orchestration.vision_system import VisionSystem

# Instância global única
_vision_system: Optional[VisionSystem] = None
_lock = threading.Lock()


def get_vision_system() -> VisionSystem:
    """
    Retorna a instância singleton do VisionSystem.

    Garantias:
    - Thread-safe
    - Uma única instância global
    - Nenhuma duplicação de YOLO, câmeras ou threads
    """
    global _vision_system

    if _vision_system is None:
        with _lock:
            if _vision_system is None:  # double-checked locking
                _vision_system = VisionSystem()

    return _vision_system


def reset_vision_system() -> None:
    """
    Força recriação do VisionSystem.

    Uso controlado para:
    - Reload de configuração
    - Troca dinâmica de câmeras
    - Ambientes de teste
    """
    global _vision_system

    with _lock:
        if _vision_system:
            try:
                _vision_system.stop_live()
            except Exception:
                pass

        _vision_system = VisionSystem()
