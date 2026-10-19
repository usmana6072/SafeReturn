"""Real Next/browser → signed API → isolated PostgreSQL; fake Auth, no mail."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from test_activation import activation as _activation
from test_activation import inventory_context as _inventory_context
from test_profiles import profile as _profile

pytest_plugins = ["test_auth_guards"]
profile = _profile
activation = _activation
inventory_context = _inventory_context


def test_real_browser_owner_management_and_activation(profile, activation, guarded):
    _pg, _, ids, client, _, settings, uid = profile
    app = client.application
    current = app.state.settings
    settings.activation_verifier_key = current.activation_verifier_key
    settings.activation_verifier_key_version = current.activation_verifier_key_version
    app.state.settings = settings
    bearer = guarded[4](
        uid, amr=[{"method": "password", "timestamp": int(time.time())}]
    )["Authorization"].removeprefix("Bearer ")
    user = {
        "id": str(uid),
        "aud": "authenticated",
        "role": "authenticated",
        "email": "fixture@example.invalid",
        "email_confirmed_at": "2026-01-01T00:00:00Z",
        "user_metadata": {},
        "app_metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
    }

    @app.get("/auth/v1/user")
    def fixture_user():
        return user

    @app.post("/auth/v1/token")
    def fixture_token():
        current_bearer = guarded[4](
            uid, amr=[{"method": "password", "timestamp": int(time.time())}]
        )["Authorization"].removeprefix("Bearer ")
        return {
            "access_token": current_bearer,
            "refresh_token": "synthetic-fixture-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user,
        }

    @app.post("/auth/v1/logout")
    def fixture_logout():
        return {}

    @app.post("/fixture/keys/{state}")
    def fixture_keys(state: str):
        from pydantic import SecretStr

        app.state.settings.profile_data_keys = (
            original_key if state == "on" else SecretStr("{}")
        )
        return {"ok": True}

    original_key = settings.profile_data_keys
    for port in (8115, 3100):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "Test port already occupied"
            )
    root = Path(__file__).parents[3]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "QR_TEST_"))
    }
    env.update(
        {
            "SAFERETURN_SUPABASE_URL": "https://fixture.test",
            "SAFERETURN_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_fixture",
            "SAFERETURN_SESSION_SIGNING_KEY": "ab" * 32,
            "SAFERETURN_API_ORIGIN": "http://127.0.0.1:8115",
            "SAFERETURN_WEB_ORIGIN": "http://127.0.0.1:3100",
            "NEXT_TELEMETRY_DISABLED": "1",
            "PLAYWRIGHT_EXTERNAL_SERVER": "1",
            "PLAYWRIGHT_CHANNEL": "msedge",
        }
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
        for _ in range(100):
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
            raise AssertionError("Isolated Next test runtime did not start")
        test_env = {
            **env,
            "QR_TEST_BEARER": bearer,
            **{f"QR_TEST_{k.upper()}": str(v) for k, v in ids.items()},
            "QR_TEST_TOKEN": activation[5]["tags"][0]["public_token"],
            "QR_TEST_ACTIVATION_SECRET": activation[5]["activation_secret"],
            "QR_TEST_ACTIVATION_PAIR": str(activation[4]),
        }
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                "tests/qr-management.spec.ts",
                "tests/qr-contract.spec.ts",
                "tests/auth-sdk.spec.ts",
                "--workers=1",
            ],
            cwd=root / "frontend",
            env=test_env,
            timeout=600,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Isolated browser acceptance failed"
        # No fixture data is in installed public/auth schemas; rehearsal verifies
        # exact installed metadata/count preservation at teardown.
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
        app.state.settings.profile_data_keys = original_key
