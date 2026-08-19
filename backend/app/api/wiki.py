"""Wiki 页面/图谱/搜索 API。"""
import mimetypes
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..dependencies import get_project_dir, get_project_wiki_store

router = APIRouter(prefix="/api/projects/{project_id}/wiki")


class SavePageRequest(BaseModel):
    path: str
    content: str


class RenamePageRequest(BaseModel):
    old_path: str
    new_path: str
    update_links: bool = True


class RestorePageRequest(BaseModel):
    path: str
    version_id: str


@router.get("/pages")
async def list_pages(wiki_store=Depends(get_project_wiki_store)):
    """列出所有 wiki 页面（树形）。"""
    tree = wiki_store.build_file_tree()
    pages = wiki_store.list_pages()
    return {"success": True, "data": {"tree": tree, "pages": pages}}


@router.get("/page")
async def get_page(path: str = Query(...), wiki_store=Depends(get_project_wiki_store)):
    """读取单个 wiki 页面。"""
    page = wiki_store.read_page(path)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    return {"success": True, "data": page}


@router.put("/page")
async def save_page(req: SavePageRequest, wiki_store=Depends(get_project_wiki_store)):
    """Create or replace a Markdown page, preserving the previous version."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="页面内容不能为空")
    try:
        path = wiki_store.write_raw_page(req.path, req.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": wiki_store.read_page(path)}


@router.post("/page/rename")
async def rename_page(req: RenamePageRequest, wiki_store=Depends(get_project_wiki_store)):
    try:
        result = wiki_store.rename_page(req.old_path, req.new_path, req.update_links)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "data": result}


@router.get("/page/history")
async def list_page_history(path: str = Query(...), wiki_store=Depends(get_project_wiki_store)):
    try:
        versions = wiki_store.list_page_history(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": versions}


@router.get("/page/history/version")
async def get_page_history(path: str = Query(...), version_id: str = Query(...), wiki_store=Depends(get_project_wiki_store)):
    try:
        version = wiki_store.read_page_history(path, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not version:
        raise HTTPException(status_code=404, detail="历史版本不存在")
    return {"success": True, "data": version}


@router.post("/page/history/restore")
async def restore_page_history(req: RestorePageRequest, wiki_store=Depends(get_project_wiki_store)):
    try:
        page = wiki_store.restore_page_history(req.path, req.version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": page}


@router.delete("/page")
async def delete_page(path: str = Query(...), wiki_store=Depends(get_project_wiki_store)):
    """删除 wiki 页面。"""
    if not wiki_store.delete_page(path):
        raise HTTPException(status_code=404, detail="页面不存在")
    return {"success": True}


@router.get("/graph")
async def get_graph(wiki_store=Depends(get_project_wiki_store)):
    """获取知识图谱（节点+边+社区+maxLinks）。"""
    graph = wiki_store.build_graph()
    return {"success": True, "data": graph}


@router.get("/graph/insights")
async def get_graph_insights(wiki_store=Depends(get_project_wiki_store)):
    """获取图谱洞察（Surprising Connections + Knowledge Gaps）。"""
    insights = wiki_store.graph_insights()
    return {"success": True, "data": insights}


@router.get("/media/{path:path}")
async def serve_media(path: str, project_dir=Depends(get_project_dir)):
    """提供 wiki/media/ 下的图片等静态文件。"""
    file_path = project_dir / "wiki" / "media" / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    # 安全检查：防止路径穿越
    media_root = (project_dir / "wiki" / "media").resolve()
    try:
        file_path.resolve().relative_to(media_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="禁止访问")
    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type)


@router.get("/search")
async def search_wiki(q: str = Query(...), limit: int = Query(10), wiki_store=Depends(get_project_wiki_store)):
    """搜索 wiki 页面。"""
    results = wiki_store.search(q, max_results=limit)
    return {"success": True, "data": results}


@router.get("/graph/search")
async def search_graph(q: str = Query(...), wiki_store=Depends(get_project_wiki_store)):
    """搜索图谱节点。"""
    graph = wiki_store.build_graph()
    query_lower = q.lower()
    from ..storage.wiki_store import _tokenize
    tokens = _tokenize(query_lower)
    if not tokens:
        return {"success": True, "data": {"nodes": [], "edges": []}}

    matched_ids = set()
    for n in graph["nodes"]:
        combined = f"{n['id']} {n['title']} {n['type']} {n.get('path', '')}".lower()
        if all(t in combined for t in tokens):
            matched_ids.add(n["id"])

    matched_nodes = [n for n in graph["nodes"] if n["id"] in matched_ids]
    matched_edges = [
        e for e in graph["edges"]
        if e["source"] in matched_ids and e["target"] in matched_ids
    ]

    return {"success": True, "data": {"nodes": matched_nodes, "edges": matched_edges}}
