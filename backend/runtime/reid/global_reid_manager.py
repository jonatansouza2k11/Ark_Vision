# backend/runtime/reid/global_reid_manager.py
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GlobalTrackProfile:
    """
    Perfil global de uma identidade ReID.

    Armazena um embedding médio (para suavizar ruído) e estatísticas básicas.
    """
    global_id: int
    embedding: np.ndarray  # L2-normalizado
    last_camera_id: int
    last_tracker_type: str
    last_seen_ts: float = field(default_factory=lambda: time.time())
    hits: int = 1

    def update(self, new_embedding: np.ndarray, camera_id: int, tracker_type: str, ts: float) -> None:
        """
        Atualiza o perfil com um novo embedding (média exponencial simples).
        """
        self.last_camera_id = camera_id
        self.last_tracker_type = tracker_type
        self.last_seen_ts = ts
        self.hits += 1

        # Média exponencial para suavizar variações de iluminação / pose
        alpha = 0.2  # peso do embedding novo
        self.embedding = (1.0 - alpha) * self.embedding + alpha * new_embedding
        # Re-normaliza para manter L2 = 1
        norm = np.linalg.norm(self.embedding)
        if norm > 0:
            self.embedding = self.embedding / norm


class GlobalReIDManager:
    """
    Gerenciador global de ReID multi-câmera / multi-tracker.

    Responsabilidades:
    - Manter uma galeria de embeddings globais (global_id).
    - Associar tracks locais (camera_id, tracker_type, track_id) a global_id.
    - Suportar múltiplos trackers por câmera.
    """

    def __init__(
        self,
        sim_threshold: float = 0.7,
        ttl_seconds: float = 60.0,
        max_gallery_size: int = 10000,
    ) -> None:
        """
        Args:
            sim_threshold: limite mínimo de similaridade (cosine) para considerar match.
            ttl_seconds: tempo em segundos para expirar perfis muito antigos.
            max_gallery_size: limite duro de tamanho da galeria (fallback: FIFO simples).
        """
        self._lock = threading.Lock()
        self._next_global_id: int = 1

        # Galeria: global_id -> GlobalTrackProfile
        self._gallery: Dict[int, GlobalTrackProfile] = {}

        # Mapa de conveniência: (camera_id, tracker_type, track_id) -> global_id
        # Útil quando não temos embedding num frame específico.
        self._local_to_global: Dict[Tuple[int, str, int], int] = {}

        self._sim_threshold: float = float(sim_threshold)
        self._ttl_seconds: float = float(ttl_seconds)
        self._max_gallery_size: int = int(max_gallery_size)

        logger.info(
            "🧬 GlobalReIDManager initialized "
            "(sim_threshold=%.3f, ttl=%ss, max_gallery=%d)",
            self._sim_threshold,
            self._ttl_seconds,
            self._max_gallery_size,
        )

    # --------------------------------------------------------------------- #
    # API pública principal
    # --------------------------------------------------------------------- #

    def assign_global_ids(
        self,
        camera_id: int,
        tracker_type: str,
        track_state: Dict[int, Dict[str, Any]],
        embeddings_by_track: Optional[Dict[int, np.ndarray]] = None,
        now: Optional[float] = None,
    ) -> Dict[int, int]:
        """
        Atribui global_id para cada track_id local de uma câmera + tracker.

        - Se tiver embedding para o track_id, tenta achar o melhor match na galeria.
        - Se a similaridade >= sim_threshold, reaproveita global_id existente.
        - Caso contrário, cria um novo global_id.
        - Se não houver embedding, tenta reutilizar mapeamento anterior (local_to_global).

        Args:
            camera_id: ID da câmera.
            tracker_type: Tipo de tracker (ex: 'yolo_bytetrack', 'strongsort').
            track_state: dict {track_id: {...}} vindo do TrackerManager.
            embeddings_by_track: dict {track_id: np.ndarray L2-normalizado} (opcional).
            now: timestamp opcional (segundos). Se None, usa time.time().

        Returns:
            Dict {track_id: global_id} para todos os tracks presentes no track_state.
        """
        if not track_state:
            return {}

        ts = now if now is not None else time.time()
        embeddings_by_track = embeddings_by_track or {}

        with self._lock:
            self._prune_expired(ts)

            mapping: Dict[int, int] = {}
            # Pré-computa estrutura para busca (matriz de embeddings da galeria)
            gallery_ids, gallery_matrix = self._build_gallery_matrix()

            for track_id in track_state.keys():
                key = (camera_id, tracker_type, int(track_id))

                emb = embeddings_by_track.get(track_id)
                if emb is not None:
                    # Garante que é np.ndarray float32 L2-normalizado
                    emb = self._ensure_l2_normalized(emb)

                    if gallery_matrix is not None and len(gallery_ids) > 0:
                        global_id = self._match_or_create(
                            emb=emb,
                            camera_id=camera_id,
                            tracker_type=tracker_type,
                            ts=ts,
                            gallery_ids=gallery_ids,
                            gallery_matrix=gallery_matrix,
                        )
                        # Atualiza mapeamento local
                        self._local_to_global[key] = global_id
                        mapping[track_id] = global_id
                    else:
                        # Galeria vazia → sempre cria primeiro global_id
                        global_id = self._create_global_profile(
                            emb, camera_id=camera_id, tracker_type=tracker_type, ts=ts
                        )
                        self._local_to_global[key] = global_id
                        mapping[track_id] = global_id

                        # Galeria mudou; reconstrói estruturas para próximos tracks
                        gallery_ids, gallery_matrix = self._build_gallery_matrix()
                else:
                    # Sem embedding neste frame → tenta reaproveitar mapeamento local
                    if key in self._local_to_global:
                        mapping[track_id] = self._local_to_global[key]
                    else:
                        # Sem embedding e sem histórico: não força criação de global_id.
                        # Você pode optar por forçar criação se quiser consistência absoluta.
                        logger.debug(
                            "GlobalReID: no embedding and no history for "
                            "camera=%s tracker=%s track_id=%s",
                            camera_id,
                            tracker_type,
                            track_id,
                        )

            return mapping

    # --------------------------------------------------------------------- #
    # Internals: galeria e matching
    # --------------------------------------------------------------------- #

    def _build_gallery_matrix(self) -> Tuple[np.ndarray | None, np.ndarray | None]:
        """
        Constrói uma matriz (N, D) com embeddings da galeria para busca rápida.

        Returns:
            gallery_ids: np.ndarray shape (N,) com global_ids.
            gallery_matrix: np.ndarray shape (N, D) com embeddings.
        """
        if not self._gallery:
            return None, None

        ids = np.array(list(self._gallery.keys()), dtype=np.int32)
        embs = np.stack([p.embedding for p in self._gallery.values()], axis=0)
        return ids, embs

    def _ensure_l2_normalized(self, emb: np.ndarray) -> np.ndarray:
        arr = np.asarray(emb, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def _match_or_create(
        self,
        emb: np.ndarray,
        camera_id: int,
        tracker_type: str,
        ts: float,
        gallery_ids: np.ndarray,
        gallery_matrix: np.ndarray,
    ) -> int:
        """
        Tenta encontrar o melhor match na galeria; se não encontrar, cria novo global_id.
        """
        # Cosine similarity = dot(emb, gallery_emb) (ambos L2-normalizados)
        sims = gallery_matrix @ emb  # shape (N,)
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_global_id = int(gallery_ids[best_idx])

        if best_sim >= self._sim_threshold:
            profile = self._gallery[best_global_id]
            profile.update(
                new_embedding=emb,
                camera_id=camera_id,
                tracker_type=tracker_type,
                ts=ts,
            )
            logger.debug(
                "GlobalReID: matched global_id=%s (sim=%.3f, hits=%d)",
                best_global_id,
                best_sim,
                profile.hits,
            )
            return best_global_id

        # Similaridade baixa → cria novo perfil global
        new_global_id = self._create_global_profile(
            emb, camera_id=camera_id, tracker_type=tracker_type, ts=ts
        )
        logger.debug(
            "GlobalReID: created new global_id=%s (best_sim=%.3f < %.3f)",
            new_global_id,
            best_sim,
            self._sim_threshold,
        )
        return new_global_id

    def _create_global_profile(
        self,
        emb: np.ndarray,
        camera_id: int,
        tracker_type: str,
        ts: float,
    ) -> int:
        if len(self._gallery) >= self._max_gallery_size:
            # Estratégia simples: remove o mais antigo
            oldest_id = min(
                self._gallery.items(), key=lambda kv: kv[1].last_seen_ts
            )[0]
            logger.warning(
                "GlobalReID: gallery full (%d). Evicting oldest global_id=%s",
                self._max_gallery_size,
                oldest_id,
            )
            self._gallery.pop(oldest_id, None)
            # Não limpamos _local_to_global aqui; TTL cuidará disso com o tempo.

        global_id = self._next_global_id
        self._next_global_id += 1

        profile = GlobalTrackProfile(
            global_id=global_id,
            embedding=emb,
            last_camera_id=camera_id,
            last_tracker_type=tracker_type,
            last_seen_ts=ts,
            hits=1,
        )
        self._gallery[global_id] = profile
        logger.debug(
            "GlobalReID: new profile created global_id=%s (camera=%s, tracker=%s)",
            global_id,
            camera_id,
            tracker_type,
        )
        return global_id

    def _prune_expired(self, now: float) -> None:
        """
        Remove perfis e mapeamentos muito antigos (TTL).
        """
        if self._ttl_seconds <= 0:
            return

        to_delete = [
            gid
            for gid, profile in self._gallery.items()
            if (now - profile.last_seen_ts) > self._ttl_seconds
        ]
        for gid in to_delete:
            logger.debug("GlobalReID: expiring global_id=%s", gid)
            self._gallery.pop(gid, None)

        # Opcional: também limpar _local_to_global baseado em TTL fraco
        # (não temos timestamp por chave, então limpamos nunca ou muito raramente).
        # Mantemos simples por enquanto.

    # --------------------------------------------------------------------- #
    # APIs auxiliares / debug
    # --------------------------------------------------------------------- #

    def get_gallery_size(self) -> int:
        with self._lock:
            return len(self._gallery)

    def clear(self) -> None:
        """
        Limpa galeria e mapeamentos locais (para testes / reset).
        """
        with self._lock:
            self._gallery.clear()
            self._local_to_global.clear()
            self._next_global_id = 1
            logger.info("GlobalReIDManager cleared (gallery + mappings).")


# Singleton global
_global_reid_manager: Optional[GlobalReIDManager] = None
_global_reid_lock = threading.Lock()


def get_global_reid_manager() -> GlobalReIDManager:
    """
    Retorna (e cria se necessário) o singleton de GlobalReIDManager.
    """
    global _global_reid_manager
    if _global_reid_manager is None:
        with _global_reid_lock:
            if _global_reid_manager is None:
                _global_reid_manager = GlobalReIDManager()
    return _global_reid_manager
