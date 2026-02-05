"""
Motor de polígonos com OpenCV
Responsabilidade: Operações geométricas avançadas (interseção, cache)
"""
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


class PolygonEngine:
    """
    Engine de polígonos otimizado com cache.
    
    Usa OpenCV para operações geométricas complexas.
    Cache evita reconstrução de polígonos a cada frame.
    """
    
    def __init__(self):
        self._polygon_cache: Dict[int, np.ndarray] = {}
    
    def get_polygon(
        self,
        zone_id: int,
        points: List[Tuple[int, int]],
        force_rebuild: bool = False
    ) -> Optional[np.ndarray]:
        """
        Obtém polígono com cache.
        
        Args:
            zone_id: ID da zona (chave do cache)
            points: Lista de (x, y)
            force_rebuild: Força reconstrução (ignore cache)
        
        Returns:
            np.ndarray [[x, y], ...] ou None se inválido
        """
        # Cache hit
        if not force_rebuild and zone_id in self._polygon_cache:
            return self._polygon_cache[zone_id]
        
        # Validação
        if not points or len(points) < 3:
            logger.warning(f"Polygon {zone_id}: menos de 3 pontos")
            return None
        
        try:
            # Construir polígono
            coords = []
            for p in points:
                if isinstance(p, dict):
                    x, y = p.get("x"), p.get("y")
                    if x is not None and y is not None:
                        coords.append([float(x), float(y)])
                elif isinstance(p, (list, tuple)) and len(p) >= 2:
                    coords.append([float(p[0]), float(p[1])])
            
            if len(coords) < 3:
                logger.warning(f"Polygon {zone_id}: coordenadas inválidas")
                return None
            
            polygon = np.array(coords, dtype=np.int32)
            
            # Salvar no cache
            self._polygon_cache[zone_id] = polygon
            
            return polygon
        
        except Exception as e:
            logger.error(f"❌ Erro ao criar polígono {zone_id}: {e}")
            return None
    
    def calculate_bbox_intersection_ratio(
        self,
        bbox: Tuple[float, float, float, float],
        polygon: np.ndarray,
        grid_size: int = 9
    ) -> float:
        """
        Calcula porcentagem da bbox que está dentro do polígono.
        
        Estratégia: Grid sampling (robusto e rápido).
        
        Args:
            bbox: (x1, y1, x2, y2)
            polygon: np.ndarray [[x, y], ...]
            grid_size: Resolução do grid (9 = 81 pontos)
        
        Returns:
            float: 0.0 a 1.0 (0% a 100%)
        """
        try:
            x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            
            if bbox_width <= 0 or bbox_height <= 0:
                return 0.0
            
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
            logger.error(f"❌ Erro ao calcular interseção: {e}")
            return 0.0
    
    def bbox_intersects_polygon(
        self,
        bbox: Tuple[float, float, float, float],
        polygon: np.ndarray
    ) -> bool:
        """
        Verifica se bbox intersecta polígono (qualquer parte).
        
        Args:
            bbox: (x1, y1, x2, y2)
            polygon: np.ndarray [[x, y], ...]
        
        Returns:
            bool: True se houver interseção
        """
        try:
            x1, y1, x2, y2 = bbox
            
            # Testar cantos da bbox
            bbox_points = np.array([
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ], dtype=np.float32)
            
            for point in bbox_points:
                if cv2.pointPolygonTest(polygon, tuple(point), False) >= 0:
                    return True
            
            # Testar se algum vértice do polígono está dentro da bbox
            for point in polygon:
                px, py = float(point[0]), float(point[1])
                if x1 <= px <= x2 and y1 <= py <= y2:
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao verificar interseção bbox: {e}")
            return False
    
    def clear_cache(self, zone_id: Optional[int] = None):
        """
        Limpa cache de polígonos.
        
        Args:
            zone_id: ID específico (None = limpar tudo)
        """
        if zone_id is None:
            self._polygon_cache.clear()
            logger.info("🗑️ Cache de polígonos limpo")
        elif zone_id in self._polygon_cache:
            del self._polygon_cache[zone_id]
            logger.debug(f"🗑️ Cache de polígono {zone_id} removido")
