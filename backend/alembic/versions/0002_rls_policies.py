"""rls_policies

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08

Milestone 5: Multi-Tenancy Hardening + RLS

Creates two least-privilege Postgres roles and RLS policies for all
tenant-scoped tables.

Roles
-----
sniper_api    — NOBYPASSRLS.  Used by FastAPI (API_DATABASE_URL).
sniper_worker — BYPASSRLS.    Used by Celery worker (WORKER_DATABASE_URL).

Both roles are created with IF-NOT-EXISTS guards so re-running upgrade is safe.
In development the existing superuser role (sniper) is typically used for both,
meaning RLS policies exist but do not enforce (superusers always bypass RLS).

RLS context variable
--------------------
All policies read  current_setting('app.current_tenant_id', TRUE).
The get_current_user dependency sets this via:
    SELECT set_config('app.current_tenant_id', :tid, TRUE)
The TRUE flag makes it transaction-local (equivalent to SET LOCAL) — the value
is automatically cleared on commit/rollback, preventing pool bleed.

Policy design
-------------
users / tenants:
  ctx = '' (no context set) is permissive — required for auth routes (login,
  register, refresh) that must query by email before any tenant identity exists.

watched_indexes / notification_channels / notification_log:
  ctx must be non-empty AND tenant_id must match — blocks all access when
  no context is set. FORCE ROW LEVEL SECURITY is applied so the table owner
  is also subject to policies.

Downgrade
---------
Drops policies and revokes grants. Roles are NOT dropped (shared resource;
dropping could break other sessions). Remove them manually if desired.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that must have context set (no-context → denied)
_STRICT_TABLES = ("watched_indexes", "notification_channels", "notification_log")
# Tables permissive when no context (auth bootstrapping)
_PERMISSIVE_TABLES = ("users", "tenants")

_CTX = "current_setting('app.current_tenant_id', TRUE)"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Roles (idempotent)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sniper_api') THEN
                CREATE ROLE sniper_api WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOBYPASSRLS PASSWORD 'sniper_api_dev';
            END IF;
        END
        $$
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sniper_worker') THEN
                CREATE ROLE sniper_worker WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    BYPASSRLS PASSWORD 'sniper_worker_dev';
            END IF;
        END
        $$
    """)

    # ------------------------------------------------------------------
    # Grants
    # ------------------------------------------------------------------
    for role in ("sniper_api", "sniper_worker"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}")

    # ------------------------------------------------------------------
    # RLS policies — users table
    # Permissive SELECT when no context (email-based login/register lookup).
    # INSERT also permissive (registration bootstrap).
    # ------------------------------------------------------------------
    op.execute(f"""
        CREATE POLICY users_rls ON users
            USING (
                {_CTX} = ''
                OR tenant_id = NULLIF({_CTX}, '')::uuid
            )
            WITH CHECK (
                {_CTX} = ''
                OR tenant_id = NULLIF({_CTX}, '')::uuid
            )
    """)

    # ------------------------------------------------------------------
    # RLS policies — tenants table
    # SELECT: permissive when no context, own tenant otherwise.
    # INSERT: only during registration (no context set yet).
    # ------------------------------------------------------------------
    op.execute(f"""
        CREATE POLICY tenants_rls ON tenants
            USING (
                {_CTX} = ''
                OR id = NULLIF({_CTX}, '')::uuid
            )
            WITH CHECK ({_CTX} = '')
    """)

    # ------------------------------------------------------------------
    # RLS policies — strict tables (context required)
    # ------------------------------------------------------------------
    for table in _STRICT_TABLES:
        op.execute(f"""
            CREATE POLICY {table}_rls ON {table}
                USING (
                    {_CTX} != ''
                    AND tenant_id = NULLIF({_CTX}, '')::uuid
                )
                WITH CHECK (
                    {_CTX} != ''
                    AND tenant_id = NULLIF({_CTX}, '')::uuid
                )
        """)
        # FORCE ROW LEVEL SECURITY: applies policies to the table owner (sniper)
        # when it connects as a non-superuser session. Superusers still bypass.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Remove FORCE RLS from strict tables
    for table in _STRICT_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_rls ON {table}")

    op.execute("DROP POLICY IF EXISTS tenants_rls ON tenants")
    op.execute("DROP POLICY IF EXISTS users_rls ON users")

    for role in ("sniper_api", "sniper_worker"):
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}")
