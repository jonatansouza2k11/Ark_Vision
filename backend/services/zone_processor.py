"""
============================================================================
backend/services/zone_processor.py v2.0
Zone Processing Engine - Clean Architecture
============================================================================
PRINCIPLES:
- Dependency Injection (zones via constructor, not DB access)
- Pure business logic (no I/O, no database)
- Mode-specific processors (occupancy, capacity, counting, alert, tracking)
- Thread-safe state management
- Performance-optimized geometric operations

RESPONSIBILITIES:
- Process YOLO detections against zone polygons
- Apply mode-specific logic (thresholds, timeouts)
- Update zone state metrics
- Generate alert conditions

DOES NOT:
- Access database (zones injected)
- Perform YOLO inference (receives detections)
- Send alerts (only flags conditions)
============================================================================
"""

import logging
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("zone_processor")


# ============================================================================
# ZONE STATE
# ============================================================================

class ZoneState:
    """
    Runtime state of a zone during processing.
    
    Tracks:
    - Current object count
    - Objects inside (track IDs)
    - Status (EMPTY/OCCUPIED/FULL/ALERT)
    - Timing for threshold logic
    """
    
    def __init__(self, zone_id: int):
        self.zone_id = zone_id
        
        # Current state
        self.object_count: int = 0
        self.objects_inside: List[int] = []
        self.status: str = "EMPTY"
        
        # Timing for alerts
        self.last_alert_time: Optional[datetime] = None
        self.empty_since: Optional[datetime] = None
        self.full_since: Optional[datetime] = None
        
        # Capacity mode
        self.capacity_alert_sent: bool = False


# ============================================================================
# ZONE PROCESSOR
# ============================================================================

