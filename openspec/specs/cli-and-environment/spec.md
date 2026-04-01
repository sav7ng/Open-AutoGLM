# CLI and Environment

## Purpose

描述 `main.py` 命令行接口与环境变量约定，与当前 `parse_args()` 及文档字符串中的 `PHONE_AGENT_*` 说明一致。

## Requirements

### Requirement: 模型相关参数与环境变量

系统 SHALL 支持以下 CLI 选项，且默认值 SHALL 可从对应环境变量读取（与 `main.py` 一致）：

| CLI | 环境变量 | 说明 |
|-----|----------|------|
| `--base-url` | `PHONE_AGENT_BASE_URL` | 模型 API base URL，默认 `http://localhost:8000/v1` |
| `--model` | `PHONE_AGENT_MODEL` | 模型名，默认 `autoglm-phone-9b` |
| `--apikey` | `PHONE_AGENT_API_KEY` | API Key，默认 `EMPTY` |
| `--max-steps` | `PHONE_AGENT_MAX_STEPS` | 每任务最大步数，默认 `100` |

#### Scenario: 仅通过环境变量配置模型

- **GIVEN** 用户设置 `PHONE_AGENT_BASE_URL` 与 `PHONE_AGENT_MODEL`
- **WHEN** 执行 `python main.py "某任务"` 且未传对应 CLI 覆盖
- **THEN** `ModelConfig` 所使用的 base_url 与 model_name SHALL 来自上述环境变量

### Requirement: 设备与连接参数

系统 SHALL 支持：

- `--device-id` / `-d`，默认 `PHONE_AGENT_DEVICE_ID`（未设置则为无默认值由实现处理）
- `--connect` / `-c`：远程设备地址（如 `ip:port`）
- `--disconnect`：断开远程或 `all`
- `--list-devices`：列出已连接设备并退出
- `--enable-tcpip`：在 USB 设备上启用 TCP/IP 调试
- `--device-type`：`adb` | `hdc` | `ios`，默认 `PHONE_AGENT_DEVICE_TYPE` 或 `adb`

#### Scenario: 多设备 ADB

- **GIVEN** 多台设备已连接
- **WHEN** 用户传入 `--device-id emulator-5554`
- **THEN** 设备工厂与 `ActionHandler` 使用的 `device_id` SHALL 对应该串

### Requirement: iOS 专用参数

当 `--device-type ios` 时，系统 SHALL 支持：

- `--wda-url`：默认 `PHONE_AGENT_WDA_URL` 或 `http://localhost:8100`
- `--pair`：与设备配对
- `--wda-status`：打印 WDA 状态并退出

#### Scenario: WiFi 上的 WDA

- **GIVEN** 用户执行 `python main.py --device-type ios --wda-url http://192.168.1.100:8100 ...`
- **WHEN** 创建 `IOSAgentConfig`
- **THEN** `wda_url` SHALL 与 CLI 一致并用于 `XCTestConnection`

### Requirement: 语言与其它开关

系统 SHALL 支持 `--lang`，取值为 `cn` 或 `en`，默认 `PHONE_AGENT_LANG` 或 `cn`，用于系统提示与 UI 文案（`phone_agent.config`）。系统 SHALL 支持 `--quiet` / `-q` 抑制详细输出；`--list-apps` SHALL 列出当前设备类型下的支持应用并退出。

#### Scenario: 英文系统提示

- **GIVEN** 用户传入 `--lang en`
- **WHEN** 构造 `AgentConfig` / `IOSAgentConfig`
- **THEN** `lang` 字段 SHALL 为 `en` 且 `get_system_prompt` 使用英文模板

### Requirement: 任务参数与交互模式

位置参数 `task` SHALL 为可选：若省略，实现 SHALL 进入交互模式（与 `main.py` 当前行为一致）。

#### Scenario: 单次非交互任务

- **GIVEN** 用户执行 `python main.py "打开微信"`
- **WHEN** 参数解析完成
- **THEN** `args.task` SHALL 为非空并作为 Agent 任务描述传入
