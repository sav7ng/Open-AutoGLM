## Why

在服务器或 CI 上一致地运行 Open-AutoGLM HTTP API（`server.py` / FastAPI）时，缺少标准容器交付物会导致环境漂移、ADB 与系统工具依赖难以复现。通过官方化的 Docker 镜像与规格说明，可缩短部署时间并明确与真机 ADB、SSH 隧道相关的运维契约。

## What Changes

- 提供多阶段 `Dockerfile`：固定 Python 3.11、虚拟环境安装 `requirements.txt`，运行时包含 `curl`、`android-tools-adb`、`iputils-ping`、`openssh-client`、`autossh`。
- 将 `adbkey/adbkey` 复制到镜像内 `/root/.android/adbkey`（权限 600），与现有 ADB 客户端认证方式对齐。
- 使用 `.dockerignore` 缩小构建上下文（排除 `.venv`、`.git` 等）。
- 容器默认暴露 8000，健康检查探测 `GET /openapi.json`；启动命令为 `python server.py`（沿用 `PHONE_AGENT_SERVER_*` 环境变量）。
- 文档化镜像内可用的运维能力（ADB、SSH 隧道）及构建前置条件（仓库内需存在 `adbkey` 文件）。

## Capabilities

### New Capabilities

- `container-deployment`: 描述容器镜像的交付范围、内含系统工具、ADB 密钥布局、健康检查与端口约定，以及与宿主机/远程 ADB 协同时的假设（不替代 `agent-runtime` 的 Python 契约）。

### Modified Capabilities

- （无）HTTP API、Agent 运行时与模型调用等行为不因容器化而改变；仅增加部署面规格。

## Impact

- 仓库根目录新增 `Dockerfile`、`.dockerignore`（若已存在则对齐本变更规格）。
- 运维与集成方：需知镜像内嵌 `adbkey` 的敏感性与可选的 volume 覆盖策略。
- 与现有 `phone_agent` / `app` 源码无 API 破坏性变更。
