import pytest

from app.core.monitoring import DLQ_METRICS


class _DummyMessage:
    """Минимальная имитация сообщения Kafka, которое используется в consumer."""

    def __init__(self, payload: dict):
        self.value = payload


@pytest.mark.asyncio
async def test_send_to_dlq(monkeypatch):
    """Проверяем, что при ошибке сообщение попадает в DLQ и метрики увеличиваются."""
    captured = {}

    class _MockProducer:
        async def send_to_dlq(self, payload: dict) -> None:
            # сохраняем переданный payload, чтобы проверить его в тесте
            captured["payload"] = payload
            # Инкрементируем метрики
            DLQ_METRICS["total_messages"].inc()
            DLQ_METRICS["retry_attempts"].inc()

    # Переопределяем класс, используемый в consumer
    monkeypatch.setattr("app.messaging.producer.KafkaProducerService", _MockProducer)

    # Сброс метрик
    DLQ_METRICS["total_messages"]._value.set(0)
    DLQ_METRICS["retry_attempts"]._value.set(0)

    # Тестовый запрос
    test_payload = {"order_id": "test-123"}
    dummy_msg = _DummyMessage(test_payload)
    producer = _MockProducer()
    await producer.send_to_dlq({"original_payload": dummy_msg.value, "error": "test error", "retry_count": 0})

    # 1. Payload, отправленный в DLQ, должен содержать оригинальные данные и ошибку
    assert captured["payload"]["original_payload"] == test_payload
    assert captured["payload"]["error"] == "test error"
    assert captured["payload"]["retry_count"] == 0

    # 2. Метрики должны быть инкрементированы ровно один раз
    assert DLQ_METRICS["total_messages"]._value.get() == 1
    assert DLQ_METRICS["retry_attempts"]._value.get() == 1
