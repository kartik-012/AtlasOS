"""
AtlasOS HuggingFace Inference API Embedding Provider.

Uses HuggingFace's hosted Inference API (free tier) to generate
embeddings via BAAI/bge-large-en-v1.5, eliminating the need for
a self-hosted inference container in production deployments.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider

logger = get_logger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-large-en-v1.5"


class HTTPEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider that routes through HuggingFace Inference API
    (free tier) or a self-hosted inference service, depending on
    whether HF_API_TOKEN is set in environment.

    - If HF_API_TOKEN is set → uses HuggingFace hosted API (production)
    - If EMBEDDING_SERVICE_URL is set → uses local inference container (dev)
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self._hf_token: str | None = getattr(settings, "HF_API_TOKEN", None)
        self._dimension = settings.EMBEDDING_DIMENSION

        if self._hf_token:
            # Production: use HuggingFace hosted API
            self.base_url = HF_API_URL
            self._use_hf = True
        else:
            # Development: use local inference container
            local_url = base_url or settings.EMBEDDING_SERVICE_URL
            if not local_url.endswith("/v1/embeddings"):
                local_url = local_url.rstrip("/") + "/v1/embeddings"
            self.base_url = local_url
            self._use_hf = False

    @property
    def dimension(self) -> int:
        return self._dimension

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a single embedding."""
        results = await self.get_embeddings([text])
        if not results:
            raise ExternalServiceError(message="Embedding service returned empty result.")
        return results[0]

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate batch embeddings."""
        if not texts:
            return []

        if self._use_hf:
            return await self._get_hf_embeddings(texts)
        return await self._get_local_embeddings(texts)

    async def _get_hf_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Call HuggingFace Inference API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self._hf_token}",
                        "Content-Type": "application/json",
                    },
                    json={"inputs": texts, "options": {"wait_for_model": True}},
                )
                response.raise_for_status()
                data = response.json()

                # HF returns list of lists directly
                if isinstance(data, list) and data and isinstance(data[0], list):
                    embeddings = data
                else:
                    raise ValueError(f"Unexpected HuggingFace response format: {type(data)}")

                if len(embeddings) != len(texts):
                    raise ValueError("Mismatch between input count and embedding count")

                return [list(map(float, emb)) for emb in embeddings]

            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
                logger.exception("hf_embedding_error", error=str(e), text_count=len(texts))
                raise ExternalServiceError(
                    message="Failed to generate embeddings from HuggingFace API.",
                ) from e

    async def _get_local_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Call local inference container (OpenAI-compatible format)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json={"input": texts, "model": "BAAI/bge-large-en-v1.5"},
                )
                response.raise_for_status()
                data = response.json()
                embeddings = [item["embedding"] for item in data.get("data", [])]

                if len(embeddings) != len(texts):
                    raise ValueError("Mismatch between input count and embedding count")

                return embeddings

            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
                logger.exception(
                    "local_embedding_error",
                    error=str(e),
                    url=self.base_url,
                    text_count=len(texts),
                )
                raise ExternalServiceError(
                    message="Failed to generate embeddings from inference service.",
                ) from e
