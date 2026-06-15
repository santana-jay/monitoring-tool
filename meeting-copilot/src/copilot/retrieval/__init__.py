"""Retrieval layer."""

from copilot.retrieval.embeddings import (
    Embedder,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    default_embedder,
)
from copilot.retrieval.store import RetrievalStore, RetrievedSnippet

__all__ = [
    "Embedder",
    "HashingEmbedder",
    "SentenceTransformerEmbedder",
    "default_embedder",
    "RetrievalStore",
    "RetrievedSnippet",
]
