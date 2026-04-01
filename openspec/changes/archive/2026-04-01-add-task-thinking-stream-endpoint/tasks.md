## 1. HTTP API 与服务层

- [x] 1.1 在 `app/api/v1/endpoints/tasks.py` 新增 `GET /task-thinking/{task_id}` 路由，返回 `StreamingResponse` 与 SSE 响应头
- [x] 1.2 新增 `app/services/task_service.py`，实现 `get_task_thinking_stream(task_id)` 的 SSE 事件生成逻辑（start/thinking/complete/error）
- [x] 1.3 为 `task_service` 增加不存在任务、超时和内部异常场景的流内错误事件处理

## 2. 任务状态与思考日志

- [x] 2.1 在 `app/core/task_manager.py` 的任务记录中新增 `thinking_logs` 字段并初始化为空数组
- [x] 2.2 在 `app/core/task_manager.py` 增加线程安全的 `add_thinking_log(...)` 能力
- [x] 2.3 确认任务清理/查询逻辑对 `thinking_logs` 字段保持兼容

## 3. 执行链路接入

- [x] 3.1 在 `app/core/executor.py` 接入思考日志写入（启动、执行中、完成/失败/取消）
- [x] 3.2 统一终止日志 `log_type`（`task_completed` / `task_failed` / `task_cancelled`）以驱动 SSE 完成事件
- [x] 3.3 保证异常路径仍能写入可观测日志并不破坏现有状态机

## 4. 验证与对齐

- [x] 4.1 增加接口验证用例或手工验证脚本，覆盖 start/thinking/complete/error 四类事件
- [x] 4.2 对齐 `AgentDroid` 的入参与响应结构，核对字段名与错误事件载荷一致
- [x] 4.3 运行基础检查（如 lint/启动）并记录验证结果
