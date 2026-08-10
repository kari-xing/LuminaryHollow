"""数据导出接口：JSON / Markdown 打包为 ZIP。"""
import io
import json
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import LongTermMemory
from app.models.user import User, UserProfile

router = APIRouter()


async def _collect_data(db: AsyncSession, user: User) -> dict:
    sessions = (
        await db.execute(
            select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.started_at)
        )
    ).scalars().all()
    memories = (
        await db.execute(select(LongTermMemory).where(LongTermMemory.user_id == user.id))
    ).scalars().all()
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()

    chat_history = []
    for s in sessions:
        msgs = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at)
            )
        ).scalars().all()
        chat_history.append(
            {
                "session_id": str(s.id),
                "started_at": s.started_at.isoformat(),
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "emotion_label": m.emotion_label,
                        "emotion_score": m.emotion_score,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in msgs
                ],
            }
        )
    return {
        "user": {"username": user.username, "email": user.email, "created_at": user.created_at.isoformat()},
        "profile": {
            "name": profile.name, "age": profile.age, "occupation": profile.occupation,
            "goal": profile.goal, "struggle": profile.struggle,
        } if profile else {},
        "chat_history": chat_history,
        "memories": [
            {"summary": m.summary, "memory_type": m.memory_type, "created_at": m.created_at.isoformat()}
            for m in memories
        ],
    }


def _to_markdown(data: dict) -> str:
    lines = ["# 心光树洞 对话记录导出", ""]
    lines.append(f"用户：{data['user'].get('username', '')}")
    lines.append(f"邮箱：{data['user'].get('email', '')}")
    lines.append("")
    for session in data["chat_history"]:
        lines.append(f"## 会话 {session['session_id'][:8]}（{session['started_at']}）")
        for m in session["messages"]:
            tag = f" [{m['emotion_label']}]" if m.get("emotion_label") else ""
            lines.append(f"- **{'用户' if m['role']=='user' else 'AI'}**{tag}：{m['content']}")
        lines.append("")
    if data["memories"]:
        lines.append("## 长期记忆")
        for m in data["memories"]:
            lines.append(f"- [{m['memory_type']}] {m['summary']}")
    return "\n".join(lines)


@router.get("")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    data = await _collect_data(db, user)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("chat_history.json", json.dumps(data, ensure_ascii=False, indent=2))
        zf.writestr("chat_history.md", _to_markdown(data))
        zf.writestr("profile.json", json.dumps(data["profile"], ensure_ascii=False, indent=2))
        zf.writestr(
            "memories.md",
            "\n".join(f"- [{m['memory_type']}] {m['summary']}" for m in data["memories"]),
        )
    buffer.seek(0)
    filename = f"export-{user.id}-{user.username}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
