"""Launch separated local runtimes and test a supplied user without domain writes.

Run with the backend virtualenv Python. Explicitly loads ignored backend/.env;
test-user credentials go only to Playwright, never the Next/FastAPI runtime.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values
from pydantic import SecretStr

root = Path(__file__).resolve().parents[2]
email_flow = len(sys.argv) == 3 and sys.argv[1] in {"--email", "--recovery-email"}
if len(sys.argv) > 1 and not email_flow:
    raise SystemExit(
        "Use no arguments for existing-account checks, or --email <authorized-destination>"
    )
cfg = dotenv_values(root / "backend" / ".env")
sys.path.insert(0, str(root / "backend"))
sys.path.insert(0, str(root / "backend/tests/integration"))
from pg_rehearsal import metadata

from app.core.config import Settings
from app.db.session import Database

# Privileged read-only inspection belongs to this controller, never either runtime.
inspection = Database.from_settings(
    Settings(database_url=SecretStr(cfg["SAFERETURN_TEST_DATABASE_URL"]))
)
try:
    with inspection.engine.connect() as connection:
        baseline = metadata(connection)
        from sqlalchemy import text

        database_now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        if abs((database_now - datetime.now(UTC)).total_seconds()) > 60:
            raise RuntimeError(
                "Local UTC clock differs from development database by over 60 seconds; sync the system clock before live Auth verification. No emails or sessions created."
            )
finally:
    inspection.close()
required = (
    "SAFERETURN_AUTH_TEST_EMAIL",
    "SAFERETURN_AUTH_TEST_PASSWORD",
    "SAFERETURN_SUPABASE_URL",
    "SAFERETURN_SUPABASE_PUBLISHABLE_KEY",
    "SAFERETURN_SESSION_SIGNING_KEY",
    "SAFERETURN_DATABASE_URL",
)
if not all(cfg.get(name) for name in required):
    raise SystemExit("Live authentication test configuration missing")
for port in (8100, 3100):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit("Live test port occupied; no server started")
base = {
    name: value
    for name, value in os.environ.items()
    if not name.startswith("SAFERETURN_")
}
base["NEXT_TELEMETRY_DISABLED"] = "1"
api_env = {
    **base,
    "SAFERETURN_DATABASE_URL": cfg["SAFERETURN_DATABASE_URL"],
    "SAFERETURN_SUPABASE_URL": cfg["SAFERETURN_SUPABASE_URL"],
}
web_env = {
    **base,
    "SAFERETURN_API_ORIGIN": "http://127.0.0.1:8100",
    "SAFERETURN_WEB_ORIGIN": "http://127.0.0.1:3100",
}
if email_flow:
    web_env["SAFERETURN_AUTH_TEST_DIAGNOSTICS"] = "1"
for name in (
    "SAFERETURN_SUPABASE_URL",
    "SAFERETURN_SUPABASE_PUBLISHABLE_KEY",
    "SAFERETURN_SESSION_SIGNING_KEY",
):
    web_env[name] = cfg[name]
test_env = {
    **web_env,
    "PLAYWRIGHT_EXTERNAL_SERVER": "1",
    "SAFERETURN_LIVE_AUTH_TEST": "1",
}
if email_flow:
    test_env["SAFERETURN_LIVE_EMAIL_DESTINATION"] = sys.argv[2]
    if sys.argv[1] == "--recovery-email":
        test_env["SAFERETURN_LIVE_EMAIL_RECOVERY_ONLY"] = "1"
    test_env["PLAYWRIGHT_CHANNEL"] = "msedge"
else:
    for name in ("SAFERETURN_AUTH_TEST_EMAIL", "SAFERETURN_AUTH_TEST_PASSWORD"):
        test_env[name] = cfg[name]
processes = []


def wait(url):
    with httpx.Client(timeout=2, trust_env=False) as client:
        for _ in range(60):
            try:
                if client.get(url).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
    raise RuntimeError("Live test runtime failed to start")


try:
    processes.append(
        subprocess.Popen(
            [
                str(root / "backend/.venv/Scripts/python.exe"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8100",
                "--no-access-log",
            ],
            cwd=root / "backend",
            env=api_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    )
    wait("http://127.0.0.1:8100/api/v1/health/live")
    processes.append(
        subprocess.Popen(
            [
                shutil.which("node"),
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "3100",
            ],
            cwd=root / "frontend",
            env=web_env,
            stdout=None if email_flow else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    )
    wait("http://127.0.0.1:3100/")
    raise SystemExit(
        subprocess.call(
            [
                shutil.which("npm.cmd"),
                "test",
                "--",
                *(
                    ["tests/auth-email-live.spec.ts", "--headed"]
                    if email_flow
                    else ["tests/auth-live.spec.ts", "tests/auth-negative.spec.ts"]
                ),
                "--workers=1",
            ],
            cwd=root / "frontend",
            env=test_env,
        )
    )
finally:
    for process in reversed(processes):
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    inspection = Database.from_settings(
        Settings(database_url=SecretStr(cfg["SAFERETURN_TEST_DATABASE_URL"]))
    )
    try:
        with inspection.engine.connect() as connection:
            if metadata(connection) != baseline:
                raise RuntimeError(
                    "Installed metadata/domain row counts changed during read-only live Auth test"
                )
    finally:
        inspection.close()
