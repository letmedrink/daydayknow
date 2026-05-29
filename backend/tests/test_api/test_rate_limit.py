import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_normal_request_not_limited(self):
        """正常请求不应被限流。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_limiter_configured(self):
        """验证 limiter 已配置。"""
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None
