"""
video.py

Schemas Pydantic para endpoints de vídeo/streaming YOLO.
Compatível com YOLOVisionSystem (yolo.py).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# =========================
# ZONE SCHEMAS
# =========================

class ZonePointSchema(BaseModel):
    """Ponto normalizado (0-1) de uma zona poligonal."""
    x: float = Field(..., ge=0.0, le=1.0, description="Coordenada X normalizada (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Coordenada Y normalizada (0-1)")


class ZoneRichSchema(BaseModel):
    """Zona rica com metadados completos (formato settings.safe_zone)."""
    name: str = Field(..., description="Nome da zona")
    mode: str = Field(default="GENERIC", description="Modo: GENERIC, ENTRY, EXIT, etc")
    points: List[List[float]] = Field(..., description="Polígono normalizado [[x,y], ...]")
    max_out_time: Optional[float] = Field(None, description="Tempo máximo fora (segundos)")
    email_cooldown: Optional[float] = Field(None, description="Cooldown de email (segundos)")
    empty_timeout: Optional[float] = Field(None, description="Timeout zona vazia (segundos)")
    full_timeout: Optional[float] = Field(None, description="Timeout zona cheia (segundos)")
    full_threshold: Optional[int] = Field(None, description="Threshold pessoas para 'cheia'")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Entrada Principal",
                "mode": "ENTRY",
                "points": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
                "max_out_time": 10.0,
                "email_cooldown": 60.0,
                "empty_timeout": 15.0,
                "full_timeout": 20.0,
                "full_threshold": 5
            }
        }


class ZoneStatsSchema(BaseModel):
    """Estatísticas em tempo real de uma zona."""
    index: int = Field(..., description="Índice da zona")
    name: str = Field(..., description="Nome da zona")
    mode: str = Field(..., description="Modo da zona")
    count: int = Field(..., description="Pessoas detectadas agora")
    empty_for: Optional[float] = Field(None, description="Tempo vazia (segundos)")
    full_for: Optional[float] = Field(None, description="Tempo cheia (segundos)")
    state: Literal["OK", "EMPTY_LONG", "FULL_LONG"] = Field(..., description="Estado da zona")

    class Config:
        json_schema_extra = {
            "example": {
                "index": 0,
                "name": "Entrada Principal",
                "mode": "ENTRY",
                "count": 3,
                "empty_for": None,
                "full_for": None,
                "state": "OK"
            }
        }


# =========================
# DETECTION SCHEMAS
# =========================

class DetectionSchema(BaseModel):
    """Detecção individual de uma pessoa."""
    id: int = Field(..., description="ID único do tracker")
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., description="Confiança da detecção (0-1)")
    status: Literal["IN", "OUT"] = Field(..., description="Dentro/fora da zona")
    out_time: float = Field(..., description="Tempo fora da zona (segundos)")
    zone_idx: int = Field(..., description="Índice da zona (-1 se fora)")
    recording: bool = Field(..., description="Gravando vídeo?")
    last_seen: float = Field(..., description="Timestamp da última detecção")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 5,
                "bbox": [100, 150, 300, 450],
                "confidence": 0.92,
                "status": "OUT",
                "out_time": 3.5,
                "zone_idx": 0,
                "recording": True,
                "last_seen": 1735603200.0
            }
        }


class DetectionsListSchema(BaseModel):
    """Lista de detecções ativas."""
    total: int = Field(..., description="Total de pessoas detectadas")
    detections: List[DetectionSchema] = Field(..., description="Lista de detecções")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp UTC")


# =========================
# VIDEO STATUS SCHEMAS
# =========================

class VideoStatusSchema(BaseModel):
    """Status completo do sistema de vídeo."""
    system_status: Literal["running", "paused", "stopped"] = Field(..., description="Estado do sistema")
    stream_active: bool = Field(..., description="Stream ativo?")
    paused: bool = Field(..., description="Stream pausado?")
    
    # FPS
    fps: float = Field(..., description="FPS média")
    fps_inst: float = Field(..., description="FPS instantânea")
    fps_avg: float = Field(..., description="FPS média suavizada")
    
    # Detecções
    in_zone: int = Field(..., description="Pessoas dentro da zona")
    out_zone: int = Field(..., description="Pessoas fora da zona")
    detected_count: int = Field(..., description="Total de pessoas detectadas")
    
    # Zonas
    zones: List[ZoneStatsSchema] = Field(..., description="Estatísticas das zonas")
    
    # Memória
    memory_mb: Optional[float] = Field(None, description="Uso de memória (MB)")
    peak_memory_mb: Optional[float] = Field(None, description="Pico de memória (MB)")
    frame_count: int = Field(..., description="Total de frames processados")
    preset: str = Field(..., description="Preset ativo (LOW-END, BALANCED, etc)")

    class Config:
        json_schema_extra = {
            "example": {
                "system_status": "running",
                "stream_active": True,
                "paused": False,
                "fps": 29.8,
                "fps_inst": 30.1,
                "fps_avg": 29.8,
                "in_zone": 2,
                "out_zone": 1,
                "detected_count": 3,
                "zones": [
                    {
                        "index": 0,
                        "name": "Entrada Principal",
                        "mode": "ENTRY",
                        "count": 2,
                        "empty_for": None,
                        "full_for": None,
                        "state": "OK"
                    }
                ],
                "memory_mb": 856.3,
                "peak_memory_mb": 1024.5,
                "frame_count": 15234,
                "preset": "BALANCED"
            }
        }


# =========================
# CONTROL SCHEMAS
# =========================

class VideoControlResponse(BaseModel):
    """Resposta de controle do vídeo (start/stop/pause)."""
    success: bool = Field(..., description="Operação bem-sucedida?")
    message: str = Field(..., description="Mensagem de status")
    system_status: Literal["running", "paused", "stopped"] = Field(..., description="Estado atual")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Stream iniciado com sucesso",
                "system_status": "running"
            }
        }


class VideoConfigUpdateRequest(BaseModel):
    """Request para atualizar configurações do vídeo em runtime."""
    conf_thresh: Optional[float] = Field(None, ge=0.0, le=1.0, description="Threshold de confiança")
    target_width: Optional[int] = Field(None, ge=320, le=1920, description="Largura alvo do frame")
    frame_step: Optional[int] = Field(None, ge=1, le=10, description="Processar a cada N frames")
    max_out_time: Optional[float] = Field(None, ge=0.0, description="Tempo máximo fora (s)")
    email_cooldown: Optional[float] = Field(None, ge=0.0, description="Cooldown de email (s)")

    class Config:
        json_schema_extra = {
            "example": {
                "conf_thresh": 0.85,
                "target_width": 960,
                "frame_step": 1,
                "max_out_time": 10.0,
                "email_cooldown": 30.0
            }
        }


# =========================
# SNAPSHOT SCHEMAS
# =========================

class SnapshotResponse(BaseModel):
    """Resposta de captura de snapshot."""
    success: bool = Field(..., description="Snapshot capturado?")
    path: Optional[str] = Field(None, description="Caminho do arquivo salvo")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp UTC")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "path": "snapshots/snapshot_20251230_230145.jpg",
                "timestamp": "2025-12-30T23:01:45.123456"
            }
        }
