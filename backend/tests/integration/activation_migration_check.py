"""Inspect and rehearse Task 3.2 forward migrations; optionally apply to dev."""

import os
import sys
from pathlib import Path

from alembic.config import Config
from pg_rehearsal import catalog, metadata
from sqlalchemy import create_engine, text

from alembic import command
from app.db.session import database_url

engine = create_engine(
    database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"]),
    hide_parameters=True,
    connect_args={"connect_timeout": 10},
)
previous_revision, target_revision = (
    ("0008_atomic_activation", "0009_activation_rechecks")
    if "--rechecks" in sys.argv
    else ("0007_qr_batch_environment", "0008_atomic_activation")
)
try:
    with engine.connect() as c:
        before = metadata(c, previous_revision)
        original = catalog(c)
        print(
            f"Before: head={before[0]}, RLS={len(before[1])}, domain rows={sum(before[3].values())}"
        )
        c.rollback()
        transaction = c.begin()
        cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        cfg.attributes["connection"] = c
        command.upgrade(cfg, target_revision)
        after = metadata(c, target_revision)
        assert after[1:] == before[1:]
        assert c.execute(
            text(
                "SELECT has_function_privilege('safereturn_api','public.sr_confirm_activation(uuid,text,text)','EXECUTE'),has_function_privilege('authenticated','public.sr_confirm_activation(uuid,text,text)','EXECUTE')"
            )
        ).one() == (True, False)
        transaction.rollback()
        assert metadata(c, previous_revision) == before
        assert catalog(c) == original
        c.rollback()
        print("Forward migration / permissions / rollback / row preservation: PASS")
        if "--apply" in sys.argv:
            with c.begin():
                command.upgrade(cfg, target_revision)
                assert metadata(c, target_revision)[1:] == before[1:]
            print(
                f"Development forward migration applied: {target_revision}; rows and runtime roles preserved"
            )
finally:
    engine.dispose()
