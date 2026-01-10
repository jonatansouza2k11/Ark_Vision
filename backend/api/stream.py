# ===================================================================
# backend/api/stream.py
# CORRIGIDO E OTIMIZADO v4.8
# - Compatível com VisionSystem antigo e novo
# - Suporte Multi-Câmeras
# - FPS unificado
# - Tracking robusto
# - Limite de streams e memória industrial
# - Mantém contratos com frontend
# ===================================================================

import logging
import asyncio
import psutil
from datetime import datetime
from typing import Set
from functools import lru_cache
from enum import Enum
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import get_current_user, get_current_admin_user
from backend.services.vision_system import VisionSystem
from backend.yolo import get_vision_system

logger = logging.getLogger("uvicorn")

# ====================================================================
# ROUTER
# ====================================================================
router = APIRouter(prefix="/api/v1/stream", tags=["YOLO Stream"])

# ====================================================================
# ENV SAFE CONFIG
# ====================================================================
MAX_CONCURRENT_STREAMS = getattr(settings, "MAX_CONCURRENT_STREAMS", 3)
MEMORY_PERCENT_THRESHOLD = getattr(settings, "MEMORY_PERCENT_THRESHOLD", 85)
MEMORY_MIN_AVAILABLE_MB = getattr(settings, "MEMORY_MIN_AVAILABLE_MB", 200)

# ====================================================================
# STATE
# ====================================================================
active_streams: Set[str] = set()
stream_events = deque(maxlen=100)
stream_stats = {
    "total_frames": 0,
    "restarts": 0,
    "errors": 0,
    "memory_errors": 0,
}

# ====================================================================
# ENUMS
# ====================================================================
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

# ====================================================================
# MODELS
# ====================================================================
class StreamStatusResponse(BaseModel):
    fps_current: float = 0.0
    fps_avg: float = 0.0
    fpsavg: float = 0.0
    inzone: int
    outzone: int
    detected_count: int
    system_status: str
    paused: bool
    stream_active: bool
    preset: str
    active_connections: int
    max_connections: int

# ====================================================================
# HELPERS
# ====================================================================
@lru_cache(maxsize=1)
def _get_vision_system_cached():
    vs = get_vision_system()
    required_attrs = [
        "start_live", "stop_live",
        "generate_frames", "track_state",
        "stream_active", "paused",
        "current_fps", "avg_fps",
    ]
    for attr in required_attrs:
        if not hasattr(vs, attr):
            raise RuntimeError(f"VisionSystem missing attribute: {attr}")
    return vs

def _is_live(vs) -> bool:
    """
    Compatibilidade com VisionSystem antigo e novo.
    Aceita is_live como método ou property.
    """
    attr = getattr(vs, "is_live", None)
    if callable(attr):
        return attr()
    if attr is not None:
        return bool(attr)
    return bool(getattr(vs, "stream_active", False))

def _stream_key(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    agent = request.headers.get("user-agent", "na")
    return f"{ip}:{agent}"

def log_event(event_type: EventType, message: str):
    stream_events.append({
        "type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
    })
    logger.info(f"📝 {event_type.value.upper()} - {message}")

def check_memory_available() -> bool:
    try:
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        if mem.percent > MEMORY_PERCENT_THRESHOLD:
            return False
        if available_mb < MEMORY_MIN_AVAILABLE_MB:
            return False
        return True
    except Exception:
        return True

# ====================================================================
# VIDEO STREAM (MJPEG)
# ====================================================================
@router.get("/video_feed", summary="📹 Stream MJPEG")
async def video_feed(request: Request):
    stream_key = _stream_key(request)

    if stream_key not in active_streams:
        if len(active_streams) >= MAX_CONCURRENT_STREAMS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum concurrent streams reached"
            )
        if not check_memory_available():
            stream_stats["memory_errors"] += 1
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail="Insufficient memory available"
            )
        active_streams.add(stream_key)
        log_event(EventType.STARTED, f"Client connected: {stream_key}")

    vs = _get_vision_system_cached()
    if not _is_live(vs):
        vs.start_live()
        await asyncio.sleep(0.3)

    def generator():
        try:
            for frame in vs.generate_frames():
                stream_stats["total_frames"] += 1
                yield frame
        except Exception as e:
            stream_stats["errors"] += 1
            logger.error(f"❌ Stream error {stream_key}: {e}")
            raise
        finally:
            active_streams.discard(stream_key)
            log_event(EventType.STOPPED, f"Client disconnected: {stream_key}")

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

# ====================================================================
# STREAM CONTROL
# ====================================================================
@router.post("/start", summary="▶️ Start stream")
async def start_stream(current_user: dict = Depends(get_current_user)):
    vs = _get_vision_system_cached()
    if _is_live(vs):
        return {"status": StreamStatus.RUNNING.value}
    if not check_memory_available():
        stream_stats["memory_errors"] += 1
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Insufficient memory available"
        )
    vs.start_live()
    stream_stats["restarts"] += 1
    log_event(EventType.STARTED, f"Started by {current_user.get('username')}")
    return {"status": StreamStatus.RUNNING.value}

@router.post("/stop", summary="⏹️ Stop stream")
async def stop_stream(current_user: dict = Depends(get_current_user)):
    vs = _get_vision_system_cached()
    if not _is_live(vs):
        return {"status": StreamStatus.STOPPED.value}
    vs.stop_live()
    active_streams.clear()
    log_event(EventType.STOPPED, f"Stopped by {current_user.get('username')}")
    return {"status": StreamStatus.STOPPED.value}

# ====================================================================
# STATUS
# ====================================================================
@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status(current_user: dict = Depends(get_current_user)):
    vs = _get_vision_system_cached()
    track_state = vs.track_state or {}
    in_zone = sum(1 for s in track_state.values() if s.get("status") == "IN")
    out_zone = sum(1 for s in track_state.values() if s.get("status") == "OUT")

    return StreamStatusResponse(
        fps_current=round(vs.current_fps, 1),
        fps_avg=round(vs.avg_fps, 1),
        fpsavg=round(vs.avg_fps, 1),
        inzone=in_zone,
        outzone=out_zone,
        detected_count=vs.get_detection_count(),
        system_status=(
            StreamStatus.PAUSED.value if vs.paused
            else StreamStatus.RUNNING.value if _is_live(vs)
            else StreamStatus.STOPPED.value
        ),
        paused=vs.paused,
        stream_active=_is_live(vs),
        preset="MEDIUM",
        active_connections=len(active_streams),
        max_connections=MAX_CONCURRENT_STREAMS,
    )

# ====================================================================
# CONNECTIONS (ADMIN)
# ====================================================================
@router.get("/connections")
async def connections(current_user: dict = Depends(get_current_admin_user)):
    return {
        "active": list(active_streams),
        "count": len(active_streams),
        "limit": MAX_CONCURRENT_STREAMS,
    }
