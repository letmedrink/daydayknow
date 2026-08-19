"""审阅项 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..dependencies import get_project_file_store, get_project_wiki_store

router = APIRouter(prefix="/api/projects/{project_id}/reviews")


class ResolveReviewRequest(BaseModel):
    action: str
    path: str | None = None
    target_path: str | None = None
    source_paths: list[str] | None = None
    content: str | None = None


@router.get("")
async def list_reviews(file_store=Depends(get_project_file_store)):
    """获取待审阅项列表。"""
    reviews = file_store.get_reviews()
    return {"success": True, "data": reviews}


@router.post("/{review_id}/resolve")
async def resolve_review(
    review_id: str, req: ResolveReviewRequest,
    file_store=Depends(get_project_file_store), wiki_store=Depends(get_project_wiki_store),
):
    """处理审阅项。"""
    review = file_store.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="审阅项不存在")
    try:
        if req.action in {"skip", "跳过", "resolved_manually"}:
            result = None
        elif req.action == "create_page":
            if not req.path or not req.content:
                raise HTTPException(status_code=400, detail="创建页面需要 path 和 content")
            wiki_store.write_raw_page(req.path, req.content)
            result = {"path": req.path}
        elif req.action == "merge_pages":
            source_paths = req.source_paths or []
            if not req.target_path or not source_paths:
                raise HTTPException(status_code=400, detail="合并页面需要 target_path 和 source_paths")
            result = wiki_store.merge_pages(source_paths, req.target_path)
        else:
            raise HTTPException(status_code=400, detail="不支持的审阅动作")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    file_store.resolve_review(review_id, req.action)
    return {"success": True, "data": result}
