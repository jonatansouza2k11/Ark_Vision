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
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime
import gc
import threading
import time

import numpy as np
import cv2
from ultralytics import YOLO

from backend.config import settings

if TYPE_CHECKING:
    from backend.services.camera_worker import CameraWorker

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
        self.model: Optional[YOLO] = None
        self.is_running = False

        logger.info("🔧 VisionSystem initialized (industrial multi-camera)")

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    async def initialize(self, cameras_data: Optional[List[dict]] = None):
        try:
            logger.info("🚀 Initializing VisionSystem...")
            await self._load_yolo_model()

            if cameras_data:
                await self.load_cameras(cameras_data)

            logger.info(
                f"✅ VisionSystem initialized with {len(self.camera_contexts)} cameras"
            )
        except Exception as e:
            logger.error(f"❌ Error initializing VisionSystem: {e}")
            raise


    async def _load_yolo_model(self):
        try:
            model_path = settings.YOLO_MODEL_PATH
            logger.info(f"📦 Loading YOLO model: {model_path}")
            self.model = YOLO(model_path)

            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy, verbose=False)

            logger.info("✅ YOLO model loaded and primed")
        except Exception as e:
            logger.error(f"❌ Error loading YOLO model: {e}")
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

            if cid in self.camera_contexts:
                self.camera_contexts[cid].zones = cam.get("zones", [])
                continue

            ctx = CameraContext(
                camera_id=cid,
                name=cam["name"],
                source=cam["source"],
                username=cam.get("username"),
                password=cam.get("password"),
            )
            ctx.zones = cam.get("zones", [])
            self.camera_contexts[cid] = ctx

            logger.info(
                f"✅ Camera loaded: {ctx.name} (ID: {cid}, Zones: {len(ctx.zones)})"
            )


    async def reload_cameras(self, cameras_data: List[dict]):
        try:
            #logger.info("🔄 Reloading cameras from DB snapshot...")

            new_ids = {c["id"] for c in cameras_data}
            cur_ids = set(self.camera_contexts.keys())

            # Remove orphaned
            for cid in cur_ids - new_ids:
                await self.remove_camera(cid)

            # Add new
            to_add = [c for c in cameras_data if c["id"] not in cur_ids]
            if to_add:
                await self.load_cameras(to_add)

            # Update zones
            for cam in cameras_data:
                cid = cam["id"]
                if cid in self.camera_contexts:
                    zones_from_db = cam.get("zones", [])
                    self.camera_contexts[cid].zones = zones_from_db
                
                    # ✅ Atualiza zone_processor com nova config do DB
                    if self.camera_contexts[cid].zone_processor:
                        self.camera_contexts[cid].zone_processor.update_zones(zones_from_db)
                        logger.info(f"🔄 ZoneProcessor updated for camera {cid} with {len(zones_from_db)} zones")

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
        from backend.services.camera_worker import CameraWorker

        source = ctx.source
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        if not ctx.worker:
            # Callback para propagar métricas do worker → context
            def metrics_callback(metrics: dict):
                ctx.update_metrics(**metrics)

            ctx.worker = CameraWorker(
                camera_id=ctx.camera_id,
                source=source,
                name=ctx.name,
                metrics_callback=metrics_callback,
            )

        ctx.model = self.model
        
        # ✅ NOVO: Inicializar processamento YOLO + Zonas
        if ctx.zones:
            from backend.services.zone_processor import ZoneProcessor
            from backend.services.inference_worker import InferenceWorker
            
            # Cria inference worker (YOLO)
            ctx.inference_worker = InferenceWorker()
            ctx.inference_worker.start()
            
            # Cria zone processor com zonas injetadas
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
                # ✅ Para thread de processamento primeiro
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
        
        # ✅ CRÍTICO: Reseta flag global do VisionSystem
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
        }



    def get_zone_metrics(self, camera_id: int) -> List[Dict]:
        """
        Retorna métricas em tempo real das zonas, garantindo governança de parâmetros.
        ✅ v5.4: Capping at limit - O tempo para de contar ao atingir o parâmetro.
        ✅ v5.5: Inclui count_in, count_out, count_direction do metadata
        ✅ v6.0: Expõe alert/status do ZoneProcessor (sem duplicar regra)
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
                metric["count_direction"] = zp_count_direction if zp_count_direction is not None else metadata.get("count_direction", "both")
                metric["reset_interval"] = zp_reset_interval if zp_reset_interval is not None else metadata.get("reset_interval")
                metric["last_reset"] = zp_last_reset if zp_last_reset is not None else metadata.get("last_reset")
                metric["alert"] = bool(zp_alert)
                metric["alert_message"] = zp_alert_message

            # ✅ Capacity
            if max_capacity is not None:
                metric["max_capacity"] = max_capacity

            metrics.append(metric)

        return metrics





    def get_zone_metadata_updates(self) -> Dict[int, Dict]:
        """
        Coleta metadata atualizado de todas as zonas (para persistência externa).
        
        ✅ v3.9: Retorna dict {zone_id: metadata} para camera_sync.py salvar.
        """
        metadata_updates = {}
        
        for ctx in self.camera_contexts.values():
            if not ctx.zone_processor:
                continue
            
            for zone in ctx.zones:
                zone_id = zone.get("id")
                if not zone_id:
                    continue
                
                # Apenas para zonas de contagem
                if zone.get("mode") != "counting":
                    continue
                
                # Metadata atual da zona (em memória)
                current_metadata = zone.get("metadata", {})
                if not current_metadata:
                    continue
                
                # Adiciona à lista de updates
                metadata_updates[zone_id] = current_metadata
        
        return metadata_updates




    def _processing_loop(self, ctx: CameraContext):
        """
        Thread de processamento YOLO + Zonas para uma câmera.

        Roda em thread separada para não bloquear captura.
        """
        logger.info(f"🧠 Processing loop started for {ctx.name}")

        # ✅ Garante atributo para guardar últimas métricas de zona
        if not hasattr(ctx, "last_zone_metrics"):
            ctx.last_zone_metrics = {}

        while ctx.processing_active and ctx.is_running:
            try:
                # Pega frame do worker
                frame = ctx.get_current_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                # Aplica YOLO
                if ctx.inference_worker and ctx.model:
                    results = ctx.inference_worker.run(frame)

                    if results and len(results) > 0:
                        # Atualiza track_state com detecções
                        track_state = {}
                        for idx, det in enumerate(results[0].boxes.data):
                            x1, y1, x2, y2, conf, cls = det.cpu().numpy()
                            track_state[idx] = {
                                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                                "class_id": int(cls),
                                "confidence": float(conf),
                            }

                        # ✅ Salva track_state no contexto (thread-safe)
                        with ctx.track_state_lock:
                            ctx.track_state = track_state

                        # Processa zonas
                        if ctx.zone_processor and track_state:
                            frame_shape = (frame.shape[0], frame.shape[1])
                            zone_metrics = ctx.zone_processor.process_frame(
                                detections=[],
                                track_state=track_state,
                                frame_shape=frame_shape,
                            )

                            # ✅ Salva últimas métricas de zona no contexto
                            ctx.last_zone_metrics = zone_metrics

                            # Atualiza métricas do context (agregado)
                            total_in_zones = sum(
                                m.get("count", 0) for m in zone_metrics.values()
                            )

                            ctx.update_metrics(
                                detected_count=len(track_state),
                                inzone=total_in_zones,
                                outzone=len(track_state) - total_in_zones,
                                active_tracks=len(track_state),
                            )

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
                frame = frame.copy()  # Cópia para evitar race condition e evita piscância no stream
                
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
