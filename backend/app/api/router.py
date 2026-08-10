"""统一 API 路由注册。"""
from fastapi import APIRouter

from app.api import auth, dashboard, export, memories, reports, schedule, sessions, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["会话"])
api_router.include_router(memories.router, prefix="/memories", tags=["记忆"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["看板"])
api_router.include_router(reports.router, prefix="/reports", tags=["周报"])
api_router.include_router(export.router, prefix="/export", tags=["导出"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["日程"])
