import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_get_star_map_success():
    """测试成功获取星图（模拟模式）"""
    mock_db = MagicMock()
    mock_db.init_mock_data.return_value = {
        "mockTerms": [
            {
                "id": "term_1",
                "term": "流动性陷阱",
                "domain": "宏观经济学",
                "captured_at": "2024-01-01T00:00:00Z"
            }
        ]
    }

    with patch("app.routers.star_map.get_db", return_value=mock_db), \
         patch("app.routers.star_map.is_mock_mode", return_value=True):
        
        response = client.get(
            "/api/star-map",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data
        assert data["stats"]["total_nodes"] == 1

def test_get_star_map_empty():
    """测试空星图"""
    mock_nodes_table = MagicMock()
    mock_nodes_table.select.return_value = mock_nodes_table
    mock_nodes_table.eq.return_value = mock_nodes_table
    mock_nodes_table.order.return_value = mock_nodes_table
    mock_nodes_table.execute.return_value = {"data": []}
    
    mock_edges_table = MagicMock()
    mock_edges_table.select.return_value = mock_edges_table
    mock_edges_table.eq.return_value = mock_edges_table
    mock_edges_table.execute.return_value = {"data": []}
    
    call_count = [0]
    def from_side_effect(table):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_nodes_table
        return mock_edges_table
    
    mock_db = MagicMock()
    mock_db.from_.side_effect = from_side_effect

    with patch("app.routers.star_map.get_db", return_value=mock_db), \
         patch("app.routers.star_map.is_mock_mode", return_value=False):
        
        response = client.get(
            "/api/star-map",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["stats"]["total_nodes"] == 0

def test_get_star_map_error():
    """测试星图查询错误"""
    mock_db = MagicMock()
    mock_db.from_().select().order().execute.return_value = {"error": {"message": "查询失败"}}

    with patch("app.routers.star_map.get_db", return_value=mock_db), \
         patch("app.routers.star_map.is_mock_mode", return_value=False):
        
        response = client.get(
            "/api/star-map",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 500
        assert "查询星图节点失败" in response.json()["detail"]