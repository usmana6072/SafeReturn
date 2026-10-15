"""Signed JWT → FastAPI dependency → real PostgreSQL RLS/owner/staff guards.

All positive account/session fixtures live only in UUID rehearsal schemas.
Actual restricted logins also verify the installed projection/permission boundary.
"""

import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_auth import ORIGIN, claims, keyset, signed
from test_commerce_schema import sample as commerce_sample
from test_health import ASGIClient
from test_identity_schema import pair, qr
from test_workflow_schema import workflow_sample

from app.api.auth import (
    AccessError,
    Authenticated,
    authorize,
    require_message_recipient,
    require_order_owner,
    require_pair_owner,
    require_payment_owner,
    require_qr_owner,
    require_staff,
    require_verified_account,
)
from app.core.auth import AuthRequired, JWTVerifier, Principal
from app.core.config import Settings
from app.db.runtime import api_transaction, worker_transaction
from app.db.session import Database
from app.main import create_app


@pytest.fixture(scope="module")
def guarded():
    with rehearsal() as pg:
        with pg.connect() as c:
            pg.upgrade(c)
            c.commit()
            pg.assert_catalog(c)
            wf = workflow_sample.__wrapped__(c)
            commerce = commerce_sample.__wrapped__(c)
            sessions = {}
            for uid in c.execute(text("SELECT id FROM auth.users")).scalars().all():
                sid = uuid.uuid4()
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:uid,'aal2',now()+interval '1 hour')"
                    ),
                    {"sid": sid, "uid": uid},
                )
                sessions[uid] = sid
            c.execute(text("UPDATE auth.users SET email_confirmed_at=now()"))
            c.commit()
        private = ec.generate_private_key(ec.SECP256R1())
        provider = JWTVerifier(
            Settings(supabase_url=ORIGIN),
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"keys": [keyset(private)]})
            ),
        )
        app = create_app(Settings(supabase_url=ORIGIN), verifier=provider)
        app.state.database, app.state.jwt_verifier = Database(pg.engine), provider
        guards = {
            "pair": require_pair_owner,
            "qr": require_qr_owner,
            "order": require_order_owner,
            "payment": require_payment_owner,
            "message": require_message_recipient,
        }

        @app.get("/guard/resource/{kind}/{rid}")
        def resource(kind: str, rid: uuid.UUID, context: Authenticated):
            guards[kind](context, rid)
            return {"ok": True}

        @app.get("/guard/verified")
        def verified(context: Authenticated):
            require_verified_account(context)
            return {"ok": True}

        @app.get("/guard/finance")
        def finance(context: Authenticated):
            require_staff(context, "finance")
            return {"ok": True}

        @app.get("/guard/lost/{rid}")
        def lost(rid: uuid.UUID, context: Authenticated):
            require_qr_owner(context, rid, tag_type="lost")
            return {"ok": True}

        @app.post("/guard/rollback")
        def rollback(context: Authenticated):
            context.session.execute(
                text(
                    "INSERT INTO public.user_profiles(user_id,display_name) VALUES(:id,'rollback-marker') ON CONFLICT(user_id) DO UPDATE SET display_name='rollback-marker'"
                ),
                {"id": context.principal.user_id},
            )
            raise AccessError(403)

        def headers(uid, **extra):
            payload = claims(
                **{
                    "sub": str(uid),
                    "session_id": str(sessions[uid]),
                    "aal": "aal2",
                    **extra,
                }
            )
            return {"Authorization": "Bearer " + signed(private, payload)}

        try:
            yield pg, wf, commerce, sessions, headers, ASGIClient(app)
        finally:
            provider.close()


@contextmanager
def change(pg, table, identity, updates):
    # Table/column names originate only in these tests, never env or requests.
    columns = list(updates)
    with pg.connect() as c:
        old = dict(
            c.execute(
                text(f"SELECT {','.join(columns)} FROM {table} WHERE id=:id"),
                {"id": identity},
            )
            .mappings()
            .one()
        )
        c.execute(
            text(
                f"UPDATE {table} SET "
                + ",".join(f"{column}=:{column}" for column in columns)
                + " WHERE id=:id"
            ),
            {"id": identity, **updates},
        )
        c.commit()
    try:
        yield
    finally:
        with pg.connect() as c:
            c.execute(
                text(
                    f"UPDATE {table} SET "
                    + ",".join(f"{column}=:{column}" for column in columns)
                    + " WHERE id=:id"
                ),
                {"id": identity, **old},
            )
            c.commit()


