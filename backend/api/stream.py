"""
============================================================================
backend/api/stream.py v4.0
Stream API - Multi-Camera & YOLO VisionSystem Orchestrator
Compatível VisionSystem v9.3+
============================================================================
RESPONSABILITIES:
- Expor endpoints MJPEG por câmera
- Garantir governança por camera_id
- Controlar lifecycle global do VisionSystem
- Gerenciar conexões por câmera
- Proteger recursos (memória, concorrência)
============================================================================
"""

import logging
import asyncio
import psutil
from datetime import datetime
from typing import Set, Deque, Any, Dict, Optional, List
from functools import lru_cache
from collections import deque, defaultdict
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import (
    get_current_user,
    get_current_admin_user,
    get_current_active_user,
)
from backend.services.vision_system import VisionSystem
from backend.services.camera_sync import sync_vision_system_from_db
from backend.dependencies import get_current_active_user


logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/v1/stream", tags=["Stream"])

MAX_CONCURRENT_STREAMS = getattr(settings, "MAX_CONCURRENT_STREAMS", 3)
MEMORY_PERCENT_THRESHOLD = getattr(settings, "MEMORY_PERCENT_THRESHOLD", 85)
MEMORY_MIN_AVAILABLE_MB = getattr(settings, "MEMORY_MIN_AVAILABLE_MB", 200)

# Governança real
active_streams: Set[str] = set()
streams_by_camera: Dict[int, Set[str]] = defaultdict(set)

stream_events: Deque[Dict[str, Any]] = deque(maxlen=200)

stream_stats = {
    "total_frames": 0,
    "restarts": 0,
    "errors": 0,
    "memory_errors": 0,
}

# ============================================================================ #
# MODELS
# ============================================================================ #

class StreamStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


class EventType(str, Enum):
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    MEMORY_ERROR = "memory_error"


class StreamStatusResponse(BaseModel):
    fps_current: float = 0.0
    fps_avg: float = 0.0
    inzone: int = 0
    outzone: int = 0
    detected_count: int = 0
    system_status: str
    paused: bool
    stream_active: bool
    preset: str
    active_connections: int
    max_connections: int


class CameraStreamStatusResponse(BaseModel):
    camera_id: int
    camera_name: str
    fps_current: float = 0.0
    fps_avg: float = 0.0
    inzone: int = 0
    outzone: int = 0
    detected_count: int = 0
    system_status: str
    paused: bool
    stream_active: bool
    zones_loaded: int
    active_tracks: int
    active_connections: int = 0


class StreamConnectionsInfo(BaseModel):
    active_by_camera: Dict[int, int]
    total_count: int
    limit: int
    memory_status: Dict[str, Any]
    stats: Dict[str, Any]
    recent_events: Any


class StreamControlResponse(BaseModel):
    status: str
    paused: Optional[bool] = None
    message: Optional[str] = None
    cameras: Optional[list[int]] = None


class CameraRuntimeStatus(BaseModel):
    camera_id: int
    name: str
    running: bool
    current_fps: float
    avg_fps: float
    detections_today: int
    active_tracks: int
    zones_loaded: int


class ReloadCamerasResponse(BaseModel):
    status: str
    cameras: list[int]
    message: str

class ZoneUpdateRequest(BaseModel):
    camera_id: int
    zones: List[Dict]  # cada zone pode ser {id, name, coordinates, etc.}
    
# ============================================================================ #
# VISION SYSTEM SINGLETON
# ============================================================================ #

@lru_cache(maxsize=1)
def get_vision_system_cached() -> VisionSystem:
    vs = VisionSystem()
    required_attrs = [
        "start_live", "stop_live", "generate_frames", "stream_active",
        "paused", "current_fps", "avg_fps", "track_state",
        "get_status", "get_detection_count", "camera_contexts"
    ]
    missing = [attr for attr in required_attrs if not hasattr(vs, attr)]
    if missing:
        logger.error("VisionSystem missing attributes: %s", ", ".join(missing))
    return vs


# ============================================================================ #
# HELPERS
# ============================================================================ #

