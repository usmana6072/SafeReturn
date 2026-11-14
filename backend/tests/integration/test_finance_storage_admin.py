"""Task 5.7L: installed-0021 synthetic namespace, no providers or object deletion."""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_commerce_schema import sample as commerce_sample
from test_health import ASGIClient
from test_workflow_schema import workflow_sample

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

BASE = "/api/v1/admin/finance/sheet-sync"


@pytest.fixture(scope="module")
def cases():
    with rehearsal(expected_revision="0021_support_case_console") as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0021_support_case_console")
            c.commit()
            pg.assert_catalog(c)
            c.rollback()
            ids = workflow_sample.__wrapped__(c)
            ids["superadmin"] = uuid4()
            c.execute(
                text("INSERT INTO auth.users(id) VALUES(:id)"),
                {"id": ids["superadmin"]},
            )
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,'superadmin'),(:other,'support')"
                ),
                {"id": ids["superadmin"], "other": ids["b"]},
            )
            users = {
                k: ids[k]
                for k in [
                    "a",
                    "b",
                    "support",
                    "operations",
                    "finance",
                    "security_admin",
                    "superadmin",
                ]
            }
            sessions = {k: uuid4() for k in users}
            for role, uid in users.items():
                c.execute(
                    text(
                        "UPDATE auth.users SET email=:email,email_confirmed_at=now() WHERE id=:id"
                    ),
                    {"id": uid, "email": role + "@synthetic.invalid"},
                )
                c.execute(
                    text(
                        "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:sid,:id,'aal2',now()+interval '1 hour')"
                    ),
                    {"id": uid, "sid": sessions[role]},
                )
            commerce = commerce_sample.__wrapped__(c)
            ids["order"] = commerce["purchase"]
            ids["attempt"] = commerce["attempt"]
            ids["sync"] = uuid4()
            ids["artifact"] = uuid4()
            ids["cleanup"] = uuid4()
            ids["print_job"] = uuid4()
            c.execute(
                text(
                    "INSERT INTO public.finance_sheet_sync(id,order_id,status,last_error_code) VALUES(:sync,:order,'failed','SYNTHETIC_OUTAGE')"
                ),
                ids,
            )
            c.execute(
                text(
                    "INSERT INTO public.payment_evidence(id,attempt_id,object_key,sha256_hex,content_type,bytes_size,retention_until) VALUES(:artifact,:attempt,'PRIVATE_LOCATOR_CANARY',:sha,'application/pdf',128,NULL)"
                ),
                {**ids, "sha": "b" * 64},
            )
            c.execute(
                text(
                    "INSERT INTO public.durable_jobs(id,job_kind,aggregate_type,aggregate_id,order_id,status,attempt_count,idempotency_key) VALUES(:cleanup,'retention.cleanup','payment_evidence',:artifact,:order,'dead',3,:key)"
                ),
                {**ids, "key": "synthetic-cleanup:" + str(ids["artifact"])},
            )
            c.commit()
        settings = Settings(
            supabase_url=ORIGIN,
            privacy_export_web_origin="http://127.0.0.1:3100",
            profile_data_keys=SecretStr(
                json.dumps({"1": base64.urlsafe_b64encode(b"S" * 32).decode()})
            ),
        )
        private = ec.generate_private_key(ec.SECP256R1())
        verifier = JWTVerifier(
            settings,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"keys": [keyset(private)]})
            ),
        )
        app = create_app(settings, verifier=verifier)
        app.state.database = Database(pg.engine)
        app.state.jwt_verifier = verifier
        client = ASGIClient(app)

        def headers(role="a", aal="aal2", key=None, age=0, session=None):
            return {
                "Authorization": "Bearer "
                + signed(
                    private,
                    claims(
                        sub=str(users[role]),
                        session_id=str(session or sessions[role]),
                        aal=aal,
                        amr=[
                            {"method": "password", "timestamp": int(time.time()) - age}
                        ],
                    ),
                ),
                "Idempotency-Key": key or str(uuid4()),
                "Origin": "http://127.0.0.1:3100",
            }

        yield pg, app, client, headers, users, sessions, settings, ids
        verifier.close()


