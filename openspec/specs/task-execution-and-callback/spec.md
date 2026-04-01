# Task Execution and Callback

## Purpose

描述线程池任务执行器、ADB 连接生命周期管理与回调机制，与 `app/core/executor.py` 对齐。

## Requirements

### Requirement: 线程池任务执行

系统 SHALL 使用 `concurrent.futures.ThreadPoolExecutor` 在独立线程中执行 Agent 任务，与 FastAPI 事件循环完全隔离。线程池 `max_workers` SHALL 默认为 `10`，可通过配置调整。

执行函数 SHALL 接收：`task_id`、`instruction`、`max_steps`、`api_key`、`base_url`、`model_name`、`callback_url`、`agent_type`、`lang`、`adb_config`、`context_history`。

#### Scenario: 异步执行不阻塞 API

- **WHEN** 提交一个耗时任务到线程池
- **THEN** API 端点 SHALL 在提交后立即返回，任务在后台线程中执行

### Requirement: Agent 创建与执行流程

执行线程 SHALL 按以下顺序操作：

1. 更新任务状态为 `running`
2. 根据 `adb_config` 建立 ADB 连接（如需）：`local` 不连接；`direct` 通过 `ADBConnection` 实例 `connect`；`ssh_tunnel` SHALL 建立 SSH 本地转发并成功 `adb connect` 至转发端口后再继续
3. 构造 `ModelConfig` 和 `AgentConfig`；当任务已通过 `direct` 或 `ssh_tunnel` 获得连接地址时，`AgentConfig.device_id` SHALL 设为该地址（与后续 `disconnect` 使用同一字符串）
4. 创建 `PhoneAgent` 实例
5. 如有 `context_history`，通过 `set_context()` 注入
6. 调用 `agent.run_as_dict(instruction)` 获取结构化结果
7. 更新任务状态为 `completed` 并存储结果
8. 清理 ADB 连接（如需）；若存在 SSH 隧道，SHALL 在断开 ADB 后关闭隧道

#### Scenario: 带 ADB 配置的任务执行

- **WHEN** 任务包含 `adb_config: {"type": "direct", "params": {"address": "10.0.0.1:5555"}}`
- **THEN** 执行线程 SHALL 先通过 `ADBConnection` 连接 `"10.0.0.1:5555"`，执行 Agent 任务，完成后对该地址 `disconnect`

#### Scenario: 执行异常处理

- **WHEN** Agent 执行过程中抛出异常
- **THEN** 执行线程 SHALL 捕获异常、更新状态为 `failed`、清理 ADB 连接，并构造包含错误信息的结果

### Requirement: 回调发送

当任务完成（成功/失败/取消）且 `callback_url` 非空时，系统 SHALL 向该 URL 发送 HTTP POST 请求，payload 为任务结果 JSON。

回调 SHALL 使用以下重试策略：
- 最大重试次数：5
- 退避策略：指数退避（基础延迟 1 秒）+ 随机抖动
- 最大延迟：30 秒
- 超时：每次请求 30 秒
- 成功判定：2xx 状态码

#### Scenario: 回调成功

- **WHEN** 任务完成且 `callback_url` 有效
- **THEN** 系统 SHALL POST 结果到该 URL，payload 包含 `task_id`、`status`、`instruction`、`message`、`history`

#### Scenario: 回调失败重试

- **WHEN** 首次回调请求返回 5xx 状态码
- **THEN** 系统 SHALL 在指数退避延迟后重试，最多 5 次

#### Scenario: 回调全部失败

- **WHEN** 5 次回调尝试均失败
- **THEN** 系统 SHALL 记录错误日志并放弃回调（不影响任务状态）

### Requirement: ADB 连接生命周期管理

执行线程 SHALL 在任务开始前根据 `adb_config` 建立连接，在任务结束后（无论成功或失败）清理连接。`direct` 类型的 TCP 连接建立与断开 SHALL 通过 `phone_agent.adb.connection.ADBConnection` 实例方法完成。`ssh_tunnel` 类型 SHALL 使用 `app/core/adb_ssh_tunnel.py`（或等价实现）建立 SSH 隧道并在隧道本地端口上完成 `connect`；任务结束后 SHALL 先对该地址 `disconnect`，再关闭 SSH 隧道。

`local` 类型 SHALL 不做连接操作。`direct` 类型 SHALL 通过 `ADBConnection` 实例调用 `connect(params["address"])`。

#### Scenario: local 类型无额外连接

- **WHEN** `adb_config.type` 为 `"local"` 或 `adb_config` 为 None
- **THEN** 执行线程 SHALL 不调用任何 ADB 连接/断开操作

#### Scenario: direct 连接与清理

- **WHEN** `adb_config.type` 为 `"direct"` 且 `params.address` 为 `"192.168.1.100:5555"`
- **THEN** 任务开始前 SHALL 通过 `ADBConnection` 连接 `"192.168.1.100:5555"`
- **THEN** 任务结束后 SHALL 对该地址 `disconnect`（在 finally 块中）

#### Scenario: ssh_tunnel 连接与清理

- **WHEN** `adb_config.type` 为 `"ssh_tunnel"` 且参数满足实现要求，隧道建立成功且 `adb connect` 成功
- **THEN** 任务开始前 SHALL 存在指向远端 ADB 的 SSH 本地转发，且 `PhoneAgent` SHALL 使用与该 `adb connect` 一致的 `device_id`
- **THEN** 任务结束后（含异常路径）SHALL 在 finally 中先对该 `device_id` `disconnect`，再执行隧道关闭逻辑，确保无残留转发

### Requirement: DeviceFactory 线程安全

在执行线程中设置 `DeviceType` 和初始化 `DeviceFactory` 时，系统 SHALL 使用全局 `threading.Lock` 保护，防止并发任务覆盖全局设备工厂状态。

#### Scenario: 并发任务不互相干扰

- **WHEN** 两个任务分别使用不同 `device_id` 并发执行
- **THEN** 各任务 SHALL 操作各自的目标设备，`device_id` 通过 `AgentConfig` 传入而非依赖全局状态

### Requirement: 任务执行线程结构化日志

在独立线程中执行 Agent 任务的入口（与 `app/core/executor.py` 中 `execute_agent_task_sync` 对齐）SHALL 在关键阶段写入 INFO 级别结构化日志；每条此类日志 SHALL 包含 `task_id`。关键阶段至少包括：任务开始执行（进入主流程且未被取消）、ADB 连接建立完成或判定为 local 跳过连接、`PhoneAgent` 实例创建完成、`run_as_dict` 调用前、`run_as_dict` 正常返回后。

当发生异常时，系统 SHALL 继续记录 ERROR 级别日志并 SHALL 包含异常栈信息（与现有行为一致）。执行线程日志 MUST 遵守：禁止明文 `api_key`；禁止完整 `instruction` 原文出现在日志中。

#### Scenario: 按 task_id 串联执行轨迹

- **WHEN** 某任务从 API 提交到线程内执行直至完成或失败
- **THEN** 运维人员 SHALL 能够仅通过 `task_id` 在标准日志中过滤出该任务在执行线程内的阶段序列

#### Scenario: 异常日志不泄露密钥与全文指令

- **WHEN** 执行线程因模型、ADB 或其他原因抛出异常
- **THEN** ERROR 日志 SHALL NOT 包含明文 `api_key` 或用户 `instruction` 的完整原文
