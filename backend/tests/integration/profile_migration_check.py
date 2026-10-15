"""Inspect development metadata and rollback-rehearse Task 3.3 forward revisions."""

import os
import sys
from pathlib import Path

from alembic.config import Config
from pg_rehearsal import catalog, metadata
from sqlalchemy import create_engine

from alembic import command
from app.db.session import database_url

engine = create_engine(
    database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"]),
    hide_parameters=True,
    connect_args={"connect_timeout": 10},
)
previous_revision, target_revision = (
    ("0010_profile_consent", "0011_profile_owner_locks")
    if "--owner-locks" in sys.argv
    else ("0009_activation_rechecks", "0010_profile_consent")
)
try:
    with engine.connect() as c:
        before = metadata(c, previous_revision)
        original = catalog(c)
        print(
            f"Before: {before[0]}, {len(before[1])} RLS tables, {sum(before[3].values())} domain rows"
        )
        c.rollback()
        cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        cfg.attributes["connection"] = c
        transaction = c.begin()
        command.upgrade(cfg, target_revision)
        assert metadata(c)[1:] == before[1:]
        transaction.rollback()
        assert metadata(c, previous_revision) == before
        assert catalog(c) == original
        c.rollback()
        print("Forward migration / complete rollback / existing row preservation: PASS")
        if "--apply" in sys.argv:
            with c.begin():
                command.upgrade(cfg, target_revision)
                assert metadata(c)[1:] == before[1:]
            print(
                f"Development {target_revision} applied; rows and runtime roles preserved"
            )
finally:
    engine.dispose()
