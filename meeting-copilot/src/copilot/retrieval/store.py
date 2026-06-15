"""Vector index + retrieval over transcript segments.

Embeds finalized segments and supports cosine top-k search. Persists vectors to
the SQLite store so past meetings remain searchable. A numpy brute-force index
is used by default (exact, dependency-free); the same interface can be backed
by sqlite-vec or FAISS for scale.

Retrieval returns snippets *with their source span and timestamps* so the AI
layer can ground suggestions and surface citations — central to the
anti-hallucination design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from copilot.core.models import Citation, TranscriptSegment
from copilot.retrieval.embeddings import Embedder, default_embedder
from copilot.store.db import Store


@dataclass
class RetrievedSnippet:
    """A retrieved transcript segment with its similarity score."""

    segment: TranscriptSegment
    score: float

    def as_citation(self) -> Citation:
        return Citation(
            segment_id=self.segment.id,
            start=self.segment.start,
            end=self.segment.end,
            quote=self.segment.text,
        )


class RetrievalStore:
    """Indexes segments and answers nearest-neighbour queries."""

    def __init__(self, store: Store, embedder: Optional[Embedder] = None):
        self.store = store
        self.embedder = embedder or default_embedder()
        self._ids: List[int] = []
        self._segments: dict[int, TranscriptSegment] = {}
        self._matrix: Optional[np.ndarray] = None
        self._load_existing()

    # -- indexing ----------------------------------------------------------
    def _load_existing(self) -> None:
        seg_by_id = {s.id: s for s in self.store.all_segments() if s.id is not None}
        vectors = []
        ids = []
        for seg_id, dim, blob in self.store.iter_embeddings():
            if seg_id not in seg_by_id:
                continue
            vec = np.frombuffer(blob, dtype=np.float32)
            if vec.shape[0] != dim:
                continue
            vectors.append(vec)
            ids.append(seg_id)
            self._segments[seg_id] = seg_by_id[seg_id]
        if vectors:
            self._ids = ids
            self._matrix = np.vstack(vectors).astype(np.float32)

    def index_segment(self, segment: TranscriptSegment) -> None:
        """Embed and persist a finalized segment, adding it to the live index."""
        if segment.id is None:
            raise ValueError("segment must be persisted (have an id) before indexing")
        vec = self.embedder.embed_one(segment.text).astype(np.float32)
        self.store.save_embedding(segment.id, vec.tobytes(), int(vec.shape[0]))
        self._segments[segment.id] = segment
        self._ids.append(segment.id)
        if self._matrix is None:
            self._matrix = vec.reshape(1, -1)
        else:
            self._matrix = np.vstack([self._matrix, vec.reshape(1, -1)])

    # -- search ------------------------------------------------------------
    def search(self, query: str, k: int = 5,
               exclude_after: Optional[float] = None,
               meeting_id: Optional[int] = None) -> List[RetrievedSnippet]:
        """Return up to ``k`` most similar segments to ``query``.

        ``exclude_after`` drops segments whose start >= the given timestamp
        (useful to avoid retrieving the very lines being responded to).
        ``meeting_id`` restricts to a single meeting when provided.
        """
        if self._matrix is None or not self._ids:
            return []
        q = self.embedder.embed_one(query).astype(np.float32)
        if np.linalg.norm(q) == 0:
            return []
        sims = self._matrix @ q  # vectors are L2-normalised → cosine similarity
        order = np.argsort(-sims)
        results: List[RetrievedSnippet] = []
        for idx in order:
            seg_id = self._ids[idx]
            seg = self._segments.get(seg_id)
            if seg is None:
                continue
            if meeting_id is not None and seg.meeting_id != meeting_id:
                continue
            if exclude_after is not None and seg.start >= exclude_after:
                continue
            results.append(RetrievedSnippet(segment=seg, score=float(sims[idx])))
            if len(results) >= k:
                break
        return results

    @property
    def size(self) -> int:
        return len(self._ids)
