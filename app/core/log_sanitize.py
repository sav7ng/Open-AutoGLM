"""
请求与执行上下文的日志脱敏摘要。

禁止在日志中出现明文 api_key 与完整 instruction；可选 PHONE_AGENT_DEBUG_LOG_BODIES 增加非敏感调试字段。
"""

from __future__ import annotations

import hashlib
import os
import urllib.parse
from typing import Any, Dict, List, Optional

from app.models.schemas import AgentRequest

_DEBUG_ENV = "PHONE_AGENT_DEBUG_LOG_BODIES"


def debug_log_bodies_enabled() -> bool:
    v = os.environ.get(_DEBUG_ENV, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def mask_adb_address_for_log(address: Optional[str]) -> str:
    """将典型 host:port 脱敏为 ***.***.***.last:port 或 ***:port。"""
    if not address:
        return "-"
    s = str(address).strip()
    host, sep, port = s.rpartition(":")
    if sep and port.isdigit() and host:
        segs = host.split(".")
        if len(segs) == 4 and all(p.isdigit() for p in segs):
            return f"***.***.***.{segs[3]}:{port}"
        return f"***:{port}"
    return "***"


def _instruction_fields(instruction: str, debug: bool) -> Dict[str, Any]:
    digest = hashlib.sha256(instruction.encode("utf-8")).hexdigest()[:8]
    out: Dict[str, Any] = {
        "instruction_len": len(instruction),
        "instruction_h8": digest,
    }
    if debug and instruction:
        prev = instruction[:20]
        out["instruction_preview"] = prev + ("…" if len(instruction) > 20 else "")
    return out


def _base_url_host(url: str) -> str:
    try:
        p = urllib.parse.urlparse(url)
        return p.hostname or "-"
    except Exception:
        return "-"


def _context_history_fields(
    history: Optional[List[Dict[str, str]]], debug: bool
) -> Dict[str, Any]:
    if not history:
        return {"context_history_count": 0}
    n = len(history)
    out: Dict[str, Any] = {"context_history_count": n}
    if debug:
        total = 0
        for m in history:
            total += len(str(m.get("content", ""))) + len(str(m.get("role", "")))
        out["context_history_chars_approx"] = total
    return out


def _adb_summary_from_model(request: AgentRequest) -> Dict[str, Any]:
    adb = request.adb_config
    debug = debug_log_bodies_enabled()
    if adb is None:
        return {"adb_type": None}
    t = adb.type
    out: Dict[str, Any] = {"adb_type": t}
    addr = adb.params.get("address") if adb.params else None
    if t == "direct" and addr:
        out["adb_address_masked"] = mask_adb_address_for_log(str(addr))
        if debug:
            out["adb_direct"] = True
    return out


def _adb_summary_from_dict(
    adb_config: Optional[Dict[str, Any]], debug: bool
) -> Dict[str, Any]:
    if not adb_config:
        return {"adb_type": None}
    t = adb_config.get("type", "local")
    out: Dict[str, Any] = {"adb_type": t}
    addr = adb_config.get("params", {}).get("address")
    if t == "direct" and addr:
        out["adb_address_masked"] = mask_adb_address_for_log(str(addr))
        if debug:
            out["adb_direct"] = True
    return out


def sanitize_agent_request_summary(request: AgentRequest) -> Dict[str, Any]:
    """供 HTTP / 服务层打印的脱敏请求摘要（不含 api_key 明文）。"""
    debug = debug_log_bodies_enabled()
    parts: Dict[str, Any] = {
        "api_key_set": bool(request.api_key),
        "base_url_host": _base_url_host(request.base_url),
        "model_name": request.model_name,
        "max_steps": request.max_steps,
        "agent_type": request.agent_type,
        "lang": request.lang,
        "callback_url_set": request.callback_url is not None,
    }
    if debug and request.callback_url:
        try:
            p = urllib.parse.urlparse(request.callback_url)
            if p.scheme in ("http", "https"):
                parts["callback_host"] = p.hostname or "-"
        except Exception:
            parts["callback_host"] = "-"
    parts.update(_instruction_fields(request.instruction, debug))
    parts.update(_context_history_fields(request.context_history, debug))
    parts.update(_adb_summary_from_model(request))
    return parts


def sanitize_execute_thread_fields(
    *,
    instruction: str,
    max_steps: int,
    model_name: str,
    agent_type: str,
    lang: str,
    base_url: str,
    adb_config: Optional[Dict[str, Any]],
    context_history: Optional[List[Dict[str, str]]],
) -> Dict[str, Any]:
    """执行线程内使用的脱敏摘要（无 AgentRequest 对象）。"""
    debug = debug_log_bodies_enabled()
    parts: Dict[str, Any] = {
        "base_url_host": _base_url_host(base_url),
        "model_name": model_name,
        "max_steps": max_steps,
        "agent_type": agent_type,
        "lang": lang,
    }
    parts.update(_instruction_fields(instruction, debug))
    parts.update(_context_history_fields(context_history, debug))
    parts.update(_adb_summary_from_dict(adb_config, debug))
    return parts


def format_summary_kv(parts: Dict[str, Any]) -> str:
    """单行日志用，键排序便于 diff。"""
    return ", ".join(f"{k}={v!r}" for k, v in sorted(parts.items()))
