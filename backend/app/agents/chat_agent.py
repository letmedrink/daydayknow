"""对话 Agent — wiki 上下文检索 + 引导选项生成。"""

import json
import re
from typing import Optional

from ..config import settings
from ..storage import FileStore, WikiStore
from ..storage.wiki_store import extract_wikilinks
from ..llm import call_llm, stream_llm
from ..wiki.context_budget import compute_context_budget

import logging
log = logging.getLogger("chat_agent")

# 预设引导选项
PRESET_OPTIONS = [
    {"label": "展开讲讲", "action": "展开讲讲"},
    {"label": "换个角度解释", "action": "换个角度解释"},
    {"label": "给个例子", "action": "给个例子"},
]

SYSTEM_PROMPT_TEMPLATE = """你是一位知识学习助手，名叫"知微"。你的特点：

1. 基于用户的知识库（wiki）回答问题，引用相关知识
2. 回答结束后，输出一行引导选项让用户选择继续学习方向
3. 语言简洁、友好、有深度

{profile_section}

{wiki_section}

## 输出规则

1. 先回答用户的问题，可以引用知识库中的内容（用 [[页面名]] 格式）
2. 回答末尾输出一行引导选项：
   OPTIONS: 选项1 | 选项2 | 选项3
3. 选项应该是自然的下一步学习方向，3 个左右
4. 只输出 OPTIONS 行，不要有其他后缀"""


class ChatAgent:
    """对话 Agent，支持 wiki 上下文注入和引导选项。"""

    def __init__(self, file_store: FileStore, wiki_store: WikiStore):
        self.file_store = file_store
        self.wiki_store = wiki_store

    async def chat(
        self,
        message: str,
        conversation_id: str,
        history: list[dict],
    ) -> dict:
        """处理对话请求，返回 {response, options, references, conversation_id}。"""
        wiki_context, references = self._retrieve_wiki_context(message)
        profile = self.file_store.get_profile()
        profile_section = self._build_profile_section(profile)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profile_section=profile_section,
            wiki_section=wiki_context,
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        response = await self._call_llm(messages)
        options, clean_response = self._parse_options(response)

        return {
            "response": clean_response,
            "options": options if options else PRESET_OPTIONS,
            "references": references,
            "conversation_id": conversation_id,
        }

    async def chat_stream(self, message: str, conversation_id: str, history: list[dict]):
        """流式对话，yield SSE 事件字典。"""
        wiki_context, references = self._retrieve_wiki_context(message)
        profile = self.file_store.get_profile()
        profile_section = self._build_profile_section(profile)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profile_section=profile_section,
            wiki_section=wiki_context,
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        full_response = ""
        async for chunk in self._stream_chunks(messages):
            full_response += chunk
            yield {"type": "chunk", "content": chunk}

        options, clean_response = self._parse_options(full_response)

        if references:
            yield {"type": "references", "references": references}
        yield {"type": "options", "options": options if options else PRESET_OPTIONS}

        self.file_store.add_message(conversation_id, "user", message)
        self.file_store.add_message(
            conversation_id, "assistant", clean_response,
            references=references,
            options=options if options else PRESET_OPTIONS,
        )

    def _retrieve_wiki_context(self, query: str) -> tuple[str, list[dict]]:
        """检索相关 wiki 页面，返回 (context_text, references)。"""
        budget = compute_context_budget()
        search_results = self.wiki_store.search(query, max_results=5)

        if not search_results:
            return "(知识库中暂无相关内容)", []

        visited = set()
        pages = []
        total = 0

        for r in search_results:
            if total >= budget.page_budget:
                break
            path = r["path"]
            if path in visited:
                continue
            visited.add(path)

            data = self.wiki_store.read_page(path)
            if not data:
                continue

            body = data["body"]
            if len(body) > budget.max_page_size:
                body = body[:budget.max_page_size] + "\n\n...(已截断)"

            pages.append({"title": r["title"], "path": path, "body": body})
            total += len(body)

            # 1 跳邻居
            for link in extract_wikilinks(body)[:3]:
                for np in self.wiki_store.list_pages():
                    if np["name"].lower() == link.lower() and np["path"] not in visited:
                        if total >= budget.page_budget:
                            break
                        visited.add(np["path"])
                        nd = self.wiki_store.read_page(np["path"])
                        if nd:
                            nb = nd["body"]
                            half = budget.max_page_size // 2
                            if len(nb) > half:
                                nb = nb[:half] + "\n\n...(已截断)"
                            pages.append({"title": np["title"], "path": np["path"], "body": nb})
                            total += len(nb)

        context_parts = ["## 相关知识库内容\n"]
        refs = []
        for p in pages:
            context_parts.append(f"### {p['title']}\n路径: {p['path']}\n{p['body']}\n")
            refs.append({"title": p["title"], "path": p["path"]})

        return "\n".join(context_parts), refs

    def _build_profile_section(self, profile: dict) -> str:
        if not profile or not any(profile.get(k) for k in ["learningStyle", "cognitivePattern", "knowledgeLevel"]):
            return ""
        parts = ["## 用户画像"]
        if profile.get("learningStyle"):
            parts.append(f"- 学习风格: {profile['learningStyle']}")
        if profile.get("cognitivePattern"):
            parts.append(f"- 认知模式: {profile['cognitivePattern']}")
        if profile.get("knowledgeLevel"):
            parts.append(f"- 知识水平: {profile['knowledgeLevel']}")
        if profile.get("interests"):
            parts.append(f"- 兴趣领域: {', '.join(profile['interests'])}")
        return "\n".join(parts)

    def _parse_options(self, response: str) -> tuple[list[dict], str]:
        """解析 OPTIONS 行，返回 (options, clean_response)。"""
        match = re.search(r"OPTIONS:\s*(.+)$", response, re.MULTILINE)
        if not match:
            return [], response.strip()

        options = []
        for opt in match.group(1).split("|"):
            label = opt.strip()
            if label:
                options.append({"label": label, "action": label})

        clean = response[:match.start()].strip()
        return options, clean

    async def _call_llm(self, messages: list[dict]) -> str:
        return await call_llm(
            self.file_store,
            messages[0]["content"] if messages else "",
            "\n".join(m["content"] for m in messages[1:]) if len(messages) > 1 else "",
        )

    async def _stream_chunks(self, messages: list[dict]):
        async for chunk in stream_llm(self.file_store, messages):
            yield chunk
