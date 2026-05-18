from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.schemas import StarMapResponse, StarNode, StarEdge, ErrorResponse
from ..dependencies import get_current_user
from ..services.supabase_client import get_db, is_mock_mode
from ..utils.logger import create_module_logger

log = create_module_logger("star-map")
router = APIRouter()

@router.get("/api/star-map", response_model=StarMapResponse)
async def get_star_map(
    user_id: str = Depends(get_current_user)
):
    """获取知识图谱（星图）"""
    try:
        db = get_db()
        
        # 检查是否为模拟模式
        if is_mock_mode():
            mock_data = db.init_mock_data(user_id)
            if mock_data:
                # 生成模拟星图数据
                nodes = []
                edges = []
                
                mock_terms = mock_data["mockTerms"]
                for i, term in enumerate(mock_terms):
                    nodes.append(StarNode(
                        id=f"node_{i}",
                        user_id=user_id,
                        term_id=term["id"],
                        term_name=term["term"],
                        domain=term["domain"],
                        x=150 + (i * 100),
                        y=250,
                        confirmed_at=term["captured_at"]
                    ))
                
                # 添加连线
                if len(nodes) > 1:
                    edges.append(StarEdge(
                        id="edge_1",
                        user_id=user_id,
                        from_node_id=nodes[0].id,
                        to_node_id=nodes[1].id,
                        relation_type="same_domain",
                        description="同属宏观经济学领域",
                        discovered_at=datetime.now().isoformat()
                    ))
                
                # 计算统计信息
                domains = list(set(node.domain for node in nodes))
                
                return StarMapResponse(
                    nodes=nodes,
                    edges=edges,
                    stats={
                        "total_nodes": len(nodes),
                        "total_edges": len(edges),
                        "domains": domains
                    }
                )
        
        # 查询星图节点
        nodes_result = db.from_("star_nodes").select("*").eq("user_id", user_id).order("confirmed_at", ascending=False).execute()
        nodes_data = nodes_result.get("data") or []
        nodes_error = nodes_result.get("error")
        
        if nodes_error:
            log.error("查询星图节点失败", nodes_error)
            raise HTTPException(status_code=500, detail="查询星图节点失败")
        
        # 查询星图连线
        edges_result = db.from_("star_edges").select("*").eq("user_id", user_id).execute()
        edges_data = edges_result.get("data") or []
        edges_error = edges_result.get("error")
        
        if edges_error:
            log.error("查询星图连线失败", edges_error)
            raise HTTPException(status_code=500, detail="查询星图连线失败")
        
        # 处理节点坐标（如果没有坐标则使用圆形布局）
        nodes = []
        for i, node_data in enumerate(nodes_data):
            if not node_data.get("x") or not node_data.get("y"):
                # 圆形布局
                import math
                angle = (2 * math.pi * i) / len(nodes_data)
                radius = 150
                x = 250 + radius * math.cos(angle)
                y = 250 + radius * math.sin(angle)
            else:
                x = node_data["x"]
                y = node_data["y"]
            
            nodes.append(StarNode(
                id=node_data["id"],
                user_id=node_data["user_id"],
                term_id=node_data["term_id"],
                term_name=node_data["term_name"],
                domain=node_data["domain"],
                x=x,
                y=y,
                confirmed_at=node_data["confirmed_at"]
            ))
        
        edges = [StarEdge(**edge) for edge in edges_data]
        
        # 计算统计信息
        domains = list(set(node.domain for node in nodes))
        
        return StarMapResponse(
            nodes=nodes,
            edges=edges,
            stats={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "domains": domains
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("获取星图数据失败", e)
        raise HTTPException(status_code=500, detail="获取星图数据失败")