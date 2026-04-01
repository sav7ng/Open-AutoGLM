## MODIFIED Requirements

### Requirement: AdbConnectionConfig 模型

系统 SHALL 定义 Pydantic 模型 `AdbConnectionConfig`，支持 ADB 连接配置：

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `type` | `str` | `"local"` |
| `params` | `Dict[str, Any]` | `{}` |

`type` SHALL 支持：

- `"local"`：使用本机已连接的 ADB 设备，执行层不发起额外 `connect`。
- `"direct"`：远程 ADB TCP 直连，`params.address` SHALL 为 `host:port` 形式（或实现所接受的等价形式），执行层 SHALL 调用 `ADBConnection.connect(params["address"])`。
- `"ssh_tunnel"`：经 SSH 本地端口转发访问远端 ADB。`params` SHALL 至少包含：`ssh_host`（`user@host` 或主机名，若仅主机名则实现 MAY 使用 `ssh_username`）、`ssh_port`（可选，默认与实现一致）、`remote_adb_host`、`remote_adb_port`（可选，默认与实现一致）；认证 SHALL 通过 `ssh_password` 和/或 `ssh_private_key`（或实现文档中与 `app/core/adb_ssh_tunnel.py` 对齐的字段名）之一提供，以满足 `sshtunnel` 建连需要。

#### Scenario: 远程 ADB 配置

- **WHEN** 请求包含 `adb_config: {"type": "direct", "params": {"address": "192.168.1.100:5555"}}`
- **THEN** 系统 SHALL 将该配置传递到执行层用于建立远程 ADB 连接

#### Scenario: SSH 隧道 ADB 配置

- **WHEN** 请求包含 `adb_config.type` 为 `"ssh_tunnel"` 且 `params` 包含有效的 `ssh_host`、`remote_adb_host` 及实现所要求的认证字段
- **THEN** 系统 SHALL 将该配置传递到执行层，执行层 SHALL 建立 SSH 隧道、对本地转发端口执行 `adb connect`，并将所连接的地址作为该任务的 `device_id` 用于后续 Agent 步骤
