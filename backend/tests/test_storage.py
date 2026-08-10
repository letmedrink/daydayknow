from app.storage import FileStore, WikiStore
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
