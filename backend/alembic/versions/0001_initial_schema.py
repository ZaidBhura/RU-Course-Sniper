"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-04-16

Milestone 1: Schema + Tenancy Foundations

Creates all six tables:
  tenants, users, watched_indexes, notification_channels, index_state, notification_log

Tenancy strategy:
  - All tenant-scoped tables have a tenant_id UUID FK column from day one.
  - RLS DDL (ENABLE ROW LEVEL SECURITY) is applied now but policy ENFORCEMENT
    is deferred to Milestone 5 — the application role uses BYPASSRLS in M1–M4.
  - Application-level tenant_id filtering is used in M1–M4.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extension
    # ------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ------------------------------------------------------------------
    # tenants
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("university_code", sa.String(), nullable=False, server_default="RU"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("idx_users_tenant_id", "users", ["tenant_id"])

    # ------------------------------------------------------------------
    # watched_indexes
    # ------------------------------------------------------------------
    op.create_table(
        "watched_indexes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("index_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("semester_code", sa.String(), nullable=False, server_default="12026"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "index_number",
            "semester_code",
            name="uq_watched_indexes_user_index_semester",
        ),
        sa.CheckConstraint(
            "index_number BETWEEN 1 AND 99999",
            name="chk_watched_indexes_index_number_range",
        ),
    )
    op.create_index("idx_watched_indexes_tenant_id", "watched_indexes", ["tenant_id"])
    op.create_index("idx_watched_indexes_user_id", "watched_indexes", ["user_id"])
    op.create_index(
        "idx_watched_indexes_active",
        "watched_indexes",
        ["index_number", "semester_code"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ------------------------------------------------------------------
    # notification_channels
    # ------------------------------------------------------------------
    op.create_table(
        "notification_channels",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(), nullable=False),
        sa.Column("credential_blob", sa.LargeBinary(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "channel_type", name="uq_notification_channels_user_type"
        ),
        sa.CheckConstraint(
            "channel_type IN ('discord', 'pushover')",
            name="chk_notification_channels_type",
        ),
    )
    op.create_index(
        "idx_notification_channels_tenant_id", "notification_channels", ["tenant_id"]
    )
    op.create_index(
        "idx_notification_channels_user_id", "notification_channels", ["user_id"]
    )

    # ------------------------------------------------------------------
    # index_state  (global, no tenant_id)
    # ------------------------------------------------------------------
    op.create_table(
        "index_state",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("index_number", sa.Integer(), nullable=False),
        sa.Column("semester_code", sa.String(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_polled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "index_number", "semester_code", name="uq_index_state_index_semester"
        ),
    )
    op.create_index(
        "idx_index_state_open",
        "index_state",
        ["index_number", "semester_code"],
        postgresql_where=sa.text("is_open = TRUE"),
    )

    # ------------------------------------------------------------------
    # notification_log  (append-only, no updated_at)
    # ------------------------------------------------------------------
    op.create_table(
        "notification_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "watched_index_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watched_indexes.id"),
            nullable=False,
        ),
        sa.Column("index_number", sa.Integer(), nullable=False),
        sa.Column("semester_code", sa.String(), nullable=False),
        sa.Column("channel_type", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("delivery_status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("course_subject", sa.String(), nullable=True),
        sa.Column("course_number", sa.String(), nullable=True),
        sa.Column("course_title", sa.String(), nullable=True),
        sa.Column("webreg_url", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('open_notify', 'close_reset')",
            name="chk_notification_log_event_type",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('sent', 'failed', 'skipped')",
            name="chk_notification_log_delivery_status",
        ),
    )
    op.create_index("idx_notification_log_user_id", "notification_log", ["user_id"])
    op.create_index("idx_notification_log_tenant_id", "notification_log", ["tenant_id"])
    op.create_index(
        "idx_notification_log_created_at", "notification_log", ["created_at"],
        postgresql_using="btree",
    )
    op.create_index(
        "idx_notification_log_index_semester",
        "notification_log",
        ["index_number", "semester_code"],
    )

    # ------------------------------------------------------------------
    # RLS: DDL defined here, enforcement deferred to Milestone 5.
    # The application role uses BYPASSRLS in M1–M4.
    # index_state is intentionally excluded (global table, no tenant_id).
    # ------------------------------------------------------------------
    for table in ("tenants", "users", "watched_indexes", "notification_channels", "notification_log"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in ("tenants", "users", "watched_indexes", "notification_channels", "notification_log"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("notification_log")
    op.drop_table("index_state")
    op.drop_table("notification_channels")
    op.drop_table("watched_indexes")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
