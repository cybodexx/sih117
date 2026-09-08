from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration. The ONLY place os.environ is read."""

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://aegis:aegis@postgres:5432/aegis_wb"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "aegis_bge_m3_1024"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Sentinel
    sentinel_url: str = "http://sentinel:8001"

    # Ollama
    ollama_url: str = "http://ollama:11434"
    llm_model: str = "llama3.1:8b-instruct-q4_K_M"
    vision_model: str = "llava:7b-v1.6"
    embed_model: str = "bge-m3"
    embed_dim: int = 1024
    ollama_timeout_s: float = 60.0
    vision_timeout_s: float = 300.0
    ollama_keep_alive: str = "30m"

    from pydantic import field_validator

    @field_validator("ollama_keep_alive")
    @classmethod
    def _sanitize_keep_alive(cls, v: str) -> str:
        if v in {"-1", "", "0"}:
            return "30m"
        return v

    # JWT
    jwt_private_key_path: Path = Path("/data/keys/jwt_private.pem")
    jwt_public_key_path: Path = Path("/data/keys/jwt_public.pem")
    access_token_ttl_min: int = 15
    refresh_token_ttl_h: int = 8

    # Upload
    max_upload_mb: int = 200
    vault_path: Path = Path("/data/vault")
    tee_vault_encryption: bool = True

    # Layout (DocLayout-YOLO, baked at /app/models/)
    doclayout_model_path: Path = Path("/app/models/doclayout_yolo_docstructbench_imgsz1024.pt")

    # RAG
    chunk_target_tokens: int = 512
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    enable_reranker: bool = True
    enable_ocr: bool = True
    enable_vision: bool = True

    # Agent
    max_agent_iterations: int = 3
    turn_deadline_s: float = 60.0
    recursion_limit: int = 12

    # App
    airgap_mode: bool = False
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
