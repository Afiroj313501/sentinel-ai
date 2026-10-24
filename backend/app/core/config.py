"""Application settings, loaded from environment variables (prefix SENTINEL_)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repo root is three levels above this folder
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"


class Settings(BaseSettings):
    app_name: str = "Sentinel AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Repository ingestion limits
    max_upload_bytes: int = 25 * 1024 * 1024
    max_archive_entries: int = 5000
    max_extracted_files: int = 2000
    max_file_bytes: int = 1024 * 1024
    max_total_extracted_bytes: int = 100 * 1024 * 1024
    max_extraction_seconds: float = 30.0
    scanner_timeout_seconds: float = 60.0
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'sentinel.db').as_posix()}"

    # AI explanations
    ai_provider: Literal["ollama", "openai_compatible"] = "ollama"
    ai_model: str = "llama3.2:3b"
    ai_base_url: str | None = None
    ai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = 120.0

    # Authentication & JWT
    jwt_secret_key: SecretStr = SecretStr("sentinel-ai-insecure-dev-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_prefix="SENTINEL_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
