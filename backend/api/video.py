"""
============================================================================
backend/api/video.py - v3.1 (Alert Clips + Buffer)

Video Streaming Routes (YOLO Real-time Detection) + Alert Clip Recording
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

import sys
from pathlib import Path

from backend.runtime.workers.metrics import FPSMeter

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from enum import Enum
import threading
from queue import Queue, Empty
from typing import Optional, Dict, Any, List, Generator, Deque, Tuple

import cv2
import numpy as np
import io
from PIL import Image

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    Query,
)
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
from psycopg_pool import AsyncConnectionPool

from backend.core.config.config import settings
from backend.application.alert.zone_alert_handler import ZoneAlertHandler
from backend.runtime.alert.zone_clip_recorder import vision_clip_recorder

from backend.adapters.storage.database import get_db_pool
from dependencies import get_current_user, get_current_admin_user, limiter


# Try to import YOLO detector
try:
    from backend.adapters.vision.yolo import YOLODetector
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("⚠️ YOLO module not available. Using mock detector.")

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

router = APIRouter(prefix="/api/v1/video", tags=["Video Streaming"])
logger = logging.getLogger("uvicorn")

# Global stream manager
active_streams: Dict[str, "VideoStream"] = {}
stream_lock = threading.Lock()


# Base path para vídeos de ocorrência de alerta
ALERT_BASE_PATH = settings.BASE_DIR / settings.ALERT_VIDEO_PATH
# Durações fixas dos clipes de alerta (ex.: 5s antes + 10s depois)
ALERT_CLIP_PRE_SEC = settings.ALERT_CLIP_PRE_SECONDS
ALERT_CLIP_POST_SEC = settings.ALERT_CLIP_POST_SECONDS
# Aliases governados para configurações de clipe
ALERT_CLIP_FPS: int = settings.ALERT_CLIP_FPS
BUFFER_DURATION_SECONDS: float = settings.BUFFER_DURATION_SECONDS
MAX_FRAMES_PER_CAMERA: float = settings.MAX_FRAMES_PER_CAMERA

# ----------------------------------------------------------------------
# Zone alert → gravação automática de clipe + dispatch de evento
# ----------------------------------------------------------------------


def _get_stream_for_camera(camera_id: int) -> Optional["VideoStream"]:
    """
    Resolve camera_id → VideoStream ativo.

    Aqui assumimos que o stream_id == camera_id (ex.: "1", "2"...).
    Se você usar outro naming para stream_id, adapte este resolver.
    """
    stream_id = str(camera_id)
    with stream_lock:
        return active_streams.get(stream_id)


def clip_recorder_impl(
    camera_id: int,
    zone_id: int,
    metrics: Dict[str, Any],
    event_time: float,
) -> Optional[str]:
    """
    Grava automaticamente um clipe com buffer pré/pós quando a zona entra em alerta.

    Usa:
    - ALERT_CLIP_PRE_SEC: segundos antes do evento (via buffer em memória)
    - ALERT_CLIP_POST_SEC: segundos depois do evento (gravação em tempo real)

    Retorna o caminho do arquivo de vídeo para usar como videopath.
    """
    stream = _get_stream_for_camera(camera_id)
    if not stream:
        logger.warning(
            "clip_recorder_impl: nenhum stream ativo encontrado para camera_id=%s",
            camera_id,
        )
        return None

    pre_sec = float(ALERT_CLIP_PRE_SEC)
    post_sec = float(ALERT_CLIP_POST_SEC)

    ts_str = datetime.fromtimestamp(event_time).strftime("%Y%m%d%H%M%S")
    filename = f"alert_cam{camera_id}_zone{zone_id}_{ts_str}.mp4"

    # Garante diretório
    ALERT_BASE_PATH.mkdir(parents=True, exist_ok=True)
    filepath = ALERT_BASE_PATH / filename

    # Abrir VideoWriter manualmente para conseguir escrever frames do buffer + futuros
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(
            str(filepath),
            fourcc,
            stream.target_fps,
            (stream.target_width, stream.target_height),
        )
        if not vw.isOpened():
            raise RuntimeError("Failed to open alert clip VideoWriter")
    except Exception as e:
        logger.error(
            "clip_recorder_impl: falha ao preparar VideoWriter para alerta "
            "(camera_id=%s, zone_id=%s, filename=%s, error=%s)",
            camera_id,
            zone_id,
            filename,
            e,
        )
        return None

    # 1) Dump do buffer pré-alerta
    with stream.latest_frame_lock:
        buffer_copy = list(stream.alert_buffer)

    pre_start_ts = event_time - pre_sec
    pre_frames = 0
    for ts, frame in buffer_copy:
        if ts >= pre_start_ts:
            vw.write(frame)
            pre_frames += 1

    logger.info(
        "clip_recorder_impl: wrote %d pre-alert frames (camera_id=%s, zone_id=%s)",
        pre_frames,
        camera_id,
        zone_id,
    )

    # 2) Gravação pós-alerta em background
    def _record_post() -> None:
        try:
            end_time = time.time() + post_sec
            while time.time() < end_time:
                with stream.latest_frame_lock:
                    frame = (
                        stream.latest_frame.copy()
                        if stream.latest_frame is not None
                        else None
                    )
                if frame is not None:
                    vw.write(frame)
                time.sleep(1.0 / max(stream.target_fps, 1))
        except Exception:
            logger.exception(
                "clip_recorder_impl: erro durante gravação pós-alerta "
                "(camera_id=%s, zone_id=%s)",
                camera_id,
                zone_id,
            )
        finally:
            vw.release()
            logger.info(
                "clip_recorder_impl: clipe de alerta finalizado "
                "(camera_id=%s, zone_id=%s, file=%s)",
                camera_id,
                zone_id,
                filepath,
            )

    threading.Thread(target=_record_post, daemon=True).start()
    return str(filepath)



def alert_sink_impl(event: Dict[str, Any]) -> None:
    """
    Sink para o evento de alerta de zona.

    Por enquanto só faz logging. Depois você pode trocar para:
    - chamar um serviço de Alert (API interna) e criar um registro no DB
    - publicar o evento em uma fila (Rabbit/Kafka/etc.)
    """
    logger.warning(
        "Zone ALERT event: camera_id=%s zone_id=%s status=%s count=%s videopath=%s",
        event.get("camera_id"),
        event.get("zone_id"),
        event.get("status"),
        event.get("count"),
        event.get("videopath"),
    )
    # TODO: plugar serviço de Alert/DB aqui (ex.: criar AlertCreate específico de zona).


# Instância global do handler, usada por todos os processors de zonas
zone_alert_handler = ZoneAlertHandler(
    clip_recorder=vision_clip_recorder,
    alert_sink=alert_sink_impl,  # continua o mesmo por enquanto
)



# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================


class VideoSource(str, Enum):
    """Video source types"""

    WEBCAM = "webcam"
    RTSP = "rtsp"
    FILE = "file"
    URL = "url"
    IP_CAMERA = "ip_camera"


class StreamState(str, Enum):
    """Stream states"""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class VideoQuality(str, Enum):
    """Video quality presets"""

    LOW = "low"  # 480p, 15fps
    MEDIUM = "medium"  # 720p, 24fps
    HIGH = "high"  # 1080p, 30fps
    ULTRA = "ultra"  # 4K, 30fps


class RecordingFormat(str, Enum):
    """Recording formats"""

    MP4 = "mp4"
    AVI = "avi"
    MKV = "mkv"


# Quality presets
QUALITY_PRESETS = {
    VideoQuality.LOW: {"width": 640, "height": 480, "fps": 15},
    VideoQuality.MEDIUM: {"width": 1280, "height": 720, "fps": 24},
    VideoQuality.HIGH: {"width": 1920, "height": 1080, "fps": 30},
    VideoQuality.ULTRA: {"width": 3840, "height": 2160, "fps": 30},
}

# ============================================================================
# PYDANTIC MODELS v2.0 (Compatible)
# ============================================================================


class VideoSourceInfo(BaseModel):
    """Video source information"""

    id: str
    type: VideoSource
    name: str
    path: Optional[str] = None
    available: bool
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None


class VideoStatusResponse(BaseModel):
    """Video status response (v2.0 compatible)"""

    status: str
    source: str
    fps: float
    uptime: Optional[float] = None
    frame_count: Optional[int] = None


# ============================================================================
# PYDANTIC MODELS v3.0 (NEW)
# ============================================================================


class StreamStartRequest(BaseModel):
    """Start stream request"""

    source_type: VideoSource
    source_path: Optional[str] = Field(
        None, description="Path for file/RTSP/URL sources"
    )
    device_id: Optional[int] = Field(
        0, description="Device ID for webcam"
    )
    enable_detection: bool = Field(
        True, description="Enable YOLO detection"
    )
    enable_tracking: bool = Field(
        True, description="Enable object tracking"
    )
    quality: VideoQuality = VideoQuality.MEDIUM

    @validator("source_path")
    def validate_source_path(cls, v, values):
        source_type = values.get("source_type")
        if source_type in [
            VideoSource.FILE,
            VideoSource.RTSP,
            VideoSource.URL,
            VideoSource.IP_CAMERA,
        ]:
            if not v:
                raise ValueError(
                    f"source_path is required for {source_type}"
                )
        return v


class StreamSettingsRequest(BaseModel):
    """Stream settings update"""

    fps: Optional[int] = Field(None, ge=1, le=60)
    width: Optional[int] = Field(None, ge=320, le=3840)
    height: Optional[int] = Field(None, ge=240, le=2160)
    quality: Optional[VideoQuality] = None
    enable_detection: Optional[bool] = None
    enable_tracking: Optional[bool] = None
    detection_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0
    )


class StreamMetrics(BaseModel):
    """Stream performance metrics"""

    stream_id: str
    state: StreamState
    fps_current: float
    fps_target: float
    frame_count: int
    dropped_frames: int
    processing_time_ms: float
    memory_usage_mb: float
    uptime_seconds: float
    source_info: Dict[str, Any]
    detection_stats: Optional[Dict[str, Any]] = None
    timestamp: datetime


class RecordingStartRequest(BaseModel):
    """Start recording request"""

    filename: Optional[str] = None
    format: RecordingFormat = RecordingFormat.MP4
    duration_seconds: Optional[int] = Field(
        None, ge=1, description="Auto-stop after duration"
    )


class RecordingInfo(BaseModel):
    """Recording information"""

    recording: bool
    filename: Optional[str] = None
    duration_seconds: float
    size_mb: float
    frame_count: int
    started_at: Optional[datetime] = None


class SnapshotRequest(BaseModel):
    """Snapshot capture request"""

    include_detections: bool = Field(
        True, description="Include YOLO detections"
    )
    format: str = Field("jpg", description="Image format (jpg, png)")


# ============================================================================
# VIDEO STREAM CLASS
# ============================================================================


class VideoStream:
    """
    Video stream handler with YOLO detection
    Manages video capture, processing, streaming and alert clips
    """

    def __init__(
        self,
        stream_id: str,
        source_type: VideoSource,
        source_path: Optional[str] = None,
        device_id: int = 0,
        enable_detection: bool = True,
        enable_tracking: bool = True,
        quality: VideoQuality = VideoQuality.MEDIUM,
    ):
        self.stream_id = stream_id
        self.source_type = source_type
        self.source_path = source_path
        self.device_id = device_id
        self.enable_detection = enable_detection
        self.enable_tracking = enable_tracking
        self.quality = quality

        # Stream state
        self.state = StreamState.IDLE
        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.paused = False

        # Frame buffer para MJPEG
        self.frame_queue: "Queue[np.ndarray]" = Queue(maxsize=10)
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_frame_lock = threading.Lock()

        # Buffer circular simples (frame + timestamp) – ainda usado em clip_recorder_impl
        self.alert_buffer: Deque[Tuple[float, np.ndarray]] = deque()
        self.alert_buffer_max_seconds = float(settings.ALERT_CLIP_PRE_SECONDS)

        # Metrics
        self.frame_count = 0
        self.dropped_frames = 0
        self.start_time: Optional[float] = None
        self.fps_current: float = 0.0
        self.processing_times: List[float] = []

        # Quality settings (precisa vir ANTES do FPSMeter)
        preset = QUALITY_PRESETS[quality]
        self.target_width = preset["width"]
        self.target_height = preset["height"]
        self.target_fps = preset["fps"]

        # Medidor governado de FPS (janela baseada no target_fps)
        window = int(self.target_fps * 4) if self.target_fps > 0 else 60
        self.fps_meter = FPSMeter(window=window)

        # Número máximo de frames aproximado para o buffer de alerta simples
        self.alert_buffer_max_frames = int(
            self.target_fps * self.alert_buffer_max_seconds
        ) or 1

        # YOLO detector
        self.detector = None
        if enable_detection and YOLO_AVAILABLE:
            try:
                self.detector = YOLODetector()
                logger.info(f"✅ YOLO detector loaded for stream {stream_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load YOLO detector: {e}")

        # Recording contínua
        self.recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_start_time: Optional[float] = None
        self.recording_frame_count = 0
        self.recording_filename: Optional[str] = None

        # =====================================================================
        # Buffer de frames para clipes de alerta (OTIMIZADO COM COMPRESSÃO JPEG)
        # =====================================================================

        min_required_buffer = (
            ALERT_CLIP_PRE_SEC + ALERT_CLIP_POST_SEC + 5.0  # margem extra
        )
        configured_buffer = float(getattr(settings, "BUFFER_DURATION_SECONDS", 30.0))
        self.buffer_duration_seconds = max(configured_buffer, min_required_buffer)

        # Capacidade em frames
        max_buffer_frames = int(self.target_fps * self.buffer_duration_seconds)

        # Estimativa de memória (JPEG ~80 KB/frame)
        estimated_memory_mb = max_buffer_frames * 0.08

        logger.info(
            f"📦 Stream {self.stream_id}: Alert buffer config:\n"
            f"   Duration: {self.buffer_duration_seconds:.1f}s "
            f"({max_buffer_frames} frames @ {self.target_fps} FPS)\n"
            f"   Clips: {ALERT_CLIP_PRE_SEC:.1f}s PRE + "
            f"{ALERT_CLIP_POST_SEC:.1f}s POST\n"
            f"   Estimated RAM: ~{estimated_memory_mb:.1f} MiB (JPEG compressed)"
        )

        # Buffer armazena: (timestamp, frame_jpeg_bytes)
        self.frame_buffer: Deque[Tuple[float, bytes]] = deque(
            maxlen=max_buffer_frames
        )

        # Estado da gravação de clipe de alerta
        self.alert_clip_writer: Optional[cv2.VideoWriter] = None
        self.alert_clip_end_time: float = 0.0
        self.alert_clip_filename: Optional[str] = None
        self.alert_clip_active: bool = False


    # --------------------------------------------------------------------- #
    # CONTROLE DE STREAM
    # --------------------------------------------------------------------- #

    def start(self) -> bool:
        """Start video stream"""
        if self.state != StreamState.IDLE:
            logger.warning(
                f"⚠️ Stream {self.stream_id} already started"
            )
            return False

        self.state = StreamState.STARTING
        try:
            # Open video source
            if self.source_type == VideoSource.WEBCAM:
                self.cap = cv2.VideoCapture(self.device_id)
            elif self.source_type in [
                VideoSource.FILE,
                VideoSource.RTSP,
                VideoSource.URL,
                VideoSource.IP_CAMERA,
            ]:
                self.cap = cv2.VideoCapture(self.source_path)
            else:
                raise ValueError(
                    f"Unsupported source type: {self.source_type}"
                )

            if not self.cap or not self.cap.isOpened():
                raise RuntimeError("Failed to open video source")

            # Set resolution
            self.cap.set(
                cv2.CAP_PROP_FRAME_WIDTH, self.target_width
            )
            self.cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT, self.target_height
            )
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Start capture thread
            self.running = True
            self.start_time = time.time()
            self.thread = threading.Thread(
                target=self._capture_loop, daemon=True
            )
            self.thread.start()

            self.state = StreamState.RUNNING
            logger.info(
                f"✅ Stream {self.stream_id} started: "
                f"{self.source_type}"
            )
            return True

        except Exception as e:
            self.state = StreamState.ERROR
            logger.error(
                f"❌ Failed to start stream {self.stream_id}: {e}"
            )
            if self.cap:
                self.cap.release()
                self.cap = None
            return False

    def stop(self):
        """Stop video stream"""
        self.running = False
        self.state = StreamState.STOPPING

        # Stop recording if active
        if self.recording:
            self.stop_recording()

        # Finalizar clipe de alerta se ativo
        if self.alert_clip_active and self.alert_clip_writer:
            try:
                self.alert_clip_writer.release()
            except Exception:
                pass
            self.alert_clip_writer = None
            self.alert_clip_active = False
            logger.info(
                f"⏹️ Alert clip forcibly closed for {self.stream_id}"
            )

        # Wait for thread
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        # Release resources
        if self.cap:
            self.cap.release()
            self.cap = None

        self.state = StreamState.IDLE
        logger.info(f"🛑 Stream {self.stream_id} stopped")

    def pause(self):
        """Pause stream"""
        if self.state == StreamState.RUNNING:
            self.paused = True
            self.state = StreamState.PAUSED
            logger.info(f"⏸️ Stream {self.stream_id} paused")

    def resume(self):
        """Resume stream"""
        if self.state == StreamState.PAUSED:
            self.paused = False
            self.state = StreamState.RUNNING
            logger.info(f"▶️ Stream {self.stream_id} resumed")

    # --------------------------------------------------------------------- #
    # LOOP DE CAPTURA
    # --------------------------------------------------------------------- #

    def _capture_loop(self):
        """Main capture loop"""
        frame_interval = 1.0 / max(self.target_fps, 1)
        last_frame_time = 0.0

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            # Frame rate control
            now = time.time()
            if now - last_frame_time < frame_interval:
                time.sleep(0.001)
                continue
            last_frame_time = now

            # Capture frame
            ret, frame = self.cap.read() if self.cap else (False, None)
            if not ret or frame is None:
                logger.warning(
                    f"⚠️ Failed to read frame from stream {self.stream_id}"
                )
                if self.source_type == VideoSource.FILE and self.cap:
                    # Loop video file
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Process frame
            process_start = time.time()
            processed_frame = self._process_frame(frame)
            process_time = (time.time() - process_start) * 1000.0

            # Atualiza métricas
            self.frame_count += 1
            self.processing_times.append(process_time)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)

            # FPS governado (FPSMeter)
            fps_inst = self.fps_meter.tick()
            self.fps_current = fps_inst
            self.fps_avg = self.fps_meter.average()

            # Atualiza buffer simples de alerta (frame + timestamp real)
            now_ts = time.time()
            self.alert_buffer.append((now_ts, processed_frame.copy()))
            # Remover por tempo
            while (
                self.alert_buffer
                and (now_ts - self.alert_buffer[0][0]) > self.alert_buffer_max_seconds
            ):
                self.alert_buffer.popleft()
            # Blindagem por número de frames
            while len(self.alert_buffer) > self.alert_buffer_max_frames:
                self.alert_buffer.popleft()

            # Buffer comprimido para clipe (JPEG)
            try:
                ret_jpeg, buffer = cv2.imencode(
                    ".jpg",
                    processed_frame,
                    [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY],
                )
                if ret_jpeg:
                    frame_jpeg_bytes = buffer.tobytes()
                    self.frame_buffer.append((now_ts, frame_jpeg_bytes))
                else:
                    logger.warning(
                        f"⚠️ Failed to compress frame for buffer (stream {self.stream_id})"
                    )
            except Exception as e:
                logger.error(f"❌ Error compressing frame for buffer: {e}")

            # Gravação POST-alerta (se ativa)
            if self.alert_clip_active and self.alert_clip_writer:
                try:
                    self.alert_clip_writer.write(processed_frame)

                    # Verifica se completou o tempo POST
                    if now_ts >= self.alert_clip_end_time:
                        post_duration = (
                            self.alert_clip_end_time
                            - (self.alert_clip_end_time - ALERT_CLIP_POST_SEC)
                        )
                        logger.info(
                            f"🎬 Alert clip FINISHED: {self.alert_clip_filename} | "
                            f"Post window: ~{post_duration:.1f}s "
                            f"(config POST={ALERT_CLIP_POST_SEC:.1f}s)"
                        )

                        self.alert_clip_writer.release()
                        self.alert_clip_writer = None
                        self.alert_clip_active = False
                        self.alert_clip_filename = None

                except Exception as e:
                    logger.error(f"❌ Error writing POST-alert frame: {e}")
                    if self.alert_clip_writer:
                        try:
                            self.alert_clip_writer.release()
                        except Exception:
                            pass
                    self.alert_clip_writer = None
                    self.alert_clip_active = False
                    self.alert_clip_filename = None

            # Monitor de memória a cada 300 frames
            if self.frame_count % 300 == 0:
                mem_stats = self._check_memory_usage()
                if mem_stats:
                    logger.debug(
                        f"💾 Stream {self.stream_id} memory: "
                        f"Process={mem_stats.get('process_rss_mb', 0):.1f} MiB, "
                        f"Buffer={mem_stats.get('buffer_estimated_mb', 0):.1f} MiB "
                        f"({mem_stats.get('buffer_frames', 0)} frames)"
                    )

            # Update latest frame
            with self.latest_frame_lock:
                self.latest_frame = processed_frame

            # Add to queue (drop if full)
            try:
                self.frame_queue.put_nowait(processed_frame)
            except Exception:
                self.dropped_frames += 1

            # Gravação contínua
            if self.recording and self.video_writer:
                self.video_writer.write(processed_frame)
                self.recording_frame_count += 1




    # --------------------------------------------------------------------- #
    # PROCESSAMENTO DE FRAME
    # --------------------------------------------------------------------- #

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process frame with YOLO detection"""
        # Resize if needed
        if (
            frame.shape[1] != self.target_width
            or frame.shape[0] != self.target_height
        ):
            frame = cv2.resize(
                frame, (self.target_width, self.target_height)
            )

        # Apply YOLO detection
        if self.enable_detection and self.detector:
            try:
                frame = self.detector.process_frame(frame)
            except Exception as e:
                logger.error(f"❌ Detection error: {e}")
        else:
            # Apenas overlay de timestamp / FPS se YOLO desativado
            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            cv2.putText(
                frame,
                timestamp,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"FPS: {self.fps_current:.1f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

        return frame

    # --------------------------------------------------------------------- #
    # SNAPSHOT / STREAM FRAME
    # --------------------------------------------------------------------- #

    def get_frame(self) -> Optional[bytes]:
        """Get latest frame as JPEG bytes"""
        with self.latest_frame_lock:
            if self.latest_frame is None:
                return None

            # Encode to JPEG
            ret, buffer = cv2.imencode(
                ".jpg",
                self.latest_frame,
                [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY],
            )
            if ret:
                return buffer.tobytes()
            return None

    # --------------------------------------------------------------------- #
    # GRAVAÇÃO CONTÍNUA
    # --------------------------------------------------------------------- #

    def start_recording(
        self,
        filename: Optional[str] = None,
        format: RecordingFormat = RecordingFormat.MP4,
    ) -> bool:
        """Start recording stream (continuous)"""
        if self.recording:
            logger.warning("⚠️ Already recording")
            return False

        try:
            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                filename = (
                    f"recording_{self.stream_id}_{timestamp}."
                    f"{format.value}"
                )

            recordings_dir = (
                settings.BASE_DIR / "data" / "recordings"
            )
            recordings_dir.mkdir(
                parents=True, exist_ok=True
            )
            filepath = recordings_dir / filename

            # Setup video writer
            fourcc_map = {
                RecordingFormat.MP4: cv2.VideoWriter_fourcc(
                    *"mp4v"
                ),
                RecordingFormat.AVI: cv2.VideoWriter_fourcc(
                    *"XVID"
                ),
                RecordingFormat.MKV: cv2.VideoWriter_fourcc(
                    *"X264"
                ),
            }

            fourcc = fourcc_map.get(
                format, cv2.VideoWriter_fourcc(*"mp4v")
            )
            self.video_writer = cv2.VideoWriter(
                str(filepath),
                fourcc,
                self.target_fps,
                (self.target_width, self.target_height),
            )

            if not self.video_writer.isOpened():
                raise RuntimeError(
                    "Failed to open video writer"
                )

            self.recording = True
            self.recording_start_time = time.time()
            self.recording_frame_count = 0
            self.recording_filename = str(filepath)

            logger.info(
                f"🔴 Recording started: {self.recording_filename}"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to start recording: {e}"
            )
            self.video_writer = None
            self.recording = False
            return False

    def stop_recording(self) -> Optional[Dict[str, Any]]:
        """Stop recording stream (continuous)"""
        if not self.recording:
            return None

        self.recording = False

        if self.video_writer:
            try:
                self.video_writer.release()
            except Exception:
                pass
            self.video_writer = None

        duration = (
            time.time() - self.recording_start_time
            if self.recording_start_time
            else 0
        )

        # Get file size
        size_mb = 0.0
        if (
            self.recording_filename
            and Path(self.recording_filename).exists()
        ):
            size_mb = (
                Path(self.recording_filename)
                .stat()
                .st_size
                / (1024 * 1024)
            )

        info = {
            "filename": self.recording_filename,
            "duration_seconds": duration,
            "frame_count": self.recording_frame_count,
            "size_mb": round(size_mb, 2),
        }

        logger.info(f"⏹️ Recording stopped: {info}")

        self.recording_filename = None
        self.recording_start_time = None
        self.recording_frame_count = 0

        return info

    # --------------------------------------------------------------------- #
    # CLIPES DE ALERTA (5s antes + 10s depois)
    # --------------------------------------------------------------------- #

    def start_alert_clip(
        self,
        alert_id: int,
        camera_id: int,
        zone_id: int,
        event_ts: Optional[float] = None,
    ) -> Optional[str]:
        """
        Inicia a gravação de um clipe de alerta em torno de event_ts.
        - Escreve imediatamente ~PRE segundos de frames anteriores (do buffer JPEG).
        - Mantém gravação por ~POST segundos após o evento no loop.
        """
        if event_ts is None:
            event_ts = time.time()

        if self.cap is None or not self.cap.isOpened():
            logger.warning(
                f"⚠️ Cannot start alert clip: stream {self.stream_id} not opened"
            )
            return None

        # Evitar sobreposição de clipes em um mesmo stream
        if self.alert_clip_active or self.alert_clip_writer:
            logger.warning(
                f"⚠️ Alert clip already active on stream {self.stream_id}"
            )
            return self.alert_clip_filename

        try:
            # LOG 1: Configurações
            logger.info(
                f"🎬 Starting alert clip: stream={self.stream_id}, "
                f"camera={camera_id}, zone={zone_id}, "
                f"PRE={ALERT_CLIP_PRE_SEC:.1f}s, POST={ALERT_CLIP_POST_SEC:.1f}s"
            )

            # Timestamp inicial (PRE segundos antes do evento)
            start_ts = event_ts - ALERT_CLIP_PRE_SEC

            # LOG 2: Análise do buffer comprimido
            buffer_copy = list(self.frame_buffer)

            if not buffer_copy:
                logger.error(
                    "❌ Alert clip: Buffer is EMPTY! Cannot write pre-alert frames."
                )
                return None

            oldest_ts = buffer_copy[0][0]
            newest_ts = buffer_copy[-1][0]
            buffer_duration = newest_ts - oldest_ts

            logger.info(
                f"📦 Buffer analysis: {len(buffer_copy)} frames (JPEG), "
                f"duration={buffer_duration:.1f}s "
                f"(oldest={oldest_ts:.2f}, newest={newest_ts:.2f}, "
                f"requested_start={start_ts:.2f})"
            )

            # Filtrar frames do PRE-evento (timestamp + bytes JPEG)
            pre_frames_jpeg = [
                (ts, frame_bytes)
                for ts, frame_bytes in buffer_copy
                if start_ts <= ts <= event_ts
            ]

            # FPS efetivo governado (UMA vez só)
            writer_fps = self._get_alert_writer_fps()
            expected_frames = int(ALERT_CLIP_PRE_SEC * writer_fps)

            logger.info(
                f"✂️ Pre-alert frames: {len(pre_frames_jpeg)} frames "
                f"(expected ~{expected_frames} @ writer_fps={writer_fps:.1f}, "
                f"fps_current={self.fps_current:.1f}, "
                f"fps_avg={getattr(self, 'fps_avg', 0.0):.1f}, "
                f"target_fps={self.target_fps})"
            )

            if len(pre_frames_jpeg) < expected_frames * 0.5:
                logger.warning(
                    f"⚠️ Insufficient pre-alert frames! Got {len(pre_frames_jpeg)}, "
                    f"expected ~{expected_frames}. Buffer may be underfilled "
                    f"or effective FPS too low."
                )

            # Diretórios por câmera e zona
            ts_str = datetime.fromtimestamp(event_ts).strftime("%Y%m%d%H%M%S")
            camera_dir = ALERT_BASE_PATH / f"camera_{camera_id}"
            zone_dir = camera_dir / f"zona_{zone_id}"
            zone_dir.mkdir(parents=True, exist_ok=True)

            filename = (
                f"video_ocorrencia_cam{camera_id}_zona{zone_id}_{ts_str}.mp4"
            )
            filepath = zone_dir / filename

            # VideoWriter com FPS governado
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                str(filepath),
                fourcc,
                writer_fps,
                (self.target_width, self.target_height),
            )

            if not writer.isOpened():
                raise RuntimeError("Failed to open alert clip VideoWriter")

            # PRE-alerta: decodificar JPEG → BGR e escrever
            decoded_count = 0
            failed_count = 0

            for ts, frame_jpeg_bytes in pre_frames_jpeg:
                try:
                    nparr = np.frombuffer(frame_jpeg_bytes, np.uint8)
                    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame_bgr is not None:
                        if (
                            frame_bgr.shape[1] != self.target_width
                            or frame_bgr.shape[0] != self.target_height
                        ):
                            frame_bgr = cv2.resize(
                                frame_bgr,
                                (self.target_width, self.target_height),
                            )

                        writer.write(frame_bgr)
                        decoded_count += 1
                    else:
                        logger.warning(
                            f"⚠️ Failed to decode JPEG frame (ts={ts:.2f})"
                        )
                        failed_count += 1

                except Exception as e:
                    logger.error(
                        f"❌ Error decoding pre-alert frame (ts={ts:.2f}): {e}"
                    )
                    failed_count += 1
                    continue

            logger.info(
                f"📝 Pre-alert frames written: {decoded_count} decoded, "
                f"{failed_count} failed"
            )

            # Estado do clipe para gravação POST-alerta no loop
            self.alert_clip_writer = writer
            self.alert_clip_end_time = event_ts + ALERT_CLIP_POST_SEC
            self.alert_clip_filename = str(filepath)
            self.alert_clip_active = True

            logger.info(
                f"✅ Alert clip started: {filepath.name} | "
                f"Pre-frames written: {decoded_count}/{len(pre_frames_jpeg)}, "
                f"Post-duration-config: {ALERT_CLIP_POST_SEC:.1f}s, "
                f"Expected total-config: "
                f"~{ALERT_CLIP_PRE_SEC + ALERT_CLIP_POST_SEC:.1f}s "
                f"@ writer_fps={writer_fps:.1f}"
            )

            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to start alert clip: {e}", exc_info=True)
            if self.alert_clip_writer:
                try:
                    self.alert_clip_writer.release()
                except Exception:
                    pass
            self.alert_clip_writer = None
            self.alert_clip_active = False
            self.alert_clip_filename = None
            return None


    def _get_alert_writer_fps(self) -> float:
        """
        Define o FPS para VideoWriter dos clipes de alerta de forma governada.
        Preferência:
        1) FPS médio recente (FPSMeter)
        2) FPS instantâneo
        3) target_fps do stream
        4) ALERT_CLIP_FPS de config
        Sempre clampado em [1, ALERT_CLIP_FPS].
        """
        fps = self.fps_meter.average()
        if fps <= 0:
            fps = getattr(self, "fps_current", 0.0)
        if fps <= 0:
            fps = float(self.target_fps or 0.0)
        if fps <= 0:
            fps = float(ALERT_CLIP_FPS)

        fps = max(1.0, min(fps, float(ALERT_CLIP_FPS)))
        return fps


    # --------------------------------------------------------------------- #
    # MÉTRICAS
    # --------------------------------------------------------------------- #

    def get_metrics(self) -> StreamMetrics:
        """Get stream metrics"""
        uptime = (
            time.time() - self.start_time
            if self.start_time
            else 0
        )
        avg_processing_time = (
            sum(self.processing_times) / len(self.processing_times)
            if self.processing_times
            else 0
        )

        # Memory usage (approximate)
        import psutil

        process = psutil.Process()
        memory_mb = (
            process.memory_info().rss / (1024 * 1024)
        )

        return StreamMetrics(
            stream_id=self.stream_id,
            state=self.state,
            fps_current=round(self.fps_current, 2),
            fps_target=self.target_fps,
            frame_count=self.frame_count,
            dropped_frames=self.dropped_frames,
            processing_time_ms=round(
                avg_processing_time, 2
            ),
            memory_usage_mb=round(memory_mb, 2),
            uptime_seconds=round(uptime, 2),
            source_info={
                "type": self.source_type.value,
                "path": self.source_path,
                "width": self.target_width,
                "height": self.target_height,
            },
            detection_stats=self._get_detection_stats(),
            timestamp=datetime.now(),
        )

    def _get_detection_stats(self) -> Optional[Dict[str, Any]]:
        """Get detection statistics"""
        if not self.detector or not hasattr(
            self.detector, "get_stats"
        ):
            return None
        try:
            return self.detector.get_stats()
        except Exception:
            return None

    def _check_memory_usage(self) -> dict:
        """Monitora uso de memória do stream"""
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            
            buffer_size_mb = (
                len(self.frame_buffer) * 0.08  # ~80 KB/frame comprimido
            )
            
            return {
                "process_rss_mb": mem_info.rss / (1024 * 1024),
                "buffer_frames": len(self.frame_buffer),
                "buffer_estimated_mb": buffer_size_mb,
                "buffer_duration_s": self.buffer_duration_seconds,
            }
        except Exception as e:
            logger.error(f"❌ Failed to check memory: {e}")
            return {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_placeholder_frame(
    width: int = 640,
    height: int = 480,
    message: str = "Video Stream",
) -> np.ndarray:
    """Create placeholder frame"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Background
    cv2.rectangle(
        frame, (0, 0), (width, height), (40, 40, 40), -1
    )

    # Text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(message, font, 1, 2)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(
        frame,
        message,
        (text_x, text_y),
        font,
        1,
        (255, 255, 255),
        2,
    )

    # Timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    cv2.putText(
        frame,
        timestamp,
        (width - 150, height - 20),
        font,
        0.6,
        (200, 200, 200),
        1,
    )

    return frame


def get_available_cameras() -> List[VideoSourceInfo]:
    """Get list of available cameras"""
    cameras: List[VideoSourceInfo] = []

    # Try first 5 camera indices
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0

            cameras.append(
                VideoSourceInfo(
                    id=f"webcam_{i}",
                    type=VideoSource.WEBCAM,
                    name=f"Webcam {i}",
                    path=str(i),
                    available=True,
                    width=width,
                    height=height,
                    fps=fps,
                )
            )
        cap.release()

    return cameras


def generate_stream(
    stream_id: str,
) -> Generator[bytes, None, None]:
    """Generate MJPEG stream"""
    stream = active_streams.get(stream_id)

    if not stream:
        # Return placeholder
        while True:
            frame = create_placeholder_frame(
                message="Stream Not Found"
            )
            ret, buffer = cv2.imencode(".jpg", frame)
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buffer.tobytes()
                    + b"\r\n"
                )
            time.sleep(0.1)
        # not reached
    else:
        while stream.running:
            frame_bytes = stream.get_frame()
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
            else:
                # No frame available, wait a bit
                time.sleep(0.01)


def trigger_alert_clip(
    stream_id: str,
    alert_id: int,
    camera_id: int,
    zone_id: int,
    event_ts: Optional[float] = None,
) -> Optional[str]:
    """
    Helper global para iniciar clipe de alerta em um stream ativo.

    Deve ser chamado pelo pipeline de zonas/alertas passando:
    - stream_id associado à câmera,
    - alert_id do alerta persistido,
    - camera_id,
    - zone_id,
    - event_ts opcional (epoch).
    """
    stream = active_streams.get(stream_id)
    if not stream:
        logger.warning(
            "⚠️ trigger_alert_clip: stream %s not found",
            stream_id,
        )
        return None

    return stream.start_alert_clip(
        alert_id=alert_id,
        camera_id=camera_id,
        zone_id=zone_id,
        event_ts=event_ts,
    )


# ============================================================================
# v2.0 ENDPOINTS - VIDEO STREAMING (Compatible)
# ============================================================================


@router.get("/video_feed", summary="📹 Stream de vídeo MJPEG")
async def video_feed():
    """
    ✅ v2.0: Endpoint de streaming de vídeo MJPEG
    **Compatível com v2.0** - Usa stream padrão
    """
    # Get or create default stream
    default_stream_id = "default"

    with stream_lock:
        if default_stream_id not in active_streams:
            stream = VideoStream(
                stream_id=default_stream_id,
                source_type=VideoSource.WEBCAM,
                device_id=0,
                quality=VideoQuality.MEDIUM,
            )
            stream.start()
            active_streams[default_stream_id] = stream

    return StreamingResponse(
        generate_stream(default_stream_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get(
    "/video_status",
    response_model=VideoStatusResponse,
    summary="📊 Status do stream",
)
async def video_status():
    """
    ✅ v2.0: Status do stream de vídeo
    **Compatível com v2.0**
    """
    default_stream_id = "default"
    stream = active_streams.get(default_stream_id)

    if not stream:
        return VideoStatusResponse(
            status="offline", source="none", fps=0.0
        )

    uptime = (
        time.time() - stream.start_time
        if stream.start_time
        else 0
    )

    return VideoStatusResponse(
        status=stream.state.value,
        source=stream.source_type.value,
        fps=round(stream.fps_current, 2),
        uptime=round(uptime, 2),
        frame_count=stream.frame_count,
    )


# ============================================================================
# v3.0 ENDPOINTS - STREAM MANAGEMENT (NEW)
# ============================================================================


@router.get("/sources", summary="📷 Listar fontes de vídeo")
@limiter.limit("30/minute")
async def list_video_sources(
    request: Request, current_user: dict = Depends(get_current_user)
):
    """
    ➕ NEW v3.0: Lista todas as fontes de vídeo disponíveis
    """
    sources = get_available_cameras()

    # Add example sources
    examples = [
        VideoSourceInfo(
            id="rtsp_example",
            type=VideoSource.RTSP,
            name="RTSP Camera Example",
            path="rtsp://example.com/stream",
            available=False,
        ),
        VideoSourceInfo(
            id="file_example",
            type=VideoSource.FILE,
            name="Video File Example",
            path="/path/to/video.mp4",
            available=False,
        ),
    ]

    return {
        "sources": sources + examples,
        "count": len(sources),
    }


@router.post("/stream/start", summary="▶️ Iniciar stream")
@limiter.limit("10/minute")
async def start_stream(
    request: Request,
    stream_request: StreamStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Inicia novo stream de vídeo
    """
    # Generate stream ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stream_id = (
        f"stream_{timestamp}_{current_user.get('username')}"
    )

    with stream_lock:
        # Check max streams
        if len(active_streams) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum number of concurrent streams reached (5)",
            )

        # Create stream
        stream = VideoStream(
            stream_id=stream_id,
            source_type=stream_request.source_type,
            source_path=stream_request.source_path,
            device_id=stream_request.device_id or 0,
            enable_detection=stream_request.enable_detection,
            enable_tracking=stream_request.enable_tracking,
            quality=stream_request.quality,
        )

        # Start stream
        if not stream.start():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start video stream",
            )

        active_streams[stream_id] = stream

    logger.info(
        "✅ Stream started: %s by %s",
        stream_id,
        current_user.get("username"),
    )

    return {
        "stream_id": stream_id,
        "status": "started",
        "feed_url": f"/api/v1/video/stream/{stream_id}/feed",
    }


