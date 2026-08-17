from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from app.storage import FileStore, WikiStore
from app.storage import file_store as file_store_module
from app.storage.project_store import ProjectStore


def test_global_and_project_stores_are_isolated(tmp_path):
    global_store = FileStore(tmp_path)
    project_store = ProjectStore(tmp_path)
    project = project_store.create_project("alpha")
    project_files = FileStore(project["path"])

    global_store.update_settings(activeProviderId="global-provider")
    global_store.update_profile(learningStyle="visual")
    project_files.add_reviews([{"type": "suggestion", "title": "project-only"}])

    assert global_store.get_settings()["activeProviderId"] == "global-provider"
    assert global_store.get_profile()["learningStyle"] == "visual"
    assert project_files.get_settings()["activeProviderId"] == ""
    assert global_store.get_reviews() == []
    assert project_files.get_reviews()[0]["title"] == "project-only"


def test_wiki_store_writes_and_backs_up_pages(tmp_path):
    store = WikiStore(tmp_path)
    store.write_page("concepts/example.md", {"title": "Example", "type": "concept"}, "first")
    store.write_page("concepts/example.md", {"tags": ["updated"]}, "second", merge=True)

    page = store.read_page("concepts/example.md")
    assert page["frontmatter"]["title"] == "Example"
    assert page["body"].strip() == "second"
    assert list((tmp_path / "page-history").glob("*.md"))


def test_wiki_store_rejects_paths_outside_wiki(tmp_path):
    store = WikiStore(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    assert store.read_page("../outside.md") is None
    assert store.delete_page("../outside.md") is False


def test_concurrent_review_updates_are_not_lost(tmp_path):
    store = FileStore(tmp_path)
    def add(index):
        store.add_reviews([{"type": "suggestion", "title": f"review-{index}"}])
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(40)))
    assert len(store.get_reviews()) == 40


def test_atomic_json_write_preserves_old_file_on_replace_failure(tmp_path, monkeypatch):
    store = FileStore(tmp_path)
    store.write_json("settings.json", {"value": "old"})

    def fail_replace(*_args):
        raise OSError("replace failed")

    monkeypatch.setattr(file_store_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        store.write_json("settings.json", {"value": "new"})
    assert json.loads((tmp_path / "settings.json").read_text())["value"] == "old"
    assert not list(tmp_path.glob(".settings.json.*.tmp"))


def test_failed_turn_commit_rolls_back_new_conversation(tmp_path, monkeypatch):
    store = FileStore(tmp_path)
    conversation_id = store.new_conversation_id()
    original_write = store.write_json
    failed = False

    def fail_index_once(relative_path, data):
        nonlocal failed
        if relative_path == "conversations/index.json" and not failed:
            failed = True
            raise OSError("index write failed")
        return original_write(relative_path, data)

    monkeypatch.setattr(store, "write_json", fail_index_once)
    with pytest.raises(OSError, match="index write failed"):
        store.save_turn(
            conversation_id,
            "title",
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        )
    assert store.get_conversation(conversation_id) is None
    assert store.get_messages(conversation_id) == []


def test_ingest_cache_is_invalidated_by_pipeline_version(tmp_path):
    store = FileStore(tmp_path)
    page = tmp_path / "wiki/concepts/page.md"
    page.parent.mkdir(parents=True)
    page.write_text("page", encoding="utf-8")
    store.save_ingest_cache("source.md", "source", ["wiki/concepts/page.md"], pipeline_version=1)
    assert store.check_ingest_cache("source.md", "source", pipeline_version=1)
    assert store.check_ingest_cache("source.md", "source", pipeline_version=2) is None


def test_wiki_cache_detects_external_changes_and_reuses_graph(tmp_path):
    store = WikiStore(tmp_path)
    store.write_page("concepts/one.md", {"title": "One", "type": "concept"}, "alpha")
    assert store.search("one")
    first_graph = store.build_graph()
    assert store.build_graph() is first_graph

    page_path = tmp_path / "wiki/concepts/one.md"
    page_path.write_text("---\ntitle: Two\ntype: concept\n---\n\nbeta changed\n", encoding="utf-8")
    assert store.search("two")
    assert store.build_graph() is not first_graph


def test_project_store_only_permanently_deletes_managed_projects(tmp_path):
    project_store = ProjectStore(tmp_path / "data")
    managed = project_store.create_project("managed")
    assert project_store.delete_project_data(managed["id"], "managed") is True
    assert not (tmp_path / "data/projects" / managed["id"]).exists()

    external_dir = tmp_path / "external"
    external = project_store.create_project("external", str(external_dir))
    with pytest.raises(PermissionError):
        project_store.delete_project_data(external["id"], "external")
    assert external_dir.exists()


def test_markdown_batch_commit_rolls_back_all_pages(tmp_path, monkeypatch):
    store = WikiStore(tmp_path)
    store.write_raw_page("concepts/existing.md", "old")
    original = store._atomic_write_text
    calls = 0

    def fail_second(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return original(path, content)

    monkeypatch.setattr(store, "_atomic_write_text", fail_second)
    with pytest.raises(OSError, match="disk full"):
        store.commit_pages([
            {"path": "concepts/existing.md", "content": "changed", "merge": False},
            {"path": "concepts/new.md", "content": "new", "merge": False},
        ])
    assert (tmp_path / "wiki/concepts/existing.md").read_text() == "old"
    assert not (tmp_path / "wiki/concepts/new.md").exists()


def test_ingest_jobs_survive_restart_and_become_resumable(tmp_path):
    store = FileStore(tmp_path)
    job = store.create_ingest_job("source.txt", b"content")
    store.update_ingest_job(job["id"], status="running")
    restarted = FileStore(tmp_path)
    recovered = restarted.recover_ingest_jobs()
    assert recovered[0]["status"] == "interrupted"
    assert restarted.ingest_job_source(job["id"]) == b"content"


def test_hybrid_search_recovers_fuzzy_title_match(tmp_path):
    store = WikiStore(tmp_path)
    store.write_page("concepts/retrieval.md", {"title": "Retrieval Architecture", "type": "concept"}, "index")
    results = store.hybrid_search("Retrievel Architecture")
    assert results[0]["path"] == "concepts/retrieval.md"
