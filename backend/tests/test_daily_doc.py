import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, call
from app.main import app

client = TestClient(app)

def test_get_daily_doc_success():
    """测试成功获取日报（模拟模式）"""
    mock_db = MagicMock()
    mock_db.init_mock_data.return_value = {
        "mockDailyDoc": {
            "doc_date": "2024-01-01",
            "cards": [{"term_id": "1", "term": "流动性陷阱", "context": "test", "simple": "test", "deep": "test", "case": "test", "history": "test", "related": [], "controversy": "", "source": "test"}],
            "term_count": 1,
            "generated_at": "2024-01-01T00:00:00Z"
        }
    }

    with patch("app.routers.daily_doc.get_db", return_value=mock_db), \
         patch("app.routers.daily_doc.is_mock_mode", return_value=True):
        
        response = client.get(
            "/api/daily-doc",
            params={"date": "2024-01-01"},
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "doc_date" in data
        assert "title" in data
        assert "cards" in data

def test_get_daily_doc_not_found():
    """测试日报不存在"""
    mock_doc_query = MagicMock()
    mock_doc_query.execute.return_value = {"data": None, "error": {"message": "Not found"}}
    
    mock_terms_query = MagicMock()
    mock_terms_query.execute.return_value = {"data": []}
    
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.single.return_value = mock_doc_query
    
    call_count = [0]
    def from_side_effect(table):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_table
        mock_terms_table = MagicMock()
        mock_terms_table.select.return_value = mock_terms_table
        mock_terms_table.eq.return_value = mock_terms_table
        mock_terms_table.gte.return_value = mock_terms_table
        mock_terms_table.lte.return_value = mock_terms_table
        mock_terms_table.execute.return_value = {"data": []}
        return mock_terms_table
    
    mock_db = MagicMock()
    mock_db.from_.side_effect = from_side_effect

    with patch("app.routers.daily_doc.get_db", return_value=mock_db), \
         patch("app.routers.daily_doc.is_mock_mode", return_value=False):
        
        response = client.get(
            "/api/daily-doc",
            params={"date": "2024-01-01"},
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "日报未生成"

def test_generate_daily_doc_already_exists():
    """测试日报已存在"""
    mock_db = MagicMock()
    mock_db.from_().select().single().execute.return_value = {
        "data": {"generated_at": "2024-01-01T00:00:00Z"}
    }

    with patch("app.routers.daily_doc.get_db", return_value=mock_db):
        
        response = client.post(
            "/api/daily-doc/generate",
            json={"date": "2024-01-01"},
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "日报已存在"
        assert data["task_id"] == ""

def test_generate_daily_doc_no_terms():
    """测试没有术语 - 异步模式会启动任务，后台失败"""
    mock_doc_result = MagicMock()
    mock_doc_result.execute.return_value = {"data": None, "error": {"message": "Not found"}}
    
    call_count = [0]
    def from_side_effect(table):
        call_count[0] += 1
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        if call_count[0] == 1:
            mock_table.single.return_value = mock_doc_result
        else:
            mock_table.execute.return_value = {"data": []}
        return mock_table
    
    mock_db = MagicMock()
    mock_db.from_.side_effect = from_side_effect

    with patch("app.routers.daily_doc.get_db", return_value=mock_db):
        
        response = client.post(
            "/api/daily-doc/generate",
            json={"date": "2024-01-01"},
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "日报生成已启动"
        assert "task_id" in data