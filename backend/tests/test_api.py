from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.agents import chat_agent
from app.ingest import pipeline
from app.api import research as research_api
from app.wiki import change_pipeline
from app.storage import SourceStore
import io
import json
import zipfile


def test_global_and_project_routes(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            created = client.post("/api/projects", json={"name": "alpha"})
            assert created.status_code == 200
            project_id = created.json()["data"]["id"]

            assert client.get("/api/settings").status_code == 200
            assert client.get("/api/profile").status_code == 200
            pages = client.get(f"/api/projects/{project_id}/wiki/pages")
            assert pages.status_code == 200
            assert pages.json()["data"] == {"tree": [], "pages": []}
    finally:
        settings.DATA_DIR = original_data_dir


def test_missing_project_uses_error_envelope(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            response = client.get("/api/projects/missing/wiki/pages")
            assert response.status_code == 404
            assert response.json()["success"] is False
            assert response.json()["code"] == "http_error"
    finally:
        settings.DATA_DIR = original_data_dir


def test_wiki_page_edit_history_rename_and_restore_api(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            project_id = client.post("/api/projects", json={"name": "wiki-edit"}).json()["data"]["id"]
            base = f"/api/projects/{project_id}/wiki/page"
            first = "---\ntitle: First\ntype: concept\n---\n\nfirst body\n"
            second = "---\ntitle: First\ntype: concept\n---\n\nsecond body\n"
            assert client.put(base, json={"path": "concepts/first.md", "content": first}).status_code == 200
            assert client.put(base, json={"path": "concepts/first.md", "content": second}).status_code == 200
            versions = client.get(f"{base}/history", params={"path": "concepts/first.md"}).json()["data"]
            assert len(versions) == 1
            renamed = client.post(f"{base}/rename", json={
                "old_path": "concepts/first.md", "new_path": "concepts/renamed.md", "update_links": True,
            })
            assert renamed.status_code == 200
            restored = client.post(f"{base}/history/restore", json={
                "path": "concepts/first.md", "version_id": versions[0]["id"],
            })
            assert restored.status_code == 200
            assert restored.json()["data"]["body"].strip() == "first body"
            assert client.put(base, json={"path": "../bad.md", "content": "bad"}).status_code == 400
    finally:
        settings.DATA_DIR = original_data_dir


def test_settings_keys_are_redacted_and_blank_update_preserves_them(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            provider = {
                "id": "one", "name": "One", "provider": "openai", "api_key": "secret",
                "base_url": "https://example.test/v1", "model": "model",
            }
            client.patch("/api/settings", json={
                "llmProviders": {"one": provider},
                "searchApiConfig": {"provider": "tavily", "api_key": "search-secret"},
                "ingestDetailedProgress": True,
            })
            visible = client.get("/api/settings").json()["data"]
            assert visible["llmProviders"]["one"]["api_key"] == ""
            assert visible["llmProviders"]["one"]["has_api_key"] is True
            assert visible["searchApiConfig"]["api_key"] == ""
            assert visible["ingestDetailedProgress"] is True

            provider["api_key"] = ""
            client.patch("/api/settings", json={"llmProviders": {"one": provider}})
            assert app.state.global_store.get_settings()["llmProviders"]["one"]["api_key"] == "secret"

            provider["clear_api_key"] = True
            client.patch("/api/settings", json={"llmProviders": {"one": provider}})
            assert app.state.global_store.get_settings()["llmProviders"]["one"]["api_key"] == ""
    finally:
        settings.DATA_DIR = original_data_dir


def test_project_remove_and_permanent_delete_semantics(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "managed"}).json()["data"]
            assert client.request("DELETE", f"/api/projects/{project['id']}/data", json={"confirmation": "wrong"}).status_code == 400
            assert client.request("DELETE", f"/api/projects/{project['id']}/data", json={"confirmation": "managed"}).status_code == 200

            external_path = tmp_path / "external"
            external = client.post("/api/projects", json={"name": "external", "path": str(external_path)}).json()["data"]
            assert client.request("DELETE", f"/api/projects/{external['id']}/data", json={"confirmation": "external"}).status_code == 403
            assert client.delete(f"/api/projects/{external['id']}").status_code == 200
            assert external_path.exists()
    finally:
        settings.DATA_DIR = original_data_dir


def test_project_export_and_import_round_trip(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "portable"}).json()["data"]
            page = f"/api/projects/{project['id']}/wiki/page"
            client.put(page, json={"path": "concepts/portable.md", "content": "portable content"})
            exported = client.get(f"/api/projects/{project['id']}/export")
            assert exported.status_code == 200
            imported = client.post("/api/projects/import", files={"archive": ("project.zip", exported.content, "application/zip")})
            assert imported.status_code == 200
            imported_id = imported.json()["data"]["id"]
            restored = client.get(f"/api/projects/{imported_id}/wiki/page", params={"path": "concepts/portable.md"})
            assert restored.json()["data"]["body"] == "portable content"

            malicious = io.BytesIO()
            with zipfile.ZipFile(malicious, "w") as package:
                package.writestr("llmwiki-project.json", json.dumps({"schemaVersion": 1, "name": "bad"}))
                package.writestr("project/../../escape.txt", "bad")
            rejected = client.post("/api/projects/import", files={"archive": ("bad.zip", malicious.getvalue(), "application/zip")})
            assert rejected.status_code == 400
    finally:
        settings.DATA_DIR = original_data_dir


def test_chat_done_is_sent_after_turn_is_persisted(tmp_path, monkeypatch):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)

    async def fake_stream(*_args, **_kwargs):
        yield {"type": "content", "content": "answer"}

    monkeypatch.setattr(chat_agent, "stream_llm", fake_stream)
    try:
        with TestClient(app) as client:
            project_id = client.post("/api/projects", json={"name": "alpha"}).json()["data"]["id"]
            response = client.post(f"/api/projects/{project_id}/chat", json={"message": "question"})
            assert response.status_code == 200
            assert '"type": "done"' in response.text
            conversations = client.get(f"/api/projects/{project_id}/conversations").json()["data"]
            detail = client.get(f"/api/projects/{project_id}/conversations/{conversations[0]['id']}").json()["data"]
            assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
            assert client.post(
                f"/api/projects/{project_id}/chat",
                json={"message": "question", "conversation_id": "missing"},
            ).status_code == 404
    finally:
        settings.DATA_DIR = original_data_dir


def test_ingest_requires_acceptance_and_can_be_rejected(tmp_path, monkeypatch):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    responses = iter([
        "analysis",
        '---FILE: wiki/concepts/preview.md---\n---\ntitle: Preview\ntype: concept\n---\nbody\n---END FILE---',
        "analysis",
        '---FILE: wiki/concepts/accepted.md---\n---\ntitle: Accepted\ntype: concept\n---\nbody\n---END FILE---',
    ])

    async def fake_call(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(pipeline, "call_llm", fake_call)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "approval"}).json()["data"]
            base = f"/api/projects/{project['id']}/ingest"
            client.patch("/api/settings", json={"ingestDetailedProgress": True})
            first = client.post(base, files={"file": ("one.txt", b"source", "text/plain")})
            assert '"type": "detail"' in first.text
            event = [line for line in first.text.splitlines() if line.startswith("data:")][-1]
            job = __import__("json").loads(event[5:])["job"]
            assert job["status"] == "awaiting_review"
            assert any(item["title"] == "生成完整 Wiki 提案" for item in job["trace"])
            assert not (tmp_path / "projects" / project["id"] / "wiki/concepts/preview.md").exists()
            assert client.post(f"{base}/jobs/{job['id']}/reject").status_code == 200
            assert not (tmp_path / "projects" / project["id"] / "wiki/concepts/preview.md").exists()

            second = client.post(base, files={"file": ("two.txt", b"source two", "text/plain")})
            event = [line for line in second.text.splitlines() if line.startswith("data:")][-1]
            job = __import__("json").loads(event[5:])["job"]
            accepted = client.post(f"{base}/jobs/{job['id']}/accept")
            assert accepted.status_code == 200
            assert (tmp_path / "projects" / project["id"] / "wiki/concepts/accepted.md").exists()
    finally:
        settings.DATA_DIR = original_data_dir


