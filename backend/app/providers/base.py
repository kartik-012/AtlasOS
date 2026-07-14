"""
AtlasOS AI Service Provider Abstractions.

Defines the core interfaces for interacting with Embedding and NLI
(Natural Language Inference) models. By programming against these
interfaces, the core memory services remain decoupled from specific
model implementations or deployment strategies (local vs. cloud).
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding generation providers.
    """

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate a vector embedding for a single text string.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the dense vector.
        """
        pass

    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate vector embeddings for a batch of text strings.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors corresponding to the inputs.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return the dimensionality of the vectors produced by this provider.
        """
        pass


class NLIProvider(ABC):
    """
    Abstract base class for Natural Language Inference (NLI) providers.
    Used for contradiction detection between memories.
    """

    @abstractmethod
    async def check_contradiction(
        self,
        premise: str,
        hypothesis: str,
    ) -> tuple[bool, float]:
        """
        Evaluate if the hypothesis contradicts the premise.

        Args:
            premise: The existing fact (e.g., "The user lives in New York").
            hypothesis: The new fact (e.g., "The user lives in London").

        Returns:
            Tuple containing:
              - is_contradiction (bool): True if contradiction detected.
              - confidence (float): Model confidence score [0.0, 1.0].
        """
        pass
