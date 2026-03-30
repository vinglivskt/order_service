from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.orders.entities import NewOrder, Order
from app.domain.orders.enums import OrderStatus
from app.domain.users.entities import User


class UserRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, user: User) -> User:
        raise NotImplementedError


class OrderRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> Order | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user_id(self, user_id: int) -> list[Order]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, order: Order | NewOrder) -> Order:
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, order: Order, new_status: OrderStatus) -> Order:
        raise NotImplementedError


class OrderCachePort(ABC):
    @abstractmethod
    async def get(self, order_id: UUID) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, order_id: UUID, payload: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, order_id: UUID) -> None:
        raise NotImplementedError
