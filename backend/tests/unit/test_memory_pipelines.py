"""
AtlasOS Phase 3 Unit Tests — Memory Pipelines.

Tests the mock providers and the composite ranking logic in the MemoryReadService.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from app.providers.embeddings import HTTPEmbeddingProvider
from app.providers.nli import HTTPNLIProvider
from app.services.memory_read import MemoryReadService


@pytest.mark.asyncio
async def test_embedding_provider_mocked():
    """Test the HTTPEmbeddingProvider logic with mocked HTTPX."""
    provider = HTTPEmbeddingProvider(base_url="http://mock-embedder/v1")
    
    mock_response = Response(
        status_code=200,
        json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
    )
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        embedding = await provider.get_embedding("Hello world")
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_nli_provider_mocked():
    """Test the HTTPNLIProvider logic with mocked HTTPX."""
    provider = HTTPNLIProvider(base_url="http://mock-nli/v1", threshold=0.85)
    
    mock_response = Response(
        status_code=200,
        json={"contradiction": 0.95, "entailment": 0.02, "neutral": 0.03},
    )
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        is_contradiction, score = await provider.check_contradiction(
            premise="The sky is blue",
            hypothesis="The sky is red",
        )
        assert is_contradiction is True
        assert score == 0.95


@pytest.mark.asyncio
async def test_composite_ranking():
    """
    Test the composite ranking logic in the MemoryReadService.
    Formula: (w_sim * similarity) + (w_imp * importance)
    where w_sim = 0.75, w_imp = 0.25
    """
    # Create mock dependencies
    mock_session = AsyncMock()
    mock_embed = AsyncMock()
    mock_embed.get_embedding.return_value = [0.1, 0.2]
    
    # Mock Qdrant results
    class MockScoredPoint:
        def __init__(self, id_str, score, imp):
            self.id = id_str
            self.score = score
            self.payload = {"memory_type": "episodic", "importance_score": imp}
            
    mock_vector_repo = AsyncMock()
    mock_vector_repo.search.return_value = [
        # Point A: High similarity, low importance
        # Comp: (0.75 * 0.90) + (0.25 * 0.10) = 0.675 + 0.025 = 0.700
        MockScoredPoint(str(uuid.uuid4()), score=0.90, imp=0.10),
        
        # Point B: Med similarity, high importance
        # Comp: (0.75 * 0.70) + (0.25 * 0.95) = 0.525 + 0.2375 = 0.7625  <- Should win
        MockScoredPoint(str(uuid.uuid4()), score=0.70, imp=0.95),
    ]
    
    service = MemoryReadService(
        session=mock_session,
        embedding_provider=mock_embed,
        vector_repo=mock_vector_repo,
    )
    
    # Mock Postgres hydration to just return the items exactly
    class MockMemory:
        def __init__(self, mem_id):
            self.id = uuid.UUID(mem_id)
            self.content = "content"
            self.metadata_ = {}
            self.created_at = None

    service._episodic_repo.get_by_ids = AsyncMock(
        side_effect=lambda tid, ids: [MockMemory(str(i)) for i in ids]
    )
    service._semantic_repo.get_by_ids = AsyncMock(return_value=[])

    response = await service.search(
        tenant_id=uuid.uuid4(),
        external_user_id="user_1",
        query="test",
        limit=2,
    )
    
    assert len(response.results) == 2
    
    # Result 0 should be Point B (index 1 from raw results) due to ranking
    assert response.results[0].id == uuid.UUID(mock_vector_repo.search.return_value[1].id)
    assert response.results[0].composite_score == 0.7625
    
    # Result 1 should be Point A
    assert response.results[1].id == uuid.UUID(mock_vector_repo.search.return_value[0].id)
    assert response.results[1].composite_score == 0.700
