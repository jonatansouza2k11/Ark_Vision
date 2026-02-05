"""
Geometry utilities for zone processing.
Reuses infrastructure/geometry/polygon_engine.py to avoid duplication.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from infrastructure.geometry.polygon_engine import PolygonEngine

logger = logging.getLogger(__name__)


# Cache global para polígonos (reutilizado entre frames)
_POLYGON_CACHE: Dict[int, np.ndarray] = {}


def point_in_polygon(
    point: Tuple[float, float],
    polygon: List[List[float]],
    frame_size: Tuple[int, int],
) -> bool:
    """
    Verifica se um ponto está dentro de um polígono usando ray-casting.
    
    Args:
        point: (x, y) coordenadas do ponto
        polygon: Lista de pontos [[x1, y1], [x2, y2], ...]
        frame_size: (height, width) do frame para normalização
    
    Returns:
        True se o ponto está dentro do polígono
    """
    return PolygonEngine.point_in_polygon(point, polygon, frame_size)


def get_zone_polygon(zone: Dict, use_cache: bool = True) -> Optional[np.ndarray]:
    """
    Obtém polígono da zona com cache opcional.
    
    Args:
        zone: Dicionário com dados da zona (deve ter 'id' e 'points')
        use_cache: Se True, usa cache para evitar reprocessamento
    
    Returns:
        np.ndarray com shape (N, 2) ou None se inválido
    """
    zone_id = zone.get("id")
    if not zone_id:
        logger.warning("Zone without ID, cannot cache polygon")
        return None
    
    # Verificar cache
    if use_cache and zone_id in _POLYGON_CACHE:
        return _POLYGON_CACHE[zone_id]
    
    # Extrair pontos
    points = zone.get("points", [])
    if not points or len(points) < 3:
        logger.warning(f"Zone {zone.get('name')} has invalid points (< 3)")
        return None
    
    try:
        # Converter pontos para formato numpy
        coords = []
        for p in points:
            if isinstance(p, dict):
                x, y = p.get("x"), p.get("y")
                if x is not None and y is not None:
                    coords.append([float(x), float(y)])
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                coords.append([float(p[0]), float(p[1])])
        
        if len(coords) < 3:
            return None
        
        polygon = np.array(coords, dtype=np.int32)
        
        # Salvar no cache
        if use_cache:
            _POLYGON_CACHE[zone_id] = polygon
        
        return polygon
    
    except Exception as e:
        logger.error(f"Error creating polygon for zone {zone.get('name')}: {e}")
        return None


def get_objects_in_zone(
    detections: List[Dict],
    zone_points: np.ndarray,
    frame_shape: Tuple[int, int, int],
    allowed_classes: Optional[Set[int]] = None,
) -> Tuple[Set[int], int]:
    """
    Filtra objetos que estão dentro da zona.
    
    Args:
        detections: Lista de detecções YOLO com trackId, bbox, classId
        zone_points: Polígono da zona (np.ndarray)
        frame_shape: Shape do frame (height, width, channels)
        allowed_classes: Set de class_ids permitidos (None = todos)
    
    Returns:
        (objects_inside, filtered_count) - IDs dos objetos dentro e contagem de filtrados
    """
    h, w = frame_shape[:2]
    objects_inside = set()
    filtered_count = 0
    
    for obj_data in detections:
        track_id = obj_data.get("trackId")
        if track_id is None:
            continue
        
        # Filtro de classe (se configurado)
        obj_class_id = obj_data.get("classId")
        if allowed_classes is not None:
            if obj_class_id not in allowed_classes:
                filtered_count += 1
                continue
        
        # Validar bbox
        bbox = obj_data.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        
        # Calcular centróide
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        # Verificar se centróide está dentro do polígono
        if PolygonEngine.point_in_polygon((cx, cy), zone_points, (h, w)):
            objects_inside.add(track_id)
    
    return objects_inside, filtered_count


def bbox_intersects_polygon(bbox: Tuple, polygon: np.ndarray) -> bool:
    """
    Verifica se bbox intersecta polígono (usado em intrusion/loitering).
    
    Args:
        bbox: (x1, y1, x2, y2) bounding box
        polygon: Polígono da zona
    
    Returns:
        True se houver interseção
    """
    try:
        import cv2
        
        x1, y1, x2, y2 = bbox
        
        # Verificar se algum canto da bbox está dentro do polígono
        bbox_points = np.array([
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2]
        ], dtype=np.float32)
        
        for point in bbox_points:
            if cv2.pointPolygonTest(polygon, tuple(point), False) >= 0:
                return True
        
        # Verificar se algum ponto do polígono está dentro da bbox
        for point in polygon:
            px, py = float(point[0]), float(point[1])
            if x1 <= px <= x2 and y1 <= py <= y2:
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking bbox intersection: {e}")
        return False


def calculate_bbox_intersection_ratio(bbox: tuple, polygon: np.ndarray) -> float:
    """
    Calcula porcentagem da bbox que está dentro do polígono.
    Usado em counting mode para validar área de interseção.
    
    Estratégia: Grid sampling (9x9) - rápido e robusto.
    
    Args:
        bbox: (x1, y1, x2, y2)
        polygon: Polígono da zona
    
    Returns:
        float 0.0 a 1.0 (0% a 100%)
    """
    try:
        import cv2
        
        x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        
        if bbox_width <= 0 or bbox_height <= 0:
            return 0.0
        
        # Grid 9x9 = 81 pontos de amostragem
        grid_size = 9
        points_inside = 0
        total_points = 0
        
        for i in range(grid_size):
            for j in range(grid_size):
                ratio_x = i / (grid_size - 1)
                ratio_y = j / (grid_size - 1)
                
                px = x1 + ratio_x * bbox_width
                py = y1 + ratio_y * bbox_height
                
                if cv2.pointPolygonTest(polygon, (px, py), False) >= 0:
                    points_inside += 1
                
                total_points += 1
        
        ratio = points_inside / total_points if total_points > 0 else 0.0
        return ratio
    
    except Exception as e:
        logger.error(f"Error calculating intersection ratio: {e}", exc_info=True)
        return 0.0


def clear_polygon_cache():
    """Limpa cache de polígonos (útil para testes ou reload de configuração)."""
    global _POLYGON_CACHE
    _POLYGON_CACHE.clear()
    logger.debug("Polygon cache cleared")
