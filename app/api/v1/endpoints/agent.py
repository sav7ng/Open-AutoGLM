"""
Agent HTTP 端点

提供 Agent 任务提交接口，接口契约与 AgentDroid 保持一致。
"""

import logging

from fastapi import APIRouter, HTTPException

from app.core.log_sanitize import format_summary_kv, sanitize_agent_request_summary
from app.models.schemas import AgentRequest
from app.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run-agent-async")
async def run_agent_async_endpoint(request: AgentRequest):
    """
    Run the agent asynchronously with the given instruction.
    Returns immediately with task_id.
    Task executes in an independent thread, completely isolated from the event loop.
    If callback_url is provided, results will be POST to that URL when complete.

    - **instruction**: The user's instruction for the agent.
    - **max_steps**: The maximum number of steps the agent can take.
    - **api_key**: The API key for the OpenAI model.
    - **base_url**: The base URL for the OpenAI API.
    - **model_name**: The name of the model to use.
    - **callback_url**: Optional URL to POST results when task completes.
    - **agent_type**: The type of agent to use.
    - **lang**: Agent 输出语言，仅支持 "cn" 或 "en"，默认 "cn"。
    - **adb_config**: ADB connection configuration (optional).
    - **context_history**: Optional conversation history for multi-turn context.
    """
    req_summary = sanitize_agent_request_summary(request)
    logger.info("[run-agent-async] 收到请求: %s", format_summary_kv(req_summary))

    try:
        result = await agent_service.run_agent_async(request)
        logger.info(
            "[run-agent-async] 即将返回: task_id=%r, status=%r, agent_type=%r",
            result.get("task_id"),
            result.get("status"),
            result.get("agent_type"),
        )
        return result

    except ValueError as e:
        logger.error(
            "[run-agent-async] 参数错误: %s, request_summary=%s",
            e,
            format_summary_kv(req_summary),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "[run-agent-async] 提交异常: request_summary=%s",
            format_summary_kv(req_summary),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
