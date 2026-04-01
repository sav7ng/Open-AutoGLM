## Why

API 请求已支持 `adb_config.type == "ssh_tunnel"`（与 AgentDroid 对齐），但执行器 `app/core/executor.py` 仅实现 `direct` 的 `ADBConnection.connect`；`ssh_tunnel` 被静默忽略，导致容器内无有效 ADB 目标，任务常在首步因设备侧命令失败而结束。仓库中已有 `app/core/adb_ssh_tunnel.py`（SSH 本地转发 + `adb connect`），未接入执行路径。需在契约与实现上补齐，使声明的 `ssh_tunnel` 配置真正生效。

## What Changes

- 在执行线程中，当 `adb_config.type == "ssh_tunnel"` 时，调用 `setup_ssh_tunnel_and_adb` 建立隧道并完成 `adb connect`；任务结束（含异常）时在 `finally` 中断开 ADB 并关闭 SSH 隧道。
- `PhoneAgent` 的 `AgentConfig.device_id` SHALL 设为隧道本地地址（如 `127.0.0.1:<动态端口>`），与 `ADBConnection.disconnect` 及现有 adb 子命令 `-s` 行为一致。
- 确认运行镜像/依赖包含 `sshtunnel`（若 `requirements.txt` 或 Docker 层尚未声明则补齐）。
- 更新规范：`AdbConnectionConfig` 文档化 `ssh_tunnel` 及 `params` 字段；任务执行规范中增加 `ssh_tunnel` 生命周期场景。

## Capabilities

### New Capabilities

（无；行为归属既有 HTTP API 与任务执行域。）

### Modified Capabilities

- `http-api`：`AdbConnectionConfig` 要求中补充 `type == "ssh_tunnel"` 及 `params`（`ssh_host`、`ssh_port`、`remote_adb_host`、`remote_adb_port`、认证相关字段）的说明与场景。
- `task-execution-and-callback`：在「ADB 连接生命周期」中增加 `ssh_tunnel`：建立隧道、`adb connect`、任务结束后 `disconnect` + 隧道清理；并增加对应 Scenario。

## Impact

- **代码**：`app/core/executor.py`（`_setup_adb_connection`、`_cleanup_adb_connection`、`_extract_device_id` 或等价结构）；可能微调 `app/core/adb_ssh_tunnel.py` 若需与 executor 清理语义对齐。
- **依赖**：`sshtunnel`（若未列入 `requirements.txt` / Dockerfile）。
- **行为**：`ssh_tunnel` 从「无操作」变为「真实建连」；失败时应有明确错误信息（隧道失败、`adb connect` 失败），而非静默跳过。
- **运维**：容器须能访问 `ssh_host:ssh_port`；远端 ADB 地址为 SSH 跳转机上的目标（与现有模块注释一致）。
