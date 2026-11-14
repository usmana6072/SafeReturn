"""Offline DDL projections only: no PL/pgSQL, ACL/RLS or PostgreSQL MVCC claim."""

import ast
import json
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).parents[1] / "alembic/versions"
SQL = (ROOT / "0034_print_template_publication.sql").read_text(encoding="utf-8")


@pytest.fixture
def projected():
    db = sqlite3.connect(":memory:")
    db.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
    db.create_function("octet_length", 1, lambda s: len(s.encode()))
    db.create_function(
        "jsonb_typeof",
        1,
        lambda s: "object" if isinstance(json.loads(s), dict) else "array",
    )
    for name in (
        "print_template_variant_bindings",
        "template_registry_sources",
        "order_use_print_specs",
        "template_registry_orders",
    ):
        ddl = re.search(
            r"CREATE TABLE public\." + name + r" \([\s\S]*?\n\);", SQL
        ).group()
        ddl = (
            ddl.replace("public.", "")
            .replace("DEFAULT gen_random_uuid()", "DEFAULT (gen_random_uuid())")
            .replace("DEFAULT clock_timestamp()", "DEFAULT CURRENT_TIMESTAMP")
            .replace("spec::text", "spec")
        )
        db.executescript(ddl)
    index = (
        re.search(r"CREATE UNIQUE INDEX uq_template_active_binding[^;]+;", SQL)
        .group()
        .replace("public.", "")
    )
    db.executescript(index)
    lifecycle = re.search(
        r"ADD CONSTRAINT ck_template_revision_lifecycle CHECK\(([\s\S]*?)\);", SQL
    ).group(1)
    db.execute(
        "CREATE TABLE lifecycle(status TEXT NOT NULL,fingerprint_sha256 TEXT,published_at TEXT,approval_id TEXT,CHECK("
        + lifecycle
        + "))"
    )
    yield db
    db.close()


def test_projection_single_active_binding_retained_history_and_rollback(projected):
    db = projected
    db.execute(
        "INSERT INTO print_template_variant_bindings(binding_id,variant_id,tag_type,revision_id) VALUES('b1','v1','lost','r1')"
    )
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO print_template_variant_bindings(binding_id,variant_id,tag_type,revision_id) VALUES('b2','v1','lost','r2')"
        )
    db.rollback()
    db.execute(
        "UPDATE print_template_variant_bindings SET is_active=false WHERE binding_id='b1'"
    )
    db.execute(
        "INSERT INTO print_template_variant_bindings(binding_id,variant_id,tag_type,revision_id) VALUES('b2','v1','lost','r2')"
    )
    db.rollback()
    assert db.execute(
        "SELECT binding_id,is_active FROM print_template_variant_bindings"
    ).fetchall() == [("b1", 1)]


@pytest.mark.parametrize(
    "row,valid",
    [
        (("draft", None, None, None), True),
        (("pending_qa", "f", None, None), True),
        (("published", "f", "time", "approval"), True),
        (("retired", "f", "time", "approval"), True),
        (("published", "f", "time", None), False),
        (("pending_qa", "f", None, "approval"), False),
        (("draft", None, "time", None), False),
        (("retired", None, "time", "approval"), False),
    ],
)
def test_projection_lifecycle_requires_real_approval_reference(projected, row, valid):
    if valid:
        projected.execute("INSERT INTO lifecycle VALUES(?,?,?,?)", row)
    else:
        with pytest.raises(sqlite3.IntegrityError):
            projected.execute("INSERT INTO lifecycle VALUES(?,?,?,?)", row)


def test_projection_use_snapshot_unique_and_bounded(projected):
    db = projected
    db.execute("INSERT INTO order_use_print_specs VALUES('u1','{}','r1','a1')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO order_use_print_specs VALUES('u1','{}','r2','a2')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO order_use_print_specs VALUES('u2',?,'r2','a2')",
            (json.dumps({"large": "s" * 32768}),),
        )


def test_actual_pending_chain_and_narrow_non_destructive_rollback_inspection():
    tree = ast.parse((ROOT / "0034_print_template_publication.py").read_text())
    assigned = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
    }
    assert assigned["down_revision"] == "0033_print_template_drafts"
    downgrade = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"
    )
    assert "DROP" not in ast.unparse(downgrade)
    assert (
        "INSERT INTO public.template_people" not in SQL
        and "INSERT INTO public.template_authorities" not in SQL
    )
    # These are source inspection safeguards, not proof that the statements execute.
    for table in (
        "order_use_print_specs",
        "template_registry_orders",
        "template_revision_contributors",
        "template_authority_withdrawals",
    ):
        assert re.search(r"CREATE TRIGGER [^;]+ ON public\." + table, SQL)
    assert "GRANT INSERT" not in SQL and "GRANT UPDATE" not in SQL
    assert SQL.index("CREATE FUNCTION public.sr_template_lifecycle") < SQL.index(
        "GRANT EXECUTE ON FUNCTION public.sr_template_service"
    )
    assert (
        "sr_template_registry_gate(true)" in SQL
        and "pg_advisory_xact_lock_shared(51340001)" in SQL
    )
    assert "source_generation" in SQL and "t.lifecycle_status='retired'" in SQL
