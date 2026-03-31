import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings
from app.core.monitoring import CACHE_HIT_TOTAL, CACHE_MISS_TOTAL


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def order_key(order_id: str) -> str:
        return f"order:{order_id}"

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """Получить заказ из кэша."""
        data = await self.redis.get(self.order_key(order_id))
        if not data:
            CACHE_MISS_TOTAL.inc()
            return None
        CACHE_HIT_TOTAL.inc()
        return json.loads(data)

    async def set_order(self, order_id: str, payload: dict[str, Any]) -> None:
        """Установить заказ в кэше."""
        await self.redis.set(
            self.order_key(order_id),
            json.dumps(payload, default=str),
            ex=settings.ORDERS_CACHE_TTL_SECONDS,
        )

    async def delete_order(self, order_id: str) -> None:
        """Удалить заказ из кэша."""
        await self.redis.delete(self.order_key(order_id))
