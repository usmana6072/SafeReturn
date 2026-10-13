# SafeReturn backend

From `backend` using Python 3.12 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Public liveness: `GET /api/v1/health/live`. Readiness is disabled (404)
unless `SAFERETURN_READINESS_TOKEN` is set in the process environment.
Send that token as a Bearer credential; unauthorized probes return 401.
Authorized readiness currently returns 503 because database integration is pending.
Environment files are not loaded implicitly. No database migrations run at startup.

Checks: `.venv/Scripts/python.exe -m pytest -q` and
`.venv/Scripts/python.exe -m ruff check app tests`.
