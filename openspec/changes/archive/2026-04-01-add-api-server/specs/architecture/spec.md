## MODIFIED Requirements

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