@router.post("/stream/stop", summary="⏹️ Parar stream")
@limiter.limit("30/minute")
async def stop_stream(
    request: Request,
    stream_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Para stream de vídeo
    """
    with stream_lock:
        stream = active_streams.get(stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found",
            )

        stream.stop()
        del active_streams[stream_id]

    logger.info("🛑 Stream stopped: %s", stream_id)

    return {"status": "stopped", "stream_id": stream_id}


@router.post("/stream/pause", summary="⏸️ Pausar stream")
@limiter.limit("30/minute")
async def pause_stream(
    request: Request,
    stream_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Pausa stream de vídeo
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    stream.pause()
    return {"status": "paused", "stream_id": stream_id}


@router.post("/stream/resume", summary="▶️ Retomar stream")
@limiter.limit("30/minute")
async def resume_stream(
    request: Request,
    stream_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Retoma stream pausado
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    stream.resume()
    return {"status": "resumed", "stream_id": stream_id}


@router.get(
    "/stream/{stream_id}/feed", summary="📹 Feed do stream"
)
async def stream_feed(stream_id: str):
    """
    ➕ NEW v3.0: Feed MJPEG de stream específico
    """
    if stream_id not in active_streams:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    return StreamingResponse(
        generate_stream(stream_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get(
    "/stream/{stream_id}/snapshot", summary="📸 Capturar snapshot"
)
@limiter.limit("30/minute")
async def capture_snapshot(
    request: Request,
    stream_id: str,
    format: str = Query("jpg", pattern="^(jpg|png)$"),
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Captura snapshot do stream
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    frame_bytes = stream.get_frame()
    if not frame_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No frame available",
        )

    # Convert to requested format
    if format == "png":
        # Decode JPEG, encode as PNG
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        ret, buffer = cv2.imencode(".png", img)
        if not ret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to encode PNG",
            )
        frame_bytes = buffer.tobytes()
        media_type = "image/png"
    else:
        media_type = "image/jpeg"

    return Response(content=frame_bytes, media_type=media_type)


@router.post("/stream/{stream_id}/record", summary="🔴 Iniciar gravação")
@limiter.limit("10/minute")
async def start_recording_endpoint(
    request: Request,
    stream_id: str,
    recording_request: RecordingStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Inicia gravação contínua do stream
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    if not stream.start_recording(
        filename=recording_request.filename,
        format=recording_request.format,
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start recording",
        )

    return {
        "status": "recording",
        "stream_id": stream_id,
        "filename": stream.recording_filename,
    }


@router.post(
    "/stream/{stream_id}/record/stop", summary="⏹️ Parar gravação"
)
@limiter.limit("30/minute")
async def stop_recording_endpoint(
    request: Request,
    stream_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Para gravação contínua do stream
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    info = stream.stop_recording()
    if not info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recording in progress",
        )

    return {"status": "stopped", "stream_id": stream_id, **info}


@router.get(
    "/stream/{stream_id}/metrics",
    response_model=StreamMetrics,
    summary="📊 Métricas do stream",
)
@limiter.limit("60/minute")
async def get_stream_metrics(
    request: Request,
    stream_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Obtém métricas de performance do stream
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    return stream.get_metrics()


@router.put(
    "/stream/{stream_id}/settings", summary="⚙️ Configurar stream"
)
@limiter.limit("30/minute")
async def update_stream_settings(
    request: Request,
    stream_id: str,
    settings_request: StreamSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Atualiza configurações do stream
    """
    stream = active_streams.get(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found",
        )

    # Update settings
    updated: Dict[str, Any] = {}

    if settings_request.quality:
        preset = QUALITY_PRESETS[settings_request.quality]
        stream.target_width = preset["width"]
        stream.target_height = preset["height"]
        stream.target_fps = preset["fps"]
        updated["quality"] = settings_request.quality.value

    if settings_request.fps is not None:
        stream.target_fps = settings_request.fps
        updated["fps"] = settings_request.fps

    if settings_request.width is not None:
        stream.target_width = settings_request.width
        updated["width"] = settings_request.width

    if settings_request.height is not None:
        stream.target_height = settings_request.height
        updated["height"] = settings_request.height

    if settings_request.enable_detection is not None:
        stream.enable_detection = (
            settings_request.enable_detection
        )
        updated["enable_detection"] = (
            settings_request.enable_detection
        )

    if settings_request.enable_tracking is not None:
        stream.enable_tracking = (
            settings_request.enable_tracking
        )
        updated["enable_tracking"] = (
            settings_request.enable_tracking
        )

    logger.info(
        "⚙️ Stream %s settings updated: %s",
        stream_id,
        updated,
    )

    return {
        "stream_id": stream_id,
        "updated": updated,
        "status": "success",
    }


@router.get("/streams", summary="📋 Listar streams ativos")
@limiter.limit("60/minute")
async def list_active_streams(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    ➕ NEW v3.0: Lista todos os streams ativos
    """
    streams_info: List[Dict[str, Any]] = []

    for stream_id, stream in active_streams.items():
        info = {
            "stream_id": stream_id,
            "state": stream.state.value,
            "source_type": stream.source_type.value,
            "fps": round(stream.fps_current, 2),
            "frame_count": stream.frame_count,
            "uptime": round(
                time.time() - stream.start_time, 2
            )
            if stream.start_time
            else 0,
            "recording": stream.recording,
            "feed_url": f"/api/v1/video/stream/{stream_id}/feed",
        }
        streams_info.append(info)

    return {"streams": streams_info, "count": len(streams_info)}


@router.delete("/streams/{stream_id}", summary="🗑️ Fechar stream")
@limiter.limit("30/minute")
async def close_stream(
    request: Request,
    stream_id: str,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    ➕ NEW v3.0: Fecha stream específico (admin only)
    """
    with stream_lock:
        stream = active_streams.get(stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found",
            )

        stream.stop()
        del active_streams[stream_id]

    logger.info(
        "🗑️ Stream %s closed by admin %s",
        stream_id,
        current_user.get("username"),
    )

    return {"status": "closed", "stream_id": stream_id}


# ============================================================================
# CLEANUP ON SHUTDOWN
# ============================================================================


@router.on_event("shutdown")
async def shutdown_streams():
    """Stop all streams on shutdown"""
    logger.info("🛑 Stopping all video streams...")
    with stream_lock:
        for stream in active_streams.values():
            stream.stop()
        active_streams.clear()
    logger.info("✅ All video streams stopped")


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🎯 VIDEO API ROUTER v3.1 - ALERT CLIPS ENABLED")
    print("=" * 80)
    print("\n✅ v2.0 ENDPOINTS (2 endpoints - 100% Compatible):")
    print(" 1. GET /api/v1/video/video_feed - Stream MJPEG")
    print(" 2. GET /api/v1/video/video_status - Status")

    print("\n➕ NEW v3.0 ENDPOINTS (12 endpoints):")
    print("\n📷 Sources:")
    print(" 3. GET /api/v1/video/sources - Listar fontes")

    print("\n▶️ Stream Control:")
    print(" 4. POST /api/v1/video/stream/start - Iniciar")
    print(" 5. POST /api/v1/video/stream/stop - Parar")
    print(" 6. POST /api/v1/video/stream/pause - Pausar")
    print(" 7. POST /api/v1/video/stream/resume - Retomar")
    print(" 8. GET /api/v1/video/stream/{id}/feed - Feed específico")

    print("\n📸 Capture:")
    print(" 9. GET /api/v1/video/stream/{id}/snapshot - Snapshot")

    print("\n🔴 Recording:")
    print(" 10. POST /api/v1/video/stream/{id}/record - Iniciar")
    print(" 11. POST /api/v1/video/stream/{id}/record/stop - Parar")

    print("\n📊 Monitoring:")
    print(" 12. GET /api/v1/video/stream/{id}/metrics - Métricas")
    print(" 13. PUT /api/v1/video/stream/{id}/settings - Configurar")
    print(" 14. GET /api/v1/video/streams - Listar ativos")
    print(" 15. DELETE /api/v1/video/streams/{id} - Fechar")

    print("\n🚀 v3.1 FEATURES:")
    print(" • Multiple video sources (webcam, RTSP, file, URL)")
    print(" • YOLO real-time detection integration")
    print(" • Stream controls (pause/resume)")
    print(" • Snapshot capture (JPG/PNG)")
    print(" • Continuous video recording (MP4/AVI/MKV)")
    print(" • Alert clips: 5s before + 10s after, per camera/zone")
    print(" • Alert videos saved under Windows path for occurrences")
    print(" • Performance metrics & monitoring")
    print(" • Configurable quality presets")
    print(" • Concurrent streams (max 5)")
    print(" • Frame rate control")
    print(" • Memory optimization with frame buffer")
    print(" • Automatic cleanup on shutdown")
    print("\n" + "=" * 80)
    print("✅ Video API v3.1 COMPLETE and READY!")
    print("=" * 80)
