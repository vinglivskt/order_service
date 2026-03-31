"""add processed_events for consumer idempotency

Revision ID: b91d0a8f2c3e
Revises: f3e1c0d7a9b2
Create Date: 2026-03-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b91d0a8f2c3e"
down_revision: Union[str, Sequence[str], None] = "f3e1c0d7a9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )

    op.create_index(
        op.f("ix_processed_events_event_type"),
        "processed_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_processed_events_order_id"),
        "processed_events",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_processed_events_correlation_id"),
        "processed_events",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_processed_events_request_id"),
        "processed_events",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_processed_events_request_id"),
        table_name="processed_events",
    )
    op.drop_index(
        op.f("ix_processed_events_correlation_id"),
        table_name="processed_events",
    )
    op.drop_index(op.f("ix_processed_events_order_id"), table_name="processed_events")
    op.drop_index(
        op.f("ix_processed_events_event_type"),
        table_name="processed_events",
    )
    op.drop_table("processed_events")

