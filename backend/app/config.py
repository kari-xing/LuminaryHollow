"""全局配置：全部通过环境变量 / .env 注入。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    PROJECT_NAME: str = "心光树洞 LuminaryHollow"
    API_V1_PREFIX: str = "/api"

    # 安全
    SECRET_KEY: str = "dev-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # 存储
    DATABASE_URL: str = "postgresql+asyncpg://hollow:hollow@localhost:5432/hollow"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8012

    # LLM（provider: ollama 本地 / openai 兼容云端，如 DeepSeek、OpenRouter、通义等）
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5"
    LLM_API_KEY: str = ""
    # Embedding 独立配置：DeepSeek 等云端 API 无 embedding 接口，向量化固定走本地 Ollama
    EMBED_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_TIMEOUT_SECONDS: int = 180

    # 记忆参数
    SHORT_MEMORY_ROUNDS: int = 10      # 短期记忆滑动窗口轮数
    SHORT_MEMORY_TTL_SECONDS: int = 24 * 3600
    SUMMARY_EVERY_ROUNDS: int = 5      # 每 N 轮触发自动总结
    MEMORY_TOP_K: int = 5              # 长期记忆召回条数
    MEMORY_DEDUP_THRESHOLD: float = 0.85

    # 定时任务
    WEEKLY_REPORT_CRON: str = "0 22 * * 0"

    # CORS 白名单
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:80"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
