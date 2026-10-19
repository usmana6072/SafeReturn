"""Controlled local Next/API browser runtime; no provider calls or real users."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import text


def run(sample, *, test_files=None, extra_env=None):
    pg, client, _call, app = sample
    with pg.connect() as c:
        c.execute(
            text(
                "INSERT INTO public.product_images(product_id,cloudinary_public_id,alt_text,is_primary,verified_public_url) SELECT id,'safereturn/catalog/browser','Synthetic public kit',true,'https://res.cloudinary.com/synthetic/image/upload/v1/safereturn/catalog/browser.png' FROM public.products WHERE slug LIKE 'projection-%'"
            )
        )
        c.commit()
    from app.api.v1 import catalog

    original_verifier = catalog.verified_asset
    catalog.verified_asset = lambda settings, public_id: (
        f"https://res.cloudinary.com/synthetic/image/upload/v1/{public_id}.png"
    )
    original_database = app.state.database
    user = {
        "id": app.state.catalog_fixture_user,
        "aud": "authenticated",
        "role": "authenticated",
        "email": "catalog@example.invalid",
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
        return {
            "access_token": app.state.catalog_fixture_token(),
            "refresh_token": "synthetic-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user,
        }

    @app.post("/fixture/catalog/{state}")
    def fixture_state(state: str):
        if state == "unavailable":
            app.state.database = None
            return {"ok": True}
        app.state.database = original_database
        with pg.connect() as c:
            c.execute(
                text(
                    "UPDATE public.products SET is_featured=:featured WHERE slug LIKE 'projection-%'"
                ),
                {"featured": state == "on"},
            )
            c.commit()
        return {"ok": True}

    for port in (8115, 3100):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "Isolated browser port is occupied"
            )
    root = Path(__file__).parents[3]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SAFERETURN_", "QR_TEST_", "PUBLIC_QR_"))
    }
    env.update(extra_env or {})
    env.update(
        {
            "SAFERETURN_API_ORIGIN": "http://127.0.0.1:8115",
            "SAFERETURN_WEB_ORIGIN": "http://127.0.0.1:3100",
            "NEXT_TELEMETRY_DISABLED": "1",
            "SAFERETURN_SUPABASE_URL": "https://fixture.test",
            "SAFERETURN_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_fixture",
            "SAFERETURN_SESSION_SIGNING_KEY": "ab" * 32,
            "PLAYWRIGHT_EXTERNAL_SERVER": "1",
            "PLAYWRIGHT_CHANNEL": "msedge",
        }
    )
    server = uvicorn.Server(
        uvicorn.Config(
            client.application,
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
        for _ in range(20):
            try:
                if httpx.get("http://127.0.0.1:3100/", timeout=10).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated Next runtime did not start")
        result = subprocess.run(
            [
                shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                "test",
                "--",
                *(test_files or ["tests/catalog.spec.ts"]),
                "--workers=1",
            ],
            cwd=root / "frontend",
            env=env,
            timeout=480,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        print(result.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        if result.returncode:
            print(result.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        assert result.returncode == 0, "Public scan browser acceptance failed"
    finally:
        catalog.verified_asset = original_verifier
        if process is not None:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