def test_roles_sessions_and_bounded_metadata(cases):
    _, _app, client, h, _, _sessions, _, ids = cases
    storage = "/api/v1/admin/storage/artifacts"
    assert client.get(BASE).status_code == 401
    for role in ["a", "b", "support", "operations"]:
        assert client.get(BASE, headers=h(role)).status_code == 403
    for role in ["a", "b", "support"]:
        assert client.get(storage, headers=h(role)).status_code == 403
    for role in ["finance", "security_admin", "superadmin"]:
        response = client.get(BASE, headers=h(role))
        assert response.status_code == 200, response.text
        row = next(x for x in response.json()["items"] if x["id"] == str(ids["sync"]))
        assert row["status"] == "failed" and row["total_pkr"] == "0.76"
    for role in ["operations", "finance", "security_admin", "superadmin"]:
        response = client.get(
            storage,
            headers=h(role),
            params={"order_id": str(ids["order"]), "resource_type": "payment_evidence"},
        )
        assert response.status_code == 200, response.text
        if role == "operations":
            assert response.json()["items"] == []
        else:
            assert len(response.json()["items"]) == 1
            assert response.json()["items"][0]["cleanup_job"]["status"] == "dead"
        assert client.get(storage, headers=h(role, aal="aal1")).status_code == 403
    assert (
        client.get(
            storage, headers=h("operations"), params={"order_id": str(uuid4())}
        ).json()["items"]
        == []
    )
    assert (
        client.get(BASE, headers=h("finance"), params={"limit": 101}).status_code == 422
    )
    assert client.get(BASE, headers=h("finance", session=uuid4())).status_code == 401
    state = client.get("/api/v1/me/staff-security", headers=h("operations")).json()
    assert (
        "storage.metadata" in state["capabilities"]
        and "storage.holds" not in state["capabilities"]
        and "finance.mirror" not in state["capabilities"]
    )
    assert client.get(BASE, headers=h("finance", aal="aal1")).status_code == 403


