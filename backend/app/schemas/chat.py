"""聊天 / 会话相关 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WSMessageIn(BaseModel):
    """客户端 → 服务端：用户消息。"""

    type: str = "user_message"  # user_message / quick_checkin
    content: str = Field(default="", max_length=2000)


class QuickCheckinIn(BaseModel):
    type: str = "quick_checkin"
    emotion_label: str  # 开心 / 平静 / 低落 / 焦虑 / 愤怒


class WSEmotionOut(BaseModel):
    type: str
    emotion_label: str | None = None
    emotion_score: float | None = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    emotion_label: str | None = None
    emotion_score: float | None = None
    is_private: bool = False
    is_quick_checkin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = 0
    avg_emotion_score: float | None = None
    summary: str | None = None

    model_config = {"from_attributes": True}
