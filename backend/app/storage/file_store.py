"""JSON 文件存储层 — 对话、用户画像、设置、审阅项、摄入缓存。"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional


class FileStore:
    """基于 JSON 文件的轻量存储，所有数据存在 data/ 目录下。"""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        # FileStore 只管理自己的 JSON 文件，wiki 的 .md 目录由 WikiStore 按需创建
        for sub in [
            "conversations",    # 对话索引 + 消息 (conversations/index.json, conversations/{id}/messages.json)
            "profile",          # 用户画像 (profile/profile.json)
        ]:
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)

    # ─── 通用 JSON 读写 ───────────────────────────────────────

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        path = self.data_dir / relative_path
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def write_json(self, relative_path: str, data: Any):
        path = self.data_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─── 对话管理 ──────────────────────────────────────────────

    def list_conversations(self) -> list[dict]:
        """返回所有对话元信息列表，按更新时间倒序。"""
        index = self.read_json("conversations/index.json", [])
        index.sort(key=lambda c: c.get("updatedAt", 0), reverse=True)
        return index

    def create_conversation(self, title: str = "新对话") -> dict:
        conv_id = f"conv_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        conv = {
            "id": conv_id,
            "title": title,
            "createdAt": int(time.time() * 1000),
            "updatedAt": int(time.time() * 1000),
        }
        index = self.read_json("conversations/index.json", [])
        index.append(conv)
        self.write_json("conversations/index.json", index)
        self.write_json(f"conversations/{conv_id}/messages.json", [])
        return conv

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        index = self.read_json("conversations/index.json", [])
        for c in index:
            if c["id"] == conv_id:
                return c
        return None

    def update_conversation(self, conv_id: str, **fields) -> Optional[dict]:
        index = self.read_json("conversations/index.json", [])
        for c in index:
            if c["id"] == conv_id:
                c.update(fields)
                c["updatedAt"] = int(time.time() * 1000)
                self.write_json("conversations/index.json", index)
                return c
        return None

    def delete_conversation(self, conv_id: str) -> bool:
        index = self.read_json("conversations/index.json", [])
        new_index = [c for c in index if c["id"] != conv_id]
        if len(new_index) == len(index):
            return False
        self.write_json("conversations/index.json", new_index)
        # 删除消息文件
        msg_path = self.data_dir / f"conversations/{conv_id}/messages.json"
        if msg_path.exists():
            msg_path.unlink()
        # 尝试删除目录
        dir_path = self.data_dir / f"conversations/{conv_id}"
        if dir_path.exists():
            try:
                dir_path.rmdir()
            except OSError:
                pass
        return True

    def get_messages(self, conv_id: str) -> list[dict]:
        return self.read_json(f"conversations/{conv_id}/messages.json", [])

    def add_message(self, conv_id: str, role: str, content: str, **extra) -> dict:
        messages = self.get_messages(conv_id)
        msg = {
            "id": f"msg_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
            "role": role,
            "content": content,
            "timestamp": int(time.time() * 1000),
            **extra,
        }
        messages.append(msg)
        self.write_json(f"conversations/{conv_id}/messages.json", messages)
        # 更新对话的 updatedAt
        self.update_conversation(conv_id)
        return msg

    # ─── 用户画像 ──────────────────────────────────────────────

    def get_profile(self) -> dict:
        return self.read_json("profile/profile.json", {
            "learningStyle": "",
            "cognitivePattern": "",
            "knowledgeLevel": "",
            "interests": [],
            "updatedAt": 0,
        })

    def update_profile(self, **fields) -> dict:
        profile = self.get_profile()
        profile.update(fields)
        profile["updatedAt"] = int(time.time() * 1000)
        self.write_json("profile/profile.json", profile)
        return profile

    # ─── 设置 ──────────────────────────────────────────────────

    def get_settings(self) -> dict:
        return self.read_json("settings.json", {
            "llmProviders": {},
            "activeProviderId": "",
            "searchApiConfig": {},
            "outputLanguage": "zh-CN",
            "multimodalModel": "",
        })

    def update_settings(self, **fields) -> dict:
        settings = self.get_settings()
        settings.update(fields)
        self.write_json("settings.json", settings)
        return settings

    # ─── 审阅项 ────────────────────────────────────────────────

    def get_reviews(self) -> list[dict]:
        return self.read_json("reviews.json", [])

    def add_reviews(self, items: list[dict]) -> list[dict]:
        """添加审阅项，按 type+title 去重，合并 affectedPages。"""
        existing = self.get_reviews()
        existing_map = {(r["type"], r["title"].strip().lower()): r for r in existing}

        for item in items:
            key = (item["type"], item["title"].strip().lower())
            if key in existing_map:
                old = existing_map[key]
                # 合并 affectedPages
                old_pages = set(old.get("affectedPages", []))
                new_pages = set(item.get("affectedPages", []))
                old["affectedPages"] = list(old_pages | new_pages)
                old["searchQueries"] = list(set(
                    old.get("searchQueries", []) + item.get("searchQueries", [])
                ))
            else:
                if "id" not in item:
                    item["id"] = f"review_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
                if "resolved" not in item:
                    item["resolved"] = False
                if "createdAt" not in item:
                    item["createdAt"] = int(time.time() * 1000)
                existing_map[key] = item

        result = list(existing_map.values())
        self.write_json("reviews.json", result)
        return result

    def resolve_review(self, review_id: str, action: str) -> bool:
        reviews = self.get_reviews()
        for r in reviews:
            if r["id"] == review_id:
                r["resolved"] = True
                r["resolvedAction"] = action
                r["resolvedAt"] = int(time.time() * 1000)
                self.write_json("reviews.json", reviews)
                return True
        return False

    # ─── 摄入缓存 ──────────────────────────────────────────────

    def check_ingest_cache(self, source_filename: str, source_content: str) -> Optional[list[str]]:
        """检查源文件是否已摄入且未变化。返回已写入文件列表或 None。"""
        cache = self.read_json("ingest-cache.json", {"entries": {}})
        entry = cache["entries"].get(source_filename)
        if not entry:
            return None

        current_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()
        if entry["hash"] != current_hash:
            return None

        # 验证所有写入的文件仍在磁盘上
        for file_path in entry.get("filesWritten", []):
            full_path = self.data_dir / file_path
            if not full_path.exists():
                return None

        return entry.get("filesWritten", [])

    def save_ingest_cache(self, source_filename: str, source_content: str, files_written: list[str]):
        cache = self.read_json("ingest-cache.json", {"entries": {}})
        cache["entries"][source_filename] = {
            "hash": hashlib.sha256(source_content.encode("utf-8")).hexdigest(),
            "timestamp": int(time.time() * 1000),
            "filesWritten": files_written,
        }
        self.write_json("ingest-cache.json", cache)

    def remove_ingest_cache(self, source_filename: str):
        cache = self.read_json("ingest-cache.json", {"entries": {}})
        cache["entries"].pop(source_filename, None)
        self.write_json("ingest-cache.json", cache)

    # ─── 图片描述缓存 ──────────────────────────────────────────

    def get_image_caption(self, image_hash: str) -> Optional[str]:
        cache = self.read_json("image-caption-cache.json", {})
        return cache.get(image_hash)

    def save_image_caption(self, image_hash: str, caption: str):
        cache = self.read_json("image-caption-cache.json", {})
        cache[image_hash] = caption
        self.write_json("image-caption-cache.json", cache)
