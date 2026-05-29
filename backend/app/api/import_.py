import csv
import io
import json

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List

from ..agents.context import AgentContext, Message
from ..agents.extraction_agent import ExtractionAgent
from ..db.factory import get_graph_store
from ..dependencies import get_current_user
from ..utils.logger import create_module_logger

log = create_module_logger("api.import")
router = APIRouter()

graph_store = get_graph_store()


class ImportRequest(BaseModel):
    content: str
    source_name: Optional[str] = None


@router.post("/api/import")
async def import_content(
    req: ImportRequest,
    user_id: str = Depends(get_current_user),
):
    """导入文本内容，自动提取知识概念。"""
    if not req.content.strip():
        return {"nodes": [], "edges": [], "error": "内容不能为空"}

    # 构造上下文，复用 ExtractionAgent
    context = AgentContext(
        conversation_id="import",
        user_id=user_id,
        messages=[Message(role="user", content=req.content)],
    )

    extraction_agent = ExtractionAgent()
    result = await extraction_agent.execute(context)

    if not result.success:
        log.warn("Import extraction failed", result.error)
        return {"nodes": [], "edges": [], "error": result.error}

    stored = await graph_store.store_extraction(
        user_id=user_id,
        extraction=result.data,
        source_ref=req.source_name or "import",
    )

    return {"nodes": stored["nodes"], "edges": stored["edges"]}


@router.post("/api/import/batch")
async def import_batch(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user),
):
    """批量导入文件（支持 JSON 和 CSV）。

    JSON 格式：
      - 知识提取格式: {"nodes": [...], "edges": [...]}
      - 节点列表: [{"name": "...", "domain": "...", "description": "..."}]

    CSV 格式：
      - 列: name, domain, description
      - 每行一个节点
    """
    results = []

    for file in files:
        filename = file.filename or "unknown"
        content = await file.read()
        text = content.decode("utf-8", errors="replace")

        try:
            if filename.endswith(".json"):
                data = json.loads(text)
                stored = await _import_json(user_id, data, filename)
            elif filename.endswith(".csv"):
                stored = await _import_csv(user_id, text, filename)
            else:
                # 尝试用 ExtractionAgent 处理纯文本
                stored = await _import_text(user_id, text, filename)

            results.append({
                "filename": filename,
                "nodes": stored["nodes"],
                "edges": stored["edges"],
            })
        except Exception as e:
            log.warn(f"Import failed for {filename}: {e}")
            results.append({
                "filename": filename,
                "nodes": [],
                "edges": [],
                "error": str(e),
            })

    total_nodes = sum(len(r["nodes"]) for r in results)
    total_edges = sum(len(r["edges"]) for r in results)
    return {
        "results": results,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
    }


async def _import_json(user_id: str, data: dict | list, source_ref: str) -> dict:
    """导入 JSON 数据。"""
    if isinstance(data, list):
        # 节点列表格式 [{"name": "...", ...}]
        extraction = {"nodes": data, "edges": []}
    elif "nodes" in data:
        # 知识提取格式 {"nodes": [...], "edges": [...]}
        extraction = data
    else:
        # 单个节点
        extraction = {"nodes": [data], "edges": []}

    return await graph_store.store_extraction(
        user_id=user_id,
        extraction=extraction,
        source_ref=source_ref,
    )


async def _import_csv(user_id: str, text: str, source_ref: str) -> dict:
    """导入 CSV 数据。"""
    reader = csv.DictReader(io.StringIO(text))
    nodes = []
    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            continue
        node = {"name": name}
        if row.get("domain"):
            node["domain"] = row["domain"].strip()
        if row.get("description"):
            node["description"] = row["description"].strip()
        nodes.append(node)

    extraction = {"nodes": nodes, "edges": []}
    return await graph_store.store_extraction(
        user_id=user_id,
        extraction=extraction,
        source_ref=source_ref,
    )


async def _import_text(user_id: str, text: str, source_ref: str) -> dict:
    """用 ExtractionAgent 处理纯文本。"""
    context = AgentContext(
        conversation_id="import",
        user_id=user_id,
        messages=[Message(role="user", content=text)],
    )
    agent = ExtractionAgent()
    result = await agent.execute(context)
    if not result.success:
        return {"nodes": [], "edges": []}
    return await graph_store.store_extraction(
        user_id=user_id,
        extraction=result.data,
        source_ref=source_ref,
    )
