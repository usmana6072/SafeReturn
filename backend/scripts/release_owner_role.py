"""Rehearse/apply owner authorization without enrolling or changing any staff."""

import argparse
import hashlib
import ipaddress
import sys
from pathlib import Path
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.util.exc import CommandError
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from alembic import command
from app.db.session import database_url

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = "0059_shipment_delivery_email"
REVISION = "0060_owner_role"


def heads(c):
    return set(
        c.execute(text("SELECT version_num FROM public.alembic_version")).scalars()
    )


def snapshot(c):
    return (
        c.execute(
            text(
                "SELECT md5(coalesce(string_agg(to_jsonb(r)::text,'' ORDER BY r.id),'')) FROM public.staff_roles r"
            )
        ).scalar_one(),
        c.execute(
            text(
                "SELECT oid,proowner,proacl::text,proconfig,prosecdef FROM pg_proc WHERE pronamespace='public'::regnamespace AND prokind='f' ORDER BY oid"
            )
        ).all(),
        c.execute(
            text(
                "SELECT oid,md5(pg_get_functiondef(oid)) FROM pg_proc WHERE pronamespace='public'::regnamespace AND prokind='f' AND position('public.staff_roles' IN pg_get_functiondef(oid))=0 ORDER BY oid"
            )
        ).all(),
        c.execute(
            text(
                "SELECT relacl::text,relrowsecurity FROM pg_class WHERE oid='public.staff_roles'::regclass"
            )
        ).one(),
    )


def verify(c):
    assert (
        "'owner'"
        in c.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='public.staff_roles'::regclass AND conname='ck_staff_roles_role'"
            )
        ).scalar_one()
    )
    assert (
        "role = 'owner'"
        in c.execute(
            text(
                "SELECT pg_get_functiondef('public.sr_is_staff(text[])'::regprocedure)"
            )
        ).scalar_one()
        or "role='owner'"
        in c.execute(
            text(
                "SELECT pg_get_functiondef('public.sr_is_staff(text[])'::regprocedure)"
            )
        ).scalar_one()
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--hostaddr", help="Optional verified pooler IP when DNS routing is unavailable"
    )
    args = parser.parse_args()
    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    url = database_url(env["SAFERETURN_MIGRATION_DATABASE_URL"])
    project = urlsplit(env["SAFERETURN_SUPABASE_URL"]).hostname.split(".")[0]
    assert url.username.endswith("." + project), "Database/Auth project mismatch"
    if args.hostaddr:
        assert ipaddress.ip_address(args.hostaddr).is_global
        assert url.host.endswith(".supabase.com")
        certificate = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
        assert (
            hashlib.sha256(certificate.read_bytes()).hexdigest()
            == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
        )
        url = url.update_query_dict(
            {
                "hostaddr": args.hostaddr,
                "sslmode": "verify-full",
                "sslrootcert": str(certificate),
            }
        )
    engine = create_engine(
        url, hide_parameters=True, connect_args={"connect_timeout": 10}
    )
    try:
        with engine.connect() as c:
            transaction = c.begin()
            c.execute(text("SET LOCAL statement_timeout='20s'"))
            c.execute(text("SET LOCAL lock_timeout='3s'"))
            c.execute(text("LOCK TABLE public.alembic_version IN EXCLUSIVE MODE"))
            before_heads, before = heads(c), snapshot(c)
            assert (PREVIOUS in before_heads) != (REVISION in before_heads), (
                "Unexpected installed revision"
            )
            other_heads = before_heads - {PREVIOUS, REVISION}
            if PREVIOUS in before_heads:
                cfg = Config(str(ROOT / "backend/alembic.ini"))
                cfg.set_main_option("script_location", str(ROOT / "backend/alembic"))
                cfg.attributes["connection"] = c
                command.upgrade(cfg, REVISION)
            verify(c)
            assert snapshot(c) == before, (
                "Existing staff grants, function ACLs or unrelated functions changed"
            )
            assert heads(c) == other_heads | {REVISION}
            if args.apply:
                transaction.commit()
            else:
                transaction.rollback()
        with engine.connect() as c:
            assert heads(c) == (
                other_heads | {REVISION} if args.apply else before_heads
            )
            if args.apply:
                verify(c)
        print(
            "Owner role migration "
            + (
                "committed and independently verified."
                if args.apply
                else "rehearsed; rollback verified."
            ),
            flush=True,
        )
        print(
            "No accounts assigned. All staff grant records, function permissions and unrelated migration heads preserved.",
            flush=True,
        )
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
            "Owner role migration stopped:",
            type(cause).__name__,
            getattr(cause, "sqlstate", None),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
