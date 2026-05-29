import json
import base64
import hmac
import hashlib
import os
import pytest
from unittest.mock import patch

from app.services.auth import verify_jwt_token, extract_user_from_token, _base64url_decode


def _make_jwt(payload: dict, secret: str = "test-secret") -> str:
    """生成测试用 JWT token。"""
    header = {"alg": "HS256", "typ": "JWT"}

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    header_b64 = b64(header)
    payload_b64 = b64(payload)
    message = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header_b64}.{payload_b64}.{sig_b64}"


class TestVerifyJwt:
    def test_valid_token(self):
        secret = "my-secret"
        token = _make_jwt({"sub": "user-123", "email": "test@example.com"}, secret)
        from app.services import auth as auth_mod
        old = auth_mod.settings.SUPABASE_JWT_SECRET
        auth_mod.settings.SUPABASE_JWT_SECRET = secret
        try:
            payload = verify_jwt_token(token)
            assert payload is not None
            assert payload["sub"] == "user-123"
        finally:
            auth_mod.settings.SUPABASE_JWT_SECRET = old

    def test_invalid_signature(self):
        token = _make_jwt({"sub": "user-123"}, secret="wrong-secret")
        from app.services import auth as auth_mod
        old = auth_mod.settings.SUPABASE_JWT_SECRET
        auth_mod.settings.SUPABASE_JWT_SECRET = "correct-secret"
        try:
            payload = verify_jwt_token(token)
            assert payload is None
        finally:
            auth_mod.settings.SUPABASE_JWT_SECRET = old

    def test_malformed_token(self):
        from app.services import auth as auth_mod
        old = auth_mod.settings.SUPABASE_JWT_SECRET
        auth_mod.settings.SUPABASE_JWT_SECRET = "test"
        try:
            assert verify_jwt_token("not.a.token") is None
            assert verify_jwt_token("invalid") is None
        finally:
            auth_mod.settings.SUPABASE_JWT_SECRET = old

    def test_no_secret_returns_none(self):
        token = _make_jwt({"sub": "user-123"}, secret="test")
        from app.services import auth as auth_mod
        old = auth_mod.settings.SUPABASE_JWT_SECRET
        auth_mod.settings.SUPABASE_JWT_SECRET = ""
        try:
            assert verify_jwt_token(token) is None
        finally:
            auth_mod.settings.SUPABASE_JWT_SECRET = old

    def test_extract_user_from_token(self):
        secret = "extract-secret"
        token = _make_jwt({"sub": "user-abc"}, secret)
        from app.services import auth as auth_mod
        old = auth_mod.settings.SUPABASE_JWT_SECRET
        auth_mod.settings.SUPABASE_JWT_SECRET = secret
        try:
            uid = extract_user_from_token(token)
            assert uid == "user-abc"
        finally:
            auth_mod.settings.SUPABASE_JWT_SECRET = old
