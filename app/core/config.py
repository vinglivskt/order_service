from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str
    DEBUG: bool

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str

    DATABASE_URL: str
    REDIS_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_ORDER_EVENTS: str
    KAFKA_TOPIC_ORDER_EVENTS_DLQ: str
    OUTBOX_MAX_ATTEMPTS: int

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    CORS_ORIGINS: list[str]
    RATE_LIMIT_DEFAULT: str
    ORDERS_CACHE_TTL_SECONDS: int
    AUTH_USER_CACHE_TTL_SECONDS: int
    ENABLE_OUTBOX_PUBLISHER: bool = True

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
