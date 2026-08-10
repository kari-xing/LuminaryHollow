"""长期记忆模型（向量本体存于 ChromaDB，此处存摘要与关联）。"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LongTermMemory(Base):
    __tablename__ = "long_term_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str | None] = mapped_column(Text)  # 原始相关内容（可选）
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # LLM 总结文本
    memory_type: Mapped[str] = mapped_column(String(20), default="event")  # event/emotion/preference
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="memories")
