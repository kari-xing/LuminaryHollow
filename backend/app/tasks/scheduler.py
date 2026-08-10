"""APScheduler 定时任务调度器。

- 生成周报：每周日 22:00（cron 可配）
- 记忆合并清理：每天 03:00
- 会话超时关闭：每天 04:00
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

from app.config import settings
from app.core.database import SessionLocal
from app.models.chat import ChatSession
from app.models.user import User
from app.services.report_service import generate_weekly_report

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def _generate_weekly_reports() -> None:
    """为活跃用户生成上周周报（幂等：已有则跳过）。"""
    logger.info("[定时任务] 开始生成周报")
    async with SessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
            today = datetime.now().date()
            last_monday = today - timedelta(days=today.weekday() + 7)
            try:
                await generate_weekly_report(db, user.id, last_monday)
            except Exception as exc:
                logger.warning("用户 %s 周报生成失败: %s", user.id, exc)


async def _close_stale_sessions() -> None:
    """超过 24h 无消息的会话标记 ended_at。"""
    async with SessionLocal() as db:
        cutoff = datetime.now() - timedelta(hours=24)
        await db.execute(
            update(ChatSession)
            .where(ChatSession.ended_at.is_(None), ChatSession.started_at < cutoff)
            .values(ended_at=datetime.now())
        )
        await db.commit()


def start_scheduler() -> None:
    if scheduler.running:
        return
    cron = settings.WEEKLY_REPORT_CRON.split()
    if len(cron) == 5:
        scheduler.add_job(
            _generate_weekly_reports,
            "cron",
            hour=int(cron[0]),
            minute=int(cron[1]),
            day_of_week=cron[4],
            id="weekly_report",
            replace_existing=True,
        )
    scheduler.add_job(_close_stale_sessions, "cron", hour=4, minute=0, id="stale_sessions")
    scheduler.start()
    logger.info("[定时任务] 调度器已启动")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
