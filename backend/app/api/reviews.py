"""审阅项 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..dependencies import get_project_file_store

router = APIRouter(prefix="/api/projects/{project_id}/reviews")


class ResolveReviewRequest(BaseModel):
    action: str


@router.get("")
async def list_reviews(file_store=Depends(get_project_file_store)):
    """获取待审阅项列表。"""
    reviews = file_store.get_reviews()
    return {"success": True, "data": reviews}


@router.post("/{review_id}/resolve")
async def resolve_review(review_id: str, req: ResolveReviewRequest, file_store=Depends(get_project_file_store)):
    """处理审阅项。"""
    if req.action not in {"skip", "跳过"}:
        raise HTTPException(status_code=400, detail="该动作需要通过生成/研究工作流执行，不能直接结案")
    if not file_store.resolve_review(review_id, "skip"):
        raise HTTPException(status_code=404, detail="审阅项不存在")
    return {"success": True}
