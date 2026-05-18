import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.services.supabase_client import get_db, is_mock_mode, generate_user_id
from app.services.mock_supabase import MockSupabase

@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)

@pytest.fixture
def mock_db():
    """模拟数据库"""
    return MockSupabase()

@pytest.fixture
def test_user_id():
    """测试用户ID"""
    return "test_user_123"

@pytest.fixture
def mock_mode():
    """模拟模式"""
    with patch("app.services.supabase_client.settings.MOCK_MODE", True):
        yield

@pytest.fixture
def mock_llm():
    """模拟 LLM 调用"""
    with patch("app.services.llm_client.llm_chat_completion") as mock_chat, \
         patch("app.services.llm_client.llm_json_completion") as mock_json:
        mock_chat.return_value = "模拟的 LLM 响应"
        mock_json.return_value = {
            "terms": ["测试术语"],
            "domain": "测试领域"
        }
        yield mock_chat, mock_json

@pytest.fixture
def mock_batch_processor():
    """模拟批处理器"""
    with patch("app.services.batch_processor.process_daily_terms") as mock:
        mock.return_value = {
            "success": True,
            "processed": 2,
            "skipped": 0
        }
        yield mock