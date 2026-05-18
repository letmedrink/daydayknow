import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_capture_term_success():
    """测试成功捕获术语"""
    mock_db = MagicMock()
    mock_db.from_().insert().execute.return_value = {"error": None}

    with patch("app.routers.capture.get_db", return_value=mock_db), \
         patch("app.routers.capture.is_mock_mode", return_value=True), \
         patch("app.routers.capture.validate_llm_config", return_value={"valid": False, "errors": []}):
        
        response = client.post(
            "/api/capture",
            json={"raw_text": "日本经济长期陷入流动性陷阱"},
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "extracted_term" in data
        assert "all_terms" in data
        assert "domain" in data
        assert data["message"] == "已捕获，明早日报见"
        assert data["user_id"] == "test_user"

def test_capture_term_missing_text():
    """测试缺少文本参数"""
    response = client.post(
        "/api/capture",
        json={},
        headers={"x-user-id": "test_user"}
    )
    
    assert response.status_code == 422

def test_capture_term_empty_text():
    """测试空文本参数"""
    response = client.post(
        "/api/capture",
        json={"raw_text": ""},
        headers={"x-user-id": "test_user"}
    )
    
    assert response.status_code == 400
    assert "缺少raw_text参数" in response.json()["detail"]