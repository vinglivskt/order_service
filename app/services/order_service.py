from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.schemas.order import SOrderCreate


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def calculate_total(items: list[dict]) -> float:
        return round(sum(item["qty"] * item["price"] for item in items), 2)

    async def create_order(self, user_id: int, payload: SOrderCreate) -> Order:
        order = Order(
            user_id=user_id,
            items=[item.model_dump() for item in payload.items],
            total_price=self.calculate_total([item.model_dump() for item in payload.items]),
            status=OrderStatus.PENDING,
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_order_by_id(self, order_id: UUID) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_orders_by_user_id(self, user_id: int) -> list[Order]:
        result = await self.db.execute(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))
        return list(result.scalars().all())
