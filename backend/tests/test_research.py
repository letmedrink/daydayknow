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
