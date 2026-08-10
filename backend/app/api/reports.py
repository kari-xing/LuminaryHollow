"""周报接口：最新 / 列表。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import WeeklyReport
from app.models.user import User

router = APIRouter()


@router.get("/weekly/latest", response_model=dict)
async def latest_report(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == user.id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return {"report": None}
    return {
        "report": {
            "id": str(report.id),
            "week_start": report.week_start.isoformat(),
            "week_end": report.week_end.isoformat(),
            "summary": report.summary,
            "emotion_trend": report.emotion_trend,
            "top_topics": report.top_topics,
            "generated_at": report.generated_at.isoformat(),
        }
    }


@router.get("/weekly", response_model=dict)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await db.execute(
            select(WeeklyReport)
            .where(WeeklyReport.user_id == user.id)
            .order_by(WeeklyReport.week_start.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "week_start": r.week_start.isoformat(),
                "week_end": r.week_end.isoformat(),
                "summary": r.summary,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in rows
        ],
        "total": len(rows),
    }
