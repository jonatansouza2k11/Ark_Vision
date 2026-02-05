"""
Zone Frame Buffer v1.1 - Memory-Governed
Mantém buffer circular de frames com limites por TEMPO e CONTAGEM.
"""
import threading
import logging
from collections import deque
from typing import Dict, Deque, Tuple, Optional
import numpy as np
import time

from backend.core.config.config import settings


logger = logging.getLogger(__name__)

_buffers_lock = threading.Lock()
_buffers: Dict[int, Deque[Tuple[float, np.ndarray]]] = {}

# Governança de memória
BUFFER_DURATION_SEC = float(getattr(settings, "BUFFER_DURATION_SECONDS", 20.0))
MAX_FRAMES_PER_CAM = int(getattr(settings, "MAX_FRAMES_PER_CAMERA", 200.0))

def push_frame(
    camera_id: int,
    frame: np.ndarray,
    buffer_seconds: float = BUFFER_DURATION_SEC,
) -> None:
    """
    Adiciona frame no buffer com governança de memória.
    
    Limites aplicados (o que atingir primeiro):
    - Tempo: mantém apenas últimos `buffer_seconds` segundos
    - Contagem: máximo `MAX_FRAMES_PER_CAM` frames
    
    Args:
        camera_id: ID da câmera
        frame: Frame BGR (será copiado internamente)
        buffer_seconds: Janela de tempo máxima (padrão 20s)
    """
    now = time.time()
    
    with _buffers_lock:
        buf = _buffers.get(camera_id)
        if buf is None:
            buf = deque(maxlen=MAX_FRAMES_PER_CAM)  # ✅ Hard limit
            _buffers[camera_id] = buf
        
        # ✅ Copia frame apenas UMA vez (aqui)
        buf.append((now, frame.copy()))
        
        # ✅ Remove frames fora da janela de tempo (além do hard limit)
        cutoff = now - buffer_seconds
        while buf and buf[0][0] < cutoff:
            buf.popleft()
        
        # ✅ Log de debug (só em caso de buffer grande)
        if len(buf) > MAX_FRAMES_PER_CAM * 0.9:
            logger.warning(
                "zone_frame_buffer: camera_id=%s buffer próximo do limite (%d/%d frames)",
                camera_id,
                len(buf),
                MAX_FRAMES_PER_CAM,
            )

def get_frames_for_interval(
    camera_id: int,
    start_ts: float,
    end_ts: float,
) -> Deque[Tuple[float, np.ndarray]]:
    """
    Retorna frames no intervalo [start_ts, end_ts].
    
    ⚠️ NÃO copia os frames - consumidor deve copiar se precisar modificá-los.
    
    Args:
        camera_id: ID da câmera
        start_ts: Timestamp inicial (epoch)
        end_ts: Timestamp final (epoch)
    
    Returns:
        Deque de tuplas (timestamp, frame) - VIEWS, não cópias
    """
    with _buffers_lock:
        buf = _buffers.get(camera_id)
        if not buf:
            return deque()
        
        # ✅ Retorna VIEWS (não cópias) para economia de memória
        # O recorder fará frame.copy() ao escrever no vídeo
        return deque((ts, f) for ts, f in buf if start_ts <= ts <= end_ts)

def clear_camera_buffer(camera_id: int) -> None:
    """Limpa buffer de uma câmera (usado ao remover câmera)."""
    with _buffers_lock:
        if camera_id in _buffers:
            _buffers[camera_id].clear()
            del _buffers[camera_id]
            logger.info("zone_frame_buffer: buffer cleared for camera_id=%s", camera_id)

def get_buffer_stats(camera_id: int) -> Optional[Dict]:
    """Retorna estatísticas do buffer (debug/monitoring)."""
    with _buffers_lock:
        buf = _buffers.get(camera_id)
        if not buf or len(buf) == 0:
            return None
        
        now = time.time()
        oldest_ts = buf[0][0]
        newest_ts = buf[-1][0]
        
        # Estima tamanho em memória (aproximado)
        frame_size_bytes = buf[0][1].nbytes if len(buf) > 0 else 0
        total_size_mb = (len(buf) * frame_size_bytes) / (1024 * 1024)
        
        return {
            "camera_id": camera_id,
            "frame_count": len(buf),
            "duration_seconds": newest_ts - oldest_ts,
            "oldest_frame_age_seconds": now - oldest_ts,
            "estimated_size_mb": round(total_size_mb, 2),
        }
