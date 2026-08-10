"""Redis 客户端：短期记忆滑动窗口 / 会话缓存 / 心跳状态。"""
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """获取单例异步 Redis 客户端（惰性初始化）。"""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True, encoding="utf-8"
        )
    return _redis


class ShortMemoryStore:
    """短期记忆：以 List 实现滑动窗口（最近 N 轮），TTL 24h。"""

    KEY = "mem:short:{session_id}"

    def __init__(self, session_id: str):
        self.key = self.KEY.format(session_id=session_id)
        self.client = get_redis()

    async def push(self, role: str, content: str, meta: dict[str, Any] | None = None) -> None:
        entry = {"role": role, "content": content, **(meta or {})}
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.rpush(self.key, json.dumps(entry, ensure_ascii=False))
            await pipe.ltrim(self.key, -settings.SHORT_MEMORY_ROUNDS * 2, -1)
            await pipe.expire(self.key, settings.SHORT_MEMORY_TTL_SECONDS)
            await pipe.execute()

    async def recent(self, rounds: int | None = None) -> list[dict[str, Any]]:
        items = await self.client.lrange(self.key, 0, -1)
        parsed = []
        for item in items:
            try:
                parsed.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return parsed[- (rounds or settings.SHORT_MEMORY_ROUNDS) * 2:]

    async def clear(self) -> None:
        await self.client.delete(self.key)


async def set_privacy_mode(user_id: str, enabled: bool) -> None:
    await get_redis().set(f"privacy:{user_id}", "1" if enabled else "0")


async def get_privacy_mode(user_id: str) -> bool:
    return bool(await get_redis().get(f"privacy:{user_id}"))
