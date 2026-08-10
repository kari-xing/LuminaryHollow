"""会话接口：列表 / 详情 / 新建。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatSessionOut
from app.services.emotion import strip_emotion_tag

router = APIRouter()


@router.get("", response_model=dict)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    total = len(
        (
            await db.execute(
                select(ChatSession).where(ChatSession.user_id == user.id)
            )
        ).scalars().all()
    )
    rows = (
        await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {"items": [ChatSessionOut.model_validate(r).model_dump() for r in rows], "total": total}


@router.get("/{session_id}", response_model=dict)
async def get_session_detail(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": 4040, "message": "会话不存在"})
    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
    ).scalars().all()
    # 历史消息可能残留旧版【情绪标签：xxx】标记，返回前统一剥离
    return {
        "session": ChatSessionOut.model_validate(session).model_dump(),
        "messages": [
            {
                **ChatMessageOut.model_validate(m).model_dump(),
                "content": strip_emotion_tag(m.content) or m.content,
            }
            for m in msgs
        ],
    }


@router.post("", response_model=ChatSessionOut, status_code=201)
async def create_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    session = ChatSession(user_id=user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
