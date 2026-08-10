"""设置 API — 多模型配置。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..dependencies import get_global_store
from ..llm import call_llm_with_config
from ..storage import FileStore

router = APIRouter()


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


@router.get("/api/settings")
async def get_settings(file_store: FileStore = Depends(get_global_store)):
    """获取设置。"""
    settings = file_store.get_settings()
    return {"success": True, "data": settings}


@router.patch("/api/settings")
async def update_settings(
    req: SettingsUpdate,
    file_store: FileStore = Depends(get_global_store),
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


@router.post("/api/settings/test-connection")
async def test_connection(req: LLMProviderConfig):
    """Test the same provider adapter used by real requests."""
    try:
        reply = await call_llm_with_config(
            req.model_dump(),
            [{"role": "user", "content": "说'连接成功'"}],
            timeout=15,
            max_tokens=50,
        )
        return {"success": True, "data": {"message": reply, "model": req.model}}
    except Exception as e:
        return {"success": False, "error": str(e), "code": "provider_connection_failed"}


@router.get("/api/profile")
async def get_profile(file_store: FileStore = Depends(get_global_store)):
    """获取用户画像。"""
    profile = file_store.get_profile()
    return {"success": True, "data": profile}


@router.patch("/api/profile")
async def update_profile(
    profile: dict,
    file_store: FileStore = Depends(get_global_store),
):
    """更新用户画像。"""
    updated = file_store.update_profile(**profile)
    return {"success": True, "data": updated}
