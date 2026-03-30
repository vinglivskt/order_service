import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.messaging.producer import KafkaProducerService
from app.tasks.order_tasks import process_order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consume() -> None:
    """Слушает Kafka топик на новые заказы и обрабатывает их."""
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_NEW_ORDER,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="order-service-consumer-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    await consumer.start()
    logger.info("Kafka consumer started")

    try:
        async for message in consumer:
            try:
                payload = message.value
                logger.info("Received message: %s", payload)

                if not payload or not isinstance(payload, dict):
                    logger.warning("Invalid payload, skipping: %s", payload)
                    continue

                message_id = payload.get("message_id")
                if not message_id:
                    logger.warning("Message missing ID, skipping: %s", payload)
                    continue

                order_id = payload["order_id"]
                process_order(order_id)

                await consumer.commit()
            except Exception as exc:
                logger.exception("Ошибка обработки сообщения: %s", exc)
                producer = KafkaProducerService()
                await producer.start()
                await producer.send_new_order({"original_payload": message.value, "error": str(exc)})
                await producer.stop()
    except Exception as consume_error:
        logger.exception("Critical error in consumer loop: %s", consume_error)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


if __name__ == "__main__":
    asyncio.run(consume())
