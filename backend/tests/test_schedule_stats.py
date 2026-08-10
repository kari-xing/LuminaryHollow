"""日程统计聚合单元测试（纯函数 build_stats，不依赖数据库）。

覆盖：今日/本周完成率、本地时区时段分桶、空数据、naive UTC 兜底、日期序列补零。
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.services.schedule_service import build_stats

TZ = ZoneInfo("Asia/Shanghai")  # UTC+8，与 settings.TIMEZONE 默认一致
UTC = timezone.utc


def test_empty_stats():
    today = date(2026, 8, 10)
    stats = build_stats([], TZ, today, days=7, heat_days=90)
    assert stats["today"]["total"] == 0
    assert stats["today"]["done"] == 0
    assert stats["today"]["done_rate"] is None
    assert stats["week"]["total"] == 0
    assert stats["week"]["done_rate"] is None
    assert len(stats["daily"]) == 7
    assert len(stats["heatmap"]) == 90
    assert len(stats["heatmap"][0]["slots"]) == 8
    assert stats["heatmap"][-1]["date"] == today.isoformat()


def test_today_done_rate_and_slot():
    # 本地 8/10 12:00 = UTC 8/10 04:00 → slot 4（本地时间，而非 UTC 4 点的 slot 1）
    # 本地 8/10 20:00 = UTC 8/10 12:00 → slot 6
    rows = [
        (datetime(2026, 8, 10, 4, 0, tzinfo=UTC), True),
        (datetime(2026, 8, 10, 12, 0, tzinfo=UTC), False),
    ]
    stats = build_stats(rows, TZ, date(2026, 8, 10), days=7, heat_days=90)
    today = stats["today"]
    assert today["total"] == 2
    assert today["done"] == 1
    assert today["done_rate"] == 0.5
    slot_map = {s["slot"]: s for s in stats["heatmap"][-1]["slots"]}
    assert slot_map[4]["total"] == 1 and slot_map[4]["done"] == 1
    assert slot_map[6]["total"] == 1 and slot_map[6]["done"] == 0
    # 未涉及的时段保持 0
    assert slot_map[0]["total"] == 0 and slot_map[0]["done_rate"] is None


def test_week_aggregate_monday_to_today():
    # 2026-08-10 是周一，8-15 是周六；本周范围 = 8/10 ~ 8/15
    rows = [
        (datetime(2026, 8, 10, 2, 0, tzinfo=UTC), True),   # 本地 8/10 10:00
        (datetime(2026, 8, 11, 2, 0, tzinfo=UTC), False),  # 本地 8/11 10:00
        (datetime(2026, 8, 15, 2, 0, tzinfo=UTC), False),  # 本地 8/15（周六）
    ]
    stats = build_stats(rows, TZ, date(2026, 8, 15), days=7, heat_days=90)
    assert stats["week"]["start"] == "2026-08-10"
    assert stats["week"]["end"] == "2026-08-15"
    assert stats["week"]["total"] == 3
    assert stats["week"]["done"] == 1
    assert stats["week"]["done_rate"] == round(1 / 3, 3)


def test_naive_utc_treated_as_utc():
    # 无时区的存储时间（驱动差异兜底）按 UTC 处理
    rows = [(datetime(2026, 8, 10, 4, 0), True)]
    stats = build_stats(rows, TZ, date(2026, 8, 10), days=7, heat_days=90)
    assert stats["today"]["total"] == 1
    assert stats["today"]["done"] == 1
    # UTC 04:00 → 本地 12:00 → slot 4
    assert stats["heatmap"][-1]["slots"][4]["total"] == 1


def test_daily_series_fills_gaps():
    rows = [(datetime(2026, 8, 8, 2, 0, tzinfo=UTC), True)]
    stats = build_stats(rows, TZ, date(2026, 8, 10), days=7, heat_days=90)
    dates = [d["date"] for d in stats["daily"]]
    assert dates[0] == "2026-08-04"
    assert dates[-1] == "2026-08-10"
    row = next(d for d in stats["daily"] if d["date"] == "2026-08-08")
    assert row["total"] == 1 and row["done"] == 1 and row["done_rate"] == 1.0
    empty = next(d for d in stats["daily"] if d["date"] == "2026-08-09")
    assert empty["total"] == 0 and empty["done_rate"] is None
