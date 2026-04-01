## 1. 依赖与文档

- [x] 1.1 确认 `requirements.txt` 包含 `sshtunnel`（若缺失则添加）；若 `Dockerfile` 单独安装依赖则同步更新
- [x] 1.2 （可选）在面向部署的简短说明中注明：容器须能访问 `ssh_host:ssh_port`，`ssh_tunnel` 与 `direct` 的网络前提差异

## 2. Executor 接入 ssh_tunnel

- [x] 2.1 在 `app/core/executor.py` 的 `_setup_adb_connection` 中处理 `conn_type == "ssh_tunnel"`：调用 `setup_ssh_tunnel_and_adb(task_id, adb_config["params"])`，返回 `adb_address` 供 `disconnect` 使用
- [x] 2.2 在同一路径保存隧道 `cleanup` 回调（局部变量或小型结构体），确保与 `adb_address` 成对出现；`direct`/`local` 下无 cleanup
- [x] 2.3 扩展 `_cleanup_adb_connection`（或 `finally` 块）：先 `ADBConnection.disconnect(adb_address)`（当 `adb_address` 非空），再调用隧道 cleanup（若存在）；异常时记录 WARNING，不吞掉主流程已抛错误
- [x] 2.4 更新 `_extract_device_id`：`ssh_tunnel` 在成功建连后 SHALL 返回与 `adb connect` 相同的地址字符串（与 `_setup_adb_connection` 返回值一致）

## 3. 验证

- [x] 3.1 手工或集成测试：`adb_config.type=ssh_tunnel` 时日志中不再出现无连接的 `local/skipped` 占位（应出现脱敏后的本地转发地址）；任务可推进超过首步（在 SSH/ADB/模型均可用的前提下）
- [x] 3.2 失败路径：故意错误 SSH 参数时，任务 SHALL 失败并带有明确错误信息，且 `finally` 不泄漏隧道（无僵尸转发进程）

## 4. OpenSpec 归档准备（实现完成后）

- [x] 4.1 实现通过后，按仓库流程将本 change 的 delta specs 归档进 `openspec/specs/`，并归档 change 目录
