from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "Enterprise AI Decision Intelligence Platform"
    environment: str = "development"

    # SQLite by default so the project runs with zero external infra.
    # Point DATABASE_URL at a postgres:// DSN for production deployment.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'platform.db'}"

    secret_key: str = "dev-secret-key-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # Optional: if set, the AI Copilot calls a real LLM for explanations.
    # If unset, the Copilot falls back to a deterministic template engine.
    llm_api_key: str | None = None
    llm_provider: str = "anthropic"  # "anthropic" | "openai" | "none"

    cors_origins: list[str] = ["http://localhost:3000"]

    data_raw_dir: Path = PROJECT_ROOT / "data" / "raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()
