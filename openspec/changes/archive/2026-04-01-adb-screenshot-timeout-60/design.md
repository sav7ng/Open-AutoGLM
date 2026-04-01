## Context

- `phone_agent/adb/screenshot.py` 中 `get_screenshot(..., timeout: int = 10)`：`subprocess.run` 对 `adb shell screencap` 使用 `timeout`，对 `adb pull` 固定 `timeout=5`。
- `PhoneAgent` 经 `DeviceFactory.get_screenshot(device_id)` 调用，factory 默认 `timeout=10` 会原样传给各平台 `get_screenshot`，因此仅改 ADB 模块默认值而**不改 factory** 时，Agent 仍传 10。
- Harmony `hdc/screenshot.py` 结构类似：截图命令用 `timeout`，`hdc file recv` 固定 5 秒。

## Goals / Non-Goals

**Goals:**

- Android ADB 截图在默认配置下为慢设备留出至多约 60 秒的完成时间。
- `pull`/`recv` 与主截图命令共享同一 `timeout`，避免第一步成功、第二步因 5 秒过短失败。
- 经 `DeviceFactory` 且未传 `timeout` 的调用（含 `PhoneAgent`）在 Android 上实际获得 60 秒行为。

**Non-Goals:**

- 引入新的环境变量或 YAML 配置层（若后续需要可另起变更）。
- 修改 iOS `xctest` 截图超时（本变更聚焦 ADB；iOS 仍走独立实现）。
- 改变 `get_screenshot` 的函数签名或 `Screenshot` 数据结构。

## Decisions

1. **ADB 默认 `timeout=60`**  
   - **理由**：与用户诉求一致，且文档化在变更规格 `adb-screenshot` 中。  
   - **备选**：仅调大 `screencap`、pull 仍 5s —— 已否决，易产生隐蔽失败。

2. **`adb pull` 使用与参数相同的 `timeout`**  
   - **理由**：单一参数、行为可预测；自定义 `timeout` 时两段一致。  
   - **备选**：pull 用 `min(timeout, 30)` —— 增加心智负担，未采用。

3. **`DeviceFactory.get_screenshot` 默认 `timeout` 改为 60**  
   - **理由**：否则 Agent 单参调用仍传 10，无法达到「运行时默认 60」目标。  
   - **备选**：在 `agent.py` 硬编码 60 —— 侵入业务层，不如在 factory 统一默认。

4. **Harmony HDC：默认 `timeout=60`，`file recv` 使用同一 `timeout`**  
   - **理由**：与 factory 新默认对齐，避免 Harmony 仍被 10s/5s 卡住而 Android 已放宽，减少平台差异。  
   - **备选**：仅改 ADB —— 保留为 rollback 时可行，但当前选择一并调整 HDC 以保持一致。

## Risks / Trade-offs

- **[风险] 单次截图最坏等待变长** → 真卡住时线程阻塞更久；可接受，因慢设备下原 10s 误失败成本更高。  
- **[风险] 自动化测试若依赖快速失败** → 测试应显式传入较小 `timeout`。  
- **[权衡] Factory 默认影响所有平台模块** → iOS 不经过该 `get_screenshot`，仅 ADB/HDC 受益，副作用可控。

## Migration Plan

- 无数据迁移；升级后默认行为变更。  
- **回滚**：将默认值与 `pull`/`recv` 超时恢复为变更前提交。

## Open Questions

- 无。若产品要求「仅 Android、Harmony 保持 10s」，可在实现阶段从 tasks 中去掉 HDC 相关条目并更新本 design 决策 4。
