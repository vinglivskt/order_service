import json
from typing import Any

from aiokafka import AIOKafkaProducer

from app.core.config import settings


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

    async def send_dlq_event(self, payload: dict[str, Any]) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")

        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_ORDER_EVENTS_DLQ,
            payload,
        )


kafka_producer = KafkaProducerService()
