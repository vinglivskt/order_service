import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.messaging.producer import KafkaProducerService
from app.tasks.order_tasks import process_order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_event(payload: Any) -> dict[str, Any]:
    """Проверяет envelope входящего события и возвращает валидный payload."""
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    event_id = payload.get("event_id")
    event_type = payload.get("event_type")
    event_payload = payload.get("payload")

    if not event_id:
        raise ValueError("Event is missing event_id")

    if not event_type:
        raise ValueError("Event is missing event_type")

    if not isinstance(event_payload, dict):
        raise ValueError("Event payload field must be an object")

    order_id = event_payload.get("order_id")
    if not order_id:
        raise ValueError("Event payload is missing order_id")

    return payload


async def consume() -> None:
    """Слушает Kafka топик событий заказов и запускает фоновую обработку."""
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_ORDER_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="order-service-consumer-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    producer = KafkaProducerService()

    await consumer.start()
    await producer.start()
    logger.info("Kafka consumer started")

    try:
        async for message in consumer:
            payload = message.value
            logger.info("Received message: %s", payload)

            try:
                event = validate_event(payload)
                event_payload = event["payload"]
                order_id = event_payload["order_id"]

                process_order.delay(
                    order_id,
                    event["event_id"],
                )

                await consumer.commit()
            except ValueError as exc:
                logger.warning("Invalid event, sending to DLQ: %s", exc)
                await producer.send_dlq_event(
                    {
                        "error": str(exc),
                        "source_topic": settings.KAFKA_TOPIC_ORDER_EVENTS,
                        "original_event": payload,
                    }
                )
                await consumer.commit()
            except Exception as exc:
                logger.exception("Ошибка обработки сообщения: %s", exc)
    except Exception as consume_error:
        logger.exception("Critical error in consumer loop: %s", consume_error)
    finally:
        await consumer.stop()
        await producer.stop()
        logger.info("Kafka consumer stopped")


if __name__ == "__main__":
    asyncio.run(consume())
