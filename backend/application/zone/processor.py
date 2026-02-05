"""
Zone Processor v3.0 - Clean Architecture

Orquestrador principal de processamento de zonas.
"""

import logging
import time
from typing import List, Dict, Tuple, Optional

from backend.core.domain.entities.zones import Zone

from backend.application.zone.modes.capacity.capacity_handler import CapacityModeHandler
from backend.application.zone.modes.occupancy.occupancy_handler import (
    OccupancyModeHandler,
)
from backend.application.zone.modes.counting.counting_handler import CountingModeHandler
from backend.application.zone.modes.alert.alert_handler import AlertModeHandler
from backend.application.zone.modes.tracking.tracking_handler import TrackingModeHandler
from backend.application.zone.modes.queue.queue_handler import QueueModeHandler

from backend.application.zone.modes.base import BaseModeHandler
from backend.application.zone.modes.common.geometry import detect_objects_in_zone
from backend.application.zone.modes.common.state import ZoneState

from backend.adapters.zone.zone_mapper import ZoneMapper
from backend.infrastructure.visualization.zone_renderer import ZoneRenderer

logger = logging.getLogger(__name__)


class ZoneProcessorV3:
    """
    Processador de zonas v3.0 - Clean Architecture.

    Responsabilidades:
    - Orquestrar detecção de objetos em zonas (geometria)
    - Delegar processamento de métricas para handlers de modo
    - Delegar visualização para ZoneRenderer
    - Manter estado runtime (domain entities)

    NÃO faz:
    - Lógica de negócio específica de modo (delegada aos handlers)
    - Geometria de baixo nível (delegada a PolygonEngine via common/geometry.py)
    - Renderização de overlays (delegada a ZoneRenderer)
    """

    def __init__(self, camera_id: int, zones_dict: List[Dict]):
        """
        Inicializa processador com zonas.

        Args:
            camera_id: ID da câmera
            zones_dict: Lista de dicts do DB (via camera_sync)
        """
        self.camera_id = camera_id

        # ✅ ADAPTER: Dict → Entity
        self.zones: List[Zone] = ZoneMapper.dicts_to_zones(zones_dict)

        # ✅ MODE HANDLERS (Strategy Pattern)
        self._mode_handlers: Dict[str, BaseModeHandler] = {
            "capacity": CapacityModeHandler(),
            "occupancy": OccupancyModeHandler(),
            "counting": CountingModeHandler(),
            "alert": AlertModeHandler(),
            "tracking": TrackingModeHandler(),
            "queue": QueueModeHandler(),
        }

        # ✅ INFRASTRUCTURE
        self.renderer = ZoneRenderer()

        # ✅ STATE
        self.last_frame_shape: Optional[Tuple[int, int]] = None

        logger.info(
            f"✅ ZoneProcessorV3 initialized for camera {camera_id} "
            f"with {len(self.zones)} zones"
        )

    def update_zones(self, zones_dict: List[Dict]):
        """
        Atualiza zonas (chamado quando DB muda).

        Args:
            zones_dict: Lista de dicts atualizados do DB
        """
        new_zones = ZoneMapper.dicts_to_zones(zones_dict)

        # Preservar estado runtime de zonas existentes
        old_zones_map = {z.config.zone_id: z for z in self.zones}
        for new_zone in new_zones:
            zone_id = new_zone.config.zone_id
            if zone_id in old_zones_map:
                # Atualiza config mas mantém state
                old_zone = old_zones_map[zone_id]
                new_zone.state = old_zone.state  # Preserva timers, counters, etc.

        self.zones = new_zones
        logger.info(
            f"🔄 Zones updated for camera {self.camera_id}: {len(new_zones)} zones"
        )

    def process_frame(
        self,
        detections: List[Dict],
        track_state: Dict[int, Dict],
        frame_shape: Tuple[int, int],
    ) -> Dict[int, Dict]:
        """
        Processa frame completo.

        Pipeline:
        1. Detectar objetos em cada zona (geometria)
        2. Atualizar estado de cada zona
        3. Delegar cálculo de métricas para handler do modo

        Args:
            detections: Lista de detecções YOLO (não usado, usa track_state)
            track_state: {track_id: {"bbox": [x1,y1,x2,y2], "class_id": int, "confidence": float}}
            frame_shape: (height, width)

        Returns:
            {zone_id: {métricas completas...}}
        """
        if not self.zones:
            return {}

        # Atualizar frame shape
        if self.last_frame_shape != frame_shape:
            self.last_frame_shape = frame_shape

        current_time = time.time()
        zone_metrics: Dict[int, Dict] = {}

        for zone in self.zones:
            zone_id = zone.config.zone_id

            # 1. GEOMETRIA: Detectar objetos dentro da zona
            objects_inside = detect_objects_in_zone(
                zone=zone,
                track_state=track_state,
                frame_size=frame_shape,
            )

            # 2. ATUALIZAR ESTADO
            zone.state.objects_inside = objects_inside
            zone.state.object_count = len(objects_inside)

            # 3. PROCESSAR MODO (delegar para handler)
            mode = zone.config.mode
            handler = self._mode_handlers.get(mode)

            if not handler:
                logger.warning(
                    f"Unknown mode '{mode}' for zone {zone_id}, using generic handler"
                )
                handler = self._generic_handler

            # Converter Zone entity → dict (compatibilidade com handlers)
            zone_dict = self._zone_to_dict(zone)

            # ✅ HANDLER processa e retorna métricas
            metrics = handler.process(
                zone=zone_dict,
                state=zone.state,
                track_state=track_state,
                current_time=current_time,
            )

            # 4. ATUALIZAR METADATA (se handler retornou)
            if "metadata_updated" in metrics:
                zone.config.metadata = metrics["metadata_updated"]
                # TODO: Persistir metadata no DB se necessário

            zone_metrics[zone_id] = metrics

        return zone_metrics

    def draw_zones(
        self,
        frame,
        track_state: Optional[Dict] = None,
    ):
        """
        Desenha overlays de zona (delega para renderer).

        Args:
            frame: Frame BGR (np.ndarray)
            track_state: {track_id: {"bbox": [...], "class_id": int}}

        Returns:
            Frame com overlays
        """
        if frame is None:
            return frame

        # ✅ DELEGA para infrastructure
        return self.renderer.draw_zones(
            frame=frame,
            zones=self.zones,
            track_state=track_state,
        )

    def get_aggregate_metrics(self) -> Dict:
        """
        Retorna métricas agregadas (compatibilidade com código legado).

        Returns:
            Dict com totais
        """
        total_count = sum(z.state.object_count for z in self.zones)
        zones_with_alerts = sum(
            1
            for z in self.zones
            if z.state.status in ("ALERT", "CRITICAL", "FULL", "WARNING")
        )

        return {
            "total_objects_in_zones": total_count,
            "zones_active": len(self.zones),
            "zones_with_alerts": zones_with_alerts,
            "zone_states": {
                z.config.zone_id: {
                    "count": z.state.object_count,
                    "status": z.state.status,
                }
                for z in self.zones
            },
        }

    # ========================================================================
    # COMPATIBILITY LAYER (v2 API)
    # ========================================================================

    @property
    def zone_states(self) -> Dict:
        """
        Compatibilidade com v2: retorna dict de states indexado por zone_id.

        Returns:
            {zone_id: ZoneStateWrapper}
        """
        return {
            zone.config.zone_id: ZoneStateWrapper(zone.state)
            for zone in self.zones
        }

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _zone_to_dict(self, zone: Zone) -> Dict:
        """
        Converte Zone entity → dict (para compatibilidade com handlers).

        Args:
            zone: Zone entity

        Returns:
            Dict com estrutura esperada pelos handlers
        """
        config = zone.config

        # Normalizar points para lista de dicts
        points = []
        for p in config.points:
            if isinstance(p, dict):
                points.append(p)
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                points.append({"x": p[0], "y": p[1]})

        return {
            "id": config.zone_id,
            "name": config.name,
            "mode": config.mode,
            "color": config.color,
            "points": points,
            "detection_classes": config.detection_classes,
            "empty_threshold": config.empty_threshold,
            "full_threshold": config.full_threshold,
            "empty_timeout": config.empty_timeout,
            "full_timeout": config.full_timeout,
            "email_cooldown": config.email_cooldown,
            "metadata": config.metadata or {},
        }

    def _generic_handler(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float,
    ) -> Dict:
        """
        Handler genérico (fallback para modos desconhecidos).

        Args:
            zone: Config da zona
            state: Estado runtime
            track_state: Estado de tracking
            current_time: Timestamp atual

        Returns:
            Dict com métricas básicas
        """
        count = state.object_count
        full_threshold = zone.get("full_threshold", 3)

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


