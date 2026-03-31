import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.log_context import clear_context, set_event_context
from app.core.monitoring import OUTBOX_PENDING_EVENTS
from app.db.session import AsyncSessionLocal
from app.messaging.producer import KafkaProducerService
from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.core.structured_logging import setup_structured_logging

logger = logging.getLogger(__name__)


setup_structured_logging(service="outbox_publisher")


class OutboxPublisherService:
    """Слушает очередь outbox и публикует события в Kafka."""

    def __init__(self, kafka_producer: KafkaProducerService) -> None:
        self._kafka_producer = kafka_producer

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_retry_delay_seconds(attempt: int) -> int:
        return min(60, 2**attempt)

    async def send_to_dlq(self, event: OutboxEvent, error_message: str) -> None:
        """Отправить сообщение в отдельный DLQ topic после исчерпания retry."""
        payload: dict[str, Any] = {
            "failed_at": self._now().isoformat(),
            "error": error_message,
            "attempts": event.attempts,
            "source_event_id": str(event.id),
            "source_event_type": event.event_type,
            "original_event": event.payload,
        }
        logger.warning(
            "Sending event to DLQ",
            extra={
                "event_id": str(event.id),
                "event_type": event.event_type,
                "attempts": event.attempts,
            },
        )
        await self._kafka_producer.send_dlq_event(payload)

    async def run(
        self, poll_interval_seconds: float = 1.0, batch_size: int = 10
    ) -> None:
        while True:
            try:
                await self.publish_pending(batch_size=batch_size)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ошибка цикла публикации outbox")
            await asyncio.sleep(poll_interval_seconds)

    async def publish_pending(self, batch_size: int = 10) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                now_expr = func.now()
                stmt = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.status == OutboxStatus.PENDING,
                        OutboxEvent.next_attempt_at <= now_expr,
                    )
                    .order_by(OutboxEvent.created_at.asc())
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                events = list(result.scalars().all())

                if not events:
                    return

                OUTBOX_PENDING_EVENTS.set(len(events))

                for event in events:
                    correlation_id = event.payload.get("correlation_id")
                    request_id = event.payload.get("request_id")
                    order_id = (
                        event.payload.get("payload", {}).get("order_id")
                        or event.payload.get("payload", {}).get("orderId")
                    )
                    set_event_context(
                        event_id=str(event.id),
                        order_id=str(order_id) if order_id else None,
                        correlation_id=str(correlation_id) if correlation_id else None,
                        request_id=str(request_id) if request_id else None,
                    )
                    try:
                        await self._kafka_producer.send_order_event(event.payload)
                    except Exception as exc:
                        event.attempts += 1
                        event.last_error = str(exc)
                        event.next_attempt_at = self._now() + timedelta(
                            seconds=self._get_retry_delay_seconds(event.attempts)
                        )

                        if event.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                            await self.send_to_dlq(event, str(exc))
                            event.status = OutboxStatus.FAILED
                            event.failed_at = self._now()
                        clear_context()
                        continue

                    event.status = OutboxStatus.SENT
                    event.last_error = None
                    event.sent_at = self._now()
                    clear_context()
