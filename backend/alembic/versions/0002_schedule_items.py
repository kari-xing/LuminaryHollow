"""schedule_items 日程表

Revision ID: 0002_schedule_items
Revises: 0001_initial_schema
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_schedule_items"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.String(200), nullable=False),
        sa.Column(
            "due_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(10), server_default="manual", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_schedule_items_user_id", "schedule_items", ["user_id"])
    op.create_index("ix_schedule_items_due_at", "schedule_items", ["due_at"])


def downgrade() -> None:
    op.drop_table("schedule_items")
