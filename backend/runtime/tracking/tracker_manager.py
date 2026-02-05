"""
backend/runtime/tracking/tracker_manager.py - v1.0

Gerenciador de trackers multi-câmera / multi-tipo.

Objetivos:
- Governança forte por camera_id + tracker_type
- Pronto para múltiplos algoritmos: ByteTrack, BoT-SORT, StrongSORT
- Escalável (O(N²) em N tracks/dets, com N pequeno típico por câmera)
- Sem dependências externas (apenas numpy), pronto para ReID via embeddings

Formato de detecções de entrada:
    detection = {
        "bbox": [x1, y1, x2, y2],  # coordenadas em pixels
        "class_id": int,
        "confidence": float,
        # opcional:
        # "feature": np.ndarray (embedding de ReID normalizado)
    }

Formato de saída (track_state):
    {
        track_id: {
            "bbox": [x1, y1, x2, y2],
            "class_id": int,
            "confidence": float,
        },
        ...
    }
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from backend.core.config.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# TIPOS BÁSICOS
# ============================================================================


@dataclass
class Track:
    """Estado interno de um track."""

    track_id: int
    bbox: np.ndarray  # [x1, y1, x2, y2] em pixels
    class_id: int
    confidence: float
    feature: Optional[np.ndarray] = None  # embedding de ReID (opcional)

    last_update: float = field(default_factory=lambda: time.time())
    age: int = 1
    hits: int = 1
    time_since_update: int = 0
    is_confirmed: bool = False

    def to_state_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox.astype(float).tolist(),
            "class_id": int(self.class_id),
            "confidence": float(self.confidence),
        }


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def _bbox_iou_matrix(
    tracks: List[Track], detections: List[Dict[str, Any]]
) -> np.ndarray:
    """
    Calcula matriz de IoU entre tracks e detecções.

    Retorno: matriz (num_tracks x num_dets) com IoU em [0, 1].
    """
    if not tracks or not detections:
        return np.zeros((len(tracks), len(detections)), dtype=np.float32)

    track_boxes = np.array([t.bbox for t in tracks], dtype=np.float32)
    det_boxes = np.array([d["bbox"] for d in detections], dtype=np.float32)

    # track_boxes: (T, 4) = [x1, y1, x2, y2]
    # det_boxes:   (D, 4)

    # Expand dims para broadcast
    t_x1 = track_boxes[:, 0:1]
    t_y1 = track_boxes[:, 1:2]
    t_x2 = track_boxes[:, 2:3]
    t_y2 = track_boxes[:, 3:4]

    d_x1 = det_boxes[:, 0:1].T
    d_y1 = det_boxes[:, 1:2].T
    d_x2 = det_boxes[:, 2:3].T
    d_y2 = det_boxes[:, 3:4].T

    inter_x1 = np.maximum(t_x1, d_x1)
    inter_y1 = np.maximum(t_y1, d_y1)
    inter_x2 = np.minimum(t_x2, d_x2)
    inter_y2 = np.minimum(t_y2, d_y2)

    inter_w = np.clip(inter_x2 - inter_x1, a_min=0.0, a_max=None)
    inter_h = np.clip(inter_y2 - inter_y1, a_min=0.0, a_max=None)
    inter_area = inter_w * inter_h

    track_area = (t_x2 - t_x1) * (t_y2 - t_y1)
    det_area = (d_x2 - d_x1) * (d_y2 - d_y1)
    union_area = track_area + det_area - inter_area

    iou = np.where(union_area > 0.0, inter_area / union_area, 0.0)
    return iou.astype(np.float32)


def _greedy_match(
    cost_matrix: np.ndarray,
    iou_threshold: float,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Matching guloso baseado em IoU (maior IoU primeiro):

    cost_matrix: matriz IoU (T x D)
    Retorna:
        matches: lista de pares (track_idx, det_idx)
        unmatched_tracks: índices de tracks sem match
        unmatched_dets: índices de dets sem match
    """
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    num_tracks, num_dets = cost_matrix.shape
    matched_tracks: set[int] = set()
    matched_dets: set[int] = set()
    matches: List[Tuple[int, int]] = []

    # Flatten e ordenar por IoU decrescente
    flat_indices = np.argsort(cost_matrix, axis=None)[::-1]

    for flat_idx in flat_indices:
        t_idx = flat_idx // num_dets
        d_idx = flat_idx % num_dets

        if t_idx in matched_tracks or d_idx in matched_dets:
            continue

        iou_val = cost_matrix[t_idx, d_idx]
        if iou_val < iou_threshold:
            break

        matched_tracks.add(t_idx)
        matched_dets.add(d_idx)
        matches.append((t_idx, d_idx))

    unmatched_tracks = [i for i in range(num_tracks) if i not in matched_tracks]
    unmatched_dets = [j for j in range(num_dets) if j not in matched_dets]

    return matches, unmatched_tracks, unmatched_dets


