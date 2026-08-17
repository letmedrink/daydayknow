"""Deep Research — 联网搜索 → LLM 综合 → 保存 wiki 页面。

研究流程（6 步）：
1. LLM 从主题生成 3-5 个搜索关键词
2. 调用搜索 API（Tavily / SerpApi）获取结果
3. LLM 综合搜索结果，产出结构化研究摘要
4. 复用摄入 pipeline 的 FILE 块协议生成 wiki 页面
5. 解析 FILE 块写入页面
6. 解析 REVIEW 块生成审阅项

LLM 调用次数：3 次（生成关键词 + 综合结果 + 生成页面）
"""

from typing import Optional

from ..config import settings
from ..storage import FileStore, WikiStore
from ..storage.wiki_store import parse_frontmatter, slugify
from ..llm import call_llm
from ..ingest.pipeline import parse_file_blocks, parse_review_blocks
from ..ingest.prompts import build_generation_prompt

import logging
log = logging.getLogger("research")


async def run_deep_research(
    topic: str,
    file_store: FileStore,
    wiki_store: WikiStore,
    global_store: FileStore,
    search_queries: Optional[list[str]] = None,
    progress_callback=None,
    auto_commit: bool = False,
) -> dict:
    """执行深度研究流程。

    Args:
        topic: 研究主题
        file_store: 文件存储
        wiki_store: wiki 存储
        search_queries: 搜索关键词列表（可选，默认从主题生成）
        progress_callback: 进度回调

    Returns:
        {files_written, reviews, search_results}
    """
    async def report(step, progress, message):
        log.info(f"[{step}] {message}")
        if progress_callback:
            await progress_callback(step, progress, message)

    # Step 1: 生成搜索关键词
    if not search_queries:
        await report("generate_queries", 0.05, "生成搜索关键词...")
        search_queries = await _generate_search_queries(topic, global_store)

    # Step 2: 联网搜索
    await report("search", 0.1, f"搜索 {len(search_queries)} 个关键词...")
    search_results = await _web_search(search_queries, global_store)
    if not search_results:
        raise RuntimeError("未获取到可用搜索结果，已停止研究，不会生成 Wiki")
    await report("search", 0.3, f"找到 {len(search_results)} 条结果")

    # Step 3: 综合搜索结果
    await report("synthesize", 0.4, "LLM 综合搜索结果...")
    synthesis = await _synthesize_results(topic, search_results, global_store)

    # Step 4: 生成 wiki 页面
    await report("generate", 0.6, "生成 wiki 页面...")
    pages = wiki_store.list_pages()
    index = "\n".join(f"- [{p['title']}] {p['path']}" for p in pages) if pages else "(知识库为空)"

    generation_prompt = build_generation_prompt(
        index, f"research-{slugify(topic)}.md", synthesis,
    )
    generation = await call_llm(
        global_store,
        generation_prompt,
        f"研究主题：{topic}\n\n综合分析：\n\n{synthesis}",
    )

    # Step 5: 构建待审核页面（默认不写入正式 Wiki）
    await report("stage", 0.8, "准备待审核 Wiki 页面...")
    file_blocks, warnings = parse_file_blocks(generation)

    proposals = []
    for block in file_blocks:
        rel_path = block["path"]
        wiki_rel = rel_path[5:] if rel_path.startswith("wiki/") else rel_path

        parsed = parse_frontmatter(block["content"])
        proposals.append({
            "path": wiki_rel,
            "content": block["content"],
            "title": parsed["frontmatter"].get("title", wiki_rel.rsplit("/", 1)[-1].removesuffix(".md")) if parsed["frontmatter"] else wiki_rel.rsplit("/", 1)[-1].removesuffix(".md"),
            "type": parsed["frontmatter"].get("type", "other") if parsed["frontmatter"] else "other",
            "replaces_existing": (wiki_store.wiki_dir / wiki_rel).exists(),
            "merge": True,
        })

    # Step 6: 解析 REVIEW 块
    review_items = parse_review_blocks(generation, source_path=f"wiki/queries/research-{slugify(topic)}.md")
    files_written = []
    if auto_commit:
        committed = wiki_store.commit_pages(proposals)
        files_written = [f"wiki/{path}" for path in committed]
    if auto_commit and review_items:
        file_store.add_reviews(review_items)

    await report("done", 1.0, f"研究完成: {len(files_written)} 个页面")

    return {
        "files_written": files_written,
        "reviews": review_items,
        "search_results": search_results,
        "warnings": warnings,
        "proposals": proposals,
        "status": "accepted" if auto_commit else "awaiting_review",
        "topic": topic,
        "search_queries": search_queries,
        "synthesis": synthesis,
    }


async def _generate_search_queries(topic: str, file_store: FileStore) -> list[str]:
    """用 LLM 从主题生成搜索关键词。"""
    try:
        response = await call_llm(
            file_store,
            "你是搜索关键词生成专家。根据给定主题，生成 3-5 个适合搜索引擎的关键词。每行一个关键词，不要编号或其他内容。",
            f"主题：{topic}",
        )
        queries = [q.strip() for q in response.strip().split("\n") if q.strip()]
        return queries[:5] if queries else [topic]
    except Exception:
        return [topic]


async def _web_search(queries: list[str], global_store: FileStore) -> list[dict]:
    """调用搜索 API 获取网络结果。"""
    stored = global_store.get_settings().get("searchApiConfig", {})
    provider = stored.get("provider") or settings.SEARCH_API_PROVIDER
    api_key = stored.get("api_key") or settings.SEARCH_API_KEY

    if not provider or not api_key:
        raise RuntimeError("未配置搜索 Provider 或 API Key，无法执行 Deep Research")

    results = []

    if provider == "tavily":
        results = await _search_tavily(queries, api_key)
    elif provider == "serpapi":
        results = await _search_serpapi(queries, api_key)
    else:
        raise RuntimeError(f"不支持的搜索提供商: {provider}")

    return results[:20]  # 最多 20 条结果


async def _search_tavily(queries: list[str], api_key: str) -> list[dict]:
    """Tavily 搜索 API。"""
    import httpx

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries:
            try:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": 5,
                        "include_answer": True,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "source": "tavily",
                        })
                    if data.get("answer"):
                        results.append({
                            "title": f"Tavily 综合回答: {query}",
                            "url": "",
                            "snippet": data["answer"],
                            "source": "tavily_answer",
                        })
            except Exception as e:
                log.error(f"Tavily 搜索失败 ({query}): {e}")

    return results


async def _search_serpapi(queries: list[str], api_key: str) -> list[dict]:
    """SerpApi 搜索。"""
    import httpx

    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries:
            try:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": api_key, "num": 5},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("organic_results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "source": "serpapi",
                        })
            except Exception as e:
                log.error(f"SerpApi 搜索失败 ({query}): {e}")

    return results


async def _synthesize_results(topic: str, search_results: list[dict], file_store: FileStore) -> str:
    """LLM 综合搜索结果。"""
    results_text = "\n\n".join(
        f"### {r['title']}\n来源: {r['url']}\n{r['snippet']}"
        for r in search_results
    )

    response = await call_llm(
        file_store,
        "你是知识综合专家。将搜索结果整合为结构化的研究摘要。用中文输出。",
        f"研究主题：{topic}\n\n搜索结果：\n\n{results_text}\n\n请综合以上结果，输出一份全面、结构化的研究摘要。包含关键发现、数据点、不同观点和结论。",
    )

    return response