def test_ingest_accepts_edited_subset(tmp_path, monkeypatch):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    responses = iter([
        "analysis",
        "---FILE: wiki/concepts/one.md---\none\n---END FILE---\n---FILE: wiki/concepts/two.md---\ntwo\n---END FILE---",
    ])

    async def fake_call(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(pipeline, "call_llm", fake_call)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "selective"}).json()["data"]
            base = f"/api/projects/{project['id']}/ingest"
            response = client.post(base, files={"file": ("source.txt", b"source", "text/plain")})
            event = [line for line in response.text.splitlines() if line.startswith("data:")][-1]
            job = __import__("json").loads(event[5:])["job"]
            accepted = client.post(f"{base}/jobs/{job['id']}/accept", json={
                "proposals": [{"path": "concepts/two.md", "content": "edited two", "merge": False}],
            })
            assert accepted.status_code == 200
            assert not (tmp_path / "projects" / project["id"] / "wiki/concepts/one.md").exists()
            assert (tmp_path / "projects" / project["id"] / "wiki/concepts/two.md").read_text() == "edited two"
    finally:
        settings.DATA_DIR = original_data_dir


def test_review_only_skip_can_resolve_directly(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "reviews"}).json()["data"]
            store = app.state.project_store.get_runtime(project["id"])[0]
            review = store.add_reviews([{"type": "suggestion", "title": "todo", "affectedPages": [], "searchQueries": [], "options": []}])[0]
            endpoint = f"/api/projects/{project['id']}/reviews/{review['id']}/resolve"
            assert client.post(endpoint, json={"action": "create_page"}).status_code == 400
            assert store.get_review(review["id"])["resolved"] is False
            assert client.post(endpoint, json={"action": "skip"}).status_code == 200
            assert store.get_review(review["id"])["resolved"] is True
            assert client.post(f"/api/projects/{project['id']}/reviews/missing/resolve", json={"action": "skip"}).status_code == 404
    finally:
        settings.DATA_DIR = original_data_dir


