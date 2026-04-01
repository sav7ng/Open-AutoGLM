## 1. 脱敏与调试开关

- [x] 1.1 新增可复用的脱敏辅助逻辑（如 `app/` 下小模块或 `executor` 同级工具），对 `api_key`、`instruction`、`context_history`、`base_url`、`adb_config` 按 `design.md` 规则输出摘要结构（禁止明文密钥与完整指令）
- [x] 1.2 支持环境变量 `PHONE_AGENT_DEBUG_LOG_BODIES`（真值时允许额外调试字段，仍 MUST 屏蔽 `api_key` 明文）

## 2. HTTP 端点与服务层

- [x] 2.1 在 `app/api/v1/endpoints/agent.py` 的 `POST /run-agent-async` 上增加入口日志、成功返回前的响应摘要日志；异常路径保持 ERROR 且 `exc_info`，并确保任何分支不打印明文 `api_key`
- [x] 2.2 在 `app/services/agent_service.py` 的 `run_agent_async` 中扩展结构化 INFO（含 `task_id`、脱敏请求摘要），在线程池 `submit` 前后各一条简要日志以便确认入队

## 3. 任务执行线程

- [x] 3.1 在 `app/core/executor.py` 的 `execute_agent_task_sync` 中按 delta spec 增加阶段 INFO（含 `task_id`：开始、ADB 就绪或 local 跳过、PhoneAgent 创建后、`run_as_dict` 前后）；异常路径不记录完整 `instruction` 与明文 `api_key`

## 4. 验证

- [x] 4.1 启动服务（本地或 Docker），调用 `POST /run-agent-async`，检查标准输出/日志：存在可过滤的 `task_id`、脱敏摘要，且检索不到请求中的 `api_key` 原文
