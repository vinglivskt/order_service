import time
import logging

from app.tasks.celery_app import celery_app
from app.observability.log_context import clear_context, set_event_context
from app.core.monitoring import (
    CELERY_TASK_FAILURE_TOTAL,
    CELERY_TASK_SUCCESS_TOTAL,
)
from app.observability.structured_logging import setup_structured_logging

setup_structured_logging(service="celery_worker")

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.order_tasks.process_order")
def process_order(
    order_id: str,
    event_id: str | None = None,
    event_type: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Обработать заказ."""
    set_event_context(
        event_id=event_id,
        order_id=order_id,
        correlation_id=correlation_id,
        request_id=request_id,
    )
    try:
        time.sleep(2)
        logger.info(
            "Order processed",
            extra={"event_type": event_type},
        )
        CELERY_TASK_SUCCESS_TOTAL.labels(task_name="process_order").inc()
    except Exception:
        CELERY_TASK_FAILURE_TOTAL.labels(task_name="process_order").inc()
        logger.exception("Order processing failed")
        raise
    finally:
        clear_context()
