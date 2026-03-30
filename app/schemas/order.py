from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.orders.enums import OrderStatus


class SOrderItem(BaseModel):
    """Схема для элемента заказа."""

    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    qty: int = Field(ge=1)
    price: float = Field(gt=0)

    model_config = ConfigDict(from_attributes=True)


class SOrderCreate(BaseModel):
    """Схема для создания заказа."""

    items: list[SOrderItem] = Field(min_length=1)


class SOrderUpdateStatus(BaseModel):
    """Схема для обновления статуса заказа."""

    status: OrderStatus


class SOrderRead(BaseModel):
    """Схема для чтения заказа."""

    id: UUID
    user_id: int
    items: list[SOrderItem]
    total_price: float
    status: OrderStatus
    created_at: datetime

    @field_validator("total_price")
    @classmethod
    def round_total(cls, value: float) -> float:
        return round(value, 2)

    model_config = ConfigDict(from_attributes=True)
