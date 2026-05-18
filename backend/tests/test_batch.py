import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

def test_batch_health():
    """测试批处理健康检查"""
    response = client.get("/api/batch")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "批处理API端点"
    assert "usage" in data
    assert "timestamp" in data

def test_batch_process_success():
    """测试成功执行批处理"""
    with patch("app.routers.batch.verify_cron_secret") as mock_verify, \
         patch("app.routers.batch.process_daily_terms") as mock_process:
        
        # 设置模拟
        mock_verify.return_value = True
        mock_process.return_value = {
            "success": True,
            "processed": 2,
            "skipped": 0
        }
        
        # 发送请求
        response = client.post(
            "/api/batch",
            json={"userId": "test_user", "date": "2024-01-01"},
            headers={"Authorization": "Bearer test-secret"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "批处理完成"
        assert data["processed"] == 2
        assert data["skipped"] == 0

def test_batch_process_unauthorized():
    """测试未授权访问"""
    with patch("app.routers.batch.verify_cron_secret") as mock_verify:
        
        # 设置模拟
        mock_verify.return_value = False
        
        # 发送请求
        response = client.post(
            "/api/batch",
            json={"userId": "test_user", "date": "2024-01-01"},
            headers={"Authorization": "Bearer wrong-secret"}
        )
        
        # 验证响应
        assert response.status_code == 401
        assert "未授权" in response.json()["detail"]

def test_batch_process_failure():
    """测试批处理失败"""
    with patch("app.routers.batch.verify_cron_secret") as mock_verify, \
         patch("app.routers.batch.process_daily_terms") as mock_process:
        
        # 设置模拟
        mock_verify.return_value = True
        mock_process.return_value = {
            "success": False,
            "error": "批处理失败",
            "processed": 0,
            "skipped": 0
        }
        
        # 发送请求
        response = client.post(
            "/api/batch",
            json={"userId": "test_user", "date": "2024-01-01"},
            headers={"Authorization": "Bearer test-secret"}
        )
        
        # 验证响应
        assert response.status_code == 500
        assert "批处理失败" in response.json()["detail"]

def test_batch_process_missing_auth():
    """测试缺少授权头"""
    # 发送请求
    response = client.post(
        "/api/batch",
        json={"userId": "test_user", "date": "2024-01-01"}
    )
    
    # 验证响应
    assert response.status_code == 401
    assert "未授权" in response.json()["detail"]