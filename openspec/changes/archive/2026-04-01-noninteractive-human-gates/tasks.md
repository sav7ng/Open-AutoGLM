## 1. 配置与 Handler（Android / HarmonyOS）

- [x] 1.1 在 `AgentConfig` 增加 `interactive_human: bool = True`，并传入 `ActionHandler` 新参数（语义与 design 一致）。
- [x] 1.2 在 `ActionHandler.__init__` 接收 `interactive_human`；在 `_handle_takeover` 中：若 `interactive_human` 为 False，不调用 `takeover_callback`，返回 `ActionResult(success=True, should_finish=True, message=...)`，`message` 取自 `action["message"]` 及现有默认 fallback。
- [x] 1.3 在 `_handle_tap` 中：若带 `message` 且 `interactive_human` 为 False，不调用 `confirmation_callback`、不执行点击，返回 `ActionResult(success=False, should_finish=True, message=...)`，message 取自 `action["message"]` 及与 1.2 一致的缺失策略。

## 2. Handler（iOS）

- [x] 2.1 在 `IOSAgentConfig` 增加 `interactive_human: bool = True`，并传入 `IOSActionHandler`。
- [x] 2.2 在 `IOSActionHandler` 中实现与 1.2、1.3 对称的 `Take_over` 与敏感 `Tap` 分支。

## 3. Agent 组装与 App

- [x] 3.1 `PhoneAgent` / `IOSPhoneAgent` 构造时将 `agent_config.interactive_human` 传入对应 `ActionHandler`。
- [x] 3.2 `app/core/executor.py` 创建 `AgentConfig` 时设置 `interactive_human=False`（或与 design 一致的等价方式）。
- [x] 3.3 检查 `main.py` / CLI 默认仍为交互模式（`interactive_human=True`），必要时显式传入。

## 4. 文档与规格落地

- [x] 4.1 更新 README / README_en 中关于回调与 `Take_over` 的说明，提及 `interactive_human` 与 executor 默认行为。
- [x] 4.2 实现完成后将 `openspec/specs/agent-runtime/spec.md` 与 `openspec/specs/model-and-actions/spec.md` 按 delta 合并归档（随 OpenSpec archive 流程）。

## 5. 验证

- [x] 5.1 手动或脚本验证：`interactive_human=False` 时 `Take_over` 与敏感 Tap 均结束任务且 message 符合 spec；`True` 时行为与变更前一致。
- [x] 5.2 确认无回归：`finish`、普通 Tap、步数上限路径仍正常。
