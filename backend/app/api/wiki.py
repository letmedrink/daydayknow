"""Wiki 页面/图谱/搜索 API。"""
from fastapi import APIRouter, Depends, Query, HTTPException
from ..dependencies import get_wiki_store

router = APIRouter(prefix="/api/wiki")


@router.get("/pages")
async def list_pages(wiki_store=Depends(get_wiki_store)):
    """列出所有 wiki 页面（树形）。"""
    tree = wiki_store.build_file_tree()
    pages = wiki_store.list_pages()
    return {"success": True, "data": {"tree": tree, "pages": pages}}


@router.get("/page")
async def get_page(path: str = Query(...), wiki_store=Depends(get_wiki_store)):
    """读取单个 wiki 页面。"""
    page = wiki_store.read_page(path)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    return {"success": True, "data": page}


@router.delete("/page")
async def delete_page(path: str = Query(...), wiki_store=Depends(get_wiki_store)):
    """删除 wiki 页面。"""
    if not wiki_store.delete_page(path):
        raise HTTPException(status_code=404, detail="页面不存在")
    return {"success": True}


@router.get("/graph")
async def get_graph(wiki_store=Depends(get_wiki_store)):
    """获取知识图谱（节点+边+社区+maxLinks）。"""
    graph = wiki_store.build_graph()
    return {"success": True, "data": graph}


@router.get("/graph/insights")
async def get_graph_insights(wiki_store=Depends(get_wiki_store)):
    """获取图谱洞察（Surprising Connections + Knowledge Gaps）。"""
    insights = wiki_store.graph_insights()
    return {"success": True, "data": insights}


@router.get("/search")
async def search_wiki(q: str = Query(...), limit: int = Query(10), wiki_store=Depends(get_wiki_store)):
    """搜索 wiki 页面。"""
    results = wiki_store.search(q, max_results=limit)
    return {"success": True, "data": results}


@router.get("/graph/search")
async def search_graph(q: str = Query(...), wiki_store=Depends(get_wiki_store)):
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
