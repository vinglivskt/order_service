from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.orders.enums import OrderStatus


@dataclass(slots=True)
class OrderItem:
    sku: str
    name: str
    qty: int
    price: float

    def total_price(self) -> float:
        return round(self.qty * self.price, 2)


@dataclass(slots=True)
class Order:
    id: UUID
    user_id: int
    items: list[OrderItem]
    total_price: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        allowed_transitions = {
            OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELED},
            OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELED},
            OrderStatus.SHIPPED: set(),
            OrderStatus.CANCELED: set(),
        }
        return new_status in allowed_transitions.get(self.status, set())

    def is_final(self) -> bool:
        return self.status in {OrderStatus.SHIPPED, OrderStatus.CANCELED}


@dataclass(slots=True)
class NewOrder:
    user_id: int
    items: list[OrderItem] = field(default_factory=list)

    def calculate_total_price(self) -> float:
        return round(sum(item.total_price() for item in self.items), 2)

    @classmethod
    def from_primitives(cls, user_id: int, items: list[dict[str, Any]]) -> "NewOrder":
        return cls(
            user_id=user_id,
            items=[
                OrderItem(
                    sku=item["sku"],
                    name=item["name"],
                    qty=item["qty"],
                    price=item["price"],
                )
                for item in items
            ],
        )
