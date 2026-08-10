"""PostgreSQL 异步引擎与会话管理（SQLAlchemy 2.0 async）。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,       # 取连接前校验，避免拿到失效连接
    pool_size=5,              # 常驻连接
    max_overflow=10,          # 峰值扩展
    pool_timeout=30,          # 等连接超时（秒）
    pool_recycle=3600,        # 1 小时回收，防止 PostgreSQL 端闲置断开
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的统一基类。"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级数据库会话。"""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """开发期便捷建表（生产环境请使用 Alembic 迁移）。"""
    # 导入模型以确保注册到 Base.metadata
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
