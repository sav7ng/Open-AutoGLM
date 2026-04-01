## Why

Open-AutoGLM 当前仅提供 CLI 入口（`main.py`），无法被外部系统通过 HTTP 调用。上层项目（如 AgentDroid）需要将手机自动化能力封装为 API 服务，以支持异步任务提交、状态查询、完成回调等标准后端集成模式。在 Open-AutoGLM 内部直接提供此能力，可消除上层项目对核心 `phone_agent` 包的二次封装成本，并保持接口契约与 AgentDroid 一致，便于调用方无缝切换。

## What Changes

- 新增 FastAPI HTTP 服务层，提供 `POST /run-agent-async` 端点，入参与响应模型与 AgentDroid 的 `AgentRequest` 完全一致。
- 新增异步任务管理：UUID task_id 生成、内存任务状态表（accepted → running → completed/failed/cancelled）、`GET /task-status/{task_id}` 查询。
- 新增线程池执行器：在独立线程中运行 `PhoneAgent.run()`，与 FastAPI 事件循环完全隔离。
- 新增回调机制：任务完成/失败/取消时，向 `callback_url` POST 结果，含指数退避重试。
- 新增 ADB 连接配置适配：接收 `adb_config`（local/direct/ssh_tunnel），桥接到现有 `ADBConnection` + `DeviceFactory`。
- 新增 `context_history` 注入：支持在 API 调用中传入多轮对话上下文。
- 新增 `server.py` 启动入口（uvicorn）。
- 新增依赖：`fastapi`、`uvicorn`、`requests`（回调用）。

## Capabilities

### New Capabilities
- `http-api`: HTTP API 服务层，包括 FastAPI 应用、路由、请求/响应模型（`AgentRequest`、`AdbConnectionConfig`）、端点定义。
- `async-task-management`: 异步任务生命周期管理，包括 task_id 生成、状态跟踪（内存）、任务查询与取消端点。
- `task-execution-and-callback`: 线程池任务执行器与回调机制，包括独立线程执行 Agent、完成后 HTTP POST 回调（含重试）。

### Modified Capabilities
- `architecture`: 新增 HTTP 服务层目录结构与模块职责说明；更新"与 HTTP 服务无关的边界"要求——现在本仓库可选地提供 FastAPI 服务入口。
- `agent-runtime`: `PhoneAgent` 需支持结构化返回（dict 而非纯字符串）及外部 `context_history` 注入。

## Impact

- **新增文件**：`server.py`、`app/` 目录（`main.py`、`models/schemas.py`、`api/v1/endpoints/agent.py`、`services/agent_service.py`、`core/executor.py`、`core/task_manager.py`）。
- **修改文件**：`phone_agent/agent.py`（`run()` 返回值适配、context_history 支持）、`requirements.txt`（新增 fastapi/uvicorn/requests）。
- **依赖**：新增 `fastapi`、`uvicorn[standard]`、`requests`。
- **API 契约**：`AgentRequest` schema 与 AgentDroid 保持字段级一致，调用方可无缝切换。
- **ADB 并发**：`DeviceFactory` 全局单例在多任务场景下需要线程安全保护。