class ZoneStateWrapper:
    """
    Wrapper para compatibilizar Zone.state com interface antiga (v2).

    Permite acesso a propriedades como objeto.
    """

    def __init__(self, zone_state: ZoneState):
        """
        Args:
            zone_state: ZoneState entity (domain)
        """
        self._state = zone_state

    @property
    def object_count(self) -> int:
        return self._state.object_count

    @property
    def status(self) -> str:
        return self._state.status

    @property
    def empty_since(self):
        """Retorna datetime ou None (compatibilidade v2)"""
        if self._state.empty_since:
            from datetime import datetime

            if isinstance(self._state.empty_since, datetime):
                return self._state.empty_since
            elif isinstance(self._state.empty_since, (int, float)):
                return datetime.fromtimestamp(self._state.empty_since)
        return None

    @property
    def full_since(self):
        """Retorna datetime ou None (compatibilidade v2)"""
        if self._state.full_since:
            from datetime import datetime

            if isinstance(self._state.full_since, datetime):
                return self._state.full_since
            elif isinstance(self._state.full_since, (int, float)):
                return datetime.fromtimestamp(self._state.full_since)
        return None

    @property
    def objects_inside(self) -> set:
        return self._state.objects_inside

    @property
    def last_alert_time(self):
        """Retorna datetime ou None"""
        if self._state.last_alert_time:
            from datetime import datetime

            if isinstance(self._state.last_alert_time, datetime):
                return self._state.last_alert_time
            elif isinstance(self._state.last_alert_time, (int, float)):
                return datetime.fromtimestamp(self._state.last_alert_time)
        return None
