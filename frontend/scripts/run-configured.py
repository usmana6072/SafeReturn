"""Run Next with only public Auth/API configuration from ignored backend/.env.

From frontend: ../backend/.venv/Scripts/python.exe scripts/run-configured.py dev
Optional trailing arguments are forwarded to Next (for example --port 3031).
The database/migration/test/worker URLs are never passed to the web process.
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
command = sys.argv[1] if len(sys.argv) >= 2 else ""
if command not in {"dev", "start", "test"}:
    raise SystemExit("Choose dev, start or test")
configuration = dotenv_values(root / "backend" / ".env")
environment = {
    key: value for key, value in os.environ.items() if not key.startswith("SAFERETURN_")
}
for key in (
    "SAFERETURN_SUPABASE_URL",
    "SAFERETURN_SUPABASE_PUBLISHABLE_KEY",
    "SAFERETURN_SESSION_SIGNING_KEY",
):
    value = configuration.get(key)
    if not value:
        raise SystemExit("Public authentication configuration missing")
    environment[key] = value
environment["SAFERETURN_API_ORIGIN"] = os.environ.get(
    "SAFERETURN_API_ORIGIN", "http://127.0.0.1:8000"
)
environment["SAFERETURN_WEB_ORIGIN"] = os.environ.get(
    "SAFERETURN_WEB_ORIGIN",
    "http://127.0.0.1:3100" if command == "test" else "http://localhost:3000",
)
environment["NEXT_TELEMETRY_DISABLED"] = "1"
raise SystemExit(
    subprocess.call(
        [
            "npm.cmd",
            "run",
            command,
            *(["--", *sys.argv[2:]] if len(sys.argv) > 2 else []),
        ],
        cwd=root / "frontend",
        env=environment,
    )
)
