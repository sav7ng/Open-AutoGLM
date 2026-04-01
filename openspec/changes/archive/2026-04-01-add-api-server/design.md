## Context

Open-AutoGLM 当前仅通过 `main.py` CLI 入口驱动 `PhoneAgent`，完整流程为：argparse → 环境检查 → 构造 ModelConfig/AgentConfig → `PhoneAgent.run(task)` → 结束消息字符串。

上层项目 AgentDroid 已实现了一套成熟的 HTTP API 模式：`AgentRequest` → 线程池异步执行 → 内存任务管理 → 回调通知。本次需要在 Open-AutoGLM 内部复刻该模式，保持接口契约一致，使调用方无缝切换。

关键约束：
- `PhoneAgent.run()` 当前返回字符串，需适配为结构化 dict
- `DeviceFactory` 是全局单例，并发任务需要线程安全保护
- 现有 CLI 入口和 `phone_agent` 包不应受到破坏性修改

## Goals / Non-Goals

**Goals:**
- 提供与 AgentDroid `/run-agent-async` 完全一致的 `AgentRequest` 入参和响应结构
- 支持异步任务提交、状态查询、取消
- 支持 `callback_url` 完成回调（含重试）
- 支持 `adb_config` 远程 ADB 连接（local/direct）
- 支持 `context_history` 多轮上下文注入
- 保持 CLI 入口 `main.py` 不受影响

**Non-Goals:**
- 不实现流式端点 `/run-agent-stream`（后续迭代）
- 不实现同步端点 `/run-agent`（后续迭代）
- 不实现 SSH 隧道 ADB 连接（仅 local 和 direct）
- 不实现持久化任务存储（仅内存）
- 不支持 iOS agent 通过 API 调用（首期仅 Android/HarmonyOS）
- 不实现认证/鉴权（由上层网关处理）

## Decisions

### Decision 1: 服务层目录结构 — 新增 `app/` 顶层目录

**选择**：在仓库根目录新增 `app/` 目录，放置 FastAPI 应用、路由、服务层、核心模块。`server.py` 作为启动入口。

**替代方案**：
- A) 放在 `phone_agent/server/` 内 — 会把 HTTP 耦合进核心包，违反现有 architecture spec 的分层意图
- B) 独立仓库 — 增加维护成本，且 proposal 要求在本仓库内完成

**理由**：`app/` 与 `phone_agent/` 平行，保持核心包纯净。`server.py` 在根目录与 `main.py` 对称，分别对应 HTTP 和 CLI 两种入口。

### Decision 2: 线程池执行 Agent — 与 AgentDroid 一致的独立线程模型

**选择**：使用 `concurrent.futures.ThreadPoolExecutor` 在独立线程中执行 `PhoneAgent.run()`，FastAPI 端点立即返回 `task_id`。

**替代方案**：
- A) asyncio 原生协程 — `PhoneAgent` 内部大量同步 ADB 调用（`subprocess.run`），无法直接 await
- B) 进程池 — 隔离更彻底但开销大，进程间传输截图数据成本高

**理由**：AgentDroid 验证过此模式可靠，ADB 命令的阻塞在线程中不影响事件循环。线程池 max_workers 默认 10（单台设备通常不会并发太多任务）。

### Decision 3: DeviceFactory 并发保护 — 线程锁 + device_id 隔离

**选择**：在 API 服务层，每个任务执行前通过 `threading.Lock` 保护 `set_device_type()` 和 `DeviceFactory` 的全局状态设置，然后在 `AgentConfig` 中传入 `device_id` 确保各任务操作正确的设备。

**替代方案**：
- A) 每任务 fork 子进程 — 完全隔离但性能差
- B) 改造 DeviceFactory 为非全局 — 侵入核心包过深

**理由**：ADB 命令通过 `-s <device_id>` 天然支持多设备并发。全局状态的竞争点仅在 `set_device_type` 阶段，锁范围极小。首期主要场景为单设备，锁竞争可忽略。

### Decision 4: PhoneAgent.run() 返回值适配 — 新增 `run_as_dict()` 方法

**选择**：在 `PhoneAgent` 中新增 `run_as_dict(task)` 方法，包装 `run()` 并返回结构化 dict（`status`、`message`、`history`、`steps_taken`）。保持原 `run()` 签名不变。

**替代方案**：
- A) 直接修改 `run()` 返回 dict — 破坏已有 CLI 和 examples 的调用方
- B) 在服务层包装 — 无法获取 agent 内部的 context/step 信息

**理由**：`run_as_dict()` 可访问 `self._context`、`self.step_count` 等内部状态，构造完整的结果 dict。CLI 代码完全不受影响。

### Decision 5: ADB 配置桥接 — 复用现有 ADBConnection

**选择**：在服务层根据 `adb_config.type` 分发：
- `local`：不做额外操作，使用本地已连接设备
- `direct`：调用 `ADBConnection.connect(address)` 建立连接，任务结束后 `disconnect`

**替代方案**：
- A) 移植 AgentDroid 的 `AdbConnectorFactory` — 引入 SSH 隧道等复杂度，首期不需要

**理由**：Open-AutoGLM 已有完善的 `ADBConnection` 类，直接复用即可。`direct` 模式覆盖云手机远程调试的核心场景。

### Decision 6: context_history 注入 — 通过 PhoneAgent 新增 setter

**选择**：在 `PhoneAgent` 中新增 `set_context(history: list)` 方法，在 `run()` 调用前注入外部上下文。`run()` 内部的 `reset()` 逻辑需要判断是否保留注入的上下文。

**理由**：最小侵入。如果 `context_history` 为空则走原有逻辑，有值则跳过 reset 直接续接。

## Risks / Trade-offs

- **[全局 DeviceFactory 竞态]** → 通过线程锁保护 `set_device_type` 调用；首期限制并发为单设备模式，后续可扩展为 device_id → factory 映射表。
- **[ADB 进程并发]** → 同一设备上的 ADB 命令（截图、输入）不支持并发 → 任务级别保证同一 device_id 不会被多任务同时操控（任务管理层检查）。
- **[内存任务状态]** → 服务重启后任务记录丢失 → 首期可接受，任务本身是短生命周期（分钟级）。
- **[回调失败]** → 网络不通或对端宕机导致回调丢失 → 5 次指数退避重试；调用方可通过 `/task-status/{task_id}` 主动轮询兜底。
- **[phone_agent 侵入]** → 新增 `run_as_dict()` 和 `set_context()` 属于 API 扩展而非行为变更，对现有代码无副作用。
