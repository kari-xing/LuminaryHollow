"""WebSocket 对话端点 /ws/chat/{session_id}。

消息协议（JSON）：
- 客户端: {"type":"user_message","content":"..."}
          {"type":"quick_checkin","emotion_label":"焦虑"}
- 服务端: typing / stream_chunk / stream_end / quick_ok / error / ping
"""
import asyncio
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import SessionLocal
from app.core.redis_client import ShortMemoryStore, get_privacy_mode, set_privacy_mode
from app.core.security import decode_token
from app.models.chat import ChatMessage, ChatSession
from app.services.emotion import detect_emotion, parse_emotion_from_reply
from app.services.llm_client import llm
from app.services.memory_service import build_prompt, maybe_summarize
from app.ws import protocol as P
from app.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()

_FALLBACK_REPLIES = [
    "我在呢，愿意继续和我说说吗？",
    "嗯嗯，我听到了，可以多说一点吗？",
    "不论如何，我都在这里陪着你。",
]


async def _handle_user_message(db: AsyncSession, session: ChatSession, user_id: uuid.UUID, ws_id: str, content: str) -> None:
    """处理一条用户消息：三级记忆 → LLM 流式 → 情绪解析 → 落库。"""
    privacy = await get_privacy_mode(str(user_id))

    # 1. 落库用户消息 + 写入短期记忆
    user_msg = ChatMessage(
        session_id=session.id, role="user", content=content, is_private=privacy
    )
    db.add(user_msg)
    session.message_count += 1
    await db.commit()

    short_store = ShortMemoryStore(str(session.id))
    await short_store.push("user", content, {"emotion": detect_emotion(content).label})

    # 2. 通知前端"正在输入"
    await manager.send_json(ws_id, {"type": P.TYPE_TYPING})

    # 3. 组装 Prompt（画像 + 长期记忆 + 短期记忆）
    prompt = await build_prompt(db, user_id, session.id, content)
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]

    # 4. LLM 流式输出并转发
    chunks: list[str] = []
    try:
        async for delta in llm.stream_chat(messages):
            chunks.append(delta)
            await manager.send_json(ws_id, {"type": P.TYPE_STREAM_CHUNK, "content": delta})
    except Exception as exc:
        logger.warning("LLM 流式失败，降级为规则回复: %s", exc)
        fallback = _FALLBACK_REPLIES[session.message_count % len(_FALLBACK_REPLIES)]
        for ch in fallback:
            chunks.append(ch)
            await manager.send_json(ws_id, {"type": P.TYPE_STREAM_CHUNK, "content": ch})
            await asyncio.sleep(0.02)

    reply = "".join(chunks)

    # 5. 情绪解析（Prompt 要求尾标【情绪标签：xxx】，正则提取 + 兜底）
    emotion = parse_emotion_from_reply(reply)

    # 6. AI 回复落库 + 写短期记忆
    ai_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply,
        emotion_label=emotion.label,
        emotion_score=emotion.score,
        is_private=privacy,
    )
    db.add(ai_msg)
    await db.commit()
    await short_store.push("assistant", reply, {"emotion_label": emotion.label})

    # 7. 更新会话平均情绪分 + 每 N 轮异步总结
    session.avg_emotion_score = (
        session.avg_emotion_score or 0
    )  # 原型简化：真实聚合在看板层
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
        {"type": P.TYPE_STREAM_END, "emotion_label": emotion.label, "emotion_score": emotion.score},
    )

    if not privacy:
        await maybe_summarize(db, session, user_id)


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
