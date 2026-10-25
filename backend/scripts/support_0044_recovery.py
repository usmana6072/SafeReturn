"""Read-only 0044 recovery assessment for the pinned development project.

Never applies/downgrades migrations, invokes commands, or repairs data. A subject
UUID is required before reading exception/receipt/grant state after installation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "fhuxryfkfrvycsojkzvq"
CHANGE = "SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba"
PINS = {
    "backend/alembic/versions/0044_support_dev_exception.sql":
        "17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d",
    "backend/alembic/versions/0044_support_dev_exception.py":
        "67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30",
}


def assess(conn, subject):
    result = {"project": PROJECT, "read_only": True}
    revisions = conn.execute(
        "SELECT version_num FROM public.alembic_version"
    ).fetchall()
    result["installed_revisions"] = [row["version_num"] for row in revisions]
    objects = conn.execute(
        """SELECT to_regclass('public.support_dev_exception') IS NOT NULL AS exception,
        to_regclass('public.support_dev_receipts') IS NOT NULL AS receipts,
        EXISTS(SELECT 1 FROM pg_roles WHERE rolname='safereturn_support_provisioner')
          AS provisioner,
        EXISTS(SELECT 1 FROM pg_roles WHERE rolname='safereturn_support_command')
          AS command_role,
        (SELECT count(*) FROM pg_policies WHERE schemaname='public' AND
          (tablename,policyname) IN (
          ('support_cases','sr_support_dev_case_fence'),
          ('support_case_events','sr_support_dev_history_fence'))) AS fence_count"""
    ).fetchone()
    result["objects"] = objects
    revision = result["installed_revisions"]
    if revision == ["0043_standalone_activation"]:
        unexpected = (
            objects["exception"] or objects["receipts"]
            or objects["provisioner"] or objects["command_role"]
            or objects["fence_count"] != 0
        )
        result["recovery_state"] = (
            "UNEXPECTED_PARTIAL_STATE_STOP" if unexpected else "0044_NOT_INSTALLED"
        )
        return result
    if revision != ["0044_support_dev_exception"] or not (
        objects["exception"] and objects["receipts"]
        and objects["provisioner"] and objects["fence_count"] == 2
    ):
        result["recovery_state"] = "UNEXPECTED_SCHEMA_STATE_STOP"
        return result
    if subject is None:
        result["recovery_state"] = "SUBJECT_REQUIRED_NO_DOMAIN_ROWS_READ"
        return result
    row = conn.execute(
        """SELECT e.subject_id,e.grant_id,e.approval_id,e.packet_digest,
        e.idempotency_key,e.created_at,e.expires_at,e.revoked_at,
        clock_timestamp() AS database_now,
        r.user_id=e.subject_id AND r.role='support' AS correct_grant,
        r.revoked_at AS grant_revoked_at,
        (SELECT count(*) FROM public.support_dev_receipts x
          WHERE x.subject_id=e.subject_id AND x.action='grant') AS grant_receipts,
        (SELECT count(*) FROM public.support_dev_receipts x
          WHERE x.subject_id=e.subject_id AND x.action='revoke') AS revoke_receipts,
        (SELECT count(*) FROM public.support_dev_receipts x
          JOIN public.audit_events a ON a.id=x.audit_id
          WHERE x.subject_id=e.subject_id AND a.target_id=e.grant_id
            AND a.request_id=%s
            AND a.actor_user_id=e.subject_id
            AND a.action='support.development.' ||
              CASE x.action WHEN 'grant' THEN 'granted' ELSE 'revoked' END)
          AS linked_audits
        FROM public.support_dev_exception e
        LEFT JOIN public.staff_roles r ON r.id=e.grant_id
        WHERE e.change_id=%s AND e.subject_id=%s""",
        (CHANGE, CHANGE, subject),
    ).fetchone()
    if row is None:
        # An absent requested UUID is not proof the singleton is unused.
        consumed = conn.execute(
            "SELECT EXISTS(SELECT 1 FROM public.support_dev_exception "
            "WHERE change_id=%s) AS consumed", (CHANGE,),
        ).fetchone()["consumed"]
        result["recovery_state"] = (
            "OTHER_SUBJECT_CONSUMED_STOP" if consumed
            else "NO_EXCEPTION_RECORDED_NO_GRANT_AUTHORIZED"
        )
        return result
    result["exception"] = row
    revoked = row["revoked_at"] is not None
    if (
        not row["correct_grant"]
        or row["grant_receipts"] != 1
        or row["revoke_receipts"] != int(revoked)
        or row["linked_audits"] != 1 + int(revoked)
        or (revoked and row["grant_revoked_at"] is None)
    ):
        result["recovery_state"] = "INCONSISTENT_HISTORY_STOP"
    elif revoked:
        result["recovery_state"] = "REVOKED_HISTORY_RETAINED"
    elif row["grant_revoked_at"] is not None:
        result["recovery_state"] = "GRANT_REVOKED_EXCEPTION_STAMP_PENDING"
    elif row["expires_at"] <= row["database_now"]:
        result["recovery_state"] = "EXPIRED_HISTORY_STAMP_PENDING"
    else:
        # This is recorded grant state, never Auth/MFA/backend readiness proof.
        result["recovery_state"] = "RECORDED_UNEXPIRED_NOT_ACCESS_ATTESTATION"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject-id", type=UUID)
    parser.add_argument(
        "--inspect", action="store_true",
        help="explicitly permit read-only database assessment; otherwise pins only",
    )
    args = parser.parse_args(argv)
    try:
        pins_match = all(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
            for name, expected in PINS.items()
        )
        if not pins_match:
            print("STOP: REVIEWED_MIGRATION_HASH_MISMATCH")
            return 2
        if not args.inspect:
            print("HASH_PINS_MATCH; no database connection; use --inspect for read-only assessment")
            return 0
        env = dotenv_values(ROOT / "backend/.env", interpolate=False)
        if env.get("SAFERETURN_SUPABASE_URL", "").rstrip("/") != (
            f"https://{PROJECT}.supabase.co"
        ):
            raise ValueError("wrong_auth_project")
        target = urlsplit(
            env["SAFERETURN_MIGRATION_DATABASE_URL"].replace(
                "postgresql+psycopg:", "postgresql:",
            )
        )
        if not (
            target.scheme in {"postgres", "postgresql"}
            and target.hostname == "aws-0-ap-northeast-2.pooler.supabase.com"
            and target.port == 5432 and target.path == "/postgres"
            and unquote(target.username or "").endswith("." + PROJECT)
            and target.password
        ):
            raise ValueError("wrong_database_project")
        ca = ROOT / "tmp/phase9-cloud-audit/supabase-verified-root.pem"
        if hashlib.sha256(ca.read_bytes()).hexdigest() != (
            "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
        ):
            raise ValueError("wrong_ca")
        for name in list(os.environ):
            if name.startswith("PG"):
                del os.environ[name]
        with psycopg.connect(
            host=target.hostname, port=5432, dbname="postgres",
            user=unquote(target.username), password=unquote(target.password),
            sslmode="verify-full", sslrootcert=str(ca), connect_timeout=5,
            autocommit=True, row_factory=dict_row,
            options="-c default_transaction_read_only=on -c search_path=pg_catalog "
                    "-c statement_timeout=8000 -c lock_timeout=2000 "
                    "-c idle_in_transaction_session_timeout=15000",
            application_name="support_0044_recovery_inspection",
        ) as conn:
            conn.execute("BEGIN READ ONLY")
            try:
                if not conn.pgconn.ssl_in_use or conn.execute(
                    "SELECT current_setting('transaction_read_only') AS ro"
                ).fetchone()["ro"] != "on":
                    raise ValueError("unsafe_connection")
                result = assess(conn, args.subject_id)
            finally:
                conn.execute("ROLLBACK")
        print(json.dumps(result, indent=2, default=str))
        return 0 if "STOP" not in result["recovery_state"] else 2
    except (OSError, ValueError, KeyError, psycopg.Error) as exc:
        print(json.dumps({
            "outcome": "STOP_INSPECTION_FAILED_NO_REPAIR_ATTEMPTED",
            "error_class": type(exc).__name__,
            "sqlstate": getattr(exc, "sqlstate", None),
        }))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
