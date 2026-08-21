"""
AtlasOS HTTP Embedding Provider.

Implementation of the EmbeddingProvider interface that communicates
with a dedicated internal HTTP microservice running the
`BAAI/bge-large-en-v1.5` model.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider

logger = get_logger(__name__)


class HTTPEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider utilizing an external HTTP service.
    Defaults to 1024 dimensions (BGE-Large).
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        # In a real deployment, this would be an internal Docker DNS name
        # e.g., "http://inference:8080"
        self.base_url = base_url or settings.EMBEDDING_SERVICE_URL
        if not self.base_url.endswith("/v1/embeddings"):
            self.base_url = self.base_url.rstrip("/") + "/v1/embeddings"
        self._dimension = settings.EMBEDDING_DIMENSION

    @property
    def dimension(self) -> int:
        return self._dimension

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a single embedding via HTTP."""
        results = await self.get_embeddings([text])
        if not results:
            raise ExternalServiceError(message="Embedding service returned empty result.")
        return results[0]

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate batch embeddings via HTTP."""
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json={"input": texts, "model": "BAAI/bge-large-en-v1.5"},
                )
                response.raise_for_status()
                data = response.json()

                # Expecting OpenAI-compatible response format:
                # { "data": [ {"embedding": [0.1, 0.2, ...]} ] }
                embeddings = [item["embedding"] for item in data.get("data", [])]

                if len(embeddings) != len(texts):
                    raise ValueError("Mismatch between input count and embedding count")

                return embeddings

            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
                logger.exception(
                    "embedding_service_error",
                    error=str(e),
                    url=self.base_url,
                    text_count=len(texts),
                )
                raise ExternalServiceError(
                    message="Failed to generate embeddings from inference service.",
                ) from e
