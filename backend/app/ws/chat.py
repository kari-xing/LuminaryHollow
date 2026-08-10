"""WebSocket 对话端点 /ws/chat/{session_id}。

消息协议（JSON）：
- 客户端: {"type":"user_message","content":"..."}
          {"type":"quick_checkin","emotion_label":"焦虑"}
- 服务端: typing / stream_chunk / stream_end / quick_ok / error / ping
"""
import asyncio
import logging
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import SessionLocal
from app.core.redis_client import ShortMemoryStore, get_privacy_mode, set_privacy_mode
from app.core.security import decode_token
from app.models.chat import ChatMessage, ChatSession
from app.models.schedule import ScheduleItem
from app.services.emotion import (
    detect_emotion,
    parse_emotion_from_reply,
    strip_emotion_tag,
)
from app.services.llm_client import llm
from app.services.memory_service import build_prompt, maybe_summarize
from app.ws import protocol as P
from app.ws.manager import manager

logger = logging.getLogger(__name__)
chat_log = logging.getLogger("luminary.chat")  # 对话详情 → logs/chat.log
router = APIRouter()

# LLM 离线时的降级回复：按用户情绪定制，保持「贴近人」
_FALLBACK_REPLIES: dict[str, list[str]] = {
    "开心": [
        "哇，真替你高兴！愿意多跟我说说吗？",
        "这太好了，我都能想象你开心的样子～",
    ],
    "平静": [
        "嗯嗯，我在听，你接着说？",
        "好，我懂你的意思，我们慢慢聊。",
    ],
    "低落": [
        "我在呢。想说什么都可以，我陪着你。",
        "辛苦了，抱抱你。愿意的话，多跟我说说？",
    ],
    "焦虑": [
        "别急，我们先慢慢捋一捋。你具体在担心哪一步呢？",
        "深呼吸一下，我在呢。把最让你紧张的那件事跟我说说？",
    ],
    "愤怒": [
        "遇到这种事确实让人生气，我理解你。愿意跟我说说发生了什么吗？",
        "这真的挺让人火大的，我在听，你说。",
    ],
}
_FALLBACK_DEFAULT = "我在呢，愿意继续和我说说吗？"

# 检测「今天还有什么安排 / 今天还有什么事没干 / 今天的日程安排 / 我今天要干什么」这类日程查询
_SCHEDULE_QUERY_RE = re.compile(
    r"(今天|今日|现在|明天|今天还有|还有|剩下).{0,12}?"
    r"(什么事|什么安排|什么日程|什么待办|哪些事|哪些安排|有什么|有啥|还有什么事|没干|没做|"
    r"要干什么|要做什么|干什么|做什么|干嘛|日程安排|今日安排|的安排|的日程|的待办|日程|待办|安排是)"
)


