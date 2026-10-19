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


def test_notification_recipient_is_worker_only_and_has_no_auth_table_grant(
    runtime_login,
):
    kind, db = runtime_login
    with scope(kind, db) as session:
        assert session.execute(
            text(
                "SELECT has_function_privilege(current_user,'public.sr_notification_recipient(uuid,integer,bytea,smallint)','EXECUTE')"
            )
        ).scalar_one() is (kind == "worker")
        assert (
            session.execute(
                text(
                    "SELECT has_table_privilege(current_user,c.oid,'SELECT') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='auth' AND c.relname='users'"
                )
            ).scalar_one()
            is False
        )
        if kind == "worker":
            assert (
                session.execute(
                    text("SELECT public.sr_notification_recipient(:id,1,NULL,NULL)"),
                    {"id": uuid.uuid4()},
                ).scalar_one()
                is None
            )


def test_finder_procedures_preserve_runtime_separation(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        permissions = session.execute(
            text(
                "SELECT p.proname,has_function_privilege(current_user,p.oid,'EXECUTE') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('sr_public_finder_budget','sr_public_lost_qr_id','sr_public_submit_finder_message')"
            )
        ).all()
        assert len(permissions) == 3
        assert all(allowed is (kind == "api") for _, allowed in permissions)
        if kind == "api":
            assert (
                session.execute(
                    text("SELECT public.sr_public_finder_budget('invalid','invalid')")
                ).scalar_one()
                is False
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


def test_public_qr_projection_preserves_restricted_logins(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        for function in ("sr_public_qr_projection", "sr_public_scan_rate"):
            assert session.execute(
                text(
                    "SELECT has_function_privilege(current_user,:signature,'EXECUTE')"
                ),
                {"signature": f"public.{function}(text)"},
            ).scalar_one() is (kind == "api")
        if kind == "api":
            assert (
                session.execute(
                    text("SELECT count(*) FROM public.ice_contacts")
                ).scalar_one()
                == 0
            )
    if kind == "api":
        with scope(kind, db) as session:
            assert (
                session.execute(
                    text(
                        "SELECT public.sr_public_qr_projection('nonexistent-task41-token')"
                    )
                ).scalar_one()
                is None
            )
    else:
        with pytest.raises(DBAPIError), scope(kind, db) as session:
            session.execute(
                text(
                    "SELECT public.sr_public_qr_projection('nonexistent-task41-token')"
                )
            )
        with pytest.raises(DBAPIError), scope(kind, db) as session:
            session.execute(text("SELECT count(*) FROM public.ice_contacts"))


def test_public_contact_functions_are_api_only(runtime_login):
    kind, db = runtime_login
    signatures = (
        "sr_public_ice_contact(text,uuid)",
        "sr_public_whatsapp_link(text)",
        "sr_public_contact_budget(text,text,text)",
        "sr_public_contact_proof(text)",
        "sr_public_whatsapp_available(text)",
    )
    with scope(kind, db) as session:
        for signature in signatures:
            assert session.execute(
                text(
                    "SELECT has_function_privilege(current_user,:signature,'EXECUTE')"
                ),
                {"signature": "public." + signature},
            ).scalar_one() is (kind == "api")
    with scope(kind, db) as session:
        if kind == "api":
            assert (
                session.execute(
                    text(
                        "SELECT public.sr_public_ice_contact('nonexistent-task42-token',:id)"
                    ),
                    {"id": uuid.uuid4()},
                ).scalar_one()
                is None
            )
        else:
            with pytest.raises(DBAPIError), session.begin_nested():
                session.execute(
                    text(
                        "SELECT public.sr_public_ice_contact('nonexistent-task42-token',:id)"
                    ),
                    {"id": uuid.uuid4()},
                )


def test_catalog_projection_and_unlink_privileges(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        allowed = session.execute(
            text(
                "SELECT has_function_privilege(current_user,'public.sr_public_catalog(text)','EXECUTE')"
            )
        ).scalar_one()
        assert allowed is (kind == "api")
        if kind == "api":
            assert isinstance(
                session.execute(
                    text("SELECT public.sr_public_catalog(NULL)")
                ).scalar_one(),
                list,
            )
            # Anonymous API context has zero writable catalog rows under RLS.
            assert (
                session.execute(
                    text("UPDATE public.products SET name=name RETURNING id")
                ).all()
                == []
            )
            assert (
                session.execute(
                    text("DELETE FROM public.product_images RETURNING id")
                ).all()
                == []
            )
        assert not session.execute(
            text(
                "SELECT has_table_privilege(current_user,c.oid,'SELECT') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='auth' AND c.relname='users'"
            )
        ).scalar_one()


def test_checkout_owner_scope_and_definer_separation(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        for function in (
            "sr_checkout_catalog(uuid[])",
            "sr_checkout_capacity()",
            "sr_checkout_reserve(uuid,uuid,uuid,integer)",
        ):
            assert session.execute(
                text("SELECT has_function_privilege(current_user,:function,'EXECUTE')"),
                {"function": "public." + function},
            ).scalar_one() is (kind == "api")
        assert session.execute(
            text(
                "SELECT has_table_privilege(current_user,'public.checkout_quotes','SELECT')"
            )
        ).scalar_one() is (kind == "api")
        if kind == "api":
            assert (
                session.execute(
                    text("SELECT public.sr_checkout_catalog(ARRAY[]::uuid[])")
                ).scalar_one()
                == []
            )
            assert (
                session.execute(
                    text("SELECT public.sr_checkout_capacity()")
                ).scalar_one()
                == 0
            )
            assert (
                session.execute(text("SELECT id FROM public.checkout_quotes")).all()
                == []
            )
            assert (
                session.execute(
                    text(
                        "UPDATE public.checkout_quotes SET status='expired' RETURNING id"
                    )
                ).all()
                == []
            )


def test_private_print_helpers_and_tables_are_role_scoped(runtime_login):
    kind, db = runtime_login
    with scope(kind, db) as session:
        for fn in ("sr_print_occurrences(uuid)", "sr_print_order_lock(uuid)"):
            assert session.execute(
                text("SELECT has_function_privilege(current_user,:fn,'EXECUTE')"),
                {"fn": "public." + fn},
            ).scalar_one()
        assert (
            session.execute(
                text("SELECT count(*) FROM public.sr_print_occurrences(:id)"),
                {"id": uuid.uuid4()},
            ).scalar_one()
            == 0
        )
        assert (
            session.execute(
                text("SELECT public.sr_print_order_lock(:id)"), {"id": uuid.uuid4()}
            ).scalar_one()
            is None
        )
        for table in ("print_download_grants", "print_job_qa"):
            assert session.execute(
                text("SELECT has_table_privilege(current_user,:t,'SELECT')"),
                {"t": "public." + table},
            ).scalar_one() is (kind == "api")
        if kind == "api":
            assert (
                session.execute(
                    text("SELECT id FROM public.print_download_grants")
                ).all()
                == []
            )
            assert (
                session.execute(text("SELECT id FROM public.print_job_qa")).all() == []
            )
            assert (
                session.execute(
                    text(
                        "UPDATE public.print_download_grants SET used_at=now() RETURNING id"
                    )
                ).all()
                == []
            )


def test_fulfillment_eligibility_is_api_only_without_finance_read_expansion(
    runtime_login,
):
    kind, db = runtime_login
    with scope(kind, db) as session:
        allowed = session.execute(
            text(
                "SELECT has_function_privilege(current_user,'public.sr_fulfillment_eligible(uuid)','EXECUTE')"
            )
        ).scalar_one()
        assert allowed is (kind == "api")
        if kind == "api":
            assert (
                session.execute(
                    text("SELECT public.sr_fulfillment_eligible(:id)"),
                    {"id": uuid.uuid4()},
                ).scalar_one()
                is False
            )
        for role in ["anon", "authenticated"]:
            assert (
                session.execute(
                    text(
                        "SELECT has_function_privilege(:role,'public.sr_fulfillment_eligible(uuid)','EXECUTE')"
                    ),
                    {"role": role},
                ).scalar_one()
                is False
            )


def test_retention_recovery_functions_are_narrow_and_require_context(runtime_login):
    kind, db = runtime_login
    functions = {
        "sr_retention_held(text,uuid)": "api",
        "sr_retention_retry(uuid,text)": "api",
        "sr_retention_schedule(text)": "worker",
        "sr_retention_prepare(uuid,integer,text)": "worker",
        "sr_retention_finish(uuid,integer)": "worker",
        "sr_retention_admission()": None,
        "sr_retention_identity()": None,
        "sr_worker_finance(uuid)": "worker",
        "sr_finance_changed()": None,
    }
    with scope(kind, db) as session:
        for function, allowed in functions.items():
            assert session.execute(
                text("SELECT has_function_privilege(current_user,:fn,'EXECUTE')"),
                {"fn": "public." + function},
            ).scalar_one() is (kind == allowed)
            for public_role in ("anon", "authenticated"):
                assert not session.execute(
                    text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                    {"role": public_role, "fn": "public." + function},
                ).scalar_one()
        if kind == "api":
            assert not session.execute(
                text("SELECT public.sr_retention_held('print_artifact',:id)"),
                {"id": uuid.uuid4()},
            ).scalar_one()
        else:
            assert not session.execute(
                text("SELECT public.sr_worker_finance(:id)"), {"id": uuid.uuid4()}
            ).scalar_one()
    statements = (
        ["SELECT public.sr_retention_retry(:id,'SYNTHETIC')"]
        if kind == "api"
        else [
            "SELECT public.sr_retention_prepare(:id,1,'SYNTHETIC')",
            "SELECT public.sr_retention_finish(:id,1)",
        ]
    )
    for statement in statements:
        with pytest.raises(DBAPIError), scope(kind, db) as session:
            session.execute(text(statement), {"id": uuid.uuid4()})