def test_research_is_staged_until_acceptance_and_can_link_review(tmp_path, monkeypatch):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)

    async def fake_research(topic, file_store, wiki_store, global_store, **_kwargs):
        return {
            "topic": topic, "search_queries": ["query"],
            "search_results": [{"title": "source", "url": "https://example.test", "snippet": "evidence", "source": "test"}],
            "synthesis": "summary", "reviews": [], "warnings": [], "files_written": [],
            "status": "awaiting_review",
            "proposals": [{"path": "concepts/researched.md", "content": "---\ntitle: Researched\ntype: concept\n---\nbody", "merge": True}],
        }

    monkeypatch.setattr(research_api, "run_deep_research", fake_research)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "research"}).json()["data"]
            store = app.state.project_store.get_runtime(project["id"])[0]
            review = store.add_reviews([{"type": "suggestion", "title": "research me", "affectedPages": [], "searchQueries": ["query"], "options": []}])[0]
            base = f"/api/projects/{project['id']}/research"
            response = client.post(base, json={"topic": "topic", "review_id": review["id"]})
            event = [line for line in response.text.splitlines() if line.startswith("data:")][-1]
            job = __import__("json").loads(event[5:])["job"]
            page = tmp_path / "projects" / project["id"] / "wiki/concepts/researched.md"
            assert job["status"] == "awaiting_review"
            assert not page.exists()
            assert store.get_review(review["id"])["resolved"] is False
            assert client.post(f"{base}/jobs/{job['id']}/accept").status_code == 200
            assert page.exists()
            assert store.get_review(review["id"])["resolved"] is True
    finally:
        settings.DATA_DIR = original_data_dir


def test_schema_sources_and_query_backfill_are_project_scoped(tmp_path, monkeypatch):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)

    async def fake_change_llm(*_args, **_kwargs):
        return '---FILE: wiki/synthesis/回答综合.md---\n---\ntitle: 回答综合\ntype: synthesis\nsources: []\n---\nanswer synthesis\n---END FILE---'

    monkeypatch.setattr(change_pipeline, "call_llm", fake_change_llm)
    try:
        with TestClient(app) as client:
            project = client.post("/api/projects", json={"name": "method"}).json()["data"]
            project_id = project["id"]
            schema_url = f"/api/projects/{project_id}/schema"
            schema = client.get(schema_url).json()["data"]
            schema["config"]["language"] = "en"
            assert client.patch(schema_url, json=schema).status_code == 200

            source = SourceStore(project["path"]).put("evidence.txt", b"evidence", "evidence", 1)
            assert client.get(f"/api/projects/{project_id}/sources").json()["data"][0]["id"] == source["id"]
            assert client.get(f"/api/projects/{project_id}/sources/{source['id']}/extraction").text == "evidence"

            wiki = app.state.project_store.get_runtime(project_id)[1]
            wiki.write_page("concepts/evidence.md", {"title": "Evidence", "type": "concept", "sources": [source["id"]]}, "evidence")
            file_store = app.state.project_store.get_runtime(project_id)[0]
            saved = file_store.save_turn(
                file_store.new_conversation_id(), "question",
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "answer", "references": [{"title": "Evidence", "path": "concepts/evidence.md"}]},
            )
            conv_id = saved["conversation"]["id"]
            message_id = saved["messages"][-1]["id"]
            created = client.post(f"/api/projects/{project_id}/changes/query", json={"conversation_id": conv_id, "message_id": message_id})
            assert created.status_code == 200
            job = created.json()["data"]
            assert job["status"] == "awaiting_review"
            assert not (tmp_path / "projects" / project_id / "wiki/synthesis/回答综合.md").exists()
            assert client.post(f"/api/projects/{project_id}/changes/jobs/{job['id']}/accept").status_code == 200
            assert (tmp_path / "projects" / project_id / "wiki/synthesis/回答综合.md").exists()
    finally:
        settings.DATA_DIR = original_data_dir
