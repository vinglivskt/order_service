import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
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
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    await consumer.start()
    logger.info("Kafka consumer started")

    try:
        async for message in consumer:
            payload = message.value
            logger.info("Received message: %s", payload)

            order_id = payload["order_id"]

            process_order.delay(order_id)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


if __name__ == "__main__":
    asyncio.run(consume())
