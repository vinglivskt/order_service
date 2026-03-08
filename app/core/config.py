import secrets
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "order-service"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    DATABASE_URL: str
    REDIS_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_NEW_ORDER: str = "new-order"

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    RATE_LIMIT_DEFAULT: str = "100/minute"
    ORDERS_CACHE_TTL_SECONDS: int = 300

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            import json

            return json.loads(value)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore


settings = get_settings()
