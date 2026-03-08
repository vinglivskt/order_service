from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import SOrderCreate, SOrderRead, SOrderUpdateStatus
from app.services.cache_service import CacheService
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


@router.post("/", response_model=SOrderRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_order(
    request: Request,
    payload: SOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SOrderRead:
    """Создаёт новый заказ."""
    order_service = OrderService(db)
    order = await order_service.create_order(current_user.id, payload)

    order_schema = SOrderRead.model_validate(order)
    cache_service = CacheService(redis)
    await cache_service.set_order(str(order.id), order_schema.model_dump(mode="json"))

    await request.app.state.kafka_producer.send_new_order(
        {
            "event": "new-order",
            "order_id": str(order.id),
            "user_id": current_user.id,
        }
    )

    return order_schema


@router.get("/{order_id}/", response_model=SOrderRead)
@limiter.limit("60/minute")
async def get_order(
    request: Request,
    order_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SOrderRead:
    """Получает заказ по `order_id`."""
    cache_service = CacheService(redis)
    cached = await cache_service.get_order(str(order_id))
    if cached:
        if int(cached["user_id"]) != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return SOrderRead.model_validate(cached)

    order_service = OrderService(db)
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    payload = SOrderRead.model_validate(order)
    await cache_service.set_order(str(order.id), payload.model_dump(mode="json"))
    return payload


@router.patch("/{order_id}/", response_model=SOrderRead)
@limiter.limit("30/minute")
async def update_order_status(
    request: Request,
    order_id: UUID,
    payload: SOrderUpdateStatus,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SOrderRead:
    """Обновляет статус заказа."""
    order_service = OrderService(db)
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    order = await order_service.update_status(order, payload.status)
    order_schema = SOrderRead.model_validate(order)

    cache_service = CacheService(redis)
    await cache_service.set_order(str(order.id), order_schema.model_dump(mode="json"))

    return order_schema


@router.get("/user/{user_id}/", response_model=list[SOrderRead])
@limiter.limit("60/minute")
async def get_orders_by_user(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SOrderRead]:
    """Получает список заказов пользователя."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    order_service = OrderService(db)
    orders = await order_service.get_orders_by_user_id(user_id)
    return [SOrderRead.model_validate(order) for order in orders]
