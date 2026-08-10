"""日程统计服务：今日/本周完成率、近 N 天柱状图、天×时段完成热力图。

所有日期按本地时区（settings.TIMEZONE）解释；每天分 8 个时段（每 3 小时一档），
与情绪看板的时段粒度保持一致，方便用户看出「上午安排的日程更多 / 晚上更容易拖延」这类规律。
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schedule import ScheduleItem

SLOT_COUNT = 8
SLOT_HOURS = 24 // SLOT_COUNT


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def _day_utc_range(d: date) -> tuple[datetime, datetime]:
    """本地时区某天的 [0 点, 次日 0 点) 转 UTC 存储比较范围。"""
    tz = _tz()
    lo = datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc)
    hi = datetime.combine(d + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    return lo, hi


def _rate(done: int, total: int) -> float | None:
    return round(done / total, 3) if total else None


def _to_local(ts: datetime, tz: ZoneInfo) -> datetime:
    """统一转为本地时间；无时区视为 UTC（PostgreSQL 驱动差异兜底）。"""
    if ts.tzinfo:
        return ts.astimezone(tz)
    return ts.replace(tzinfo=timezone.utc).astimezone(tz)


async def get_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 7,
    heat_days: int = 90,
) -> dict:
    """返回今日/本周完成率、近 days 天柱状图、近 heat_days 天时段热力图。"""
    tz = _tz()
    today = datetime.now(tz).date()
    span = max(days, heat_days)
    start = today - timedelta(days=span - 1)

    lo, _ = _day_utc_range(start)
    _, hi = _day_utc_range(today + timedelta(days=1))

    stmt = (
        select(ScheduleItem)
        .where(
            ScheduleItem.user_id == user_id,
            ScheduleItem.due_at >= lo,
            ScheduleItem.due_at < hi,
        )
        .order_by(ScheduleItem.due_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return build_stats([(it.due_at, it.done) for it in rows], tz, today, days, heat_days)


def build_stats(
    rows: list[tuple[datetime, bool]],
    tz: ZoneInfo,
    today: date,
    days: int = 7,
    heat_days: int = 90,
) -> dict:
    """纯聚合：输入 [(due_at, done)]，按本地时区分桶后输出统计结构。

    返回 today（今日完成率）/ week（本周，周一~今天）/ daily（近 days 天）/
    heatmap（近 heat_days 天，每天 8 个时段格）。
    """
    # 按本地日期 + 时段聚合
    days_map: dict[date, dict] = {}
    for ts, done in rows:
        local = _to_local(ts, tz)
        d = local.date()
        slot = local.hour // SLOT_HOURS
        day = days_map.setdefault(d, {"total": 0, "done": 0, "slots": {}})
        day["total"] += 1
        if done:
            day["done"] += 1
        s = day["slots"].setdefault(slot, {"total": 0, "done": 0})
        s["total"] += 1
        if done:
            s["done"] += 1

    # 今日 / 本周（周一 ~ 今天）
    monday = today - timedelta(days=today.weekday())
    today_info = days_map.get(today, {"total": 0, "done": 0, "slots": {}})
    week_total = week_done = 0
    for i in range((today - monday).days + 1):
        day = days_map.get(today - timedelta(days=i), {"total": 0, "done": 0, "slots": {}})
        week_total += day["total"]
        week_done += day["done"]

    daily = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        day = days_map.get(d, {"total": 0, "done": 0, "slots": {}})
        daily.append(
            {
                "date": d.isoformat(),
                "total": day["total"],
                "done": day["done"],
                "done_rate": _rate(day["done"], day["total"]),
            }
        )

    heatmap = []
    for i in range(heat_days):
        d = today - timedelta(days=heat_days - 1 - i)
        day = days_map.get(d, {"total": 0, "done": 0, "slots": {}})
        slots = []
        for s in range(SLOT_COUNT):
            info = day["slots"].get(s, {"total": 0, "done": 0})
            slots.append(
                {
                    "slot": s,
                    "total": info["total"],
                    "done": info["done"],
                    "done_rate": _rate(info["done"], info["total"]),
                }
            )
        heatmap.append(
            {
                "date": d.isoformat(),
                "total": day["total"],
                "done": day["done"],
                "done_rate": _rate(day["done"], day["total"]),
                "slots": slots,
            }
        )

    return {
        "today": {
            "date": today.isoformat(),
            "total": today_info["total"],
            "done": today_info["done"],
            "done_rate": _rate(today_info["done"], today_info["total"]),
        },
        "week": {
            "start": monday.isoformat(),
            "end": today.isoformat(),
            "total": week_total,
            "done": week_done,
            "done_rate": _rate(week_done, week_total),
        },
        "daily": daily,
        "heatmap": heatmap,
    }
