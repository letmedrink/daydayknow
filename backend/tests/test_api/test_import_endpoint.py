import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


client = TestClient(app)


class TestImportEndpoint:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    def test_import_extracts_concepts(self):
        extraction = {
            "nodes": [
                {"name": "注意力机制", "domain": "AI", "description": "Transformer核心组件", "confidence": 0.9}
            ],
            "edges": [],
        }
        mock = MockLLMProvider()
        mock.default_response = json.dumps(extraction)
        ModelRouter.set_provider(mock)

        response = client.post(
            "/api/import",
            json={"content": "注意力机制是Transformer的核心组件，通过QKV计算实现序列建模。", "source_name": "笔记"},
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "注意力机制"

    def test_import_empty_content(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)

        response = client.post(
            "/api/import",
            json={"content": "   "},
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert "不能为空" in data["error"]

    def test_import_extraction_failure(self):
        mock = MockLLMProvider(error_on="chat_json")
        ModelRouter.set_provider(mock)

        response = client.post(
            "/api/import",
            json={"content": "some content to extract"},
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert "error" in data
