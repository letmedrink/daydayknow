import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from datetime import datetime, timedelta
from typing import Optional
from ..models.schemas import (
    DailyDocResponse, DailyDocNotFoundResponse, DailyDocGenerateRequest,
    DailyDocGenerateResponse, ErrorResponse, AsyncTaskResponse, TaskResponse
)
from ..dependencies import get_current_user
from ..services.supabase_client import get_db, is_mock_mode
from ..services.task_manager import task_manager, TaskStatus
from ..utils.logger import create_module_logger

log = create_module_logger("daily-doc")
router = APIRouter()

@router.get("/api/daily-doc", response_model=DailyDocResponse | DailyDocNotFoundResponse)
async def get_daily_doc(
    date: Optional[str] = Query(None),
    force: Optional[bool] = Query(False),
    user_id: str = Depends(get_current_user)
):
    """获取每日知识文档"""
    try:
        doc_date = date or datetime.now().strftime("%Y-%m-%d")
        db = get_db()
        
        if is_mock_mode():
            mock_data = db.init_mock_data(user_id)
            if mock_data:
                mock_doc = mock_data["mockDailyDoc"]
                return DailyDocResponse(
                    doc_date=mock_doc["doc_date"],
                    title=f"昨日你收录了{mock_doc['term_count']}个术语",
                    cards=mock_doc["cards"],
                    new_connections=[],
                    generated_at=mock_doc["generated_at"]
                )
        
        doc_result = db.from_("daily_docs").select("*").eq("user_id", user_id).eq("doc_date", doc_date).single().execute()
        doc = doc_result.get("data")
        doc_error = doc_result.get("error")
        
        if doc_error or not doc:
            terms_result = db.from_("terms").select("*").eq("user_id", user_id).gte("captured_at", f"{doc_date}T00:00:00").lte("captured_at", f"{doc_date}T23:59:59").execute()
            terms = terms_result.get("data") or []
            
            return DailyDocNotFoundResponse(
                doc_date=doc_date,
                title="日报未生成",
                cards=[],
                new_connections=[],
                message="今日日报尚未生成",
                terms_collected=[{
                    "id": t["id"],
                    "term": t["term"],
                    "domain": t["domain"],
                    "captured_at": t["captured_at"]
                } for t in terms],
                terms_count=len(terms),
                can_generate=len(terms) > 0
            )
        
        new_connections = []
        if doc.get("cards"):
            term_ids = [card["term_id"] for card in doc["cards"]]
            nodes_result = db.from_("star_nodes").select("*").eq("user_id", user_id).in_("term_id", term_ids).execute()
            nodes = nodes_result.get("data") or []
            
            if nodes:
                node_ids = [node["id"] for node in nodes]
                edges_result = db.from_("star_edges").select("*").eq("user_id", user_id).or_(f"from_node_id.in.({','.join(node_ids)}),to_node_id.in.({','.join(node_ids)})").execute()
                edges = edges_result.get("data") or []
                
                new_connections = [{
                    "from": edge["from_node_id"],
                    "to": edge["to_node_id"],
                    "description": edge["description"]
                } for edge in edges]
        
        return DailyDocResponse(
            doc_date=doc["doc_date"],
            title=f"昨日你收录了{doc['term_count']}个术语",
            cards=doc["cards"],
            new_connections=new_connections,
            generated_at=doc["generated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("获取日报失败", e)
        raise HTTPException(status_code=500, detail="获取日报失败")

async def _generate_single_term(term: dict, use_mock: bool) -> dict:
    """为单个术语生成解释"""
    if use_mock:
        return {
            "simple": f"{term['term']}是一个{term.get('domain', '未知')}领域的专业术语",
            "deep": f"{term['term']}是{term.get('domain', '未知')}领域的一个重要概念。",
            "case": f"关于{term['term']}的具体案例...",
            "history": f"{term['term']}的起源和发展...",
            "related": ["相关术语1", "相关术语2", "相关术语3"],
            "controversy": "",
            "source": "模拟来源"
        }
    
    from ..services.batch_processor import generate_mock_explanation, HYDE_PROMPT, FINAL_PROMPT
    from ..services.llm_client import llm_chat_completion, llm_json_completion
    
    try:
        # 合并为单次 LLM 调用，减少延迟
        combined_prompt = f"""你是一个善于用通俗语言解释复杂概念的朋友。为术语"{term['term']}"（领域：{term.get('domain', 'unknown')}）生成详细解释。

输出JSON格式：
{{
  "simple": "一句话白话解释，让小学生也能听懂，20字以内",
  "deep": "深入浅出的详细解释，200-300字",
  "case": "1-2个具体案例，150-200字",
  "history": "术语的起源和发展历程，100-150字",
  "related": ["3-5个相关术语"],
  "controversy": "争议或不同观点（如有），100字",
  "source": "参考来源"
}}"""
        
        explanation = await llm_json_completion(
            system_prompt=combined_prompt,
            user_prompt=term["term"],
            temperature=0.3
        )
        return explanation
    except Exception as error:
        log.error(f"LLM调用失败: {term['term']}", error)
        return generate_mock_explanation(term["term"], term.get("domain", "unknown"))

async def _generate_daily_doc_background(task_id: str, user_id: str, doc_date: str):
    """后台生成日报的任务"""
    db = get_db()
    
    try:
        task_manager.update_progress(task_id, 0, 1, "查询术语...")
        
        terms_result = db.from_("terms").select("*").eq("user_id", user_id).gte("captured_at", f"{doc_date}T00:00:00").lte("captured_at", f"{doc_date}T23:59:59").execute()
        terms = terms_result.get("data") or []
        
        if not terms:
            task_manager.fail_task(task_id, "没有收集到术语")
            return
        
        total_terms = len(terms)
        task_manager.update_progress(task_id, 0, total_terms, f"开始生成，共{total_terms}个术语")
        
        use_mock = is_mock_mode()
        
        # 并发生成所有术语解释（最多3个并发）
        async def process_term(i, term):
            task_manager.update_progress(task_id, i, total_terms, f"正在生成: {term['term']}")
            explanation = await _generate_single_term(term, use_mock)
            task_manager.update_progress(task_id, i + 1, total_terms, f"已完成: {term['term']}")
            return {
                "term_id": term["id"],
                "term": term["term"],
                "context": term["original_context"],
                **explanation
            }
        
        # 使用 asyncio.gather 并发处理，限制并发数为3
        semaphore = asyncio.Semaphore(3)
        
        async def process_with_semaphore(i, term):
            async with semaphore:
                return await process_term(i, term)
        
        cards = await asyncio.gather(*[process_with_semaphore(i, term) for i, term in enumerate(terms)])
        
        task_manager.update_progress(task_id, total_terms, total_terms, "保存日报...")
        
        insert_result = db.from_("daily_docs").insert({
            "user_id": user_id,
            "doc_date": doc_date,
            "cards": cards,
            "term_count": len(cards),
            "generated_at": datetime.now().isoformat()
        }).execute()
        
        insert_error = insert_result.get("error")
        
        if insert_error:
            task_manager.fail_task(task_id, f"保存日报失败: {insert_error}")
            return
        
        task_manager.complete_task(task_id, {
            "message": "日报生成成功",
            "doc_date": doc_date,
            "term_count": len(cards)
        })
        
    except Exception as e:
        log.error("日报生成失败", e)
        task_manager.fail_task(task_id, str(e))

@router.post("/api/daily-doc/generate", response_model=AsyncTaskResponse)
async def generate_daily_doc(
    request: DailyDocGenerateRequest = DailyDocGenerateRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: str = Depends(get_current_user)
):
    """异步生成每日知识文档"""
    try:
        doc_date = request.date or datetime.now().strftime("%Y-%m-%d")
        db = get_db()
        
        existing_doc_result = db.from_("daily_docs").select("*").eq("user_id", user_id).eq("doc_date", doc_date).single().execute()
        existing_doc = existing_doc_result.get("data")
        
        if existing_doc:
            return AsyncTaskResponse(
                message="日报已存在",
                task_id="",
                status_url=""
            )
        
        # 检查是否有正在进行的任务
        user_tasks = task_manager.get_user_tasks(user_id, "generate_daily_doc")
        for task in user_tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                return AsyncTaskResponse(
                    message="日报正在生成中",
                    task_id=task.task_id,
                    status_url=f"/api/daily-doc/task/{task.task_id}"
                )
        
        # 创建新任务
        task = task_manager.create_task("generate_daily_doc", user_id)
        
        # 使用 BackgroundTasks 启动后台任务
        background_tasks.add_task(_generate_daily_doc_background, task.task_id, user_id, doc_date)
        
        return AsyncTaskResponse(
            message="日报生成已启动",
            task_id=task.task_id,
            status_url=f"/api/daily-doc/task/{task.task_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("启动日报生成失败", e)
        raise HTTPException(status_code=500, detail="启动日报生成失败")

@router.get("/api/daily-doc/task/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    """查询任务状态"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        total=task.total,
        current_step=task.current_step,
        percent=task.percent,
        result=task.result,
        error=task.error
    )