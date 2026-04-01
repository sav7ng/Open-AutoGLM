## Why

在慢设备、高负载或 `adb` 链路不稳定时，`screencap` 可能在 10 秒内未完成，导致 `subprocess` 超时并落入黑屏回退，Agent 误判为截图失败。将 ADB 截图相关默认超时提高到 60 秒，可减少误杀、与真实设备节奏更匹配。

## What Changes

- 将 Android ADB 路径下 `get_screenshot` 用于 **`adb shell screencap`** 的默认超时从 10 秒调整为 **60 秒**。
- 将同一路径中 **`adb pull`** 子进程的超时从硬编码 5 秒调整为与主超时一致或可推导的合理值（避免 screencap 成功但 pull 仍易超时）。
- （可选一致化）`DeviceFactory.get_screenshot` 的默认 `timeout` 与 ADB 实现默认对齐，使 `PhoneAgent` 等未显式传参的调用获得 60 秒行为；Harmony `hdc` 路径若当前共享同一默认，一并评估是否同步，避免平台间行为分叉过大。

## Capabilities

### New Capabilities

- `adb-screenshot`: 约定 Android ADB 截图辅助函数的默认超时与 `adb pull` 超时策略，与 `phone_agent/adb/screenshot.py` 对齐。

### Modified Capabilities

- （无）现有 baseline 规格未单独描述截图秒级超时；本变更通过新增 `adb-screenshot` 能力承载可测试需求，不修改其他能力文本。

## Impact

- **代码**: `phone_agent/adb/screenshot.py`；可能 `phone_agent/device_factory.py`；若采用跨平台默认一致，则 `phone_agent/hdc/screenshot.py`。
- **API**: `get_screenshot(..., timeout=...)` 签名不变，仅默认值与内部 `pull` 超时行为变化；对显式传入 `timeout` 的调用方无 **BREAKING** 变更。
- **行为**: 失败/卡住时等待更久才超时，单次截图最坏耗时上限提高。
