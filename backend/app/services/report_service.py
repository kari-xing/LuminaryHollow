"""周报服务：聚合一周数据 → LLM 生成 → 落库。"""
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.report import WeeklyReport
from app.services.llm_client import llm

logger = logging.getLogger(__name__)


async def generate_weekly_report(db: AsyncSession, user_id: uuid.UUID, week_start: date) -> WeeklyReport:
    week_end = week_start + timedelta(days=6)

    stmt = (
        select(
            func.count(ChatMessage.id),
            func.avg(ChatMessage.emotion_score),
        )
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.user_id == user_id,
            func.date(ChatMessage.created_at) >= week_start,
            func.date(ChatMessage.created_at) <= week_end,
        )
    )
    count, avg = (await db.execute(stmt)).one()

    # 高频话题（复用看板聚合思路，简化为取消息内容）
    msg_stmt = (
        select(ChatMessage.content)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.user_id == user_id,
            func.date(ChatMessage.created_at) >= week_start,
            func.date(ChatMessage.created_at) <= week_end,
        )
    )
    contents = (await db.execute(msg_stmt)).scalars().all()
    topics = "、".join([c[:20] for c in contents[:8]])

    summary = await llm.chat(
        [
            {
                "role": "system",
                "content": "你是情绪周报撰写助手。请基于以下一周对话数据，写一段温暖、简洁的中文周报（100字内），"
                "包含：本周情绪整体情况、高频话题、给用户的一句鼓励。",
            },
            {
                "role": "user",
                "content": f"本周消息数：{count}，平均情绪评分：{round(avg, 2) if avg else '无'}（0消极~1积极）。高频内容：{topics}",
            },
        ]
    )

    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        summary=summary or "本周没有足够的数据生成周报。",
        emotion_trend={"avg_score": round(avg, 3) if avg else None, "message_count": count},
        top_topics={"topics": [t for t in topics.split("、") if t][:5]},
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
