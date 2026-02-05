"""
Entidades de domínio do Ark Vision v3.0
Imutáveis, versionadas, sem dependências externas.
"""

from .zones import Zone, ZoneConfig, ZoneMode, ZoneEvent
from .detection import Detection, BoundingBox
from .camera import Camera, CameraConfig

__all__ = [
    "Zone",
    "ZoneConfig",
    "ZoneMode",
    "ZoneEvent",
    "Detection",
    "BoundingBox",
    "Camera",
    "CameraConfig",
]
