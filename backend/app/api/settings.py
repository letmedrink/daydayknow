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
    context_window: int = 0
    clear_api_key: bool = False
    has_api_key: bool = False


class SettingsUpdate(BaseModel):
    llm_providers: Optional[dict] = Field(default=None, alias="llmProviders")
    active_provider_id: Optional[str] = Field(default=None, alias="activeProviderId")
    search_api_config: Optional[dict] = Field(default=None, alias="searchApiConfig")
    output_language: Optional[str] = Field(default=None, alias="outputLanguage")
    multimodal_model: Optional[str] = Field(default=None, alias="multimodalModel")
    ingest_detailed_progress: Optional[bool] = Field(default=None, alias="ingestDetailedProgress")
    retrieval_config: Optional[dict] = Field(default=None, alias="retrievalConfig")

    model_config = {"populate_by_name": True}


@router.get("/api/settings")
async def get_settings(file_store: FileStore = Depends(get_global_store)):
    """获取设置。"""
    return {"success": True, "data": _redact_settings(file_store.get_settings())}


@router.patch("/api/settings")
async def update_settings(
    req: SettingsUpdate,
    file_store: FileStore = Depends(get_global_store),
):
    """更新设置。"""
    updates = {}
    current = file_store.get_settings()
    if req.llm_providers is not None:
        updates["llmProviders"] = _merge_secret_map(current.get("llmProviders", {}), req.llm_providers)
    if req.active_provider_id is not None:
        updates["activeProviderId"] = req.active_provider_id
    if req.search_api_config is not None:
        updates["searchApiConfig"] = _merge_secret_config(current.get("searchApiConfig", {}), req.search_api_config)
    if req.output_language is not None:
        updates["outputLanguage"] = req.output_language
    if req.multimodal_model is not None:
        updates["multimodalModel"] = req.multimodal_model
    if req.ingest_detailed_progress is not None:
        updates["ingestDetailedProgress"] = req.ingest_detailed_progress
    if req.retrieval_config is not None:
        mode = req.retrieval_config.get("mode", "lexical")
        if mode not in {"lexical", "hybrid"}:
            mode = "lexical"
        updates["retrievalConfig"] = {
            "mode": mode,
            "candidateLimit": max(5, min(int(req.retrieval_config.get("candidateLimit", 12)), 30)),
            "rerankLimit": max(1, min(int(req.retrieval_config.get("rerankLimit", 5)), 10)),
        }

    result = file_store.update_settings(**updates)
    return {"success": True, "data": _redact_settings(result)}


@router.post("/api/settings/test-connection")
async def test_connection(req: LLMProviderConfig, file_store: FileStore = Depends(get_global_store)):
    """Test the same provider adapter used by real requests."""
    try:
        config = req.model_dump()
        if not config.get("api_key") and not req.clear_api_key:
            stored = file_store.get_settings().get("llmProviders", {}).get(req.id, {})
            config["api_key"] = stored.get("api_key", "")
        reply = await call_llm_with_config(
            config,
            [{"role": "user", "content": "说'连接成功'"}],
            timeout=15,
            max_tokens=50,
        )
        return {"success": True, "data": {"message": reply, "model": req.model}}
    except Exception as e:
        return {"success": False, "error": str(e), "code": "provider_connection_failed"}


def _merge_secret_map(current: dict, incoming: dict) -> dict:
    merged = {}
    for provider_id, raw in incoming.items():
        provider = dict(raw)
        old_key = current.get(provider_id, {}).get("api_key", "")
        if provider.pop("clear_api_key", False):
            provider["api_key"] = ""
        elif not provider.get("api_key"):
            provider["api_key"] = old_key
        provider.pop("has_api_key", None)
        merged[provider_id] = provider
    return merged


def _merge_secret_config(current: dict, incoming: dict) -> dict:
    merged = {**current, **incoming}
    if incoming.get("clear_api_key"):
        merged["api_key"] = ""
    elif not incoming.get("api_key"):
        merged["api_key"] = current.get("api_key", "")
    merged.pop("clear_api_key", None)
    merged.pop("has_api_key", None)
    return merged


def _redact_settings(settings: dict) -> dict:
    redacted = {**settings}
    providers = {}
    for provider_id, raw in settings.get("llmProviders", {}).items():
        provider = {**raw, "has_api_key": bool(raw.get("api_key")), "api_key": ""}
        providers[provider_id] = provider
    redacted["llmProviders"] = providers
    search = dict(settings.get("searchApiConfig", {}))
    search["has_api_key"] = bool(search.get("api_key"))
    search["api_key"] = ""
    redacted["searchApiConfig"] = search
    return redacted


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
