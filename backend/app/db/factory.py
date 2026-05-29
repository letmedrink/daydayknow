from ..config import settings
from .graph_store import InMemoryGraphStore

_store = None


def get_graph_store():
    """返回图谱存储实例（单例）。有 DATABASE_URL 用 Postgres，否则用 InMemory。"""
    global _store
    if _store is None:
        if settings.DATABASE_URL:
            from .postgres_store import PostgresGraphStore
            _store = PostgresGraphStore(settings.DATABASE_URL)
        else:
            _store = InMemoryGraphStore()
    return _store


def reset_store():
    """重置单例（用于测试）。"""
    global _store
    _store = None
