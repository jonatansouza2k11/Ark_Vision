# ============================================================================
# backend/services/vision_system.py v9.4
# Multi-Camera Vision System - Industrial Grade
# Compatível com stream.py v3.1 e camera_sync.py
# ============================================================================
# PRINCIPLES:
# - Determinismo por camera_id
# - Governança rígida de contexto
# - Fail-fast sob erro estrutural
# - Nenhum estado fantasma
# - Ciclo de vida previsível
# - Zero acesso a banco (pure business logic)
# ============================================================================

import asyncio
import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Set, Tuple
from datetime import datetime
import gc
import threading
import time

import numpy as np
import cv2
from ultralytics import YOLO

from backend.api.video import zone_alert_handler 
from backend.core.config.config import settings
from backend.runtime.tracking.appearance_embedder import get_appearance_embedder
from backend.runtime.reid.global_reid_manager import get_global_reid_manager

from backend.runtime.workers.zone_processor_v3 import REID_CAPABLE_TRACKERS, ZoneProcessorV3

USE_SAM3 = False

if TYPE_CHECKING:
    from backend.runtime.workers.camera_worker import CameraWorker
    from backend.runtime.tracking.tracker_manager import get_tracker_manager

logger = logging.getLogger(__name__)


# ============================================================================
# CAMERA CONTEXT
# ============================================================================

