"""Execute only the owner's hash-pinned development asset-set registration."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
ASSET_ID = "0a7c508b-fc96-42d6-ba58-e367dbb8d08b"
SQL_HASH = "c115c52ab30b3cc73c2a626ae637668db8c052ec06f3ca54e724f1ee22d5be1c"


def main():
    # Canonical LF bytes keep the approved hash stable across Windows/Git checkout.
    raw = (ROOT / "ops/enroll-development-print-assets.sql").read_text(encoding="utf-8").encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == SQL_HASH, "Reviewed SQL changed"
    manifest = json.loads((ROOT / "backend/print-assets/manifest.json").read_text())
    assert manifest["project"] == PROJECT and manifest["asset_set_id"] == ASSET_ID
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((ROOT / "backend/print-assets" / name).read_bytes()).hexdigest() == digest
    if sys.argv[1:] != ["--execute"]:
        print(json.dumps({"checked": True, "sql_sha256": SQL_HASH, "executed": False}))
        return
    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env["SAFERETURN_SUPABASE_URL"].rstrip("/") == f"https://{PROJECT}.supabase.co"
    target = urlsplit(env["SAFERETURN_MIGRATION_DATABASE_URL"].replace("postgresql+psycopg:", "postgresql:"))
    assert target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com" and target.port == 5432 and target.path == "/postgres"
    assert unquote(target.username).endswith("." + PROJECT)
    ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
    assert hashlib.sha256(ca.read_bytes()).hexdigest() == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
    with psycopg.connect(host=target.hostname, port=target.port, dbname="postgres", user=unquote(target.username), password=unquote(target.password), sslmode="verify-full", sslrootcert=str(ca), connect_timeout=10, autocommit=True) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchall() == [("0043_standalone_activation",)]
        connection.execute(raw.decode(), prepare=False)
        observed = connection.execute("SELECT font_path,font_sha256,logo_path,logo_sha256,withdrawn_at FROM public.print_template_asset_sets WHERE asset_set_id=%s", (ASSET_ID,)).fetchone()
        assert observed == ("/app/print-assets/Amiri-Regular.ttf", manifest["files"]["Amiri-Regular.ttf"], "/app/print-assets/logo.svg", manifest["files"]["logo.svg"], None)
    receipt = {"project": PROJECT, "asset_set_id": ASSET_ID, "sql_sha256": SQL_HASH, "executed": True, "record_verified": True, "template_or_qa_approval": False}
    (ROOT / "tmp/template-activation/asset-enrollment-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error as error:
        print(json.dumps({"executed_successfully": False, "error_type": type(error).__name__, "sqlstate": error.sqlstate}))
        sys.exit(1)
