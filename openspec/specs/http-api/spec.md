# HTTP API

## Purpose

描述 Open-AutoGLM 的 HTTP API 服务层：FastAPI 应用、请求/响应模型、端点定义，与 `app/` 目录下实现对齐。接口契约与 AgentDroid 项目的 `AgentRequest` 保持字段级一致。

## Requirements

### Requirement: FastAPI 应用与启动入口

系统 SHALL 在仓库根目录提供 `server.py` 作为 HTTP 服务启动入口，通过 `uvicorn` 运行 FastAPI 应用。FastAPI 应用 SHALL 定义在 `app/main.py` 中。默认监听端口 SHALL 为 `8000`，可通过环境变量 `PHONE_AGENT_SERVER_PORT` 覆盖。

#### Scenario: 启动 HTTP 服务

- **WHEN** 用户执行 `python server.py`
- **THEN** uvicorn SHALL 在 `0.0.0.0:8000` 启动 FastAPI 应用并接受 HTTP 请求

#### Scenario: 自定义端口

- **WHEN** 用户设置 `PHONE_AGENT_SERVER_PORT=9000` 并执行 `python server.py`
- **THEN** 服务 SHALL 在端口 9000 上监听

### Requirement: AgentRequest 请求模型

系统 SHALL 定义 Pydantic 模型 `AgentRequest`，字段与 AgentDroid 的同名模型保持一致：

| 字段 | 类型 | 默认值 | 必填 |
|------|------|--------|------|
| `instruction` | `str` | — | 是 |
| `max_steps` | `int` | `50` | 否 |
| `api_key` | `str` | — | 是 |
| `base_url` | `str` | — | 是 |
| `model_name` | `str` | `"autoglm-phone"` | 否 |
| `callback_url` | `Optional[str]` | `None` | 否 |
| `agent_type` | `str` | `"phone-agent"` | 否 |
| `adb_config` | `Optional[AdbConnectionConfig]` | `None` | 否 |
| `context_history` | `Optional[List[Dict[str, str]]]` | `None` | 否 |
| `lang` | `Literal["cn", "en"]` | `"cn"` | 否 |

#### Scenario: 最小请求

- **WHEN** 调用方 POST 仅包含 `instruction`、`api_key`、`base_url` 的 JSON
- **THEN** 系统 SHALL 使用默认值填充其余字段并正常处理

#### Scenario: 完整请求

- **WHEN** 调用方 POST 包含所有字段（含 `adb_config`、`callback_url`、`context_history`）
- **THEN** 系统 SHALL 将所有字段传递到服务层

### Requirement: AdbConnectionConfig 模型

系统 SHALL 定义 Pydantic 模型 `AdbConnectionConfig`，支持 ADB 连接配置：

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `type` | `str` | `"local"` |
| `params` | `Dict[str, Any]` | `{}` |

`type` SHALL 支持：

- `"local"`：使用本机已连接的 ADB 设备，执行层不发起额外 `connect`。
- `"direct"`：远程 ADB TCP 直连，`params.address` SHALL 为 `host:port` 形式（或实现所接受的等价形式），执行层 SHALL 通过 `ADBConnection` 实例调用 `connect`。
- `"ssh_tunnel"`：经 SSH 本地端口转发访问远端 ADB。`params` SHALL 至少包含：`ssh_host`（`user@host` 或主机名，若仅主机名则实现 MAY 使用 `ssh_username`）、`ssh_port`（可选，默认与实现一致）、`remote_adb_host`、`remote_adb_port`（可选，默认与实现一致）；认证 SHALL 通过 `ssh_password` 和/或 `ssh_private_key`（或实现文档中与 `app/core/adb_ssh_tunnel.py` 对齐的字段名）之一提供，以满足 `sshtunnel` 建连需要。

#### Scenario: 远程 ADB 配置

- **WHEN** 请求包含 `adb_config: {"type": "direct", "params": {"address": "192.168.1.100:5555"}}`
- **THEN** 系统 SHALL 将该配置传递到执行层用于建立远程 ADB 连接

