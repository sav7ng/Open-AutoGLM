# Agent Runtime

## Purpose

描述 `PhoneAgent` 与 `IOSPhoneAgent` 的运行时契约：配置类型、单步与整任务循环、上下文与结束条件，与 `phone_agent/agent.py`、`phone_agent/agent_ios.py` 对齐。

## Requirements

### Requirement: 配置类型

`AgentConfig`（`phone_agent/agent.py`）SHALL 包含：`max_steps`（默认 100）、`device_id`、`lang`（默认 `cn`）、`system_prompt`（默认由 `get_system_prompt(lang)` 填充）、`verbose`（默认 True）、`interactive_human`（默认 True，表示在需要人工接管或敏感确认时调用回调；为 False 时表示非交互模式，行为见 model-and-actions 中「敏感操作与接管」）。

`IOSAgentConfig`（`phone_agent/agent_ios.py`）SHALL 包含：`max_steps`、`wda_url`（默认 `http://localhost:8100`）、`session_id`、`device_id`（iOS UDID）、`lang`、`system_prompt`、`verbose`、`interactive_human`（默认 True）；若 `session_id` 为 None，Agent 构造时 SHALL 尝试通过 `XCTestConnection.start_wda_session()` 创建会话。

#### Scenario: 默认系统提示

- **GIVEN** 调用方未传 `system_prompt`
- **WHEN** 执行 `AgentConfig()` 或 `IOSAgentConfig()` 的 `__post_init__`
- **THEN** `system_prompt` SHALL 等于 `get_system_prompt(self.lang)`

#### Scenario: 默认交互模式

- **GIVEN** 调用方未显式设置 `interactive_human`
- **WHEN** 构造 `AgentConfig` 或 `IOSAgentConfig`
- **THEN** `interactive_human` SHALL 为 True

### Requirement: 核心依赖组装

`PhoneAgent.__init__` SHALL 创建 `ModelClient(model_config)` 与 `ActionHandler(device_id=agent_config.device_id, confirmation_callback=..., takeover_callback=..., interactive_human=agent_config.interactive_human, ...)`（参数名以实现为准，语义对齐）。`IOSPhoneAgent.__init__` SHALL 创建 `ModelClient`、`XCTestConnection(wda_url=...)` 与 `IOSActionHandler(..., interactive_human=agent_config.interactive_human, ...)`。

#### Scenario: 交互模式下回调注入

- **GIVEN** 调用方传入 `confirmation_callback` 与 `takeover_callback` 且 `interactive_human` 为 True
- **WHEN** 执行敏感操作或 `Take_over` 动作
- **THEN** SHALL 调用传入的回调而非仅使用控制台默认实现（与变更前一致）

#### Scenario: 非交互模式下人类门控

- **GIVEN** `interactive_human` 为 False
- **WHEN** 执行 `Take_over` 或需确认的敏感 `Tap`
- **THEN** SHALL **不**在上述路径调用 `takeover_callback` 或 `confirmation_callback`；任务结束语义与结束消息 SHALL 符合 model-and-actions「敏感操作与接管」

### Requirement: 观察-行动主循环

`PhoneAgent.run(task)` SHALL 重置上下文与步数；首先以用户任务与首屏截图调用 `_execute_step(..., is_first=True)`；随后在 `step_count < max_steps` 时重复 `_execute_step(..., is_first=False)` 直至 `finished` 或达到上限。返回值 SHALL 为结束消息字符串或 `"Max steps reached"`。

`PhoneAgent` SHALL 额外提供 `run_as_dict(task)` 方法，行为与 `run(task)` 一致但返回结构化 dict：

```python
{
    "status": "completed" | "max_steps_reached" | "error",
    "message": str,           # 结束消息
    "history": list[dict],    # agent._context 的副本
    "steps_taken": int,       # 实际执行步数
}
```

`IOSPhoneAgent.run` SHALL 遵循相同控制流，差异仅在截图与当前应用来源（xctest）及动作为 `IOSActionHandler`。`IOSPhoneAgent` SHALL 同样提供 `run_as_dict(task)` 方法。

