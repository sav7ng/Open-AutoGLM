"""
API v1 路由注册
"""

from fastapi import APIRouter

from app.api.v1.endpoints import agent, tasks

api_router = APIRouter()
api_router.include_router(agent.router, tags=["agent"])
api_router.include_router(tasks.router, tags=["tasks"])
