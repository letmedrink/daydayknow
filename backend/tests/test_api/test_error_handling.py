import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.errors import AppError, NotFoundError, BadRequestError


class TestCustomExceptions:

    def test_not_found_error(self):
        err = NotFoundError("节点不存在")
        assert err.status_code == 404
        assert err.detail == "节点不存在"
        assert err.code == "not_found"

    def test_bad_request_error(self):
        err = BadRequestError("标题不能为空")
        assert err.status_code == 400
        assert err.code == "bad_request"

    def test_custom_app_error(self):
        err = AppError(403, "无权访问", "forbidden")
        assert err.status_code == 403


class TestRequestIDMiddleware:

    @pytest.mark.asyncio
    async def test_response_has_request_id(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_custom_request_id(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Request-Id": "my-req-123"})
        assert resp.headers["x-request-id"] == "my-req-123"


class TestGenericErrorHandler:

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
