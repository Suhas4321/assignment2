from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Resolve .env relative to this file so it works regardless of cwd
_ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    # Default to SQLite for zero-config local demo; override with Postgres URL in .env
    DATABASE_URL: str = f"sqlite:///{Path(__file__).resolve().parent / 'crm_hcp.db'}"
    GROQ_API_KEY: str = ""
    # gemma2-9b-it was decommissioned by Groq (2025/26). Free-tier defaults:
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    DEFAULT_REP_ID: str = "REP-001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


settings = Settings()
