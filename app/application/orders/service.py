from uuid import UUID

from app.application.common.ports import OrderRepositoryPort
from app.domain.orders.entities import NewOrder, Order
from app.domain.orders.enums import OrderStatus
from app.domain.orders.exceptions import (
    FinalOrderStatusError,
    InvalidOrderStatusTransitionError,
    OrderAccessDeniedError,
    OrderNotFoundError,
)
from app.schemas.order import SOrderCreate


class OrderApplicationService:
    """Application service for order use cases."""

    def __init__(self, order_repository: OrderRepositoryPort) -> None:
        self._order_repository = order_repository

    async def create_order(self, user_id: int, payload: SOrderCreate) -> Order:
        new_order = NewOrder.from_primitives(
            user_id=user_id,
            items=[item.model_dump() for item in payload.items],
        )
        return await self._order_repository.add(new_order)

    async def get_order(self, order_id: UUID, current_user_id: int) -> Order:
        order = await self._order_repository.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError()

        if order.user_id != current_user_id:
            raise OrderAccessDeniedError()

        return order

    async def update_order_status(
        self,
        order_id: UUID,
        current_user_id: int,
        new_status: OrderStatus,
    ) -> Order:
        order = await self.get_order(order_id, current_user_id)

        if order.is_final():
            raise FinalOrderStatusError(order.status.value)

        if not order.can_transition_to(new_status):
            raise InvalidOrderStatusTransitionError(
                order.status.value,
                new_status.value,
            )

        return await self._order_repository.update_status(order, new_status)

    async def get_orders_by_user(
        self,
        user_id: int,
        current_user_id: int,
    ) -> list[Order]:
        if user_id != current_user_id:
            raise OrderAccessDeniedError()

        return await self._order_repository.list_by_user_id(user_id)
