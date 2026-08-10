"""记忆服务：三级记忆组装 / 长期记忆写入 / 自动总结。

调用流程（见需求文档 §4.4.2）：
用户发消息 → 检索画像(PostgreSQL) → 检索长期记忆(ChromaDB Top-K)
→ 拼接近期短期记忆(Redis) → 组装 Prompt → LLM 生成回复
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import chroma_client
from app.core.redis_client import ShortMemoryStore
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import LongTermMemory
from app.models.user import UserProfile
from app.services.emotion import detect_emotion
from app.services.llm_client import llm

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """你是一个温暖、善解人意的AI朋友。以下是与当前用户的对话历史和相关信息：

【用户画像】
{profile}

【长期记忆】（AI自动总结的过往重要信息）
{memories}

【近期对话】（最近{rounds}轮）
{recent}

【当前用户情绪感知】：{detected_emotion}

请以温暖、共情的语气回复用户，自然地引用长期记忆中的信息（如"上次你说过..."），回复不超过150字。同时根据用户最后一句话判断其当前情绪，在回复结尾用【情绪标签：xxx】标注（只能取：开心/平静/低落/焦虑/愤怒 之一）。"""


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _profile_text(profile: UserProfile | None) -> str:
    if not profile:
        return "- 用户暂未填写画像"
    return "\n".join(
        f"- {k}: {v}"
        for k, v in {
            "姓名": profile.name,
            "年龄": profile.age,
            "职业": profile.occupation,
            "核心目标": profile.goal,
            "长期困扰": profile.struggle,
        }.items()
        if v
    )


async def build_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    user_content: str,
) -> str:
    """并行检索三级记忆并组装 Prompt。"""
    profile = await get_profile(db, user_id)

    memories: list[dict] = []
    try:
        memories = await chroma_client.query_memories(
            str(user_id), user_content, top_k=settings.MEMORY_TOP_K
        )
    except Exception as exc:  # Chroma 不可用时降级为空记忆
        logger.warning("长期记忆检索失败，降级处理: %s", exc)

    short_store = ShortMemoryStore(str(session_id))
    recent = await short_store.recent(settings.SHORT_MEMORY_ROUNDS)
    recent_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent[-10:]) or "（暂无）"

    mem_text = "\n".join(f"- {m['content']}" for m in memories) or "（暂无）"
    emotion = detect_emotion(user_content)

    return PROMPT_TEMPLATE.format(
        profile=_profile_text(profile),
        memories=mem_text,
        recent=recent_text,
        rounds=settings.SHORT_MEMORY_ROUNDS,
        detected_emotion=f"{emotion.label}({emotion.score:.2f})",
    )


async def save_memory(db: AsyncSession, user_id: uuid.UUID, summary: str, memory_type: str = "event") -> None:
    """写入长期记忆：ChromaDB 向量 + PostgreSQL 摘要表。"""
    memory_id = str(uuid.uuid4())
    try:
        await chroma_client.add_memory(str(user_id), memory_id, summary, memory_type)
    except Exception as exc:
        logger.warning("Chroma 写入失败: %s", exc)
        return
    record = LongTermMemory(
        user_id=user_id, summary=summary, memory_type=memory_type
    )
    db.add(record)
    await db.commit()


async def maybe_summarize(db: AsyncSession, session: ChatSession, user_id: uuid.UUID) -> None:
    """每满 SUMMARY_EVERY_ROUNDS 轮触发一次异步总结（不阻塞回复）。"""
    if session.message_count % settings.SUMMARY_EVERY_ROUNDS != 0:
        return
    messages = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    )
    rows = messages.scalars().all()
    transcript = "\n".join(f"{m.role}: {m.content}" for m in rows[-10:])
    try:
        summary = await llm.chat(
            [
                {
                    "role": "system",
                    "content": "你是记忆提炼助手。请从对话中提炼：关键事件、用户情绪状态变化、用户偏好。"
                    "输出 2-3 句简洁中文，以'用户'为主语。",
                },
                {"role": "user", "content": transcript},
            ]
        )
        if summary.strip():
            await save_memory(db, user_id, summary.strip(), "event")
    except Exception as exc:
        logger.warning("自动总结失败: %s", exc)
