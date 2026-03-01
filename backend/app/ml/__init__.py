# backend/app/ml/__init__.py

from .embedder import Embedder

# Module-level singleton — loaded once when FastAPI starts
_embedder_instance: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance