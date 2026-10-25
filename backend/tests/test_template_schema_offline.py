"""SQLite projection of additive DDL constraints, not a PostgreSQL rehearsal."""

import json
import re
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from test_print_templates import content

from app.core.template_content import Content


@pytest.fixture
def schema():
    sql = (
        Path(__file__).parents[1] / "alembic/versions/0033_print_template_drafts.sql"
    ).read_text()
    ddl = sql.split("ALTER TABLE public.print_templates ENABLE ROW LEVEL SECURITY;")[0]
    ddl = ddl.replace("public.", "").replace("auth.users", "staff_users")
    ddl = ddl.replace("DEFAULT gen_random_uuid()", "DEFAULT (gen_random_uuid())")
    ddl = ddl.replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP").replace(
        "DEFAULT clock_timestamp()", "DEFAULT CURRENT_TIMESTAMP"
    )
    ddl = ddl.replace("content::text", "content")
    ddl = re.sub(r"(\w+) ~ ('[^']*')", r"\1 REGEXP \2", ddl)
    # SQLite cannot add a named CHECK after creation; emulate the validator with
    # the production Python DTO. This does not execute the PL/pgSQL validator.
    ddl = ddl.replace(
        "content jsonb NOT NULL",
        "content jsonb NOT NULL CHECK (sr_template_content_valid(content))",
    )
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
    db.create_function("char_length", 1, len)
    db.create_function(
        "regexp",
        2,
        lambda pattern, value: (
            None if value is None else re.search(pattern, value) is not None
        ),
    )
    db.create_function("octet_length", 1, lambda value: len(value.encode()))
    db.create_function(
        "jsonb_typeof",
        1,
        lambda value: "object" if isinstance(json.loads(value), dict) else "array",
    )

    def valid(value):
        try:
            Content.model_validate_json(value)
            return 1
        except ValueError:
            return 0

    db.create_function("sr_template_content_valid", 1, valid)
    db.execute("CREATE TABLE staff_users(id uuid PRIMARY KEY)")
    db.execute("INSERT INTO staff_users VALUES(?)", (str(UUID(int=1)),))
    db.executescript(ddl)
    yield db
    db.close()


def insert_template(db, key="synthetic-key"):
    tid = str(uuid4())
    db.execute(
        "INSERT INTO print_templates(template_id,key,name,purpose,created_by) VALUES(?,?,'Synthetic','lost',?)",
        (tid, key, str(UUID(int=1))),
    )
    return tid


def insert_revision(db, tid, version=1):
    rid = str(uuid4())
    db.execute(
        "INSERT INTO print_template_revisions(revision_id,template_id,version,content,version_note,created_by,updated_by) VALUES(?,?,?,?,?,?,?)",
        (
            rid,
            tid,
            version,
            json.dumps(content()),
            "Synthetic draft",
            str(UUID(int=1)),
            str(UUID(int=1)),
        ),
    )
    return rid


def test_offline_duplicate_key_and_case_sensitive_namespace(schema):
    insert_template(schema)
    with pytest.raises(sqlite3.IntegrityError):
        insert_template(schema)
    insert_template(schema, "Synthetic-key")
    assert schema.execute("SELECT count(*) FROM print_templates").fetchone()[0] == 2


def test_offline_single_draft_version_and_parent_constraints(schema):
    tid = insert_template(schema)
    rid = insert_revision(schema, tid)
    with pytest.raises(sqlite3.IntegrityError):
        insert_revision(schema, tid, 2)
    with pytest.raises(sqlite3.IntegrityError):
        insert_revision(schema, str(uuid4()))
    with pytest.raises(sqlite3.IntegrityError):
        schema.execute(
            "UPDATE print_template_revisions SET status='pending_qa' WHERE revision_id=?",
            (rid,),
        )
    schema.execute(
        "UPDATE print_template_revisions SET status='pending_qa',fingerprint_sha256=?,row_version=row_version+1 WHERE revision_id=?",
        ("a" * 64, rid),
    )
    insert_revision(schema, tid, 2)
    with pytest.raises(sqlite3.IntegrityError):
        schema.execute("UPDATE print_template_revisions SET status='published'")
    with pytest.raises(sqlite3.IntegrityError):
        schema.execute("DELETE FROM print_templates WHERE template_id=?", (tid,))


def test_offline_transaction_rollback_keeps_no_partial_draft(schema):
    schema.commit()
    schema.execute("BEGIN")
    tid = insert_template(schema)
    insert_revision(schema, tid)
    schema.rollback()
    assert schema.execute("SELECT count(*) FROM print_templates").fetchone()[0] == 0
    assert (
        schema.execute("SELECT count(*) FROM print_template_revisions").fetchone()[0]
        == 0
    )
