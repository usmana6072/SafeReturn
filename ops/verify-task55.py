"""Run bounded isolated Task 5.5 checks and verify installed rows/DDL/roles stay exact."""

import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

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


def main():
    cfg = dotenv_values(ROOT / "backend/.env")
    env = {
        **os.environ,
        **{k: v for k, v in cfg.items() if k.startswith("SAFERETURN_") and v},
    }
    engine = create_engine(
        database_url(cfg["SAFERETURN_TEST_DATABASE_URL"]),
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
        before = snapshot(engine)
        env["SAFERETURN_CHECKOUT_BASE_REVISION"] = before[0][0]
        args = sys.argv[1:] or ["tests/integration/test_fulfillment.py"]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *args,
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(ROOT / "tmp" / ("task55-" + uuid.uuid4().hex)),
            ],
            check=False,
            cwd=ROOT / "backend",
            env=env,
        )
        assert snapshot(engine) == before, (
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
