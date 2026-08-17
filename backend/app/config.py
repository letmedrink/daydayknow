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

    # 数据目录（所有持久化数据存储位置）
    DATA_DIR: str = os.getenv("DATA_DIR", str(env_dir / "data"))

    # LLM 默认配置（可在前端设置页面动态覆盖）
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # 多模态模型（图片描述用）
    MULTIMODAL_MODEL: str = os.getenv("MULTIMODAL_MODEL", "")
    MULTIMODAL_API_KEY: str = os.getenv("MULTIMODAL_API_KEY", "")
    MULTIMODAL_BASE_URL: str = os.getenv("MULTIMODAL_BASE_URL", "")

    # 搜索 API（Deep Research 用）
    SEARCH_API_PROVIDER: str = os.getenv("SEARCH_API_PROVIDER", "")  # tavily / serpapi / searxng
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
    SEARCH_API_BASE_URL: str = os.getenv("SEARCH_API_BASE_URL", "")

    # 应用配置
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))

    # 固定用户 ID（个人使用，无需登录）
    USER_ID: str = os.getenv("USER_ID", "default-user")


settings = Settings()
