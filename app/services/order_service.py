from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.schemas.order import SOrderCreate


class OrderService:
    """Сервис для работы с заказами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def calculate_total(items: list[dict]) -> float:
        """Рассчитать общую стоимость заказа."""
        return round(sum(item["qty"] * item["price"] for item in items), 2)

    async def create_order(self, user_id: int, payload: SOrderCreate) -> Order:
        """Создать новый заказ."""
        order = Order(
            user_id=user_id,
            items=[item.model_dump() for item in payload.items],
            total_price=self.calculate_total(
                [item.model_dump() for item in payload.items]
            ),
            status=OrderStatus.PENDING,
        )
        self.db.add(order)

        # Пишем событие в outbox в рамках той же транзакции БД.
        # Это предотвращает потерю события, если Kafka временно недоступна.
        self.db.add(
            OutboxEvent(
                event_type="new-order",
                payload={
                    "event": "new-order",
                    "order_id": str(order.id),
                    "user_id": user_id,
                },
                # Явное значение поддерживает предсказуемость вставки даже без server default.
                status=OutboxStatus.PENDING,
            )
        )

        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_order_by_id(self, order_id: UUID) -> Order | None:
        """Получить заказ по его идентификатору."""
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_status(self, order: Order, new_status: OrderStatus) -> Order:
        """Обновить статус заказа с проверкой допустимых переходов."""
        current_status = order.status

        # Определяем допустимые переходы
        allowed_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELED],
            OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELED],
            OrderStatus.SHIPPED: [],
            OrderStatus.CANCELED: [],
        }

        # Проверяем, является ли текущий статус конечным
        if current_status in [OrderStatus.SHIPPED, OrderStatus.CANCELED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно изменить статус заказа из '{current_status.value}'",
            )

        # Проверяем, допустим ли переход
        if new_status not in allowed_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недопустимый переход статуса из '{current_status.value}' в '{new_status.value}'",
            )

        order.status = new_status
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_orders_by_user_id(self, user_id: int) -> list[Order]:
        """Получить все заказы пользователя по его идентификатору."""
        result = await self.db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())
