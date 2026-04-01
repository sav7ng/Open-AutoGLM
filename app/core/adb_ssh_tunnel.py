"""SSH 本地端口转发 + adb connect（adb_config.type == ssh_tunnel）。"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def setup_ssh_tunnel_and_adb(
    task_id: str, params: Dict[str, Any]
) -> Tuple[str, Callable[[], None]]:
    """
    建立 SSH -L 转发到远端 ADB，再在本机 adb connect 127.0.0.1:<动态端口>。

    Returns:
        (adb_address, cleanup) — cleanup 仅负责关闭隧道；adb disconnect 由 executor 统一处理。
    """
    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError as e:
        raise RuntimeError(
            "ssh_tunnel 需要依赖 sshtunnel，请在环境中执行: pip install sshtunnel"
        ) from e

    from phone_agent.adb.connection import ADBConnection

    from app.core.log_sanitize import mask_adb_address_for_log

    raw_host = (params.get("ssh_host") or "").strip()
    if "@" in raw_host:
        ssh_username, ssh_hostname = raw_host.split("@", 1)
    else:
        ssh_username = str(params.get("ssh_username") or "root").strip()
        ssh_hostname = raw_host

    if not ssh_hostname:
        raise ValueError("ssh_tunnel 需要 params.ssh_host，格式为 user@host 或单独主机名")

    ssh_port = int(params.get("ssh_port", 22))
    remote_host = params.get("remote_adb_host")
    if not remote_host:
        raise ValueError("ssh_tunnel 需要 params.remote_adb_host")
    remote_port = int(params.get("remote_adb_port", 5555))

    ssh_password = params.get("ssh_password")
    ssh_pkey = params.get("ssh_pkey") or params.get("ssh_private_key")
    if isinstance(ssh_pkey, str) and not ssh_pkey.strip():
        ssh_pkey = None

    if ssh_pkey is None and ssh_password is None:
        raise ValueError("ssh_tunnel 需要 params.ssh_password 或 params.ssh_private_key（密钥文件路径）")

    tunnel_kw: Dict[str, Any] = {
        "ssh_address_or_host": (ssh_hostname, ssh_port),
        "ssh_username": ssh_username,
        "remote_bind_address": (str(remote_host), remote_port),
        "local_bind_address": ("127.0.0.1", 0),
        "set_keepalive": 30.0,
        "allow_agent": False,
        "host_pkey_directories": [],
    }
    if ssh_pkey is not None:
        tunnel_kw["ssh_pkey"] = ssh_pkey
    if ssh_password is not None:
        tunnel_kw["ssh_password"] = ssh_password

    tunnel = SSHTunnelForwarder(**tunnel_kw)
    tunnel.start()
    local_port = tunnel.local_bind_port
    address = f"127.0.0.1:{local_port}"

    logger.info(
        "SSH 转发已建立: task_id=%s, local=%s, remote_adb=%s:%s",
        task_id,
        mask_adb_address_for_log(address),
        remote_host,
        remote_port,
    )

    conn = ADBConnection()
    ok, msg = conn.connect(address, timeout=30)
    if not ok:
        try:
            tunnel.stop()
        except Exception:
            pass
        raise RuntimeError(f"ADB 经 SSH 隧道连接失败: {msg}")

    def _cleanup_tunnel() -> None:
        try:
            tunnel.stop()
        except Exception as ex:
            logger.warning("SSH 隧道关闭失败: task_id=%s, error=%s", task_id, ex)

    return address, _cleanup_tunnel
