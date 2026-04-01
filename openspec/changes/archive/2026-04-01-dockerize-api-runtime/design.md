## Context

Open-AutoGLM 已通过 `server.py` 提供 FastAPI 服务；生产与集成方需要可重复的 Linux 运行时，且 Phone Agent 依赖宿主机或网络上的 ADB。参考 AgentDroid 的多阶段镜像实践，本变更将交付物与运维假设写清，避免「能跑 demo、不能稳定部署」的落差。

## Goals / Non-Goals

**Goals:**

- 单一镜像内包含 API 进程所需 Python 依赖与常用运维工具（ADB 客户端、网络探测、SSH/隧道）。
- 镜像内预置 ADB 私钥路径，与标准 Android SDK/adb 期望一致。
- 健康检查可在编排系统中判断进程是否就绪。
- 构建上下文通过 `.dockerignore` 控制体积与缓存有效性。

**Non-Goals:**

- 不在镜像内捆绑 GPU 推理栈（vLLM/sglang 等仍由外部服务提供）。
- 不解决 USB 透传或特定云厂商的独占设备插件；仅约定容器内 CLI 能力与文件布局。
- 不修改 HTTP 或 Agent 的 Python API 契约。

## Decisions

1. **基础镜像 `python:3.11-slim`（Debian bookworm）**  
   - *理由*：与项目 Python 版本要求一致，体积小。  
   - *备选*：`ubuntu:*` 更大；`alpine` 与部分 wheel 兼容性差。

2. **多阶段构建：builder 安装依赖，runtime 仅复制 venv**  
   - *理由*：减小最终层中的编译链残留。  
   - *备选*：单阶段更简单但镜像更大。

3. **国内镜像源（清华 PyPI、USTC Debian）**  
   - *理由*：与 AgentDroid 一致，降低国内构建失败率。  
   - *备选*：默认官方源，由构建参数覆盖（未在本阶段强制）。

4. **运行时安装 `curl`、`android-tools-adb`、`iputils-ping`、`openssh-client`、`autossh`**  
   - *理由*：`curl` 用于 HEALTHCHECK 与调试；`adb` 与业务一致；`ping` 做连通性；`ssh`/`autossh` 支持通过隧道把远端或宿主的 adbd/adb 端口映射进容器，避免 Docker 化后无法管理连接。  
   - *备选*：仅 `adb` 无 SSH——无法满足「经 SSH 管理 ADB」的运维路径。

5. **`adbkey` 构建期复制到 `/root/.android/adbkey`，权限 600**  
   - *理由*：与 AgentDroid 及 adb 默认查找路径一致。  
   - *备选*：运行时 volume 挂载（更安全，适合公开发布镜像；可在运维文档中说明）。

6. **HEALTHCHECK 请求 `GET /openapi.json`（默认端口 8000）**  
   - *理由*：当前应用未提供专用 `/`，OpenAPI JSON 稳定可用。  
   - *权衡*：若运行时仅修改 `PHONE_AGENT_SERVER_PORT` 而非映射容器 8000，需同步调整 HEALTHCHECK 或改用固定内部端口的启动方式。

7. **启动命令 `python server.py`**  
   - *理由*：与现有入口及 `PHONE_AGENT_SERVER_HOST` / `PHONE_AGENT_SERVER_PORT` 一致。

## Risks / Trade-offs

- **[Risk] 镜像内嵌 ADB 私钥泄露** → **Mitigation**：私有 registry、最小分发范围；生产可用 secret mount 覆盖 `/root/.android/adbkey`；构建流水线使用受控密钥。

- **[Risk] 健康检查端口与监听端口不一致** → **Mitigation**：默认使用 8000；自定义端口时改 `docker run -e` 与 HEALTHCHECK 或文档说明。

- **[Risk] 构建机缺少 `adbkey/adbkey` 文件导致 COPY 失败** → **Mitigation**：CI 注入密钥文件或文档明确前置条件。

- **[Risk] 容器网络与 adbd 不在同一网络命名空间** → **Mitigation**：由运维使用 `adb connect`、`host.docker.internal`、SSH `-L`/`autossh` 等组合解决（超出镜像本身）。

## Migration Plan

1. 在具备 `adbkey/adbkey` 的环境中执行 `docker build`。  
2. `docker run -p 8000:8000` 并配置模型 `base_url` 等环境变量（与裸机一致）。  
3. 验证 `curl` 访问 `/openapi.json` 与一次需 ADB 的任务。  
4. **回滚**：继续使用裸机 `python server.py`，无数据迁移。

## Open Questions

- 是否需要在后续变更中增加构建参数以切换官方源/禁用国内镜像（跨国 CI）。  
- 是否增加专用 `GET /health` 以解耦 OpenAPI 与健康检查语义。
