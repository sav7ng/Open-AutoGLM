# HTTP API (delta)

## MODIFIED Requirements

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