def is_live(vs: VisionSystem) -> bool:
    return bool(vs.stream_active)


def stream_key(request: Request, camera_id: int) -> str:
    ip = request.client.host if request.client else "unknown"
    agent = request.headers.get("user-agent", "n/a")
    return f"{camera_id}:{ip}:{agent}"


def log_event(event_type: EventType, message: str) -> None:
    stream_events.append({
        "type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
    })
    logger.info("%s - %s", event_type.value.upper(), message)


def check_memory_available() -> bool:
    try:
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        if mem.percent >= MEMORY_PERCENT_THRESHOLD:
            return False
        if available_mb <= MEMORY_MIN_AVAILABLE_MB:
            return False
        return True
    except Exception:
        return True


# ============================================================================ #
# VIDEO FEED POR CÂMERA - UNIFICADO
# ============================================================================ #

@router.get(
    "/video_feed/{camera_id}",
    summary="📹 Stream MJPEG por câmera específica"
)
@router.get(
    "/video_feed",
    summary="📹 Stream MJPEG (query/fallback)"
)
#async def video_feed(request: Request, camera_id: Optional[int] = None, current_user: dict = Depends(get_current_active_user)):
async def video_feed(request: Request, camera_id: Optional[int] = None):
    """
    Retorna o stream MJPEG de uma câmera específica.
    - Se `camera_id` não for informado, usa a primeira câmera ativa.
    - Limita número de streams concorrentes.
    - Verifica memória disponível.
    """

    vs: VisionSystem = get_vision_system_cached()

    # fallback para primeira câmera ativa
    if camera_id is None:
        if not vs.camera_contexts:
            raise HTTPException(status_code=404, detail="Nenhuma câmera carregada")
        camera_id = next(iter(vs.camera_contexts.keys()))

    # valida se a câmera existe
    if camera_id not in vs.camera_contexts:
        raise HTTPException(status_code=404, detail="Câmera não carregada no VisionSystem")

    # gera chave única por cliente + câmera
    ip = request.client.host if request.client else "unknown"
    agent = request.headers.get("user-agent", "na")
    skey = f"{camera_id}:{ip}:{agent}"

    # controla limites e memória
    if skey not in active_streams:
        if len(active_streams) >= MAX_CONCURRENT_STREAMS:
            raise HTTPException(status_code=429, detail="Número máximo de streams concorrentes atingido")
        if not check_memory_available():
            stream_stats["memory_errors"] += 1
            raise HTTPException(status_code=507, detail="Memória insuficiente disponível")
        active_streams.add(skey)
        log_event(EventType.STARTED, f"Cliente conectado: {skey}")

    # inicia stream se ainda não estiver ativo
    if not vs.stream_active:
        await vs.start_live()
        await asyncio.sleep(0.2)

    # generator para MJPEG
    def generator():
        try:
            for frame in vs.generate_frames(camera_id=camera_id):
                stream_stats["total_frames"] += 1
                yield frame
        except Exception as e:
            stream_stats["errors"] += 1
            log_event(EventType.ERROR, f"Erro no stream {skey}: {e}")
            raise
        finally:
            active_streams.discard(skey)
            log_event(EventType.STOPPED, f"Cliente desconectado: {skey}")
            # se não há mais consumidores, encerra o pipeline
            if not active_streams and vs.stream_active:
                log_event(EventType.STOPPED, "Nenhum stream ativo. Parando VisionSystem")
                asyncio.run(vs.stop_live())

    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



# ============================================================================ #
# SNAPSHOT POR CÂMERA
# ============================================================================ #

