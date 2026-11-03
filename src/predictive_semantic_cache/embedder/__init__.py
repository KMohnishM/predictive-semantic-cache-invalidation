"""Embedder submodule for semantic representations and drift computation."""

try:
    from .embedding_manager import EmbeddingManager
except ImportError:
    EmbeddingManager = None

__all__ = ["EmbeddingManager"]
