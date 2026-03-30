from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.application.orders.service import OrderApplicationService
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.domain.orders.exceptions import (
    FinalOrderStatusError,
    InvalidOrderStatusTransitionError,
    OrderAccessDeniedError,
    OrderNotFoundError,
)
from app.infrastructure.cache.order_cache import RedisOrderCache
from app.infrastructure.db.repositories.order_repository import SQLAlchemyOrderRepository
from app.models.user import User
from app.schemas.order import SOrderCreate, SOrderRead, SOrderUpdateStatus

router = APIRouter(prefix="/orders", tags=["orders"])


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_order_application_service(
    db: AsyncSession,
) -> OrderApplicationService:
    return OrderApplicationService(
        order_repository=SQLAlchemyOrderRepository(db),
    )


@router.post("/", response_model=SOrderRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_order(
    request: Request,
    payload: SOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SOrderRead:
    app_service = get_order_application_service(db)
    order = await app_service.create_order(current_user.id, payload)

    order_schema = SOrderRead.model_validate(
        {
            "id": order.id,
            "user_id": order.user_id,
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "qty": item.qty,
                    "price": item.price,
                }
                for item in order.items
            ],
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
        }
    )
    cache = RedisOrderCache(redis)
    await cache.set(order.id, order_schema.model_dump(mode="json"))

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
    cache = RedisOrderCache(redis)
    cached = await cache.get(order_id)
    if cached:
        if int(cached["user_id"]) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return SOrderRead.model_validate(cached)

    app_service = get_order_application_service(db)
    try:
        order = await app_service.get_order(order_id, current_user.id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from exc
    except OrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from exc

    payload_schema = SOrderRead.model_validate(
        {
            "id": order.id,
            "user_id": order.user_id,
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "qty": item.qty,
                    "price": item.price,
                }
                for item in order.items
            ],
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
        }
    )
    await cache.set(order.id, payload_schema.model_dump(mode="json"))
    return payload_schema


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
    app_service = get_order_application_service(db)
    try:
        order = await app_service.update_order_status(
            order_id=order_id,
            current_user_id=current_user.id,
            new_status=payload.status,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from exc
    except OrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from exc
    except (FinalOrderStatusError, InvalidOrderStatusTransitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    order_schema = SOrderRead.model_validate(
        {
            "id": order.id,
            "user_id": order.user_id,
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "qty": item.qty,
                    "price": item.price,
                }
                for item in order.items
            ],
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
        }
    )

    cache = RedisOrderCache(redis)
    await cache.set(order.id, order_schema.model_dump(mode="json"))

    return order_schema


@router.get("/user/{user_id}/", response_model=list[SOrderRead])
@limiter.limit("60/minute")
async def get_orders_by_user(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SOrderRead]:
    app_service = get_order_application_service(db)
    try:
        orders = await app_service.get_orders_by_user(user_id, current_user.id)
    except OrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from exc

    return [
        SOrderRead.model_validate(
            {
                "id": order.id,
                "user_id": order.user_id,
                "items": [
                    {
                        "sku": item.sku,
                        "name": item.name,
                        "qty": item.qty,
                        "price": item.price,
                    }
                    for item in order.items
                ],
                "total_price": order.total_price,
                "status": order.status,
                "created_at": order.created_at,
            }
        )
        for order in orders
    ]
