"""Entidades de câmera v1.0"""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class CameraConfig:
    """Configuração imutável de câmera (origem: DB)"""
    camera_id: int
    name: str
    source: str | int  # URL RTSP ou índice webcam (0, 1, ...)
    location: str
    enabled: bool
    fps_target: float = 30.0
    resolution: Tuple[int, int] = (1920, 1080)

@dataclass
class Camera:
    """Estado runtime de câmera (mutável)"""
    config: CameraConfig
    is_running: bool = False
    current_fps: float = 0.0
    frame_count: int = 0
    last_frame_timestamp: float = 0.0
