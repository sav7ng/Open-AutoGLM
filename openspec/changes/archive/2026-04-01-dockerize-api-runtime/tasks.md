## 1. 镜像与构建上下文

- [x] 1.1 实现并核对根目录 `Dockerfile`：多阶段构建、`python:3.11-slim`、builder 安装 `requirements.txt` 至 `/opt/venv`，runtime 安装 `curl`、`android-tools-adb`、`iputils-ping`、`openssh-client`、`autossh`，Debian 源与 PyPI 镜像按设计文档
- [x] 1.2 将 `adbkey/adbkey` 复制到 `/root/.android/adbkey` 并设置权限 600
- [x] 1.3 复制 `phone_agent/`、`app/`、`server.py` 至 `/app`，`WORKDIR /app`，`EXPOSE 8000`，`HEALTHCHECK` 探测 `http://localhost:8000/openapi.json`，`CMD` 为 `python server.py`
- [x] 1.4 添加或核对根目录 `.dockerignore`（至少排除 `.git`、`.venv`、`__pycache__` 等无关路径）

## 2. 验证

- [x] 2.1 在含有效 `adbkey/adbkey` 的环境中执行 `docker build`，构建成功
- [x] 2.2 运行容器并确认 `adb version`、`ssh -V` 可用；默认端口下 `GET /openapi.json` 返回 200
- [ ] 2.3 （可选）在可连 ADB 的目标环境下跑通一次依赖设备的 Agent 任务，确认隧道/网络配置与镜像工具链一致

## 3. 规格与变更闭环

- [x] 3.1 实现完成后将本 change 归档，使 `container-deployment` 能力进入主 specs（按项目 `openspec-archive` 流程执行）
