"""
内存任务状态管理

功能：
1. 维护所有异步任务的状态表（内存）
2. 支持任务创建、状态更新、查询、取消
3. 所有操作通过 threading.Lock 保护线程安全
"""

import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_tasks: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def create_task_record(
    task_id: str,
    instruction: str,
    agent_type: str,
    max_steps: int,
    callback_url: Optional[str] = None,
) -> dict[str, Any]:
    """创建任务记录并设置初始状态为 accepted。"""
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "task_id": task_id,
        "status": TaskStatus.ACCEPTED,
        "instruction": instruction,
        "agent_type": agent_type,
        "max_steps": max_steps,
        "callback_url": callback_url,
        "created_at": now,
        "updated_at": now,
        "result": None,
        "error": None,
        "cancel_requested": False,
    }
    with _lock:
        _tasks[task_id] = record
    return record


def update_task_status(
    task_id: str,
    status: TaskStatus,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """更新任务状态。"""
    with _lock:
        if task_id not in _tasks:
            return
        _tasks[task_id]["status"] = status
        _tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        if result is not None:
            _tasks[task_id]["result"] = result
        if error is not None:
            _tasks[task_id]["error"] = error


def get_task_status(task_id: str) -> Optional[dict[str, Any]]:
    """查询指定任务的完整状态记录，不存在则返回 None。"""
    with _lock:
        task = _tasks.get(task_id)
        return dict(task) if task else None


def should_cancel_task(task_id: str) -> bool:
    """检查任务是否被请求取消。"""
    with _lock:
        task = _tasks.get(task_id)
        return task["cancel_requested"] if task else False


def cancel_task(task_id: str) -> bool:
    """
    设置任务取消标志。

    Returns:
        True 如果成功设置标志，False 如果任务不存在或已终结。
    """
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return False
        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        if task["status"] in terminal:
            return False
        task["cancel_requested"] = True
        return True


def list_tasks() -> list[dict[str, Any]]:
    """列出所有任务（副本）。"""
    with _lock:
        return [dict(t) for t in _tasks.values()]
