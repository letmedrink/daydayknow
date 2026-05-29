import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（优先 .env.local，其次 .env）
env_dir = Path(__file__).resolve().parent.parent
if (env_dir / ".env.local").exists():
    load_dotenv(env_dir / ".env.local")
else:
    load_dotenv(env_dir / ".env")

class Settings:
    """应用配置"""
    
    # 模拟模式
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL_LEVEL: str = os.getenv("LLM_MODEL_LEVEL", "fast")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Embedding
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "mock")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_SIMILARITY_THRESHOLD: float = float(os.getenv("EMBEDDING_SIMILARITY_THRESHOLD", "0.85"))

    # Redis / ARQ
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # 应用配置
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    CRON_SECRET: str = os.getenv("CRON_SECRET", "default-secret")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

settings = Settings()