"""Embedding generation utilities for semantic search."""

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using sentence transformers."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L12-v2",
        device: str | None = None,
    ):
        """Initialize the embedding generator.

        Args:
            model_name: Name of the sentence transformer model to use.
            device: Device to run the model on (None for auto-detect).
        """
        self.model_name = model_name
        self.vector_dim = 384  # MiniLM-L12-v2 output dimension

        try:
            self.encoder = SentenceTransformer(model_name, device=device)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def encode_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to encode.

        Returns:
            Numpy array of embedding vector.
        """
        if not text:
            return np.zeros(self.vector_dim)

        try:
            embedding = self.encoder.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return np.zeros(self.vector_dim)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to encode.

        Returns:
            Numpy array of embedding vectors.
        """
        if not texts:
            return np.zeros((0, self.vector_dim))

        try:
            embeddings = self.encoder.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return np.zeros((len(texts), self.vector_dim))

    def combine_text_for_embedding(
        self,
        technique: str,
        payload: str | None = None,
        result: str | None = None,
    ) -> str:
        """Combine technique information into a single text for embedding.

        Args:
            technique: The technique name/description.
            payload: Optional payload used.
            result: Optional result obtained.

        Returns:
            Combined text for embedding generation.
        """
        parts = [f"Technique: {technique}"]

        if payload:
            # Truncate long payloads for embedding
            truncated_payload = payload[:500] if len(payload) > 500 else payload
            parts.append(f"Payload: {truncated_payload}")

        if result:
            # Truncate long results for embedding
            truncated_result = result[:500] if len(result) > 500 else result
            parts.append(f"Result: {truncated_result}")

        return " | ".join(parts)
