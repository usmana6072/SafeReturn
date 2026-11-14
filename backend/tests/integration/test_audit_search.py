"""Task 5.7M: installed-0021 synthetic namespace, no providers or object deletion."""

import base64
import json
import time
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pg_rehearsal import rehearsal
from pydantic import SecretStr
from sqlalchemy import text
from test_auth import ORIGIN, claims, keyset, signed
from test_health import ASGIClient
from test_workflow_schema import workflow_sample

from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

BASE = "/api/v1/admin/audit-events"


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
            ids["target"] = uuid4()
            ids["events"] = [uuid4() for _ in range(25)]
            for event in ids["events"]:
                c.execute(
                    text(
                        "INSERT INTO public.audit_events(id,actor_user_id,actor_kind,action,target_type,target_id,occurred_at,reason,request_id,safe_details) VALUES(:id,:uid,'staff','support_case.read','support_case',:target,now()-interval '1 hour','PRIVATE_REASON_CANARY','PRIVATE_REQUEST_CANARY',jsonb_build_object('reason_code','PRIVATE_DETAILS_CANARY'))"
                    ),
                    {"id": event, "uid": ids["support"], "target": ids["target"]},
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


def test_restricted_roles_filters_paging_redaction(cases, caplog):
    pg, _app, client, h, users, _sessions, _settings, ids = cases
    assert client.get(BASE).status_code == 401
    for role in ["a", "b", "support", "finance", "operations", "superadmin"]:
        assert client.get(BASE, headers=h(role)).status_code == 403
    for header in [
        h("security_admin", aal="aal1"),
        h("security_admin", age=301),
        h("security_admin", session=uuid4()),
    ]:
        assert client.get(BASE, headers=header).status_code in [401, 403]
    params = {
        "target_id": str(ids["target"]),
        "target_type": "support_case",
        "action": "support_case.read",
        "limit": 10,
    }
    found = []
    cursor = None
    for size in [10, 10, 5]:
        response = client.get(
            BASE,
            headers=h("security_admin"),
            params={**params, **({"cursor": cursor} if cursor else {})},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["items"]) == size
        found.extend(row["id"] for row in data["items"])
        cursor = data["next_cursor"]
        assert (
            "CANARY" not in response.text
            and "reason" not in response.text
            and "safe_details" not in response.text
        )
        assert response.headers["cache-control"] == "private, no-store"
    assert cursor is None and len(set(found)) == 25
    assert found == sorted(map(str, ids["events"]), reverse=True)
    assert (
        client.get(
            BASE,
            headers=h("security_admin"),
            params={"actor_id": str(users["a"]), "target_id": str(ids["target"])},
        ).json()["items"]
        == []
    )
    for params in [
        {"action": "' OR 1=1 --"},
        {"limit": 101},
        {"cursor": "broken"},
        {"target_type": "private_secret"},
        {"start": "2026-01-01", "end": "2026-10-01"},
        {"start": "2026-10-01T00:00:00", "end": "2026-10-02T00:00:00"},
        {"path": "/admin/support-cases"},
    ]:
        r = client.get(BASE, headers=h("security_admin"), params=params)
        assert r.status_code == 422, r.text
        assert "CANARY" not in r.text
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM public.audit_events WHERE action='audit.search' AND actor_user_id=:id"
                ),
                {"id": users["security_admin"]},
            ).scalar_one()
            >= 3
        )
    assert "PRIVATE_" not in caplog.text


def test_immutable_unknown_labels_and_query_budget(cases):
    from sqlalchemy.exc import DBAPIError

    from app.db.runtime import api_transaction

    pg, app, client, h, users, _sessions, _settings, ids = cases
    event = uuid4()
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO public.audit_events(id,actor_kind,action,target_type,target_id) VALUES(:id,'system','PRIVATE_ACTION_CANARY','PRIVATE_TYPE_CANARY',:target)"
            ),
            {"id": event, "target": ids["target"]},
        )
        c.commit()
    r = client.get(
        BASE, headers=h("security_admin"), params={"target_id": str(ids["target"])}
    )
    assert r.status_code == 200, r.text
    row = next(x for x in r.json()["items"] if x["id"] == str(event))
    assert (
        row["action"] == "restricted_event"
        and row["target_type"] == "restricted"
        and "CANARY" not in r.text
    )
    with pg.connect() as c:
        for sql in [
            "UPDATE public.audit_events SET reason=NULL WHERE id=:id",
            "DELETE FROM public.audit_events WHERE id=:id",
        ]:
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(text(sql), {"id": event})
        plan = c.execute(
            text(
                "EXPLAIN (FORMAT JSON) SELECT id FROM public.audit_events WHERE actor_user_id=:id AND occurred_at>now()-interval '7 days' ORDER BY occurred_at DESC,id DESC LIMIT 21"
            ),
            {"id": users["support"]},
        ).scalar_one()
        assert plan[0]["Plan"]["Node Type"] == "Limit"
    with api_transaction(
        app.state.database, users["operations"], mfa_verified=True
    ) as db:
        assert (
            db.execute(
                text("SELECT count(*) FROM public.audit_events WHERE id=:id"),
                {"id": event},
            ).scalar_one()
            == 0
        )


def test_audit_browser(cases):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    _pg, app, _client, headers, users, _sessions, _settings, ids = cases
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
        AUDIT_TARGET=str(ids["target"]),
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
            cwd=root / "tmp/task57m-web",
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
                "tests/audit-search.spec.ts",
                "--workers=1",
                "--output=../tmp/task57m-playwright-" + uuid4().hex,
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
        assert result.returncode == 0, "Synthetic audit browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
