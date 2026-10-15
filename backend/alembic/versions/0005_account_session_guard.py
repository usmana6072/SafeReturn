"""Narrow active-account/session projection; no managed Auth writes or grants."""

from sqlalchemy import inspect, text

from alembic import op

revision = "0005_account_session_guard"
down_revision = "0004_runtime_privacy"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    required = {
        "users": {
            "id",
            "email_confirmed_at",
            "deleted_at",
            "banned_until",
            "is_anonymous",
        },
        "sessions": {"id", "user_id", "not_after", "aal"},
    }
    for table, columns in required.items():
        if not inspector.has_table(table, schema="auth") or not columns.issubset(
            {column["name"] for column in inspector.get_columns(table, schema="auth")}
        ):
            raise RuntimeError(
                "Managed Auth metadata requires reconciliation; nothing changed"
            )
    if bind.execute(
        text(
            "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='sr_account_session_state'"
        )
    ).scalar_one():
        raise RuntimeError(
            "Existing session guard requires reconciliation; nothing changed"
        )
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("""
CREATE FUNCTION public.sr_account_session_state(sid uuid)
RETURNS TABLE(email_verified boolean, mfa_active boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT u.email_confirmed_at IS NOT NULL, s.aal::text='aal2'
 FROM auth.users u JOIN auth.sessions s ON s.user_id=u.id
 WHERE u.id=public.sr_actor_id() AND s.id=sid
 AND u.deleted_at IS NULL AND NOT COALESCE(u.is_anonymous,false)
 AND (u.banned_until IS NULL OR u.banned_until<=pg_catalog.statement_timestamp())
 AND (s.not_after IS NULL OR s.not_after>pg_catalog.statement_timestamp())
$$;
REVOKE ALL ON FUNCTION public.sr_account_session_state(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.sr_account_session_state(uuid) TO safereturn_api;
""")


def downgrade():
    raise RuntimeError("Auth guard downgrade disabled; use reviewed forward correction")
