"""ChromaDB 客户端：长期记忆向量写入 / 检索 / 删除。"""
import logging
import os
import uuid

# 绕过 Windows 系统代理：ChromaDB 内部 httpx 默认读取系统代理，
# 会把 localhost 请求误发给代理（如 Clash localhost:29758）导致 503
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.llm_client import llm

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None


def get_chroma() -> chromadb.ClientAPI:
    """惰性初始化 ChromaDB 客户端（持久化目录 ./chroma_data）。"""
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.CHROMA_HOST, port=settings.CHROMA_PORT
        )
    return _client


def _collection(user_id: str):
    """按用户隔离 collection。"""
    return get_chroma().get_or_create_collection(name=f"user_{user_id}")


async def add_memory(user_id: str, memory_id: str, summary: str, memory_type: str) -> None:
    """写入一条长期记忆（向量 = embedding）。"""
    embedding = await llm.embed(summary)
    _collection(user_id).upsert(
        ids=[memory_id],
        documents=[summary],
        embeddings=[embedding],
        metadatas=[{"memory_type": memory_type}],
    )


async def query_memories(user_id: str, query: str, top_k: int | None = None) -> list[dict]:
    """按语义相似度检索 Top-K 长期记忆。"""
    k = top_k or settings.MEMORY_TOP_K
    col = _collection(user_id)
    if col.count() == 0:
        return []
    embedding = await llm.embed(query)
    result = col.query(query_embeddings=[embedding], n_results=k)
    docs, metas, dists = result["documents"], result["metadatas"], result["distances"]
    return [
        {"content": doc, "memory_type": meta.get("memory_type", ""), "distance": dist}
        for doc, meta, dist in zip((docs or [[]])[0], (metas or [[]])[0], (dists or [[]])[0])
    ]


def delete_memory(user_id: str, memory_id: str) -> None:
    _collection(user_id).delete(ids=[memory_id])


def clear_memories(user_id: str) -> None:
    get_chroma().delete_collection(name=f"user_{user_id}")


def new_memory_id() -> str:
    return str(uuid.uuid4())
