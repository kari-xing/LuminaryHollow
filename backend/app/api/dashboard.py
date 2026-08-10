"""看板接口：热力图 / 趋势 / 时间轴 / 词云。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services import dashboard_service

router = APIRouter()


@router.get("/heatmap", response_model=dict)
async def heatmap(
    year: int = Query(default=2026),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    days = await dashboard_service.get_heatmap(db, user.id, year)
    return {"year": year, "days": days}


@router.get("/trend", response_model=dict)
async def trend(
    days: int = Query(30, ge=7, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    points = await dashboard_service.get_trend(db, user.id, days)
    return {"days": days, "points": points}


@router.get("/timeline", response_model=dict)
async def timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await dashboard_service.get_timeline(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page}


@router.get("/wordcloud", response_model=dict)
async def wordcloud(
    period: str = Query("month", pattern="^(week|month|all)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    words = await dashboard_service.get_wordcloud(db, user.id, period)
    return {"period": period, "words": words}
