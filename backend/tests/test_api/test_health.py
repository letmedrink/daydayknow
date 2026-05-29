import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health_returns_status(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_health_checks_structure(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        data = resp.json()
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "llm" in checks
        assert "embedding" in checks
