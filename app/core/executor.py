"""
任务执行与回调处理模块

功能：
1. 在独立线程中执行 Agent 任务
2. 管理 ADB 连接生命周期（建立/清理）
3. 实现回调重试机制和错误处理
"""

import logging
import random
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from app.core.adb_ssh_tunnel import setup_ssh_tunnel_and_adb
from app.core.log_sanitize import (
    format_summary_kv,
    mask_adb_address_for_log,
    sanitize_execute_thread_fields,
)
from app.core.task_manager import (
    TaskStatus,
    add_thinking_log,
    should_cancel_task,
    update_task_status,
)
from phone_agent.agent import AgentConfig, PhoneAgent
from phone_agent.adb.connection import ADBConnection
from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from phone_agent.model import ModelConfig

logger = logging.getLogger(__name__)

_device_factory_lock = threading.Lock()

SUPPORTED_AGENT_TYPES = {"phone-agent"}
_THINKING_PATTERNS = [
    re.compile(r"<think>(.*?)</think>", re.DOTALL),
    re.compile(r"<redacted_thinking>(.*?)</redacted_thinking>", re.DOTALL),
]


def is_supported_agent_type(agent_type: str) -> bool:
    return agent_type in SUPPORTED_AGENT_TYPES


def execute_agent_task_sync(
    task_id: str,
    instruction: str,
    max_steps: int,
    api_key: str,
    base_url: str,
    model_name: str,
    callback_url: Optional[str] = None,
    agent_type: str = "phone-agent",
    lang: str = "cn",
    adb_config: Optional[Dict[str, Any]] = None,
    context_history: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    在独立线程中执行 agent 任务（完全隔离，不阻塞事件循环）。

    完整流程：ADB 连接 → PhoneAgent 构造 → run_as_dict → 状态更新 → 回调 → 清理
    """
    adb_address: Optional[str] = None
    tunnel_cleanup: Optional[Callable[[], None]] = None

    try:
        if should_cancel_task(task_id):
            logger.info("任务在执行前被取消: %s", task_id)
            _handle_cancel(task_id, instruction, agent_type, callback_url)
            return

        update_task_status(task_id, TaskStatus.RUNNING)
        add_thinking_log(task_id, step=0, thinking="任务开始执行", log_type="thinking")

        ctx = sanitize_execute_thread_fields(
            instruction=instruction,
            max_steps=max_steps,
            model_name=model_name,
            agent_type=agent_type,
            lang=lang,
            base_url=base_url,
            adb_config=adb_config,
            context_history=context_history,
        )
        logger.info("[execute] 开始: task_id=%s, %s", task_id, format_summary_kv(ctx))

        # ADB 连接管理
        adb_address, tunnel_cleanup = _setup_adb_connection(task_id, adb_config)
        device_id = (
            adb_address
            if adb_address is not None
            else _extract_device_id(adb_config)
        )

        adb_masked = (
            mask_adb_address_for_log(adb_address) if adb_address else "local/skipped"
        )
        logger.info("[execute] ADB 就绪: task_id=%s, adb=%s", task_id, adb_masked)

        # 初始化 DeviceFactory（线程安全）
        with _device_factory_lock:
            set_device_type(DeviceType.ADB)

        model_config = ModelConfig(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            lang=lang,
        )
        agent_config = AgentConfig(
            max_steps=max_steps,
            device_id=device_id,
            lang=lang,
            verbose=False,
            interactive_human=False,
        )

        agent = PhoneAgent(model_config, agent_config)
        logger.info("[execute] PhoneAgent 已创建: task_id=%s", task_id)

        if context_history:
            agent.set_context(context_history)

        logger.info("[execute] run_as_dict 调用前: task_id=%s", task_id)
        result = agent.run_as_dict(instruction)
        logger.info("[execute] run_as_dict 返回: task_id=%s", task_id)
        _append_thinking_logs_from_history(task_id, result.get("history", []))

        if should_cancel_task(task_id):
            logger.info("任务在执行后被取消: %s", task_id)
            _handle_cancel(task_id, instruction, agent_type, callback_url)
            return

        result["task_id"] = task_id
        result["instruction"] = instruction
        result["agent_type"] = agent_type

        add_thinking_log(
            task_id,
            step=max(1, int(result.get("steps_taken", 0))),
            thinking=result.get("message", "任务执行完成"),
            log_type="task_completed",
        )
        update_task_status(task_id, TaskStatus.COMPLETED, result=result)

        logger.info(
            "任务执行完成: %s, status=%s, steps=%d",
            task_id,
            result.get("status"),
            result.get("steps_taken", 0),
        )

        if callback_url:
            send_callback_sync(callback_url, result)

    except Exception as e:
        logger.error("任务执行失败: %s, error=%s", task_id, e, exc_info=True)
        add_thinking_log(
            task_id,
            step=0,
            thinking=f"任务执行失败: {e}",
            log_type="task_failed",
        )
        error_result = {
            "task_id": task_id,
            "instruction": instruction,
            "agent_type": agent_type,
            "status": "error",
            "message": str(e),
            "history": [],
            "steps_taken": 0,
        }
        update_task_status(task_id, TaskStatus.FAILED, error=str(e), result=error_result)
        if callback_url:
            send_callback_sync(callback_url, error_result)

    finally:
        _cleanup_adb_connection(adb_address, tunnel_cleanup)


def _setup_adb_connection(
    task_id: str, adb_config: Optional[Dict[str, Any]]
) -> Tuple[Optional[str], Optional[Callable[[], None]]]:
    """根据 adb_config 建立 ADB 连接。返回 (adb 地址供 disconnect, SSH 隧道 cleanup 或 None)。"""
    if not adb_config:
        return None, None

    conn_type = adb_config.get("type", "local")
    params = adb_config.get("params") or {}

    if conn_type == "direct":
        address = params.get("address")
        if address:
            addr_str = str(address)
            masked = mask_adb_address_for_log(addr_str)
            logger.info(
                "建立远程 ADB 连接: task_id=%s, address_masked=%s", task_id, masked
            )
            conn = ADBConnection()
            ok, msg = conn.connect(addr_str)
            if not ok:
                raise RuntimeError(f"ADB 连接失败: {msg}")
            return addr_str, None
        return None, None

    if conn_type == "ssh_tunnel":
        address, cleanup = setup_ssh_tunnel_and_adb(task_id, params)
        return address, cleanup

    return None, None


def _extract_device_id(adb_config: Optional[Dict[str, Any]]) -> Optional[str]:
    """从 adb_config 中提取 device_id。direct 模式下使用 address 作为 device_id。"""
    if not adb_config:
        return None
    conn_type = adb_config.get("type", "local")
    if conn_type == "direct":
        return adb_config.get("params", {}).get("address")
    return None


def _cleanup_adb_connection(
    adb_address: Optional[str],
    tunnel_cleanup: Optional[Callable[[], None]] = None,
) -> None:
    """清理 ADB 连接；若有 SSH 隧道，在 disconnect 之后关闭隧道。"""
    if adb_address:
        try:
            logger.info(
                "断开远程 ADB 连接: address_masked=%s",
                mask_adb_address_for_log(adb_address),
            )
            ADBConnection().disconnect(adb_address)
        except Exception as e:
            logger.warning(
                "ADB 断开失败: address_masked=%s, error=%s",
                mask_adb_address_for_log(adb_address),
                e,
            )
    if tunnel_cleanup:
        try:
            tunnel_cleanup()
        except Exception as e:
            logger.warning("SSH 隧道关闭失败: error=%s", e)


def _handle_cancel(
    task_id: str,
    instruction: str,
    agent_type: str,
    callback_url: Optional[str],
) -> None:
    """处理任务取消。"""
    cancel_result = {
        "task_id": task_id,
        "instruction": instruction,
        "agent_type": agent_type,
        "status": "cancelled",
        "message": f"任务 {task_id} 已取消",
        "history": [],
        "steps_taken": 0,
    }
    add_thinking_log(
        task_id,
        step=0,
        thinking=f"任务 {task_id} 已取消",
        log_type="task_cancelled",
    )
    update_task_status(task_id, TaskStatus.CANCELLED, result=cancel_result)
    if callback_url:
        send_callback_sync(callback_url, cancel_result)


def _append_thinking_logs_from_history(task_id: str, history: list[dict]) -> None:
    """从 history 的 assistant 消息中提取 think 内容并写入日志。"""
    step = 1
    for message in history:
        if message.get("role") != "assistant":
            continue
        content = message.get("content", "")
        if not isinstance(content, str):
            continue
        extracted = None
        for pattern in _THINKING_PATTERNS:
            match = pattern.search(content)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    break
        if extracted:
            add_thinking_log(task_id, step=step, thinking=extracted, log_type="thinking")
            step += 1


# ==============================
# 回调发送
# ==============================


def send_callback_sync(callback_url: str, result: dict) -> None:
    """
    同步发送回调（在线程中执行），使用重试机制和指数退避。
    """
    task_id = result.get("task_id", "unknown")

    max_attempts = 5
    base_delay = 1.0
    max_delay = 30.0

    logger.info("开始发送回调: task_id=%s, url=%s", task_id, callback_url)

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                callback_url,
                json=result,
                timeout=30,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Phone-Agent-API/1.0",
                },
            )

            if 200 <= response.status_code < 300:
                logger.info("回调成功: task_id=%s, attempt=%d", task_id, attempt)
                return

            logger.warning(
                "回调非成功状态码: task_id=%s, attempt=%d, status=%d",
                task_id,
                attempt,
                response.status_code,
            )

        except requests.exceptions.Timeout:
            logger.error("回调超时: task_id=%s, attempt=%d", task_id, attempt)
        except requests.exceptions.ConnectionError:
            logger.error("回调连接失败: task_id=%s, attempt=%d", task_id, attempt)
        except Exception as e:
            logger.error(
                "回调意外错误: task_id=%s, attempt=%d, error=%s",
                task_id,
                attempt,
                e,
                exc_info=True,
            )

        if attempt < max_attempts:
            backoff = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0, 0.5)
            delay = backoff + jitter
            logger.info("回调重试: next_attempt=%d, delay=%.2fs", attempt + 1, delay)
            time.sleep(delay)
        else:
            logger.error("所有回调尝试均失败: task_id=%s", task_id)
