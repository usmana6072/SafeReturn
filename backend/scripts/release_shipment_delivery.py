"""Rehearse or apply only the shipment delivery email migration on the configured database."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from alembic.config import Config
from alembic.util.exc import CommandError
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from alembic import command
from app.db.session import database_url

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = "0058_finder_email_details"
REVISION = "0059_shipment_delivery_email"
SIGNATURE = "public.sr_shipment_notification_recipient(uuid,integer,bytea,smallint)"


def heads(connection):
    return set(
        connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalars()
    )


def definitions(connection):
    return connection.execute(
        text("""
        SELECT oid,md5(pg_get_functiondef(oid)),proowner,proacl::text,proconfig
        FROM pg_proc WHERE pronamespace='public'::regnamespace AND prokind='f'
          AND proname NOT IN ('sr_shipment_notification_recipient','sr_outbox_relation') ORDER BY oid
    """)
    ).all()


def verify(connection):
    guard = connection.execute(
        text("SELECT pg_get_functiondef('public.sr_outbox_relation()'::regprocedure)")
    ).scalar_one()
    assert "Delivery notification must match delivered shipment/customer" in guard
    assert "Notification event identity/payload is immutable" in guard
    for role in ("anon", "authenticated", "safereturn_api", "safereturn_worker"):
        allowed = connection.execute(
            text("SELECT has_function_privilege(:role,:signature,'EXECUTE')"),
            {"role": role, "signature": SIGNATURE},
        ).scalar_one()
        assert allowed == (role == "safereturn_worker"), "Unexpected function access"
    assert connection.execute(
        text(
            "SELECT proconfig FROM pg_proc WHERE oid=CAST(:signature AS regprocedure)"
        ),
        {"signature": SIGNATURE},
    ).scalar_one() == ["search_path=pg_catalog"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit after verification; default rehearses and rolls back",
    )
    args = parser.parse_args()
    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    raw = env.get("SAFERETURN_MIGRATION_DATABASE_URL")
    if not raw:
        raise RuntimeError("Migration database is not configured")
    url = database_url(raw)
    # Pin the same project as the application's configured Supabase Auth.
    project = urlsplit(env["SAFERETURN_SUPABASE_URL"]).hostname.split(".")[0]
    assert url.username.endswith("." + project), "Database/Auth project mismatch"
    engine = create_engine(
        url, hide_parameters=True, connect_args={"connect_timeout": 10}
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET LOCAL statement_timeout='20s'"))
            connection.execute(text("SET LOCAL lock_timeout='3s'"))
            connection.execute(
                text("LOCK TABLE public.alembic_version IN EXCLUSIVE MODE")
            )
            before = heads(connection)
            assert (PREVIOUS in before) != (REVISION in before), (
                "Unexpected installed revision"
            )
            unrelated_heads = before - {PREVIOUS, REVISION}
            guard_acl = connection.execute(
                text(
                    "SELECT proowner,proacl::text,proconfig,prosecdef FROM pg_proc WHERE oid='public.sr_outbox_relation()'::regprocedure"
                )
            ).one()
            original_functions = definitions(connection)
            counts = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM finder_messages),(SELECT count(*) FROM notification_outbox)"
                )
            ).one()
            if REVISION not in before:
                config = Config(str(ROOT / "backend/alembic.ini"))
                config.set_main_option("script_location", str(ROOT / "backend/alembic"))
                config.attributes["connection"] = connection
                command.upgrade(config, REVISION)
            verify(connection)
            assert heads(connection) == unrelated_heads | {REVISION}
            assert definitions(connection) == original_functions, (
                "Unrelated functions changed"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT proowner,proacl::text,proconfig,prosecdef FROM pg_proc WHERE oid='public.sr_outbox_relation()'::regprocedure"
                    )
                ).one()
                == guard_acl
            )
            assert (
                connection.execute(
                    text(
                        "SELECT (SELECT count(*) FROM finder_messages),(SELECT count(*) FROM notification_outbox)"
                    )
                ).one()
                == counts
            )
            if args.apply:
                transaction.commit()
            else:
                transaction.rollback()
        with engine.connect() as connection:
            assert heads(connection) == (
                unrelated_heads | {REVISION} if args.apply else before
            )
            if args.apply:
                verify(connection)
        print(
            "Shipment delivery email migration",
            "committed and independently verified"
            if args.apply
            else "rehearsed; rollback verified",
            flush=True,
        )
        print(
            "Unrelated migration heads, unrelated functions and message/outbox counts preserved.",
            flush=True,
        )
        if args.apply:
            worker_url = database_url(env["SAFERETURN_WORKER_DATABASE_URL"])
            worker_engine = create_engine(
                worker_url, hide_parameters=True, connect_args={"connect_timeout": 10}
            )
            try:
                with worker_engine.begin() as connection:
                    connection.execute(text("SET LOCAL ROLE safereturn_worker"))
                    connection.execute(
                        text(
                            "SELECT set_config('safereturn.worker_id','delivery-release-verification',true)"
                        )
                    )
                    assert (
                        connection.execute(
                            text(
                                "SELECT public.sr_shipment_notification_recipient(:id,1,NULL,NULL)"
                            ),
                            {"id": uuid4()},
                        ).scalar_one()
                        is None
                    )
                print(
                    "Restricted worker login verified; an unleased request exposes no customer email.",
                    flush=True,
                )
            finally:
                worker_engine.dispose()
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except (
        SQLAlchemyError,
        CommandError,
        AssertionError,
        KeyError,
        ValueError,
        OSError,
    ) as error:
        cause = getattr(error, "orig", error)
        print(
            "Shipment delivery migration stopped:",
            type(cause).__name__,
            getattr(cause, "sqlstate", None),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
