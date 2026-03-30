class OrderDomainError(Exception):
    """Базовая ошибка домена заказов."""


class OrderNotFoundError(OrderDomainError):
    """Заказ не найден."""


class OrderAccessDeniedError(OrderDomainError):
    """Доступ к заказу запрещён."""


class InvalidOrderStatusTransitionError(OrderDomainError):
    """Недопустимый переход статуса заказа."""

    def __init__(self, current_status: str, new_status: str) -> None:
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Недопустимый переход статуса из '{current_status}' в '{new_status}'")


class FinalOrderStatusError(OrderDomainError):
    """Нельзя изменить финальный статус заказа."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(f"Невозможно изменить статус заказа из '{current_status}'")
