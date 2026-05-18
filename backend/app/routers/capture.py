from fastapi import APIRouter, Depends, HTTPException
from ..models.schemas import TermCreate, TermResponse, ErrorResponse
from ..dependencies import get_current_user
from ..services.supabase_client import get_db, is_mock_mode
from ..services.llm_client import llm_json_completion, validate_llm_config
from ..utils.logger import create_module_logger

log = create_module_logger("capture")
router = APIRouter()

# 模拟术语提取
MOCK_TERMS = {
    "流动性陷阱": {"domain": "宏观经济学"},
    "零利率下限": {"domain": "宏观经济学"},
    "量化宽松": {"domain": "宏观经济学"},
    "通货膨胀": {"domain": "宏观经济学"},
    "供给侧改革": {"domain": "宏观经济学"},
    "中等收入陷阱": {"domain": "发展经济学"},
    "人口红利": {"domain": "发展经济学"},
    "全要素生产率": {"domain": "经济增长理论"},
    "基尼系数": {"domain": "收入分配"},
    "恩格尔系数": {"domain": "消费经济学"},
}

async def extract_terms_mock(text: str) -> dict:
    """模拟术语提取"""
    import re
    
    found_terms = []
    for term in MOCK_TERMS:
        if term in text:
            found_terms.append({"term": term, "confidence": 0.9})
    
    if not found_terms:
        words = re.findall(r'[\u4e00-\u9fa5]{2,8}', text)
        if words:
            found_terms = [{"term": words[0], "confidence": 0.5}]
            domain = "未知领域"
        else:
            found_terms = [{"term": "未知术语", "confidence": 0.1}]
            domain = "unknown"
    else:
        domain = MOCK_TERMS[found_terms[0]["term"]]["domain"]
    
    # 按置信度排序，取前3个
    found_terms.sort(key=lambda x: x["confidence"], reverse=True)
    found_terms = found_terms[:3]
    
    return {
        "terms": found_terms,
        "domain": domain
    }

@router.post("/api/capture", response_model=TermResponse)
async def capture_term(
    request: TermCreate,
    user_id: str = Depends(get_current_user)
):
    """捕获术语"""
    try:
        if not request.raw_text:
            raise HTTPException(status_code=400, detail="缺少raw_text参数")
        
        # 检查是否使用模拟模式
        llm_config = validate_llm_config()
        use_mock = is_mock_mode() or not llm_config["valid"]
        
        if use_mock:
            result = await extract_terms_mock(request.raw_text)
        else:
            # 调用 LLM 提取术语
            system_prompt = """你是一个专业的术语提取助手。从用户提供的文本中提取专业术语。

输出JSON格式：
{
  "terms": [
    {"term": "术语1", "confidence": 0.95},
    {"term": "术语2", "confidence": 0.85},
    {"term": "术语3", "confidence": 0.75}
  ],
  "domain": "主要领域"
}

要求：
- 只提取专业术语，不提取普通词汇
- 最多提取3个最相关的术语，按相关度从高到低排序
- confidence 表示该术语在文本中的重要程度（0-1）
- 如果文本中没有明显的专业术语，返回空数组
- 领域应该是具体的学科分类"""
            
            result = await llm_json_completion(
                system_prompt=system_prompt,
                user_prompt=request.raw_text,
                temperature=0.3
            )
        
        terms_data = result.get("terms", [])
        domain = result.get("domain", "unknown")
        
        # 兼容旧格式（纯字符串数组）
        if terms_data and isinstance(terms_data[0], str):
            terms_data = [{"term": t, "confidence": 0.8} for t in terms_data]
        
        if not terms_data:
            terms_data = [{"term": "未知术语", "confidence": 0.1}]
            domain = "unknown"
        
        # 取前3个最相关的
        terms_data = terms_data[:3]
        
        # 保存到数据库
        db = get_db()
        saved_count = 0
        
        for item in terms_data:
            insert_result = db.from_("terms").insert({
                "user_id": user_id,
                "term": item["term"],
                "original_context": request.raw_text,
                "domain": domain,
                "confidence": item.get("confidence", 0.8),
                "processed_status": "pending",
                "captured_at": "now()"
            }).execute()
            
            if not insert_result.get("error"):
                saved_count += 1
        
        return TermResponse(
            extracted_term=terms_data[0]["term"],
            all_terms=[t["term"] for t in terms_data],
            domain=domain,
            message="已捕获，明早日报见",
            user_id=user_id,
            saved_count=saved_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("术语提取失败", e)
        raise HTTPException(status_code=500, detail="术语提取失败")