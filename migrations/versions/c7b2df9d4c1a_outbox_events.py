"""outbox_events (документация миграции)

Идентификатор ревизии: c7b2df9d4c1a
Отменяет (previous): 831ba9b83ab1
Дата создания: 2026-03-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Идентификаторы ревизии, используемые Alembic.
revision: str = "c7b2df9d4c1a"
down_revision: Union[str, Sequence[str], None] = "831ba9b83ab1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "SENT", name="outbox_status"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_outbox_events_event_type"),
        "outbox_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_outbox_events_next_attempt_at"),
        "outbox_events",
        ["next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_next_attempt_at"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_status"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_event_type"), table_name="outbox_events")
    op.drop_table("outbox_events")

    # Явное удаление enum-типа для Postgres.
    op.execute("DROP TYPE IF EXISTS outbox_status")
