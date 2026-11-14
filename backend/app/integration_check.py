"""Read-only integration preflight. Never loads files or modifies environment implicitly."""

import argparse
import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import database_url


def inspect(values, *, connect=False, metadata_role=False):
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    scripts = ScriptDirectory.from_config(cfg)
    head = scripts.get_current_head()
    required = [
        "SAFERETURN_DATABASE_URL",
        "SAFERETURN_SUPABASE_URL",
        "SAFERETURN_PROFILE_DATA_KEYS",
    ]
    result = {
        "source_head": head,
        "configuration_present": {k: bool(values.get(k)) for k in required},
        "database": "not_inspected",
        "ready_for_independent_orders": False,
    }
    if not connect:
        return result
    raw = values.get(
        "SAFERETURN_MIGRATION_DATABASE_URL"
        if metadata_role
        else "SAFERETURN_DATABASE_URL"
    )
    if not raw:
        result["database"] = "not_configured"
        return result
    engine = None
    try:
        engine = create_engine(
            database_url(raw),
            hide_parameters=True,
            connect_args={
                "connect_timeout": 5,
                "options": "-c statement_timeout=5000 -c default_transaction_read_only=on",
            },
        )
        with engine.connect() as c:
            c.execute(text("SET TRANSACTION READ ONLY"))
            if c.execute(text("SHOW transaction_read_only")).scalar_one() != "on":
                raise RuntimeError("Read-only transaction required")
            revisions = (
                c.execute(text("SELECT version_num FROM public.alembic_version"))
                .scalars()
                .all()
            )
            result.update(database="connected_read_only", installed_revisions=revisions)
            pending = []
            if len(revisions) == 1:
                try:
                    pending = [
                        r.revision
                        for r in reversed(
                            list(scripts.iterate_revisions(head, revisions[0]))
                        )
                    ]
                except (CommandError, ValueError):
                    result["migration_graph"] = "requires_manual_review"
            result["pending_migrations"] = pending
            gates = {}
            for table in ("single_checkout_release", "standalone_owner_release"):
                exists = c.execute(
                    text("SELECT to_regclass(:name) IS NOT NULL"),
                    {"name": "public." + table},
                ).scalar_one()
                gates[table] = (
                    c.execute(text("SELECT enabled FROM public." + table))
                    .scalars()
                    .all()
                    if exists
                    else "missing"
                )
            result["release_gates"] = gates
            result["schema_at_source_head"] = revisions == [head]
            # Schema/connectivity alone cannot establish physical/provider acceptance.
            result["remaining_acceptance"] = [
                "isolated_upgrade_rehearsal",
                "runtime_role_and_rls",
                "auth_storage_worker_journeys",
                "physical_template_approval",
            ]
    except (SQLAlchemyError, ValueError, RuntimeError) as error:
        result["database"] = "inspection_unavailable"
        result["error_type"] = type(error).__name__
        result["sqlstate"] = getattr(getattr(error, "orig", None), "sqlstate", None)
    finally:
        if engine is not None:
            engine.dispose()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Explicitly read configuration without modifying process environment",
    )
    parser.add_argument(
        "--database", action="store_true", help="Read-only schema metadata inspection"
    )
    parser.add_argument(
        "--metadata-role",
        action="store_true",
        help="Use configured migration connection for read-only metadata; never DDL",
    )
    args = parser.parse_args()
    import os

    values = dict(os.environ)
    if args.env_file:
        from dotenv import dotenv_values

        values = {**dotenv_values(args.env_file), **values}
    result = inspect(values, connect=args.database, metadata_role=args.metadata_role)
    print(json.dumps(result, indent=2))
    return (
        2 if result["database"] in {"inspection_unavailable", "not_configured"} else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
