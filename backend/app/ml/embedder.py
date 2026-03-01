# backend/app/ml/embedder.py

import time
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class Embedder:
    """
    Singleton-safe wrapper around BAAI/bge-small-en-v1.5.
    Loads model once. encode() returns a normalized float32 vector.
    Target: <200ms per inference.
    """

    def __init__(self):
        logger.info(f"[Embedder] Loading model: {MODEL_NAME}")
        t0 = time.perf_counter()
        self.model = SentenceTransformer(MODEL_NAME)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[Embedder] Model loaded in {elapsed:.1f}ms")

    def encode(self, text: str) -> list[float]:
        """
        Encode a single text string into a normalized 384-dim vector.
        Returns: list[float] — compatible with pgvector literal casting.
        """
        t0 = time.perf_counter()

        # BGE models benefit from this prefix for retrieval tasks
        prefixed = f"Represent this sentence for searching relevant passages: {text}"

        vector: np.ndarray = self.model.encode(
            prefixed,
            normalize_embeddings=True,   # L2 normalize → cosine via dot product
            convert_to_numpy=True,
        )

        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug(f"[Embedder] encode() completed in {elapsed:.1f}ms")

        return vector.astype(np.float32).tolist()

    def build_query(self, subject: str, topic: str | None = None) -> str:
        """
        Construct a retrieval query string from student context.
        This is what gets embedded and used for similarity search.
        """
        parts = [subject.strip()]
        if topic and topic.strip():
            parts.append(topic.strip())
        return " ".join(parts)