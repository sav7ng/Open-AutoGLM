## MODIFIED Requirements

### Requirement: Agent 创建与执行流程

执行线程 SHALL 按以下顺序操作：

1. 更新任务状态为 `running`
2. 根据 `adb_config` 建立 ADB 连接（如需）：`local` 不连接；`direct` 使用 `ADBConnection.connect`；`ssh_tunnel` SHALL 建立 SSH 本地转发并成功 `adb connect` 至转发端口后再继续
3. 构造 `ModelConfig` 和 `AgentConfig`；当任务已通过 `direct` 或 `ssh_tunnel` 获得连接地址时，`AgentConfig.device_id` SHALL 设为该地址（与后续 `disconnect` 使用同一字符串）
4. 创建 `PhoneAgent` 实例
5. 如有 `context_history`，通过 `set_context()` 注入
6. 调用 `agent.run_as_dict(instruction)` 获取结构化结果
7. 更新任务状态为 `completed` 并存储结果
8. 清理 ADB 连接（如需）；若存在 SSH 隧道，SHALL 在断开 ADB 后关闭隧道

#### Scenario: 带 ADB 配置的任务执行

- **WHEN** 任务包含 `adb_config: {"type": "direct", "params": {"address": "10.0.0.1:5555"}}`
- **THEN** 执行线程 SHALL 先调用 `ADBConnection.connect("10.0.0.1:5555")`，执行 Agent 任务，完成后调用 `ADBConnection.disconnect("10.0.0.1:5555")`

#### Scenario: 执行异常处理

- **WHEN** Agent 执行过程中抛出异常
- **THEN** 执行线程 SHALL 捕获异常、更新状态为 `failed`、清理 ADB 连接，并构造包含错误信息的结果

### Requirement: ADB 连接生命周期管理

执行线程 SHALL 在任务开始前根据 `adb_config` 建立连接，在任务结束后（无论成功或失败）清理连接。`direct` 类型的 TCP 连接建立与断开 SHALL 通过 `phone_agent.adb.connection.ADBConnection` 完成。`ssh_tunnel` 类型 SHALL 使用 `app/core/adb_ssh_tunnel.py`（或等价实现）建立 SSH 隧道并在隧道本地端口上完成 `ADBConnection.connect`；任务结束后 SHALL 先 `ADBConnection.disconnect` 所使用的地址，再关闭 SSH 隧道。

`local` 类型 SHALL 不做连接操作。`direct` 类型 SHALL 调用 `ADBConnection.connect(params["address"])`。

#### Scenario: local 类型无额外连接

- **WHEN** `adb_config.type` 为 `"local"` 或 `adb_config` 为 None
- **THEN** 执行线程 SHALL 不调用任何 ADB 连接/断开操作

#### Scenario: direct 连接与清理

- **WHEN** `adb_config.type` 为 `"direct"` 且 `params.address` 为 `"192.168.1.100:5555"`
- **THEN** 任务开始前 SHALL 调用 `ADBConnection.connect("192.168.1.100:5555")`
- **THEN** 任务结束后 SHALL 调用 `ADBConnection.disconnect("192.168.1.100:5555")`（在 finally 块中）

#### Scenario: ssh_tunnel 连接与清理

- **WHEN** `adb_config.type` 为 `"ssh_tunnel"` 且参数满足实现要求，隧道建立成功且 `adb connect` 成功
- **THEN** 任务开始前 SHALL 存在指向远端 ADB 的 SSH 本地转发，且 `PhoneAgent` SHALL 使用与该 `adb connect` 一致的 `device_id`
- **THEN** 任务结束后（含异常路径）SHALL 在 finally 中先对该 `device_id` 调用 `ADBConnection.disconnect`，再执行隧道关闭逻辑，确保无残留转发
