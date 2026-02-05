"""
Operações geométricas puras (sem dependências externas).

Versão: 1.0
Performance: Otimizado para 30 FPS com 20+ objetos
"""
from typing import List, Tuple, Set, Dict

class GeometryService:
    """Serviço de geometria 2D para zonas"""
    
    @staticmethod
    def point_in_polygon(
        point: Tuple[float, float],
        polygon: List[Tuple[int, int]],
        frame_size: Tuple[int, int]
    ) -> bool:
        """
        Ray-casting algorithm para point-in-polygon test.
        
        Suporta coordenadas normalizadas (0-1) e absolutas (pixels).
        
        Args:
            point: (x, y) em pixels
            polygon: Lista de (x, y) vértices
            frame_size: (height, width) do frame
        
        Returns:
            True se ponto está dentro do polígono
        """
        x, y = point
        h, w = frame_size
        
        # Detectar se coordenadas são normalizadas
        is_normalized = all(0 <= p[0] <= 1 and 0 <= p[1] <= 1 for p in polygon)
        
        if is_normalized:
            poly = [(p[0] * w, p[1] * h) for p in polygon]
        else:
            poly = polygon
        
        inside = False
        n = len(poly)
        p1x, p1y = poly[0]
        
        for i in range(1, n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    @staticmethod
    def bbox_center(bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """
        Retorna centro do bbox.
        
        Args:
            bbox: (x1, y1, x2, y2) em pixels
        
        Returns:
            (cx, cy) centro em pixels
        """
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    @staticmethod
    def bbox_iou(
        box1: Tuple[int, int, int, int],
        box2: Tuple[int, int, int, int]
    ) -> float:
        """
        Calcula IoU (Intersection over Union) entre dois bboxes.
        
        Args:
            box1: (x1, y1, x2, y2)
            box2: (x1, y1, x2, y2)
        
        Returns:
            float: IoU (0.0 a 1.0)
        """
        x1_max = max(box1[0], box2[0])
        y1_max = max(box1[1], box2[1])
        x2_min = min(box1[2], box2[2])
        y2_min = min(box1[3], box2[3])
        
        inter_w = max(0, x2_min - x1_max)
        inter_h = max(0, y2_min - y1_max)
        inter_area = inter_w * inter_h
        
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    @staticmethod
    def objects_in_zone(
        zone_polygon: List[Tuple[int, int]],
        track_state: Dict[int, Dict],
        frame_size: Tuple[int, int],
        allowed_classes: Set[int] | None = None
    ) -> Set[int]:
        """
        Encontra objetos rastreados dentro de zona (otimizado).
        
        Args:
            zone_polygon: Polígono da zona
            track_state: {track_id: {"bbox": [x1,y1,x2,y2], "class_id": int}}
            frame_size: (height, width)
            allowed_classes: Classes permitidas (None = todas)
        
        Returns:
            Set de track_ids dentro da zona
        """
        objects_inside = set()
        
        for track_id, obj_data in track_state.items():
            if "bbox" not in obj_data:
                continue
            
            # Filtro de classe (se configurado)
            if allowed_classes is not None:
                class_id = obj_data.get("class_id", 0)
                if class_id not in allowed_classes:
                    continue
            
            # Teste de geometria (centro do bbox)
            bbox = obj_data["bbox"]
            cx, cy = GeometryService.bbox_center(bbox)
            
            if GeometryService.point_in_polygon((cx, cy), zone_polygon, frame_size):
                objects_inside.add(track_id)
        
        return objects_inside
