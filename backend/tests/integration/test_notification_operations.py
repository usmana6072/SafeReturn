"""Task 5.7H: isolated migration, canonical guards, metadata and recovery."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient
from test_notification_delivery import notification_database  # noqa: F401
from test_notification_delivery import sample as _sample

from app.core.auth import JWTVerifier
from app.main import create_app
from app.workers import notifications as worker

sample = _sample

BASE = "/api/v1/admin/notification-outbox"


@pytest.fixture(scope="module")
def ops(notification_database):  # noqa: F811
    pg, database, settings, *_ = notification_database
    with pg.connect() as c:
        pg.upgrade(c, "0019_retention_recovery")
        c.commit()
        if "sr_notification_metadata" not in dict(pg.installed_catalog["functions"]):
            pg.assert_catalog(c)
        pg.upgrade(c)
        c.rollback()
        assert c.execute(
            text(
                "SELECT to_regprocedure('public.sr_notification_retry(uuid,integer,integer,text,text)') IS NULL"
            )
        ).scalar_one()
        c.rollback()
        pg.upgrade(c)
        c.commit()
        if "sr_notification_metadata" in dict(pg.installed_catalog["functions"]):
            pg.assert_catalog(c)
        users = {
            role: uuid4()
            for role in [
                "operations",
                "finance",
                "support",
                "security_admin",
                "superadmin",
            ]
        }
        sessions = {role: uuid4() for role in users}
        for role, uid in users.items():
            c.execute(
                text(
                    "INSERT INTO auth.users(id,email,email_confirmed_at) VALUES(:id,:email,now())"
                ),
                {"id": uid, "email": role + "@synthetic.invalid"},
            )
            c.execute(
                text(
                    "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:id,'aal2',now()+interval '1 hour')"
                ),
                {"sid": sessions[role], "id": uid},
            )
            c.execute(
                text("INSERT INTO public.staff_roles(user_id,role) VALUES(:id,:role)"),
                {"id": uid, "role": role},
            )
        c.commit()
    private = ec.generate_private_key(ec.SECP256R1())
    provider = JWTVerifier(
        settings.model_copy(update={"supabase_url": ORIGIN}),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
        ),
    )
    app = create_app(
        settings.model_copy(update={"supabase_url": ORIGIN}), verifier=provider
    )
    app.state.database = database
    app.state.jwt_verifier = provider

    def headers(role="operations", aal="aal2", key=None):
        return {
            "Authorization": "Bearer "
            + signed(
                private,
                claims(sub=str(users[role]), session_id=str(sessions[role]), aal=aal),
            ),
            "Idempotency-Key": key or str(uuid4()),
        }

    yield pg, app, ASGIClient(app), headers, users, sessions
    provider.close()


def dead(sample, code="provider_http_401", count=1):
    oid = sample.enqueue()
    sample.update(
        "UPDATE public.notification_outbox SET status='dead',attempt_count=:n,last_error_code=:code WHERE id=:id",
        {"id": oid, "n": count, "code": code},
    )
    sample.update(
        "INSERT INTO public.notification_attempts(outbox_id,attempt_number,outcome,error_code,finished_at) VALUES(:id,:n,'permanent_failure',:code,now())",
        {"id": oid, "n": count, "code": code},
    )
    return oid


def retry(ops, oid, expected=1, key=None, **extra):
    return ops[2].post(
        BASE + f"/{oid}/retry",
        headers=ops[3](key=key),
        json={
            "expected_attempt_count": expected,
            "reason": "provider_recovered",
            "confirmed": True,
            **extra,
        },
    )


def test_roles_projection_filters_and_boundaries(ops, sample, caplog):
    pg, _app, client, headers, users, sessions = ops
    oid = dead(sample, code="PRIVATE_EMAIL_someone@example.invalid")
    assert client.get(BASE).status_code == 401
    for role in ["finance", "support", "superadmin"]:
        assert client.get(BASE, headers=headers(role)).status_code == 403
        assert (
            client.post(
                BASE + f"/{oid}/retry",
                headers=headers(role),
                json={
                    "expected_attempt_count": 1,
                    "reason": "provider_recovered",
                    "confirmed": True,
                },
            ).status_code
            == 403
        )
    assert client.get(BASE, headers=headers(aal="aal1")).status_code == 403
    for role in ["operations", "security_admin"]:
        r = client.get(
            BASE,
            headers=headers(role),
            params={"id": str(oid), "status": "dead", "attempt_limit": 1},
        )
        assert r.status_code == 200, r.text
        assert r.headers["cache-control"] == "no-store"
        item = r.json()["items"][0]
        assert item["last_error_code"] == "provider_failure"
        assert item["retry_blocked_reason"] == "manual_review_required"
        for secret in [
            "PRIVATE_EMAIL",
            "original-owner",
            "PRIVATE-FINDER",
            "ciphertext",
            "provider_message_id",
            "aggregate_id",
            "recipient_user_id",
            "idempotency_key",
            "lease_owner",
        ]:
            assert secret not in r.text and secret not in caplog.text
        assert len(item["attempts"]) == 1
    for params in [
        {"limit": 101},
        {"cursor": "bad"},
        {"status": "invalid"},
        {"attempt_before": 0},
        {"attempt_limit": 0},
    ]:
        assert client.get(BASE, headers=headers(), params=params).status_code == 422
    with pg.connect() as c:
        c.execute(
            text("UPDATE auth.sessions SET aal='aal1' WHERE id=:id"),
            {"id": sessions["operations"]},
        )
        c.commit()
    assert client.get(BASE, headers=headers()).status_code == 403
    with pg.connect() as c:
        c.execute(
            text("UPDATE auth.sessions SET aal='aal2' WHERE id=:id"),
            {"id": sessions["operations"]},
        )
        c.commit()
    for role in users:
        state = client.get("/api/v1/me/staff-security", headers=headers(role)).json()
        assert ("notifications.manage" in state["capabilities"]) == (
            role in ["operations", "security_admin"]
        )


def test_retry_idempotency_stale_claim_and_history(ops, sample):
    oid = dead(sample)
    key = str(uuid4())
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: retry(ops, oid, key=key), range(2)))
    assert [r.status_code for r in results] == [202, 202], [r.text for r in results]
    assert results[0].json() == results[1].json()
    assert retry(ops, oid, key=key, reason="recipient_reverified").status_code == 409
    assert retry(ops, oid, key=str(uuid4())).status_code == 409
    assert retry(ops, oid, expected=2).status_code == 412
    assert retry(ops, oid, confirmed=False).status_code == 422
    assert retry(ops, oid, confirmed=1).status_code == 422
    with sample.pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.notification_attempts WHERE outbox_id=:id"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='notification.retry' AND target_id=:id"
                ),
                {"id": oid},
            ).scalar_one()
            == 1
        )
    row = sample.row(oid)
    original_key = row["idempotency_key"]

    class Provider:
        def send(self, **kwargs):
            assert kwargs["idempotency_key"] == original_key
            assert "PRIVATE-FINDER" not in kwargs["html"]
            return "synthetic-accepted"

    # Other test fixtures may leave due work; claim only this event by delaying the rest.
    sample.update(
        "UPDATE public.notification_outbox SET next_attempt_at=now()+interval '1 day' WHERE id<>:id AND status IN ('pending','retry')",
        {"id": oid},
    )
    assert worker.process_one(
        sample.database, sample.settings, Provider(), worker_id="synthetic-ops-worker"
    )
    assert sample.row(oid)["status"] == "sent"
    assert sample.row(oid)["attempt_count"] == 2
    assert retry(ops, oid, expected=2).status_code == 409
    assert (
        retry(ops, oid, key=key).status_code == 202
    )  # receipt replay, not a second send


def test_cutoff_budget_recipient_and_active_refusals(ops, sample):
    oid = dead(sample)
    sample.update(
        "UPDATE public.notification_attempts SET attempted_at=now()-interval '24 hours' WHERE outbox_id=:id",
        {"id": oid},
    )
    assert retry(ops, oid).status_code == 409
    oid = dead(sample, count=sample.settings.notification_max_attempts)
    assert (
        retry(ops, oid, expected=sample.settings.notification_max_attempts).status_code
        == 409
    )
    oid = dead(sample)
    sample.update(
        "UPDATE public.finder_messages SET retention_until=now()-interval '1 day',deleted_at=now() WHERE id=(SELECT aggregate_id FROM public.notification_outbox WHERE id=:id)",
        {"id": oid},
    )
    assert retry(ops, oid).status_code == 409
    oid = dead(sample)
    sample.update(
        "UPDATE public.notification_outbox SET status='leased',lease_owner='synthetic-worker',lease_until=now()+interval '1 minute' WHERE id=:id",
        {"id": oid},
    )
    assert retry(ops, oid).status_code == 409
    sample.expire(oid)
    assert (
        retry(ops, oid).status_code == 409
    )  # expired leases remain worker recovery, never an admin resend
    assert retry(ops, uuid4()).status_code == 404


def test_worker_preserves_stable_keys_and_stale_fencing(ops, sample, monkeypatch):
    from test_notification_delivery import (
        test_crash_after_provider_acceptance_reclaims_with_same_key,
        test_same_worker_id_cannot_acknowledge_old_attempt,
    )

    test_same_worker_id_cannot_acknowledge_old_attempt(sample)
    test_crash_after_provider_acceptance_reclaims_with_same_key(sample, monkeypatch)


def test_notification_browser(ops, sample):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    _pg, app, _client, headers, users, _sessions = ops
    root = Path(__file__).parents[3]
    state = {"role": "operations", "stale_updates": 0}
    target = dead(sample)
    stale = dead(sample)
    user = lambda: {
        "id": str(users[state["role"]]),
        "aud": "authenticated",
        "role": "authenticated",
        "email": state["role"] + "@synthetic.invalid",
        "email_confirmed_at": "2026-01-01T00:00:00Z",
        "user_metadata": {},
        "app_metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
    }

    @app.get("/auth/v1/user")
    def fixture_user():
        return user()

    @app.post("/auth/v1/token")
    def fixture_token():
        return {
            "access_token": headers(state["role"])["Authorization"].removeprefix(
                "Bearer "
            ),
            "refresh_token": "synthetic-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user(),
        }

    @app.post("/fixture/notification-role/{role}")
    def fixture_role(role: str):
        assert role in users
        state["role"] = role
        return {"ok": True}

    @app.post("/fixture/notification-stale")
    def fixture_stale():
        state["stale_updates"] += 1
        if state["stale_updates"] > 1:
            sample.update(
                "UPDATE public.notification_outbox SET attempt_count=2 WHERE id=:id",
                {"id": stale},
            )
            sample.update(
                "INSERT INTO public.notification_attempts(outbox_id,attempt_number,outcome,error_code) VALUES(:id,2,'permanent_failure','provider_http_401')",
                {"id": stale},
            )
        return {"ok": True}

    @app.post("/fixture/notification-deliver/{oid}")
    def fixture_deliver(oid: str):
        assert oid == str(target)
        sample.update(
            "UPDATE public.notification_outbox SET next_attempt_at=now()+interval '1 day' WHERE id<>:id AND status IN ('pending','retry')",
            {"id": target},
        )

        class Provider:
            def send(self, **kwargs):
                return "synthetic-browser-acceptance"

        assert worker.process_one(
            sample.database,
            sample.settings,
            Provider(),
            worker_id="synthetic-browser-worker",
        )
        return {"ok": True}

    for port in (3100, 8115):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "Isolated port occupied"
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "TASK", "QR_TEST_"))
    }
    env.update(
        SAFERETURN_API_ORIGIN="http://127.0.0.1:8115",
        SAFERETURN_WEB_ORIGIN="http://127.0.0.1:3100",
        SAFERETURN_SUPABASE_URL="https://fixture.test",
        SAFERETURN_SUPABASE_PUBLISHABLE_KEY="sb_publishable_fixture",
        SAFERETURN_SESSION_SIGNING_KEY="ab" * 32,
        NEXT_TELEMETRY_DISABLED="1",
        PLAYWRIGHT_EXTERNAL_SERVER="1",
        PLAYWRIGHT_CHANNEL="msedge",
        NOTIFICATION_EVENT=str(target),
        NOTIFICATION_STALE=str(stale),
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8115,
            lifespan="off",
            access_log=False,
            log_level="error",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    process = None
    try:
        process = subprocess.Popen(
            [
                shutil.which("node"),
                "--require",
                str(root / "frontend/tests/qr-fixture-fetch.cjs"),
                str(root / "frontend/node_modules/next/dist/bin/next"),
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "3100",
            ],
            cwd=root / "tmp/task57h-web",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for _ in range(50):
            try:
                if (
                    httpx.get("http://127.0.0.1:3100/login", timeout=2).status_code
                    == 200
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated frontend did not start")
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                "tests/notification-operations.spec.ts",
                "--workers=1",
                "--output=../tmp/task57h-playwright",
            ],
            cwd=root / "frontend",
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Synthetic notification browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
