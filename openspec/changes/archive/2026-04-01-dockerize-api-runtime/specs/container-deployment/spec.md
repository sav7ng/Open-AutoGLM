# Container deployment（变更增量）

## Purpose

定义 Open-AutoGLM API 服务容器镜像的交付要求：构建阶段、运行时工具、ADB 密钥布局与健康检查，与仓库根目录 `Dockerfile` 及 `.dockerignore` 对齐。

## ADDED Requirements

### Requirement: 多阶段镜像与 Python 运行时

交付的容器镜像 SHALL 使用至少两阶段构建：第一阶段在隔离环境中创建虚拟环境并安装 `requirements.txt`；最终阶段基于 `python:3.11-slim` 且 SHALL 将虚拟环境复制为默认 `PATH` 中的 Python 解释器与依赖。最终镜像 SHALL 将工作目录设为 `/app`。

#### Scenario: 镜像内 Python 版本

- **WHEN** 在运行中的容器内执行 `python --version`
- **THEN** 主版本号 SHALL 为 3.11

### Requirement: 运行时系统工具

最终镜像 SHALL 通过发行版包管理器安装以下可执行文件（或其所属软件包提供的等价命令）：`curl`、`adb`、`ping`（`iputils-ping`）、`ssh`（`openssh-client`）、`autossh`。这些工具 SHALL 可供运维在容器内执行健康检查、ADB 客户端操作与基于 SSH 的端口转发/隧道维护。

#### Scenario: ADB 客户端可用

- **WHEN** 在容器内执行 `adb version`
- **THEN** 命令 SHALL 成功输出版本信息而非「command not found」

#### Scenario: SSH 客户端可用

- **WHEN** 在容器内执行 `ssh -V`
- **THEN** 命令 SHALL 成功输出 OpenSSH 版本信息

### Requirement: ADB 客户端密钥路径与权限

镜像构建 SHALL 将仓库中 `adbkey/adbkey` 复制到容器路径 `/root/.android/adbkey`，且该文件权限 SHALL 为仅所有者可读写（例如 Unix 模式 600）。

#### Scenario: 密钥文件存在且权限受限

- **WHEN** 检查容器内路径 `/root/.android/adbkey`
- **THEN** 文件 SHALL 存在且对非所有者的读权限 SHALL 被拒绝（以镜像构建结果为准）

### Requirement: 应用文件布局

最终镜像 SHALL 包含运行 `python server.py` 所需的最小源码树：`server.py`、`app/` 目录、`phone_agent/` 目录，且 SHALL 位于 `/app` 下相对路径与仓库一致（即 `/app/server.py`、`/app/app/`、`/app/phone_agent/`）。

#### Scenario: 默认启动入口

- **WHEN** 容器以镜像默认命令启动且未覆盖 `CMD`
- **THEN** 进程 SHALL 执行 `python server.py` 并加载 `app.main` 中的 FastAPI 应用

### Requirement: 暴露端口与健康检查

镜像 SHALL 声明暴露 TCP 端口 8000。镜像 SHALL 配置 `HEALTHCHECK`，在容器内使用 `curl` 对 `http://localhost:8000/openapi.json` 发起成功请求（HTTP 2xx）时视为健康；若服务监听地址或端口通过环境变量改为非默认，运维方 SHALL 相应调整健康检查或端口映射以保持一致性。

#### Scenario: 默认端口下 OpenAPI 可访问即健康

- **WHEN** 服务在容器内监听 `0.0.0.0:8000` 且路由已注册
- **THEN** `GET /openapi.json` SHALL 返回 200，且 HEALTHCHECK 所用 `curl` SHALL 成功

### Requirement: 构建上下文排除

仓库 SHALL 提供根目录 `.dockerignore`，排除对运行时无用的路径（至少包含版本控制目录、本地虚拟环境目录及 Python 缓存），以缩短构建时间与减小发送到守护进程的上下文。

#### Scenario: 虚拟环境不进入镜像构建上下文

- **WHEN** 执行 `docker build` 且上下文为仓库根目录
- **THEN** `.dockerignore` SHALL 列出 `.venv`（或等价本地 venv 目录名）使该目录不被 COPY 进镜像层（除非显式移除该规则）
