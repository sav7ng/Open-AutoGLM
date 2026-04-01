## MODIFIED Requirements

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

## ADDED Requirements

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
