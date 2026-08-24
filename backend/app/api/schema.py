"""Project-scoped wiki schema API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_project_schema_store, get_project_wiki_store

router = APIRouter(prefix="/api/projects/{project_id}/schema")


class UpdateSchemaRequest(BaseModel):
    config: dict
    instructions: str


@router.get("")
async def get_schema(schema_store=Depends(get_project_schema_store)):
    try:
        return {"success": True, "data": schema_store.get()}
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("")
async def update_schema(
    request: UpdateSchemaRequest,
    schema_store=Depends(get_project_schema_store),
    wiki_store=Depends(get_project_wiki_store),
):
    used_types = {}
    for page in wiki_store.list_pages():
        page_type = str(page.get("type") or "other")
        if page_type != "other" and "/" in page["path"]:
            used_types.setdefault(page_type, page["path"].split("/", 1)[0])
    try:
        updated = schema_store.update(request.config, request.instructions, used_types)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for item in updated["config"]["pageTypes"]:
        if item.get("enabled"):
            (schema_store.project_dir / "wiki" / item["directory"]).mkdir(parents=True, exist_ok=True)
    return {"success": True, "data": updated}
