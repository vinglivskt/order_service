import json
from typing import Any

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.monitoring import DLQ_METRICS, KAFKA_PUBLISHED_TOTAL


class KafkaProducerService:
    """Сервис для отправки сообщений в Kafka."""

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send_order_event(self, payload: dict[str, Any]) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")

        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_ORDER_EVENTS,
            payload,
        )
        KAFKA_PUBLISHED_TOTAL.labels(topic=settings.KAFKA_TOPIC_ORDER_EVENTS).inc()

    async def send_dlq_event(self, payload: dict[str, Any]) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")

        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_ORDER_EVENTS_DLQ,
            payload,
        )
        DLQ_METRICS["total_messages"].inc()
        attempts = payload.get("attempts")
        if isinstance(attempts, int) and attempts > 0:
            DLQ_METRICS["retry_attempts"].inc()


kafka_producer = KafkaProducerService()
