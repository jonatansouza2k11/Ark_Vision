# ===================================================================
# backend/yolo.py
# YOLO / VisionSystem Facade
# - Singleton global do VisionSystem
# - Ponto único de acesso em toda a API
# - Evita múltiplas cargas de modelo e câmeras duplicadas
# ===================================================================

from typing import Optional
from backend.services.vision_system import VisionSystem

# Instância global única
_vision_system: Optional[VisionSystem] = None


def get_vision_system() -> VisionSystem:
    """
    Retorna a instância singleton do VisionSystem.

    Responsabilidades:
    - Garantir que apenas UMA instância do pipeline exista
    - Centralizar acesso ao sistema de visão
    - Evitar múltiplas cargas de YOLO, câmeras duplicadas, threads redundantes

    Uso típico em routers / services:
        from backend.yolo import get_vision_system

        vs = get_vision_system()
        vs.start_live()
    """
    global _vision_system

    if _vision_system is None:
        _vision_system = VisionSystem()

    return _vision_system


def reset_vision_system() -> None:
    """
    Força recriação do VisionSystem.
    Útil para:
    - Reload de configuração
    - Troca dinâmica de câmeras
    - Ambientes de teste
    """
    global _vision_system

    if _vision_system:
        try:
            _vision_system.stop_live()
        except Exception:
            pass

    _vision_system = VisionSystem()
