## Context

`Open-AutoGLM` 现有 HTTP API 仅提供任务提交、状态查询、任务列表与取消接口，缺少与 `AgentDroid` 对齐的任务思考流接口。当前任务状态记录结构也未包含思考日志字段，执行链路没有统一的思考事件落库点，因此即使新增路由也无法稳定产出可消费的 SSE 事件流。

该变更属于跨模块改动，涉及 API 路由层（`app/api/v1/endpoints/tasks.py`）、服务层（新增任务思考流服务）、任务状态管理（`app/core/task_manager.py`）与执行链路（`app/core/executor.py`）。

## Goals / Non-Goals

**Goals:**
- 提供 `GET /task-thinking/{task_id}`，入参和响应事件结构与 `AgentDroid` 对齐。
- 建立任务思考日志采集与读取能力，支持执行中任务的实时增量推送。
- 统一错误处理为 SSE `error` 事件，避免该接口通过 HTTP 异常中断。

**Non-Goals:**
- 不改造任务持久化存储（仍采用内存态，不引入 Redis/DB）。
- 不扩展新的鉴权模型或多租户隔离逻辑。
- 不改变 `POST /run-agent-async` 与现有任务状态接口的外部契约。

## Decisions

1. **在任务状态记录中引入 `thinking_logs` 字段**
   - 选择：在 `create_task_record` 初始化 `thinking_logs: []`，并通过线程锁保护增删读。
   - 原因：最小改动复用现有内存任务表与锁机制，避免新增共享状态容器。
   - 备选方案：独立日志缓冲表（按 `task_id` 索引）。未采用，因为会引入额外一致性维护。

2. **新增任务思考日志写入函数**
   - 选择：在 `task_manager` 增加 `add_thinking_log(task_id, step, thinking, log_type)`。
   - 原因：将日志结构与并发控制收敛在同一模块，避免执行器重复实现锁逻辑。
   - 备选方案：在执行器直接写 `_tasks`。未采用，因为破坏封装并提高并发风险。

3. **SSE 输出由独立服务函数生成**
   - 选择：新增 `task_service.get_task_thinking_stream(task_id)`，统一生成 `start/thinking/complete/error` 事件。
   - 原因：让路由层保持薄封装，便于后续复用与测试。
   - 备选方案：在路由里直接拼装 SSE。未采用，因为可测试性与可维护性较差。

4. **错误语义保持“流内错误”**
   - 选择：该接口所有业务错误均通过 `event_type=error` 返回（如 `not_found`、`internal_error`、`timeout`）。
   - 原因：与 `AgentDroid` 行为一致，客户端可统一按 SSE 协议消费。
   - 备选方案：404/500 直接抛 HTTP 异常。未采用，因为会导致客户端处理分叉。

## Risks / Trade-offs

- **[风险] 执行链路无法稳定产生思考内容** → **缓解**：至少写入开始、完成/失败/取消等终止日志，确保流可闭环；若思考文本缺失，也能输出状态事件。
- **[风险] 内存日志增长导致单进程占用上升** → **缓解**：沿用现有任务清理机制，任务清理时连带释放思考日志。
- **[风险] 轮询推流造成空转开销** → **缓解**：采用短间隔轮询与超时上限，结束态立即退出。
