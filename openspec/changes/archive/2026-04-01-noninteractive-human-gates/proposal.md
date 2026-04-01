## Why

在无 stdin 或服务端线程中执行 Agent 时，默认的 `takeover_callback`（等待回车）与 `confirmation_callback`（交互式 Y/N）会阻塞任务；需要一种**非交互**模式：遇到 `Take_over` 或需确认的敏感 Tap 时，不等待用户，直接结束任务并返回模型在动作中提供的 `message`，敏感 Tap 不执行点击。

## What Changes

- 在 Agent / 动作层增加**非交互人类门控**配置（名称以实现为准，例如 `interactive_human` 或 `block_on_human_gate` 的反义），默认保持与当前 CLI 交互行为一致。
- **Take_over**：非交互模式下不调用 `takeover_callback`（或等价于不阻塞）；任务本步即结束，`run` / `run_as_dict` 返回的结束信息使用模型在 `Take_over` 中给出的 `message`。
- **敏感 Tap**（带 `message`、走 `confirmation_callback`）：非交互模式下不调用 `confirmation_callback`、不执行点击；任务结束，返回信息使用该次 Tap 动作中模型给出的 `message`（与 `Take_over` 对齐）。
- **交互模式**（默认）：`Take_over` 与敏感确认行为与现状一致（仍调用回调；`Take_over` 后是否继续多步保持现有语义，除非设计另有说明）。
- Android 与 iOS 的 `ActionHandler` / `IOSActionHandler` 行为对齐；`app` 侧执行器在创建 Agent 时采用非交互默认值（避免服务端挂起），若需可配置。

## Capabilities

### New Capabilities

- （无独立新能力域；行为归入现有 model-and-actions 与 agent-runtime。）

### Modified Capabilities

- `model-and-actions`：补充「非交互模式下 `Take_over` / 敏感 Tap 不阻塞、结束语义与返回 message 来源」的 SHALL 与场景。
- `agent-runtime`：补充 `AgentConfig`（及 iOS 侧等价配置若存在）中非交互门控字段及与 `ActionHandler` 组装的契约；补充 `executor` 或调用方默认策略的说明（若属于本变更范围）。

## Impact

- **代码**：`phone_agent/actions/handler.py`、`handler_ios.py`；`phone_agent/agent.py`、`agent_ios.py`；可能 `app/core/executor.py` 与 README 示例。
- **API**：`AgentConfig`（及构造参数）新增字段；**非默认**时行为变化，属可控破坏性需在发布说明中写明。
- **依赖**：无新第三方依赖。
