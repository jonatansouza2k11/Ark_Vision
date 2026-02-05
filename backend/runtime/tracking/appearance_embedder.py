# backend/runtime/tracking/appearance_embedder.py

import logging
from enum import Enum
from typing import List, Dict, Any, Optional
import cv2

import numpy as np
import torch
import torch.nn.functional as F

from backend.core.config.config import settings

logger = logging.getLogger(__name__)


class ReIDProfile(str, Enum):
    EDGE = "edge"
    DEFAULT = "default"
    HIGH = "high"


class AppearanceEmbedder:
    """
    Extrator de embeddings de aparência para ReID.

    - Assume um modelo Torch que recebe crops (CHW, float32) e retorna vetores 1D.
    - Embeddings são L2-normalizados para uso em cosine distance.
    - Suporta perfis de ReID: edge / default / high.
    """

    def __init__(
        self,
        profile: str | ReIDProfile | None = None,
        device: Optional[str] = None,
    ):
        # Normaliza profile (fallback para settings.REID_PROFILE_DEFAULT)
        p = (profile or settings.REID_PROFILE_DEFAULT or "default").lower()
        if p not in ("edge", "default", "high"):
            logger.warning("⚠️ Unknown ReID profile '%s', falling back to 'default'", p)
            p = "default"

        self.profile: ReIDProfile = ReIDProfile(p)
        self.device = device or (
            "cuda:0" if torch.cuda.is_available() and settings.USE_GPU else "cpu"
        )

        self.model = self._load_model().to(self.device)
        self.model.eval()
        logger.info("🧬 AppearanceEmbedder initialized on %s (profile=%s)", self.device, self.profile.value)

    # >>> AQUI o trecho que você pediu, com _resolve_model_path <<<
    def _resolve_model_path(self) -> str:
        """
        Resolve o caminho do modelo conforme o profile de ReID.

        Espera que o settings tenha algo como:
          - REID_MODEL_PATH_EDGE
          - REID_MODEL_PATH_DEFAULT
          - REID_MODEL_PATH_HIGH
        """
        if self.profile == ReIDProfile.EDGE:
            path = getattr(settings, "REID_MODEL_PATH_EDGE", None)
        elif self.profile == ReIDProfile.HIGH:
            path = getattr(settings, "REID_MODEL_PATH_HIGH", None)
        else:
            path = getattr(settings, "REID_MODEL_PATH_DEFAULT", None)

        if not path:
            raise RuntimeError(
                f"ReID model path not configured for profile '{self.profile.value}' "
                f"(expected REID_MODEL_PATH_{self.profile.value.upper()})"
            )

        return path

    def _load_model(self) -> torch.nn.Module:
        model_path = self._resolve_model_path()
        logger.info("🔍 Loading ReID model (%s): %s", self.profile.value, model_path)

        try:
            # Tentativa padrão (state_dict / nn.Module)
            model = torch.load(model_path, map_location="cpu")
        except Exception as e:
            # PyTorch 2.6+: TorchScript archive com weights_only=True não é permitido
            msg = str(e)
            if "weights_only=True" in msg or "TorchScript" in msg:
                logger.warning(
                    "⚠️ Detected TorchScript archive for ReID model, "
                    "retrying torch.load with weights_only=False (use only with trusted files)."
                )
                model = torch.load(model_path, map_location="cpu", weights_only=False)
            else:
                raise

        if hasattr(model, "eval"):
            model.eval()
        return model


    @torch.inference_mode()
    def extract_batch(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
    ) -> List[Optional[np.ndarray]]:
        """
        Recebe frame BGR (H, W, 3) e detecções com bbox [x1, y1, x2, y2] em pixels.
        Retorna lista de embeddings (np.ndarray 1D, L2-normalizados) ou None por det.
        """
        if frame is None or not detections:
            return [None] * len(detections)

        H, W, _ = frame.shape

        # Tamanho fixo de entrada do modelo de ReID (OSNet típico: 256x128)
        TARGET_H, TARGET_W = 256, 128

        crops: list[np.ndarray] = []
        valid_idx: list[int] = []

        for idx, det in enumerate(detections):
            x1, y1, x2, y2 = map(int, det["bbox"])

            # Clamp defensivo
            x1 = max(0, min(W - 1, x1))
            x2 = max(0, min(W, x2))
            y1 = max(0, min(H - 1, y1))
            y2 = max(0, min(H, y2))

            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2, :]
            if crop.size == 0:
                continue

            # BGR -> RGB, [0,255] -> [0,1]
            crop_rgb = crop[:, :, ::-1].astype("float32") / 255.0

            # Resize para tamanho fixo (H, W)
            crop_resized = cv2.resize(
                crop_rgb,
                (TARGET_W, TARGET_H),
                interpolation=cv2.INTER_LINEAR,
            )

            # HWC -> CHW
            crop_chw = np.transpose(crop_resized, (2, 0, 1))

            crops.append(crop_chw)
            valid_idx.append(idx)

        if not crops:
            return [None] * len(detections)

        try:
            tensor = torch.from_numpy(np.stack(crops, axis=0)).to(self.device)
        except Exception as e:
            logger.error("❌ Failed to stack crops for ReID: %s", e)
            # Fallback seguro: não quebra o loop, só desliga feature neste frame
            return [None] * len(detections)

        # Normalização padrão (ex: ImageNet mean/std)
        mean = torch.tensor(
            [0.485, 0.456, 0.406],
            device=self.device
        )[None, :, None, None]
        std = torch.tensor(
            [0.229, 0.224, 0.225],
            device=self.device
        )[None, :, None, None]
        tensor = (tensor - mean) / std

        feats = self.model(tensor)  # (N, D)
        feats = F.normalize(feats, p=2, dim=1)  # L2-normaliza

        embeddings: List[Optional[np.ndarray]] = [None] * len(detections)
        for idx, emb in zip(valid_idx, feats):
            embeddings[idx] = emb.detach().cpu().numpy().astype("float32")

        return embeddings



# Cache por profile: evita recarregar modelo para cada câmera
_embedder_cache: dict[str, Optional[AppearanceEmbedder]] = {}

def get_appearance_embedder(profile: Optional[str] = None) -> Optional[AppearanceEmbedder]:
    """
    Retorna (e cria se necessário) um AppearanceEmbedder para o profile dado.

    - profile: "edge" | "default" | "high" | None
      - None -> usa settings.REID_PROFILE_DEFAULT ou "default".
    """
    global _embedder_cache

    key = (profile or settings.REID_PROFILE_DEFAULT or "default").lower()
    if key not in ("edge", "default", "high"):
        logger.warning("⚠️ get_appearance_embedder(): unknown profile '%s', falling back to 'default'", key)
        key = "default"

    if key not in _embedder_cache:
        try:
            _embedder_cache[key] = AppearanceEmbedder(profile=key)
        except Exception as e:
            logger.error("❌ Failed to initialize AppearanceEmbedder (profile=%s): %s", key, e)
            _embedder_cache[key] = None

    return _embedder_cache[key]

