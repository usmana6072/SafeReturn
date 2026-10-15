"""Rollback-only rehearsal of the additive guard on inspected real Auth metadata."""

import os
from pathlib import Path

from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def test_auth_guard_upgrade_is_narrow_and_transactional():
    db = Database.from_settings(
        Settings(database_url=SecretStr(os.environ["SAFERETURN_TEST_DATABASE_URL"]))
    )
    try:
        with db.engine.connect() as c:
            prior = c.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert prior in ("0004_runtime_privacy", "0005_account_session_guard")
            before = c.execute(
                text(
                    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='sr_account_session_state'"
                )
            ).scalar_one()
            cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "head")
            assert c.execute(
                text(
                    "SELECT prosecdef,proconfig FROM pg_proc WHERE oid='public.sr_account_session_state(uuid)'::regprocedure"
                )
            ).one() == (True, ["search_path=pg_catalog"])
            for role, expected in (
                ("safereturn_api", True),
                ("safereturn_worker", False),
                ("anon", False),
                ("authenticated", False),
                ("safereturn_api_login", False),
            ):
                assert (
                    c.execute(
                        text(
                            "SELECT has_function_privilege(:role,'public.sr_account_session_state(uuid)','EXECUTE')"
                        ),
                        {"role": role},
                    ).scalar_one()
                    is expected
                )
            c.rollback()
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == prior
            )
            assert (
                c.execute(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='sr_account_session_state'"
                    )
                ).scalar_one()
                == before
            )
    finally:
        db.close()
