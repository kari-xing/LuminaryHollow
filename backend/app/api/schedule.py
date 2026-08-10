"""日程接口：按日期范围查询 / 新建 / 更新 / 删除。

- GET  /api/schedule?date=YYYY-MM-DD 或 ?start=&end=（按本地时区日期范围）
- POST /api/schedule              手动或对话自动补充创建
- PUT  /api/schedule/{id}         更新内容 / 时间 / 完成状态
- DELETE /api/schedule/{id}       删除
"""
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.schedule import ScheduleItem
from app.models.user import User
from app.schemas.schedule import ScheduleItemCreate, ScheduleItemOut, ScheduleItemUpdate
from app.services import schedule_service

router = APIRouter()
_tz = ZoneInfo(settings.TIMEZONE)


def _day_range(d: date) -> tuple[datetime, datetime]:
    """本地时区某天的 [0 点, 次日 0 点) 范围（转 UTC 存储比较）。"""
    start = datetime.combine(d, time.min, tzinfo=_tz).astimezone(ZoneInfo("UTC"))
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=_tz).astimezone(ZoneInfo("UTC"))
    return start, end


@router.get("", response_model=dict)
async def list_schedule(
    date_query: date | None = Query(default=None, alias="date"),
    start: date | None = Query(default=None, alias="start"),
    end: date | None = Query(default=None, alias="end"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if date_query is not None:
        lo, hi = _day_range(date_query)
    else:
        lo_d = start or date.today()
        hi_d = end or lo_d
        lo, _ = _day_range(lo_d)
        _, hi = _day_range(hi_d)
    stmt = (
        select(ScheduleItem)
        .where(
            ScheduleItem.user_id == user.id,
            ScheduleItem.due_at >= lo,
            ScheduleItem.due_at < hi,
        )
        .order_by(ScheduleItem.due_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [ScheduleItemOut.model_validate(r).model_dump() for r in rows]}


@router.get("/stats", response_model=dict)
async def schedule_stats(
    days: int = Query(7, ge=1, le=30),
    heat_days: int = Query(90, ge=7, le=180),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """日程统计：今日/本周完成率、近 N 天柱状图、天×时段完成热力图（本地时区聚合）。"""
    return await schedule_service.get_stats(db, user.id, days=days, heat_days=heat_days)


@router.post("", response_model=ScheduleItemOut, status_code=201)
async def create_schedule(
    payload: ScheduleItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleItem:
    item = ScheduleItem(
        user_id=user.id,
        content=payload.content,
        due_at=payload.due_at,
        source=payload.source,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ScheduleItemOut)
async def update_schedule(
    item_id: uuid.UUID,
    payload: ScheduleItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduleItem:
    item = await db.get(ScheduleItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": 4040, "message": "日程不存在"})
    if payload.content is not None:
        item.content = payload.content
    if payload.due_at is not None:
        item.due_at = payload.due_at
    if payload.done is not None:
        item.done = payload.done
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_schedule(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    item = await db.get(ScheduleItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": 4040, "message": "日程不存在"})
    await db.delete(item)
    await db.commit()
