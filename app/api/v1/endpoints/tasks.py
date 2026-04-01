"""
任务查询与管理端点
"""

import logging

from fastapi import APIRouter, HTTPException

from app.core.task_manager import cancel_task, get_task_status, list_tasks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/task-status/{task_id}")
async def get_task_status_endpoint(task_id: str):
    """查询指定任务的状态与结果。"""
    task = get_task_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return task


@router.get("/active-tasks")
async def list_active_tasks_endpoint():
    """列出所有任务。"""
    return list_tasks()


@router.delete("/task/{task_id}")
async def cancel_task_endpoint(task_id: str):
    """取消指定任务。"""
    success = cancel_task(task_id)
    if not success:
        task = get_task_status(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        raise HTTPException(
            status_code=400,
            detail=f"任务已终结，当前状态: {task.get('status')}",
        )
    return {"task_id": task_id, "message": "取消请求已发送"}
