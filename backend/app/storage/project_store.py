"""项目管理 — 维护 project list，每个项目指向一个目录。"""
import json
import os
import shutil
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

_PROJECT_LOCKS_GUARD = threading.Lock()
_PROJECT_LOCKS: dict[str, threading.RLock] = {}


class ProjectStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir).resolve()
        self._index_path = self.data_dir / "projects.json"
        with _PROJECT_LOCKS_GUARD:
            self._lock = _PROJECT_LOCKS.setdefault(str(self.data_dir), threading.RLock())
        self._runtimes: dict[str, tuple[object, object]] = {}

    def _read_index(self) -> list[dict]:
        with self._lock:
            if self._index_path.exists():
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            return []

    def _write_index(self, index: list[dict]):
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".projects.", suffix=".tmp", dir=self.data_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(index, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self._index_path)
            except BaseException:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
                raise

    def list_projects(self) -> list[dict]:
        return [self._with_managed_flag(project) for project in self._read_index()]

    def create_project(self, name: str, path: Optional[str] = None) -> dict:
        """创建项目。path 为空时默认用 data/projects/{id}/。"""
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        custom_path = bool(path)
        if not path:
            path = str(self.data_dir / "projects" / project_id)
        project_dir = Path(path)
        project_dir.mkdir(parents=True, exist_ok=True)
        # 创建 wiki 子目录
        wiki_dir = project_dir / "wiki"
        for subdir in ["entities", "concepts", "sources", "comparisons",
                       "queries", "synthesis", "findings", "thesis",
                       "methodology", "media"]:
            (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        (project_dir / "conversations").mkdir(parents=True, exist_ok=True)
        metadata_path = project_dir / ".llmwiki-project.json"
        if not metadata_path.exists():
            metadata_path.write_text(json.dumps({"schemaVersion": 1}, indent=2), encoding="utf-8")

        with self._lock:
            index = self._read_index()
            project = {
                "id": project_id,
                "name": name,
                "path": str(project_dir.resolve()),
                "managed": not custom_path,
                "createdAt": datetime.now().isoformat(),
            }
            index.append(project)
            self._write_index(index)
            return project

    def delete_project(self, project_id: str) -> bool:
        """从列表中删除项目（不删除磁盘数据）。"""
        with self._lock:
            index = self._read_index()
            new_index = [p for p in index if p["id"] != project_id]
            if len(new_index) == len(index):
                return False
            self._write_index(new_index)
            self._runtimes.pop(project_id, None)
            return True

    def delete_project_data(self, project_id: str, confirmation: str) -> bool:
        """Permanently delete a managed project after exact name confirmation."""
        with self._lock:
            project = next((p for p in self._read_index() if p["id"] == project_id), None)
            if not project:
                return False
            if confirmation != project["name"]:
                raise ValueError("项目名称确认不匹配")
            project_dir = Path(project["path"]).resolve()
            managed_root = (self.data_dir / "projects").resolve()
            try:
                relative = project_dir.relative_to(managed_root)
            except ValueError as exc:
                raise PermissionError("自定义外部目录只能从列表移除") from exc
            if len(relative.parts) != 1 or relative.name != project_id:
                raise PermissionError("拒绝删除非标准托管项目目录")
            if project_dir.exists():
                shutil.rmtree(project_dir)
            return self.delete_project(project_id)

    def get_project_dir(self, project_id: str) -> Optional[Path]:
        """获取项目目录。"""
        index = self._read_index()
        for p in index:
            if p["id"] == project_id:
                return Path(p["path"])
        return None

    def _with_managed_flag(self, project: dict) -> dict:
        enriched = dict(project)
        project_dir = Path(project["path"]).resolve()
        expected = (self.data_dir / "projects" / project["id"]).resolve()
        enriched["managed"] = project_dir == expected
        return enriched

    def get_runtime(self, project_id: str):
        """Return long-lived project-scoped stores for locks and in-memory indexes."""
        with self._lock:
            project_dir = self.get_project_dir(project_id)
            if not project_dir:
                return None
            runtime = self._runtimes.get(project_id)
            if runtime is None:
                from .file_store import FileStore
                from .wiki_store import WikiStore
                runtime = (FileStore(project_dir), WikiStore(project_dir))
                self._runtimes[project_id] = runtime
            return runtime
