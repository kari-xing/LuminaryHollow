"""记忆相关 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class LongTermMemoryOut(BaseModel):
    id: uuid.UUID
    summary: str
    memory_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryListOut(BaseModel):
    items: list[LongTermMemoryOut]
    total: int
    page: int
