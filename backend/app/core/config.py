from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ────────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Fraud & Risk Detection Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://fraud_user:fraud_pass@localhost:5432/fraud_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://fraud_user:fraud_pass@localhost:5432/fraud_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TOKEN_BLACKLIST_DB: int = 1

    # ── JWT (RS256) ────────────────────────────────────────────────────────────
    # Generate with: openssl genrsa -out private.pem 2048 && openssl rsa -in private.pem -pubout -out public.pem
    JWT_PRIVATE_KEY: str = ""          # full PEM string (from env)
    JWT_PUBLIC_KEY: str = ""           # full PEM string (from env)
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Field Encryption (Fernet) ──────────────────────────────────────────────
    FIELD_ENCRYPTION_KEY: str = ""     # base64 32-byte key from: Fernet.generate_key()

    # ── External Module URLs (stubs until Modules 2 & 3 are ready) ────────────
    MODULE2_BASE_URL: str = "http://localhost:8001"    # Sultan's risk engine
    MODULE3_BASE_URL: str = "http://localhost:8002"    # Noor's alerts/profiles

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    EXTERNAL_API_RATE_LIMIT: str = "60/minute"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"

    # ── CSV Import ────────────────────────────────────────────────────────────
    CSV_MAX_ROWS: int = 50_000
    CSV_BATCH_SIZE: int = 500


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
