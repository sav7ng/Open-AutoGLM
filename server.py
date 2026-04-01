"""
HTTP 服务启动入口

用法：
    python server.py

环境变量：
    PHONE_AGENT_SERVER_PORT  服务端口（默认 8000）
    PHONE_AGENT_SERVER_HOST  服务监听地址（默认 0.0.0.0）
"""

import os

import uvicorn


def main():
    host = os.environ.get("PHONE_AGENT_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("PHONE_AGENT_SERVER_PORT", "8000"))

    print(f"Starting Open-AutoGLM API server on {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
