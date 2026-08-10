"""看板聚合服务：热力图（天×时段）/ 趋势 / 时间轴 / 词云。

情绪时段聚合：按本地时区（settings.TIMEZONE）把一天分为 8 个时段（每 3 小时一档），
让「上午低落、晚上开心」这类阶段性情绪规律可见。
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat import ChatMessage, ChatSession

# 情绪 → 积极程度（与 emotion.EMOTION_SCORE 保持一致）
EMOTION_SCORE = {"开心": 0.85, "平静": 0.6, "低落": 0.35, "焦虑": 0.25, "愤怒": 0.1}

# 每天 8 个时段（每 3 小时一档）
SLOT_COUNT = 8
SLOT_HOURS = 24 // SLOT_COUNT


async def _period_scores(
    db: AsyncSession, user_id: uuid.UUID, start: date, end: date
) -> dict[date, dict[int, dict]]:
    """按本地时区聚合「天 × 时段」的情绪均分与条数（仅统计有情绪评分的非隐私消息）。"""
    tz = ZoneInfo(settings.TIMEZONE)
    stmt = (
        select(ChatMessage.created_at, ChatMessage.emotion_score)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.is_private.is_(False),
            ChatMessage.emotion_score.is_not(None),
            func.date(ChatMessage.created_at) >= start,
            func.date(ChatMessage.created_at) <= end,
        )
    )
    rows = (await db.execute(stmt)).all()

    bucket: dict[date, dict[int, list[float]]] = {}
    for ts, score in rows:
        local = ts.astimezone(tz) if ts.tzinfo else ts.replace(tzinfo=timezone.utc).astimezone(tz)
        d = local.date()
        slot = local.hour // SLOT_HOURS
        bucket.setdefault(d, {}).setdefault(slot, []).append(score)

    result: dict[date, dict[int, dict]] = {}
    for d, slots in bucket.items():
        result[d] = {
            s: {"avg_score": round(sum(v) / len(v), 3), "count": len(v)}
            for s, v in slots.items()
        }
    return result


def _fill_day(d: date, slots: dict[int, dict]) -> dict:
    """把某天的时段数据展开为固定 8 档数组，并汇总日级情绪。"""
    day_slots = []
    total_score = 0.0
    total_cnt = 0
    for s in range(SLOT_COUNT):
        info = slots.get(s)
        if info:
            total_score += info["avg_score"] * info["count"]
            total_cnt += info["count"]
        day_slots.append(
            {
                "slot": s,
                "avg_score": info["avg_score"] if info else None,
                "count": info["count"] if info else 0,
            }
        )
    day_avg = round(total_score / total_cnt, 3) if total_cnt else None
    mode = min(EMOTION_SCORE, key=lambda k: abs(EMOTION_SCORE[k] - (day_avg or 0))) if day_avg else None
    return {"avg_score": day_avg, "count": total_cnt, "label_mode": mode, "slots": day_slots}


async def get_heatmap(db: AsyncSession, user_id: uuid.UUID, year: int) -> list[dict]:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    agg = await _period_scores(db, user_id, start, end)
    return [
        {"date": start + timedelta(days=i), **_fill_day(start + timedelta(days=i), agg.get(start + timedelta(days=i), {}))}
        for i in range((end - start).days + 1)
    ]


async def get_trend(db: AsyncSession, user_id: uuid.UUID, days: int) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    agg = await _period_scores(db, user_id, start, end)
    return [
        {
            "date": start + timedelta(days=i),
            "avg_score": _fill_day(start + timedelta(days=i), agg.get(start + timedelta(days=i), {}))["avg_score"],
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
