"""日程接口的 Pydantic Schema。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScheduleItemCreate(BaseModel):
    content: str = Field(min_length=1, max_length=200)
    due_at: datetime
    source: str = Field(default="manual", pattern="^(manual|chat)$")


class ScheduleItemUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=200)
    due_at: datetime | None = None
    done: bool | None = None


class ScheduleItemOut(BaseModel):
    id: UUID
    content: str
    due_at: datetime
    done: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
