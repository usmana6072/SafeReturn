"""Task 5.7I: real PostgreSQL, synthetic identities, canonical case guards."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient
from test_workflow_schema import workflow_sample

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.profile_crypto import encrypt
from app.db.session import Database
from app.main import create_app

BASE = "/api/v1/admin/support-cases"


@pytest.fixture(scope="module")
def cases():
    with rehearsal(expected_revision="0020_notification_operations") as pg:
        with pg.connect() as c:
            pg.upgrade(c, "0020_notification_operations")
            c.commit()
            pg.assert_catalog(c)
            c.rollback()
            pg.upgrade(c, "0021_support_case_console")
            c.rollback()
            assert c.execute(
                text("SELECT to_regclass('public.support_case_events') IS NULL")
            ).scalar_one()
            pg.assert_catalog(c)
            c.rollback()
            pg.upgrade(c, "0021_support_case_console")
            assert c.execute(
                text("""SELECT bool_and(has_function_privilege(r.role,p.oid,'EXECUTE')=(r.role='safereturn_api' AND p.proname<>'sr_support_finder_hold_lock'))
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            CROSS JOIN (VALUES('anon'),('authenticated'),('safereturn_api'),('safereturn_worker')) r(role)
            WHERE n.nspname=current_schema() AND p.proname LIKE 'sr_support_%'""")
            ).scalar_one()
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
            c.commit()
        settings = Settings(
            supabase_url=ORIGIN,
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

        def headers(role="support", aal="aal2", key=None):
            return {
                "Authorization": "Bearer "
                + signed(
                    private,
                    claims(
                        sub=str(users[role]), session_id=str(sessions[role]), aal=aal
                    ),
                ),
                "Idempotency-Key": key or str(uuid4()),
            }

        yield pg, app, client, headers, users, sessions, settings, ids
        verifier.close()


def create(cases, role="support", key=None, **body):
    r = cases[2].post(
        BASE,
        headers=cases[3](role, key=key),
        json={
            "case_type": "other",
            "description": "PRIVATE synthetic support context",
            **body,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def change(cases, cid, rev, role="support", **body):
    return cases[2].request(
        "PATCH",
        BASE + "/" + str(cid),
        headers=cases[3](role),
        json={"action": "update", "expected_revision": rev, "confirmed": True, **body},
    )


def test_roles_scope_and_safe_projections(cases, caplog):
    pg, _app, client, headers, _users, sessions, _settings, _ = cases
    cid = create(cases)["id"]
    assert client.get(BASE).status_code == 401
    for role in ["a", "finance", "operations", "security_admin", "superadmin"]:
        assert client.get(BASE, headers=headers(role)).status_code == 403
        assert (
            client.post(
                BASE,
                headers=headers(role),
                json={"case_type": "other", "description": "test"},
            ).status_code
            == 403
        )
        assert change(cases, cid, 1, role=role, note="test").status_code == 403
    assert client.get(BASE, headers=headers(aal="aal1")).status_code == 403
    assert (
        client.get(BASE, headers=headers("b"), params={"case_id": cid}).status_code
        == 404
    )
    assert change(cases, cid, 1, role="b", note="test").status_code == 404
    queue = client.get(BASE, headers=headers()).json()
    assert "PRIVATE" not in json.dumps(queue)
    assert "description" not in queue["items"][0]
    own = client.get(BASE, headers=headers(), params={"case_id": cid})
    assert own.status_code == 200, own.text
    assert own.json()["items"][0]["description"].startswith("PRIVATE")
    assert "ciphertext" not in own.text
    invalid = client.post(
        BASE,
        headers=headers(),
        json={"case_type": "other", "description": "PRIVATE" * 300},
    )
    assert invalid.status_code == 422 and "PRIVATE" not in invalid.text
    assert "PRIVATE" not in caplog.text
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE target_id=:id AND action='support_case.read'"
                ),
                {"id": cid},
            ).scalar_one()
            == 1
        )
        c.execute(
            text("UPDATE auth.sessions SET aal='aal1' WHERE id=:id"),
            {"id": sessions["support"]},
        )
        c.commit()
    try:
        assert client.get(BASE, headers=headers()).status_code == 403
    finally:
        with pg.connect() as c:
            c.execute(
                text("UPDATE auth.sessions SET aal='aal2' WHERE id=:id"),
                {"id": sessions["support"]},
            )
            c.commit()


def test_legacy_claim_concurrency_and_private_reason(cases):
    pg, _, client, headers, users, _, settings, _ = cases
    cid = uuid4()
    cipher, version = encrypt(
        settings, users["a"], "account_deletion_reason", "RESTRICTED legacy reason"
    )
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO public.support_cases(id,case_type,opened_by_user_id,description_ciphertext,description_key_version) VALUES(:id,'privacy',:uid,:cipher,:v)"
            ),
            {"id": cid, "uid": users["a"], "cipher": cipher, "v": version},
        )
        c.execute(
            text(
                "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details) VALUES(:uid,'customer','account.deletion.requested','support_case',:id,'{}')"
            ),
            {"id": cid, "uid": users["a"]},
        )
        c.commit()
    r = client.get(BASE, headers=headers(), params={"case_id": str(cid)})
    assert r.status_code == 200 and r.json()["items"][0]["can_claim"]
    assert "description" not in r.json()["items"][0]
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda role: change(cases, cid, 1, role=role, action="claim"),
                ["support", "b"],
            )
        )
    assert sorted(r.status_code for r in results) == [200, 404]
    winner = "support" if results[0].status_code == 200 else "b"
    detail = client.get(
        BASE, headers=headers(winner), params={"case_id": str(cid)}
    ).json()["items"][0]
    assert (
        detail["description"] is None
        and detail["legacy_description_restricted"]
        and detail["account_deletion_request"]
    )
    assert "RESTRICTED" not in json.dumps(detail)
    assert change(cases, cid, 2, role=winner, status="investigating").status_code == 200
    assert change(cases, cid, 3, role=winner, status="resolved").status_code == 409


def test_idempotency_encryption_stale_and_terminal_history(cases):
    pg, _, client, headers, *_ = cases
    key = str(uuid4())
    with ThreadPoolExecutor(2) as pool:
        receipts = list(pool.map(lambda _: create(cases, key=key), range(2)))
    assert receipts[0] == receipts[1]
    cid = receipts[0]["id"]
    assert (
        client.post(
            BASE,
            headers=headers(key=key),
            json={"case_type": "other", "description": "different context"},
        ).status_code
        == 409
    )
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda note: change(cases, cid, 1, note=note),
                ["PRIVATE note one", "PRIVATE note two"],
            )
        )
    assert sorted(r.status_code for r in results) == [200, 412]
    detail = client.get(
        BASE, headers=headers(), params={"case_id": cid, "event_limit": 1}
    ).json()["items"][0]
    assert detail["history"]["items"][0]["note"].startswith("PRIVATE")
    assert detail["history"]["next_before_revision"] == 2
    with pg.connect() as c:
        stored = c.execute(
            text(
                "SELECT note_ciphertext FROM public.support_case_events WHERE case_id=:id AND note_ciphertext IS NOT NULL"
            ),
            {"id": cid},
        ).scalar_one()
        assert b"PRIVATE" not in bytes(stored)
        before = {
            table: c.execute(
                text(
                    f"SELECT md5(coalesce(string_agg(t::text,'' ORDER BY id),'')) FROM public.{table} t"
                )
            ).scalar_one()
            for table in [
                "orders",
                "tag_pairs",
                "qr_codes",
                "payment_attempts",
                "notification_outbox",
                "retention_holds",
            ]
        }
    for rev, status in [(2, "investigating"), (3, "resolved"), (4, "closed")]:
        r = change(cases, cid, rev, status=status)
        assert r.status_code == 200, r.text
    assert change(cases, cid, 5, note="terminal edit").status_code == 409
    assert change(cases, cid, 4, note="stale edit").status_code == 412
    with pg.connect() as c:
        after = {
            table: c.execute(
                text(
                    f"SELECT md5(coalesce(string_agg(t::text,'' ORDER BY id),'')) FROM public.{table} t"
                )
            ).scalar_one()
            for table in before
        }
        assert before == after
        with pytest.raises(DBAPIError):
            c.execute(
                text("DELETE FROM public.support_case_events WHERE case_id=:id"),
                {"id": cid},
            )
        c.rollback()


@pytest.mark.parametrize("kind", ["payment", "privacy", "ownership_dispute"])
def test_high_risk_resolution_requires_separate_authorization(cases, kind):
    cid = create(cases, case_type=kind)["id"]
    assert (
        change(
            cases, cid, 1, status="investigating", note="Investigation context"
        ).status_code
        == 200
    )
    assert change(cases, cid, 2, status="resolved").status_code == 409


def test_hold_committing_before_transition_and_retention_admission(cases):
    from test_commerce_schema import pay, place, sample

    pg, _, client, headers, users, *_ = cases
    with pg.connect() as c:
        commerce = sample.__wrapped__(c)
        c.commit()
    oid = commerce["purchase"]
    cid = create(cases, order_id=str(oid))["id"]
    assert change(cases, cid, 1, status="investigating").status_code == 200
    # The hold writer and case writer serialize on the same order before case locks.
    with pg.connect() as c, ThreadPoolExecutor(1) as pool:
        c.execute(
            text("SELECT 1 FROM public.orders WHERE id=:id FOR UPDATE"), {"id": oid}
        )
        c.execute(
            text(
                "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('order',:id,'SYNTHETIC_HOLD',:uid)"
            ),
            {"id": oid, "uid": users["security_admin"]},
        )
        future = pool.submit(change, cases, cid, 2, status="resolved")
        c.commit()
        r = future.result(timeout=30)
        assert r.status_code == 409, r.text
    detail = client.get(BASE, headers=headers(), params={"case_id": cid}).json()[
        "items"
    ][0]
    assert detail["has_active_hold"] is True
    assert "SYNTHETIC_HOLD" not in json.dumps(detail)
    assert "retention_holds" not in json.dumps(detail)
    wf = cases[7]
    finder_case = create(cases, pair_id=str(wf["pa"]))["id"]
    assert change(cases, finder_case, 1, status="investigating").status_code == 200
    with pg.connect() as c, ThreadPoolExecutor(1) as pool:
        c.execute(
            text("SELECT 1 FROM public.tag_pairs WHERE id=:id FOR UPDATE"),
            {"id": wf["pa"]},
        )
        c.execute(
            text(
                "INSERT INTO public.retention_holds(resource_type,resource_id,reason_code,placed_by) VALUES('finder_message',:id,'SYNTHETIC_FINDER_HOLD',:uid)"
            ),
            {"id": wf["ma"], "uid": users["security_admin"]},
        )
        future = pool.submit(change, cases, finder_case, 2, status="resolved")
        c.commit()
        assert future.result(timeout=30).status_code == 409
    with pg.connect() as c:
        second = sample.__wrapped__(c)
        place(c, second)
        pay(c, second)
        job = c.execute(
            text(
                "INSERT INTO public.print_jobs(order_id,job_revision,template_fingerprint,render_config) VALUES(:id,1,'synthetic','{}') RETURNING id"
            ),
            {"id": second["purchase"]},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO public.print_artifacts(print_job_id,object_key,format,sha256_hex,size_bytes,deletion_hold_reason) VALUES(:id,:key,'pdf',:sha,1,'retention.deleting')"
            ),
            {
                "id": job,
                "key": "synthetic-no-stored-object/" + str(uuid4()),
                "sha": "a" * 64,
            },
        )
        c.commit()
    r = client.post(
        BASE,
        headers=headers(),
        json={
            "case_type": "other",
            "order_id": str(second["purchase"]),
            "description": "Synthetic retention conflict",
        },
    )
    assert r.status_code == 409, r.text
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.support_cases WHERE order_id=:id"),
                {"id": second["purchase"]},
            ).scalar_one()
            == 0
        )


def test_support_browser(cases):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    _pg, app, _client, headers, users, _sessions, *_ = cases
    root = Path(__file__).parents[3]
    state = {"role": "support"}
    target = create(cases)["id"]
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

    @app.post("/fixture/support-stale")
    def fixture_stale():
        response = change(cases, target, 1, note="Concurrent synthetic note")
        assert response.status_code == 200, response.text
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
        SUPPORT_CASE=str(target),
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
            cwd=root / "tmp/task57i-web",
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
                "tests/support-cases.spec.ts",
                "--workers=1",
                "--output=../tmp/task57i-playwright-" + uuid4().hex,
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
        assert result.returncode == 0, "Synthetic support browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
