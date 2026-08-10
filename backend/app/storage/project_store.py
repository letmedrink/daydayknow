"""项目管理 — 维护 project list，每个项目指向一个目录。"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProjectStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._index_path = self.data_dir / "projects.json"

    def _read_index(self) -> list[dict]:
        if self._index_path.exists():
            import json
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return []

    def _write_index(self, index: list[dict]):
        import json
        self._index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_projects(self) -> list[dict]:
        return self._read_index()

    def create_project(self, name: str, path: Optional[str] = None) -> dict:
        """创建项目。path 为空时默认用 data/projects/{id}/。"""
        import json
        import shutil

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
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

        # 继承全局设置（LLM 配置等）
        global_settings = self.data_dir / "settings.json"
        if global_settings.exists():
            shutil.copy2(global_settings, project_dir / "settings.json")

        index = self._read_index()
        project = {
            "id": project_id,
            "name": name,
            "path": str(project_dir),
            "createdAt": datetime.now().isoformat(),
        }
        index.append(project)
        self._write_index(index)
        return project

    def delete_project(self, project_id: str) -> bool:
        """从列表中删除项目（不删除磁盘数据）。"""
        index = self._read_index()
        new_index = [p for p in index if p["id"] != project_id]
        if len(new_index) == len(index):
            return False
        self._write_index(new_index)
        return True

    def get_project_dir(self, project_id: str) -> Optional[Path]:
        """获取项目目录。"""
        index = self._read_index()
        for p in index:
            if p["id"] == project_id:
                return Path(p["path"])
        return None