@pytest.mark.parametrize("kind", ["pair", "qr", "order", "payment", "message"])
def test_owner_guard_success_cross_owner_and_missing_are_concealed(guarded, kind):
    _, wf, commerce, _, headers, client = guarded
    rid, owner = {
        "pair": (wf["pa"], wf["a"]),
        "qr": (wf["la"], wf["a"]),
        "order": (commerce["purchase"], commerce["customer"]),
        "payment": (commerce["attempt"], commerce["customer"]),
        "message": (wf["ma"], wf["a"]),
    }[kind]
    assert (
        client.get(f"/guard/resource/{kind}/{rid}", headers=headers(owner)).status_code
        == 200
    )
    denied = client.get(f"/guard/resource/{kind}/{rid}", headers=headers(wf["b"]))
    missing = client.get(
        f"/guard/resource/{kind}/{uuid.uuid4()}", headers=headers(wf["b"])
    )
    assert denied.status_code == missing.status_code == 404
    for key in ("code", "message", "message_ur", "details"):
        assert denied.json()["error"][key] == missing.json()["error"][key]
    assert str(rid) not in denied.text
    assert denied.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("state", ["banned", "deleted", "anonymous", "expired-session"])
def test_account_and_session_state_checked_per_request(guarded, state):
    pg, wf, _, sessions, headers, client = guarded
    # Provider/DB timestamps are checked by PostgreSQL, whose clock may differ
    # from the client. Derive fixture transitions from that authoritative clock.
    with pg.connect() as c:
        database_now = c.execute(text("SELECT clock_timestamp()")).scalar_one()
    table, uid, updates = {
        "banned": (
            "auth.users",
            wf["a"],
            {"banned_until": database_now + timedelta(hours=1)},
        ),
        "deleted": ("auth.users", wf["a"], {"deleted_at": database_now}),
        "anonymous": ("auth.users", wf["a"], {"is_anonymous": True}),
        "expired-session": (
            "auth.sessions",
            sessions[wf["a"]],
            {"not_after": database_now - timedelta(seconds=1)},
        ),
    }[state]
    token = headers(wf["a"])
    assert client.get("/guard/verified", headers=token).status_code == 200
    with change(pg, table, uid, updates):
        assert client.get("/guard/verified", headers=token).status_code == 401
    assert client.get("/guard/verified", headers=token).status_code == 200


def test_email_confirmation_comes_from_auth_not_token_metadata(guarded):
    pg, wf, _, _, headers, client = guarded
    with change(pg, "auth.users", wf["a"], {"email_confirmed_at": None}):
        forged = headers(
            wf["a"], email_verified=True, user_metadata={"email_verified": True}
        )
        assert client.get("/guard/verified", headers=forged).status_code == 403
        assert (
            client.get(f"/guard/resource/pair/{wf['pa']}", headers=forged).status_code
            == 200
        )


def test_staff_requires_database_role_and_session_backed_mfa(guarded):
    pg, wf, _, sessions, headers, client = guarded
    assert (
        client.get("/guard/finance", headers=headers(wf["finance"])).status_code == 200
    )
    assert (
        client.get("/guard/finance", headers=headers(wf["operations"])).status_code
        == 403
    )
    assert (
        client.get(
            "/guard/finance",
            headers=headers(
                wf["a"],
                app_metadata={"role": "finance"},
                user_metadata={"is_admin": True},
            ),
        ).status_code
        == 403
    )
    # Both signed JWT assurance and current provider session assurance are needed.
    assert (
        client.get(
            "/guard/finance", headers=headers(wf["finance"], aal="aal1")
        ).status_code
        == 403
    )
    token = headers(wf["finance"])
    with change(pg, "auth.sessions", sessions[wf["finance"]], {"aal": "aal1"}):
        assert client.get("/guard/finance", headers=token).status_code == 403
    with pg.connect() as c:
        role_id = c.execute(
            text("SELECT id FROM staff_roles WHERE user_id=:id AND role='finance'"),
            {"id": wf["finance"]},
        ).scalar_one()
    with change(pg, "staff_roles", role_id, {"revoked_at": datetime.now(UTC)}):
        assert client.get("/guard/finance", headers=token).status_code == 403
    assert client.get("/guard/finance", headers=token).status_code == 200


