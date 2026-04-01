"""
FastAPI 应用创建与配置
"""

import logging

from fastapi import FastAPI

from app.api.v1.api import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Open-AutoGLM API",
    description="HTTP API for Open-AutoGLM Phone Agent — AI-powered phone automation",
    version="0.1.0",
)

app.include_router(api_router)
