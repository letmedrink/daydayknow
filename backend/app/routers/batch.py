from fastapi import APIRouter, Depends, HTTPException, Header
from datetime import datetime
from typing import Optional
from ..models.schemas import BatchRequest, BatchResponse, BatchHealthResponse, ErrorResponse
from ..dependencies import verify_cron_secret
from ..services.batch_processor import process_daily_terms
from ..utils.logger import create_module_logger

log = create_module_logger("batch")
router = APIRouter()

@router.get("/api/batch", response_model=BatchHealthResponse)
async def batch_health():
    """批处理健康检查"""
    return BatchHealthResponse(
        message="批处理API端点",
        usage="POST /api/batch with Authorization header",
        timestamp=datetime.now().isoformat()
    )

@router.post("/api/batch", response_model=BatchResponse)
async def batch_process(
    request: BatchRequest = BatchRequest(),
    authorization: Optional[str] = Header(None)
):
    """批处理任务"""
    try:
        # 验证密钥
        if not await verify_cron_secret(authorization):
            raise HTTPException(status_code=401, detail="未授权")
        
        # 执行批处理
        result = await process_daily_terms(
            user_id=request.userId,
            target_date=request.date
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "批处理失败"))
        
        return BatchResponse(
            message="批处理完成",
            processed=result["processed"],
            skipped=result["skipped"],
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("批处理失败", e)
        raise HTTPException(status_code=500, detail="服务器内部错误")