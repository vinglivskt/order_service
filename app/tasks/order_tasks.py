import time

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.order_tasks.process_order")
def process_order(
    order_id: str,
    event_id: str | None = None,
    event_type: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Обработать заказ."""
    time.sleep(2)
    print(
        "Order "
        f"{order_id} processed (event_id={event_id}, event_type={event_type}, correlation_id={correlation_id}, request_id={request_id})"
    )