#### Scenario: SSH 隧道 ADB 配置

- **WHEN** 请求包含 `adb_config.type` 为 `"ssh_tunnel"` 且 `params` 包含有效的 `ssh_host`、`remote_adb_host` 及实现所要求的认证字段
- **THEN** 系统 SHALL 将该配置传递到执行层，执行层 SHALL 建立 SSH 隧道、对本地转发端口执行 `adb connect`，并将所连接的地址作为该任务的 `device_id` 用于后续 Agent 步骤

### Requirement: POST /run-agent-async 端点

系统 SHALL 在 FastAPI 路由中注册 `POST /run-agent-async` 端点，接收 `AgentRequest`，调用服务层 `run_agent_async(request)` 并返回包含 `task_id` 和 `status: "accepted"` 的 JSON 响应。

端点 SHALL 捕获以下异常并返回对应 HTTP 状态码：

- `ValueError` → 400
- 其他异常 → 500

系统 SHALL 在本端点及相关服务层路径上写入结构化日志，以便在容器等环境中排障：在调用服务层之前记录请求已到达；在 `task_id` 生成之后，与该次提交相关的日志 SHALL 包含同一 `task_id`。系统 SHALL 记录脱敏后的请求摘要与将返回给客户端的响应摘要（成功路径）。脱敏规则 SHALL 满足：**禁止**在日志中出现明文 `api_key`；`instruction` 与 `context_history` 正文 SHALL 不得以完整原文出现在日志中，仅允许长度或单向摘要（如加密 hash 的短前缀）；`base_url` SHALL 仅记录解析后的主机名（不含用户信息与路径、查询、片段）；`adb_config` SHALL 仅记录 `type` 以及对连接地址的脱敏形式（须避免日志中可直接复用的完整敏感地址与凭证）。上述可观测性日志 SHALL 在默认 INFO 级别下可见。

当环境变量 `PHONE_AGENT_DEBUG_LOG_BODIES` 设置为项目文档规定的真值时，实现 MAY 输出额外调试字段，但仍 MUST 对 `api_key` 使用占位符而非明文。

#### Scenario: 正常提交异步任务

- **WHEN** 调用方 POST 合法 `AgentRequest` 到 `/run-agent-async`
- **THEN** 响应 SHALL 为 200，body 包含 `task_id`（UUID 字符串）、`status: "accepted"`、`agent_type`、`message`

#### Scenario: 不支持的 agent_type

- **WHEN** 请求中 `agent_type` 为系统未注册的类型
- **THEN** 响应 SHALL 为 400，detail 包含错误信息

#### Scenario: 可观测日志与 task_id 关联

- **WHEN** 调用方 POST 合法 `AgentRequest` 且任务被接受
- **THEN** 系统在生成 `task_id` 后 SHALL 至少输出一条包含该 `task_id` 及脱敏请求摘要的 INFO 日志，并在返回 200 响应前输出一条包含该 `task_id` 及响应关键字段（至少含 `status: "accepted"`）的 INFO 日志

#### Scenario: 异常路径不泄露密钥

- **WHEN** 端点或服务层抛出异常并导致 400 或 500
- **THEN** 系统 SHALL 记录 ERROR 级别日志（未预期异常 SHALL 包含异常栈信息），且 MUST NOT 在日志中输出明文 `api_key`

### Requirement: GET /task-status/{task_id} 端点

系统 SHALL 提供 `GET /task-status/{task_id}` 端点，返回指定任务的当前状态和结果（如已完成）。

#### Scenario: 查询运行中的任务

- **WHEN** 调用方 GET `/task-status/{task_id}` 且任务正在执行
- **THEN** 响应 SHALL 包含 `task_id`、`status: "running"`

#### Scenario: 查询已完成的任务

- **WHEN** 调用方 GET `/task-status/{task_id}` 且任务已完成
- **THEN** 响应 SHALL 包含 `task_id`、`status: "completed"`、`result` 字段

#### Scenario: 查询不存在的任务

- **WHEN** 调用方 GET `/task-status/{unknown_id}`
- **THEN** 响应 SHALL 为 404
