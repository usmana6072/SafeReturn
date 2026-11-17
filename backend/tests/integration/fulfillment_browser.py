"""Run the real Next.js portal against the disposable fulfillment database."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import Request


def run(app, scope_tokens, order_id, job_id):
    root = Path(__file__).resolve().parents[3]
    frontend = root / "frontend"
    users = {
        email: {
            "id": str(uid), "aud": "authenticated", "role": "authenticated", "email": email,
            "email_confirmed_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z",
            "user_metadata": {}, "app_metadata": {},
        }
        for email, (uid, _) in scope_tokens.items()
    }
    by_token = {token: users[email] for email, (_, token) in scope_tokens.items()}

    @app.get("/auth/v1/user")
    def fixture_user(request: Request):
        return by_token[request.headers.get("authorization", "").removeprefix("Bearer ")]

    @app.post("/auth/v1/token")
    async def fixture_token(request: Request):
        email = (await request.json())["email"]
        return {
            "user": users[email], "access_token": scope_tokens[email][1],
            "refresh_token": "fixture-refresh-token", "token_type": "bearer", "expires_in": 3600,
        }

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        web_port = listener.getsockname()[1]
    web = f"http://127.0.0.1:{web_port}"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 8115))
    env = {name: value for name, value in os.environ.items() if "SAFERETURN_" not in name}
    env.update(
        SAFERETURN_SUPABASE_URL="https://fixture.test", SAFERETURN_SUPABASE_PUBLISHABLE_KEY="sb_publishable_fixture",
        SAFERETURN_WEB_ORIGIN=web, SAFERETURN_API_ORIGIN="http://127.0.0.1:8115",
        PLAYWRIGHT_EXTERNAL_SERVER="1", PLAYWRIGHT_BASE_URL=web, PLAYWRIGHT_CHANNEL="msedge",
        FULFILLMENT_ORDER=str(order_id), FULFILLMENT_JOB=job_id, NEXT_TELEMETRY_DISABLED="1",
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8115, lifespan="off", log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = None
    try:
        process = subprocess.Popen([
            shutil.which("node"), "--require", "./tests/qr-fixture-fetch.cjs", "./node_modules/next/dist/bin/next",
            "start", "--hostname", "127.0.0.1", "--port", str(web_port),
        ], cwd=frontend, env=env, creationflags=flags)
        for _ in range(50):
            try:
                if server.started and httpx.get(web + "/login", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated browser servers did not start")
        result = subprocess.run([
            shutil.which("node"), "./node_modules/@playwright/test/cli.js", "test",
            "tests/fulfillment-workflow.spec.ts", "--reporter=line", "--workers=1", "--output=../tmp/fulfillment-browser-results",
        ], cwd=frontend, env=env, check=False, capture_output=True, encoding="utf-8", errors="replace", timeout=145, creationflags=flags)
        print(result.stdout, result.stderr, flush=True)
        result.check_returncode()
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        server.should_exit = True
        thread.join(timeout=10)
