"""LLM 适配层：Ollama（本地）与云端 API 可配置切换。

- stream_chat: 流式对话（Ollama /api/chat）
- embed: 文本向量化（/api/embed）
- summarize: 单次非流式总结
"""
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str = ""):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.api_key = api_key or settings.LLM_API_KEY

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def stream_chat(self, messages: list[dict]):
        """流式对话：逐块产出文本增量。Ollama 每行一个 JSON 对象。"""
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", url, json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("message") or {}).get("content") or ""
                    if delta:
                        yield delta

    async def chat(self, messages: list[dict]) -> str:
        """非流式对话（用于总结、周报等一次性调用）。"""
        chunks = []
        async for chunk in self.stream_chat(messages):
            chunks.append(chunk)
        return "".join(chunks)

    async def embed(self, text: str) -> list[float]:
        """文本向量化，返回 768/1024 维向量。"""
        url = f"{self.base_url}/api/embed"
        payload = {"model": settings.EMBEDDING_MODEL, "input": text}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings")
            if embeddings:
                return embeddings[0]
            return data.get("embedding", [])


llm = LLMClient()
