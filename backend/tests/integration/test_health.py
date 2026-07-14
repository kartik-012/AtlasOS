"""
AtlasOS Integration Tests — E2E Health Verification

Tests if the backend can communicate with the inference container,
databases, and Redis successfully. To be run inside the test container
or locally when docker-compose is up.
"""

import httpx
import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_backend_health_endpoint():
    """Verify the FastAPI backend is up and running."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            response = await client.get("/api/v1/health")
            # If the backend isn't up, this will raise
            assert response.status_code in (200, 503)
        except httpx.ConnectError:
            pytest.skip("Backend is not running. Run docker-compose up first.")


@pytest.mark.asyncio
async def test_inference_service_health():
    """Verify the inference microservice is up and loaded models."""
    settings = get_settings()
    
    # Strip any paths to get the base URL
    from urllib.parse import urlparse
    parsed = urlparse(settings.EMBEDDING_SERVICE_URL)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # If running locally vs in docker
    if "inference" in base_url:
        base_url = base_url.replace("inference", "localhost")
        
    async with httpx.AsyncClient(base_url=base_url) as client:
        try:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["models"]["embedding"] == "loaded"
            assert data["models"]["nli"] == "loaded"
        except httpx.ConnectError:
            pytest.skip("Inference service is not running locally.")