#### Scenario: 第一步附带用户任务

- **GIVEN** `run("打开设置")` 且为首步
- **WHEN** 构建用户消息
- **THEN** 文本内容 SHALL 包含用户任务与当前应用等屏幕信息，图像 SHALL 为当前截图的 base64

#### Scenario: run_as_dict 返回结构化结果

- **GIVEN** 调用 `agent.run_as_dict("打开微信")`
- **WHEN** 任务正常完成
- **THEN** 返回 dict SHALL 包含 `status: "completed"`、`message`（结束消息）、`history`（上下文列表）、`steps_taken`

#### Scenario: run_as_dict 达到步数上限

- **GIVEN** 调用 `agent.run_as_dict(task)` 且执行达到 `max_steps`
- **WHEN** 循环结束
- **THEN** 返回 dict SHALL 包含 `status: "max_steps_reached"`、`message: "Max steps reached"`

### Requirement: 单步 API

`PhoneAgent.step(task | None)` / iOS 对等方法 SHALL：若上下文为空且未提供 `task`，抛出 `ValueError`；否则调用 `_execute_step` 并返回 `StepResult`（`success`、`finished`、`action`、`thinking`、`message`）。

#### Scenario: 调试逐步执行

- **GIVEN** 开发者先 `step("任务")` 再多次 `step()`
- **WHEN** 每步返回
- **THEN** `StepResult` SHALL 反映该步模型思考、解析后的动作与是否结束

### Requirement: 上下文与图像裁剪

每步在模型返回后，Agent SHALL 将最后一条用户消息中的图像通过 `MessageBuilder.remove_images_from_message` 移除后再追加助手消息；助手消息格式 SHALL 包含 `<redacted_thinking>...</redacted_thinking><answer>...</answer>` 包裹的模型输出片段。

#### Scenario: 控制上下文体积

- **GIVEN** 多步执行后查看 `agent.context`
- **WHEN** 检查历史中的用户消息
- **THEN** 已完成的步骤中用户侧消息 SHALL 不再包含内联截图（仅保留文本部分）

### Requirement: 结束判定

一步结束后 `finished` SHALL 在以下任一成立时为真：`action.get("_metadata") == "finish"`，或 `ActionResult.should_finish` 为真（含动作执行失败时降级为 `finish` 的路径，与实现一致）。iOS 路径 SHALL 使用 `IOSActionHandler` 的 `ActionResult` 语义对齐。

#### Scenario: 模型返回 finish

- **GIVEN** 解析后的动作 `_metadata` 为 `finish`
- **WHEN** 构造 `StepResult`
- **THEN** `finished` SHALL 为 True

### Requirement: 模型异常处理

若 `model_client.request` 抛错，Agent SHALL 返回 `StepResult(success=False, finished=True, message=含错误信息)`（在 `verbose` 下可打印栈）。

#### Scenario: 推理服务不可用

- **GIVEN** 网络或 API 错误
- **WHEN** `_execute_step` 捕获异常
- **THEN** 该步 SHALL 标记为失败并结束循环（`finished=True`）

### Requirement: 外部上下文注入

`PhoneAgent` SHALL 提供 `set_context(history: list[dict])` 方法，允许在调用 `run()` 或 `run_as_dict()` 前注入外部对话上下文。注入后，`run()` 内部 SHALL 跳过上下文重置（`self._context = []`），直接在已注入的上下文基础上继续执行。

`IOSPhoneAgent` SHALL 提供相同的 `set_context` 方法。

#### Scenario: 注入上下文后执行

- **GIVEN** 调用方先执行 `agent.set_context([{"role": "user", "content": "打开设置"}, {"role": "assistant", "content": "..."}])`
- **WHEN** 随后执行 `agent.run("继续下一步操作")`
- **THEN** Agent SHALL 在已注入的上下文基础上继续执行，而非从空白上下文开始

#### Scenario: 无上下文注入时保持原行为

- **GIVEN** 调用方未调用 `set_context()`
- **WHEN** 执行 `agent.run(task)`
- **THEN** Agent SHALL 按原有逻辑重置上下文并从零开始执行
