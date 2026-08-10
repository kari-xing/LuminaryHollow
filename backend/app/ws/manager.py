"""WebSocket 连接管理器：连接注册 / 广播 / 清理。"""
import asyncio
import uuid

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # session_id -> set[WebSocket]
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            conns = self._connections.get(session_id)
            if conns:
                # 同一会话只保留最新连接：先关闭旧连接，避免新旧并存时
                # send_json 把同一份消息广播两份 → 前端收到重复的流式内容。
                for old in list(conns):
                    try:
                        await old.close()
                    except Exception:
                        pass
                conns.clear()
            self._connections.setdefault(session_id, set()).add(ws)

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(session_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    self._connections.pop(session_id, None)

    async def send_json(self, session_id: str, payload: dict) -> None:
        conns = list(self._connections.get(session_id, set()))
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(session_id, ws)


manager = ConnectionManager()
