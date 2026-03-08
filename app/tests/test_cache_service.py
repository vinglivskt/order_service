import pytest
from redis.asyncio import Redis

from app.services.cache_service import CacheService

pytestmark = pytest.mark.asyncio


async def test_cache_set_and_get_order():
    redis = Redis.from_url("redis://redis:6379/15", decode_responses=True)
    service = CacheService(redis)

    order_id = "test-order-id"
    payload = {
        "id": order_id,
        "user_id": 1,
        "status": "PENDING",
    }

    await redis.flushdb()
    await service.set_order(order_id, payload)

    cached = await service.get_order(order_id)

    assert cached is not None
    assert cached["id"] == order_id
    assert cached["status"] == "PENDING"

    await redis.flushdb()
    await redis.close()
