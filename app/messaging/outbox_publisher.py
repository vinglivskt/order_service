import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.messaging.producer import KafkaProducerService
from app.models.outbox_event import OutboxEvent, OutboxStatus

logger = logging.getLogger(__name__)


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

                for event in events:
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
                        continue

                    event.status = OutboxStatus.SENT
                    event.last_error = None
                    event.sent_at = self._now()
