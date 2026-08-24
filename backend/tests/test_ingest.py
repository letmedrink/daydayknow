import pytest

from app.ingest import pipeline
from app.storage import FileStore, WikiStore


@pytest.mark.asyncio
async def test_ingest_writes_only_to_project_directory(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    responses = iter([
        "analysis",
        '---FILE: wiki/concepts/example.md---\n---\ntitle: Example\ntype: concept\n---\nbody\n---END FILE---'
    ])

    async def fake_call(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(pipeline, "call_llm", fake_call)
    result = await pipeline.run_ingest_pipeline(
        "example.txt", b"source", project_store, wiki_store, global_store,
    )

    assert result["files_written"] == ["wiki/concepts/example.md"]
    assert (tmp_path / "project/wiki/concepts/example.md").exists()
    assert not (tmp_path / "global/wiki/concepts/example.md").exists()


@pytest.mark.asyncio
async def test_ingest_cache_uses_raw_content_and_force_bypasses_it(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    calls = 0

    async def fake_call(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return "analysis" if calls % 2 else '---FILE: wiki/concepts/cached.md---\nbody\n---END FILE---'

    monkeypatch.setattr(pipeline, "call_llm", fake_call)
    first = await pipeline.run_ingest_pipeline("same.txt", b"source", project_store, wiki_store, global_store)
    second = await pipeline.run_ingest_pipeline("same.txt", b"source", project_store, wiki_store, global_store)
    forced = await pipeline.run_ingest_pipeline("same.txt", b"source", project_store, wiki_store, global_store, force=True)
    assert first["cached"] is False
    assert second["cached"] is True
    assert forced["cached"] is False
    assert calls == 4


@pytest.mark.asyncio
async def test_long_ingest_analyzes_tail_and_keeps_raw_source(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    calls = []
    details = []

    async def fake_call(_store, _system, user):
        calls.append(user)
        if user.startswith("分析结果"):
            return '---FILE: wiki/concepts/长文档.md---\n---\ntitle: 长文档\ntype: concept\nsources: []\n---\ntail kept\n---END FILE---'
        return "TAIL_SEEN" if "TAIL_MARKER" in user else "chunk"

    monkeypatch.setattr(pipeline, "call_llm", fake_call)
    content = ("a" * 85_000 + "TAIL_MARKER").encode()
    async def capture_detail(event):
        details.append(event)

    result = await pipeline.run_ingest_pipeline(
        "long.txt", content, project_store, wiki_store, global_store,
        auto_commit=False, detail_callback=capture_detail,
    )
    assert result["generation_info"]["analysis_chunks"] >= 3
    assert any("TAIL_MARKER" in call for call in calls)
    assert result["source_id"].startswith("src_")
    assert (tmp_path / "project/raw/sources" / result["source_id"] / "original.txt").exists()
    assert result["proposals"][0]["baseSha256"] is None
    assert any(event["title"] == "分析分块计划" and event["meta"][0]["value"] == "3" for event in details)
    assert any(event["title"] == "生成完整 Wiki 提案" for event in details)
    assert all("api_key" not in str(event).lower() for event in details)
