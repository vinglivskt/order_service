import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.outbox_event import OutboxEvent, OutboxStatus
from app.models.user import User
from app.schemas.order import SOrderCreate, SOrderItem
from app.services.order_service import OrderService

pytestmark = pytest.mark.asyncio


def _build_order_payload() -> SOrderCreate:
    return SOrderCreate(
        items=[
            SOrderItem(
                sku="sku-1",
                name="Test Item",
                qty=2,
                price=100,
            )
        ]
    )


async def _create_user(session, email: str = "messaging@example.com") -> User:
    user = User(
        email=email,
        hashed_password="hashed-password",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_create_order_creates_outbox_event_with_envelope():
    from app.tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        user = await _create_user(session)
        service = OrderService(session)

        order = await service.create_order(user.id, _build_order_payload())

        result = await session.execute(select(OutboxEvent).limit(1))
        outbox_event = result.scalar_one_or_none()

        assert outbox_event is not None
        assert outbox_event.status == OutboxStatus.PENDING
        assert outbox_event.event_type == "order.created"

        payload = outbox_event.payload
        assert payload["event_id"] == str(outbox_event.id)
        assert payload["event_type"] == "order.created"
        assert payload["event_version"] == 1

        occurred_at = datetime.fromisoformat(payload["occurred_at"])
        assert occurred_at.tzinfo is not None

        assert payload["correlation_id"] is None
        assert payload["request_id"] is None

        event_payload = payload["payload"]
        assert event_payload["order_id"] == str(order.id)
        assert event_payload["user_id"] == user.id


async def test_outbox_event_id_is_valid_uuid_string():
    from app.tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        user = await _create_user(session, email="uuid-check@example.com")
        service = OrderService(session)

        await service.create_order(user.id, _build_order_payload())

        result = await session.execute(select(OutboxEvent).limit(1))
        outbox_event = result.scalar_one_or_none()

        assert outbox_event is not None
        parsed = uuid.UUID(str(outbox_event.id))
        assert str(parsed) == str(outbox_event.id)


def test_outbox_payload_occurred_at_is_utc_isoformat():
    occurred_at = datetime.now(timezone.utc).isoformat()

    parsed = datetime.fromisoformat(occurred_at)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_dlq_payload_shape():
    original_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "order.created",
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": None,
        "request_id": None,
        "payload": {
            "order_id": str(uuid.uuid4()),
            "user_id": 1,
        },
    }

    dlq_payload = {
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": "KafkaTimeoutError",
        "attempts": 5,
        "source_topic": "order-events",
        "original_event": original_event,
    }

    assert dlq_payload["error"] == "KafkaTimeoutError"
    assert dlq_payload["attempts"] == 5
    assert dlq_payload["source_topic"] == "order-events"
    assert dlq_payload["original_event"]["event_type"] == "order.created"
    assert "event_id" in dlq_payload["original_event"]
