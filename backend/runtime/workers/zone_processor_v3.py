"""
Zone Processor v3.0 - Clean Architecture
Responsabilidade: Orquestrar use cases (sem lógica duplicada)
"""
import logging
import time
from typing import List, Dict, Tuple, Optional, Callable, Any  

from backend.core.domain.entities import Zone
from backend.core.domain.entities.zones import ZoneMode
from backend.application.zone import ProcessZoneFrameUseCase
from backend.application.zone.zone_metadata_service import normalize_metadata_for_mode

from backend.infrastructure.visualization import ZoneRenderer
from backend.adapters.zone import ZoneMapper

logger = logging.getLogger(__name__)

REID_CAPABLE_TRACKERS = {"strongsort", "yolo_strongsort", "fast_strongsort"}

ZoneAlertCallback = Callable[
    [int, int, Dict[str, Any], Optional[str], float],
    Optional[Dict[str, Any]],
]

class ZoneProcessorV3:
    """
    Processador de zonas v3.0 - Clean Architecture.
    
    Responsabilidades:
    - Orquestrar use cases (application layer)
    - Delegar geometria (infrastructure)
    - Delegar visualização (infrastructure)
    - Manter estado runtime (domain entities)
    """
    
    def __init__(
            self,
            camera_id: int,
            zones_dict: List[Dict],
            alert_callback: Optional[
                Callable[[int, int, Dict[str, Any], Optional[str], float], None]
            ] = None,):
        """
        Inicializa processador com zonas.

        Args:
            camera_id: ID da câmera
            zones_dict: Lista de dicts do DB (via camera_sync)
            alert_callback: Callback opcional chamado quando uma zona
                entra em estado de alerta (alert=True) com mudança de status.
                Assinatura: (camera_id, zone_id, metrics_dict, event_time_epoch)
        """
        self.camera_id = camera_id
        
        # ADAPTER: Dict → Entity
        self.zones: List[Zone] = ZoneMapper.dicts_to_zones(zones_dict)
        
        # USE CASES
        self.process_frame_usecase = ProcessZoneFrameUseCase()
        
        # INFRASTRUCTURE
        self.renderer = ZoneRenderer()
        
        # STATE
        self.last_frame_shape: Optional[Tuple[int, int]] = None

        # Hook opcional para gravação de vídeo / integração com Alert
        self.alert_callback = alert_callback

        logger.info(
                "✅ ZoneProcessorV3 initialized for camera %s with %d zones",
                camera_id,
                len(self.zones),
            )
        
    def _maybe_emit_alert(
        self,
        zone_id: int,
        metrics_dict: Dict[str, Any],
        prev_status_by_zone: Dict[int, str],
        event_time: float,
    ) -> None:
        """Chama o alert_callback (se configurado), blindando erros."""
        if self.alert_callback is None:
            return

        try:
            previous_status = prev_status_by_zone.get(zone_id)
            self.alert_callback(
                self.camera_id,
                zone_id,
                metrics_dict,
                previous_status,
                event_time,
            )
        except Exception:
            logger.exception(
                "ZoneProcessorV3: erro ao executar alert_callback "
                "(camera_id=%s, zone_id=%s)",
                self.camera_id,
                zone_id,
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
        
        logger.info(f"🔄 Zones updated for camera {self.camera_id}: {len(new_zones)} zones")
        
    
    def process_frame(
        self,
        detections: List[Dict],
        default_track_state: Dict[int, Dict],
        frame_shape: Tuple[int, int],
        per_tracker_state: Optional[Dict[str, Dict[int, Dict]]] = None,
        camera_tracker_type: str = "yolo_bytetrack",
    ) -> Dict[int, Dict]:
        """
        Processa frame (delega para use case), respeitando overrides de tracker por zona
        e modo `detection_only`, agora com governança de ReID por zona (reid_required).

        Returns:
            Dict[zone_id, metrics_dict]
        """
        if not self.zones:
            return {}

        # Atualiza shape
        if self.last_frame_shape != frame_shape:
            self.last_frame_shape = frame_shape

        current_time = time.time()
        per_tracker_state = per_tracker_state or {}

        # Captura status anterior das zonas para detectar "novo alerta"
        prev_status_by_zone: Dict[int, str] = {
                    z.config.zone_id: z.state.status for z in self.zones
                }

        # Particiona zonas por tipo de tracker efetivo + reid_required
        normal_groups: Dict[str, List[Zone]] = {}
        reid_groups: Dict[str, List[Zone]] = {}
        detection_only_zones: List[Zone] = []

        for zone in self.zones:
            meta = zone.config.metadata or {}
            override = meta.get("tracker_override")

            # Flag de ReID por zona (normalizada pela API)
            reid_required = bool(meta.get("reid_required", False))

            # Define tracker efetivo
            effective_tracker = camera_tracker_type

            if override is not None:
                override_str = str(override)
                ov_lower = override_str.lower()

                if ov_lower in ("", "inherit", "camera_default"):
                    # Herda tracker da câmera
                    effective_tracker = camera_tracker_type
                elif ov_lower in ("detection_only", "none", "off"):
                    if reid_required:
                        # Zonas que exigem ReID não podem ser somente detecção
                        logger.warning(
                            "ZoneProcessorV3: zone_id=%s name='%s' tem "
                            "reid_required=True mas tracker_override='%s'. "
                            "Forçando uso do tracker da câmera '%s'.",
                            zone.config.zone_id,
                            zone.config.name,
                            override_str,
                            camera_tracker_type,
                        )
                        effective_tracker = camera_tracker_type
                    else:
                        effective_tracker = "detection_only"
                else:
                    # Usa exatamente o valor configurado, para bater com ctx.required_tracker_types
                    effective_tracker = override_str

            # Zonas detection_only só são permitidas para modos que não dependem
            # fortemente de histórico de IDs (exclui COUNTING e QUEUE).
            if (
                effective_tracker == "detection_only"
                and zone.config.mode not in (ZoneMode.COUNTING, ZoneMode.QUEUE)
            ):
                detection_only_zones.append(zone)
            else:
                # Blindagem: se pediu ReID mas o tracker efetivo não é compatível,
                # faz fallback para processamento normal (sem filtro de global_id)
                if reid_required and effective_tracker not in REID_CAPABLE_TRACKERS:
                    logger.warning(
                        "ZoneProcessorV3: zone_id=%s name='%s' tem reid_required=True "
                        "mas tracker efetivo '%s' não é compatível com ReID. "
                        "Aplicando fallback para processamento SEM filtro de ReID.",
                        zone.config.zone_id,
                        zone.config.name,
                        effective_tracker,
                    )
                    use_reid = False
                else:
                    use_reid = reid_required

                if use_reid:
                    reid_groups.setdefault(effective_tracker, []).append(zone)
                else:
                    normal_groups.setdefault(effective_tracker, []).append(zone)

        results: Dict[int, Dict] = {}

        # ------------------------------------------------------------------ #
        # 1) Zonas normais: usam track_state completo do tracker escolhido
        # ------------------------------------------------------------------ #
        for tracker_type, zones_group in normal_groups.items():
            if not zones_group:
                continue

            # Escolhe o track_state correto
            if tracker_type == camera_tracker_type:
                ts = default_track_state
            else:
                ts = per_tracker_state.get(tracker_type)

            if ts is None:
                # Fallback seguro: loga e usa o default da câmera
                logger.warning(
                    "ZoneProcessorV3: tracker '%s' não encontrado em per_tracker_state; "
                    "usando estado do tracker default '%s'.",
                    tracker_type,
                    camera_tracker_type,
                )
                ts = default_track_state

            if not ts:
                # Sem estado de tracking útil para este grupo
                continue

            zone_metrics = self.process_frame_usecase.execute(
                zones=zones_group,
                track_state=ts,
                frame_size=frame_shape,
                current_time=current_time,
            )

            for zone_id, metrics in zone_metrics.items():
                            md = metrics.to_dict()
                            results[zone_id] = md
                            self._maybe_emit_alert(
                                zone_id=zone_id,
                                metrics_dict=md,
                                prev_status_by_zone=prev_status_by_zone,
                                event_time=current_time,
                            )

        # ------------------------------------------------------------------ #
        # 2) Zonas com reid_required=True: filtram tracks sem global_id
        # ------------------------------------------------------------------ #
        for tracker_type, zones_group in reid_groups.items():
            if not zones_group:
                continue

            # Escolhe o track_state correto
            if tracker_type == camera_tracker_type:
                ts = default_track_state
            else:
                ts = per_tracker_state.get(tracker_type)

            if ts is None:
                logger.warning(
                    "ZoneProcessorV3: tracker '%s' não encontrado em per_tracker_state "
                    "para zonas com reid_required; usando estado do tracker default '%s'.",
                    tracker_type,
                    camera_tracker_type,
                )
                ts = default_track_state

            if not ts:
                # Sem estado de tracking útil para este grupo
                continue

            # Filtra apenas tracks que têm global_id (ReID resolvido pelo VisionSystem)
            ts_reid = {tid: st for tid, st in ts.items() if st.get("global_id") is not None}

            if not ts_reid:
                logger.debug(
                    "ZoneProcessorV3: nenhuma track com global_id disponível para "
                    "tracker '%s' em zonas com reid_required=True (camera_id=%s).",
                    tracker_type,
                    self.camera_id,
                )
                continue

            zone_metrics = self.process_frame_usecase.execute(
                zones=zones_group,
                track_state=ts_reid,
                frame_size=frame_shape,
                current_time=current_time,
            )

            for zone_id, metrics in zone_metrics.items():
                            md = metrics.to_dict()
                            md.setdefault("reid_required", True)
                            results[zone_id] = md
                            self._maybe_emit_alert(
                                zone_id=zone_id,
                                metrics_dict=md,
                                prev_status_by_zone=prev_status_by_zone,
                                event_time=current_time,
                            )

        # ------------------------------------------------------------------ #
        # 3) Zonas detection_only: constroem track_state sintético a partir das detecções YOLO (somente para zonas que NÃO exigem ReID)
        # ------------------------------------------------------------------ #
        if detection_only_zones and detections:
            detection_based_state: Dict[int, Dict] = {}

            for idx, det in enumerate(detections):
                bbox = det.get("bbox")
                class_id = det.get("class_id")
                if bbox is None or class_id is None:
                    continue

                detection_based_state[idx + 1] = {
                    "bbox": bbox,
                    "class_id": class_id,
                    "confidence": det.get("confidence", 1.0),
                }

            if detection_based_state:
                zone_metrics_do = self.process_frame_usecase.execute(
                    zones=detection_only_zones,
                    track_state=detection_based_state,
                    frame_size=frame_shape,
                    current_time=current_time,
                )

                for zone_id, metrics in zone_metrics_do.items():
                                    md = metrics.to_dict()
                                    results[zone_id] = md
                                    self._maybe_emit_alert(
                                        zone_id=zone_id,
                                        metrics_dict=md,
                                        prev_status_by_zone=prev_status_by_zone,
                                        event_time=current_time,
                                    )

        return results





    
    def draw_zones(
        self,
        frame,
        track_state: Optional[Dict] = None
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
        
        # DELEGA para infrastructure
        return self.renderer.draw_zones(
            frame=frame,
            zones=self.zones,
            track_state=track_state
        )
    
    def get_aggregate_metrics(self) -> Dict:
        """
        Retorna métricas agregadas (compatibilidade com código legado).
        
        Returns:
            Dict com totais
        """
        total_count = sum(z.state.object_count for z in self.zones)
        zones_with_alerts = sum(
            1 for z in self.zones
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
            }
        }

    @property
    def zone_states(self) -> Dict:
        """Compatibilidade com v2: retorna dict de states indexado por zone_id"""
        class ZoneStateWrapper:
            """Wrapper para compatibilizar Zone.state com interface antiga"""
            def __init__(self, zone_state):
                self._state = zone_state
            
            @property
            def object_count(self):
                return self._state.object_count
            
            @property
            def status(self):
                return self._state.status
            
            @property
            def empty_since(self):
                # Converter float → datetime se necessário
                if self._state.empty_since > 0:
                    from datetime import datetime
                    return datetime.fromtimestamp(self._state.empty_since)
                return None
            
            @property
            def full_since(self):
                if self._state.full_since > 0:
                    from datetime import datetime
                    return datetime.fromtimestamp(self._state.full_since)
                return None
        
        return {
            zone.config.zone_id: ZoneStateWrapper(zone.state)
            for zone in self.zones
        }
    
    def get_zone_metadata(self, zone_id: int) -> Optional[Dict]:
        """
        Retorna metadata normalizada da zona (modo-específica).

        Usa o mesmo serviço de normalização da API para garantir
        consistência entre o que é salvo no banco e o que é usado
        em runtime.
        """
        zone = next((z for z in self.zones if z.config.zone_id == zone_id), None)
        if not zone:
            return None

        raw_meta = zone.config.metadata or {}
        normalized = normalize_metadata_for_mode(
            mode=zone.config.mode,
            metadata=raw_meta,
        )
        return normalized