# ============================================================================
# BASE TRACKER
# ============================================================================


class BaseTracker:
    """
    Tracker base. Subclasses podem customizar:
    - thresholds de confiança
    - thresholds de IoU
    - combinação IoU + ReID
    """

    def __init__(
        self,
        iou_threshold: float,
        ttl_seconds: float,
        min_confirmed_hits: int = 1,
        name: str = "base",
    ):
        self._tracks: Dict[int, Track] = {}
        self._next_track_id: int = 1
        self._iou_threshold = float(iou_threshold)
        self._ttl_seconds = float(ttl_seconds)
        self._min_confirmed_hits = int(min_confirmed_hits)
        self._name = name

    # ------------------------------------------------------------------ #
    # API principal
    # ------------------------------------------------------------------ #

    def update(
        self,
        detections: List[Dict[str, Any]],
        timestamp: Optional[float] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Atualiza o estado de tracking com as novas detecções.

        Retorna track_state pronto para o VisionSystem.
        """
        now = timestamp if timestamp is not None else time.time()

        # Atualiza contadores de idade / time_since_update
        for track in self._tracks.values():
            track.age += 1
            track.time_since_update += 1

        if not detections:
            # Apenas aplica TTL / limpeza
            self._prune_stale_tracks(now)
            return {tid: t.to_state_dict() for tid, t in self._tracks.items()}

        matches, unmatched_tracks, unmatched_dets = self._associate(detections)

        # Atualiza tracks casados
        tracks_list = list(self._tracks.values())
        for t_idx, d_idx in matches:
            track = tracks_list[t_idx]
            det = detections[d_idx]

            track.bbox = np.array(det["bbox"], dtype=np.float32)
            track.class_id = int(det["class_id"])
            track.confidence = float(det["confidence"])
            track.last_update = now
            track.hits += 1
            track.time_since_update = 0
            if track.hits >= self._min_confirmed_hits:
                track.is_confirmed = True

        # Cria tracks novos para detecções não casadas
        for d_idx in unmatched_dets:
            det = detections[d_idx]
            self._create_track(det, now)

        # Limpa tracks obsoletos
        self._prune_stale_tracks(now)

        # Retorno: apenas tracks confirmados ou recentes
        return {
            track_id: track.to_state_dict()
            for track_id, track in self._tracks.items()
            if track.is_confirmed or track.time_since_update == 0
        }

    # ------------------------------------------------------------------ #
    # Métodos que subclasses podem customizar
    # ------------------------------------------------------------------ #

    def _associate(
        self,
        detections: List[Dict[str, Any]],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associação padrão: IoU puro com threshold único.
        """
        tracks_list = list(self._tracks.values())
        if not tracks_list or not detections:
            return [], list(range(len(tracks_list))), list(range(len(detections)))

        iou_matrix = _bbox_iou_matrix(tracks_list, detections)

        # Opcional: filtrar por class_id (só associa mesmo tipo)
        for i, track in enumerate(tracks_list):
            for j, det in enumerate(detections):
                if det["class_id"] != track.class_id:
                    iou_matrix[i, j] = 0.0

        matches, unmatched_tracks, unmatched_dets = _greedy_match(
            iou_matrix, self._iou_threshold
        )
        return matches, unmatched_tracks, unmatched_dets


    def _create_track(self, det: Dict[str, Any], now: float) -> None:
        bbox = np.array(det["bbox"], dtype=np.float32)
        class_id = int(det["class_id"])
        confidence = float(det["confidence"])
        feature = det.get("feature")

        track = Track(
            track_id=self._next_track_id,
            bbox=bbox,
            class_id=class_id,
            confidence=confidence,
            feature=feature,
            last_update=now,
            age=1,
            hits=1,
            time_since_update=0,
            is_confirmed=False,
        )
        self._tracks[self._next_track_id] = track
        self._next_track_id += 1


    def _prune_stale_tracks(self, now: float) -> None:
        """
        Remove tracks que não foram atualizados dentro do TTL.
        """
        to_remove: List[int] = []
        for track_id, track in self._tracks.items():
            if (now - track.last_update) > self._ttl_seconds:
                to_remove.append(track_id)

        for track_id in to_remove:
            del self._tracks[track_id]

        if to_remove:
            logger.debug(
                f"[Tracker:{self._name}] Removed {len(to_remove)} stale tracks "
                f"(ttl={self._ttl_seconds}s)"
            )


# ============================================================================
# BYTE-TRACK-LIKE TRACKER
# ============================================================================


class ByteTrackLikeTracker(BaseTracker):
    """
    Implementação inspirada no ByteTrack:

    - Dois thresholds de confiança: alto/baixo
    - Primeiro associa tracks com detecções de alta confiança
    - Depois, tenta associar tracks remanescentes com detecções de baixa
      confiança (para manter rastros "fracos" vivos).

    Observação: esta é uma versão simplificada, sem conjunto explícito de
    'lost tracks', mas respeita a filosofia do ByteTrack.
    """

    def __init__(
        self,
        high_conf_threshold: float,
        low_conf_threshold: float,
        iou_high: float,
        iou_low: float,
        ttl_seconds: float,
        min_confirmed_hits: int = 2,
    ):
        super().__init__(
            iou_threshold=iou_high,
            ttl_seconds=ttl_seconds,
            min_confirmed_hits=min_confirmed_hits,
            name="bytetrack_like",
        )
        self._high_conf = float(high_conf_threshold)
        self._low_conf = float(low_conf_threshold)
        self._iou_high = float(iou_high)
        self._iou_low = float(iou_low)

    def update(
        self,
        detections: List[Dict[str, Any]],
        timestamp: Optional[float] = None,
    ) -> Dict[int, Dict[str, Any]]:
        now = timestamp if timestamp is not None else time.time()

        for track in self._tracks.values():
            track.age += 1
            track.time_since_update += 1

        if not detections:
            self._prune_stale_tracks(now)
            return {tid: t.to_state_dict() for tid, t in self._tracks.items()}

        # Split por confiança
        high_dets: List[Dict[str, Any]] = []
        low_dets: List[Dict[str, Any]] = []

        for det in detections:
            conf = float(det["confidence"])
            if conf >= self._high_conf:
                high_dets.append(det)
            elif conf >= self._low_conf:
                low_dets.append(det)
            # abaixo de low_conf: ignorado

        tracks_list = list(self._tracks.values())

        # 1) Associação com detecções de alta confiança
        matches_high, unmatched_tracks_idx, unmatched_high_idx = self._associate_subset(
            tracks_list, high_dets, self._iou_high
        )

        # Atualiza matches de alta confiança
        for t_idx, d_idx in matches_high:
            track = tracks_list[t_idx]
            det = high_dets[d_idx]
            track.bbox = np.array(det["bbox"], dtype=np.float32)
            track.class_id = int(det["class_id"])
            track.confidence = float(det["confidence"])
            track.last_update = now
            track.hits += 1
            track.time_since_update = 0
            if track.hits >= self._min_confirmed_hits:
                track.is_confirmed = True

        # Tracks remanescentes para tentar casar com low_conf
        remaining_tracks = [tracks_list[i] for i in unmatched_tracks_idx]

        # 2) Associação com detecções de baixa confiança
        matches_low: List[Tuple[int, int]] = []
        unmatched_low_idx: List[int] = list(range(len(low_dets)))

        if remaining_tracks and low_dets:
            iou_matrix_low = _bbox_iou_matrix(remaining_tracks, low_dets)

            # filtra por class_id
            for i, track in enumerate(remaining_tracks):
                for j, det in enumerate(low_dets):
                    if det["class_id"] != track.class_id:
                        iou_matrix_low[i, j] = 0.0

            m_low, unmatched_tracks_low, unmatched_low_idx = _greedy_match(
                iou_matrix_low, self._iou_low
            )

            # m_low tem índices relativos a remaining_tracks
            # precisamos mapear para índices de tracks_list
            for rt_idx, d_idx in m_low:
                track = remaining_tracks[rt_idx]
                det = low_dets[d_idx]
                track.bbox = np.array(det["bbox"], dtype=np.float32)
                track.class_id = int(det["class_id"])
                track.confidence = float(det["confidence"])
                track.last_update = now
                track.hits += 1
                track.time_since_update = 0
                if track.hits >= self._min_confirmed_hits:
                    track.is_confirmed = True

            matches_low = m_low  # apenas pra logging se quiser

        # 3) Cria novos tracks para detecções de alta confiança sem match
        for d_idx in unmatched_high_idx:
            det = high_dets[d_idx]
            self._create_track(det, now)

        # (opcional) criar tracks também a partir de low_conf sem match:
        # isso depende da agressividade desejada; aqui mantemos conservador.
        # for d_idx in unmatched_low_idx:
        #     det = low_dets[d_idx]
        #     self._create_track(det, now)

        self._prune_stale_tracks(now)

        return {
            track_id: track.to_state_dict()
            for track_id, track in self._tracks.items()
            if track.is_confirmed or track.time_since_update == 0
        }


    def _associate_subset(
        self,
        tracks_list: List[Track],
        detections: List[Dict[str, Any]],
        iou_threshold: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        if not tracks_list or not detections:
            return [], list(range(len(tracks_list))), list(range(len(detections)))

        iou_matrix = _bbox_iou_matrix(tracks_list, detections)

        # filtra por class_id
        for i, track in enumerate(tracks_list):
            for j, det in enumerate(detections):
                if det["class_id"] != track.class_id:
                    iou_matrix[i, j] = 0.0

        matches, unmatched_tracks, unmatched_dets = _greedy_match(
            iou_matrix, iou_threshold
        )
        return matches, unmatched_tracks, unmatched_dets


# ============================================================================
# BOT-SORT-LIKE / STRONGSORT-LIKE
# ============================================================================


class AppearanceAwareTracker(BaseTracker):
    """
    Tracker genérico sensível à aparência (BoT-SORT / StrongSORT-like).

    - Combina IoU com distância de ReID (se feature estiver presente).
    - Quando não há embeddings, cai para IoU puro.
    """

    def __init__(
        self,
        iou_threshold: float,
        ttl_seconds: float,
        min_confirmed_hits: int = 2,
        alpha_iou: float = 0.5,
        name: str = "appearance",
    ):
        super().__init__(
            iou_threshold=iou_threshold,
            ttl_seconds=ttl_seconds,
            min_confirmed_hits=min_confirmed_hits,
            name=name,
        )
        self._alpha_iou = float(alpha_iou)

    def _associate(
        self,
        detections: List[Dict[str, Any]],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        tracks_list = list(self._tracks.values())
        if not tracks_list or not detections:
            return [], list(range(len(tracks_list))), list(range(len(detections)))

        iou_matrix = _bbox_iou_matrix(tracks_list, detections)

        # Matriz de distância de aparência (0–1), 0 = idêntico, 1 = totalmente diferente
        app_dist = np.zeros_like(iou_matrix, dtype=np.float32)

        any_feature = False
        for i, track in enumerate(tracks_list):
            if track.feature is None:
                continue
            for j, det in enumerate(detections):
                feat = det.get("feature")
                if feat is None:
                    continue
                # Assume embeddings L2-normalizados
                any_feature = True
                # Distância coseno ~ 1 - dot
                sim = float(np.clip(np.dot(track.feature, feat), -1.0, 1.0))
                app_dist[i, j] = 1.0 - ((sim + 1.0) / 2.0)

        # Se não há nenhuma feature, volta para IoU puro
        if not any_feature:
            # filtra por class_id
            for i, track in enumerate(tracks_list):
                for j, det in enumerate(detections):
                    if det["class_id"] != track.class_id:
                        iou_matrix[i, j] = 0.0

            matches, unmatched_tracks, unmatched_dets = _greedy_match(
                iou_matrix, self._iou_threshold
            )
            return matches, unmatched_tracks, unmatched_dets

        # Combina IoU e distância de aparência:
        # score alto = melhor
        # score = alpha * IoU + (1 - alpha) * (1 - app_dist)
        score = self._alpha_iou * iou_matrix + (1.0 - self._alpha_iou) * (
            1.0 - app_dist
        )

        # Gating básico: se IoU < um determinado threshold, zera o score
        for i, track in enumerate(tracks_list):
            for j, det in enumerate(detections):
                if det["class_id"] != track.class_id or iou_matrix[i, j] < (
                    self._iou_threshold * 0.5
                ):
                    score[i, j] = 0.0

        matches, unmatched_tracks, unmatched_dets = _greedy_match(
            score, iou_threshold=self._iou_threshold
        )
        return matches, unmatched_tracks, unmatched_dets


class BotSortLikeTracker(AppearanceAwareTracker):
    def __init__(self):
        super().__init__(
            iou_threshold=settings.TRACKING_IOU_THRESHOLD,
            ttl_seconds=settings.TRACKING_TTL_SECONDS,
            min_confirmed_hits=2,
            alpha_iou=0.6,
            name="botsort_like",
        )


class StrongSortLikeTracker(AppearanceAwareTracker):
    def __init__(self):
        # Dá mais peso à aparência
        super().__init__(
            iou_threshold=settings.TRACKING_IOU_THRESHOLD,
            ttl_seconds=settings.TRACKING_TTL_SECONDS,
            min_confirmed_hits=2,
            alpha_iou=0.3,
            name="strongsort_like",
        )


class IdentityTracker(BaseTracker):
    """
    Tracker "burro" que não tenta manter identidade real, apenas cria novos IDs em cada frame. Útil para debug / fallback.
    """

    def __init__(self):
        super().__init__(
            iou_threshold=0.0,
            ttl_seconds=0.1,
            min_confirmed_hits=1,
            name="identity",
        )

    def _associate(
        self,
        detections: List[Dict[str, Any]],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        # Não associa nada, força criação de novos tracks
        return [], list(range(len(self._tracks))), list(range(len(detections)))


# ============================================================================
# TRACKER MANAGER (MULTI-CAMERA)
# ============================================================================


class TrackerManager:
    """
    Gerencia instâncias de trackers por câmera + tipo.

    Uso:
        manager = get_tracker_manager()
        track_state = manager.update(
            camera_id=ctx.camera_id,
            tracker_type=ctx.tracker_type,
            detections=detections,
        )
    """

    def __init__(self):
        # camera_id -> tracker_type -> BaseTracker
        self._trackers: Dict[int, Dict[str, BaseTracker]] = {}

        # thresholds derivados das settings globais
        self._iou_threshold = settings.TRACKING_IOU_THRESHOLD
        self._ttl_seconds = settings.TRACKING_TTL_SECONDS
        self._yolo_conf = settings.YOLO_CONF_THRESHOLD

        # thresholds para ByteTrack-like
        self._byt_high_conf = self._yolo_conf
        self._byt_low_conf = max(0.1, self._yolo_conf * 0.5)
        self._byt_iou_high = self._iou_threshold
        self._byt_iou_low = max(0.1, self._iou_threshold * 0.5)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #

    def update(
        self,
        camera_id: int,
        tracker_type: str,
        detections: List[Dict[str, Any]],
        timestamp: Optional[float] = None,
    ) -> Dict[int, Dict[str, Any]]:
        tracker_type_norm = self._normalize_tracker_type(tracker_type)
        tracker = self._get_or_create_tracker(camera_id, tracker_type_norm)
        return tracker.update(detections, timestamp=timestamp)

    # ------------------------------------------------------------------ #
    # Helpers internos
    # ------------------------------------------------------------------ #

    def _normalize_tracker_type(self, tracker_type: str) -> str:
        """
        Normaliza o nome do tracker vindo do frontend/DB para um tipo canônico
        interno usado pelo TrackerManager.

        Aliases suportados (case-insensitive, com trim):

        - ByteTrack-like:
        "yolo_bytetrack", "bytetrack", "byte", "byte_track", "simple"

        - BoT-SORT-like:
        "yolo_botsort", "yolo_botsort_fast", "botsort", "bot_sort", "bot"

        - StrongSORT-like (appearance-aware):
        "yolo_botsort_strong", "yolo_strongsort", "strongsort", "strong",
        "fast_strongsort", "yolo_strongsort_fast", "faststrongsort"

        - Identity (debug/fallback):
        "none", "off", "disabled"

        Qualquer outro valor cai no default global "bytetrack".
        """
        t = (tracker_type or "").strip().lower()

        # Aliases compatíveis com o frontend para ByteTrack-like
        if t in ("yolo_bytetrack", "bytetrack", "byte", "byte_track", "simple"):
            return "bytetrack"

        # Aliases para BoT-SORT-like
        if t in (
            "yolo_botsort",
            "yolo_botsort_fast",
            "botsort",
            "bot_sort",
            "bot",
        ):
            return "botsort"

        # Aliases para StrongSORT-like (inclui variantes "fast_*")
        if t in (
            "yolo_botsort_strong",
            "yolo_strongsort",
            "strongsort",
            "strong",
            "fast_strongsort",
            "yolo_strongsort_fast",
            "faststrongsort",
        ):
            return "strongsort"

        # Identity tracker (sem manutenção real de ID)
        if t in ("none", "off", "disabled"):
            return "identity"

        # Default global seguro
        return "bytetrack"



    def _get_or_create_tracker(
        self,
        camera_id: int,
        tracker_type: str,
    ) -> BaseTracker:
        if camera_id not in self._trackers:
            self._trackers[camera_id] = {}

        cam_trackers = self._trackers[camera_id]

        if tracker_type in cam_trackers:
            return cam_trackers[tracker_type]

        # Cria tracker novo conforme tipo
        if tracker_type == "bytetrack":
            tracker = ByteTrackLikeTracker(
                high_conf_threshold=self._byt_high_conf,
                low_conf_threshold=self._byt_low_conf,
                iou_high=self._byt_iou_high,
                iou_low=self._byt_iou_low,
                ttl_seconds=self._ttl_seconds,
                min_confirmed_hits=2,
            )
        elif tracker_type == "botsort":
            tracker = BotSortLikeTracker()
        elif tracker_type == "strongsort":
            tracker = StrongSortLikeTracker()
        elif tracker_type == "identity":
            tracker = IdentityTracker()
        else:
            # Fallback seguro
            logger.warning(
                f"⚠️ Unknown tracker_type='{tracker_type}' for camera {camera_id}, "
                f"falling back to ByteTrack-like."
            )
            tracker = ByteTrackLikeTracker(
                high_conf_threshold=self._byt_high_conf,
                low_conf_threshold=self._byt_low_conf,
                iou_high=self._byt_iou_high,
                iou_low=self._byt_iou_low,
                ttl_seconds=self._ttl_seconds,
                min_confirmed_hits=2,
            )

        cam_trackers[tracker_type] = tracker
        logger.info(
            f"🧭 Tracker created: camera_id={camera_id}, "
            f"type={tracker_type}, class={tracker.__class__.__name__}"
        )
        return tracker


# ============================================================================
# SINGLETON PÚBLICO
# ============================================================================

_default_tracker_manager: Optional[TrackerManager] = None


def get_tracker_manager() -> TrackerManager:
    global _default_tracker_manager
    if _default_tracker_manager is None:
        _default_tracker_manager = TrackerManager()
    return _default_tracker_manager
