"""设置 API — 多模型配置。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..dependencies import get_file_store
from ..storage import FileStore

router = APIRouter(prefix="/api/settings")


class LLMProviderConfig(BaseModel):
    id: str
    name: str
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    api_mode: str = "openai"


class SettingsUpdate(BaseModel):
    llm_providers: Optional[dict] = Field(default=None, alias="llmProviders")
    active_provider_id: Optional[str] = Field(default=None, alias="activeProviderId")
    search_api_config: Optional[dict] = Field(default=None, alias="searchApiConfig")
    output_language: Optional[str] = Field(default=None, alias="outputLanguage")
    multimodal_model: Optional[str] = Field(default=None, alias="multimodalModel")

    model_config = {"populate_by_name": True}


@router.get("")
async def get_settings(file_store: FileStore = Depends(get_file_store)):
    """获取设置。"""
    settings = file_store.get_settings()
    return {"success": True, "data": settings}


@router.patch("")
async def update_settings(
    req: SettingsUpdate,
    file_store: FileStore = Depends(get_file_store),
):
    """更新设置。"""
    updates = {}
    if req.llm_providers is not None:
        updates["llmProviders"] = req.llm_providers
    if req.active_provider_id is not None:
        updates["activeProviderId"] = req.active_provider_id
    if req.search_api_config is not None:
        updates["searchApiConfig"] = req.search_api_config
    if req.output_language is not None:
        updates["outputLanguage"] = req.output_language
    if req.multimodal_model is not None:
        updates["multimodalModel"] = req.multimodal_model

    result = file_store.update_settings(**updates)
    return {"success": True, "data": result}


@router.post("/test-connection")
async def test_connection(req: LLMProviderConfig):
    """测试 LLM 连接。支持 OpenAI 兼容和 Anthropic 兼容协议。"""
    import httpx

    base_url = req.base_url or "https://api.openai.com/v1"
    api_mode = req.api_mode or "openai"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if api_mode == "anthropic":
                # Anthropic Messages API
                url = base_url.rstrip("/")
                if not url.endswith("/messages"):
                    url = url + "/messages"

                resp = await client.post(
                    url,
                    headers={
                        "x-api-key": req.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": req.model or "claude-sonnet-4-20250514",
                        "max_tokens": 50,
                        "messages": [{"role": "user", "content": "说'连接成功'"}],
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    reply = data.get("content", [{}])[0].get("text", "")
                    return {"success": True, "data": {"message": reply, "model": req.model}}
                else:
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            else:
                # OpenAI-compatible Chat Completions API
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {req.api_key}"},
                    json={
                        "model": req.model or "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "说'连接成功'"}],
                        "max_tokens": 50,
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    return {"success": True, "data": {"message": reply, "model": req.model}}
                else:
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/profile")
async def get_profile(file_store: FileStore = Depends(get_file_store)):
    """获取用户画像。"""
    profile = file_store.get_profile()
    return {"success": True, "data": profile}


@router.patch("/profile")
async def update_profile(
    profile: dict,
    file_store: FileStore = Depends(get_file_store),
):
    """更新用户画像。"""
    updated = file_store.update_profile(**profile)
    return {"success": True, "data": updated}
