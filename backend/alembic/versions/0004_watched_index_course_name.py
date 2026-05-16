"""watched_index_course_name

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13

Add course_name column to watched_indexes.
Populated at creation time from the Redis enricher cache (course title + subject/number).
Null when the cache is cold at creation time — filled on the next enricher run via resnipe or re-add.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watched_indexes",
        sa.Column("course_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watched_indexes", "course_name")
