"""Register the versioned Icon Kitchen logo asset set in the development project."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
OLD_ASSET_ID = "0a7c508b-fc96-42d6-ba58-e367dbb8d08b"
ASSET_ID = "70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4"
SQL_HASH = "773aa9ebc8fb3202f8e696587858217a8ce63f61a98e34485ae85ac30775c701"
OLD_LOGO_HASH = "6edd586082d2f2005252d4e745303cc1b2705cfad890d495575d51ed440beeea"
FONT_HASH = "ab391c4147d054c48976e98322ad0eefe1427aa0e0502a12a4c75d80a70cfcd7"
NEW_LOGO_HASH = "652c5cbae3a5f67a8007c37831abf18cea427174018941bf439437dbc76e8d97"


def main():
    sql_path = ROOT / "ops/enroll-development-print-icon-192.sql"
    raw = sql_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SQL_HASH, "Reviewed registration SQL changed"

    assets = ROOT / "backend/print-assets"
    manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project"] == PROJECT
    assert manifest["candidate_asset_set_id"] == ASSET_ID
    assert manifest["candidate_logo_file"] == "logo-icon-192.svg"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == digest
    assert manifest["files"]["Amiri-Regular.ttf"] == FONT_HASH
    assert manifest["files"]["logo.svg"] == OLD_LOGO_HASH
    assert manifest["files"]["logo-icon-192.svg"] == NEW_LOGO_HASH

    if sys.argv[1:] != ["--execute"]:
        print(json.dumps({"checked": True, "project": PROJECT, "asset_set_id": ASSET_ID, "sql_sha256": SQL_HASH, "executed": False}))
        return

    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env["SAFERETURN_SUPABASE_URL"].rstrip("/") == f"https://{PROJECT}.supabase.co"
    target = urlsplit(env["SAFERETURN_MIGRATION_DATABASE_URL"].replace("postgresql+psycopg:", "postgresql:"))
    assert target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com"
    assert target.port == 5432 and target.path == "/postgres"
    assert unquote(target.username).endswith("." + PROJECT)
    ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"

    with psycopg.connect(
        host=target.hostname,
        port=target.port,
        dbname="postgres",
        user=unquote(target.username),
        password=unquote(target.password),
        sslmode="verify-full",
        sslrootcert=str(ca),
        connect_timeout=10,
        autocommit=True,
    ) as connection:
        versions = connection.execute(
            "SELECT version_num FROM public.alembic_version ORDER BY version_num"
        ).fetchall()
        assert versions == [("0044_support_dev_exception",), ("0064_template_auth_60h",)]
        assert connection.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_trigger "
            "WHERE tgname='sr_template_asset_fixed' AND NOT tgisinternal)"
        ).fetchone()[0], "Historical-asset immutability trigger missing; refusing registration"
        existing = connection.execute(
            "SELECT font_path,font_sha256,logo_path,logo_sha256,withdrawn_at "
            "FROM public.print_template_asset_sets WHERE asset_set_id=%s",
            (OLD_ASSET_ID,),
        ).fetchone()
        assert existing == (
            "/app/print-assets/Amiri-Regular.ttf",
            FONT_HASH,
            "/app/print-assets/logo.svg",
            OLD_LOGO_HASH,
            None,
        ), "Historical asset set is missing or differs; refusing registration"
        connection.execute(raw.decode("utf-8"), prepare=False)
        added = connection.execute(
            "SELECT font_path,font_sha256,logo_path,logo_sha256,withdrawn_at "
            "FROM public.print_template_asset_sets WHERE asset_set_id=%s",
            (ASSET_ID,),
        ).fetchone()
        assert added == (
            "/app/print-assets/Amiri-Regular.ttf",
            FONT_HASH,
            "/app/print-assets/logo-icon-192.svg",
            NEW_LOGO_HASH,
            None,
        ), "New asset set did not verify"

    print(json.dumps({"project": PROJECT, "asset_set_id": ASSET_ID, "new_logo_sha256": NEW_LOGO_HASH, "executed": True, "record_verified": True, "template_or_qa_approval": False}))


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error as error:
        print(json.dumps({"executed_successfully": False, "error_type": type(error).__name__, "sqlstate": error.sqlstate}))
        sys.exit(1)
