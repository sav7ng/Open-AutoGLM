"""
任务查询扩展服务（含 task-thinking SSE 流）。
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.core.task_manager import get_task_status

logger = logging.getLogger(__name__)

_TERMINAL_LOG_TYPES = {"task_completed", "task_failed", "task_cancelled"}


def _sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def get_task_thinking_stream(task_id: str) -> AsyncGenerator[str, None]:
    """
    流式返回任务思考内容（SSE）。

    事件类型：
    - start
    - thinking
    - complete
    - error
    """
    try:
        task_info = get_task_status(task_id)
        if task_info is None:
            yield _sse_data(
                {
                    "event_type": "error",
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": {
                        "type": "not_found",
                        "message": f"任务不存在: {task_id}",
                        "status_code": 404,
                    },
                }
            )
            return

        yield _sse_data(
            {
                "event_type": "start",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"task_status": task_info.get("status")},
            }
        )

        max_wait_seconds = 300
        started_at = time.time()
        last_sent_index = 0
        has_terminal_log = False

        while time.time() - started_at < max_wait_seconds:
            task_info = get_task_status(task_id)
            if task_info is None:
                break

            current_logs = task_info.get("thinking_logs", [])
            for log in current_logs[last_sent_index:]:
                log_type = log.get("log_type", "thinking")
                yield _sse_data(
                    {
                        "event_type": "thinking",
                        "task_id": task_id,
                        "step": log.get("step"),
                        "timestamp": log.get("timestamp"),
                        "data": {
                            "log_type": log_type,
                            "thinking": log.get("thinking"),
                        },
                    }
                )
                last_sent_index += 1
                if log_type in _TERMINAL_LOG_TYPES:
                    has_terminal_log = True
                    break

            if has_terminal_log:
                break

            await asyncio.sleep(0.5)

        if has_terminal_log:
            yield _sse_data(
                {
                    "event_type": "complete",
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"total_steps": last_sent_index},
                }
            )
            return

        yield _sse_data(
            {
                "event_type": "error",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": {
                    "type": "timeout",
                    "message": f"等待任务完成超时（{max_wait_seconds}秒）",
                    "status_code": 408,
                },
            }
        )
    except Exception as exc:
        logger.error("流式返回任务思考内容时发生异常: task_id=%s", task_id, exc_info=True)
        yield _sse_data(
            {
                "event_type": "error",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": {
                    "type": "internal_error",
                    "message": str(exc),
                    "status_code": 500,
                },
            }
        )
