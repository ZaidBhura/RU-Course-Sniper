"""watched_index_status

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13

Add status column to watched_indexes to track lifecycle:
  'watching' — actively monitored (default)
  'opened'   — notification sent; moved to Opened tab
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watched_indexes",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="watching",
        ),
    )
    op.create_check_constraint(
        "chk_watched_indexes_status",
        "watched_indexes",
        "status IN ('watching', 'opened')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_watched_indexes_status", "watched_indexes", type_="check")
    op.drop_column("watched_indexes", "status")