@router.get("/snapshot/{camera_id}", summary="📸 Capturar snapshot de uma câmera específica")
@router.get("/snapshot", summary="📸 Capturar snapshot de uma câmera (query/fallback)")
async def get_snapshot(camera_id: Optional[int] = None, current_user: dict = Depends(get_current_active_user)):
    """
    Captura um snapshot de uma câmera específica. 
    - Se `camera_id` não for informado, usa a primeira câmera ativa como fallback.
    - Garante que o stream esteja ativo e que a câmera exista.
    """
    import cv2

    vs = get_vision_system_cached()

    # fallback para primeira câmera ativa
    if camera_id is None:
        if not vs.camera_contexts:
            raise HTTPException(status_code=404, detail="Nenhuma câmera carregada")
        camera_id = next(iter(vs.camera_contexts.keys()))

    # valida se a câmera existe
    if camera_id not in vs.camera_contexts:
        raise HTTPException(status_code=404, detail="Câmera não carregada no VisionSystem")

    # valida se o stream está ativo
    if not vs.stream_active:
        raise HTTPException(status_code=503, detail="Stream não está ativo")

    # Pega o frame RAW diretamente do context (não do generator)
    ctx = vs.camera_contexts.get(camera_id)
    if not ctx or not ctx.worker:
        raise HTTPException(status_code=503, detail="Worker não disponível")

    frame = ctx.get_current_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Nenhum frame disponível")

    # Encoda em JPEG de alta qualidade
    ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
    if not ret:
        raise HTTPException(status_code=500, detail="Erro ao encodar snapshot")

    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )



# ============================================================================ #
# STATUS GLOBAL E POR CÂMERA
# ============================================================================ #

