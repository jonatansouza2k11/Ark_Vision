"""
Renderizador de zonas
Responsabilidade: Desenhar overlays de zona em frames (OpenCV)
"""
from typing import Dict, Tuple, Set, Optional
import numpy as np
import cv2
import logging

from backend.core.domain.entities import Zone

from .color_utils import ColorUtils

logger = logging.getLogger(__name__)


class ZoneRenderer:
    """
    Renderiza zonas em frames (OpenCV).
    
    Responsabilidade: UI/Visualização (separado de lógica)
    """
    
    def __init__(self):
        self.color_utils = ColorUtils()
    
    def draw_zones(
        self,
        frame: np.ndarray,
        zones: list[Zone],
        track_state: Optional[Dict[int, Dict]] = None
    ) -> np.ndarray:
        """
        Desenha overlays de zonas em frame.
        
        Args:
            frame: Frame BGR (np.ndarray)
            zones: Lista de Zone entities
            track_state: {track_id: {"bbox": [...], "class_id": int}} (opcional)
        
        Returns:
            Frame com overlays desenhados
        """
        if frame is None or not zones:
            return frame
        
        h, w = frame.shape[:2]
        
        for zone in zones:
            if not zone.config.enabled:
                continue
            
            # Converter pontos para pixels
            polygon = zone.config.polygon
            is_normalized = all(0 <= p[0] <= 1 and 0 <= p[1] <= 1 for p in polygon)
            
            if is_normalized:
                points = np.array(
                    [[int(p[0] * w), int(p[1] * h)] for p in polygon],
                    dtype=np.int32
                )
            else:
                points = np.array(polygon, dtype=np.int32)
            
            # Cor da zona
            color = self.color_utils.hex_to_bgr(zone.config.color)
            
            # Desenhar polígono
            cv2.polylines(frame, [points], True, color, 2)
            
            # Preenchimento translúcido
            try:
                overlay = frame.copy() #Tenta alocar overlay (pode falhar se RAM baixa)
            except np.core._exceptions._ArrayMemoryError:
                    logger.error(
                        "ZoneRenderer: MemoryError em frame.copy(); desenhando sem overlay neste frame."
                    )
            #overlay = frame  # desenha direto (sem transparência)

            cv2.fillPoly(overlay, [points], color)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            
            # Desenhar bounding boxes dos objetos
            if track_state:
                self._draw_tracked_objects(
                    frame, zone, track_state, color
                )
            
            # Textos informativos
            self._draw_zone_info(frame, zone, points)
        
        return frame
    
    def _draw_tracked_objects(
        self,
        frame: np.ndarray,
        zone: Zone,
        track_state: Dict[int, Dict],
        zone_color: Tuple[int, int, int]
    ):
        """Desenha bounding boxes dos objetos rastreados na zona"""
        allowed_classes = set(zone.config.metadata.get("detection_classes", []))
        
        for obj_id in zone.state.objects_inside:
            if obj_id not in track_state:
                continue
            
            obj_data = track_state[obj_id]
            bbox = obj_data.get("bbox")
            class_id = obj_data.get("class_id", -1)
            confidence = obj_data.get("confidence", 0.0)
            
            if not bbox or len(bbox) < 4:
                continue
            
            # Filtrar por classe (se configurado)
            if allowed_classes and class_id not in allowed_classes:
                continue
            
            # Desenhar bbox
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), zone_color, 2)
            
            # Label com classe e confiança
            try:
                from backend.adapters.vision.coco_classes import COCO_CLASSES
                class_name = COCO_CLASSES.get(class_id, f"class_{class_id}")
            except:
                class_name = f"class_{class_id}"
            
            label = f"{class_name} {confidence:.2f}"
            
            # Background do label
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            
            label_y1 = max(y1 - label_h - 10, label_h + 10)
            label_y2 = label_y1 + label_h + 10
            
            cv2.rectangle(
                frame,
                (x1, label_y1),
                (x1 + label_w + 10, label_y2),
                zone_color,
                -1
            )
            
            # Texto do label
            cv2.putText(
                frame,
                label,
                (x1 + 5, label_y2 - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )
    
    def _draw_zone_info(
        self,
        frame: np.ndarray,
        zone: Zone,
        points: np.ndarray
    ):
        """Desenha informações da zona (nome, contagem, status)"""
        # Centro do polígono
        c = points.mean(axis=0).astype(int)
        
        # 1. Nome da zona
        self._draw_text_with_outline(
            frame,
            zone.config.name,
            (c[0] - 60, c[1] - 40),
            cv2.FONT_HERSHEY_DUPLEX,
            0.45,
            (255, 255, 255),
            1
        )
        
        # 2. Contagem
        if zone.config.mode.value == "capacity":
            max_cap = zone.config.metadata.get("max_capacity", "?")
            count_text = f"{zone.state.object_count}/{max_cap}"
        else:
            count_text = f"{zone.state.object_count}"
        
        self._draw_text_with_outline(
            frame,
            count_text,
            (c[0] - 25, c[1] + 10),
            cv2.FONT_HERSHEY_DUPLEX,
            0.9,
            (255, 255, 255),
            2
        )
        
        # 3. Status
        status_labels = {
            "NORMAL": "OK",
            "WARNING": "AVISO",
            "CRITICAL": "ALERTA",
            "EMPTY": "VAZIO",
            "OCCUPIED": "OCUPADO",
            "FULL": "CHEIO",
            "ALERT": "ALERTA",
            "PENDING": "PENDENTE",
            "EMPTY_PENDING": "VAZIO (aguardando)",
            "FULL_PENDING": "CHEIO (aguardando)",
            "COUNTING": "CONTANDO",
            "TRACKING": "RASTREANDO",
            "IDLE": "INATIVO",
        }
        
        status_text = status_labels.get(zone.state.status, zone.state.status)
        
        self._draw_text_with_outline(
            frame,
            status_text,
            (c[0] - 35, c[1] + 35),
            cv2.FONT_HERSHEY_DUPLEX,
            0.35,
            (255, 255, 255),
            1
        )
    
    @staticmethod
    def _draw_text_with_outline(
        img: np.ndarray,
        text: str,
        pos: Tuple[int, int],
        font: int,
        scale: float,
        color: Tuple[int, int, int],
        thickness: int,
        outline_color: Tuple[int, int, int] = (0, 0, 0),
        outline_thickness: int = 3
    ):
        """Desenha texto com outline (contraste)"""
        # Outline (contorno preto)
        cv2.putText(img, text, pos, font, scale, outline_color, outline_thickness, cv2.LINE_AA)
        # Texto principal
        cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)
