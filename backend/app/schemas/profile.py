"""用户画像相关 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    age: int | None = Field(default=None, ge=5, le=120)
    occupation: str | None = Field(default=None, max_length=64)
    goal: str | None = None
    struggle: str | None = None
    preferred_tone: str | None = "warm"
    privacy_mode: bool | None = None


class ProfileOut(BaseModel):
    user_id: uuid.UUID
    name: str | None = None
    age: int | None = None
    occupation: str | None = None
    goal: str | None = None
    struggle: str | None = None
    preferred_tone: str = "warm"
    privacy_mode: bool = False
    updated_at: datetime

    model_config = {"from_attributes": True}
