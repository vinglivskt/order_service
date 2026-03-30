from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.ports import OrderRepositoryPort
from app.domain.orders.entities import NewOrder, Order, OrderItem
from app.domain.orders.enums import OrderStatus
from app.models.order import Order as OrderModel
from app.models.outbox_event import OutboxEvent, OutboxStatus


class SQLAlchemyOrderRepository(OrderRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order | NewOrder) -> Order:
        orm_order = self._to_orm(order)
        self._session.add(orm_order)
        await self._session.flush()

        self._session.add(
            OutboxEvent(
                event_type="new-order",
                payload={
                    "event": "new-order",
                    "order_id": str(orm_order.id),
                    "user_id": orm_order.user_id,
                },
                status=OutboxStatus.PENDING,
            )
        )

        await self._session.commit()
        await self._session.refresh(orm_order)
        return self._to_domain(orm_order)

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == order_id))
        orm_order = result.scalar_one_or_none()
        if orm_order is None:
            return None
        return self._to_domain(orm_order)

    async def list_by_user_id(self, user_id: int) -> list[Order]:
        result = await self._session.execute(
            select(OrderModel).where(OrderModel.user_id == user_id).order_by(OrderModel.created_at.desc())
        )
        return [self._to_domain(orm_order) for orm_order in result.scalars().all()]

    async def update_status(self, order: Order, new_status: OrderStatus) -> Order:
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == order.id))
        orm_order = result.scalar_one_or_none()
        if orm_order is None:
            return order

        orm_order.status = new_status
        await self._session.commit()
        await self._session.refresh(orm_order)
        return self._to_domain(orm_order)

    @staticmethod
    def _to_domain(orm_order: OrderModel) -> Order:
        return Order(
            id=orm_order.id,
            user_id=orm_order.user_id,
            items=[
                OrderItem(
                    sku=item["sku"],
                    name=item["name"],
                    qty=item["qty"],
                    price=item["price"],
                )
                for item in orm_order.items
            ],
            total_price=orm_order.total_price,
            status=orm_order.status,
            created_at=orm_order.created_at,
        )

    @staticmethod
    def _serialize_items(items: list[OrderItem]) -> list[dict]:
        return [asdict(item) for item in items]

    @classmethod
    def _to_orm(cls, order: Order | NewOrder) -> OrderModel:
        if isinstance(order, NewOrder):
            return OrderModel(
                user_id=order.user_id,
                items=cls._serialize_items(order.items),
                total_price=order.calculate_total_price(),
                status=OrderStatus.PENDING,
            )

        return OrderModel(
            id=order.id,
            user_id=order.user_id,
            items=cls._serialize_items(order.items),
            total_price=order.total_price,
            status=order.status,
            created_at=order.created_at,
        )
