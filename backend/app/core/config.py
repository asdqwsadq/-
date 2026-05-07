from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parents[3]
    app_name: str = "Kongming Agent"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    )
    default_agent_code: str = _env("DEFAULT_AGENT_CODE", "kongming")
    default_model_name: str = _env("DEFAULT_MODEL_NAME", "gpt-4.1-mini")
    default_temperature: float = float(_env("DEFAULT_TEMPERATURE", "0.5"))
    default_max_tokens: int = int(_env("DEFAULT_MAX_TOKENS", "1500"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = _env("OPENAI_MODEL", "gpt-4.1-mini")
    chat_history_limit: int = int(_env("CHAT_HISTORY_LIMIT", "12"))
    knowledge_top_k: int = int(_env("KNOWLEDGE_TOP_K", "4"))
    ollama_base_url: str = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_chunk_model: str = _env("OLLAMA_CHUNK_MODEL", "qwen2.5:14b")
    ollama_embedding_model: str = _env("OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m")
    milvus_host: str = _env("MILVUS_HOST", "127.0.0.1")
    milvus_port: int = int(_env("MILVUS_PORT", "19530"))
    milvus_collection: str = _env("MILVUS_COLLECTION", "four_classics_chunks")
    embedding_dim: int = int(_env("EMBEDDING_DIM", "768"))
    chunk_target_size: int = int(_env("CHUNK_TARGET_SIZE", "1200"))
    chunk_max_size: int = int(_env("CHUNK_MAX_SIZE", "1800"))
    use_llm_chunk_planning: bool = _env("USE_LLM_CHUNK_PLANNING", "0") == "1"
    embedding_workers: int = int(_env("EMBEDDING_WORKERS", "1"))
    embedding_request_timeout: float = float(_env("EMBEDDING_REQUEST_TIMEOUT", "45"))
    chat_request_timeout: float = float(_env("CHAT_REQUEST_TIMEOUT", "90"))
    allow_chat_embedding_fallback: bool = _env("ALLOW_CHAT_EMBEDDING_FALLBACK", "0") == "1"
    dashscope_api_key: str | None = os.getenv("DASHSCOPE_API_KEY")
    dashscope_base_url: str = _env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    dashscope_embedding_model: str = _env("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
    dashscope_embedding_dimensions: int = int(_env("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024"))
    dashscope_embedding_batch_size: int = int(_env("DASHSCOPE_EMBEDDING_BATCH_SIZE", "10"))
    dashscope_embedding_request_timeout: float = float(_env("DASHSCOPE_EMBEDDING_REQUEST_TIMEOUT", "60"))
    mysql_host: str = _env("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(_env("MYSQL_PORT", "3306"))
    mysql_user: str = _env("MYSQL_USER", "root")
    mysql_password: str = _env("MYSQL_PASSWORD", "")
    mysql_database: str = _env("MYSQL_DATABASE", "kongming_agent")
    mysql_charset: str = _env("MYSQL_CHARSET", "utf8mb4")
    mysql_echo: bool = _env("MYSQL_ECHO", "0") == "1"
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    deepseek_base_url: str = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_chat_model: str = _env("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    deepseek_chat_timeout: float = float(_env("DEEPSEEK_CHAT_TIMEOUT", "120"))


settings = Settings()
