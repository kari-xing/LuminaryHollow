"""周报相关 Schema。"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: uuid.UUID
    week_start: date
    week_end: date
    summary: str
    emotion_trend: dict | None = None
    top_topics: dict | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class ReportListOut(BaseModel):
    items: list[ReportOut]
    total: int
