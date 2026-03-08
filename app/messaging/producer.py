import json

from aiokafka import AIOKafkaProducer

from app.core.config import settings


class KafkaProducerService:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send_new_order(self, payload: dict) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")

        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_NEW_ORDER,
            payload,
        )


kafka_producer = KafkaProducerService()
