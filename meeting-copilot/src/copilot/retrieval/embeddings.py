"""Embedding backends.

``Embedder`` is the interface. The default real backend is
sentence-transformers (lazy import). A dependency-free ``HashingEmbedder`` is
provided as a deterministic fallback so retrieval — and its tests — work
without downloading any models. The fallback is intentionally simple; for
production quality install the ``retrieval`` extra.
"""

from __future__ import annotations

import abc
import hashlib
import re
from typing import List, Optional

import numpy as np

_TOKEN = re.compile(r"[a-z0-9']+")


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


class Embedder(abc.ABC):
    dim: int

    @abc.abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalised embeddings."""

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


class HashingEmbedder(Embedder):
    """Deterministic hashing bag-of-words embedder (no external deps).

    Maps tokens into a fixed-dimensional space via hashing. Good enough for
    grounding/retrieval tests and as an offline fallback; not as accurate as a
    trained sentence encoder.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _TOKEN.findall(text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign
        return _normalize(vec)

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self._embed_text(t) for t in texts]).astype(np.float32)


class SentenceTransformerEmbedder(Embedder):
    """sentence-transformers backend (e.g. all-MiniLM-L6-v2), lazily loaded."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self.dim = 384  # all-MiniLM-L6-v2; corrected on first load

    def _ensure(self):  # pragma: no cover - optional heavy dep
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. Install with: "
                    "pip install 'meeting-copilot[retrieval]'"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
            self.dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:  # pragma: no cover - heavy dep
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        model = self._ensure()
        vecs = model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)


def default_embedder() -> Embedder:
    """Return a sentence-transformer embedder if available, else the fallback."""
    try:  # pragma: no cover - depends on environment
        import sentence_transformers  # noqa: F401

        return SentenceTransformerEmbedder()
    except Exception:
        return HashingEmbedder()
