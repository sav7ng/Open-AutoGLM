# Architecture

## Purpose

描述 Open-AutoGLM（Phone Agent CLI）的代码布局、设备抽象与多平台实现分工，与当前仓库目录及 `main.py` / `phone_agent/` 行为一致，便于导航与变更影响分析。

## Requirements

### Requirement: 可执行入口与分发包

系统 SHALL 通过根目录 `main.py` 提供 CLI；`setup.py` SHALL 注册控制台入口 `phone-agent` 指向 `main:main`。Python 版本要求 SHALL 与 `setup.py` 中 `python_requires` 一致（当前为 `>=3.10`）。

#### Scenario: 从源码运行

- **GIVEN** 开发者在仓库根目录执行 `python main.py`
- **WHEN** 解析参数并完成可选的系统检查
- **THEN** 根据 `--device-type` 与任务参数进入 Android / HarmonyOS / iOS 对应执行路径或辅助子命令

### Requirement: 核心包职责

`phone_agent` 包 SHALL 导出 `PhoneAgent` 与 `IOSPhoneAgent`（见 `phone_agent/__init__.py`）。编排逻辑 SHALL 位于 `phone_agent/agent.py`（Android/HarmonyOS 经设备工厂）与 `phone_agent/agent_ios.py`（iOS 经 WDA / XCTest）。

#### Scenario: 按平台定位 Agent 实现

- **GIVEN** 维护者需要修改「一步循环」或上下文构建
- **WHEN** 目标为 ADB/HDC 路径
- **THEN** 主要查阅 `phone_agent/agent.py`
- **WHEN** 目标为 iOS
- **THEN** 主要查阅 `phone_agent/agent_ios.py`

### Requirement: 设备类型与实现模块映射

系统 SHALL 使用 `phone_agent/device_factory.py` 中的 `DeviceType` 枚举：`ADB`、`HDC`、`IOS`。全局工厂 SHALL 通过 `set_device_type` / `get_device_factory` 访问；`DeviceType.ADB` 与 `DeviceType.HDC` SHALL 分别懒加载 `phone_agent.adb` 与 `phone_agent.hdc` 子包。`DeviceType.IOS` SHALL 不通过该工厂的 `module` 属性走 ADB/HDC 实现（iOS 使用 `phone_agent.xctest` 与独立 Agent）。

#### Scenario: CLI 选择 HDC

- **GIVEN** 用户指定 `--device-type hdc`
- **WHEN** `main.py` 调用 `set_device_type(DeviceType.HDC)`
- **THEN** `get_device_factory()` 返回的工厂 SHALL 将截图、输入、应用启动等委托给 `phone_agent.hdc`

### Requirement: 分层目录约定

代码组织 SHALL 遵循以下映射（核心路径）：

| 路径 | 职责 |
|------|------|
| `main.py` | CLI、环境检查、参数解析、任务启动 |
| `server.py` | HTTP 服务启动入口（uvicorn） |
| `app/main.py` | FastAPI 应用创建与中间件配置 |
| `app/models/schemas.py` | API 请求/响应 Pydantic 模型 |
| `app/api/v1/endpoints/agent.py` | Agent HTTP 端点（/run-agent-async 等） |
| `app/api/v1/endpoints/tasks.py` | 任务查询/取消端点 |
| `app/api/v1/api.py` | 路由注册 |
| `app/services/agent_service.py` | Agent 业务编排层 |
| `app/core/executor.py` | 线程池执行器与回调机制 |
| `app/core/task_manager.py` | 内存任务状态管理 |
| `phone_agent/agent.py` | `PhoneAgent`、基于设备工厂的观察-行动循环 |
| `phone_agent/agent_ios.py` | `IOSPhoneAgent`、WDA 会话与 `IOSActionHandler` |
| `phone_agent/model/` | OpenAI 兼容多模态客户端与 `MessageBuilder` |
| `phone_agent/actions/` | 模型输出解析与 `ActionHandler` / `IOSActionHandler` |
| `phone_agent/adb/` | Android 连接、截图、输入 |
| `phone_agent/hdc/` | HarmonyOS 连接、截图、输入 |
| `phone_agent/xctest/` | iOS 侧截图、会话与 WDA 通信 |
| `phone_agent/config/` | 多语言文案、系统提示词、应用列表、时序配置 |
| `docs/`、`examples/`、`scripts/` | 文档、示例与脚本 |

#### Scenario: 修改截图链路

- **GIVEN** 变更仅影响 Android 截图格式或获取方式
- **WHEN** 开发者从 `phone_agent/adb/screenshot.py` 或 adb 包内同类模块入手
- **THEN** 无需修改 `phone_agent/agent.py` 中「调用 `device_factory.get_screenshot`」的契约（除非接口签名变更）

#### Scenario: 定位 API 服务层代码

- **GIVEN** 维护者需要修改 HTTP 端点或请求模型
- **WHEN** 目标为 API 层
- **THEN** 主要查阅 `app/` 目录，无需修改 `phone_agent/` 核心包

### Requirement: 与 HTTP 服务无关的边界

本仓库 SHALL 将 FastAPI/ASGI 应用作为可选的服务入口（`server.py` + `app/`），但 SHALL 不将其作为 Phone Agent 运行时的必需组件。`phone_agent` 包 SHALL 保持独立可用，无需 FastAPI 依赖即可通过 CLI 或编程方式调用。模型访问 SHALL 通过 `openai` 库的 `OpenAI` 客户端指向用户配置的 `base_url`。

#### Scenario: 纯 CLI 部署

- **GIVEN** 仅安装 `phone_agent` 与核心依赖（Pillow、openai）并配置模型端点
- **WHEN** 不安装 fastapi/uvicorn，不启动 HTTP 服务
- **THEN** CLI（`python main.py`）仍 SHALL 完成设备自动化任务

#### Scenario: HTTP 服务部署

- **GIVEN** 安装完整依赖（含 fastapi、uvicorn、requests）
- **WHEN** 用户执行 `python server.py`
- **THEN** 系统 SHALL 提供 HTTP API 入口并通过 `phone_agent` 包执行任务
