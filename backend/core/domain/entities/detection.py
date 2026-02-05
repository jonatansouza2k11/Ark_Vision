"""Entidades de detecção YOLO v1.0"""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class BoundingBox:
    """Bounding box normalizada (0-1)"""
    x1: float
    y1: float
    x2: float
    y2: float
    
    def to_absolute(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """Converte para coordenadas absolutas (pixels)"""
        return (
            int(self.x1 * width),
            int(self.y1 * height),
            int(self.x2 * width),
            int(self.y2 * height),
        )
    
    def center(self) -> Tuple[float, float]:
        """Retorna centro normalizado (0-1)"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def center_absolute(self, width: int, height: int) -> Tuple[int, int]:
        """Retorna centro em pixels"""
        cx, cy = self.center()
        return (int(cx * width), int(cy * height))
    
    def area(self) -> float:
        """Área normalizada (0-1)"""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

@dataclass(frozen=True)
class Detection:
    """Detecção YOLO pós-NMS"""
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    timestamp: float
