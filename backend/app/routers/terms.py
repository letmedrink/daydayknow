from fastapi import APIRouter, Depends, HTTPException
from ..models.schemas import TermConfirmResponse, ErrorResponse
from ..dependencies import get_current_user
from ..services.supabase_client import get_db, is_mock_mode
from ..utils.logger import create_module_logger
import uuid

log = create_module_logger("terms")
router = APIRouter()

@router.post("/api/terms/{term_id}/confirm", response_model=TermConfirmResponse)
async def confirm_term(
    term_id: str,
    user_id: str = Depends(get_current_user)
):
    """确认术语"""
    try:
        if not term_id:
            raise HTTPException(status_code=400, detail="缺少termId参数")
        
        db = get_db()
        
        # 查询术语
        term_result = db.from_("terms").select("*").eq("id", term_id).eq("user_id", user_id).single().execute()
        term = term_result.get("data")
        term_error = term_result.get("error")
        
        if term_error or not term:
            raise HTTPException(status_code=404, detail="术语不存在")
        
        # 更新术语状态
        update_result = db.from_("terms").update({"processed_status": "done"}).eq("id", term_id).execute()
        update_error = update_result.get("error")
        
        if update_error:
            log.error("更新术语状态失败", update_error)
            raise HTTPException(status_code=500, detail="更新术语状态失败")
        
        # 创建星图节点
        import random
        node_id = str(uuid.uuid4())
        node_data = {
            "id": node_id,
            "user_id": user_id,
            "term_id": term_id,
            "term_name": term["term"],
            "domain": term["domain"],
            "x": random.uniform(50, 450),
            "y": random.uniform(50, 450),
            "confirmed_at": "now()"
        }
        
        insert_node_result = db.from_("star_nodes").insert(node_data).execute()
        insert_node_error = insert_node_result.get("error")
        
        if insert_node_error:
            log.error("创建星图节点失败", insert_node_error)
            raise HTTPException(status_code=500, detail="创建星图节点失败")
        
        # 查询同领域节点
        same_domain_nodes_result = db.from_("star_nodes").select("*").eq("user_id", user_id).eq("domain", term["domain"]).neq("id", node_id).execute()
        same_domain_nodes = same_domain_nodes_result.get("data") or []
        
        # 创建连线
        new_connections = []
        for other_node in same_domain_nodes:
            edge_id = str(uuid.uuid4())
            edge_data = {
                "id": edge_id,
                "user_id": user_id,
                "from_node_id": node_id,
                "to_node_id": other_node["id"],
                "relation_type": "same_domain",
                "description": f"同属{term['domain']}领域",
                "discovered_at": "now()"
            }
            
            insert_edge_result = db.from_("star_edges").insert(edge_data).execute()
            insert_edge_error = insert_edge_result.get("error")
            
            if not insert_edge_error:
                new_connections.append({
                    "from": node_id,
                    "to": other_node["id"],
                    "description": f"同属{term['domain']}领域"
                })
        
        return TermConfirmResponse(
            message="已点亮星图",
            star_node_id=node_id,
            new_connections=new_connections,
            term_name=term["term"],
            domain=term["domain"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("射箭确认失败", e)
        raise HTTPException(status_code=500, detail="射箭确认失败")