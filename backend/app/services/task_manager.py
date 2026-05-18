import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskInfo:
    def __init__(self, task_id: str, task_type: str, user_id: str):
        self.task_id = task_id
        self.task_type = task_type
        self.user_id = user_id
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total = 0
        self.current_step = ""
        self.result = None
        self.error = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
    
    @property
    def percent(self) -> int:
        return round(self.progress / self.total * 100) if self.total > 0 else 0
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "percent": round(self.progress / self.total * 100) if self.total > 0 else 0
        }

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
    
    def create_task(self, task_type: str, user_id: str) -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(task_id, task_type, user_id)
        self._tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)
    
    def get_user_tasks(self, user_id: str, task_type: str = None) -> list:
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return tasks
    
    def update_progress(self, task_id: str, progress: int, total: int, current_step: str):
        task = self._tasks.get(task_id)
        if task:
            task.progress = progress
            task.total = total
            task.current_step = current_step
            task.status = TaskStatus.RUNNING
    
    def complete_task(self, task_id: str, result: Any = None):
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.progress = task.total
            task.result = result
            task.completed_at = datetime.now().isoformat()
    
    def fail_task(self, task_id: str, error: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now().isoformat()
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理超过指定时间的任务"""
        now = datetime.now()
        to_delete = []
        for task_id, task in self._tasks.items():
            created = datetime.fromisoformat(task.created_at)
            if (now - created).total_seconds() > max_age_hours * 3600:
                to_delete.append(task_id)
        for task_id in to_delete:
            del self._tasks[task_id]

# 全局任务管理器
task_manager = TaskManager()