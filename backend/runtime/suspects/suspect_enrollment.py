# backend/runtime/suspects/suspect_enrollment.py

from typing import Dict, Any
import numpy as np
from backend.services.vision_system import get_vision_system
from backend.runtime.segmentation.sam3_service import get_sam3_service
from backend.core.config.config import settings

def enroll_suspect_from_track(camera_id: int, track_id: int) -> Dict[str, Any]:
    """
    Pega frame + bbox + global_id de um track e cria um 'template' de suspeito.
    Se USE_SAM3=True, usa SAM3 para máscara refinada; caso contrário, usa crop retangular.
    """
    vs = get_vision_system()
    ctx = vs.camera_contexts.get(camera_id)
    if not ctx or not ctx.is_running:
        raise RuntimeError("Camera not active")

    frame = ctx.get_current_frame()
    if frame is None:
        raise RuntimeError("No frame available")

    with ctx.track_state_lock:
        ts = ctx.track_state.copy()

    track = ts.get(track_id)
    if not track:
        raise RuntimeError("Track not found")

    bbox = track["bbox"]  # [x1,y1,x2,y2]
    global_id = track.get("global_id")

    x1, y1, x2, y2 = map(int, bbox)
    crop = frame[y1:y2, x1:x2].copy()

    mask = None
    if settings.USE_SAM3:
        sam3 = get_sam3_service()
        if sam3.is_enabled():
            result = sam3.segment_from_bbox(frame, bbox_xyxy=bbox)
            mask = result.get("mask")

    if mask is not None:
        # Aplica máscara só na região da bbox (simples: recortar a máscara)
        mask_crop = mask[y1:y2, x1:x2]
        # Você pode salvar mask_crop junto ou aplicar no crop para gerar RGBA/PNG

    # Aqui você integra com o seu GlobalReIDManager / storage de suspeitos
    return {
        "camera_id": camera_id,
        "track_id": track_id,
        "global_id": global_id,
        "bbox": bbox,
        "crop": crop,
        "mask": mask,  # opcional
    }
