"""
Centralized app configuration, loaded from environment variables / .env.
Never hardcode secrets here — see ../../.env.example for required keys.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Statement Extractor"
    ENV: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://statement_user:changeme@localhost:5432/statement_extractor"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Auth
    JWT_SECRET_KEY: str = "changeme-generate-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # File storage (local disk — no S3/Firebase dependency)
    UPLOAD_DIR: str = "/var/lib/statement-extractor/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # CORS — tighten this list per environment
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Billing (Stripe) — external API, unrelated to the "no AI" extraction constraint
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
