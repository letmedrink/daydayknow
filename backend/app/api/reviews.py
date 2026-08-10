"""审阅项 API。"""
from fastapi import APIRouter, Depends
from ..dependencies import get_active_file_store

router = APIRouter(prefix="/api/reviews")


@router.get("")
async def list_reviews(file_store=Depends(get_active_file_store)):
    """获取待审阅项列表。"""
    reviews = file_store.get_reviews()
    return {"success": True, "data": reviews}


@router.post("/{review_id}/resolve")
async def resolve_review(review_id: str, action: str = "skip", file_store=Depends(get_active_file_store)):
    """处理审阅项。"""
    if not file_store.resolve_review(review_id, action):
        return {"success": False, "error": "审阅项不存在"}
    return {"success": True}
