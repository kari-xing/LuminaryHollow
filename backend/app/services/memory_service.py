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
from app.core.database import SessionLocal
from app.core.redis_client import ShortMemoryStore
from app.models.chat import ChatMessage, ChatSession
from app.models.memory import LongTermMemory
from app.models.user import UserProfile
from app.services.emotion import EmotionResult, detect_emotion
from app.services.llm_client import llm

logger = logging.getLogger(__name__)

# 每种情绪对应的「陪伴策略」：让检测到的情绪真正驱动 AI 的回应方式
EMOTION_STRATEGY: dict[str, str] = {
    "开心": "用户正在分享喜悦。先真诚地为他高兴、追问开心的细节，让快乐被放大。不要急着分析或给建议。",
    "平静": "用户在平静地叙述。像老朋友一样自然回应，可以轻轻引导他多说一点，保持轻松陪伴感。",
    "低落": "用户情绪低落。先温柔接住这份情绪（如「我在呢」「辛苦了」），允许他低落，别急着讲道理或灌鸡汤；等情绪被看见后，再给一点温暖和力量。",
    "焦虑": "用户感到焦虑。先帮他慢下来、共情安抚，再温和地陪他拆解：具体在担心什么、什么是他能控制的；最后给一个很小、可执行的第一步。不要空洞地说「别担心」。",
    "愤怒": "用户有愤怒的情绪。先接纳他的愤怒，不评判、不急着讲道理，让他感到被理解；可以温柔地问问发生了什么，帮他梳理情绪背后的真实需求。",
}

SYSTEM_PROMPT_TEMPLATE = """你是「心光树洞」，一个温暖、会倾听、有记忆的AI朋友。你和用户已经聊过一段时间了，像认识很久的微信好友。

【你的说话方式】
- 口语、短句、自然，偶尔带语气词（嗯、呢、哈、呀），绝不用书面语，不说「您」；
- 真诚第一：先接住情绪，再回应内容；不堆大词、不说教、不灌鸡汤、不一条条列建议；
- 记得你说过的话：自然地引用你记得的过往（如「上次你说……」），让用户感到被记得、被在乎。

【用户画像】
{profile}

【你记得的过往】
{memories}

【刚才的对话】
{recent}

【用户此刻的情绪】{emotion}（强度 {intensity:.0%}）
【此刻你该怎么做】{strategy}

【回复结构】（自然融入，不要出现小标题）
1. 一句简短真诚的共情；
2. 自然回应他说的内容，可引用记忆；
3. 温和收尾，或给一个很小、可行的行动提议。

【防重复铁律】
- 绝不重复自己的话、不复述或转述用户的话，每轮都是全新内容；
- 避免每轮都用相同的套话开头（如"我理解""辛苦了""我在这"），用不同的自然表达；
- 上一轮说过的话，这轮不要再原样再说。

【硬性要求】
- 全文不超过 120 字；
- 结尾另起一行用【情绪标签：xxx】标注用户当前情绪（只能是：开心/平静/低落/焦虑/愤怒）。"""


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
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    user_content: str,
    emotion: EmotionResult | None = None,
) -> str:
    """并行检索三级记忆并组装 Prompt（情绪驱动对话风格）。

    使用独立短生命周期数据库会话执行只读查询：
    - 与调用方会话解耦，不干扰其事务与 ORM 对象状态
    - 查询结束自动关闭会话、归还连接，LLM 流式期间不占数据库连接
    """
    profile_text = "- 用户暂未填写画像"
    async with SessionLocal() as query_db:
        profile = await get_profile(query_db, user_id)
        profile_text = _profile_text(profile)  # 会话内提取，避免关闭后对象过期
    # query_db 已自动关闭，连接归还

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
    emotion = emotion or detect_emotion(user_content)

    return SYSTEM_PROMPT_TEMPLATE.format(
        profile=profile_text,
        memories=mem_text,
        recent=recent_text,
        emotion=emotion.label,
        intensity=emotion.intensity,
        strategy=EMOTION_STRATEGY.get(emotion.label, EMOTION_STRATEGY["平静"]),
    )


async def save_memory(user_id: uuid.UUID, summary: str, memory_type: str = "event") -> None:
    """写入长期记忆：ChromaDB 向量 + PostgreSQL 摘要表（独立会话）。"""
    memory_id = str(uuid.uuid4())
    try:
        await chroma_client.add_memory(str(user_id), memory_id, summary, memory_type)
    except Exception as exc:
        logger.warning("Chroma 写入失败: %s", exc)
        return
    async with SessionLocal() as db:
        record = LongTermMemory(
            user_id=user_id, summary=summary, memory_type=memory_type
        )
        db.add(record)
        await db.commit()


async def maybe_summarize(session: ChatSession, user_id: uuid.UUID) -> None:
    """每满 SUMMARY_EVERY_ROUNDS 轮触发一次异步总结（独立会话，不阻塞回复）。"""
    if session.message_count % settings.SUMMARY_EVERY_ROUNDS != 0:
        return
    # 独立会话只读查询，关闭后不占用连接，也避免污染主会话对象状态
    transcript = ""
    async with SessionLocal() as query_db:
        messages = await query_db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
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
            await save_memory(user_id, summary.strip(), "event")
    except Exception as exc:
        logger.warning("自动总结失败: %s", exc)
