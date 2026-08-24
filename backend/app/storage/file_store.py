"""JSON 文件存储层 — 对话、用户画像、设置、审阅项、摄入缓存。"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


class FileStore:
    """基于 JSON 文件的轻量存储，所有数据存在 data/ 目录下。"""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()

    def _lock_for(self, relative_path: str) -> threading.RLock:
        key = str((self.data_dir / relative_path).resolve())
        with _LOCKS_GUARD:
            return _PATH_LOCKS.setdefault(key, threading.RLock())

    def _ensure_dirs(self):
        # FileStore 只管理自己的 JSON 文件，wiki 的 .md 目录由 WikiStore 按需创建
        for sub in [
            "conversations",    # 对话索引 + 消息 (conversations/index.json, conversations/{id}/messages.json)
            "profile",          # 用户画像 (profile/profile.json)
            "ingest-jobs",      # 持久化的摄入任务、源文件和暂存媒体
            "research-jobs",    # 持久化的 Deep Research 任务
            "change-jobs",      # 问答回写和 Wiki Lint 变更任务
        ]:
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)

    # ─── 通用 JSON 读写 ───────────────────────────────────────

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        with self._lock_for(relative_path):
            path = self.data_dir / relative_path
            if not path.exists():
                return default
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default

    def write_json(self, relative_path: str, data: Any):
        with self._lock_for(relative_path):
            path = self.data_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            except BaseException:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
                raise

    def mutate_json(self, relative_path: str, default: Any, mutator: Callable[[Any], Any]) -> Any:
        """Run a read-modify-write cycle while holding the path lock."""
        with self._lock_for(relative_path):
            data = self.read_json(relative_path, default)
            result = mutator(data)
            self.write_json(relative_path, data)
            return result

    # ─── 对话管理 ──────────────────────────────────────────────

    def list_conversations(self) -> list[dict]:
        """返回所有对话元信息列表，按更新时间倒序。"""
        index = self.read_json("conversations/index.json", [])
        index.sort(key=lambda c: c.get("updatedAt", 0), reverse=True)
        return index

    def create_conversation(self, title: str = "新对话") -> dict:
        return self.save_turn(self.new_conversation_id(), title, None, None)["conversation"]

    def new_conversation_id(self) -> str:
        return f"conv_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    def save_turn(
        self,
        conv_id: str,
        title: str,
        user_message: Optional[dict],
        assistant_message: Optional[dict],
    ) -> dict:
        """Atomically commit a conversation index entry and an optional full turn."""
        index_path = "conversations/index.json"
        messages_path = f"conversations/{conv_id}/messages.json"
        locks = sorted(
            [(index_path, self._lock_for(index_path)), (messages_path, self._lock_for(messages_path))],
            key=lambda item: item[0],
        )
        for _, lock in locks:
            lock.acquire()
        try:
            now = int(time.time() * 1000)
            original_index = self.read_json(index_path, [])
            index = [dict(item) for item in original_index]
            conv = next((item for item in index if item["id"] == conv_id), None)
            if conv is None:
                conv = {"id": conv_id, "title": title, "createdAt": now, "updatedAt": now}
                index.append(conv)
            else:
                conv["updatedAt"] = now
            original_messages = self.read_json(messages_path, [])
            messages = [dict(item) for item in original_messages]
            for raw in (user_message, assistant_message):
                if raw is not None:
                    messages.append({
                        "id": f"msg_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
                        "timestamp": int(time.time() * 1000),
                        **raw,
                    })
            # Write messages first: an index never points at a missing message file.
            try:
                self.write_json(messages_path, messages)
                self.write_json(index_path, index)
            except Exception:
                # Best-effort rollback for ordinary write failures. Atomic replace
                # keeps each individual file valid even if rollback also fails.
                try:
                    self.write_json(messages_path, original_messages)
                    self.write_json(index_path, original_index)
                except Exception:
                    pass
                raise
            return {"conversation": conv, "messages": messages}
        finally:
            for _, lock in reversed(locks):
                lock.release()

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        index = self.read_json("conversations/index.json", [])
        for c in index:
            if c["id"] == conv_id:
                return c
        return None

    def update_conversation(self, conv_id: str, **fields) -> Optional[dict]:
        def update(index):
            for conversation in index:
                if conversation["id"] == conv_id:
                    conversation.update(fields)
                    conversation["updatedAt"] = int(time.time() * 1000)
                    return dict(conversation)
            return None
        return self.mutate_json("conversations/index.json", [], update)

    def delete_conversation(self, conv_id: str) -> bool:
        removed = False
        def update(index):
            nonlocal removed
            new_index = [c for c in index if c["id"] != conv_id]
            removed = len(new_index) != len(index)
            index[:] = new_index
        self.mutate_json("conversations/index.json", [], update)
        if not removed:
            return False
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
        result = self.save_turn(
            conv_id,
            "新对话",
            {"role": role, "content": content, **extra},
            None,
        )
        return result["messages"][-1]

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
        def update(profile):
            profile.update(fields)
            profile["updatedAt"] = int(time.time() * 1000)
            return dict(profile)
        return self.mutate_json("profile/profile.json", self.get_profile(), update)

    # ─── 设置 ──────────────────────────────────────────────────

    def get_settings(self) -> dict:
        return self.read_json("settings.json", {
            "llmProviders": {},
            "activeProviderId": "",
            "searchApiConfig": {},
            "outputLanguage": "zh-CN",
            "multimodalModel": "",
            "ingestDetailedProgress": False,
            "retrievalConfig": {"mode": "lexical", "candidateLimit": 12, "rerankLimit": 5},
        })

    def update_settings(self, **fields) -> dict:
        def update(current):
            current.update(fields)
            return dict(current)
        return self.mutate_json("settings.json", self.get_settings(), update)

    # ─── 审阅项 ────────────────────────────────────────────────

    def get_reviews(self) -> list[dict]:
        return self.read_json("reviews.json", [])

    def add_reviews(self, items: list[dict]) -> list[dict]:
        """添加审阅项，按 type+title 去重，合并 affectedPages。"""
        result: list[dict] = []
        def update(existing):
            nonlocal result
            existing_map = {(r["type"], r["title"].strip().lower()): r for r in existing}
            for raw_item in items:
                item = dict(raw_item)
                key = (item["type"], item["title"].strip().lower())
                if key in existing_map:
                    old = existing_map[key]
                    old["affectedPages"] = list(set(old.get("affectedPages", [])) | set(item.get("affectedPages", [])))
                    old["searchQueries"] = list(set(old.get("searchQueries", []) + item.get("searchQueries", [])))
                else:
                    item.setdefault("id", f"review_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}")
                    item.setdefault("resolved", False)
                    item.setdefault("createdAt", int(time.time() * 1000))
                    existing_map[key] = item
            existing[:] = existing_map.values()
            result = list(existing)
            return result
        self.mutate_json("reviews.json", [], update)
        return result

    def resolve_review(self, review_id: str, action: str) -> bool:
        def update(reviews):
            for review in reviews:
                if review["id"] == review_id:
                    review["resolved"] = True
                    review["resolvedAction"] = action
                    review["resolvedAt"] = int(time.time() * 1000)
                    return True
            return False
        return self.mutate_json("reviews.json", [], update)

    def get_review(self, review_id: str) -> Optional[dict]:
        return next((item for item in self.get_reviews() if item.get("id") == review_id), None)

    def update_review(self, review_id: str, **fields) -> Optional[dict]:
        def update(reviews):
            for review in reviews:
                if review.get("id") == review_id:
                    review.update(fields)
                    return dict(review)
            return None
        return self.mutate_json("reviews.json", [], update)

    # ─── 摄入缓存 ──────────────────────────────────────────────

    def check_ingest_cache(self, source_filename: str, source_content: str, pipeline_version: int = 1) -> Optional[list[str]]:
        """检查源文件是否已摄入且未变化。返回已写入文件列表或 None。"""
        cache = self.read_json("ingest-cache.json", {"entries": {}})
        entry = cache["entries"].get(source_filename)
        if not entry:
            return None

        if entry.get("pipelineVersion", 1) != pipeline_version:
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

    def save_ingest_cache(self, source_filename: str, source_content: str, files_written: list[str], pipeline_version: int = 1):
        self.save_ingest_cache_hash(
            source_filename,
            hashlib.sha256(source_content.encode("utf-8")).hexdigest(),
            files_written,
            pipeline_version,
        )

    def save_ingest_cache_hash(self, source_filename: str, source_hash: str, files_written: list[str], pipeline_version: int = 1):
        def update(cache):
            cache.setdefault("entries", {})[source_filename] = {
                "hash": source_hash,
                "timestamp": int(time.time() * 1000),
                "filesWritten": files_written,
                "pipelineVersion": pipeline_version,
            }
        self.mutate_json("ingest-cache.json", {"entries": {}}, update)

    def remove_ingest_cache(self, source_filename: str):
        self.mutate_json(
            "ingest-cache.json", {"entries": {}},
            lambda cache: cache.setdefault("entries", {}).pop(source_filename, None),
        )

    # ─── 图片描述缓存 ──────────────────────────────────────────

    def get_image_caption(self, image_hash: str) -> Optional[str]:
        cache = self.read_json("image-caption-cache.json", {})
        return cache.get(image_hash)

    def save_image_caption(self, image_hash: str, caption: str):
        self.mutate_json("image-caption-cache.json", {}, lambda cache: cache.__setitem__(image_hash, caption))

    # ─── 摄入任务 ────────────────────────────────

    def create_ingest_job(self, filename: str, content: bytes, force: bool = False) -> dict:
        job_id = f"ingest_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        job_dir = self.data_dir / "ingest-jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        source_path = job_dir / "source.bin"
        fd, temp_name = tempfile.mkstemp(prefix=".source.", suffix=".tmp", dir=job_dir)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, source_path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
        now = int(time.time() * 1000)
        job = {
            "id": job_id, "filename": filename, "status": "pending", "force": force,
            "createdAt": now, "updatedAt": now, "progress": 0, "step": "queued",
        }
        self.write_json(f"ingest-jobs/{job_id}/job.json", job)
        return job

    def get_ingest_job(self, job_id: str) -> Optional[dict]:
        if not re_safe_id(job_id, "ingest_"):
            return None
        return self.read_json(f"ingest-jobs/{job_id}/job.json")

    def update_ingest_job(self, job_id: str, **fields) -> Optional[dict]:
        if not re_safe_id(job_id, "ingest_"):
            return None
        path = f"ingest-jobs/{job_id}/job.json"
        if not (self.data_dir / path).exists():
            return None
        def update(job):
            job.update(fields)
            job["updatedAt"] = int(time.time() * 1000)
            return dict(job)
        return self.mutate_json(path, {}, update)

    def append_ingest_trace(self, job_id: str, event: dict) -> Optional[dict]:
        """Persist a bounded, redacted execution trace on an ingest job."""
        if not re_safe_id(job_id, "ingest_"):
            return None
        path = f"ingest-jobs/{job_id}/job.json"
        if not (self.data_dir / path).exists():
            return None
        def update(job):
            trace = list(job.get("trace") or [])
            trace.append(event)
            job["trace"] = trace[-300:]
            job["updatedAt"] = int(time.time() * 1000)
            return dict(job)
        return self.mutate_json(path, {}, update)

    def list_ingest_jobs(self) -> list[dict]:
        jobs = []
        root = self.data_dir / "ingest-jobs"
        for path in root.glob("ingest_*/job.json"):
            job = self.read_json(str(path.relative_to(self.data_dir)))
            if job:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.get("createdAt", 0), reverse=True)

    def recover_ingest_jobs(self) -> list[dict]:
        """Mark jobs interrupted by a process restart as resumable."""
        recovered = []
        for job in self.list_ingest_jobs():
            if job.get("status") in {"pending", "running"}:
                updated = self.update_ingest_job(
                    job["id"], status="interrupted", step="interrupted",
                    message="服务重启导致任务中断，可重试",
                )
                if updated:
                    recovered.append(updated)
        return recovered

    def ingest_job_source(self, job_id: str) -> bytes:
        job = self.get_ingest_job(job_id)
        if not job:
            raise FileNotFoundError("摄入任务不存在")
        return (self.data_dir / "ingest-jobs" / job_id / "source.bin").read_bytes()

    def delete_ingest_job(self, job_id: str) -> bool:
        job = self.get_ingest_job(job_id)
        if not job:
            return False
        if job.get("status") in {"pending", "running"}:
            raise ValueError("运行中的任务不能删除")
        shutil.rmtree(self.data_dir / "ingest-jobs" / job_id)
        return True

    # ─── Deep Research 任务 ───────────────────────────

    def create_research_job(self, topic: str, keywords: list[str], review_id: Optional[str] = None) -> dict:
        job_id = f"research_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        now = int(time.time() * 1000)
        job = {
            "id": job_id, "topic": topic, "keywords": keywords, "reviewId": review_id,
            "status": "pending", "step": "queued", "progress": 0,
            "createdAt": now, "updatedAt": now,
        }
        self.write_json(f"research-jobs/{job_id}/job.json", job)
        return job

    def get_research_job(self, job_id: str) -> Optional[dict]:
        if not re_safe_id(job_id, "research_"):
            return None
        return self.read_json(f"research-jobs/{job_id}/job.json")

    def update_research_job(self, job_id: str, **fields) -> Optional[dict]:
        if not re_safe_id(job_id, "research_"):
            return None
        path = f"research-jobs/{job_id}/job.json"
        if not (self.data_dir / path).exists():
            return None
        def update(job):
            job.update(fields)
            job["updatedAt"] = int(time.time() * 1000)
            return dict(job)
        return self.mutate_json(path, {}, update)

    def list_research_jobs(self) -> list[dict]:
        jobs = []
        for path in (self.data_dir / "research-jobs").glob("research_*/job.json"):
            job = self.read_json(str(path.relative_to(self.data_dir)))
            if job:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.get("createdAt", 0), reverse=True)

    def recover_research_jobs(self) -> list[dict]:
        recovered = []
        for job in self.list_research_jobs():
            if job.get("status") in {"pending", "running"}:
                updated = self.update_research_job(
                    job["id"], status="interrupted", step="interrupted",
                    message="服务重启导致研究中断，可重试",
                )
                if updated:
                    recovered.append(updated)
        return recovered

    def delete_research_job(self, job_id: str) -> bool:
        job = self.get_research_job(job_id)
        if not job:
            return False
        if job.get("status") in {"pending", "running"}:
            raise ValueError("运行中的任务不能删除")
        shutil.rmtree(self.data_dir / "research-jobs" / job_id)
        return True

    # ─── 统一 Wiki 变更任务 ───────────────────────────

    def create_change_job(self, kind: str, title: str, origin: Optional[dict] = None) -> dict:
        if kind not in {"query", "lint"}:
            raise ValueError("不支持的变更任务类型")
        job_id = f"change_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        now = int(time.time() * 1000)
        job = {
            "id": job_id, "kind": kind, "title": title, "origin": origin or {},
            "status": "pending", "step": "queued", "progress": 0,
            "createdAt": now, "updatedAt": now,
        }
        self.write_json(f"change-jobs/{job_id}/job.json", job)
        return job

    def get_change_job(self, job_id: str) -> Optional[dict]:
        if not re_safe_id(job_id, "change_"):
            return None
        return self.read_json(f"change-jobs/{job_id}/job.json")

    def update_change_job(self, job_id: str, **fields) -> Optional[dict]:
        if not re_safe_id(job_id, "change_"):
            return None
        path = f"change-jobs/{job_id}/job.json"
        if not (self.data_dir / path).exists():
            return None
        def update(job):
            job.update(fields)
            job["updatedAt"] = int(time.time() * 1000)
            return dict(job)
        return self.mutate_json(path, {}, update)

    def list_change_jobs(self) -> list[dict]:
        jobs = []
        for path in (self.data_dir / "change-jobs").glob("change_*/job.json"):
            job = self.read_json(str(path.relative_to(self.data_dir)))
            if job:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.get("createdAt", 0), reverse=True)

    def recover_change_jobs(self) -> list[dict]:
        recovered = []
        for job in self.list_change_jobs():
            if job.get("status") in {"pending", "running"}:
                updated = self.update_change_job(
                    job["id"], status="interrupted", step="interrupted",
                    message="服务重启导致任务中断，可重试",
                )
                if updated:
                    recovered.append(updated)
        return recovered

    def delete_change_job(self, job_id: str) -> bool:
        job = self.get_change_job(job_id)
        if not job:
            return False
        if job.get("status") in {"pending", "running"}:
            raise ValueError("运行中的任务不能删除")
        shutil.rmtree(self.data_dir / "change-jobs" / job_id)
        return True

    def record_accepted_change(self) -> int:
        """Increment and return the number of accepted changes since the last auto lint."""
        def update(state):
            state["acceptedSinceLint"] = int(state.get("acceptedSinceLint", 0)) + 1
            return state["acceptedSinceLint"]
        return self.mutate_json("maintenance-state.json", {"acceptedSinceLint": 0}, update)

    def reset_accepted_change_count(self) -> None:
        self.write_json("maintenance-state.json", {"acceptedSinceLint": 0})


def re_safe_id(value: str, prefix: str) -> bool:
    return value.startswith(prefix) and value.replace("_", "").isalnum()
