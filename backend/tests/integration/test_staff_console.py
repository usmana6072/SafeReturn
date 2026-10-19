"""Staff console: existing signed guards, isolated PostgreSQL, synthetic Auth only."""

import os
import shutil
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from test_auth_guards import change

pytest_plugins = ["test_auth_guards"]


@pytest.fixture(scope="module")
def console(guarded):
    pg, wf, _, _, _, _ = guarded
    with pg.connect() as c:
        for uid, role in [
            (wf["a"], "superadmin"),
            (wf["b"], "operations"),
            (wf["b"], "finance"),
        ]:
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role,reason) VALUES(:uid,:role,'synthetic-console')"
                ),
                {"uid": uid, "role": role},
            )
        c.commit()
    return guarded


def test_console_capabilities_are_live_and_explicit(console):
    pg, wf, _, sessions, headers, client = console
    cases = [
        (
            "operations",
            [
                "catalog.manage",
                "fulfillment.manage",
                "notifications.manage",
                "printing.manage",
            ],
        ),
        ("finance", ["payments.review"]),
        ("support", ["support.manage"]),
        ("security_admin", ["catalog.manage", "notifications.manage"]),
        ("a", ["catalog.manage"]),
        (
            "b",
            [
                "catalog.manage",
                "fulfillment.manage",
                "notifications.manage",
                "payments.review",
                "printing.manage",
            ],
        ),
    ]
    for identity, expected in cases:
        response = client.get(
            "/api/v1/me/staff-security", headers=headers(wf[identity])
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["capabilities"] == expected
        aal1 = client.get(
            "/api/v1/me/staff-security", headers=headers(wf[identity], aal="aal1")
        )
        assert aal1.json()["capabilities"] == []
        assert aal1.json()["mfa_verified"] is False
    uid = wf["finance"]
    with change(pg, "auth.sessions", sessions[uid], {"aal": "aal1"}):
        assert (
            client.get("/api/v1/me/staff-security", headers=headers(uid)).json()[
                "capabilities"
            ]
            == []
        )
    with change(
        pg,
        "auth.sessions",
        sessions[uid],
        {"not_after": datetime(2020, 1, 1, tzinfo=UTC)},
    ):
        assert (
            client.get("/api/v1/me/staff-security", headers=headers(uid)).status_code
            == 401
        )
    with pg.connect() as c:
        rid = c.execute(
            text(
                "SELECT id FROM public.staff_roles WHERE user_id=:uid AND role='finance' AND revoked_at IS NULL"
            ),
            {"uid": uid},
        ).scalar_one()
    with change(
        pg,
        "staff_roles",
        rid,
        {"revoked_at": datetime.now(UTC)},
    ):
        assert (
            client.get("/api/v1/me/staff-security", headers=headers(uid)).status_code
            == 403
        )
    assert client.get("/api/v1/me/staff-security").status_code == 401


def test_console_browser_flow(console):
    pg, wf, _, _sessions, headers, client = console
    app = client.application
    state = {"identity": "b", "aal": "aal1", "revoked": False}
    factor = {
        "id": "00000000-0000-4000-8000-000000000099",
        "factor_type": "totp",
        "status": "verified",
        "created_at": "2026-01-01T00:00:00Z",
    }

    def user():
        return {
            "id": str(wf[state["identity"]]),
            "aud": "authenticated",
            "role": "authenticated",
            "email": "staff@example.invalid",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
            "user_metadata": {},
            "app_metadata": {},
            "created_at": "2026-01-01T00:00:00Z",
            "factors": [factor],
        }

    def token():
        return {
            "access_token": headers(wf[state["identity"]], aal=state["aal"])[
                "Authorization"
            ].removeprefix("Bearer "),
            "refresh_token": "synthetic-console-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user(),
        }

    @app.get("/auth/v1/user")
    def fixture_user():
        return user()

    @app.post("/auth/v1/token")
    def fixture_token():
        return token()

    @app.post("/auth/v1/logout")
    def fixture_logout():
        return {}

    @app.post("/auth/v1/factors/{factor_id}/challenge")
    def challenge(factor_id: str):
        assert factor_id == factor["id"]
        return {"id": "synthetic-challenge", "expires_at": int(time.time()) + 60}

    @app.post("/auth/v1/factors/{factor_id}/verify")
    async def verify(factor_id: str, request: Request):
        if factor_id != factor["id"] or (await request.json()).get("code") != "123456":
            return JSONResponse(
                {"msg": "Invalid fixture code", "code": "mfa_verification_failed"},
                status_code=400,
            )
        state["aal"] = "aal2"
        return token()

    @app.post("/fixture/staff/{identity}")
    def select(identity: str):
        assert identity in (
            "b",
            "finance",
            "operations",
            "support",
            "security_admin",
            "a",
            "customer",
            "revoked",
        )
        if identity == "revoked":
            with pg.connect() as c:
                c.execute(
                    text(
                        "UPDATE public.staff_roles SET revoked_at=now() WHERE user_id=:uid AND revoked_at IS NULL"
                    ),
                    {"uid": wf[state["identity"]]},
                )
                c.commit()
        else:
            state.update(
                identity="support" if identity == "customer" else identity, aal="aal2"
            )
            if identity == "customer":
                with pg.connect() as c:
                    c.execute(
                        text(
                            "UPDATE public.staff_roles SET revoked_at=now() WHERE user_id=:uid AND revoked_at IS NULL"
                        ),
                        {"uid": wf["support"]},
                    )
                    c.commit()
        return {"ok": True}

    for port in (8115, 3100):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "Isolated browser port occupied"
            )
    root = Path(__file__).parents[3]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "QR_TEST_", "TASK"))
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
    process = None
    thread.start()
    try:
        process = subprocess.Popen(
            [
                shutil.which("node"),
                "--require",
                "./tests/qr-fixture-fetch.cjs",
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "3100",
            ],
            cwd=root / "frontend",
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
            raise AssertionError("Synthetic frontend did not start")
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                "tests/staff-console.spec.ts",
                "--workers=1",
                "--reporter=line",
            ],
            cwd=root / "frontend",
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Synthetic console browser checks failed"
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
