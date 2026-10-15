"""Authenticate using the actual restricted logins, not an admin SET ROLE."""

import os
import uuid

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.db.runtime import api_transaction, worker_transaction
from app.db.session import Database


@pytest.fixture(scope="module", params=["api", "worker"])
def runtime_login(request):
    key = (
        "SAFERETURN_API_DATABASE_URL"
        if request.param == "api"
        else "SAFERETURN_WORKER_DATABASE_URL"
    )
    url = os.environ.get(key)
    if not url:
        pytest.skip("Dedicated development runtime login not provisioned")
    db = Database.from_settings(
        Settings(database_url=SecretStr(url), database_pool_size=1)
    )
    try:
        yield request.param, db
    finally:
        db.close()


def scope(kind, db):
    return (
        api_transaction(db) if kind == "api" else worker_transaction(db, "smoke-worker")
    )


def test_activation_procedures_preserve_runtime_separation(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        assert session.execute(
            text(
                "SELECT has_function_privilege(current_user,'public.sr_lock_profile_qr(uuid,text)','EXECUTE')"
            )
        ).scalar_one() is (kind == "api")
        assert session.execute(
            text(
                "SELECT has_function_privilege(current_user,'public.sr_confirm_activation(uuid,text,text)','EXECUTE')"
            )
        ).scalar_one() is (kind == "api")
        assert (
            session.execute(
                text(
                    "SELECT has_table_privilege(current_user,'public.activation_intents','INSERT')"
                )
            ).scalar_one()
            is False
        )
        for role in ("anon", "authenticated"):
            assert (
                session.execute(
                    text(
                        "SELECT has_function_privilege(:role,'public.sr_confirm_activation(uuid,text,text)','EXECUTE')"
                    ),
                    {"role": role},
                ).scalar_one()
                is False
            )
    if kind == "api":
        with scope(kind, db) as session:
            assert (
                session.execute(
                    text(
                        "SELECT public.sr_activation_context('nonexistent-task32-token')"
                    )
                ).scalar_one()
                is None
            )
    else:
        with pytest.raises(DBAPIError), scope(kind, db) as session:
            session.execute(
                text("SELECT public.sr_activation_context('nonexistent-task32-token')")
            )


def test_real_login_attributes_and_no_role_escalation(runtime_login):
    kind, db = runtime_login
    expected = "safereturn_" + kind
    other = "safereturn_worker" if kind == "api" else "safereturn_api"
    with scope(kind, db) as session:
        assert session.execute(text("SELECT current_user,session_user")).one() == (
            expected,
            expected + "_login",
        )
        assert session.execute(
            text(
                "SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=session_user"
            )
        ).one() == (False, False, False, False)
    with pytest.raises(DBAPIError), scope(kind, db) as session:
        session.execute(text("SET LOCAL ROLE " + other))
    with pytest.raises(DBAPIError), scope(kind, db) as session:
        session.execute(text("SET LOCAL ROLE postgres"))


def test_runtime_pool_context_is_cleared_after_commit_and_rollback(runtime_login):
    kind, db = runtime_login
    context = (
        api_transaction(db, uuid.uuid4(), mfa_verified=True)
        if kind == "api"
        else worker_transaction(db, "smoke-worker")
    )
    with context as session:
        assert (
            session.execute(text("SELECT current_user")).scalar_one()
            == "safereturn_" + kind
        )
    with db.session() as session:
        assert (
            session.execute(text("SELECT current_user")).scalar_one()
            == "safereturn_" + kind + "_login"
        )
        assert session.execute(
            text(
                "SELECT NULLIF(current_setting('safereturn.actor_id',true),''),NULLIF(current_setting('safereturn.worker_id',true),'')"
            )
        ).one() == (None, None)
    with pytest.raises(RuntimeError), scope(kind, db):
        raise RuntimeError("synthetic service failure")
    with db.session() as session:
        assert (
            session.execute(text("SELECT current_user")).scalar_one()
            == "safereturn_" + kind + "_login"
        )
    assert db.engine.pool.checkedout() == 0


def test_reset_role_cannot_read_private_tables(runtime_login):
    kind, db = runtime_login
    with pytest.raises(DBAPIError), scope(kind, db) as session:
        session.execute(text("RESET ROLE"))
        session.execute(text("SELECT * FROM public.ice_contacts"))
    with pytest.raises(DBAPIError), scope(kind, db) as session:
        session.execute(text("CREATE TABLE public.runtime_escape(id integer)"))
