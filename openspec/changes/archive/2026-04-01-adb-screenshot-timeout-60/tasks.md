## 1. ADB 截图模块

- [x] 1.1 将 `phone_agent/adb/screenshot.py` 中 `get_screenshot` 的默认参数 `timeout` 从 `10` 改为 `60`，并更新 docstring 中的说明。
- [x] 1.2 将 `adb pull` 的 `subprocess.run` 中硬编码 `timeout=5` 改为使用与 `screencap` 相同的 `timeout` 变量。

## 2. DeviceFactory 默认超时

- [x] 2.1 将 `phone_agent/device_factory.py` 中 `get_screenshot` 的默认 `timeout` 从 `10` 改为 `60`，并更新 docstring（若存在）。

## 3. Harmony HDC 对齐（与设计决策 4 一致）

- [x] 3.1 将 `phone_agent/hdc/screenshot.py` 中 `get_screenshot` 默认 `timeout` 改为 `60`。
- [x] 3.2 将 `hdc file recv` 调用处的固定 `timeout=5` 改为使用同一 `timeout` 参数。

## 4. 验证

- [x] 4.1 手动或现有测试路径确认：`PhoneAgent` 在未传截图超时的情况下，ADB 链路 `screencap`/`pull` 均使用 60 秒默认（可通过临时日志或断点核对传入 `subprocess` 的 `timeout`）。
