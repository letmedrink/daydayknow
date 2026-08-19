import pytest

from app.research import deep_research
from app.storage import FileStore, WikiStore


@pytest.mark.asyncio
async def test_research_refuses_to_generate_without_search_configuration(tmp_path):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    with pytest.raises(RuntimeError, match="未配置搜索"):
        await deep_research.run_deep_research(
            "topic", project_store, wiki_store, global_store, search_queries=["topic"],
        )
    assert wiki_store.list_pages() == []


@pytest.mark.asyncio
async def test_research_refuses_zero_results(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    global_store.update_settings(searchApiConfig={"provider": "tavily", "api_key": "key"})
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")

    async def no_results(*_args):
        return []

    monkeypatch.setattr(deep_research, "_web_search", no_results)
    with pytest.raises(RuntimeError, match="未获取到"):
        await deep_research.run_deep_research(
            "topic", project_store, wiki_store, global_store, search_queries=["topic"],
        )
    assert wiki_store.list_pages() == []


def test_research_deduplicates_tracking_urls_and_assigns_citations(monkeypatch):
    results = [
        {"title": "One", "url": "https://example.com/page?utm_source=x", "snippet": "a"},
        {"title": "Duplicate", "url": "https://example.com/page", "snippet": "b"},
        {"title": "Two", "url": "https://example.org/other", "snippet": "c"},
    ]
    unique = deep_research._deduplicate_results(results)
    assert len(unique) == 2
    assert unique[0]["url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_research_enrichment_keeps_snippet_when_fetch_fails(monkeypatch):
    async def no_content(_url):
        return ""
    monkeypatch.setattr(deep_research, "_fetch_source_text", no_content)
    enriched = await deep_research._enrich_search_results([
        {"title": "One", "url": "https://example.com/", "snippet": "fallback"},
    ])
    assert enriched[0]["citation_id"] == "S1"
    assert enriched[0]["content"] == ""
    assert enriched[0]["snippet"] == "fallback"
