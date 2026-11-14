"""Pinned, read-only template prerequisites; never reads QR/domain/Auth rows."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
env = dotenv_values(ROOT / "backend/.env", interpolate=False)
assert env.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == "https://fhuxryfkfrvycsojkzvq.supabase.co"
target = urlsplit(env["SAFERETURN_MIGRATION_DATABASE_URL"].replace("postgresql+psycopg:", "postgresql:"))
assert target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com" and target.port == 5432
assert unquote(target.username).endswith(".fhuxryfkfrvycsojkzvq") and target.path == "/postgres"
ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
assert hashlib.sha256(ca.read_bytes()).hexdigest() == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
result = {"project": "fhuxryfkfrvycsojkzvq", "read_only": True, "platform": sys.platform,
          "management_enabled": env.get("SAFERETURN_PRINT_TEMPLATE_MANAGEMENT_ENABLED", "false").lower() == "true",
          "web_origin_matches": env.get("SAFERETURN_PRINT_TEMPLATE_WEB_ORIGIN") == "http://127.0.0.1:3100",
          "asset_root_configured": bool(env.get("SAFERETURN_PRINT_TEMPLATE_ASSET_ROOT"))}
queries = {
    "revision": "SELECT version_num FROM public.alembic_version",
    "template_count": "SELECT count(*) FROM public.print_templates",
    "enrolled_assets": "SELECT count(*) FROM public.print_template_asset_sets WHERE withdrawn_at IS NULL",
    "valid_authorities": "SELECT count(*) FROM public.template_authorities WHERE revoked_at IS NULL AND valid_from<=now() AND expires_at>now()",
    "qa_approvals": "SELECT count(*) FROM public.template_qa_approvals",
    "registry_helper": "SELECT to_regprocedure('public.sr_template_registry_gate(boolean)') IS NOT NULL",
}
with psycopg.connect(host=target.hostname, port=target.port, dbname="postgres", user=unquote(target.username), password=unquote(target.password), sslmode="verify-full", sslrootcert=str(ca), connect_timeout=10, autocommit=True) as connection:
    connection.execute("BEGIN READ ONLY")
    connection.execute("SET LOCAL statement_timeout='5000ms'")
    for name, sql in queries.items():
        connection.execute("SAVEPOINT prerequisite")
        try:
            result[name] = connection.execute(sql).fetchall()
        except psycopg.Error as error:
            connection.execute("ROLLBACK TO SAVEPOINT prerequisite")
            result[name] = {"sqlstate": error.sqlstate}
        connection.execute("RELEASE SAVEPOINT prerequisite")
    connection.execute("ROLLBACK")
output = ROOT / "tmp/template-activation/prerequisites.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
