# Task Execution and Callback (delta)

## ADDED Requirements

### Requirement: 任务执行线程结构化日志

在独立线程中执行 Agent 任务的入口（与 `app/core/executor.py` 中 `execute_agent_task_sync` 对齐）SHALL 在关键阶段写入 INFO 级别结构化日志；每条此类日志 SHALL 包含 `task_id`。关键阶段至少包括：任务开始执行（进入主流程且未被取消）、ADB 连接建立完成或判定为 local 跳过连接、`PhoneAgent` 实例创建完成、`run_as_dict` 调用前、`run_as_dict` 正常返回后。

当发生异常时，系统 SHALL 继续记录 ERROR 级别日志并 SHALL 包含异常栈信息（与现有行为一致）。执行线程日志 MUST 遵守：禁止明文 `api_key`；禁止完整 `instruction` 原文出现在日志中。

#### Scenario: 按 task_id 串联执行轨迹

- **WHEN** 某任务从 API 提交到线程内执行直至完成或失败
- **THEN** 运维人员 SHALL 能够仅通过 `task_id` 在标准日志中过滤出该任务在执行线程内的阶段序列

#### Scenario: 异常日志不泄露密钥与全文指令

- **WHEN** 执行线程因模型、ADB 或其他原因抛出异常
- **THEN** ERROR 日志 SHALL NOT 包含明文 `api_key` 或用户 `instruction` 的完整原文
