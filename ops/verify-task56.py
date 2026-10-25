"""Run bounded isolated Task 5.6 checks and verify installed rows/DDL/roles stay exact."""

import hashlib
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests/integration"))
from app.db.session import database_url
from pg_rehearsal import catalog, metadata


def snapshot(engine):
    with engine.connect() as c:
        c.execute(text("SET TRANSACTION READ ONLY"))
        revision = c.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one()
        assert revision in {
            "0017_print_download_grants",
            "0018_fulfillment_eligibility",
            "0019_retention_recovery",
        }
        meta = metadata(c, revision)
        fingerprints = {}
        for table, _ in meta[1]:
            values = (
                c.execute(text(f'SELECT to_jsonb(r)::text FROM public."{table}" r'))
                .scalars()
                .all()
            )
            fingerprints[table] = hashlib.sha256(
                "\n".join(sorted(values)).encode()
            ).hexdigest()
        return meta, catalog(c), fingerprints


def stable_snapshot(engine):
    # Retry read-only comparisons only. Never replay a test/mutation implicitly.
    for attempt in range(3):
        try:
            return snapshot(engine)
        except OperationalError:
            engine.dispose()
            if attempt == 2:
                raise
            print(
                "Read-only preservation snapshot unavailable; reconnecting.", flush=True
            )
            time.sleep(2)


def cache_database_address(env):
    """Use one fresh pooler DNS answer for this verification process tree only.

    hostaddr supplements the original hostname; TLS, project identity and all
    credential values stay unchanged. No environment file or system DNS edit.
    """
    target = database_url(env["SAFERETURN_TEST_DATABASE_URL"])
    if not target.host.endswith(".pooler.supabase.com") or target.query.get("hostaddr"):
        return
    for attempt in range(3):
        try:
            address = socket.getaddrinfo(
                target.host, target.port or 5432, socket.AF_INET, socket.SOCK_STREAM
            )[0][4][0]
            break
        except socket.gaierror:
            if attempt == 2:
                raise RuntimeError("Development database DNS is unavailable") from None
            time.sleep(2)
    for key in (
        "SAFERETURN_TEST_DATABASE_URL",
        "SAFERETURN_DATABASE_URL",
        "SAFERETURN_API_DATABASE_URL",
        "SAFERETURN_WORKER_DATABASE_URL",
        "SAFERETURN_MIGRATION_DATABASE_URL",
    ):
        if env.get(key):
            url = database_url(env[key])
            if url.host == target.host and not url.query.get("hostaddr"):
                env[key] = url.update_query_dict(
                    {"hostaddr": address}
                ).render_as_string(hide_password=False)
    print(
        "Using a fresh process-scoped pooler address; hostname/TLS/credentials retained.",
        flush=True,
    )


def main():
    cfg = dotenv_values(ROOT / "backend/.env")
    env = {
        **os.environ,
        **{k: v for k, v in cfg.items() if k.startswith("SAFERETURN_") and v},
    }
    cache_database_address(env)
    engine = create_engine(
        database_url(env["SAFERETURN_TEST_DATABASE_URL"]),
        hide_parameters=True,
        pool_pre_ping=True,
        pool_recycle=120,
        connect_args={"connect_timeout": 10},
    )
    awake = None
    if os.name == "nt":
        import ctypes

        awake = ctypes.windll.kernel32.SetThreadExecutionState
        awake.argtypes = [ctypes.c_uint]
        awake.restype = ctypes.c_uint
        if not awake(0x80000001):
            raise RuntimeError("Temporary verification awake request failed")
    try:
        before = stable_snapshot(engine)
        env["SAFERETURN_CHECKOUT_BASE_REVISION"] = before[0][0]
        args = sys.argv[1:]
        if "--live-storage" in args:
            args.remove("--live-storage")
            env["SAFERETURN_TASK56_LIVE_STORAGE"] = "1"
        args = args or [
            "tests/integration/test_finance_retention.py",
            "-k",
            "finance_outage or finance_stale or api_authorization or approval_and_delivery",
            "-x",
        ]
        basetemp_dir = ROOT / "tmp" / ("task56-" + uuid.uuid4().hex)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *args,
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(basetemp_dir),
            ],
            check=False,
            cwd=ROOT / "backend",
            env=env,
            timeout=900,
        )
        assert stable_snapshot(engine) == before, (
            "Installed data, roles or definitions changed"
        )
        print("Installed row fingerprints, roles and DDL preserved exactly.")
        return result.returncode
    finally:
        engine.dispose()
        if awake is not None:
            awake(0x80000000)


if __name__ == "__main__":
    raise SystemExit(main())
