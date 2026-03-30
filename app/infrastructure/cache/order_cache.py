import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.application.common.ports import OrderCachePort
from app.core.config import settings


class RedisOrderCache(OrderCachePort):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(order_id: UUID) -> str:
        return f"order:{order_id}"

    async def get(self, order_id: UUID) -> dict[str, Any] | None:
        data = await self._redis.get(self._key(order_id))
        if not data:
            return None
        return json.loads(data)

    async def set(self, order_id: UUID, payload: dict[str, Any]) -> None:
        await self._redis.set(
            self._key(order_id),
            json.dumps(payload, default=str),
            ex=settings.ORDERS_CACHE_TTL_SECONDS,
        )

    async def delete(self, order_id: UUID) -> None:
        await self._redis.delete(self._key(order_id))
