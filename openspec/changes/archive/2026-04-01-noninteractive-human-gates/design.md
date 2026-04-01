## Context

`ActionHandler` / `IOSActionHandler` 在 `Take_over` 上调用 `takeover_callback`，默认实现阻塞于 `input`；敏感 `Tap`（带 `message`）调用 `confirmation_callback`，默认阻塞于 Y/N。`app/core/executor.py` 创建 `PhoneAgent` 时未注入回调，服务端线程易永久挂起。需要显式**非交互**配置，并在该模式下以「结束任务 + 模型 message」替代阻塞。

## Goals / Non-Goals

**Goals:**

- 在 `AgentConfig` / `IOSAgentConfig` 上增加布尔配置（建议名 `interactive_human`，默认 `True`），并传入双端 `ActionHandler`。
- `interactive_human=False` 时：`Take_over` 不调用 `takeover_callback`，本步 `ActionResult` 使任务结束，结束 message 为动作中的 `message`；敏感 Tap 不调用 `confirmation_callback`、不执行点击，结束 message 为动作中的 `message`。
- `executor` 创建 Agent 时使用 `interactive_human=False`（或等价），避免默认挂起。
- Android 与 iOS handler 语义对齐。

**Non-Goals:**

- 不改变 `interactive_human=True` 时的既有回调签名与敏感拒绝时的英文固定文案（仍可与现实现一致）。
- 不新增第三方依赖；不改变 `parse_action` 与 DSL 语法。

## Decisions

1. **配置名 `interactive_human`（默认 `True`）**  
   - **理由**：`True` 与历史 CLI 交互行为一致，避免静默改变默认。  
   - **备选**：`non_interactive_mode` 默认 `False`——等价，但团队更倾向正向命名「是否交互」。

2. **非交互时结束 message 来源**  
   - **规则**：`Take_over` 与敏感 Tap 均使用**该次动作**中模型提供的 `message` 字段（缺省时使用实现约定的单一路径 fallback，与现 `Take_over` 默认字符串对齐）。  
   - **理由**：与前期产品共识一致；敏感 Tap 与 `Take_over` 对称。

3. **敏感 Tap 在非交互下的语义**  
   - **决策**：不执行点击，等同「拒绝」，`success` 与现 `confirmation_callback` 返回 False 时一致（`False`），`should_finish=True`。  
   - **理由**：安全默认，避免无确认执行敏感操作。

4. **`Take_over` 在非交互下**  
   - **决策**：`should_finish=True`，`success=True`（任务按「需人工但策略为立即结束」正常结束），message 为模型文案。  
   - **理由**：与「完成任务返回结果」一致；与敏感 Tap 的 success=False 区分因后者为「未执行敏感操作」。

5. **executor 默认**  
   - **决策**：服务端路径默认 `interactive_human=False`。  
   - **理由**：无 tty 时阻塞无意义；本地 CLI / examples 仍可默认 `True`。

## Risks / Trade-offs

- **[Risk] 调用方未读文档仍假设默认可交互** → **缓解**：默认 `True`；在 README / 变更说明中强调 executor 默认非交互。
- **[Risk] 模型未提供 `message` 时文案不一致** → **缓解**：与现实现共用 fallback（如 `"User intervention required"`）。
- **[Trade-off] `Take_over` 在非交互下不再调用自定义 `takeover_callback`** → 集成方若依赖回调做埋点，需在非交互模式下改用结束 message 或外层日志；可在后续 change 增加「仅通知回调」选项。

## Migration Plan

1. 发布说明：列出 `AgentConfig` / `IOSAgentConfig` 新字段及 `executor` 默认行为。
2. 若集成方依赖阻塞式接管，显式设置 `interactive_human=True` 并保留回调注入。
3. 无数据迁移；回滚即恢复旧代码路径。

## Open Questions

- CLI `main.py` 是否默认保持 `interactive_human=True`（建议：是）。
- iOS 测试覆盖是否与 Android 同等（任务中跟进）。
