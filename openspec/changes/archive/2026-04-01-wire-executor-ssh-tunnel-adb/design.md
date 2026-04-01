## Context

- `app/core/adb_ssh_tunnel.py` 已实现 `setup_ssh_tunnel_and_adb(task_id, params) -> (adb_address, cleanup)`：启动 `SSHTunnelForwarder`、本地动态端口、`ADBConnection().connect(address)`，并返回用于关闭隧道的 `cleanup` 回调。
- `app/core/executor.py` 中 `_setup_adb_connection` 仅处理 `direct`，`ssh_tunnel` 与 `local` 一样返回 `None`；`_extract_device_id` 亦未为 `ssh_tunnel` 填充 `AgentConfig.device_id`。
- 现象：请求带 `ssh_tunnel` 时容器内无 `adb connect`，首步 `get_current_app` 等易失败，表现为立即 `error` 且无真实触控。

## Goals / Non-Goals

**Goals:**

- `adb_config.type == "ssh_tunnel"` 时，执行线程在运行 Agent 前完成隧道 + `adb connect`，并将 `device_id` 设为与 `disconnect` 一致的地址字符串。
- 任务结束（成功、失败、取消路径）时：先 `ADBConnection.disconnect(adb_address)`（与现有 `direct` 一致），再调用隧道 `cleanup`，避免泄漏转发进程。
- 隧道或 `adb connect` 失败时向上抛出明确异常，由现有 executor 错误处理与回调承载，而非静默跳过。
- 规范与依赖（`sshtunnel`）与实现一致，便于 Docker 构建与排障。

**Non-Goals:**

- 不改变 OpenAI/模型协议与 `PhoneAgent` 循环语义。
- 不解决「多任务共享全局 `DeviceFactory`」的深层并发模型问题（仅延续现有 `threading.Lock` 与每任务 `device_id` 约定）。
- 不规定调用方 SSH 密钥/密码的具体格式校验（沿用 `adb_ssh_tunnel.py` 与 `sshtunnel` 行为）；文档中可提示密码与密钥路径字段的适用场景。

## Decisions

1. **在 executor 内聚合「地址 + 隧道清理」**  
   - **做法**：扩展 `_setup_adb_connection`（或引入小助手）使 `ssh_tunnel` 返回需 `disconnect` 的 `adb_address`，并在执行器作用域保存 `tunnel_cleanup: Optional[Callable]`；`finally` 中先 `disconnect` 再 `cleanup()`。  
   - **备选**：把隧道对象挂到 `ADBConnection` 上——与当前 `ADBConnection` 静态/实例职责混杂，不推荐。

2. **`device_id` 与 `adb_address` 相同**  
   - 隧道成功后地址形如 `127.0.0.1:<port>`；`AgentConfig.device_id` 与该字符串一致，保证 `adb -s` 与 `disconnect` 使用同一标识。  
   - **备选**：仅用环境变量或全局默认设备——与多任务、并发不符。

3. **依赖 `sshtunnel`**  
   - `setup_ssh_tunnel_and_adb` 已在缺包时抛出清晰 `RuntimeError`；将 `sshtunnel` 列入 `requirements.txt`（及 Dockerfile `pip install` 若独立维护），避免镜像内 ImportError。

4. **日志**  
   - 延续现有脱敏：`adb_ssh_tunnel` 已用 `mask_adb_address_for_log`；executor 在「ADB 就绪」日志中应能区分 `direct` / `ssh_tunnel`（可记录 `type`，不记录密码/密钥内容）。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 容器无法访问公网/内网 SSH 端口 | 部署文档说明网络出站要求；错误信息保留 SSH/ADB 失败原因 |
| 每任务一条隧道，并发多时 SSH 连接数上升 | 与现有多任务模型一致；后续可通过连接池或队列化单独变更 |
| `ssh_password` 与密钥材料误用 | 在 `http-api` 规范中说明 `ssh_private_key` 为文件路径、与 `sshtunnel` 参数对齐 |

## Migration Plan

- 合并后：重新构建镜像并安装含 `sshtunnel` 的依赖；现有仅 `local`/`direct` 的调用不受影响。
- 回滚：还原 executor 与依赖；`ssh_tunnel` 请求行为回到当前「不建连」状态（不推荐长期停留）。

## Open Questions

- Pydantic `AdbConnectionConfig` 是否在模型层为 `ssh_tunnel` 增加字段级校验（可选），或保持 `Dict[str, Any]` 由执行期报错即可（实现阶段权衡）。
