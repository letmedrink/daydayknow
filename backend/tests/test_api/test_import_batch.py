import pytest
import json
import io

from app.api.import_ import _import_json, _import_csv
from app.db.graph_store import InMemoryGraphStore


class TestImportJson:
    """JSON 导入测试。"""

    @pytest.mark.asyncio
    async def test_import_extraction_format(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        data = {
            "nodes": [
                {"name": "注意力机制", "domain": "NLP"},
                {"name": "Transformer", "domain": "NLP"},
            ],
            "edges": [
                {"from": "注意力机制", "to": "Transformer", "relation_type": "part_of"},
            ],
        }
        result = await _import_json("user1", data, "test.json")
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    @pytest.mark.asyncio
    async def test_import_node_list(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        data = [
            {"name": "Python", "domain": "Language"},
            {"name": "JavaScript", "domain": "Language"},
        ]
        result = await _import_json("user1", data, "test.json")
        assert len(result["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_import_single_node(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        data = {"name": "量子力学", "domain": "Physics"}
        result = await _import_json("user1", data, "test.json")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "量子力学"


class TestImportCsv:
    """CSV 导入测试。"""

    @pytest.mark.asyncio
    async def test_import_basic_csv(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        csv_text = "name,domain,description\n注意力机制,NLP,序列建模核心\nTransformer,NLP,基于注意力"
        result = await _import_csv("user1", csv_text, "test.csv")
        assert len(result["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_import_csv_skip_empty_name(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        csv_text = "name,domain\n,NLP\nPython,Language"
        result = await _import_csv("user1", csv_text, "test.csv")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "Python"

    @pytest.mark.asyncio
    async def test_import_csv_name_only(self):
        store = InMemoryGraphStore()
        import app.api.import_ as imp
        imp.graph_store = store

        csv_text = "name\nPython\nGo\nRust"
        result = await _import_csv("user1", csv_text, "test.csv")
        assert len(result["nodes"]) == 3
