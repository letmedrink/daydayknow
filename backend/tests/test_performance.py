"""Scale-oriented regression tests for the in-memory Wiki index."""

from app.storage import WikiStore


def test_ten_thousand_page_index_and_graph_cache(tmp_path):
    wiki_dir = tmp_path / "wiki" / "concepts"
    wiki_dir.mkdir(parents=True)
    for index in range(10_000):
        marker = "needle-topic" if index == 9_999 else "ordinary-topic"
        title = "Needle Page" if index == 9_999 else f"Page {index}"
        (wiki_dir / f"page-{index}.md").write_text(
            f"---\ntitle: {title}\ntype: concept\n---\n\n{marker}\n",
            encoding="utf-8",
        )

    store = WikiStore(tmp_path)
    results = store.search("needle")
    assert results[0]["path"] == "concepts/page-9999.md"
    first = store.build_graph()
    assert len(first["nodes"]) == 10_000
    assert store.build_graph() is first
