"""记忆管理接口：列表 / 删除 / 清空。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import chroma_client
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import LongTermMemory
from app.models.user import User

router = APIRouter()


@router.get("", response_model=dict)
async def list_memories(
    memory_type: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(LongTermMemory).where(LongTermMemory.user_id == user.id)
    if memory_type:
        stmt = stmt.where(LongTermMemory.memory_type == memory_type)
    total = len((await db.execute(stmt)).scalars().all())
    rows = (
        await db.execute(
            stmt.order_by(LongTermMemory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(m.id),
                "summary": m.summary,
                "memory_type": m.memory_type,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ],
        "total": total,
        "page": page,
    }


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    memory = await db.get(LongTermMemory, memory_id)
    if memory is None or memory.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": 4040, "message": "记忆不存在"})
    chroma_client.delete_memory(str(user.id), str(memory_id))
    await db.delete(memory)
    await db.commit()


@router.delete("", status_code=204)
async def clear_memories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    chroma_client.clear_memories(str(user.id))
    await db.execute(delete(LongTermMemory).where(LongTermMemory.user_id == user.id))
    await db.commit()
