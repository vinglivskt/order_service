import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.core.log_context import clear_context, set_event_context
from app.core.monitoring import KAFKA_CONSUMED_TOTAL
from app.messaging.producer import KafkaProducerService
from app.models.processed_event import ProcessedEvent
from app.core.structured_logging import setup_structured_logging
from app.tasks.order_tasks import process_order

logger = logging.getLogger(__name__)

setup_structured_logging(service="consumer")


def _now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_uuid(value: Any, field_name: str) -> uuid.UUID:
    if value is None or value == "None":
        raise ValueError(f"Missing or null {field_name}")
    try:
        return uuid.UUID(str(value))
    except Exception as exc:
        raise ValueError(f"Invalid {field_name}") from exc


def _parse_optional_uuid(value: Any, field_name: str) -> uuid.UUID | None:
    if value is None or value == "None":
        return None
    return _parse_uuid(value, field_name)


def validate_event(envelope: Any) -> dict[str, Any]:
    """Проверяет envelope входящего события и возвращает валидные поля."""
    if not isinstance(envelope, dict):
        raise ValueError("Event payload must be an object")

    event_id = _parse_uuid(envelope.get("event_id"), "event_id")
    event_type = envelope.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("Event is missing or invalid event_type")

    event_payload = envelope.get("payload")
    if not isinstance(event_payload, dict):
        raise ValueError("Event payload field must be an object")

    order_id = _parse_uuid(event_payload.get("order_id"), "order_id")

    correlation_id = _parse_optional_uuid(envelope.get("correlation_id"), "correlation_id")
    request_id = _parse_optional_uuid(envelope.get("request_id"), "request_id")

    return {
        "event_id": event_id,
        "event_type": event_type,
        "order_id": order_id,
        "correlation_id": correlation_id,
        "request_id": request_id,
        "envelope": envelope,
    }


async def _send_dlq(
    producer: KafkaProducerService,
    *,
    error: str,
    attempts: int,
    original_event: Any,
    event_id: uuid.UUID | None = None,
    event_type: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "failed_at": _now_isoformat(),
        "error": error,
        "attempts": attempts,
        "source_topic": settings.KAFKA_TOPIC_ORDER_EVENTS,
        "event_id": str(event_id) if event_id else None,
        "event_type": event_type,
        "original_event": original_event,
    }
    await producer.send_dlq_event(payload)


async def consume() -> None:
    """Слушает Kafka топик событий заказов и запускает обработку с идемпотентностью."""
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_ORDER_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="order-service-consumer-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: m,  # получаем raw bytes, JSON декодируем с контролем ошибок
    )
    producer = KafkaProducerService()

    await consumer.start()
    await producer.start()
    logger.info("Kafka consumer started")

    retry_attempts: dict[str, int] = {}

    try:
        async for message in consumer:
            message_key = (
                f"{message.topic}:{message.partition}:{message.offset}"
            )

            raw_bytes = message.value
            raw_text = raw_bytes.decode("utf-8", errors="replace")
            KAFKA_CONSUMED_TOTAL.labels(topic=message.topic).inc()

            try:
                envelope = json.loads(raw_text)
                event = validate_event(envelope)

                event_id = event["event_id"]
                event_type = event["event_type"]
                order_id = event["order_id"]
                correlation_id = event["correlation_id"]
                request_id = event["request_id"]

                set_event_context(
                    event_id=str(event_id),
                    order_id=str(order_id),
                    correlation_id=str(correlation_id) if correlation_id else None,
                    request_id=str(request_id) if request_id else None,
                )

                async with AsyncSessionLocal() as session:
                    inserted = False
                    async with session.begin():
                        try:
                            session.add(
                                ProcessedEvent(
                                    event_id=event_id,
                                    event_type=event_type,
                                    order_id=order_id,
                                    correlation_id=correlation_id,
                                    request_id=request_id,
                                )
                            )
                            await session.flush()
                            inserted = True
                        except IntegrityError:
                            inserted = False

                        if inserted:
                            process_order.delay(
                                str(order_id),
                                str(event_id),
                                event_type,
                                str(correlation_id) if correlation_id else None,
                                request_id=str(request_id) if request_id else None,
                            )

                # Коммит делаем только после успешной фиксации идемпотентности (и enqueue для новых).
                logger.info("Message consumed and committed", extra={"event_type": event_type})
                await consumer.commit()
                clear_context()
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Poison/invalid event, sending to DLQ: %s", exc)
                attempts = retry_attempts.get(message_key, 0) + 1

                # Для poison ошибок event_id может быть невалидным/отсутствующим.
                await _send_dlq(
                    producer,
                    error=str(exc),
                    attempts=attempts,
                    original_event=envelope if "envelope" in locals() else {"raw": raw_text},
                )
                retry_attempts.pop(message_key, None)
                await consumer.commit()
                clear_context()
            except Exception as exc:
                retry_attempts[message_key] = retry_attempts.get(message_key, 0) + 1
                attempts = retry_attempts[message_key]

                logger.exception(
                    "Error processing message (attempt %s), will %s",
                    attempts,
                    "DLQ" if attempts >= settings.OUTBOX_MAX_ATTEMPTS else "retry",
                )

                if attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                    await _send_dlq(
                        producer,
                        error=str(exc),
                        attempts=attempts,
                        original_event={"raw": raw_text},
                    )
                    retry_attempts.pop(message_key, None)
                    await consumer.commit()
                    clear_context()
                else:
                    delay_seconds = min(60, 2**attempts)
                    clear_context()
                    await asyncio.sleep(delay_seconds)
    except Exception as consume_error:
        logger.exception("Critical error in consumer loop: %s", consume_error)
    finally:
        await consumer.stop()
        await producer.stop()
        logger.info("Kafka consumer stopped")


if __name__ == "__main__":
    asyncio.run(consume())
