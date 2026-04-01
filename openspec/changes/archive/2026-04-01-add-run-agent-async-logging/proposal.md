## Why

在 Docker 等容器环境中调用 `POST /run-agent-async` 时，失败可能发生在 HTTP 层（校验、入参）或任务已 `accepted` 后的后台执行阶段；当前日志不足以用单一 `task_id` 串起「请求 → 入队 → ADB/Agent」全链路，且缺少可安全落盘的入参与响应摘要，排障成本高。

## What Changes

- 在 `POST /run-agent-async` 路径上增加**结构化日志**：请求进入、校验通过后、返回响应前，以及服务层提交线程池前后；日志字段与 `task_id` 对齐。
- 记录**脱敏后的请求摘要**与**响应摘要**（禁止明文 `api_key`；`instruction` / `context_history` 仅长度或 hash；`base_url` 仅 host；`adb_config` 仅 type 与脱敏地址）。
- 可选：通过环境变量开启更详细的调试日志（仍须对密钥与敏感文本脱敏）。
- 在任务执行层（`execute_agent_task_sync` 及相关步骤）增加**阶段级** info 日志（ADB 连接、Agent 构造、run 起止），异常保持 `exc_info`，便于 `docker logs` 关联同一 `task_id`。

## Capabilities

### New Capabilities

（无 — 行为约束落在既有能力上。）

### Modified Capabilities

- `http-api`：补充 `POST /run-agent-async` 的可观测性要求（日志时点、脱敏规则、与 `task_id` 关联）。
- `task-execution-and-callback`：补充异步任务在线程中执行时的阶段日志要求（不泄露密钥与完整用户指令）。

## Impact

- 代码：`app/api/v1/endpoints/agent.py`、`app/services/agent_service.py`、`app/core/executor.py`；必要时 `app/main.py` 或统一 logging 配置。
- 运维：容器标准输出日志量增加；需约定日志级别（如默认 INFO 可见结构化行）。
- API 契约与 JSON 形状不变；无 **BREAKING** 变更。