async def _get_today_schedule_text(db: AsyncSession, user_id: uuid.UUID) -> str:
    """返回今天（本地时区）的日程摘要；无日程返回空字符串。"""
    tz = ZoneInfo(settings.TIMEZONE)
    now_local = datetime.now(tz)
    today = now_local.date()
    start = datetime.combine(today, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    stmt = (
        select(ScheduleItem)
        .where(
            ScheduleItem.user_id == user_id,
            ScheduleItem.due_at >= start,
            ScheduleItem.due_at < end,
        )
        .order_by(ScheduleItem.due_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return ""
    lines = []
    for it in rows:
        local = it.due_at.astimezone(tz)
        if it.done:
            status = "已完成"
        elif local < now_local:
            status = "已过期未完成"
        else:
            status = "未完成"
        lines.append(f"- {local.strftime('%H:%M')} {it.content}（{status}）")
    return "今天的日程安排：\n" + "\n".join(lines)


async def _stream_reply(user_emotion, session_id: uuid.UUID, messages: list[dict]) -> tuple[str, bool]:
    """LLM 流式生成回复；返回 (回复文本, 是否降级)。"""
    import random

    chunks: list[str] = []
    degraded = False
    try:
        async for delta in llm.stream_chat(messages):
            chunks.append(delta)
    except Exception as exc:
        logger.warning("LLM 流式失败，降级为规则回复: %s", exc)
        degraded = True
        candidates = _FALLBACK_REPLIES.get(user_emotion.label, [_FALLBACK_DEFAULT])
        chunks.append(random.choice(candidates))
    return "".join(chunks), degraded


async def _is_repetitive(short_store, reply: str) -> bool:
    """检测回复是否与近期 AI 回复雷同（≥10 字符连续重叠即判重复）。"""
    if len(reply) < 12:
        return False
    recent = await short_store.recent(6)
    for m in recent:
        if m.get("role") != "assistant":
            continue
        prev = m.get("content", "")
        if not prev or len(prev) < 12:
            continue
        # 当前回复是否几乎等于历史回复 / 存在长串重叠
        if reply == prev:
            return True
        for i in range(0, len(reply) - 9):
            if reply[i:i + 10] in prev:
                return True
    return False


async def _handle_user_message(db: AsyncSession, session: ChatSession, user_id: uuid.UUID, ws_id: str, content: str) -> None:
    """处理一条用户消息：三级记忆 → LLM 流式 → 情绪解析 → 落库。"""
    import time as _time

    start_ts = _time.time()
    privacy = await get_privacy_mode(str(user_id))
    user_emotion = detect_emotion(content)  # 规则感知（含强度），供 Prompt 与前端使用
    chat_log.info("== 用户[%s] 会话[%s] 消息[%s] 规则情绪=%s(%.0f%%)",
                  user_id, session.id, content[:200], user_emotion.label, user_emotion.intensity * 100)

    # 1. 落库用户消息 + 写入短期记忆
    user_msg = ChatMessage(
        session_id=session.id, role="user", content=content, is_private=privacy
    )
    db.add(user_msg)
    session.message_count += 1
    await db.commit()

    short_store = ShortMemoryStore(str(session.id))
    await short_store.push(
        "user", content,
        {"emotion": user_emotion.label, "intensity": user_emotion.intensity},
    )

    # 2. 通知前端"正在输入"
    await manager.send_json(ws_id, {"type": P.TYPE_TYPING})

    # 3. 组装 Prompt（画像 + 长期记忆 + 短期记忆 + 情绪策略；内部独立会话，不占本会话连接）
    prompt = await build_prompt(user_id, session.id, content, emotion=user_emotion)
    # 用户询问「今天还有什么安排/日程/事没干」→ 注入今日日程，让 AI 用朋友口吻自然回复
    if _SCHEDULE_QUERY_RE.search(content):
        schedule_note = await _get_today_schedule_text(db, user_id)
        if schedule_note:
            prompt += (
                "\n\n【用户正在询问今天的安排，请用朋友口吻把日程回复给他】\n"
                + schedule_note
                + "\n规则：口语化带过即可，不要列小标题；未完成或已过期的日程温柔提醒、不要责怪；"
                + "先正面回答今天还有哪些事，再给一句鼓励。"
            )
        else:
            prompt += (
                "\n\n【用户正在询问今天的安排】他今天没有任何日程。"
                "请轻松地告诉他今天很自由，可以好好放松，或临时想做点什么也好。"
            )
    chat_log.info("--- Prompt[%s] 情绪策略=%s ---", session.id, user_emotion.label)
    chat_log.info("%s", prompt[:800])
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]

    # 4. LLM 流式生成（完整生成后做重复检测，再以打字机效果转发给前端）
    reply, degraded = await _stream_reply(user_emotion, session.id, messages)
    if not degraded and await _is_repetitive(short_store, reply):
        chat_log.warning("会话[%s] 检测到与近期回复重复，重新生成", session.id)
        reply2, _ = await _stream_reply(user_emotion, session.id, messages)
        if not await _is_repetitive(short_store, reply2):
            reply = reply2
    for ch in reply:
        await manager.send_json(ws_id, {"type": P.TYPE_STREAM_CHUNK, "content": ch})
        await asyncio.sleep(0.012)

    # 5. 情绪解析（Prompt 要求尾标【情绪标签：xxx】，正则提取 + 别名映射 + 规则兜底）
    emotion = parse_emotion_from_reply(reply)
    emotion.intensity = user_emotion.intensity  # 强度取用户消息感知结果
    reply_display = strip_emotion_tag(reply) or reply  # 剥离标签，仅内部解析不展示

    # 重复检测：AI 是否复述了用户原话 / 是否与近期回复雷同
    echo_hits = [kw for kw in ("我理解", "辛苦了", "我在这", "我在这儿", "抱抱", "别担心") if kw in reply]
    elapsed = _time.time() - start_ts
    chat_log.info("--- AI[%s] 原始回复(%.1fs) ---\n%s", session.id, elapsed, reply[:500])
    chat_log.info("--- AI 展示内容(标签已剥离) ---\n%s", reply_display[:500])
    chat_log.info("--- 解析情绪=%s 复述/套话命中=%s ---", emotion.label, echo_hits or "无")

    # 6. AI 回复落库 + 写短期记忆
    ai_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_display,
        emotion_label=emotion.label,
        emotion_score=emotion.score,
        is_private=privacy,
    )
    db.add(ai_msg)
    await db.commit()
    await short_store.push(
        "assistant", reply_display,
        {"emotion_label": emotion.label, "intensity": emotion.intensity},
    )

    # 7. 更新会话平均情绪分 + 每 N 轮异步总结
    session.avg_emotion_score = session.avg_emotion_score or 0
    if session.message_count % 2 == 0:
        session.avg_emotion_score = round(
            (
                (session.avg_emotion_score or 0) * (session.message_count - 1) + emotion.score
            ) / session.message_count,
            3,
        )
    await db.commit()

    await manager.send_json(
        ws_id,
        {
            "type": P.TYPE_STREAM_END,
            "emotion_label": emotion.label,
            "emotion_score": emotion.score,
            "emotion_intensity": emotion.intensity,
        },
    )

    if not privacy:
        await maybe_summarize(session, user_id)
    # 注意：此处不调用 rollback —— 独立会话方案下主会话每次消息处理已 commit 结束事务；
    # 对主会话 rollback 会使其 ORM 对象过期，下一次同步属性访问会触发 MissingGreenlet


@router.websocket("/ws/chat/{session_id}")
async def chat_ws(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str = Query(default=""),
) -> None:
    """握手鉴权 → 连接注册 → 消息循环。"""
    user_id = decode_token(token, expected_type="access")
    if not user_id:
        await websocket.close(code=4401)
        return

    async with SessionLocal() as db:
        session = await db.get(ChatSession, session_id)
        if session is None or str(session.user_id) != user_id:
            await websocket.close(code=4403)
            return

        await manager.connect(str(session.id), websocket)
        try:
            while True:
                raw = await websocket.receive_json()
                msg_type = raw.get("type", P.TYPE_USER_MESSAGE)

                if msg_type == P.TYPE_QUICK_CHECKIN:
                    label = raw.get("emotion_label", "")
                    score = detect_emotion(label).score
                    checkin = ChatMessage(
                        session_id=session.id,
                        role="user",
                        content=f"[快捷情绪打卡] {label}",
                        emotion_label=label,
                        emotion_score=score,
                        is_quick_checkin=True,
                        is_private=await get_privacy_mode(user_id),
                    )
                    db.add(checkin)
                    await db.commit()
                    await manager.send_json(
                        str(session.id),
                        {"type": P.TYPE_QUICK_OK, "emotion_label": label, "emotion_score": score},
                    )
                    continue

                content = (raw.get("content") or "").strip()
                if not content:
                    continue
                await _handle_user_message(db, session, uuid.UUID(user_id), str(session.id), content)

        except WebSocketDisconnect:
            logger.info("WebSocket 断开: session=%s", session.id)
        finally:
            await manager.disconnect(str(session.id), websocket)
            session.ended_at = None  # 保留会话，等待超时任务关闭
            await db.commit()
