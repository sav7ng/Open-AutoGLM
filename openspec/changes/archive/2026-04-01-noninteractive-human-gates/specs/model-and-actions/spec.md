# Model Client and Actions — Delta

## MODIFIED Requirements

### Requirement: 敏感操作与接管

`Take_over` SHALL 在**交互模式**下触发 `takeover_callback`（与实现一致：默认可为控制台阻塞实现）。**非交互模式**下 SHALL **不**调用 `takeover_callback`；SHALL 返回 `ActionResult`，使 Agent 结束本任务，且结束消息 SHALL 取自该动作 `message` 字段；若缺失 SHALL 使用与实现一致的默认字符串（与交互路径下 `Take_over` 所用默认一致）。

需要确认的敏感操作（当前实现为带 `message` 的 `Tap`，与 `handler` 一致）在**交互模式**下 SHALL 在继续前调用 `confirmation_callback`；若返回 False，SHALL 中止该动作并返回相应 `ActionResult`。在**非交互模式**下 SHALL **不**调用 `confirmation_callback`、SHALL **不**执行点击；SHALL 返回 `ActionResult`，使 Agent 结束本任务，结束消息 SHALL 取自该动作 `message` 字段（缺失时同上默认）。

交互模式与非交互模式由运行时传入 `ActionHandler` / `IOSActionHandler` 的配置区分（与 agent-runtime spec 中的 `interactive_human` 对齐）；默认 SHALL 为交互模式，与历史行为一致。

#### Scenario: 交互模式下用户拒绝敏感确认

- **GIVEN** `interactive_human` 为 True（默认）且 `confirmation_callback` 返回 False
- **WHEN** 执行需确认的敏感 `Tap`
- **THEN** `ActionResult` SHALL 反映未执行且不应视为成功完成，且 SHALL 结束任务（与当前实现一致）

#### Scenario: 非交互模式下 Take_over

- **GIVEN** `interactive_human` 为 False
- **WHEN** 执行 `Take_over` 且动作含 `message="需要登录"`
- **THEN** SHALL **不**调用 `takeover_callback`；Agent SHALL 结束任务；返回给用户/上层的结束消息 SHALL 为 `需要登录`（或实现默认 fallback）

#### Scenario: 非交互模式下敏感 Tap

- **GIVEN** `interactive_human` 为 False
- **WHEN** 执行带 `message` 的敏感 `Tap`
- **THEN** SHALL **不**调用 `confirmation_callback`；SHALL **不**执行点击；Agent SHALL 结束任务；结束消息 SHALL 为该动作 `message` 字段（或默认 fallback）

#### Scenario: 交互模式下 Take_over 仍调用接管回调

- **GIVEN** `interactive_human` 为 True 且调用方注入 `takeover_callback`
- **WHEN** 执行 `Take_over`
- **THEN** SHALL 调用 `takeover_callback`（行为与变更前一致）
