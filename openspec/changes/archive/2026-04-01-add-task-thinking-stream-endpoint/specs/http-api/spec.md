## ADDED Requirements

### Requirement: GET /task-thinking/{task_id} 端点
系统 SHALL 在 FastAPI 路由中注册 `GET /task-thinking/{task_id}` 端点，路径参数 `task_id` 类型为字符串。端点响应 MUST 为 `text/event-stream`，并设置适用于 SSE 的响应头（至少包括 `Cache-Control: no-cache`、`Connection: keep-alive`、`X-Accel-Buffering: no`）。

#### Scenario: 成功建立思考流连接
- **WHEN** 调用方请求 `GET /task-thinking/{task_id}` 且服务可正常处理
- **THEN** 系统 SHALL 返回 HTTP 200 与 `text/event-stream`，并以 SSE `data:` 帧持续输出事件

#### Scenario: 流式起始事件
- **WHEN** 调用方建立思考流连接
- **THEN** 系统 SHALL 首先输出 `event_type: "start"` 事件，包含 `task_id`、时间戳与当前任务状态

#### Scenario: 统一错误返回语义
- **WHEN** 发生任务不存在、内部异常或等待超时
- **THEN** 系统 MUST 通过 `event_type: "error"` 事件在流内返回错误信息，而不是抛出 HTTP 异常中断连接
