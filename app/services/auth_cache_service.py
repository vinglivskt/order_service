import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings


@dataclass(frozen=True)
class CachedUser:
    id: int
    is_active: bool


class AuthCacheService:
    """
    Кэш для авторизации.

    Используется для проверки `is_active` без похода в БД на каждый запрос.
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def user_key(user_id: int) -> str:
        return f"auth:user:{user_id}"

    async def get_user(self, user_id: int) -> CachedUser | None:
        raw = await self.redis.get(self.user_key(user_id))
        if not raw:
            return None

        data: dict[str, Any] = json.loads(raw)
        return CachedUser(
            id=int(data["id"]),
            is_active=bool(data["is_active"]),
        )

    async def set_user(self, user_id: int, is_active: bool) -> None:
        await self.redis.set(
            self.user_key(user_id),
            json.dumps({"id": user_id, "is_active": is_active}),
            ex=settings.AUTH_USER_CACHE_TTL_SECONDS,
        )

    async def invalidate_user(self, user_id: int) -> None:
        await self.redis.delete(self.user_key(user_id))

