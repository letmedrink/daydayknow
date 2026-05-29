import json
import base64
import hmac
import hashlib
from typing import Optional

from ..config import settings


def _base64url_decode(data: str) -> bytes:
    """Base64url 解码（JWT 标准编码）。"""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def verify_jwt_token(token: str) -> Optional[dict]:
    """验证 Supabase JWT token 并返回 payload。

    使用 HMAC-SHA256 验证签名。Supabase 的 JWT_SECRET
    通常就是 SUPABASE_JWT_SECRET 环境变量。
    """
    jwt_secret = settings.SUPABASE_JWT_SECRET
    if not jwt_secret:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, signature_b64 = parts

    # 验证签名
    try:
        message = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(
            jwt_secret.encode(), message, hashlib.sha256
        ).digest()
        actual_sig = _base64url_decode(signature_b64)
    except Exception:
        return None

    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    # 解析 payload
    try:
        payload = json.loads(_base64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError):
        return None

    return payload


def extract_user_from_token(token: str) -> Optional[str]:
    """从 JWT token 中提取用户 ID。"""
    payload = verify_jwt_token(token)
    if not payload:
        return None
    return payload.get("sub")