def test_qr_purpose_and_message_recipient_survive_transfer(guarded):
    pg, wf, _, _, headers, client = guarded
    assert (
        client.get(f"/guard/lost/{wf['la']}", headers=headers(wf["a"])).status_code
        == 200
    )
    assert (
        client.get(f"/guard/lost/{wf['ia']}", headers=headers(wf["a"])).status_code
        == 404
    )
    with change(pg, "tag_pairs", wf["pa"], {"owner_user_id": wf["b"]}):
        assert (
            client.get(
                f"/guard/resource/pair/{wf['pa']}", headers=headers(wf["a"])
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/guard/resource/pair/{wf['pa']}", headers=headers(wf["b"])
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/guard/resource/message/{wf['ma']}", headers=headers(wf["a"])
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/guard/resource/message/{wf['ma']}", headers=headers(wf["b"])
            ).status_code
            == 404
        )


def test_dependency_rolls_back_and_clears_context_after_denial(guarded):
    pg, wf, _, _, headers, client = guarded
    assert client.post("/guard/rollback", headers=headers(wf["a"])).status_code == 403
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM user_profiles WHERE display_name='rollback-marker'"
                )
            ).scalar_one()
            == 0
        )
        assert c.execute(
            text(
                "SELECT current_user, NULLIF(current_setting('safereturn.actor_id',true),''),NULLIF(current_setting('safereturn.mfa_verified',true),'')"
            )
        ).one()[1:] == (None, None)


def test_session_must_exist_and_belong_to_signed_subject(guarded):
    _, wf, _, sessions, headers, client = guarded
    for sid in (sessions[wf["b"]], uuid.uuid4()):
        assert (
            client.get(
                "/guard/verified", headers=headers(wf["a"], session_id=str(sid))
            ).status_code
            == 401
        )


def test_historical_qr_is_not_a_current_profile_target(guarded):
    pg, wf, _, _, headers, client = guarded
    with pg.connect() as c:
        pid, tags = pair(c)
        c.execute(
            text(
                "UPDATE tag_pairs SET owner_user_id=:uid,ownership_status='active',activated_at=now() WHERE id=:id"
            ),
            {"uid": wf["a"], "id": pid},
        )
        c.execute(
            text(
                "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:id"
            ),
            {"id": tags["lost"]},
        )
        replacement = qr(c, pid, "lost", old=tags["lost"])
        c.commit()
    assert (
        client.get(
            f"/guard/resource/qr/{tags['lost']}", headers=headers(wf["a"])
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/guard/resource/qr/{replacement}", headers=headers(wf["a"])
        ).status_code
        == 200
    )


def test_actual_restricted_logins_projection_and_auth_table_denial():
    for kind in ("api", "worker"):
        db = Database.from_settings(
            Settings(
                database_url=SecretStr(
                    os.environ[f"SAFERETURN_{kind.upper()}_DATABASE_URL"]
                )
            )
        )
        try:
            uid = uuid.uuid4()
            if kind == "api":
                with (
                    pytest.raises(AccessError) as denied,
                    api_transaction(db, uid) as session,
                ):
                    authorize(session, Principal(uid, uuid.uuid4(), False))
                assert denied.value.status == 401
            else:
                with (
                    pytest.raises(DBAPIError) as denied,
                    worker_transaction(db, "auth-guard-check") as session,
                ):
                    session.execute(
                        text("SELECT * FROM public.sr_account_session_state(:id)"),
                        {"id": uuid.uuid4()},
                    )
                assert denied.value.orig.sqlstate == "42501"
            with (
                pytest.raises(DBAPIError) as denied,
                api_transaction(db)
                if kind == "api"
                else worker_transaction(db, "auth-guard-check") as session,
            ):
                session.execute(text("SELECT id FROM auth.users LIMIT 1"))
            assert denied.value.orig.sqlstate == "42501"
        finally:
            db.close()


def test_live_supabase_public_key_rejects_foreign_signature():
    settings = Settings()
    assert settings.supabase_url
    response = httpx.get(
        settings.supabase_url + "/auth/v1/.well-known/jwks.json", timeout=10
    )
    response.raise_for_status()
    key = response.json()["keys"][0]
    assert key["alg"] == "ES256"
    provider = JWTVerifier(settings)
    try:
        private = ec.generate_private_key(ec.SECP256R1())
        payload = claims(iss=settings.supabase_url + "/auth/v1")
        with pytest.raises(AuthRequired):
            provider.verify(signed(private, payload, kid=key["kid"]))
    finally:
        provider.close()
