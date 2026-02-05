"""
Use Case: Processar frame de zona

Responsabilidade: Orquestrar geometria + métricas
"""

from typing import Dict, Tuple, List, Set
import logging

from backend.core.domain.entities import Zone
from backend.core.domain.services import GeometryService

from .zone_metrics_calculator import ZoneMetricsCalculator, ZoneMetrics

logger = logging.getLogger(__name__)


class ProcessZoneFrameUseCase:
    """
    Use Case: Processar zonas em um frame.

    Responsabilidade:
    - Encontrar objetos dentro de zonas (geometria)
    - Calcular métricas (lógica de modo)
    - Retornar resultados agregados
    """

    def __init__(self) -> None:
        self.geometry_service = GeometryService()
        self.metrics_calculator = ZoneMetricsCalculator()

    def execute(
        self,
        zones: List[Zone],
        track_state: Dict[int, Dict],
        frame_size: Tuple[int, int],
        current_time: float,
    ) -> Dict[int, ZoneMetrics]:
        """
        Processa todas as zonas para um frame.

        Args:
            zones: Lista de zonas (entities)
            track_state: {track_id: {"bbox": [...], "class_id": int, ...}}
            frame_size: (height, width)
            current_time: Timestamp (epoch)

        Returns:
            {zone_id: ZoneMetrics}
        """
        results: Dict[int, ZoneMetrics] = {}

        for zone in zones:
            # 1. Geometria: encontrar objetos na zona
            meta = zone.config.metadata or {}
            allowed_classes = set(meta.get("detection_classes", []))
            if not allowed_classes:
                # None = todas as classes
                allowed_classes = None

            objects_inside: Set[int] = self.geometry_service.objects_in_zone(
                zone_polygon=zone.config.polygon,
                track_state=track_state,
                frame_size=frame_size,
                allowed_classes=allowed_classes,
            )

            # 2. Derivar global_ids_inside a partir do mesmo track_state
            global_ids_inside: Set[int] = set()
            for track_id in objects_inside:
                ts = track_state.get(track_id)
                if not ts:
                    continue
                gid = ts.get("global_id")
                if gid is not None:
                    global_ids_inside.add(gid)

            global_ids_param: Set[int] | None = (
                global_ids_inside if global_ids_inside else None
            )

            # 3. Lógica de negócio: calcular métricas
            metrics = self.metrics_calculator.calculate(
                zone=zone,
                objects_inside=objects_inside,
                current_time=current_time,
                global_ids_inside=global_ids_param,
            )

            results[zone.config.zone_id] = metrics

        return results
