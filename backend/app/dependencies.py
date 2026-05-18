from fastapi import Header, Query, Depends
from typing import Optional
from .services.supabase_client import generate_user_id, is_mock_mode, get_db
from .config import settings

async def get_user_id(
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
    user_id: Optional[str] = Query(None, alias="userId")
) -> str:
    """获取用户ID（匿名用户）"""
    if x_user_id:
        return x_user_id
    if user_id:
        return user_id
    return generate_user_id()

async def get_current_user(
    user_id: str = Depends(get_user_id)
) -> str:
    """获取当前用户（依赖注入）"""
    return user_id

async def verify_cron_secret(
    authorization: Optional[str] = Header(None)
) -> bool:
    """验证批处理密钥"""
    if not authorization:
        return False
    
    if not authorization.startswith("Bearer "):
        return False
    
    token = authorization[7:]  # 移除 "Bearer " 前缀
    return token == settings.CRON_SECRET