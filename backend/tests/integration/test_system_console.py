"""5.7N: approved health boundaries and bounded synthetic browser only."""

from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from test_audit_search import cases as _audit_cases
from test_health import ASGIClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(scope="module")
def cases():
    yield from _audit_cases.__wrapped__()


def test_existing_health_contract_is_not_staff_readiness():
    app = create_app(Settings(readiness_token=SecretStr("SYNTHETIC_INTERNAL_TOKEN")))
    client = ASGIClient(app)
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    assert client.get("/api/v1/health/ready").status_code == 401
    denied = client.get(
        "/api/v1/health/ready", headers={"Authorization": "Bearer synthetic-staff-jwt"}
    )
    assert denied.status_code == 401 and "SYNTHETIC_INTERNAL_TOKEN" not in denied.text
    unavailable = client.get(
        "/api/v1/health/ready",
        headers={"Authorization": "Bearer SYNTHETIC_INTERNAL_TOKEN"},
    )
    assert unavailable.status_code == 503 and unavailable.json() == {
        "status": "not_ready",
        "database": "unavailable",
    }
    assert (
        ASGIClient(create_app(Settings())).get("/api/v1/health/ready").status_code
        == 404
    )
    paths = app.openapi()["paths"]
    assert not any(
        p in paths
        for p in [
            "/api/v1/admin/system",
            "/api/v1/admin/health",
            "/api/v1/admin/workers",
        ]
    )


def test_existing_role_session_aal_boundary(cases):
    client, h = cases[2:4]
    for role in ["operations", "security_admin", "finance", "support", "superadmin"]:
        response = client.get("/api/v1/me/staff-security", headers=h(role))
        assert response.status_code == 200
        assert ("notifications.manage" in response.json()["capabilities"]) == (
            role in ["operations", "security_admin"]
        )
        assert (
            client.get("/api/v1/me/staff-security", headers=h(role, aal="aal1")).json()[
                "capabilities"
            ]
            == []
        )
    assert client.get("/api/v1/me/staff-security").status_code == 401
    assert (
        client.get(
            "/api/v1/me/staff-security",
            headers=h("operations", session=uuid4()),
        ).status_code
        == 401
    )
    assert client.get("/api/v1/me/staff-security", headers=h("a")).status_code == 403


def test_system_browser(cases):
    import os
    import shutil
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    _pg, app, _client, headers, users, _sessions, _settings, _ids = cases
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
        NEXT_TELEMETRY_DISABLED="1",
        PLAYWRIGHT_EXTERNAL_SERVER="1",
        PLAYWRIGHT_CHANNEL="msedge",
    )
    import asyncio

    from starlette.responses import JSONResponse

    health = {"mode": "normal", "ready_calls": 0}

    @app.post("/fixture/system-mode/{mode}")
    def mode_fixture(mode: str):
        assert mode in ["normal", "down", "malformed", "slow"]
        health["mode"] = mode
        return {"ok": True}

    @app.get("/fixture/system-stats")
    def stats_fixture():
        return {"ready_calls": health["ready_calls"]}

    async def synthetic_app(scope, receive, send):
        if scope.get("path") == "/api/v1/health/ready":
            health["ready_calls"] += 1
        if scope.get("path") == "/api/v1/health/live":
            mode = health["mode"]
            if mode == "slow":
                await asyncio.sleep(6)
            elif mode != "normal":
                response = JSONResponse(
                    {"status": "ok", "PRIVATE_CANARY": "https://secret.invalid/key"},
                    status_code=503 if mode == "down" else 200,
                )
                return await response(scope, receive, send)
        return await app(scope, receive, send)

    server = uvicorn.Server(
        uvicorn.Config(
            synthetic_app,
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
            cwd=root / "tmp/task57n-web",
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
                "tests/system-health.spec.ts",
                "tests/system-observation.spec.ts",
                "--workers=1",
                "--output=../tmp/task57n-playwright-" + uuid4().hex,
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
        assert result.returncode == 0, "Synthetic system browser failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
