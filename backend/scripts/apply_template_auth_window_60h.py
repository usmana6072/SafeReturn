"""Apply only the reviewed 0063/0064 revisions to the pinned dev database."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
BEFORE = ["0044_support_dev_exception", "0062_template_geometry_minimums"]
AFTER = ["0044_support_dev_exception", "0064_template_auth_60h"]
REVISION = "0064_template_auth_60h"
FUNCTIONS = (
    "sr_template_draft_service_v33",
    "sr_template_preview_admit",
    "sr_template_lifecycle",
)
AUTH_FUNCTIONS = """SELECT proname,prosrc,prosecdef,proconfig,pg_get_userbyid(proowner),proacl::text
FROM pg_proc WHERE oid IN (
 'public.sr_template_draft_service_v33(uuid,bigint,text,jsonb)'::regprocedure,
 'public.sr_template_preview_admit(uuid,bigint,text,text)'::regprocedure,
 'public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure)
ORDER BY proname"""
METADATA = """SELECT oid::text,proowner::regrole::text,proacl::text,proconfig,prosecdef
FROM pg_proc WHERE oid='public.sr_template_content_valid(jsonb)'::regprocedure"""


def revisions(connection):
    return connection.execute(
        text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
    ).scalars().all()


def functions(connection):
    return connection.execute(text(AUTH_FUNCTIONS)).all()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()

    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env["SAFERETURN_SUPABASE_URL"].rstrip("/") == (
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
        and target.path == "/postgres"
        and unquote(target.username).endswith("." + PROJECT)
    )
    ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == (
        "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
    )
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/alembic"))
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(config)
    assert script.get_revision("0063_optional_urdu_compact").down_revision == (
        "0062_template_geometry_minimums"
    )
    assert script.get_revision(REVISION).down_revision == (
        "0063_optional_urdu_compact"
    )

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
    result = {"project": PROJECT, "revision": REVISION}
    template_metadata = text(METADATA)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text("SET LOCAL lock_timeout='3s'"))
            connection.execute(text("SET LOCAL statement_timeout='20000ms'"))
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": "safereturn.template-auth-window-60h"},
            )
            installed = revisions(connection)
            if installed != BEFORE:
                raise RuntimeError(
                    f"Unexpected DB migration state {installed}; no update attempted"
                )
            before_auth = functions(connection)
            assert [row[0] for row in before_auth] == sorted(FUNCTIONS)
            assert all(
                row[2] and row[3] == ["search_path=pg_catalog"]
                for row in before_auth
            )
            for name, body, *_ in before_auth:
                assert "sr_account_session_state" in body and "sr_is_staff" in body
                assert "-amr>1200" in body or "-amr>300" in body
                assert "-amr>216000" not in body
            before_metadata = connection.execute(template_metadata).one()

            config.attributes["connection"] = connection
            command.upgrade(config, REVISION)

            assert revisions(connection) == AFTER
            after_auth = functions(connection)
            assert [row[2:] for row in after_auth] == [row[2:] for row in before_auth]
            for old, new in zip(before_auth, after_auth, strict=True):
                expected_body = old[1].replace("-amr>1200", "-amr>216000").replace(
                    "-amr>300", "-amr>216000"
                )
                assert new[1].strip() == expected_body.strip()
                assert "-amr>216000" in new[1]
            assert connection.execute(template_metadata).one() == before_metadata
            result.update(
                applied_revisions=["0063_optional_urdu_compact", REVISION],
                installed_revisions=AFTER,
                updated_functions=[row[0] for row in after_auth],
                function_security_metadata_preserved=True,
                content_validator_metadata_preserved=True,
                auth_age_seconds=216000,
            )
            transaction.commit()

        with engine.connect() as connection:
            assert revisions(connection) == AFTER
            result["commit_verified"] = True
    finally:
        engine.dispose()

    receipt = ROOT / "tmp/template-activation/auth-window-60h-applied.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
