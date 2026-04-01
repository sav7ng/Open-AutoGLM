"""
Agent 业务编排层

功能：
1. 验证请求参数与 agent_type
2. 生成 task_id、创建任务记录
3. 提交线程池执行
4. 返回 accepted 响应
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.core.log_sanitize import format_summary_kv, sanitize_agent_request_summary
from app.core.executor import execute_agent_task_sync, is_supported_agent_type
from app.core.task_manager import create_task_record
from app.models.schemas import AgentRequest

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=10)


async def run_agent_async(request: AgentRequest) -> dict:
    """
    异步提交 Agent 任务。

    1. 验证 agent_type
    2. 生成 task_id 并创建任务记录
    3. 提交到线程池
    4. 立即返回 accepted 响应
    """
    if not is_supported_agent_type(request.agent_type):
        raise ValueError(f"不支持的 agent_type: {request.agent_type}")

    task_id = str(uuid.uuid4())

    create_task_record(
        task_id=task_id,
        instruction=request.instruction,
        agent_type=request.agent_type,
        max_steps=request.max_steps,
        callback_url=request.callback_url,
    )

    adb_config_dict = None
    if request.adb_config:
        adb_config_dict = {
            "type": request.adb_config.type,
            "params": request.adb_config.params,
        }

    req_summary = sanitize_agent_request_summary(request)
    logger.info(
        "[run-agent-async] 任务已就绪: task_id=%s, %s",
        task_id,
        format_summary_kv(req_summary),
    )

    logger.info("[run-agent-async] 线程池提交前: task_id=%s", task_id)
    _executor.submit(
        execute_agent_task_sync,
        task_id=task_id,
        instruction=request.instruction,
        max_steps=request.max_steps,
        api_key=request.api_key,
        base_url=request.base_url,
        model_name=request.model_name,
        callback_url=request.callback_url,
        agent_type=request.agent_type,
        lang=request.lang,
        adb_config=adb_config_dict,
        context_history=request.context_history,
    )
    logger.info("[run-agent-async] 线程池已提交: task_id=%s", task_id)

    return {
        "task_id": task_id,
        "status": "accepted",
        "agent_type": request.agent_type,
        "message": f"任务已提交，task_id: {task_id}",
        "callback_url": request.callback_url,
    }
