import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.messaging.producer import KafkaProducerService
from app.models.outbox_event import OutboxEvent, OutboxStatus

logger = logging.getLogger(__name__)


class OutboxPublisherService:
    async def send_to_dlq(self, payload: dict) -> None:
        """Send message to Dead Letter Queue."""
        logger.warning("Sending message to DLQ: %s", payload)
        await self._kafka_producer.send_new_order(payload)

    """Слушает очередь outbox и публикует события в Kafka."""

    def __init__(self, kafka_producer: KafkaProducerService) -> None:
        self._kafka_producer = kafka_producer

    async def run(self, poll_interval_seconds: float = 1.0, batch_size: int = 10) -> None:
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
                        OutboxEvent.event_type == "new-order",
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
                        await self._kafka_producer.send_new_order(event.payload)
                    except Exception as exc:
                        # Сохраняем событие в outbox для повторной попытки.
                        event.attempts += 1
                        event.last_error = str(exc)

                        # Задержка для повторной попытки.
                        delay_seconds = min(60, 2**event.attempts)
                        event.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                        # Отправляем событие в DLQ после нескольких неудачных попыток
                        if event.attempts >= 5:
                            await self.send_to_dlq(event.payload)
                            event.status = OutboxStatus("FAILED")
                        else:
                            continue

                    event.status = OutboxStatus.SENT
                    event.last_error = None
                    event.sent_at = datetime.now(timezone.utc)