@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status(current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()

    track_state = getattr(vs, "track_state", {})
    inzone = sum(1 for s in track_state.values() if s.get("status") == "IN")
    outzone = sum(1 for s in track_state.values() if s.get("status") == "OUT")

    return StreamStatusResponse(
        fps_current=round(vs.current_fps, 1),
        fps_avg=round(vs.avg_fps, 1),
        inzone=inzone,
        outzone=outzone,
        detected_count=vs.get_detection_count(),
        system_status=(
            StreamStatus.PAUSED.value
            if vs.paused
            else StreamStatus.RUNNING.value
            if is_live(vs)
            else StreamStatus.STOPPED.value
        ),
        paused=vs.paused,
        stream_active=is_live(vs),
        preset="MEDIUM",
        active_connections=len(active_streams),
        max_connections=MAX_CONCURRENT_STREAMS,
    )


@router.get("/status/{camera_id}", response_model=CameraStreamStatusResponse)
async def get_stream_status_by_camera(camera_id: int, current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()

    if camera_id not in vs.camera_contexts:
        raise HTTPException(status_code=404, detail="Camera não carregada")

    status_dict = vs.get_status(camera_id=camera_id)
    status_dict["active_connections"] = len(streams_by_camera.get(camera_id, []))

    return CameraStreamStatusResponse(**status_dict)


@router.get("/zone_metrics/{camera_id}", summary="Métricas de zonas em tempo real")
async def get_zone_metrics(camera_id: int, current_user: dict = Depends(get_current_user)):
    """
    Retorna métricas em tempo real de todas as zonas de uma câmera.
    
    Usado pelo Dashboard para atualizar tabela de zonas.
    """
    vs = get_vision_system_cached()
    
    if camera_id not in vs.camera_contexts:
        raise HTTPException(status_code=404, detail="Câmera não carregada")
    
    metrics = vs.get_zone_metrics(camera_id)
    
    return metrics

# ============================================================================ #
# LISTA DE CÂMERAS
# ============================================================================ #

@router.get("/cameras", response_model=list[CameraRuntimeStatus])
async def list_stream_cameras(current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()
    cameras: list[CameraRuntimeStatus] = []

    for cid, ctx in vs.camera_contexts.items():
        cameras.append(
            CameraRuntimeStatus(
                camera_id=cid,
                name=ctx.name,
                running=ctx.is_running,
                current_fps=float(ctx.metrics.get("fps_current", 0.0)),
                avg_fps=float(ctx.metrics.get("fps_avg", 0.0)),
                detections_today=int(ctx.metrics.get("detected_count", 0)),
                active_tracks=int(ctx.metrics.get("active_tracks", 0)),
                zones_loaded=len(ctx.zones),
            )
        )

    return cameras




@router.post("/update_zones", summary="Atualiza zonas de uma câmera no VisionSystem")
async def update_camera_zones(req: ZoneUpdateRequest, current_user: dict = Depends(get_current_active_user)):
    """
    Atualiza as zonas de uma câmera específica no VisionSystem.
    - Recebe `camera_id` e lista de `zones`
    - Mantém a governança e estado do VisionSystem
    """
    vs: VisionSystem = get_vision_system_cached()

    ctx = vs.camera_contexts.get(req.camera_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Câmera {req.camera_id} não carregada")

    ctx.zones = req.zones
    return {"status": "ok", "camera_id": req.camera_id, "zones_loaded": len(ctx.zones)}


# ============================================================================ #
# CONTROLE DE STREAM
# ============================================================================ #

@router.post("/start", summary="Start stream")
async def start_stream(current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()

    if is_live(vs):
        return StreamControlResponse(status=StreamStatus.RUNNING.value)

    if not check_memory_available():
        stream_stats["memory_errors"] += 1
        raise HTTPException(status_code=507, detail="Insufficient memory available")

    await vs.start_live()
    stream_stats["restarts"] += 1
    log_event(EventType.STARTED, f"Started by {current_user.get('username')}")

    return StreamControlResponse(
        status=StreamStatus.RUNNING.value,
       paused=False,
       message="Stream started",
   )


@router.post("/pause", summary="Pausar/Retomar stream")
async def toggle_pause_stream(current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()

    if not is_live(vs):
        raise HTTPException(status_code=400, detail="Stream não está ativo")

    vs.paused = not vs.paused
    status_msg = "pausado" if vs.paused else "retomado"

    log_event(
        EventType.STOPPED if vs.paused else EventType.STARTED,
        f"Stream {status_msg} por {current_user.get('username')}",
    )

    return StreamControlResponse(
        status=StreamStatus.PAUSED.value if vs.paused else StreamStatus.RUNNING.value,
        paused=vs.paused,
        message=f"Stream {status_msg}",
    )


@router.post("/stop", summary="Stop stream")
async def stop_stream(current_user: dict = Depends(get_current_user)):
    vs = get_vision_system_cached()

    if not is_live(vs):
        return StreamControlResponse(status=StreamStatus.STOPPED.value)

    await vs.stop_live()
    active_streams.clear()
    streams_by_camera.clear()

    log_event(EventType.STOPPED, f"Stopped by {current_user.get('username')}")

    return StreamControlResponse(
        status=StreamStatus.STOPPED.value,
        paused=False,
        message="Stream stopped",
    )




# ============================================================================ #
# RELOAD DE CÂMERAS
# ============================================================================ #

@router.post("/reload_cameras", summary="Recarregar câmeras do banco")
async def reload_cameras(current_user: dict = Depends(get_current_admin_user)):
    """
    Recarrega TODAS as câmeras ativas do banco de dados no VisionSystem.
    """
    camera_ids = await sync_vision_system_from_db()

    # garante alinhamento de estruturas internas
    for cid in camera_ids:
        streams_by_camera.setdefault(cid, set())

    return ReloadCamerasResponse(
        status="ok",
        cameras=camera_ids,
        message=f"Câmeras recarregadas com sucesso ({len(camera_ids)} carregadas)",
    )


# ============================================================================ #
# CONEXÕES E MÉTRICAS
# ============================================================================ #

@router.get("/connections", response_model=StreamConnectionsInfo)
async def connections(current_user: dict = Depends(get_current_admin_user)):
    vs = get_vision_system_cached()

    active_by_camera: Dict[int, int] = {
        cid: len(streams_by_camera.get(cid, []))
        for cid in vs.camera_contexts.keys()
    }

    mem = psutil.virtual_memory()
    memory_status = {
        "available": mem.available / (1024 * 1024),
        "percent_used": mem.percent,
        "threshold_percent": MEMORY_PERCENT_THRESHOLD,
        "min_available_mb": MEMORY_MIN_AVAILABLE_MB,
        "available_ok": check_memory_available(),
    }

    return StreamConnectionsInfo(
        active_by_camera=active_by_camera,
        total_count=len(active_streams),
        limit=MAX_CONCURRENT_STREAMS,
        memory_status=memory_status,
        stats=stream_stats,
        recent_events=list(stream_events),
    )
