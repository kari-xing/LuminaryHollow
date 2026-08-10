"""LLM 适配层：支持 Ollama 本地与 OpenAI 兼容云端 API 双 Provider。

- provider=ollama：Ollama 本地 `/api/chat` 流式
- provider=openai：OpenAI 兼容接口（DeepSeek / OpenRouter / 通义等）`/chat/completions` SSE 流式
- embed：独立使用本地 Ollama embedding（DeepSeek 等云端 API 无 embedding 接口）
- chat：非流式对话（用于记忆总结 / 周报等一次性调用）
"""
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        provider: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str = "",
        embed_base_url: str | None = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.api_key = api_key or settings.LLM_API_KEY
        self.embed_base_url = (embed_base_url or settings.EMBED_BASE_URL).rstrip("/")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def stream_chat(self, messages: list[dict]):
        """流式对话：按 provider 分发到对应实现，逐块产出文本增量。"""
        if self.provider == "openai":
            async for chunk in self._stream_openai(messages):
                yield chunk
        else:
            async for chunk in self._stream_ollama(messages):
                yield chunk

    async def _stream_ollama(self, messages: list[dict]):
        """Ollama 流式：每行一个 JSON 对象。"""
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(
            timeout=settings.LLM_TIMEOUT_SECONDS, trust_env=False
        ) as client:
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

    async def _stream_openai(self, messages: list[dict]):
        """OpenAI 兼容 SSE 流式：`data: {json}` 行，`data: [DONE]` 结束。"""
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(
            timeout=settings.LLM_TIMEOUT_SECONDS, trust_env=False
        ) as client:
            async with client.stream("POST", url, json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        yield content

    async def chat(self, messages: list[dict]) -> str:
        """非流式对话（用于总结、周报等一次性调用）。"""
        chunks = []
        async for chunk in self.stream_chat(messages):
            chunks.append(chunk)
        return "".join(chunks)

    async def embed(self, text: str) -> list[float]:
        """文本向量化：固定走本地 Ollama embedding（云端 API 通常无 embedding 接口）。"""
        url = f"{self.embed_base_url}/api/embed"
        payload = {"model": settings.EMBEDDING_MODEL, "input": text}
        # trust_env=False：绕过系统代理，本地 Ollama 直连（Windows 系统代理会把 localhost 请求误发到代理）
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post(
                url, json=payload, headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings")
            if embeddings:
                return embeddings[0]
            return data.get("embedding", [])


llm = LLMClient()

