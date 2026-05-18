try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
from ..config import settings
from .mock_supabase import MockSupabase

# 全局 Supabase 客户端实例
_supabase_client: Client = None
_mock_supabase: MockSupabase = None

def get_supabase_client() -> Client:
    """获取 Supabase 客户端"""
    global _supabase_client
    
    if settings.MOCK_MODE:
        return None
    
    if create_client is None:
        raise ImportError("supabase 包未安装，请运行: pip install supabase，或将 MOCK_MODE 设为 true")
    
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError("Supabase URL and Anon Key are required when MOCK_MODE is false")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    return _supabase_client

def get_db():
    """获取数据库客户端（真实或模拟）"""
    global _mock_supabase
    
    if settings.MOCK_MODE:
        if _mock_supabase is None:
            _mock_supabase = MockSupabase()
        return _mock_supabase
    
    return SupabaseWrapper(get_supabase_client())

def generate_user_id() -> str:
    """生成用户ID（匿名用户）"""
    import random
    import string
    return "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=9))

def is_mock_mode() -> bool:
    """检查是否为模拟模式"""
    return settings.MOCK_MODE

class SupabaseWrapper:
    """Supabase 客户端包装器，统一响应格式"""
    
    def __init__(self, client: Client):
        self._client = client
    
    def from_(self, table: str):
        return SupabaseTableWrapper(self._client.table(table))

class SupabaseTableWrapper:
    """Supabase 表查询包装器"""
    
    def __init__(self, query_builder):
        self._query = query_builder
    
    def select(self, fields: str = "*"):
        self._query = self._query.select(fields)
        return self
    
    def insert(self, data: dict):
        self._last_insert_data = data
        self._is_insert = True
        return self
    
    def update(self, data: dict):
        self._query = self._query.update(data)
        return self
    
    def delete(self):
        self._query = self._query.delete()
        return self
    
    def eq(self, field: str, value):
        self._query = self._query.eq(field, value)
        return self
    
    def neq(self, field: str, value):
        self._query = self._query.neq(field, value)
        return self
    
    def gte(self, field: str, value):
        self._query = self._query.gte(field, value)
        return self
    
    def lte(self, field: str, value):
        self._query = self._query.lte(field, value)
        return self
    
    def in_(self, field: str, values: list):
        self._query = self._query.in_(field, values)
        return self
    
    def or_(self, conditions: str):
        self._query = self._query.or_(conditions)
        return self
    
    def order(self, field: str, ascending: bool = True):
        self._query = self._query.order(field, desc=not ascending)
        return self
    
    def limit(self, count: int):
        self._query = self._query.limit(count)
        return self
    
    def single(self):
        self._is_single = True
        return self
    
    def execute(self, retries=2):
        for attempt in range(retries + 1):
            try:
                if hasattr(self, '_is_insert') and self._is_insert:
                    result = self._query.insert(self._last_insert_data).execute()
                elif hasattr(self, '_is_single') and self._is_single:
                    result = self._query.single().execute()
                else:
                    result = self._query.execute()
                return {"data": result.data, "error": None}
            except Exception as e:
                if attempt < retries:
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {"data": None, "error": str(e)}