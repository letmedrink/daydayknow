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