class ZoneProcessor:
    """
    Processes detections against zones for a specific camera.
    
    Architecture: Strategy Pattern per zone mode
    Each mode has its own processing logic.
    """
    
    def __init__(self, camera_id: int, zones: List[Dict]):
        """
        Initialize processor with injected zones.
        
        Args:
            camera_id: Camera ID for logging
            zones: List of zone dicts from VisionSystem context
        """
        self.camera_id = camera_id
        self.zones = zones
        self.zone_states: Dict[int, ZoneState] = {}
        self.last_frame_shape: Optional[Tuple[int, int]] = None
        
        # Initialize states
        for zone in zones:
            zone_id = zone.get("id")
            if zone_id:
                self.zone_states[zone_id] = ZoneState(zone_id)        

        logger.info(
            f"✅ ZoneProcessor initialized for camera {camera_id} "
            f"with {len(self.zones)} zones"
        )
    
    def update_zones(self, zones: List[Dict]):
        """
        Update zones when configuration changes.
        
        Args:
            zones: Updated list of zone dicts
        """
        self.zones = zones
        
        # Add new zone states
        for zone in zones:
            zone_id = zone.get("id")
            if zone_id and zone_id not in self.zone_states:
                self.zone_states[zone_id] = ZoneState(zone_id)
        
        # Remove orphaned states
        current_ids = {z.get("id") for z in zones if z.get("id")}
        orphaned = set(self.zone_states.keys()) - current_ids
        for zone_id in orphaned:
            del self.zone_states[zone_id]
    
    def process_frame(
        self,
        detections: List[Dict],
        track_state: Dict,
        frame_shape: Tuple[int, int],
    ) -> Dict[int, Dict]:
        """
        Process detections against all zones.
        
        Args:
            detections: YOLO detection results
            track_state: Current tracking state {track_id: {bbox, ...}}
            frame_shape: (height, width)
        
        Returns:
            Dict of zone metrics: {zone_id: {count, status, alert, ...}}
        """
        if not self.zones:
            return {}
        
        # Update frame shape
        if self.last_frame_shape and self.last_frame_shape != frame_shape:
            logger.warning(
                f"Frame shape changed for camera {self.camera_id}: "
                f"{self.last_frame_shape} → {frame_shape}"
            )
        self.last_frame_shape = frame_shape
        
        zone_metrics = {}
        
        for zone in self.zones:
            zone_id = zone.get("id")
            if not zone_id:
                continue
            
            # Get objects in this zone
            objects_in_zone = self.get_objects_in_zone(zone, track_state, frame_shape)
            
            # Update state
            state = self.zone_states[zone_id]
            state.object_count = len(objects_in_zone)
            state.objects_inside = objects_in_zone
            
            # Apply mode-specific logic
            mode = zone.get("mode", "occupancy").lower()
            
            if mode == "capacity":
                metrics = self._process_capacity_mode(zone, state)
            elif mode == "occupancy":
                metrics = self._process_occupancy_mode(zone, state)
            elif mode == "counting":
                metrics = self._process_counting_mode(zone, state)
            elif mode == "alert":
                metrics = self._process_alert_mode(zone, state)
            elif mode == "tracking":
                metrics = self._process_tracking_mode(zone, state)
            else:
                # Generic/legacy mode
                metrics = self._process_generic_mode(zone, state)
            
            zone_metrics[zone_id] = metrics
        
        return zone_metrics
    
    def get_objects_in_zone(
        self, zone: Dict, track_state: Dict, frame_shape: Tuple[int, int]
    ) -> List[int]:
        """
        Find which tracked objects are inside a zone.
        
        ✅ v3.6: Filtra por classes configuradas em zone.detection_classes
        """
        objects_inside = []
        
        if not self.last_frame_shape:
            return objects_inside
        
        h, w = self.last_frame_shape
        
        # ✅ v3.6: Obter classes permitidas (prioriza zone.detection_classes direto)
        allowed_classes = zone.get("detection_classes")
        
        # Fallback: tentar buscar em metadata se não encontrou direto
        if not allowed_classes:
            zone_metadata = zone.get("metadata", {})
            allowed_classes = zone_metadata.get("detection_classes")
        
        # ⚠️ Se não há classes configuradas, não filtra nada (aceita tudo)
        # Isso evita o warning quando o usuário não quer filtrar por classe
        if not allowed_classes or not isinstance(allowed_classes, list):
            # Sem filtro configurado - processa todos os objetos
            allowed_classes_set = None
        else:
            # Converter para set para lookup O(1)
            allowed_classes_set = set(allowed_classes)
        
        # 🐛 DEBUG: Log classes configuradas (apenas uma vez por zona)
        #zone_id = zone.get("id")
        #if not hasattr(self, '_logged_zone_classes'):
        #    self._logged_zone_classes = set()
        #
        #if zone_id and zone_id not in self._logged_zone_classes:
        #    from backend.coco_classes import get_class_name
        #    try:
        #        class_names = [get_class_name(cid) for cid in allowed_classes]
        #        logger.info(
        #            f"✅ Zone '{zone.get('name')}' (ID: {zone_id}) - "
        #            f"Classes permitidas: {allowed_classes} = ({', '.join(class_names)})"
        #        )
        #    except Exception as e:
        #        logger.warning(f"⚠️ Error getting class names: {e}")
        #        logger.info(
        #            f"✅ Zone '{zone.get('name')}' (ID: {zone_id}) - "
        #            f"Classes permitidas: {allowed_classes}"
        #        )
        #    self._logged_zone_classes.add(zone_id)
        
        zone_points = zone.get("points", [])
        filtered_count = 0  # Contador de objetos filtrados
        detected_but_filtered = []  # Classes detectadas mas filtradas
        
        for obj_id, obj_data in track_state.items():
            if "bbox" not in obj_data:
                continue
            
            # ✅ v3.6: Filtrar por classe ANTES de verificar polígono (performance)
            if allowed_classes_set is not None:  # Só filtra se há filtro configurado
                obj_class_id = obj_data.get("class_id", 0)
                
                if obj_class_id not in allowed_classes_set:
                    filtered_count += 1
                    if obj_class_id not in detected_but_filtered:
                        detected_but_filtered.append(obj_class_id)
                    continue  # ⛔ Objeto de classe não permitida
            
            # Calcular centro do bounding box
            bbox = obj_data["bbox"]
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            # Verificar se centro está dentro do polígono
            if self.point_in_polygon((cx, cy), zone_points, (h, w)):
                objects_inside.append(obj_id)
        
        # 🐛 DEBUG: Log detalhado quando filtrar objetos
        #if filtered_count > 0:
        #    from backend.coco_classes import get_class_name
        #    filtered_names = [get_class_name(cid) for cid in detected_but_filtered]
        #    logger.info(
        #        f"🔍 Zone '{zone.get('name')}': "
        #        f"✅ {len(objects_inside)} aceitos | "
        #        f"⛔ {filtered_count} filtrados (classes: {detected_but_filtered} = {filtered_names})"
        #    )
        
        return objects_inside

    @staticmethod
    def point_in_polygon(
        point: Tuple[float, float],
        polygon: List[List[float]],
        frame_size: Tuple[int, int],
    ) -> bool:
        """
        Ray-casting algorithm for point-in-polygon test.
        Supports normalized [0-1] and absolute pixel coordinates.
        """
        x, y = point
        h, w = frame_size
        
        # Detect if normalized coordinates
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
    

    # ========================================================================
    # MODE-SPECIFIC PROCESSORS
    # ========================================================================
    

    # ========================================================================
    # CAPACIDADE MAXIMA  OK
    # ========================================================================
    def _process_capacity_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Capacity mode: Alert when approaching/exceeding maximum capacity.
        
        ✅ v2.3 FINAL:
        - 100% configurável
        - Timeouts respeitados
        - Logs de entrada E saída
        - Reset correto de timers
        """
        metadata = zone.get("metadata", {})
        max_capacity = metadata.get("max_capacity", 50)
        alert_percentage = metadata.get("alert_percentage", 100)
        count = state.object_count
        now = datetime.now()
        
        alert_threshold = int(max_capacity * (alert_percentage / 100))
        capacity_timeout = zone.get('full_timeout', 10.0)
        
        # Determinar status
        if count >= alert_threshold:
            if state.full_since is None:
                state.full_since = now
            
            elapsed = (now - state.full_since).total_seconds()
            
            if elapsed >= capacity_timeout:
                # ✅ Confirmado
                if count >= max_capacity:
                    new_status = "CRITICAL"
                else:
                    new_status = "WARNING"
                alert = True
            else:
                # ⏳ Aguardando
                new_status = "PENDING"
                alert = False
        else:
            # ✅ MELHORADO: Log ao sair do alerta
            if state.full_since is not None and state.status in ["WARNING", "CRITICAL", "PENDING"]:
                logger.info(
                    f"📉 Zone '{zone['name']}' saiu do alerta: "
                    f"{state.status} → NORMAL ({count}/{max_capacity})"
                )
            
            state.full_since = None
            new_status = "NORMAL"
            alert = False
        
        # Email cooldown
        email_cooldown = zone.get("email_cooldown", 600.0)
        can_alert = True
        
        if alert and state.last_alert_time:
            elapsed = (now - state.last_alert_time).total_seconds()
            can_alert = elapsed >= email_cooldown
        
        if alert and can_alert:
            state.last_alert_time = now
        
        # Log mudanças
        if new_status != state.status:
            logger.info(
                f"📊 Zone '{zone['name']}' (camera {self.camera_id}): "
                f"{state.status} → {new_status} ({count}/{max_capacity} = {round(count/max_capacity*100)}%)"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "capacity",
            "count": count,
            "max_capacity": max_capacity,
            "occupancy_percent": round((count / max_capacity) * 100, 1) if max_capacity > 0 else 0,
            "status": new_status,
            "alert": alert and can_alert,
            "alert_message": f"Capacidade: {count}/{max_capacity} ({round(count/max_capacity*100)}%)" if alert else None,
        }


    
    # ========================================================================
    # OCUPACAO  OK
    # ========================================================================    
    def _process_occupancy_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Occupancy mode: Detect EMPTY / OCCUPIED / FULL states.
        
        ✅ v2.2 MELHORADO:
        - Estados PENDING para feedback visual
        - Logs detalhados com timing
        - 100% configurável (sem hardcode)
        
        Lógica:
        - empty_threshold: pessoas <= X → EMPTY
        - full_threshold: pessoas >= Y → FULL
        - Timeouts: tempo mínimo em cada estado antes de alertar
        
        Estados possíveis:
        - EMPTY: Zona vazia (confirmado após timeout)
        - EMPTY_PENDING: Vazia mas aguardando confirmação
        - OCCUPIED: Ocupada (estado intermediário)
        - FULL: Zona cheia (confirmado após timeout)
        - FULL_PENDING: Cheia mas aguardando confirmação
        """
        
       
        # ✅ Obter configurações da zona (tudo do banco)
        count = state.object_count
        empty_threshold = zone.get("empty_threshold", 0)
        full_threshold = zone.get("full_threshold", 3)
        empty_timeout = zone.get("empty_timeout", 5.0)
        full_timeout = zone.get("full_timeout", 10.0)
        email_cooldown = zone.get("email_cooldown", 600.0)
        
        now = datetime.now()
        
        # ✅ Determinar status RAW (baseado em threshold)
        if count < empty_threshold:   raw_status = "EMPTY"
        elif count >= full_threshold: raw_status = "FULL"
        else:                         raw_status = "OCCUPIED"
        
        # ✅ Atualizar timing
        if raw_status == "EMPTY":
            if state.empty_since is None:
                state.empty_since = now
            state.full_since = None
        elif raw_status == "FULL":
            if state.full_since is None:
                state.full_since = now
            state.empty_since = None
        else:
            state.empty_since = None
            state.full_since = None
        
        # ✅ Verificar se deve alertar (após timeout)
        alert = False
        alert_message = None
        confirmed_status = raw_status
        
        if raw_status == "EMPTY" and state.empty_since:
            elapsed = (now - state.empty_since).total_seconds()
            if elapsed >= empty_timeout:
                # ✅ Confirmado após timeout
                alert = True
                alert_message = f"Zona vazia por {int(elapsed)}s"
                confirmed_status = "EMPTY"
            else:
                # ⏳ Aguardando confirmação
                confirmed_status = "EMPTY_PENDING"
                alert = False
        
        if raw_status == "FULL" and state.full_since:
            elapsed = (now - state.full_since).total_seconds()
            if elapsed >= full_timeout:
                # ✅ Confirmado após timeout
                alert = True
                alert_message = f"Zona cheia por {int(elapsed)}s"
                confirmed_status = "FULL"
            else:
                # ⏳ Aguardando confirmação
                confirmed_status = "FULL_PENDING"
                alert = False
        
        # ✅ Email cooldown
        can_alert = True
        if alert and state.last_alert_time:
            elapsed = (now - state.last_alert_time).total_seconds()
            can_alert = elapsed >= email_cooldown
        
        if alert and can_alert:
            state.last_alert_time = now
        
        # ✅ Log status changes com informações de timing
        if confirmed_status != state.status:
            elapsed_info = ""
            if state.empty_since:
                elapsed_info = f" (vazia há {int((now - state.empty_since).total_seconds())}s)"
            elif state.full_since:
                elapsed_info = f" (cheia há {int((now - state.full_since).total_seconds())}s)"
            
            logger.info(
                f"🏢 Zone '{zone['name']}' (camera {self.camera_id}): "
                f"{state.status} → {confirmed_status} ({count} pessoas){elapsed_info}"
            )
        
        state.status = confirmed_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "occupancy",
            "count": count,
            "status": confirmed_status,
            "alert": alert and can_alert,
            "alert_message": alert_message,
            "empty_duration": (now - state.empty_since).total_seconds() if state.empty_since else 0,
            "full_duration": (now - state.full_since).total_seconds() if state.full_since else 0,
        }

    

    def _process_counting_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Counting mode: Simple threshold-based counting.
        
        Lógica:
        - full_threshold: mínimo de pessoas para registrar
        - Usado para contagem de entrada/saída simples
        """
        count = state.object_count
        full_threshold = zone.get("fullthreshold", 1)
        
        # Status baseado apenas no threshold
        if count >= full_threshold:
            new_status = "DETECTED"
            alert = True
        else:
            new_status = "IDLE"
            alert = False
        
        # Log status changes
        if new_status != state.status:
            logger.info(
                f"🔢 Zone {zone['name']} (camera {self.camera_id}): "
                f"{state.status} → {new_status} ({count} pessoas)"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "counting",
            "count": count,
            "status": new_status,
            "alert": alert,
            "alert_message": f"{count} pessoas detectadas" if alert else None,
        }
    


    def _process_alert_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Alert mode: Immediate alert when threshold exceeded.
        
        Lógica:
        - full_threshold: pessoas >= X → ALERTA IMEDIATO
        - full_timeout: tolerância antes de alertar
        """
        count = state.object_count
        full_threshold = zone.get("fullthreshold", 1)
        empty_timeout = zone.get('empty_timeout', 5.0)
        full_timeout = zone.get("fulltimeout", 10.0)  
        
        now = datetime.now()
        
        if count >= full_threshold:
            if state.full_since is None:
                state.full_since = now
            
            elapsed = (now - state.full_since).total_seconds()
            
            if elapsed >= full_timeout:
                new_status = "ALERT"
                alert = True
            else:
                new_status = "PENDING"
                alert = False
        else:
            state.full_since = None
            new_status = "NORMAL"
            alert = False
        
        # Email cooldown
        email_cooldown = zone.get("emailcooldown", 120.0)
        can_alert = True
        
        if alert and state.last_alert_time:
            elapsed = (now - state.last_alert_time).total_seconds()
            can_alert = elapsed >= email_cooldown
        
        if alert and can_alert:
            state.last_alert_time = now
        
        if new_status != state.status:
            logger.warning(
                f"🚨 Zone {zone['name']} (camera {self.camera_id}): "
                f"{state.status} → {new_status} ({count} pessoas)"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "alert",
            "count": count,
            "status": new_status,
            "alert": alert and can_alert,
            "alert_message": f"ALERTA: {count} pessoas na zona" if alert else None,
        }
    


    def _process_tracking_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Tracking mode: Simple presence tracking.
        
        Lógica:
        - Rastreia IDs únicos que passam pela zona
        - Não aplica thresholds ou timeouts
        """
        count = state.object_count
        
        new_status = "TRACKING" if count > 0 else "IDLE"
        
        if new_status != state.status:
            logger.info(
                f"🎯 Zone {zone['name']} (camera {self.camera_id}): "
                f"tracking {count} object(s)"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "tracking",
            "count": count,
            "tracked_ids": state.objects_inside,
            "status": new_status,
            "alert": False,
        }
    

    def _process_generic_mode(self, zone: Dict, state: ZoneState) -> Dict:
        """
        Generic/legacy mode: Basic occupancy logic.
        """
        count = state.object_count
        full_threshold = zone.get("fullthreshold", 3)
        
        if count >= full_threshold:
            new_status = "FULL"
        elif count > 0:
            new_status = "OCCUPIED"
        else:
            new_status = "EMPTY"
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "generic",
            "count": count,
            "status": new_status,
            "alert": False,
        }
    

    
    # ========================================================================
    # VISUALIZATION
    # ========================================================================
    
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
        """Desenha texto com outline para contraste perfeito."""
        cv2.putText(img, text, pos, font, scale, outline_color, outline_thickness, cv2.LINE_AA)
        cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)


    def draw_zones(self, frame: np.ndarray, track_state: Dict = None) -> np.ndarray:
        """
        Draw zones overlay on frame with custom colors, clean design, and bounding boxes.
        
        Args:
            frame: Input frame to draw on
            track_state: Current tracking state {track_id: {"bbox": [x1,y1,x2,y2], "class_id": int, "confidence": float}}
        """
        if frame is None or not self.zones:
            return frame
        
        if not self.last_frame_shape:
            logger.warning(
                f"Zones loaded for camera {self.camera_id} "
                f"but frame shape not initialized yet"
            )
            return frame
        
        h, w = frame.shape[:2]
        
        for zone in self.zones:
            zone_id = zone.get("id")
            if not zone_id or zone_id not in self.zone_states:
                continue
            
            state = self.zone_states[zone_id]
            
            # Convert points to pixel coordinates
            is_normalized = all(
                0 <= p[0] <= 1 and 0 <= p[1] <= 1 for p in zone["points"]
            )
            
            if is_normalized:
                points = np.array(
                    [[int(p[0] * w), int(p[1] * h)] for p in zone["points"]],
                    dtype=np.int32,
                )
            else:
                points = np.array(zone["points"], dtype=np.int32)
            
            # ✅ Usa SEMPRE a cor configurada pelo usuário (salva no banco)
            if zone.get("color"):
                color = self._hex_to_bgr(zone["color"])
            else:
                # Fallback para azul suave padrão
                color = (246, 130, 59)  # #3B82F6
            
            # Draw polygon border
            cv2.polylines(frame, [points], True, color, 2)
            
            # Fill with transparency (mais translúcido = mais bonito)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], color)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            
            # ========== DESENHAR BOUNDING BOXES DOS OBJETOS NA ZONA ==========
            if track_state:
                # Obter lista de classes permitidas na zona (se houver filtro)
                detection_classes = zone.get("detection_classes", [])
                
                for obj_id in state.objects_inside:
                    if obj_id not in track_state:
                        continue
                    
                    obj_data = track_state[obj_id]
                    bbox = obj_data.get("bbox")
                    class_id = obj_data.get("class_id", -1)
                    confidence = obj_data.get("confidence", 0.0)
                    
                    if not bbox or len(bbox) < 4:
                        continue
                    
                    # Verificar se objeto está nas classes permitidas (se houver filtro)
                    if detection_classes and class_id not in detection_classes:
                        continue  # Não desenha objetos filtrados
                    
                    # Coordenadas da bounding box
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # Desenhar retângulo ao redor do objeto (mesma cor da zona)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Importar COCO classes para obter nome da classe
                    try:
                        from backend.services.coco_classes import COCO_CLASSES
                        class_name = COCO_CLASSES.get(class_id, f"class_{class_id}")
                    except:
                        class_name = f"class_{class_id}"
                    
                    # Label com classe e confiança
                    label = f"{class_name} {confidence:.2f}"
                    
                    # Tamanho do texto para background
                    (label_w, label_h), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                    )
                    
                    # Garantir que o label não saia da imagem
                    label_y1 = max(y1 - label_h - 10, label_h + 10)
                    label_y2 = label_y1 + label_h + 10
                    
                    # Desenhar background do label (mesma cor da zona)
                    cv2.rectangle(
                        frame,
                        (x1, label_y1),
                        (x1 + label_w + 10, label_y2),
                        color,
                        -1  # Preenchido
                    )
                    
                    # Desenhar texto do label (branco)
                    cv2.putText(
                        frame,
                        label,
                        (x1 + 5, label_y2 - 7),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),  # Branco
                        1,
                        cv2.LINE_AA
                    )
            # ========== FIM DO DESENHO DAS BOUNDING BOXES ==========
            
            # Calculate center for text
            c = points.mean(axis=0).astype(int)
            
            # ✅ TEXTOS PROFISSIONAIS com outline            
            # Função auxiliar para desenhar texto com outline
            def draw_text_with_outline(img, text, pos, font, scale, color, thickness, outline_color=(0, 0, 0), outline_thickness=3):
                # Outline (contorno preto)
                cv2.putText(img, text, pos, font, scale, outline_color, outline_thickness, cv2.LINE_AA)
                # Texto principal
                cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)
            
            # 1. NOME DA ZONA (topo, discreto)
            name_text = zone["name"]
            draw_text_with_outline(
                frame,
                name_text,
                (c[0] - 60, c[1] - 40),
                cv2.FONT_HERSHEY_DUPLEX,
                0.45,
                (255, 255, 255),
                1
            )
            
            # 2. CONTAGEM (centro, destaque)
            if zone.get("mode") == "capacity":
                max_cap = zone.get("metadata", {}).get("max_capacity", "?")
                count_text = f"{state.object_count}/{max_cap}"
            else:
                count_text = f"{state.object_count}"
            
            draw_text_with_outline(
                frame,
                count_text,
                (c[0] - 25, c[1] + 10),
                cv2.FONT_HERSHEY_DUPLEX,
                0.9,
                (255, 255, 255),
                2
            )
            
            # 3. STATUS (embaixo, em português)
            status_labels = {
                "NORMAL": "OK",
                "WARNING": "AVISO",
                "CRITICAL": "ALERTA",
                "EMPTY": "VAZIO",
                "OCCUPIED": "OCUPADO",
                "FULL": "CHEIO",
                "ALERT": "ALERTA",
                "PENDING": "PENDENTE",
                "DETECTED": "DETECTADO",
                "IDLE": "INATIVO",
                "TRACKING": "RASTREANDO",
            }
            status_text = status_labels.get(state.status, state.status)
            
            draw_text_with_outline(
                frame,
                status_text,
                (c[0] - 35, c[1] + 35),
                cv2.FONT_HERSHEY_DUPLEX,
                0.35,
                (255, 255, 255),
                1
            )
        
        return frame

    
    
    @staticmethod
    def _get_status_color(mode: str, status: str) -> Tuple[int, int, int]:
        """
        Get BGR color based on mode and status.
        
        Returns:
            (B, G, R) tuple
        """
        # Capacity mode colors
        if mode == "capacity":
            if status == "CRITICAL":
                return (0, 0, 255)  # Red
            elif status == "WARNING":
                return (0, 165, 255)  # Orange
            else:
                return (0, 255, 0)  # Green
        
        # Occupancy mode colors
        if mode == "occupancy":
            if status == "FULL":
                return (0, 0, 255)  # Red
            elif status == "OCCUPIED":
                return (0, 255, 255)  # Yellow
            else:
                return (128, 128, 128)  # Gray
        
        # Alert mode colors
        if mode == "alert":
            if status == "ALERT":
                return (0, 0, 255)  # Red
            elif status == "PENDING":
                return (0, 165, 255)  # Orange
            else:
                return (0, 255, 0)  # Green
        
        # Default: blue
        return (255, 130, 0)
    
    @staticmethod
    def _hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to BGR tuple.
        
        Args:
            hex_color: Hex string like "#3B82F6" or "3B82F6"
        
        Returns:
            (B, G, R) tuple
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)
    
    # ========================================================================
    # METRICS AGGREGATION
    # ========================================================================
    
    def get_aggregate_metrics(self) -> Dict:
        """
        Get aggregated metrics across all zones.
        
        Returns:
            Dict with total counts, alerts, etc.
        """
        total_count = sum(state.object_count for state in self.zone_states.values())
        zones_with_alerts = sum(
            1 for zone in self.zones
            for state in [self.zone_states.get(zone.get("id"))]
            if state and state.status in ("ALERT", "CRITICAL", "FULL")
        )
        
        return {
            "total_objects_in_zones": total_count,
            "zones_active": len(self.zones),
            "zones_with_alerts": zones_with_alerts,
            "zone_states": {
                zone_id: {
                    "count": state.object_count,
                    "status": state.status,
                }
                for zone_id, state in self.zone_states.items()
            },
        }
