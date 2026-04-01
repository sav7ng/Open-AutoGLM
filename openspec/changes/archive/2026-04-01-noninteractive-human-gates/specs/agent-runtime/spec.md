# Agent Runtime — Delta

## MODIFIED Requirements

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
- **THEN** SHALL **不**在上述路径调用 `takeover_callback` 或 `confirmation_callback`；任务结束语义与结束消息 SHALL 符合 model-and-actions delta「敏感操作与接管」
