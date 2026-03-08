from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.order import OrderStatus


class SOrderItem(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    qty: int = Field(ge=1)
    price: float = Field(gt=0)


class SOrderCreate(BaseModel):
    items: list[SOrderItem] = Field(min_length=1)


class SOrderUpdateStatus(BaseModel):
    status: OrderStatus


class SOrderRead(BaseModel):
    id: UUID
    user_id: int
    items: list[dict[str, Any]]
    total_price: float
    status: OrderStatus
    created_at: datetime

    @field_validator("total_price")
    @classmethod
    def round_total(cls, value: float) -> float:
        return round(value, 2)

    model_config = {"from_attributes": True}
