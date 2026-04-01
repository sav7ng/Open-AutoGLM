## ADDED Requirements

### Requirement: 任务思考日志采集与流式推送
系统 MUST 支持按任务维度采集思考日志，并通过 SSE 以增量方式推送给调用方。每条日志 SHALL 至少包含 `step`、`log_type`、`thinking`、`timestamp` 字段。

#### Scenario: 执行中任务实时推送思考日志
- **WHEN** 调用方请求 `GET /task-thinking/{task_id}` 且任务仍在执行
- **THEN** 系统 SHALL 按日志新增顺序持续输出 `event_type: "thinking"` 事件，直到任务终止事件出现或超时

#### Scenario: 不存在任务返回流内错误
- **WHEN** 调用方请求不存在的 `task_id`
- **THEN** 系统 SHALL 返回一个 `event_type: "error"` 事件，且错误类型为 `not_found`，并结束流

#### Scenario: 终止状态后发送完成事件
- **WHEN** 日志中出现 `task_completed`、`task_failed` 或 `task_cancelled` 终止日志
- **THEN** 系统 SHALL 输出 `event_type: "complete"` 事件并结束流