class CameraContext:
    def __init__(
        self,
        camera_id: int,
        name: str,
        source: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.camera_id = camera_id
        self.name = name
        self.source = source
        self.username = username
        self.password = password

        self.worker: Optional["CameraWorker"] = None
        self.model: Optional[YOLO] = None

        self.zones: List[dict] = []
        self.metrics: dict = {
            "fps_current": 0.0,
            "fps_avg": 0.0,
            "detected_count": 0,
            "inzone": 0,
            "outzone": 0,
            "active_tracks": 0,
        }

        self.is_running = False
        self.is_paused = False

        self._last_frame_ts: float = 0.0

        # Componentes de processamento YOLO + Zonas
        self.inference_worker: Optional[Any] = None  # InferenceWorker
        self.zone_processor: Optional[Any] = None    # ZoneProcessor
        self.processing_thread: Optional[threading.Thread] = None
        self.processing_active: bool = False
        
        # Track state compartilhado entre threads (para bounding boxes)
        self.track_state: Dict = {}
        self.track_state_lock = threading.Lock()

        # Estado de tracking
        self.trackstate: Dict = {}
        self.trackstatelock = threading.Lock()

        # Tipo de tracker efetivo desta câmera (padrão: ByteTrack YOLO)
        self.tracker_type: str = "yolo_bytetrack"

        # Default da câmera + overrides das zonas; exclui zonas "somente detecção"
        self.required_tracker_types: Set[str] = set()

        # Estado de tracking por tipo de tracker
        # {tracker_type: {track_id: {...}}}
        self.multi_track_state: Dict[str, Dict] = {}

         # Profile de ReID desta câmera (edge/default/high)
        self.reid_profile: str = settings.REID_PROFILE_DEFAULT or "default"

        logger.info(f"📷 CameraContext created: {self.name} (ID: {self.camera_id})")


    def update_metrics(self, **kwargs):
        self.metrics.update(kwargs)

    def get_current_frame(self) -> Optional[np.ndarray]:
        if not self.worker:
            return None
        return self.worker.get_frame()

    #def get_current_frame(self) -> Optional[np.ndarray]:
    #    if not self.worker:
    #        return None

    #    frame = self.worker.get_frame()
    #    if frame is None:
    #        return None

    #    # Snapshot imutável por consumidor
    #    return frame.copy()



# ============================================================================
# VISION SYSTEM (SINGLETON)
# ============================================================================

class VisionSystem:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
            if hasattr(self, "_initialized"):
                return
            self._initialized = True

            self.camera_contexts: Dict[int, CameraContext] = {}
            self.model: Optional[YOLO] = None  # ✅ NÃO carrega ainda
            self.is_running = False
            self._model_loading = False  # ✅ Flag para evitar carregamento paralelo

            logger.info("🔧 VisionSystem initialized (singleton, lazy YOLO loading)")


    def _rebuild_tracker_governance(self, ctx: CameraContext) -> None:
        """
        Decide quais tipos de tracker precisam ser executados para esta câmera.

        Regras:
        - Sempre considera o tracker_default da câmera (ctx.tracker_type).
        - Para cada zona:
        - tracker_override ausente / "inherit" → usa tracker_default (já incluso).
        - "detection_only" / "none" / "off" → não exige tracker (usa só detecção).
        - Qualquer outro valor → adiciona esse tipo ao conjunto.
        """

        required: Set[str] = set()

        # Normaliza o tracker_default da câmera para lowercase
        if ctx.tracker_type:
            ctx.tracker_type = str(ctx.tracker_type).strip().lower()
            required.add(ctx.tracker_type)

        for zone in ctx.zones or []:
            meta = zone.get("metadata") or {}
            override = meta.get("tracker_override")

            # Herda tracker da câmera
            if not override or str(override).strip().lower() in ("inherit", "camera_default"):
                continue

            ov = str(override).strip().lower()

            # Modos "somente detecção" não exigem tracker
            if ov in ("detection_only", "none", "off"):
                continue

            # Usa sempre o nome normalizado
            required.add(ov)

        # Se por algum motivo ficou vazio, volta para o default normalizado
        if not required and ctx.tracker_type:
            required.add(ctx.tracker_type)

        ctx.required_tracker_types = required

        logger.info(
            "🎯 Tracker governance for camera %s: default=%s, required=%s",
            ctx.camera_id,
            ctx.tracker_type,
            sorted(ctx.required_tracker_types),
        )

    # ========================================================================
    # ✅ LAZY LOADING: Carrega YOLO apenas quando necessário
    # ========================================================================
    
    def _get_or_load_yolo_model(self) -> YOLO:
        """
        Lazy loading thread-safe do modelo YOLO.
        Carrega apenas na primeira vez que é solicitado.
        """
        if self.model is not None:
            return self.model
        
        with self._lock:
            # Double-check locking pattern
            if self.model is not None:
                return self.model
            
            if self._model_loading:
                # Aguarda outro thread terminar de carregar
                while self._model_loading:
                    time.sleep(0.1)
                return self.model
            
            try:
                self._model_loading = True
                from ultralytics import __version__ as ulty_ver
                
                model_path = settings.YOLO_MODEL_PATH
                logger.info(f"📦 Lazy loading YOLO model: {model_path} (ultralytics {ulty_ver})")
                
                self.model = YOLO(model_path)
                
                # Warm-up
                dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                _ = self.model(dummy, verbose=False)
                
                logger.info("✅ YOLO model loaded and primed (lazy)")
                return self.model
                
            except Exception as e:
                logger.error(f"❌ Error loading YOLO model: {e}")
                raise
            finally:
                self._model_loading = False

    # ========================================================================
    # INITIALIZATION (SEM YOLO LOADING)
    # ========================================================================

    async def initialize(self, cameras_data: Optional[List[dict]] = None):
            """
            Inicializa VisionSystem sem carregar modelo YOLO.
            YOLO será carregado lazy na primeira vez que uma câmera iniciar.
            """
            try:
                logger.info("🚀 Initializing VisionSystem (lazy YOLO mode)...")
                
                # ❌ NÃO carrega YOLO aqui
                # await self._load_yolo_model()  # REMOVIDO
                
                if cameras_data:
                    await self.load_cameras(cameras_data)

                logger.info(
                    f"✅ VisionSystem initialized with {len(self.camera_contexts)} cameras "
                    "(YOLO will load on first camera start)"
                )
            except Exception as e:
                logger.error(f"❌ Error initializing VisionSystem: {e}")
                raise


    # ========================================================================
    # CAMERA MANAGEMENT
    # ========================================================================

    async def load_cameras(self, cameras_data: List[dict]):
        if not cameras_data:
            logger.warning("⚠️ No cameras provided to load")
            return

        logger.info(f"📷 Loading {len(cameras_data)} cameras...")

        for cam in cameras_data:
            cid = cam["id"]

            # Se a câmera já existe, só atualiza zonas + tracker_type + reid_profile
            if cid in self.camera_contexts:
                ctx = self.camera_contexts[cid]
                ctx.zones = cam.get("zones", [])
                metadata = cam.get("metadata") or {}

                # Atualiza tipo de tracker a partir do metadata da câmera (normalizado)
                tracker_raw = metadata.get("default_tracker", ctx.tracker_type or "yolo_bytetrack")
                ctx.tracker_type = str(tracker_raw).strip().lower()

                # Atualiza perfil de ReID (mantém o atual se não vier no metadata), normalizado
                reid_raw = metadata.get(
                    "reid_profile",
                    getattr(ctx, "reid_profile", settings.REID_PROFILE_DEFAULT or "default"),
                )
                ctx.reid_profile = str(reid_raw).strip().lower()

                # Recalcula governança de trackers dessa câmera
                self._rebuild_tracker_governance(ctx)
                continue

            # Nova câmera
            ctx = CameraContext(
                camera_id=cid,
                name=cam["name"],
                source=cam["source"],
                username=cam.get("username"),
                password=cam.get("password"),
            )

            ctx.zones = cam.get("zones", [])
            metadata = cam.get("metadata") or {}

            tracker_raw = metadata.get("default_tracker", "yolo_bytetrack")
            ctx.tracker_type = str(tracker_raw).strip().lower()

            reid_raw = metadata.get("reid_profile", settings.REID_PROFILE_DEFAULT or "default")
            ctx.reid_profile = str(reid_raw).strip().lower()

            # Governança inicial de trackers por câmera
            self._rebuild_tracker_governance(ctx)

            self.camera_contexts[cid] = ctx

            logger.info(
                f"✅ Camera loaded: {ctx.name} (ID: {cid}, Zones: {len(ctx.zones)})"
            )



    async def reload_cameras(self, cameras_data: List[dict]):
        try:
            new_ids = {c["id"] for c in cameras_data}
            cur_ids = set(self.camera_contexts.keys())

            # Remove orphaned
            for cid in cur_ids - new_ids:
                await self.remove_camera(cid)

            # Add new
            to_add = [c for c in cameras_data if c["id"] not in cur_ids]
            if to_add:
                await self.load_cameras(to_add)

            # Update zones + tracker_type + reid_profile
            for cam in cameras_data:
                cid = cam["id"]
                if cid not in self.camera_contexts:
                    continue

                ctx = self.camera_contexts[cid]
                zones_from_db = cam.get("zones", [])
                ctx.zones = zones_from_db
                metadata = cam.get("metadata") or {}

                # ✅ Atualiza tracker_type conforme metadata atual da câmera (normalizado)
                tracker_raw = metadata.get("default_tracker", ctx.tracker_type or "yolo_bytetrack")
                ctx.tracker_type = str(tracker_raw).strip().lower()

                # ✅ Atualiza reid_profile conforme metadata (com fallback, normalizado)
                reid_raw = metadata.get(
                    "reid_profile",
                    getattr(ctx, "reid_profile", settings.REID_PROFILE_DEFAULT or "default"),
                )
                ctx.reid_profile = str(reid_raw).strip().lower()

                # ✅ Atualiza zone_processor com nova config do DB
                if ctx.zone_processor:
                    ctx.zone_processor.update_zones(zones_from_db)
                    logger.info(
                        f"🔄 ZoneProcessor updated for camera {cid} "
                        f"with {len(zones_from_db)} zones"
                    )

                # Recalcula governança de trackers após reload
                self._rebuild_tracker_governance(ctx)

            logger.info(
                "✅ Reload complete: "
                f"-{len(cur_ids - new_ids)} removed, "
                f"+{len(new_ids - cur_ids)} added, "
                f"{len(cur_ids & new_ids)} updated"
            )

        except Exception as e:
            logger.error(f"❌ Error reloading cameras: {e}")
            raise



    async def remove_camera(self, camera_id: int):
        ctx = self.camera_contexts.get(camera_id)
        if not ctx:
            logger.warning(f"⚠️ Camera {camera_id} not found")
            return

        try:
            if ctx.worker and ctx.worker.is_running:
                ctx.worker.stop()

            del self.camera_contexts[camera_id]
            gc.collect()

            logger.info(f"🗑️ Camera {camera_id} ({ctx.name}) removed")
        except Exception as e:
            logger.error(f"❌ Error removing camera {camera_id}: {e}")

  
    # ========================================================================
    # SYSTEM CONTROL
    # ========================================================================

    async def start(self):
        if self.is_running:
            logger.warning("⚠️ VisionSystem already running")
            return

        if not self.camera_contexts:
            logger.warning("⚠️ No cameras to start")
            return

        logger.info(f"▶️ Starting VisionSystem with {len(self.camera_contexts)} cameras")

        for ctx in self.camera_contexts.values():
            try:
                await self._start_camera(ctx)
            except Exception as e:
                logger.error(f"❌ Error starting camera {ctx.camera_id}: {e}")

        self.is_running = True
        logger.info("✅ VisionSystem started")


    async def _start_camera(self, ctx: CameraContext):
        from backend.runtime.workers.camera_worker import CameraWorker

        source = ctx.source
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        if not ctx.worker:
            def metrics_callback(metrics: dict):
                ctx.update_metrics(**metrics)

            ctx.worker = CameraWorker(
                camera_id=ctx.camera_id,
                source=source,
                name=ctx.name,
                metrics_callback=metrics_callback,
            )

        # ✅ LAZY LOAD: Carrega modelo apenas agora
        ctx.model = self._get_or_load_yolo_model()
        
        # Inicializar processamento YOLO + Zonas
        if ctx.zones:
            from backend.runtime.workers.inference_worker import InferenceWorker
            
            # Cria inference worker (YOLO)
            ctx.inference_worker = InferenceWorker()
            ctx.inference_worker.start()
            
            # SWITCH: v2 (legado) vs v3 (clean architecture)
            if settings.USE_ZONE_PROCESSOR_V3:
                logger.info(f"🆕 Using ZoneProcessorV3 (Clean Architecture) for camera {ctx.camera_id}")
                ctx.zone_processor = ZoneProcessorV3(
                    camera_id=ctx.camera_id,
                    zones_dict=ctx.zones,
                    alert_callback=zone_alert_handler.handle_zone_metrics,
                )
            else:
                from backend.runtime.workers.zone_processor import ZoneProcessor
                logger.info(f"📦 Using ZoneProcessor (Legacy) for camera {ctx.camera_id}")
                ctx.zone_processor = ZoneProcessor(
                    camera_id=ctx.camera_id,
                    zones=ctx.zones
                )

            
            ctx.worker.start()
            ctx.is_running = True

            # Inicia thread de processamento
            ctx.processing_active = True
            ctx.processing_thread = threading.Thread(
                target=self._processing_loop,
                args=(ctx,),
                daemon=True
            )
            ctx.processing_thread.start()
            
            logger.info(
                f"🧠 Processing started: {ctx.name} "
                f"({len(ctx.zones)} zones, YOLO ready)"
            )

        logger.info(f"🎥 Worker started: {ctx.name} (ID: {ctx.camera_id})")


    async def stop(self):
        if not self.is_running:
            logger.warning("⚠️ VisionSystem not running")
            return

        logger.info("⏹️ Stopping VisionSystem...")

        for ctx in self.camera_contexts.values():
            try:
                # Para thread de processamento primeiro
                if ctx.processing_thread and ctx.processing_thread.is_alive():
                    ctx.processing_active = False
                    ctx.processing_thread.join(timeout=2.0)
                
                # Para worker de captura
                if ctx.worker and ctx.worker.is_running:
                    ctx.worker.stop()
                    ctx.is_running = False
                
                # Limpa processadores
                if ctx.inference_worker:
                    ctx.inference_worker.stop()
                    ctx.inference_worker = None
                ctx.zone_processor = None
                
            except Exception as e:
                logger.error(f"❌ Error stopping camera {ctx.camera_id}: {e}")
        
        # Reseta flag global do VisionSystem
        self.is_running = False
        logger.info("✅ VisionSystem stopped")


    async def start_live(self):
        await self.start()


    async def stop_live(self):
        await self.stop()

    
    # ========================================================================
    # STREAM STATE & METRICS
    # ========================================================================

    @property
    def stream_active(self) -> bool:
        return self.is_running

    @property
    def paused(self) -> bool:
        return any(ctx.is_paused for ctx in self.camera_contexts.values())

    @paused.setter
    def paused(self, value: bool):
        for ctx in self.camera_contexts.values():
            ctx.is_paused = value

    @property
    def current_fps(self) -> float:
        vals = [ctx.metrics.get("fps_current", 0.0) for ctx in self.camera_contexts.values() if ctx.is_running]
        return float(sum(vals) / len(vals)) if vals else 0.0

    @property
    def avg_fps(self) -> float:
        vals = [ctx.metrics.get("fps_avg", 0.0) for ctx in self.camera_contexts.values() if ctx.is_running]
        return float(sum(vals) / len(vals)) if vals else 0.0

    @property
    def track_state(self) -> dict:
        return {}
  
    def get_detection_count(self) -> int:
        return int(sum(ctx.metrics.get("detected_count", 0) for ctx in self.camera_contexts.values()))


    # ========================================================================
    # METHODS USED BY stream.py
    # ========================================================================

    def get_status(self, camera_id: int) -> dict:
        ctx = self.camera_contexts.get(camera_id)
        if not ctx:
            return {"error": "Camera not found"}

        return {
            "camera_id": ctx.camera_id,
            "camera_name": ctx.name,
            "fps_current": ctx.metrics.get("fps_current", 0.0),
            "fps_avg": ctx.metrics.get("fps_avg", 0.0),
            "inzone": ctx.metrics.get("inzone", 0),
            "outzone": ctx.metrics.get("outzone", 0),
            "detected_count": ctx.metrics.get("detected_count", 0),
            "system_status": "paused" if ctx.is_paused else "running" if ctx.is_running else "stopped",
            "paused": ctx.is_paused,
            "stream_active": ctx.is_running,
            "zones_loaded": len(ctx.zones),
            "active_tracks": ctx.metrics.get("active_tracks", 0),
            "active_connections": 0,

            # NOVO: governança de tracking/ReID
            "tracker_type": ctx.tracker_type,
            "required_tracker_types": sorted(ctx.required_tracker_types)
                if getattr(ctx, "required_tracker_types", None) else [],
            "reid_profile": getattr(ctx, "reid_profile", None),
        }




    def get_zone_metrics(self, camera_id: int) -> List[Dict]:
        """
        Retorna métricas em tempo real das zonas, garantindo governança de parâmetros.
        ✅ v5.4: Capping at limit - O tempo para de contar ao atingir o parâmetro.
        ✅ v5.5: Inclui count_in, count_out, count_direction do metadata
        ✅ v6.0: Expõe alert/status do ZoneProcessor (sem duplicar regra)
        ✅ v6.1: Expõe KPIs de fila (queue_length, avg_wait_time, max_wait_time, abandon_*)
        """
        ctx = self.camera_contexts.get(camera_id)
        if not ctx or not ctx.zone_processor:
            return []

        metrics: List[Dict] = []
        now = datetime.now()

        # Pode não existir se ainda não processou nenhum frame
        last_zone_metrics = getattr(ctx, "last_zone_metrics", {}) or {}

        for zone_id, state in ctx.zone_processor.zone_states.items():
            # Busca zona correspondente
            zone = next((z for z in ctx.zones if z.get("id") == zone_id), None)
            if not zone:
                continue

            # ✅ GOVERNANÇA: Obter limites configurados no banco
            e_limit = zone.get("empty_timeout", 5.0)
            f_limit = zone.get("full_timeout", 10.0)

            # --- LÓGICA TEMPO VAZIA (CAPPED) ---
            time_empty = 0
            if state.empty_since:
                elapsed = (now - state.empty_since).total_seconds()
                if state.status == "EMPTY":
                    time_empty = int(e_limit)
                else:
                    time_empty = int(elapsed)

            # --- LÓGICA TEMPO CHEIA (CAPPED) ---
            time_full = 0
            if state.full_since:
                elapsed = (now - state.full_since).total_seconds()
                if state.status in ["FULL", "CRITICAL", "ALERT"]:
                    time_full = int(f_limit)
                else:
                    time_full = int(elapsed)

            # ✅ Extrai metadata original
            metadata = zone.get("metadata", {}) or {}

            # ✅ max_capacity para modo Capacity
            max_capacity = None
            if zone.get("mode") == "capacity":
                max_capacity = metadata.get("max_capacity", 50)

            # ✅ Métricas ricas vindas do ZoneProcessor (se já existirem)
            zp_metrics = last_zone_metrics.get(zone_id, {})  # dict retornado por _process_*_mode

            # Fallbacks seguros
            zp_status = zp_metrics.get("status")
            zp_alert = zp_metrics.get("alert", False)
            zp_alert_message = zp_metrics.get("alert_message")
            zp_count_in = zp_metrics.get("count_in")
            zp_count_out = zp_metrics.get("count_out")
            zp_count_direction = zp_metrics.get("count_direction")
            zp_reset_interval = zp_metrics.get("reset_interval")
            zp_last_reset = zp_metrics.get("last_reset")

            # ⬇️ NOVO: KPIs de fila vindos do ZoneProcessor / metadata
            zp_queue_length = zp_metrics.get("queue_length")
            zp_avg_wait_time = zp_metrics.get("avg_wait_time")
            zp_max_wait_time = zp_metrics.get("max_wait_time")
            zp_abandon_count = zp_metrics.get("abandon_count")
            zp_abandon_avg_wait = zp_metrics.get("abandon_avg_wait")
            zp_last_abandon_wait = zp_metrics.get("last_abandon_wait")

            # Monta payload base
            metric: Dict[str, Any] = {
                "zone_id": zone_id,
                "zone_name": zone["name"],
                "mode": zone.get("mode", "occupancy"),
                "current_count": state.object_count,
                "time_empty": time_empty,
                "time_full": time_full,
                # Usa status do processor se disponível, senão o do state
                "state": (zp_status or state.status).lower(),
                "camera_id": zone.get("camera_id"),
                "full_timeout": f_limit,
            }

            # ✅ Campos específicos de COUNTING (sem duplicar lógica)
            if zone.get("mode") == "counting":
                metric["count_in"] = zp_count_in if zp_count_in is not None else metadata.get("count_in", 0)
                metric["count_out"] = zp_count_out if zp_count_out is not None else metadata.get("count_out", 0)
                metric["count_direction"] = (
                    zp_count_direction if zp_count_direction is not None else metadata.get("count_direction", "both")
                )
                metric["reset_interval"] = (
                    zp_reset_interval if zp_reset_interval is not None else metadata.get("reset_interval")
                )
                metric["last_reset"] = zp_last_reset if zp_last_reset is not None else metadata.get("last_reset")

            # ⬇️ NOVO: Campos específicos de QUEUE
            if zone.get("mode") == "queue":
                metric["queue_length"] = (
                    zp_queue_length if zp_queue_length is not None else metadata.get("queue_length", 0)
                )
                metric["avg_wait_time"] = (
                    zp_avg_wait_time if zp_avg_wait_time is not None else metadata.get("avg_wait_time")
                )
                metric["max_wait_time"] = (
                    zp_max_wait_time if zp_max_wait_time is not None else metadata.get("max_wait_time")
                )
                metric["abandon_count"] = (
                    zp_abandon_count if zp_abandon_count is not None else metadata.get("abandon_count", 0)
                )
                metric["abandon_avg_wait"] = (
                    zp_abandon_avg_wait if zp_abandon_avg_wait is not None else metadata.get("abandon_avg_wait")
                )
                metric["last_abandon_wait"] = (
                    zp_last_abandon_wait if zp_last_abandon_wait is not None else metadata.get("last_abandon_wait")
                )

            # Alert sempre disponível no payload
            metric["alert"] = bool(zp_alert)
            metric["alert_message"] = zp_alert_message

            # ✅ Capacity
            if max_capacity is not None:
                metric["max_capacity"] = max_capacity

            metrics.append(metric)

        return metrics



    #def get_zone_metadata_updates(self) -> Dict[int, Dict]:
    #    """
    #    Coleta metadata atualizado de todas as zonas (para persistência externa).
    #    
    #    ✅ v3.9: Retorna dict {zone_id: metadata} para camera_sync.py salvar.
    #    """
    #    metadata_updates = {}
    #    
    #    for ctx in self.camera_contexts.values():
    #        if not ctx.zone_processor:
    #            continue
    #        
    #        for zone in ctx.zones:
    #            zone_id = zone.get("id")
    #            if not zone_id:
    #                continue
    #            
    #            # Apenas para zonas de contagem
    #            if zone.get("mode") != "counting":
    #                continue
    #            
    #            # Metadata atual da zona (em memória)
    #            current_metadata = zone.get("metadata", {})
    #            if not current_metadata:
    #                continue
    #            
    #            # Adiciona à lista de updates
    #            metadata_updates[zone_id] = current_metadata
    #    
    #    return metadata_updates

    def get_zone_metadata_updates(self) -> Dict[int, Dict]:
        """
        Coleta metadata atualizado de todas as zonas (para persistência externa).
        
        ✅ v3.9: Retorna dict {zone_id: metadata} para camera_sync.py salvar.
        ✅ v4.0: Busca metadata do ZoneProcessor (estado atualizado em memória)
        """
        metadata_updates = {}
        
        for ctx in self.camera_contexts.values():
            if not ctx.zone_processor:
                continue
            
            for zone_id in ctx.zone_processor.zone_states.keys():
                zone = next((z for z in ctx.zones if z.get("id") == zone_id), None)
                if not zone:
                    continue
                
                # Apenas para zonas de contagem (outras não têm metadata mutável)
                if zone.get("mode") != "counting":
                    continue
                
                # ✅ Obtém metadata atualizado do processor
                if hasattr(ctx.zone_processor, 'get_zone_metadata'):
                    updated_metadata = ctx.zone_processor.get_zone_metadata(zone_id)
                    if updated_metadata:
                        metadata_updates[zone_id] = updated_metadata
                else:
                    # Fallback seguro: usa metadata atual da zona
                    logger.warning(f"⚠️ ZoneProcessor não tem get_zone_metadata(), usando fallback")
                    current_metadata = zone.get("metadata", {})
                    if current_metadata:
                        metadata_updates[zone_id] = current_metadata
        
        return metadata_updates

    # ========================================================================
    # TRACKING HELPERS (preparado para multi-tracker/ReID)
    # ========================================================================

    def _build_detections_from_yolo(
        self,
        ctx: CameraContext,
        frame: np.ndarray,
        results: Any,
    ) -> List[Dict[str, Any]]:
        """
        Converte o resultado bruto do YOLO em uma lista de detecções normalizadas.
        Cada detecção: {bbox: [x1, y1, x2, y2], class_id, confidence, [feature]}.

        Regras de ReID:
        - Sempre monta detecções básicas (bbox/class/confidence).
        - Só extrai embeddings de aparência (feature) se houver tracker compatível
        com ReID ativo para esta câmera (ctx.required_tracker_types ∩ REID_CAPABLE_TRACKERS).
        """
        detections: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return detections

        boxes = results[0].boxes
        if boxes is None or boxes.data is None or len(boxes.data) == 0:
            return detections

        for det in boxes.data:
            x1, y1, x2, y2, conf, cls = det.cpu().numpy()
            detections.append(
                {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "class_id": int(cls),
                    "confidence": float(conf),
                }
            )

        # Decide se esta câmera precisa de aparência neste frame
        need_appearance = any(
            t in ctx.required_tracker_types
            for t in REID_CAPABLE_TRACKERS
        )

        logger.debug(
            "ReID gating: camera_id=%s tracker_type=%s required=%s need_appearance=%s",
            ctx.camera_id,
            ctx.tracker_type,
            sorted(ctx.required_tracker_types),
            need_appearance,
        )

        if not need_appearance:
            return detections

        # Usa o profile de ReID configurado para a câmera (edge/default/high)
        embedder = get_appearance_embedder(profile=getattr(ctx, "reid_profile", None))
        if embedder is None or not detections:
            return detections

        # Extrai embeddings por detecção e injeta em "feature"
        embeddings = embedder.extract_batch(frame, detections)
        for det, feat in zip(detections, embeddings):
            if feat is not None:
                det["feature"] = feat

        return detections



    def _apply_tracking(
        self,
        ctx: CameraContext,
        detections: List[Dict[str, Any]],
    ) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[int, Dict[str, Any]]]]:
        """
        Aplica tracking em cima das detecções, respeitando governança de trackers por câmera (ctx.required_tracker_types).

        Retorna:
        - track_state_default: estado do tracker default da câmera
        - per_tracker_state: {tracker_type: {track_id: {...}}}
        """
        if not detections:
            return {}, {}

        # Import local para evitar ciclos
        from backend.runtime.tracking.tracker_manager import get_tracker_manager

        tracker_manager = get_tracker_manager()

        # Se por algum motivo ainda não foi calculado, recalcula aqui
        if not getattr(ctx, "required_tracker_types", None):
            self._rebuild_tracker_governance(ctx)

        per_tracker_state: Dict[str, Dict[int, Dict[str, Any]]] = {}

        for tracker_type in ctx.required_tracker_types:
            state = tracker_manager.update(
                camera_id=ctx.camera_id,
                tracker_type=tracker_type,
                detections=detections,
            ) or {}
            per_tracker_state[tracker_type] = state

        # Escolhe o estado default (tracker da câmera), com fallback seguro
        default_state = per_tracker_state.get(ctx.tracker_type)
        if default_state is None and per_tracker_state:
            # fallback: primeiro tracker disponível
            default_state = next(iter(per_tracker_state.values()))

        return default_state or {}, per_tracker_state


    def _build_embeddings_by_track(
        self,
        detections: List[Dict[str, Any]],
        track_state: Dict[int, Dict[str, Any]],
    ) -> Dict[int, np.ndarray]:
        """
        Associa cada track_id ao embedding da detecção mais próxima (maior IoU),
        usando os campos "bbox" de track_state e detecções.

        Retorna: {track_id: embedding_np} apenas para tracks onde existe feature.
        """
        if not detections or not track_state:
            return {}

        # Extrai bboxes e features das detecções
        det_boxes = np.array(
            [det["bbox"] for det in detections],
            dtype=np.float32,
        )
        det_features = [det.get("feature") for det in detections]

        # Se nenhuma detecção tem feature, não há o que fazer
        if not any(feat is not None for feat in det_features):
            return {}

        track_ids = list(track_state.keys())
        track_boxes = np.array(
            [track_state[tid]["bbox"] for tid in track_ids],
            dtype=np.float32,
        )

        # Calcula IoU track x det (T x D)
        if track_boxes.size == 0 or det_boxes.size == 0:
            return {}

        t_x1 = track_boxes[:, 0:1]
        t_y1 = track_boxes[:, 1:2]
        t_x2 = track_boxes[:, 2:3]
        t_y2 = track_boxes[:, 3:4]

        d_x1 = det_boxes[:, 0:1].T
        d_y1 = det_boxes[:, 1:2].T
        d_x2 = det_boxes[:, 2:3].T
        d_y2 = det_boxes[:, 3:4].T

        inter_x1 = np.maximum(t_x1, d_x1)
        inter_y1 = np.maximum(t_y1, d_y1)
        inter_x2 = np.minimum(t_x2, d_x2)
        inter_y2 = np.minimum(t_y2, d_y2)

        inter_w = np.clip(inter_x2 - inter_x1, a_min=0.0, a_max=None)
        inter_h = np.clip(inter_y2 - inter_y1, a_min=0.0, a_max=None)
        inter_area = inter_w * inter_h

        track_area = (t_x2 - t_x1) * (t_y2 - t_y1)
        det_area = (d_x2 - d_x1) * (d_y2 - d_y1)

        union_area = track_area + det_area - inter_area
        iou = np.where(union_area > 0.0, inter_area / union_area, 0.0).astype(
            np.float32
        )

        embeddings_by_track: Dict[int, np.ndarray] = {}

        # Para cada track, pega a detecção com maior IoU e, se tiver feature, usa
        for t_idx, track_id in enumerate(track_ids):
            ious = iou[t_idx]
            if ious.size == 0:
                continue
            det_idx = int(np.argmax(ious))
            feat = det_features[det_idx]
            if feat is not None:
                # Garante np.ndarray float32 1D
                emb = np.asarray(feat, dtype=np.float32).reshape(-1)
                # Normaliza L2 defensivamente
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                embeddings_by_track[track_id] = emb

        return embeddings_by_track


    def _attach_global_ids(
        self,
        ctx: CameraContext,
        detections: List[Dict[str, Any]],
        per_tracker_state: Dict[str, Dict[int, Dict[str, Any]]],
    ) -> Dict[str, Dict[int, int]]:
        """
        Usa o GlobalReIDManager para atribuir global_id a cada track_id
        de cada tracker_type, injetando 'global_id' dentro do track_state.

        Retorna: {tracker_type: {track_id: global_id}}
        """
        if not per_tracker_state or not detections:
            return {}

        reid_manager = get_global_reid_manager()
        per_tracker_global_ids: Dict[str, Dict[int, int]] = {}

        for tracker_type, track_state in per_tracker_state.items():
            if not track_state:
                continue

            # Associa embeddings por track_id (se houver features nas detecções)
            embeddings_by_track = self._build_embeddings_by_track(
                detections, track_state
            )

            # Mesmo sem embeddings, o manager ainda pode reaproveitar histórico
            global_ids = reid_manager.assign_global_ids(
                camera_id=ctx.camera_id,
                tracker_type=tracker_type,
                track_state=track_state,
                embeddings_by_track=embeddings_by_track,
            )

            per_tracker_global_ids[tracker_type] = global_ids

            # Injeta global_id no próprio track_state para consumo downstream
            for track_id, global_id in global_ids.items():
                if track_id in track_state:
                    track_state[track_id]["global_id"] = int(global_id)

            # 🔍 LOG DE DEBUG: resumo de ReID por tracker_type
            if global_ids:
                # Monta alguns exemplos para log (no máx. 5 pares)
                examples = list(global_ids.items())[:5]
                logger.debug(
                    "ReID summary: camera_id=%s tracker_type=%s "
                    "tracks=%d with_global_id=%d examples=%s",
                    ctx.camera_id,
                    tracker_type,
                    len(track_state),
                    len(global_ids),
                    examples,
                )
            else:
                logger.debug(
                    "ReID summary: camera_id=%s tracker_type=%s "
                    "tracks=%d with_global_id=0 (nenhum global_id atribuído)",
                    ctx.camera_id,
                    tracker_type,
                    len(track_state),
                )

        return per_tracker_global_ids



    def _processing_loop(self, ctx: CameraContext):
        """
        Thread de processamento YOLO + Zonas para uma câmera.
        Roda em thread separada para não bloquear captura.
        """
        logger.info(f"🧠 Processing loop started for {ctx.name}")

        # Garante atributo para guardar últimas métricas de zona
        if not hasattr(ctx, "last_zone_metrics"):
            ctx.last_zone_metrics = {}

        # ✅ NOVO: Import do buffer (no topo do arquivo ou aqui inline)
        from backend.runtime.alert.zone_frame_buffer import push_frame

        while ctx.processing_active and ctx.is_running:
            try:
                # Pega frame do worker
                frame = ctx.get_current_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                # Estados de tracking para este frame
                detections: List[Dict[str, Any]] = []
                default_track_state: Dict[int, Dict[str, Any]] = {}
                per_tracker_state: Dict[str, Dict[int, Dict[str, Any]]] = {}

                if ctx.inference_worker and ctx.model:
                    results = ctx.inference_worker.run(frame)

                    # Converte resultado YOLO para detecções normalizadas (+ opcional feature)
                    detections = self._build_detections_from_yolo(ctx, frame, results)

                    if detections:
                        # Aplica multi-tracker de acordo com governança da câmera
                        default_track_state, per_tracker_state = self._apply_tracking(
                            ctx, detections
                        )

                        # Global ReID (atribui global_id por track_id)
                        if per_tracker_state:
                            self._attach_global_ids(
                                ctx=ctx,
                                detections=detections,
                                per_tracker_state=per_tracker_state,
                            )
                            # default_track_state é o mesmo dict que está em per_tracker_state
                            # então já vem enriquecido com global_id quando existir

                # Salva estados de tracking no contexto (thread-safe)
                with ctx.track_state_lock:
                    ctx.track_state = default_track_state or {}
                    ctx.multi_track_state = per_tracker_state or {}

                # Processa zonas (default tracker + detection_only tratadas no ZoneProcessorV3)
                if ctx.zone_processor and (default_track_state or detections):
                    frame_shape = (frame.shape[0], frame.shape[1])

                    zone_metrics = ctx.zone_processor.process_frame(
                        detections=detections,
                        default_track_state=default_track_state,
                        per_tracker_state=per_tracker_state,
                        frame_shape=frame_shape,
                        camera_tracker_type=ctx.tracker_type,
                    )

                    ctx.last_zone_metrics = zone_metrics

                    # Atualiza métricas do context (agregado)
                    total_in_zones = sum(
                        m.get("count", 0) for m in zone_metrics.values()
                    )

                    # detected_count segue a mesma governança dos trackers:
                    # - se há tracker default, conta tracks
                    # - senão, mas há detecções, conta detecções (caso detection_only)
                    if default_track_state:
                        detected_count = len(default_track_state)
                    else:
                        detected_count = len(detections)

                    ctx.update_metrics(
                        detected_count=detected_count,
                        inzone=total_in_zones,
                        outzone=detected_count - total_in_zones,
                        active_tracks=len(default_track_state),
                    )

                # ========================================================================
                # ✅ NOVO: Alimenta buffer de frames para gravação de clipes de alerta
                # ========================================================================
                    buffer_seconds = min(
                        float(getattr(settings, "ALERT_CLIP_PRE_SECONDS", 5.0))
                        + float(getattr(settings, "ALERT_CLIP_POST_SECONDS", 10.0))
                        + 5.0,  # margem de segurança
                        20.0,   # máximo absoluto
                    )
                push_frame(ctx.camera_id, frame, buffer_seconds=buffer_seconds)
                # ========================================================================

                # Throttle: processa a ~10 FPS
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Error in processing loop for {ctx.name}: {e}")
                time.sleep(0.5)

        logger.info(f"🧠 Processing loop stopped for {ctx.name}")



    def generate_frames(self, camera_id: int):
        """
        Generate frames for streaming with zones and bounding boxes overlay.
        """
        ctx = self.camera_contexts.get(camera_id)
        if not ctx:
            raise RuntimeError(f"Camera {camera_id} not registered in VisionSystem")

        if not ctx.worker:
            raise RuntimeError(f"Camera {camera_id} has no worker bound")

        backoff = 0.01
        max_backoff = 0.2

        while True:
            if not ctx.is_running:
                time.sleep(0.05)
                continue

            frame = ctx.get_current_frame()
            if frame is None:
                time.sleep(backoff)
                backoff = min(max_backoff, backoff * 1.5)
                continue

            backoff = 0.01

            # Desenha zonas no frame antes de encodar
            if ctx.zone_processor and ctx.zones:
                try:
                     frame = frame.copy()
                except np.core._exceptions._ArrayMemoryError:
                     logger.error("VisionSystem: MemoryError em frame.copy(); "
                                  "seguindo sem cópia.")
                # Obter track_state atual do contexto (thread-safe)
                with ctx.track_state_lock:
                    track_state = ctx.track_state.copy()
                
                # Desenha zonas com bounding boxes dos objetos
                frame = ctx.zone_processor.draw_zones(frame, track_state=track_state)


            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY])
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )



    # ============================================================================
    # REALOAD CAMERAS FROM DB
    # ============================================================================

    async def reload_from_db(self, cameras_data: List[dict]):
        await self.reload_cameras(cameras_data)



# ============================================================================
# PUBLIC SINGLETON GETTER
# ============================================================================

_vision_system_instance: Optional[VisionSystem] = None


def get_vision_system() -> VisionSystem:
    global _vision_system_instance
    if _vision_system_instance is None:
        _vision_system_instance = VisionSystem()
    return _vision_system_instance