def test_retry_hold_recovery_and_stale_worker_guards(cases):
    from sqlalchemy.exc import DBAPIError

    from app.db.runtime import worker_transaction

    pg, app, client, h, _users, _, _, ids = cases
    path = f"/api/v1/admin/storage/artifacts/{ids['artifact']}"
    for role in ["operations", "finance", "support"]:
        assert (
            client.post(
                path + "/retention-holds",
                headers=h(role),
                json={"reason_code": "SYNTHETIC"},
            ).status_code
            == 403
        )
        assert (
            client.request(
                "DELETE", path + "/retention-holds", headers=h(role)
            ).status_code
            == 403
        )
        assert (
            client.post(
                path + "/cleanup-retry",
                headers=h(role),
                json={"reason_code": "SYNTHETIC"},
            ).status_code
            == 403
        )
    assert (
        client.post(
            path + "/retention-holds",
            headers=h("security_admin", aal="aal1"),
            json={"reason_code": "SYNTHETIC"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            path + "/retention-holds",
            headers=h("security_admin"),
            json={"reason_code": "SYNTHETIC", "policy_approved": True},
        ).status_code
        == 422
    )
    first = client.post(
        path + "/retention-holds",
        headers=h("security_admin"),
        json={"reason_code": "SYNTHETIC"},
    )
    assert first.status_code == 201, first.text
    assert (
        client.post(
            path + "/retention-holds",
            headers=h("security_admin"),
            json={"reason_code": "SYNTHETIC"},
        ).json()
        == first.json()
    )
    assert (
        client.post(
            path + "/retention-holds",
            headers=h("superadmin"),
            json={"reason_code": "SECOND_SYNTHETIC"},
        ).status_code
        == 201
    )
    assert (
        client.request(
            "DELETE", path + "/retention-holds", headers=h("security_admin")
        ).status_code
        == 204
    )
    assert (
        client.request(
            "DELETE", path + "/retention-holds", headers=h("security_admin")
        ).status_code
        == 404
    )
    retry = BASE + f"/{ids['sync']}/retry"
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(lambda _: client.post(retry, headers=h("finance")), range(2))
        )
    assert all(r.status_code == 202 for r in replies)
    for _ in range(2):
        assert (
            client.post(
                path + "/cleanup-retry",
                headers=h("security_admin"),
                json={"reason_code": "SYNTHETIC_RECOVERY"},
            ).status_code
            == 202
        )
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.durable_jobs WHERE order_id=:order AND job_kind='finance.sync' AND status IN ('pending','retry','leased')"
                ),
                ids,
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='storage.cleanup_retry' AND target_id=:artifact"
                ),
                ids,
            ).scalar_one()
            == 1
        )
        assert c.execute(
            text(
                "SELECT payment_status,fulfillment_status FROM public.orders WHERE id=:order"
            ),
            ids,
        ).one() == ("awaiting_transfer", "unallocated")
        c.execute(
            text("UPDATE public.finance_sheet_sync SET status='synced' WHERE id=:sync"),
            ids,
        )
        c.execute(
            text(
                "UPDATE public.durable_jobs SET status='leased',attempt_count=1,lease_owner='synthetic-lease',lease_until=now()+interval '5 minutes' WHERE id=:cleanup"
            ),
            ids,
        )
        c.commit()
    assert client.post(retry, headers=h("finance")).status_code == 409
    # The unapproved-policy path cannot authorize deletion, even with a live lease.
    with worker_transaction(app.state.database, "synthetic-lease") as db:
        assert db.execute(
            text("SELECT public.sr_retention_prepare(:cleanup,1,NULL)"), ids
        ).scalar_one() == {"deleted": False, "reason": "policy_not_approved"}
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.durable_jobs SET lease_until=now()-interval '1 second' WHERE id=:cleanup"
            ),
            ids,
        )
        c.commit()
    with (
        pytest.raises(DBAPIError),
        worker_transaction(app.state.database, "synthetic-lease") as db,
    ):
        db.execute(
            text("SELECT public.sr_retention_prepare(:cleanup,1,'synthetic-policy')"),
            ids,
        )
    # Simulate pre-existing committed intent metadata only; never contact/delete objects.
    with pg.connect() as c:
        c.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason='retention.deleting' WHERE id=:artifact"
            ),
            ids,
        )
        c.execute(
            text(
                "INSERT INTO public.audit_events(actor_kind,action,target_type,target_id) VALUES('system','storage.deletion_authorized','payment_evidence',:artifact)"
            ),
            ids,
        )
        c.commit()
    assert (
        client.post(
            path + "/retention-holds",
            headers=h("security_admin"),
            json={"reason_code": "LATE_SYNTHETIC"},
        ).status_code
        == 409
    )
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT deleted_at IS NULL FROM public.payment_evidence WHERE id=:artifact"
            ),
            ids,
        ).scalar_one()
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.retention_holds WHERE resource_id=:artifact AND released_at IS NULL"
                ),
                ids,
            ).scalar_one()
            == 0
        )
        c.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason=NULL WHERE id=:artifact"
            ),
            ids,
        )
        c.execute(
            text(
                "UPDATE public.durable_jobs SET status='dead',lease_owner=NULL,lease_until=NULL WHERE id=:cleanup"
            ),
            ids,
        )
        c.execute(
            text("UPDATE public.finance_sheet_sync SET status='failed' WHERE id=:sync"),
            ids,
        )
        c.commit()


def test_finance_storage_browser(cases):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    pg, app, _client, headers, users, _sessions, _settings, ids = cases
    root = Path(__file__).parents[3]
    state = {"role": "a"}
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

    @app.post("/fixture/support-role/{role}")
    def fixture_role(role: str):
        assert role in users
        state["role"] = role
        return {"ok": True}

    @app.post("/fixture/reset-finance-storage")
    def reset_fixture():
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.finance_sheet_sync SET status='failed' WHERE id=:sync"
                ),
                ids,
            )
            c.execute(
                text(
                    "UPDATE public.durable_jobs SET status='dead',lease_owner=NULL,lease_until=NULL WHERE id=:cleanup"
                ),
                ids,
            )
            c.commit()
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
        FINANCE_SYNC=str(ids["sync"]),
        STORAGE_ARTIFACT=str(ids["artifact"]),
        NEXT_TELEMETRY_DISABLED="1",
        PLAYWRIGHT_EXTERNAL_SERVER="1",
        PLAYWRIGHT_CHANNEL="msedge",
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
            cwd=root / "tmp/task57l-web",
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
                "tests/finance-storage-admin.spec.ts",
                "--workers=1",
                "--output=../tmp/task57l-playwright-" + uuid4().hex,
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
        assert result.returncode == 0, "Synthetic finance/storage browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
