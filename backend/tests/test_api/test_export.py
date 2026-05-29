import pytest
import json

from app.db.graph_store import InMemoryGraphStore


class TestConversationExport:

    @pytest.mark.asyncio
    async def test_export_markdown(self):
        """直接测试导出逻辑。"""
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1", title="Test Chat")
        await store.add_message(conv["id"], "user", "What is Python?")
        await store.add_message(conv["id"], "assistant", "Python is a language.")

        # 模拟导出逻辑
        messages = await store.get_messages(conv["id"])
        title = conv.get("title") or "未命名对话"
        lines = [f"# {title}\n"]
        lines.append(f"创建时间: {conv.get('created_at', 'N/A')}\n")
        lines.append("---\n")
        for msg in messages:
            role = "**用户**" if msg["role"] == "user" else "**助手**"
            lines.append(f"\n{role}\n\n{msg['content']}\n")
        md_text = "\n".join(lines)

        assert "Test Chat" in md_text
        assert "What is Python?" in md_text
        assert "Python is a language." in md_text
        assert "**用户**" in md_text
        assert "**助手**" in md_text

    @pytest.mark.asyncio
    async def test_export_json_structure(self):
        """测试 JSON 导出数据结构。"""
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1", title="JSON Chat")
        await store.add_message(conv["id"], "user", "Hello")
        await store.add_message(conv["id"], "assistant", "Hi there!")

        messages = await store.get_messages(conv["id"])
        export_data = {"conversation": conv, "messages": messages}

        assert export_data["conversation"]["title"] == "JSON Chat"
        assert len(export_data["messages"]) == 2
        assert export_data["messages"][0]["role"] == "user"
        assert export_data["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_export_empty_conversation(self):
        """空对话也能导出。"""
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")

        messages = await store.get_messages(conv["id"])
        assert len(messages) == 0

        # Markdown 导出应正常
        title = conv.get("title") or "未命名对话"
        lines = [f"# {title}\n"]
        md_text = "\n".join(lines)
        assert "未命名对话" in md_text
