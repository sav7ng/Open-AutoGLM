## ADDED Requirements

### Requirement: 线程池任务执行

系统 SHALL 使用 `concurrent.futures.ThreadPoolExecutor` 在独立线程中执行 Agent 任务，与 FastAPI 事件循环完全隔离。线程池 `max_workers` SHALL 默认为 `10`，可通过配置调整。

执行函数 SHALL 接收：`task_id`、`instruction`、`max_steps`、`api_key`、`base_url`、`model_name`、`callback_url`、`agent_type`、`lang`、`adb_config`、`context_history`。

#### Scenario: 异步执行不阻塞 API

- **WHEN** 提交一个耗时任务到线程池
- **THEN** API 端点 SHALL 在提交后立即返回，任务在后台线程中执行

### Requirement: Agent 创建与执行流程

执行线程 SHALL 按以下顺序操作：
1. 更新任务状态为 `running`
2. 根据 `adb_config` 建立 ADB 连接（如需）
3. 构造 `ModelConfig` 和 `AgentConfig`
4. 创建 `PhoneAgent` 实例
5. 如有 `context_history`，通过 `set_context()` 注入
6. 调用 `agent.run_as_dict(instruction)` 获取结构化结果
7. 更新任务状态为 `completed` 并存储结果
8. 清理 ADB 连接（如需）

#### Scenario: 带 ADB 配置的任务执行

- **WHEN** 任务包含 `adb_config: {"type": "direct", "params": {"address": "10.0.0.1:5555"}}`
- **THEN** 执行线程 SHALL 先调用 `ADBConnection.connect("10.0.0.1:5555")`，执行 Agent 任务，完成后调用 `ADBConnection.disconnect("10.0.0.1:5555")`

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

执行线程 SHALL 在任务开始前根据 `adb_config` 建立连接，在任务结束后（无论成功或失败）清理连接。连接建立 SHALL 通过 `phone_agent.adb.connection.ADBConnection` 完成。

`local` 类型 SHALL 不做连接操作。`direct` 类型 SHALL 调用 `ADBConnection.connect(params["address"])`。

#### Scenario: local 类型无额外连接

- **WHEN** `adb_config.type` 为 `"local"` 或 `adb_config` 为 None
- **THEN** 执行线程 SHALL 不调用任何 ADB 连接/断开操作

#### Scenario: direct 连接与清理

- **WHEN** `adb_config.type` 为 `"direct"` 且 `params.address` 为 `"192.168.1.100:5555"`
- **THEN** 任务开始前 SHALL 调用 `ADBConnection.connect("192.168.1.100:5555")`
- **THEN** 任务结束后 SHALL 调用 `ADBConnection.disconnect("192.168.1.100:5555")`（在 finally 块中）

### Requirement: DeviceFactory 线程安全

在执行线程中设置 `DeviceType` 和初始化 `DeviceFactory` 时，系统 SHALL 使用全局 `threading.Lock` 保护，防止并发任务覆盖全局设备工厂状态。

#### Scenario: 并发任务不互相干扰

- **WHEN** 两个任务分别使用不同 `device_id` 并发执行
- **THEN** 各任务 SHALL 操作各自的目标设备，`device_id` 通过 `AgentConfig` 传入而非依赖全局状态
