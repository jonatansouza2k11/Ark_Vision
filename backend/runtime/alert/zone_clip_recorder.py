"""
Zone Clip Recorder v1.1 - Memory-Efficient
Grava clipes de alerta usando buffer do VisionSystem.
"""
import cv2
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from backend.runtime.alert.zone_frame_buffer import get_frames_for_interval
from backend.core.config.config import settings

logger = logging.getLogger(__name__)

def vision_clip_recorder(
    camera_id: int,
    zone_id: int,
    metrics: Dict[str, Any],
    event_time: float,
) -> Optional[str]:
    """
    Grava clipe de alerta usando buffer de frames do VisionSystem.
    
    Args:
        camera_id: ID da câmera
        zone_id: ID da zona
        metrics: Métricas da zona (ZoneMetrics.to_dict())
        event_time: Timestamp do evento (epoch)
    
    Returns:
        Caminho do arquivo de vídeo salvo, ou None em caso de erro
    """
    pre_sec = float(getattr(settings, "ALERT_CLIP_PRE_SECONDS", 5.0))
    post_sec = float(getattr(settings, "ALERT_CLIP_POST_SECONDS", 10.0))
    
    start_ts = event_time - pre_sec
    end_ts = event_time + post_sec
    
    # ✅ Pega frames do buffer (retorna VIEWS, não cópias)
    frames = get_frames_for_interval(camera_id, start_ts, end_ts)
    
    if not frames:
        logger.warning(
            "vision_clip_recorder: nenhum frame no buffer para camera_id=%s "
            "(event_time=%.2f, buffer vazio ou muito antigo)",
            camera_id,
            event_time,
        )
        return None
    
    if len(frames) < 3:
        logger.warning(
            "vision_clip_recorder: apenas %d frames no buffer para camera_id=%s "
            "(clipe muito curto, ignorando)",
            len(frames),
            camera_id,
        )
        return None
    
    # ========================================================================
    # ✅ AJUSTE: Respeita caminho configurado (absoluto ou relativo)
    # ========================================================================
    
    # Pega o caminho configurado para clipes de alerta
    alert_video_path = getattr(settings, "ALERT_VIDEO_PATH", "storage/alert_clips")
    
    # Converte para Path se vier como string
    if isinstance(alert_video_path, str):
        alert_video_path = Path(alert_video_path)
    
    # Se for caminho absoluto, usa diretamente
    # Se for relativo, resolve a partir de BASE_DIR
    if alert_video_path.is_absolute():
        base_path = alert_video_path
    else:
        # Caminho relativo: resolve a partir de BASE_DIR
        base_dir = getattr(settings, "BASE_DIR", Path.cwd())
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        base_path = base_dir / alert_video_path
    
    # Cria diretório se não existir
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(
            "❌ vision_clip_recorder: erro ao criar diretório %s: %s",
            base_path,
            e,
        )
        return None
    
    # ========================================================================
    
    ts_str = datetime.fromtimestamp(event_time).strftime("%Y%m%d_%H%M%S")
    filename = f"alert_cam{camera_id}_zone{zone_id}_{ts_str}.mp4"
    filepath = base_path / filename
    
    try:
        # ✅ Pega dimensões do primeiro frame
        _, first_frame = frames[0]
        h, w = first_frame.shape[:2]
        
        # ✅ FPS do clipe (reduzido para economizar espaço)
        fps = min(
            float(getattr(settings, "ALERT_CLIP_FPS", 10)),
            10.0  # máximo 10 FPS para clipes de alerta
        )
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(str(filepath), fourcc, fps, (w, h))
        
        if not vw.isOpened():
            raise RuntimeError("Failed to open VideoWriter for alert clip")
        
        # ✅ COPIA frames apenas aqui (ao escrever no vídeo)
        for _, frame in frames:
            # frame.copy() não é necessário - VideoWriter não modifica o buffer
            vw.write(frame)
        
        vw.release()
        
        logger.info(
            "✅ vision_clip_recorder: clipe salvo (camera_id=%s, zone_id=%s, "
            "frames=%d, duration=%.1fs, file=%s)",
            camera_id,
            zone_id,
            len(frames),
            len(frames) / fps,
            filepath.name,
        )
        
        return str(filepath)
        
    except Exception as e:
        logger.exception(
            "❌ vision_clip_recorder: erro ao gravar clipe "
            "(camera_id=%s, zone_id=%s, error=%s)",
            camera_id,
            zone_id,
            e,
        )
        return None
