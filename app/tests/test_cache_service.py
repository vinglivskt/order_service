from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.infrastructure.cache.order_cache import RedisOrderCache

pytestmark = pytest.mark.asyncio


async def test_cache_set_and_get_order():
    redis = Redis.from_url("redis://redis:6379/15", decode_responses=True)
    cache = RedisOrderCache(redis)

    order_id = uuid4()
    payload = {
        "id": str(order_id),
        "user_id": 1,
        "status": "PENDING",
    }

    await redis.flushdb()

    await cache.set(order_id, payload)
    cached = await cache.get(order_id)

    assert cached == payload
