import uuid
from contextvars import ContextVar
from typing import Optional


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
event_id_var: ContextVar[str | None] = ContextVar("event_id", default=None)
order_id_var: ContextVar[str | None] = ContextVar("order_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
service_var: ContextVar[str | None] = ContextVar("service", default=None)


def set_service(service: str) -> None:
    service_var.set(service)


def set_request_context(
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    user_id: str | None = None,
) -> None:
    if request_id is not None:
        request_id_var.set(request_id)
    if correlation_id is not None:
        correlation_id_var.set(correlation_id)
    if user_id is not None:
        user_id_var.set(user_id)


def set_event_context(
    *,
    event_id: str | None = None,
    order_id: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> None:
    if event_id is not None:
        event_id_var.set(event_id)
    if order_id is not None:
        order_id_var.set(order_id)
    if correlation_id is not None:
        correlation_id_var.set(correlation_id)
    if request_id is not None:
        request_id_var.set(request_id)


def clear_context() -> None:
    request_id_var.set(None)
    correlation_id_var.set(None)
    event_id_var.set(None)
    order_id_var.set(None)
    user_id_var.set(None)
    # service_var не сбрасываем: он задается на уровне процесса.


def get_context() -> dict[str, str | None]:
    return {
        "request_id": request_id_var.get(),
        "correlation_id": correlation_id_var.get(),
        "event_id": event_id_var.get(),
        "order_id": order_id_var.get(),
        "user_id": user_id_var.get(),
        "service": service_var.get(),
    }


def ensure_uuid_str(value: str | None) -> str | None:
    """Нормализует строку UUID; если значение некорректное — возвращает None."""
    if value is None:
        return None
    try:
        return str(uuid.UUID(value))
    except Exception:
        return None

