"""Apply the reviewed template auth-window SQL to the pinned development DB."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
REVISION = "0043_standalone_activation"
SQL_PATH = ROOT / "backend/alembic/versions/0064_template_auth_60_hours.sql"
SQL_SHA256 = "2b4d5b6c60a801344df0f448eb08a9890e79ba3d7fe999e5aae5c0398fd77ff1"
FUNCTIONS = (
    "sr_template_draft_service_v33",
    "sr_template_preview_admit",
    "sr_template_lifecycle",
)


def definitions(connection):
    return connection.execute(
        "SELECT proname,prosrc,prosecdef,proconfig,pg_get_userbyid(proowner),proacl::text "
        "FROM pg_proc WHERE oid IN ("
        "'public.sr_template_draft_service_v33(uuid,bigint,text,jsonb)'::regprocedure,"
        "'public.sr_template_preview_admit(uuid,bigint,text,text)'::regprocedure,"
        "'public.sr_template_lifecycle(uuid,bigint,text,jsonb)'::regprocedure) "
        "ORDER BY proname"
    ).fetchall()


def expected_bodies():
    source = (ROOT / "ops/template-auth-window-20min.sql").read_text(encoding="utf-8")
    result = {}
    for name in FUNCTIONS:
        marker = f"CREATE OR REPLACE FUNCTION public.{name}("
        chunk = source[source.index(marker) :]
        result[name] = chunk.split("AS $$", 1)[1].split("$$;", 1)[0].strip()
    return result


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
    sql = SQL_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(sql).hexdigest() == SQL_SHA256
    expected = expected_bodies()
    password = unquote(target.password)
    with psycopg.connect(
        host=target.hostname,
        port=target.port,
        dbname="postgres",
        user=unquote(target.username),
        password=password,
        sslmode="verify-full",
        sslrootcert=str(ca),
        connect_timeout=10,
    ) as connection:
        connection.execute("SET LOCAL lock_timeout='3s'")
        connection.execute("SET LOCAL statement_timeout='20000ms'")
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            ("safereturn.template-auth-window-60h",),
        )
        revisions = connection.execute(
            "SELECT version_num FROM public.alembic_version ORDER BY version_num"
        ).fetchall()
        assert revisions == [(REVISION,)], (
            "Unexpected DB migration state; no update attempted"
        )
        before = definitions(connection)
        assert [row[0] for row in before] == sorted(FUNCTIONS)
        for name, body, security_definer, config, _owner, _acl in before:
            assert body.strip() == expected[name], (
                f"Installed {name} differs from reviewed source"
            )
            assert security_definer and config == ["search_path=pg_catalog"]

        connection.execute(sql.decode("utf-8"), prepare=False)
        after = definitions(connection)
        assert [row[2:] for row in after] == [row[2:] for row in before]
        for name, body, *_ in after:
            expected_body = expected[name].replace("-amr>1200", "-amr>216000").replace(
                "-amr>300", "-amr>216000"
            )
            assert body.strip() == expected_body, (
                f"Unexpected updated body for {name}"
            )
            assert "-amr>216000" in body and "-amr>1200" not in body
        assert connection.execute(
            "SELECT version_num FROM public.alembic_version ORDER BY version_num"
        ).fetchall() == revisions

    result = {
        "project": PROJECT,
        "database_revision_unchanged": REVISION,
        "updated_functions": [row[0] for row in after],
        "owner_acl_search_path_and_security_definer_preserved": True,
        "auth_age_seconds": 216000,
        "alembic_revision_stamped": False,
    }
    receipt = ROOT / "tmp/template-activation/auth-window-60h-applied.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
