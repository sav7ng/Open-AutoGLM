## Why

当前 `Open-AutoGLM` 缺少 `GET /task-thinking/{task_id}`，导致调用方无法以与 `AgentDroid` 一致的方式实时获取任务思考流，影响现有集成迁移与观测能力。需要补齐该接口并统一事件契约，确保跨项目调用行为一致。

## What Changes

- 新增 `GET /task-thinking/{task_id}` HTTP 端点，返回 `text/event-stream`。
- 新增任务思考流服务逻辑，按 SSE 输出 `start` / `thinking` / `complete` / `error` 事件。
- 扩展任务状态记录，增加思考日志存储字段与写入能力，支持流式增量读取。
- 在任务执行链路中补充思考与终止事件日志写入，保证接口可返回真实内容而非空流。

## Capabilities

### New Capabilities

- `task-thinking-streaming`: 规定任务思考日志的采集、存储与 SSE 实时推送能力及事件契约。

### Modified Capabilities

- `http-api`: 增加 `/task-thinking/{task_id}` 端点契约与错误流返回要求。
- `async-task-management`: 增加任务思考日志字段、写入接口及并发访问约束。

## Impact

- API：`app/api/v1/endpoints/tasks.py` 增加新路由与 SSE 响应头。
- 服务层：新增/扩展任务查询服务（SSE 生成器）。
- 核心状态管理：`app/core/task_manager.py` 增加 `thinking_logs` 与写日志函数。
- 执行链路：`app/core/executor.py` 增加思考日志采集与终止事件记录。
