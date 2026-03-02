"""
Application configuration using Pydantic BaseSettings.

WHY BaseSettings?
- Reads from environment variables automatically
- Validates types at startup (fail fast, not at runtime)
- Centralizes all config in one place — no scattered os.getenv() calls
- Interview tip: "12-Factor App" methodology says config should come from environment
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to THIS file, not the cwd
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/railway_db"

    # ── JWT ───────────────────────────────────────────────────
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "Railway Reservation System"
    DEBUG: bool = True

    class Config:
        env_file = str(BASE_DIR / ".env")   # absolute path to .env
        env_file_encoding = "utf-8"


@lru_cache()              # singleton — same Settings object reused everywhere
def get_settings() -> Settings:
    return Settings()
