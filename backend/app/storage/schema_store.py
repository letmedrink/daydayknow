"""Project-scoped, versioned wiki schema configuration."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import threading
from pathlib import Path


DEFAULT_SCHEMA = {
    "version": 1,
    "revision": 1,
    "language": "zh-CN",
    "filenamePolicy": "chinese",
    "pageTypes": [
        {"id": "entity", "label": "实体", "directory": "entities", "enabled": True},
        {"id": "concept", "label": "概念", "directory": "concepts", "enabled": True},
        {"id": "source", "label": "来源", "directory": "sources", "enabled": True},
        {"id": "comparison", "label": "对比", "directory": "comparisons", "enabled": True},
        {"id": "synthesis", "label": "综合", "directory": "synthesis", "enabled": True},
        {"id": "finding", "label": "发现", "directory": "findings", "enabled": True},
        {"id": "thesis", "label": "论点", "directory": "thesis", "enabled": True},
        {"id": "methodology", "label": "方法论", "directory": "methodology", "enabled": True},
    ],
    "requiredFrontmatter": ["type", "title", "created", "updated", "tags", "related", "sources"],
    "specialPages": {"index": "index.md", "log": "log.md"},
    "reviewTypes": ["contradiction", "duplicate", "missing-page", "suggestion"],
    "lint": {"autoEveryAcceptedChanges": 0},
}

DEFAULT_SCHEMA_MARKDOWN = """# Wiki 维护规则

- 全部页面默认使用中文标题、中文正文和中文文件名。
- 每份来源创建摘要页，并把关键实体和概念整合进已有页面。
- 正文使用 `[[页面标题]]` 建立交叉引用。
- 新来源与已有知识冲突时保留双方证据，并创建 contradiction 审阅项。
- 可能重复的实体、缺失的重要页面和后续研究建议应创建审阅项。
- 所有可核验事实必须通过 `sources` 关联到稳定的原始来源。
"""

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_LOCKS_GUARD = threading.Lock()
_SCHEMA_LOCKS: dict[str, threading.RLock] = {}


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def validate_schema(schema: dict) -> dict:
    candidate = copy.deepcopy(schema)
    if candidate.get("version") != 1:
        raise ValueError("仅支持项目 Schema version 1")
    if not isinstance(candidate.get("language"), str) or not candidate["language"].strip():
        raise ValueError("Schema language 不能为空")
    page_types = candidate.get("pageTypes")
    if not isinstance(page_types, list) or not page_types:
        raise ValueError("Schema 至少需要一个页面类型")
    ids: set[str] = set()
    directories: set[str] = set()
    normalized = []
    for raw in page_types:
        if not isinstance(raw, dict):
            raise ValueError("pageTypes 必须是对象数组")
        page_type = str(raw.get("id") or "").strip()
        directory = str(raw.get("directory") or "").strip()
        label = str(raw.get("label") or page_type).strip()
        if not _IDENTIFIER_RE.fullmatch(page_type) or not _IDENTIFIER_RE.fullmatch(directory):
            raise ValueError("页面类型 ID 和目录只能使用小写字母、数字、下划线或连字符")
        if page_type in ids or directory in directories:
            raise ValueError("页面类型 ID 和目录必须唯一")
        ids.add(page_type)
        directories.add(directory)
        normalized.append({"id": page_type, "label": label, "directory": directory, "enabled": bool(raw.get("enabled", True))})
    candidate["pageTypes"] = normalized
    required = candidate.get("requiredFrontmatter", [])
    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        raise ValueError("requiredFrontmatter 必须是字符串数组")
    lint = candidate.setdefault("lint", {})
    interval = int(lint.get("autoEveryAcceptedChanges", 0))
    if interval < 0 or interval > 10_000:
        raise ValueError("自动 Lint 间隔必须在 0 到 10000 之间")
    lint["autoEveryAcceptedChanges"] = interval
    return candidate


class ProjectSchemaStore:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.json_path = self.project_dir / "schema.json"
        self.markdown_path = self.project_dir / "schema.md"
        with _LOCKS_GUARD:
            self._lock = _SCHEMA_LOCKS.setdefault(str(self.project_dir.resolve()), threading.RLock())

    def ensure(self) -> dict:
        with self._lock:
            if not self.json_path.exists():
                _atomic_write(self.json_path, json.dumps(DEFAULT_SCHEMA, ensure_ascii=False, indent=2).encode("utf-8"))
            if not self.markdown_path.exists():
                _atomic_write(self.markdown_path, DEFAULT_SCHEMA_MARKDOWN.encode("utf-8"))
            return self.get()

    def get(self) -> dict:
        with self._lock:
            if not self.json_path.exists() or not self.markdown_path.exists():
                return self.ensure()
            try:
                config = validate_schema(json.loads(self.json_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"项目 Schema 无效: {exc}") from exc
            return {"config": config, "instructions": self.markdown_path.read_text(encoding="utf-8")}

    def update(self, config: dict, instructions: str, used_types: dict[str, str] | None = None) -> dict:
        with self._lock:
            current = self.get()["config"]
            validated = validate_schema(config)
            old_by_id = {item["id"]: item for item in current["pageTypes"]}
            new_by_id = {item["id"]: item for item in validated["pageTypes"]}
            for page_type, directory in (used_types or {}).items():
                replacement = new_by_id.get(page_type)
                if replacement is None:
                    raise ValueError(f"页面类型 {page_type} 已被使用，不能删除")
                old = old_by_id.get(page_type)
                expected = old["directory"] if old else directory
                if replacement["directory"] != expected:
                    raise ValueError(f"页面类型 {page_type} 已被使用，不能修改目录")
            validated["version"] = int(current.get("version", 1))
            validated["revision"] = int(current.get("revision", 1)) + 1
            if len(instructions.encode("utf-8")) > 200_000:
                raise ValueError("schema.md 不能超过 200KB")
            old_json = self.json_path.read_bytes()
            old_markdown = self.markdown_path.read_bytes()
            try:
                _atomic_write(self.json_path, json.dumps(validated, ensure_ascii=False, indent=2).encode("utf-8"))
                _atomic_write(self.markdown_path, instructions.encode("utf-8"))
            except BaseException:
                _atomic_write(self.json_path, old_json)
                _atomic_write(self.markdown_path, old_markdown)
                raise
            return self.get()

    def prompt_text(self) -> str:
        schema = self.get()
        return "项目 Schema（必须遵守）：\n" + json.dumps(schema["config"], ensure_ascii=False) + "\n\n" + schema["instructions"]
