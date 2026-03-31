"""Add failed outbox status and metadata columns

Revision ID: f3e1c0d7a9b2
Revises: c7b2df9d4c1a
Create Date: 2026-03-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3e1c0d7a9b2"
down_revision: Union[str, Sequence[str], None] = "c7b2df9d4c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_OUTBOX_STATUS = "outbox_status"
NEW_OUTBOX_STATUS = "outbox_status_new"


def upgrade() -> None:
    op.execute("ALTER TYPE outbox_status RENAME TO outbox_status_old")
    op.execute("CREATE TYPE outbox_status AS ENUM ('PENDING', 'SENT', 'FAILED')")
    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN status
        TYPE outbox_status
        USING status::text::outbox_status
        """
    )
    op.execute("DROP TYPE outbox_status_old")

    op.add_column(
        "outbox_events",
        sa.Column(
            "correlation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "outbox_events",
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_outbox_events_correlation_id"),
        "outbox_events",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_outbox_events_correlation_id"),
        table_name="outbox_events",
    )
    op.drop_column("outbox_events", "failed_at")
    op.drop_column("outbox_events", "correlation_id")

    op.execute("ALTER TYPE outbox_status RENAME TO outbox_status_new")
    op.execute("CREATE TYPE outbox_status AS ENUM ('PENDING', 'SENT')")
    op.execute(
        """
        UPDATE outbox_events
        SET status = 'PENDING'
        WHERE status = 'FAILED'
        """
    )
    op.execute(
        """
        ALTER TABLE outbox_events
        ALTER COLUMN status
        TYPE outbox_status
        USING status::text::outbox_status
        """
    )
    op.execute("DROP TYPE outbox_status_new")
