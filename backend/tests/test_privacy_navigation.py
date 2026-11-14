"""5.7O in-memory contract checks; no PostgreSQL/provider acceptance claim."""

import os
import shutil
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
import uvicorn
from fastapi import Depends, Response
from test_health import ASGIClient

from app.api.auth import authorize, get_auth_context, get_principal
from app.core.auth import AuthRequired, Principal
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def memory():
    users = {name: uuid4() for name in ("a", "b")}
    state = {"user": "a", "expired": False, "history": "full", "status": "requested"}
    rid = uuid4()
    tokens = {}
    for name, uid in users.items():
        tokens[name] = jwt.encode(
            {"sub": str(uid), "exp": int(time.time()) + 3600, "aud": "authenticated"},
            "synthetic-key-only-0000000000000000",
            algorithm="HS256",
        )

    class Verifier:
        def verify(self, token):
            if state["expired"] or token not in tokens.values():
                raise AuthRequired()
            name = next(k for k, value in tokens.items() if value == token)
            return Principal(users[name], users[name], False, int(time.time()))

    class Result:
        def __init__(self, value):
            self.value = value

        def mappings(self):
            return self

        def all(self):
            return self.value

        def scalar_one(self):
            return self.value

        def one_or_none(self):
            return self.value

    class Session:
        def __init__(self, principal):
            self.principal = principal

        def execute(self, statement, params):
            sql = str(statement)
            if "sr_account_session_state" in sql:
                return Result(SimpleNamespace(email_verified=True, mfa_active=False))
            if "set_config" in sql:
                return Result(None)
            if "FROM public.audit_events" in sql:
                # Synthetic repository models only the approved actor-scoped query.
                assert (
                    "actor_user_id=:uid" in sql
                    and "ORDER BY occurred_at DESC,id DESC LIMIT 101" in sql
                )
                assert params["uid"] == self.principal.user_id
                if state["history"] == "down":
                    raise RuntimeError("synthetic unavailable")
                count = (
                    105
                    if state["history"] == "full" and params["uid"] == users["a"]
                    else 0
                )
                return Result(
                    [
                        {
                            "id": UUID(int=n + 1),
                            "target_id": UUID(int=999),
                            "action": "profile.whatsapp.updated",
                            "consent_version": "wa-public-v1",
                            "active_state": "enabled",
                            "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
                            "private": "PRIVATE_CANARY_NOTE_CONTACT_MEDICAL",
                        }
                        for n in reversed(range(count))
                    ][:101]
                )
            if "sr_export_read" in sql:
                # Synthetic stand-in for unapplied 0022 owner-safe read, not SQL/RLS proof.
                return Result(
                    {
                        "request_id": str(rid),
                        "case_id": str(UUID(int=888)),
                        "status": state["status"],
                        "revision": 1,
                        "scope_version": "basic_v1",
                    }
                    if params["id"] == rid and self.principal.user_id == users["a"]
                    else None
                )
            raise AssertionError("Unexpected synthetic query")

    app = create_app(Settings())
    app.state.jwt_verifier = Verifier()

    def context(
        response: Response, principal: Annotated[Principal, Depends(get_principal)]
    ):
        response.headers["Cache-Control"] = "no-store"
        return authorize(Session(principal), principal)

    app.dependency_overrides[get_auth_context] = context
    client = ASGIClient(app)
    headers = lambda name: {"Authorization": "Bearer " + tokens[name]}
    return app, client, state, users, tokens, headers, rid


def test_history_contract_cap_projection_and_actor_boundary(memory):
    _, client, state, _, _, headers, _ = memory
    response = client.get("/api/v1/me/privacy-consents", headers=headers("a"))
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    data = response.json()
    assert len(data["items"]) == 100 and data["has_more"] is True
    assert [row["id"] for row in data["items"]] == [
        str(UUID(int=n)) for n in range(105, 5, -1)
    ]
    assert all(row["state_scope"] == "recorded_event" for row in data["items"])
    assert "PRIVATE_CANARY" not in response.text and "private" not in response.text
    assert client.get("/api/v1/me/privacy-consents", headers=headers("b")).json() == {
        "items": [],
        "has_more": False,
    }
    # No approved cursor exists: do not claim traversal/stale-cursor acceptance.
    assert "next_cursor" not in data
    state["history"] = "empty"
    assert (
        client.get("/api/v1/me/privacy-consents", headers=headers("a")).json()["items"]
        == []
    )


def test_existing_status_owner_and_session_denial(memory):
    _, client, state, _, _, headers, rid = memory
    path = "/api/v1/me/privacy/exports/" + str(rid)
    for status in ("requested", "reviewing", "ready", "rejected", "expired"):
        state["status"] = status
        response = client.get(path, headers=headers("a"))
        assert response.status_code == 200 and response.json()["status"] == status
        assert response.headers["cache-control"] == "private, no-store"
        assert "PRIVATE_CANARY" not in response.text
    assert client.get(path, headers=headers("b")).status_code == 404
    for target in (path, "/api/v1/me/privacy-consents"):
        assert client.get(target).status_code == 401
        state["expired"] = True
        assert client.get(target, headers=headers("a")).status_code == 401
        state["expired"] = False
    assert (
        client.get(
            "/api/v1/me/privacy/erasures/" + str(rid), headers=headers("a")
        ).status_code
        == 404
    )


def test_privacy_navigation_browser(memory):
    app, _, state, users, tokens, _, rid = memory
    root = Path(__file__).parents[2]

    def user():
        return {
            "id": str(users[state["user"]]),
            "aud": "authenticated",
            "role": "authenticated",
            "email": state["user"] + "@synthetic.invalid",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
            "user_metadata": {},
            "app_metadata": {},
            "created_at": "2026-01-01T00:00:00Z",
        }

    @app.get("/auth/v1/user")
    def fixture_user():
        if state["expired"]:
            return Response(status_code=401)
        return user()

    @app.post("/auth/v1/token")
    def fixture_token():
        return {
            "access_token": tokens[state["user"]],
            "refresh_token": "synthetic-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user(),
        }

    @app.post("/fixture/privacy/{kind}/{value}")
    def fixture_state(kind: str, value: str):
        assert kind in ("user", "expired", "history", "status")
        state[kind] = value == "true" if kind == "expired" else value
        return {"request_id": str(rid)}

    for port in (3100, 8115):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "Isolated test port occupied"
            )
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
        with (root / "output/task57o/frontend-browser.log").open(
            "w", encoding="utf-8"
        ) as log:
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
                cwd=root / "tmp/task57o-web",
                env=env,
                stdout=log,
                stderr=log,
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
                raise AssertionError("Isolated frontend unavailable")
            result = subprocess.run(
                [
                    shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                    "test",
                    "--",
                    "tests/privacy-navigation.spec.ts",
                    "--workers=1",
                    "--output=../tmp/task57o-playwright-" + uuid4().hex,
                ],
                cwd=root / "frontend",
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
            if result.returncode:
                print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
            assert result.returncode == 0
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
