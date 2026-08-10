"""心光树洞 LuminaryHollow · FastAPI 应用入口。

启动：uvicorn app.main:app --reload --port 8012
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.tasks.scheduler import shutdown_scheduler, start_scheduler
from app.ws.chat import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：定时任务
    start_scheduler()
    logger.info("%s 启动完成", settings.PROJECT_NAME)
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="有记忆、有温度、能感知情绪的 AI 对话伙伴",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# WebSocket 实时对话
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    """健康检查：DB / Redis / Chroma 连通性。"""
    status = {"status": "ok", "services": {}}

    from app.core.chroma_client import get_chroma
    from app.core.redis_client import get_redis

    # PostgreSQL
    try:
        from sqlalchemy import text
        from app.core.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["services"]["postgres"] = "up"
    except Exception:
        status["services"]["postgres"] = "down"

    # Redis
    try:
        await get_redis().ping()
        status["services"]["redis"] = "up"
    except Exception:
        status["services"]["redis"] = "down"

    # ChromaDB
    try:
        get_chroma().heartbeat()
        status["services"]["chroma"] = "up"
    except Exception:
        status["services"]["chroma"] = "down"

    status["status"] = "ok" if all(v == "up" for v in status["services"].values()) else "degraded"
    return status
