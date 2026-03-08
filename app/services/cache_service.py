import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def order_key(order_id: str) -> str:
        return f"order:{order_id}"

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        data = await self.redis.get(self.order_key(order_id))
        if not data:
            return None
        return json.loads(data)

    async def set_order(self, order_id: str, payload: dict[str, Any]) -> None:
        await self.redis.set(self.order_key(order_id), json.dumps(payload, default=str), ex=settings.ORDERS_CACHE_TTL_SECONDS)

    async def delete_order(self, order_id: str) -> None:
        await self.redis.delete(self.order_key(order_id))
