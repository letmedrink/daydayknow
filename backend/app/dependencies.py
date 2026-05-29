from fastapi import Header, Query, Depends
from typing import Optional
from .services.supabase_client import generate_user_id
from .services.auth import extract_user_from_token
from .config import settings


async def get_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
    user_id: Optional[str] = Query(None, alias="userId"),
) -> str:
    """获取用户ID。优先 JWT token，其次 x-user-id header，最后生成匿名 ID。"""
    # 1. 尝试从 Authorization: Bearer <token> 提取
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        uid = extract_user_from_token(token)
        if uid:
            return uid

    # 2. 兼容旧的 x-user-id header（测试用）
    if x_user_id:
        return x_user_id

    # 3. 兼容 query param
    if user_id:
        return user_id

    # 4. 生成匿名 ID
    return generate_user_id()


async def get_current_user(
    user_id: str = Depends(get_user_id),
) -> str:
    """获取当前用户（依赖注入）"""
    return user_id


async def verify_cron_secret(
    authorization: Optional[str] = Header(None),
) -> bool:
    """验证批处理密钥"""
    if not authorization:
        return False

    if not authorization.startswith("Bearer "):
        return False

    token = authorization[7:]
    return token == settings.CRON_SECRET
