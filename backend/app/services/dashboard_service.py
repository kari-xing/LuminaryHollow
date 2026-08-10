"""看板聚合服务：热力图 / 趋势 / 时间轴 / 词云。

原型阶段：从 chat_messages 实时聚合；数据缺失时返回空列表。
"""
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession

# 情绪 → 积极程度（与 emotion.EMOTION_SCORE 保持一致）
EMOTION_SCORE = {"开心": 0.85, "平静": 0.6, "低落": 0.35, "焦虑": 0.25, "愤怒": 0.1}


async def _daily_scores(
    db: AsyncSession, user_id: uuid.UUID, start: date, end: date
) -> dict[date, dict]:
    """按天聚合 avg_score / count / label_mode（仅统计有情绪评分的非隐私消息）。"""
    stmt = (
        select(
            func.date(ChatMessage.created_at).label("d"),
            func.avg(ChatMessage.emotion_score).label("avg"),
            func.count(ChatMessage.id).label("cnt"),
            func.max(ChatMessage.emotion_score).label("max"),
        )
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.is_private.is_(False),
            ChatMessage.emotion_score.is_not(None),
            func.date(ChatMessage.created_at) >= start,
            func.date(ChatMessage.created_at) <= end,
        )
        .group_by("d")
    )
    rows = (await db.execute(stmt)).all()
    result: dict[date, dict] = {}
    for d, avg, cnt, max_score in rows:
        mode = min(EMOTION_SCORE, key=lambda k: abs(EMOTION_SCORE[k] - (avg or 0)))
        result[d] = {"avg_score": round(float(avg), 3) if avg else None, "count": cnt, "label_mode": mode}
    return result


async def get_heatmap(db: AsyncSession, user_id: uuid.UUID, year: int) -> list[dict]:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    agg = await _daily_scores(db, user_id, start, end)
    return [
        {
            "date": start + timedelta(days=i),
            "avg_score": agg.get(start + timedelta(days=i), {}).get("avg_score"),
            "count": agg.get(start + timedelta(days=i), {}).get("count", 0),
            "label_mode": agg.get(start + timedelta(days=i), {}).get("label_mode"),
        }
        for i in range((end - start).days + 1)
    ]


async def get_trend(db: AsyncSession, user_id: uuid.UUID, days: int) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    agg = await _daily_scores(db, user_id, start, end)
    return [
        {
            "date": start + timedelta(days=i),
            "avg_score": agg.get(start + timedelta(days=i), {}).get("avg_score"),
        }
        for i in range(days)
    ]


async def get_timeline(
    db: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[dict], int]:
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.summary.is_not(None))
        .order_by(ChatSession.started_at.desc())
    )
    total = len((await db.execute(stmt)).scalars().all())
    rows = (
        (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    )
    items = [
        {
            "session_id": str(s.id),
            "date": s.started_at.date(),
            "duration_min": 0,
            "summary": s.summary,
            "emotion_label": None,
        }
        for s in rows
    ]
    return items, total


async def get_wordcloud(db: AsyncSession, user_id: uuid.UUID, period: str) -> list[dict]:
    """关键词云：原型阶段提取高频名词（简单统计）。"""
    days = {"week": 7, "month": 30, "all": 365 * 10}.get(period, 30)
    start = datetime.now() - timedelta(days=days)
    stmt = (
        select(ChatMessage.content)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == user_id, ChatMessage.created_at >= start)
    )
    contents = (await db.execute(stmt)).scalars().all()
    freq: dict[str, int] = {}
    stopwords = {"我", "你", "的", "了", "吗", "啊", "吧", "是", "这", "那", "一个", "什么", "今天", "觉得", "有点"}
    for text in contents:
        for ch in "，。！？、；：""''（）《》… ":
            text = text.replace(ch, " ")
        for word in text.split():
            if len(word) >= 2 and word not in stopwords:
                freq[word] = freq.get(word, 0) + 1
    top = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:50]
    return [{"text": w, "weight": c} for w, c in top]
