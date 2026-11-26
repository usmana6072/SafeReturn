"""Pinned template geometry migration; rollback rehearsal by default."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
REVISION = "0062_template_geometry_minimums"
SQL_SHA256 = "c4c1018429375d81fff846052ccf7588d8fd2e705c5963ce70561eb8a1755cbe"
BEFORE = ["0044_support_dev_exception", "0061_delivery_print_cleanup"]
AFTER = ["0044_support_dev_exception", REVISION]
CONTENT = {
    "schema_version": 1,
    "renderer": "safereturn-vector-v1",
    "preset": "fixed-footer-v1",
    "symbol_mm": "25.00",
    "width_mm": "35.00",
    "height_mm": "50.00",
    "qr_x_mm": "5.00",
    "qr_y_mm": "13.00",
    "logo_mm": "3.50",
    "min_pitch_mm": "0.30",
    "font_pt": "8.00",
    "header": "SafeReturn",
    "english_lines": ["SCAN TO CONTACT THE OWNER"],
    "urdu_lines": ["مالک سے رابطہ کرنے کے لیے اسکین کریں"],
    "asset_set_id": "0a7c508b-fc96-42d6-ba58-e367dbb8d08b",
    "material_codes": ["vinyl"],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == (
        f"https://{PROJECT}.supabase.co"
    )
    target = urlsplit(
        env["SAFERETURN_MIGRATION_DATABASE_URL"].replace(
            "postgresql+psycopg:", "postgresql:"
        )
    )
    assert (
        target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com"
        and target.port == 5432
        and unquote(target.username).endswith("." + PROJECT)
        and target.path == "/postgres"
    )
    ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == (
        "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
    )
    sql_path = ROOT / "backend/alembic/versions/0062_template_geometry_minimums.sql"
    sql_bytes = sql_path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(sql_bytes).hexdigest() == SQL_SHA256

    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/alembic"))
    from alembic.script import ScriptDirectory

    migration = ScriptDirectory.from_config(config).get_revision(REVISION)
    assert migration.down_revision == "0061_delivery_print_cleanup"

    engine = create_engine(
        "postgresql+psycopg://",
        creator=lambda: psycopg.connect(
            host=target.hostname,
            port=target.port,
            dbname="postgres",
            user=unquote(target.username),
            password=unquote(target.password),
            sslmode="verify-full",
            sslrootcert=str(ca),
            connect_timeout=10,
        ),
    )
    report = {
        "project": PROJECT,
        "revision": REVISION,
        "sql_sha256": SQL_SHA256,
        "mode": "apply" if args.apply else "rollback-rehearsal",
    }
    function_metadata = text(
        "SELECT oid::text,proowner::regrole::text,proacl::text,proconfig,prosecdef "
        "FROM pg_proc WHERE oid='public.sr_template_content_valid(jsonb)'::regprocedure"
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET LOCAL lock_timeout='3s'"))
            connection.execute(text("SET LOCAL statement_timeout='20000ms'"))
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock("
                    "hashtextextended('safereturn.template-geometry-0062',0))"
                )
            )
            installed = connection.execute(
                text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
            ).scalars().all()
            assert installed == BEFORE, "Unexpected installed revisions; no upgrade attempted"
            assert connection.execute(
                text("SELECT to_regclass('public.print_template_revisions') IS NOT NULL")
            ).scalar_one()
            assert connection.execute(
                text(
                    "SELECT convalidated FROM pg_constraint "
                    "WHERE conrelid='public.print_template_revisions'::regclass "
                    "AND conname='ck_template_content'"
                )
            ).scalar_one()
            before_metadata = connection.execute(function_metadata).one()
            before_definition = connection.execute(
                text(
                    "SELECT pg_get_functiondef("
                    "'public.sr_template_content_valid(jsonb)'::regprocedure)"
                )
            ).scalar_one()
            assert re.search(r"NOT\s+BETWEEN\s+30\s+AND\s+100", before_definition)
            assert re.search(r"NOT\s+BETWEEN\s+40\s+AND\s+190", before_definition)
            assert re.search(r"NOT\s+BETWEEN\s+60\s+AND\s+270", before_definition)
            assert re.search(r"qr_y_mm.{0,80}<18", before_definition)
            payload = json.dumps(CONTENT, ensure_ascii=False)
            accepted_before = connection.execute(
                text(
                    "SELECT public.sr_template_content_valid(CAST(:payload AS jsonb))"
                ),
                {"payload": payload},
            ).scalar_one()
            assert accepted_before is False, "Unexpected pre-migration validator behavior"
            revision_count = connection.execute(
                text("SELECT count(*) FROM public.print_template_revisions")
            ).scalar_one()
            connection.execute(text("SELECT public.sr_template_registry_gate(true)"))
            config.attributes["connection"] = connection
            command.upgrade(config, REVISION)
            installed = connection.execute(
                text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
            ).scalars().all()
            assert installed == AFTER
            assert connection.execute(function_metadata).one() == before_metadata
            accepted_after = connection.execute(
                text(
                    "SELECT public.sr_template_content_valid(CAST(:payload AS jsonb))"
                ),
                {"payload": payload},
            ).scalar_one()
            assert accepted_after is True, "Compact design still fails the database check"
            assert connection.execute(
                text("SELECT count(*) FROM public.print_template_revisions")
            ).scalar_one() == revision_count
            report.update(
                validator_accepts_reported_design=True,
                function_metadata_preserved=True,
                revision_count_unchanged=True,
            )
            if args.apply:
                transaction.commit()
            else:
                transaction.rollback()

        with engine.connect() as connection:
            installed = connection.execute(
                text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
            ).scalars().all()
            expected = AFTER if args.apply else BEFORE
            assert installed == expected
            accepted = connection.execute(
                text(
                    "SELECT public.sr_template_content_valid(CAST(:payload AS jsonb))"
                ),
                {"payload": json.dumps(CONTENT, ensure_ascii=False)},
            ).scalar_one()
            assert accepted is args.apply
            report["installed_revisions"] = installed
            report["commit_verified" if args.apply else "rollback_verified"] = True
    finally:
        engine.dispose()

    output = ROOT / (
        "tmp/template-activation/template-geometry-minimums-applied.json"
        if args.apply
        else "tmp/template-activation/template-geometry-minimums-rehearsal.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
