# backend/runtime/segmentation/sam3_service.py

import threading
from typing import List, Dict, Any, Optional

import numpy as np
from ultralytics.models.sam import SAM3SemanticPredictor
from backend.core.config.config import settings
import logging

logger = logging.getLogger(__name__)


class Sam3Service:
    """
    Wrapper fino em cima do SAM3SemanticPredictor da Ultralytics.
    Responsável por:
    - carregar sam3.pt uma vez (singleton)
    - expor métodos simples para segmentar a partir de frame+bbox
    """
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

        if not settings.USE_SAM3:
            logger.info("SAM3 disabled by config (USE_SAM3=False)")
            self._predictor = None
            return

        overrides = dict(
            conf=settings.SAM3_CONFIDENCE,
            task="segment",
            mode="predict",
            imgsz=settings.SAM3_IMAGE_SIZE,
            model=settings.SAM3_MODEL_PATH,
            half=True,
        )
        logger.info(f"Loading SAM3SemanticPredictor with overrides={overrides}")
        self._predictor = SAM3SemanticPredictor(overrides=overrides)  # API oficial[web:435]

    def is_enabled(self) -> bool:
        return settings.USE_SAM3 and self._predictor is not None

    def segment_from_bbox(
        self,
        frame_bgr: np.ndarray,
        bbox_xyxy: List[float],
        text_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Usa SAM3 em modo PVS (visual prompt com box) e, opcionalmente,
        em PCS (texto) para refinar a segmentação de uma única instância.

        Retorna dict com:
        - mask: np.ndarray bool/uint8 [H,W] da instância alvo
        - bbox: bbox refinado (opcional)
        - score: confiança da máscara escolhida
        """
        if not self.is_enabled():
            raise RuntimeError("SAM3 is disabled")

        # A API oficial usa 'set_image' + chamada ao predictor; aqui vamos
        # seguir o padrão do SAM3Predictor/SAM3SemanticPredictor: setar imagem
        # e depois passar prompts.[web:435]
        # Importante: assumir frame em BGR, converter se o predictor exigir RGB.
        self._predictor.set_image(frame_bgr)  # internamente converte

        x1, y1, x2, y2 = bbox_xyxy
        boxes = [[x1, y1, x2, y2]]
        labels = [1]  # 1 = positive exemplar

        if text_prompt:
            # PCS + exemplo de imagem: texto + bbox positivo[web:435]
            results = self._predictor(text=[text_prompt], bboxes=boxes, labels=labels)
        else:
            # PVS (visual prompt only, estilo SAM 2, mas com SAM3Predictor)[web:435]
            results = self._predictor(bboxes=boxes, labels=labels)

        if not results:
            return {}

        # results[0] deve conter masks, scores etc. seguindo o padrão Ultralytics
        r0 = results[0]
        mask = r0.masks.data[0].cpu().numpy()  # [H,W] da instância principal
        score = float(r0.probs[0]) if getattr(r0, "probs", None) is not None else 1.0

        return {
            "mask": mask,
            "score": score,
            "bbox": bbox_xyxy,
        }


# helper global
_sam3_service: Optional[Sam3Service] = None


def get_sam3_service() -> Sam3Service:
    global _sam3_service
    if _sam3_service is None:
        _sam3_service = Sam3Service()
    return _sam3_service
