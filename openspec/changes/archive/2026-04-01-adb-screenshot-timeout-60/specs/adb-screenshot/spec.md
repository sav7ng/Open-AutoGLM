# ADB 截图超时（变更增量）

## ADDED Requirements

### Requirement: 默认 screencap 子进程超时

`phone_agent.adb.screenshot.get_screenshot` 在未传入 `timeout` 参数时 SHALL 对 `adb shell screencap` 所执行的子进程使用 **60 秒**超时。

#### Scenario: 省略 timeout 的调用

- **WHEN** 调用方调用 `get_screenshot(device_id)` 或 `get_screenshot()` 且未传 `timeout`
- **THEN** `screencap` 对应的 `subprocess.run` SHALL 使用 `timeout=60`

### Requirement: pull 与 screencap 共用 timeout 参数

`get_screenshot` 中对设备文件拉取（`adb pull`）的子进程 SHALL 使用与 `screencap` **相同**的 `timeout` 值（含调用方传入值与默认值）。

#### Scenario: 使用默认值时 pull 与 screencap 一致

- **WHEN** 调用方使用默认 `timeout` 调用 `get_screenshot`
- **THEN** `adb pull` 子进程的 `timeout` SHALL 等于 `screencap` 子进程的 `timeout`（均为 60）

#### Scenario: 调用方传入自定义 timeout

- **WHEN** 调用方调用 `get_screenshot(device_id="任意", timeout=120)`
- **THEN** `screencap` 与 `adb pull` 的子进程 SHALL 均使用 `timeout=120`
