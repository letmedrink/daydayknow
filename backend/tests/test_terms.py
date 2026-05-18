import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_confirm_term_success():
    """测试成功确认术语"""
    call_count = [0]
    
    def from_side_effect(table):
        call_count[0] += 1
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.neq.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.insert.return_value = mock_table
        
        if call_count[0] == 1:
            # 术语查询
            mock_table.single.return_value = MagicMock(execute=MagicMock(return_value={
                "data": {"id": "term_1", "term": "测试术语", "domain": "测试领域"}
            }))
        elif call_count[0] == 2:
            # 术语更新
            mock_table.execute.return_value = {"error": None}
        elif call_count[0] == 3:
            # 星图节点插入
            mock_table.execute.return_value = {"error": None}
        elif call_count[0] == 4:
            # 同领域节点查询
            mock_table.execute.return_value = {
                "data": [{"id": "node_2", "term_name": "其他术语", "domain": "测试领域"}]
            }
        else:
            # 连线插入
            mock_table.execute.return_value = {"error": None}
        
        return mock_table
    
    mock_db = MagicMock()
    mock_db.from_.side_effect = from_side_effect
    
    with patch("app.routers.terms.get_db", return_value=mock_db):
        
        response = client.post(
            "/api/terms/term_1/confirm",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "已点亮星图"
        assert "star_node_id" in data
        assert data["term_name"] == "测试术语"
        assert data["domain"] == "测试领域"

def test_confirm_term_not_found():
    """测试术语不存在"""
    mock_db = MagicMock()
    mock_db.from_().select().single().execute.return_value = {"data": None, "error": {"message": "Not found"}}
    
    with patch("app.routers.terms.get_db", return_value=mock_db):
        
        response = client.post(
            "/api/terms/nonexistent/confirm",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 404
        assert "术语不存在" in response.json()["detail"]

def test_confirm_term_database_error():
    """测试数据库错误"""
    call_count = [0]
    
    def from_side_effect(table):
        call_count[0] += 1
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        
        if call_count[0] == 1:
            mock_table.single.return_value = MagicMock(execute=MagicMock(return_value={
                "data": {"id": "term_1", "term": "测试术语", "domain": "测试领域"}
            }))
        else:
            mock_table.execute.return_value = {"error": {"message": "更新失败"}}
        
        return mock_table
    
    mock_db = MagicMock()
    mock_db.from_.side_effect = from_side_effect
    
    with patch("app.routers.terms.get_db", return_value=mock_db):
        
        response = client.post(
            "/api/terms/term_1/confirm",
            headers={"x-user-id": "test_user"}
        )
        
        assert response.status_code == 500
        assert "更新术语状态失败" in response.json()["detail"]