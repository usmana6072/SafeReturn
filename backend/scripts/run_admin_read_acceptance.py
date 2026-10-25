"""Pinned development read acceptance; no fixture creation or mutation endpoints.

Optional --staff-token-file is an owner-supplied existing access token, never a
generated token/login/refresh credential. Evidence never contains token or rows.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
READS = {
    "current_security": "/api/v1/me/staff-security",
    "products": "/api/v1/admin/products?limit=1",
    "orders_metadata": "/api/v1/admin/order-metadata?limit=1",
    "support_list": "/api/v1/admin/support-case-metadata?limit=1",
    "notifications": "/api/v1/admin/notification-outbox?limit=1",
    "privacy_metadata": "/api/v1/admin/privacy/exports?limit=1",
    "finance_metadata": "/api/v1/admin/finance/sheet-sync?limit=1",
    "storage_metadata": "/api/v1/admin/storage/artifacts?limit=1",
    "trends": "/api/v1/admin/dashboard/trends?display_timezone=UTC",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8030")
    parser.add_argument("--output", type=Path, required=True)
    token_source = parser.add_mutually_exclusive_group()
    token_source.add_argument("--staff-token-file", type=Path)
    token_source.add_argument("--staff-token-stdin", action="store_true", help="Existing verified session transported in memory; never echoed or saved")
    parser.add_argument("--session-only", action="store_true", help="Skip previously completed catalogs and anonymous checks")
    parser.add_argument("--read", action="append", default=[], choices=[k for k in READS if k not in {"current_security", "support_list"}], help="Explicit bounded authenticated SELECT-only endpoint; requires existing owner-supplied MFA token")
    args = parser.parse_args()
    if args.session_only and not (args.staff_token_file or args.staff_token_stdin):
        parser.error("--session-only requires an existing private session input")
    assert args.origin == "http://127.0.0.1:8030", "Existing development backend only"
    env = dotenv_values(ROOT / "backend/.env", interpolate=False)
    assert env.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") == f"https://{PROJECT}.supabase.co"
    result = {"assessment_date": "2026-10-25", "checked_at_utc": datetime.now(UTC).isoformat(), "project": PROJECT, "read_only": True, "catalog": {}, "http": {}, "staff": {"supplied": bool(args.staff_token_file or args.staff_token_stdin)}}
    for key in ("SAFERETURN_DASHBOARD_ENABLED", "SAFERETURN_PRINT_TEMPLATE_MANAGEMENT_ENABLED", "SAFERETURN_STAFF_DIRECTORY_ENABLED", "SAFERETURN_SUPPORT_DEV_ENABLED"):
        result.setdefault("configured_flags", {})[key] = str(os.environ.get(key, env.get(key) or "false")).lower() in {"true", "1"}
    result["auth_configuration"] = {"expected_project": True, "symmetric_jwt_fallback": False, "session_input_in_config": any(v and any(s in k for s in ("ACCESS_TOKEN", "SESSION_TOKEN", "STORAGE_STATE", "COOKIE")) for k, v in env.items())}
    tables = ["staff_roles", "products", "orders", "support_cases", "support_case_events", "notification_outbox", "privacy_exports", "finance_sheet_sync", "print_artifacts", "payment_evidence", "audit_events"]
    helpers = ["sr_account_session_state", "sr_is_staff", "sr_dashboard_trend", "sr_export_list", "sr_export_authorized", "sr_retention_held"]
    queries = {
        "revision": "SELECT version_num FROM public.alembic_version",
        "runtime_roles": "SELECT rolname,rolsuper,rolbypassrls,rolcreaterole FROM pg_roles WHERE rolname IN ('safereturn_api','safereturn_worker') ORDER BY rolname",
        "table_security": "SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,pg_get_userbyid(c.relowner) AS owner,has_table_privilege('safereturn_api',c.oid,'SELECT') AS api_select FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY(%s) ORDER BY c.relname",
        "policy_metadata": "SELECT tablename,policyname,cmd,roles,permissive FROM pg_policies WHERE schemaname='public' AND tablename=ANY(%s) ORDER BY tablename,policyname",
        "helper_security": "SELECT p.proname,p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner) AS owner,has_function_privilege('safereturn_api',p.oid,'EXECUTE') AS api_execute FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname=ANY(%s) ORDER BY p.proname",
    }
    # Existing runtime first; privileged configured connection only for catalog
    # revision/ACL metadata if the runtime cannot inspect Alembic's version table.
    for key in (() if args.session_only else ("SAFERETURN_DATABASE_URL", "SAFERETURN_MIGRATION_DATABASE_URL")):
        if not env.get(key):
            continue
        target = urlsplit(env[key].replace("postgresql+psycopg:", "postgresql:"))
        assert target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com" and target.port == 5432 and target.path == "/postgres"
        assert unquote(target.username or "").endswith("." + PROJECT)
        ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
        assert hashlib.sha256(ca.read_bytes()).hexdigest() == "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
        entry = {"connection_kind": "runtime" if key == "SAFERETURN_DATABASE_URL" else "catalog_inspection", "tls": "verify-full", "queries": {}}
        try:
            with psycopg.connect(host=target.hostname, port=target.port, dbname="postgres", user=unquote(target.username), password=unquote(target.password), sslmode="verify-full", sslrootcert=str(ca), connect_timeout=10, autocommit=True, row_factory=dict_row) as connection:
                connection.execute("BEGIN READ ONLY")
                connection.execute("SET LOCAL statement_timeout='5000ms'")
                for name, sql in queries.items():
                    connection.execute("SAVEPOINT acceptance_read")
                    try:
                        params = (helpers if name == "helper_security" else tables, ) if "%s" in sql else None
                        entry["queries"][name] = connection.execute(sql, params).fetchall()
                    except psycopg.Error as error:
                        connection.execute("ROLLBACK TO SAVEPOINT acceptance_read")
                        entry["queries"][name] = {"sqlstate": error.sqlstate, "unavailable": True}
                    connection.execute("RELEASE SAVEPOINT acceptance_read")
                connection.execute("ROLLBACK")
                entry["reachable"] = True
        except psycopg.Error as error:
            entry.update(reachable=False, error_type=type(error).__name__)
            message = str(error).lower()
            entry["failure_category"] = next((category for category, terms in {"name_resolution": ["could not translate", "getaddrinfo", "name or service"], "tls_verification": ["certificate verify", "root certificate"], "connection_refused": ["refused"], "timeout": ["timeout", "timed out"], "authentication": ["password authentication", "tenant or user"]}.items() if any(term in message for term in terms)), "connection_unavailable")
        result["catalog"][entry["connection_kind"]] = entry
        if isinstance(entry["queries"].get("revision"), list):
            break
    with httpx.Client(base_url=args.origin, timeout=15, follow_redirects=False, trust_env=False) as client:
        for name, path in ({} if args.session_only else {"liveness": "/api/v1/health/live", **READS}).items():
            try:
                response = client.get(path)
                result["http"][name] = {"status": response.status_code, "expected": 200 if name == "liveness" else 401, "no_store": "no-store" in response.headers.get("cache-control", ""), "exact_liveness": response.json() == {"status": "ok"} if name == "liveness" else None}
            except (httpx.HTTPError, ValueError) as error:
                result["http"][name] = {"error_type": type(error).__name__}
        if args.staff_token_file or args.staff_token_stdin:
            token = sys.stdin.read(16385).strip() if args.staff_token_stdin else args.staff_token_file.read_text().strip()
            assert token.count(".") == 2 and len(token) < 16384
            response = client.get(READS["current_security"], headers={"Authorization": "Bearer " + token})
            result["staff"]["security_status"] = response.status_code
            if response.status_code == 200:
                security = response.json()
                assert set(security) == {"roles", "mfa_verified", "capabilities"}
                result["staff"].update(roles=security["roles"], mfa_verified=security["mfa_verified"], capabilities=security["capabilities"])
                result["staff"]["reads"] = {}
                if security["mfa_verified"] is True:
                    for name in args.read:
                        observed = client.get(READS[name], headers={"Authorization": "Bearer " + token})
                        receipt = {"status": observed.status_code, "no_store": "no-store" in observed.headers.get("cache-control", "")}
                        if observed.status_code == 200:
                            body = observed.json()
                            receipt["object_response"] = isinstance(body, dict)
                            receipt["attachment_rejected"] = "content-disposition" not in observed.headers
                            if isinstance(body, dict):
                                receipt["response_fields"] = sorted(body)
                                items = body.get("items")
                                receipt["bounded_items"] = isinstance(items, list) and len(items) <= 1 if name != "trends" else None
                                receipt["row_field_names"] = sorted(items[0]) if isinstance(items, list) and items and isinstance(items[0], dict) else []
                                cursor = body.get("next_cursor")
                                if isinstance(cursor, str) and 0 < len(cursor) <= 2000:
                                    page_url = httpx.URL(READS[name]).copy_add_param("cursor", cursor)
                                    page = client.get(page_url, headers={"Authorization": "Bearer " + token})
                                    receipt["cursor_page_status"] = page.status_code
                        result["staff"]["reads"][name] = receipt
                # No enumeration or mutation-adjacent reads without verified MFA.
                # Audit/detail/history emit access-audit writes and are not run.
                result["staff"]["next_step"] = "Named owner-approved fixture manifest and endpoint-specific schema/RLS/pagination checks; no automatic admission"
    result["not_executed"] = ["authenticated RLS/pagination/redaction without supplied genuine staff session and safe fixture evidence", "Audit API-100 and all Support read access-audit writes", "all prohibited/quarantined APIs", "all mutations/providers", "migration0044"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps({"evidence": str(args.output), "catalog_reachable": any(e.get("reachable") for e in result["catalog"].values()), "staff_session_supplied": result["staff"]["supplied"], "http": result["http"]}, indent=2))


if __name__ == "__main__":
    main()
