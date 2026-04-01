## 1. PhoneAgent 核心适配

- [x] 1.1 在 `phone_agent/agent.py` 的 `PhoneAgent` 中新增 `run_as_dict(task)` 方法，包装 `run()` 并返回结构化 dict（status/message/history/steps_taken）
- [x] 1.2 在 `phone_agent/agent.py` 的 `PhoneAgent` 中新增 `set_context(history)` 方法，支持注入外部对话上下文；修改 `run()` 使其在已注入上下文时跳过 reset
- [x] 1.3 在 `phone_agent/agent_ios.py` 的 `IOSPhoneAgent` 中同步新增 `run_as_dict()` 和 `set_context()` 方法

## 2. 数据模型

- [x] 2.1 创建 `app/models/__init__.py` 和 `app/models/schemas.py`，定义 `AdbConnectionConfig` 和 `AgentRequest` Pydantic 模型（字段与 AgentDroid 一致，`model_name` 默认值改为 `"autoglm-phone"`）

## 3. 任务管理

- [x] 3.1 创建 `app/core/__init__.py` 和 `app/core/task_manager.py`，实现内存任务状态表（TaskStatus 枚举、create_task_record、update_task_status、get_task_status、should_cancel_task、cancel_task），所有操作通过 threading.Lock 保护

## 4. 任务执行与回调

- [x] 4.1 创建 `app/core/executor.py`，实现 `execute_agent_task_sync()` 函数——在独立线程中完成 ADB 连接管理 → PhoneAgent 构造 → run_as_dict 执行 → 状态更新 → 回调发送 → 清理的完整流程
- [x] 4.2 在 `app/core/executor.py` 中实现 `send_callback_sync()` 函数——同步 HTTP POST 回调，含 5 次指数退避重试

## 5. 服务层

- [x] 5.1 创建 `app/services/__init__.py` 和 `app/services/agent_service.py`，实现 `run_agent_async(request)` 函数——验证 agent_type → 生成 task_id → 创建任务记录 → 提交线程池 → 返回 accepted 响应

## 6. API 端点

- [x] 6.1 创建 `app/api/__init__.py`、`app/api/v1/__init__.py`、`app/api/v1/api.py` 路由注册
- [x] 6.2 创建 `app/api/v1/endpoints/__init__.py` 和 `app/api/v1/endpoints/agent.py`，实现 `POST /run-agent-async` 端点
- [x] 6.3 创建 `app/api/v1/endpoints/tasks.py`，实现 `GET /task-status/{task_id}` 端点

## 7. FastAPI 应用与启动

- [x] 7.1 创建 `app/__init__.py` 和 `app/main.py`，创建 FastAPI 应用实例并注册路由
- [x] 7.2 创建 `server.py`（仓库根目录），通过 uvicorn 启动 FastAPI 应用，支持 `PHONE_AGENT_SERVER_PORT` 环境变量

## 8. 依赖与配置

- [x] 8.1 更新 `requirements.txt`，在 API 可选依赖区块中新增 `fastapi`、`uvicorn[standard]`、`requests`
