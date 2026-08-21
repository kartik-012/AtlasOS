"""
AtlasOS HTTP NLI Provider.

Implementation of the NLIProvider interface that communicates
with a dedicated internal HTTP microservice running the
`roberta-large-mnli` model for Cross-Encoder contradiction detection.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.providers.base import NLIProvider

logger = get_logger(__name__)


class HTTPNLIProvider(NLIProvider):
    """
    NLI provider utilizing an external HTTP inference service.

    The service evaluates a Premise and Hypothesis and returns probabilities
    for Entailment, Contradiction, and Neutral.
    """

    def __init__(self, base_url: str | None = None, threshold: float = 0.85) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.NLI_SERVICE_URL
        if not self.base_url.endswith("/v1/nli"):
            self.base_url = self.base_url.rstrip("/") + "/v1/nli"
        self.threshold = threshold

    async def check_contradiction(
        self,
        premise: str,
        hypothesis: str,
    ) -> tuple[bool, float]:
        """
        Evaluate if hypothesis contradicts premise via HTTP service.

        Returns True if the contradiction probability exceeds the threshold.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json={
                        "premise": premise,
                        "hypothesis": hypothesis,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Expected response: { "contradiction": 0.95, "entailment": 0.02, "neutral": 0.03 }
                contradiction_score = float(data.get("contradiction", 0.0))

                is_contradiction = contradiction_score >= self.threshold
                return is_contradiction, contradiction_score

            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, TypeError) as e:
                logger.exception(
                    "nli_service_error",
                    error=str(e),
                    url=self.base_url,
                )
                raise ExternalServiceError(
                    message="Failed to analyze contradiction via inference service.",
                ) from e
