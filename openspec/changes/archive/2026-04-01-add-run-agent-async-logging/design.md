## Context

`POST /run-agent-async` 在 `app/api/v1/endpoints/agent.py` 委托 `app/services/agent_service.py` 生成 `task_id` 并 `ThreadPoolExecutor.submit` 到 `app/core/executor.py`。HTTP 200 返回后，真实失败常发生在容器内 ADB、模型 API 或 Agent 运行阶段；现有日志在端点成功路径较薄，且缺少与「脱敏入参/响应」一致的字段约定。

## Goals / Non-Goals

**Goals:**

- 用统一 `task_id` 串起 API → 服务层 → 执行线程的 INFO 日志，便于 `docker logs` 过滤。
- 默认 INFO 即可看到脱敏后的请求摘要与 accepted 响应摘要。
- 执行层关键阶段打点，异常保持栈追踪且不泄露密钥。

**Non-Goals:**

- 引入集中式链路追踪（OpenTelemetry 等）、结构化 JSON log 驱动程序或第三方日志后端。
- 修改对外 JSON 契约或任务状态机语义。
- 记录完整原始 HTTP body 或明文 `api_key`（即使在调试模式下也禁止明文密钥）。

## Decisions

1. **脱敏策略（统一实现小函数或模块内私有函数）**  
   - `api_key`：永不记录；调试模式仅允许 `***` 或布尔「已提供」。  
   - `instruction`：`len` + 可选短前缀（如 ≤20 字符）或 SHA256 前 8 位。  
   - `context_history`：条数；可选总字符长度。  
   - `base_url`：`urllib.parse.urlparse` 的 `hostname`（无则记 `"-"`）。  
   - `adb_config`：`type`；`direct` 时对 `address` 做主机脱敏（如只显示最后一段或 `***:5555`）。  
   - **Rationale**：满足排障（连哪台设备、哪类 agent、哪类模型端点）同时避免日志成为秘密泄露面。

2. **日志落点**  
   - 端点：`logger` 在请求进入、调用 service 返回后（成功/失败分支分别足够）。  
   - 服务层：生成 `task_id` 后扩展当前 `info`，并增加 `submit` 前后各一行（若需确认入队）。  
   - 执行器：在现有 `update_task_status(RUNNING)`、ADB 设置、`PhoneAgent` 创建、`run_as_dict` 前后加 `info`。  
   - **Rationale**：失败点分散，分层打点成本最低。

3. **可选调试开关**  
   - 环境变量 `PHONE_AGENT_DEBUG_LOG_BODIES`（或文档中与现有 `PHONE_AGENT_*` 命名一致）：开启时允许更冗长脱敏字段，仍禁止 `api_key` 明文。  
   - **Alternatives considered**：仅用 `logging.DEBUG` — 不利于容器默认 INFO 排障；仅用 `LOG_LEVEL` — 会放大无关模块噪声。

4. **与现有 `logger.error(..., exc_info=True)` 的关系**  
   - 保留；新增 INFO 不替代异常栈。  
   - **Rationale**：Docker 下栈最有用。

## Risks / Trade-offs

- **日志量上升** → 控制每条为单行结构化 key=value 或少量占位符；避免每 step 打印模型全文。  
- **脱敏过度导致仍难排障** → 保留 `task_id` + `agent_type` + `base_url` host + adb `type`；必要时文档说明临时提高调试开关。  
- **多线程日志交错** → 依赖 `task_id` 过滤；不在此变更引入异步上下文变量强制约束。

## Migration Plan

- 部署：仅代码与 spec 更新；无需数据迁移。  
- 回滚：还原日志相关提交；行为与日志量恢复先前状态。  
- 运维：在 compose/k8s 中如需更少日志，可将根 logger 级别设为 WARNING（接受可观测性减弱）。

## Open Questions

- 是否在 `server.py` / `app/main.py` 统一配置 `logging` 格式（时间戳、级别、logger 名），以便多容器聚合工具解析（本变更可先沿用 uvicorn 默认）。
