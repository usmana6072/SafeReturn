"""Offline SQL DDL projections/source inspection, never PostgreSQL acceptance."""

import ast
import json
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).parents[1] / "alembic/versions"
SQL = (ROOT / "0035_public_abuse_intake.sql").read_text(encoding="utf-8")


@pytest.fixture
def projected():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
    db.create_function("clock_timestamp", 0, lambda: "2026-10-21T00:00:00Z")
    db.create_function(
        "octet_length", 1, lambda v: len(v.encode() if isinstance(v, str) else v)
    )
    db.create_function(
        "regexp",
        2,
        lambda pattern, value: (
            bool(re.fullmatch(pattern, value)) if value is not None else None
        ),
    )
    db.create_function(
        "jsonb_typeof",
        1,
        lambda v: "object" if isinstance(json.loads(v), dict) else "array",
    )
    db.execute("CREATE TABLE support_cases(id uuid PRIMARY KEY)")
    ddl = SQL.split("CREATE FUNCTION public.sr_abuse_gate")[0].replace("public.", "")
    ddl = ddl.replace(
        "DEFAULT gen_random_uuid()", "DEFAULT (gen_random_uuid())"
    ).replace("DEFAULT clock_timestamp()", "DEFAULT (clock_timestamp())")
    ddl = re.sub(r"(\w+)~('[^']*')", r"\1 REGEXP \2", ddl)
    db.executescript(ddl)
    db.execute(
        "INSERT INTO abuse_intake_policies(policy_id,version,body,sha256,effective_at,expires_at) VALUES('p',1,'{}',?,'2026-10-20','2026-10-22')",
        ("a" * 64,),
    )
    db.execute("INSERT INTO support_cases VALUES('c')")
    yield db
    db.close()


def insert_report(db, report="r", case="c"):
    db.execute(
        """INSERT INTO abuse_reports(report_id,case_id,category,context_ciphertext,context_key_version,duplicate_hash,policy_id,policy_version,hmac_key_version,consent_version)
     VALUES(?,?,'spam',?,1,?,'p',1,1,'abuse-report-v1')""",
        (report, case, b"x" * 32, "b" * 64),
    )


def test_projection_unique_case_linkage_context_and_consent(projected):
    insert_report(projected)
    assert projected.execute(
        "SELECT status,consent_accepted,consent_at FROM abuse_reports"
    ).fetchone() == ("received", 1, "2026-10-21T00:00:00Z")
    with pytest.raises(sqlite3.IntegrityError):
        insert_report(projected, "r2")
    with pytest.raises(sqlite3.IntegrityError):
        insert_report(projected, "r2", "missing")
    with pytest.raises(sqlite3.IntegrityError):
        projected.execute("UPDATE abuse_reports SET context_ciphertext=x'00'")
    with pytest.raises(sqlite3.IntegrityError):
        projected.execute("UPDATE abuse_reports SET consent_accepted=false")


def test_projection_receipt_proof_uniqueness_and_policy_fk(projected):
    insert_report(projected)
    args = ("c" * 64, "d" * 64, "e" * 64)
    sql = "INSERT INTO abuse_report_receipts(scope_hash,retry_hash,body_hash,report_id,policy_id,policy_version,retention_until) VALUES(?,?,?,'r','p',1,'2026-10-22')"
    projected.execute(sql, args)
    with pytest.raises(sqlite3.IntegrityError):
        projected.execute(sql, args)
    proof = "INSERT INTO abuse_report_proofs(proof_hash,policy_id,policy_version,retention_until) VALUES(?,'p',1,'2026-10-22')"
    projected.execute(proof, ("f" * 64,))
    with pytest.raises(sqlite3.IntegrityError):
        projected.execute(proof, ("f" * 64,))
    with pytest.raises(sqlite3.IntegrityError):
        projected.execute("DELETE FROM abuse_intake_policies")


def test_projection_final_rollback_preserves_committed_attempt(projected):
    projected.execute(
        "INSERT INTO abuse_report_attempts(kind,scope_hash,policy_id,policy_version,retention_until) VALUES('peer',?,'p',1,'2026-10-22')",
        ("a" * 64,),
    )
    projected.commit()
    insert_report(projected)
    projected.rollback()
    assert projected.execute("SELECT count(*) FROM abuse_reports").fetchone()[0] == 0
    assert (
        projected.execute("SELECT count(*) FROM abuse_report_attempts").fetchone()[0]
        == 1
    )


def test_real_source_chain_no_policy_seeds_no_enforcement_and_narrow_grants():
    tree = ast.parse((ROOT / "0035_public_abuse_intake.py").read_text())
    assignments = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
    }
    assert assignments["down_revision"] == "0034_print_template_publication"
    assert "INSERT INTO public.abuse_intake_policies" not in SQL
    assert (
        "GRANT INSERT" not in SQL
        and "GRANT UPDATE" not in SQL
        and "GRANT SELECT" not in SQL
    )
    assert (
        "qr_codes" not in SQL
        and "finder_messages" not in SQL
        and "notification_outbox" not in SQL
    )
    assert "actor_kind='anonymous'" in SQL and "sr_support_change_v34" in SQL
    assert (
        "next_status IN('resolved','closed')" in SQL
        and "NEW.status IN('resolved','closed')" in SQL
    )
    for table in (
        "abuse_reports",
        "abuse_report_events",
        "abuse_report_receipts",
        "abuse_report_proofs",
        "abuse_report_attempts",
    ):
        assert re.search(r"CREATE TRIGGER [^;]+ ON public\." + table, SQL)
    assert "CREATE POLICY sr_abuse_case_scope" in SQL
    downgrade = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"
    )
    assert "DROP" not in ast.unparse(downgrade)
    # Lexical inspection only: not a SQL/PLpgSQL parser or ACL/trigger execution.
    plain = re.sub(r"'(?:''|[^'])*'", "''", re.sub(r"--[^\n]*", "", SQL))
    depth = 0
    for c in plain:
        depth += (c == "(") - (c == ")")
        assert depth >= 0
    assert depth == 0 and SQL.count("$$") % 2 == 0
