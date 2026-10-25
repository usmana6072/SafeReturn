"""Phase 1 row checks/FKs in SQLite, plus static migration admission checks.

This does not execute PostgreSQL triggers, RLS, deferred checks or locks.
SQLite's compiler omits the cross-schema auth.users FK; that FK is not proved here.
"""

import ast
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.commerce import Product
from app.db.models import QRBatch, QRCode, StandaloneQRState


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
    connection.create_function("now", 0, lambda: "2026-10-22T00:00:00Z")
    connection.execute("CREATE TABLE tag_pairs(id TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO tag_pairs VALUES('legacy-pair')")
    connection.execute("CREATE TABLE product_categories(id TEXT PRIMARY KEY)")
    for model in (QRBatch, QRCode, StandaloneQRState, Product):
        connection.execute(
            str(CreateTable(model.__table__).compile(dialect=sqlite.dialect()))
        )
    # PostgreSQL partial-index predicates must be retained, not silently omitted
    # by SQLite's compiler (the production indexes use postgresql_where).
    for index in QRCode.__table__.indexes:
        connection.execute(
            str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        )
    connection.execute(
        "INSERT INTO qr_batches(id,batch_code,ecc_level) VALUES('legacy-batch','LEGACY','Q')"
    )
    connection.execute(
        "INSERT INTO qr_batches(id,batch_code,ecc_level,generation_mode,qr_type,requested_quantity) "
        "VALUES('standalone-batch','SINGLE','Q','standalone','lost',3)"
    )
    connection.execute(
        "INSERT INTO qr_batches(id,batch_code,ecc_level,generation_mode,qr_type,requested_quantity) "
        "VALUES('emergency-batch','EMERGENCY','Q','standalone','ice',1)"
    )
    yield connection
    connection.close()


def qr(db, **changes):
    values = {
        "id": str(uuid4()),
        "pair_id": None,
        "batch_id": "standalone-batch",
        "tag_type": "lost",
        "serial_number": str(uuid4()),
        "public_token": str(uuid4()),
        "ecc_level": "Q",
    }
    values.update(changes)
    columns = ",".join(values)
    placeholders = ",".join("?" for _ in values)
    db.execute(
        f"INSERT INTO qr_codes({columns}) VALUES({placeholders})",
        tuple(values.values()),
    )
    return values["id"]


def state(db, qid, **changes):
    values = {"qr_id": qid, **changes}
    columns = ",".join(values)
    placeholders = ",".join("?" for _ in values)
    db.execute(
        f"INSERT INTO standalone_qr_states({columns}) VALUES({placeholders})",
        tuple(values.values()),
    )


def test_legacy_and_standalone_rows_coexist_without_dummy_sibling(db):
    legacy = qr(db, pair_id="legacy-pair", batch_id=None)
    single = qr(db)
    state(db, single)
    assert db.execute(
        "SELECT pair_id,batch_id FROM qr_codes WHERE id=?", (legacy,)
    ).fetchone() == ("legacy-pair", None)
    assert (
        db.execute(
            "SELECT count(*) FROM qr_codes WHERE batch_id='standalone-batch'"
        ).fetchone()[0]
        == 1
    )


@pytest.mark.parametrize(
    "pair,batch", [(None, None), ("legacy-pair", "standalone-batch")]
)
def test_identity_requires_exactly_one_provenance(db, pair, batch):
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, pair_id=pair, batch_id=batch)


@pytest.mark.parametrize(
    "field,value", [("pair_id", "missing"), ("batch_id", "missing")]
)
def test_provenance_foreign_keys(db, field, value):
    changes = {"pair_id": None, "batch_id": "standalone-batch"}
    if field == "pair_id":
        changes["batch_id"] = None
    changes[field] = value
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, **changes)


@pytest.mark.parametrize("field", ["serial_number", "public_token"])
def test_identity_uniqueness_is_global_across_both_models(db, field):
    qr(db, pair_id="legacy-pair", batch_id=None, **{field: "global-value"})
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, **{field: "global-value"})


def test_current_legacy_pair_type_uniqueness_remains(db):
    qr(db, pair_id="legacy-pair", batch_id=None)
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, pair_id="legacy-pair", batch_id=None)
    qr(db, pair_id="legacy-pair", batch_id=None, tag_type="ice")
    # Multiple standalone identities of the same type are valid.
    qr(db)
    qr(db)


def test_standalone_replacement_is_not_enabled_implicitly(db):
    predecessor = qr(db)
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, replaces_qr_id=predecessor)
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, is_current=False)


def test_legacy_replacement_row_shape_and_current_index_preserved(db):
    old = qr(
        db,
        pair_id="legacy-pair",
        batch_id=None,
        is_current=False,
        public_status="revoked",
        revoked_at="2026-10-22",
    )
    qr(db, pair_id="legacy-pair", batch_id=None, replaces_qr_id=old)
    with pytest.raises(sqlite3.IntegrityError):
        qr(db, pair_id="legacy-pair", batch_id=None, replaces_qr_id=old)


@pytest.mark.parametrize(
    "mode,tag,quantity",
    [
        ("legacy_pair", "lost", None),
        ("legacy_pair", None, 2),
        ("standalone", None, 1),
        ("standalone", "emergency", 1),
        ("standalone", "lost", None),
        ("standalone", "lost", 0),
        ("standalone", "ice", 1001),
        ("unknown", None, None),
    ],
)
def test_batch_generation_shape_cannot_pass_with_null_or_wrong_type(
    db, mode, tag, quantity
):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO qr_batches(batch_code,ecc_level,generation_mode,qr_type,requested_quantity) VALUES(?,'Q',?,?,?)",
            (str(uuid4()), mode, tag, quantity),
        )


def test_one_state_per_qr_and_state_requires_existing_qr(db):
    qid = qr(db)
    state(db, qid)
    with pytest.raises(sqlite3.IntegrityError):
        state(db, qid)
    with pytest.raises(sqlite3.IntegrityError):
        state(db, "missing")


@pytest.mark.parametrize(
    "changes",
    [
        {"ownership_status": "active"},
        {
            "ownership_status": "active",
            "owner_user_id": "owner",
            "activated_at": "2026-10-22",
        },
        {
            "ownership_status": "active",
            "owner_user_id": "owner",
            "inventory_status": "allocated",
        },
        {"owner_user_id": "owner"},
        {"activated_at": "2026-10-22"},
        {"ownership_status": "revoked"},
        {"revoked_at": "2026-10-22"},
        {"row_version": 0},
        {"inventory_status": "reserved"},
    ],
)
def test_invalid_independent_owner_states_rejected(db, changes):
    with pytest.raises(sqlite3.IntegrityError):
        state(db, qr(db), **changes)


def test_row_checks_allow_independent_owner_shapes(db):
    lost = qr(db)
    emergency = qr(db, tag_type="ice", batch_id="emergency-batch")
    state(
        db,
        lost,
        inventory_status="allocated",
        ownership_status="active",
        owner_user_id="owner",
        activated_at="2026-10-22",
    )
    state(db, emergency)
    assert db.execute(
        "SELECT owner_user_id,ownership_status FROM standalone_qr_states WHERE qr_id=?",
        (emergency,),
    ).fetchone() == (None, "unclaimed")


@pytest.mark.parametrize("tag", [None, "lost", "ice"])
def test_product_type_does_not_force_legacy_backfill(db, tag):
    db.execute(
        "INSERT INTO products(slug,name,qr_type,price_per_copy) VALUES(?,?,?,?)",
        (str(uuid4()), "Product", tag, "12.30"),
    )


def test_unknown_product_type_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO products(slug,name,qr_type) VALUES('wrong','Product','both')"
        )


def test_migration_graph_and_static_closed_admission():
    directory = Path(__file__).parents[1] / "alembic/versions"
    parents = {}
    for path in directory.glob("*.py"):
        assignments = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                assignments.update(
                    {
                        target.id: node.value.value
                        for target in node.targets
                        if isinstance(target, ast.Name)
                    }
                )
        parents[assignments["revision"]] = assignments["down_revision"]
    assert set(parents) - set(parents.values()) == {"0043_standalone_activation"}
    seen = set()
    current = "0043_standalone_activation"
    while current is not None:
        assert current not in seen
        seen.add(current)
        current = parents[current]
    assert seen == set(parents)
    sql = (directory / "0037_independent_qr_foundation.sql").read_text(encoding="utf-8")
    assert "standalone_qr_states ENABLE ROW LEVEL SECURITY" in sql
    assert not any(line.lstrip().startswith("GRANT ") for line in sql.splitlines())
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "IF pid IS NULL THEN RETURN NULL" in sql
    assert "IF n<>2 THEN RAISE EXCEPTION" in sql
    assert "qr_codes.pair_id IS NOT NULL;" in sql


def test_public_projection_changes_only_legacy_admission_filter():
    directory = Path(__file__).parents[1] / "alembic/versions"
    old = (directory / "0014_public_finder_messages.py").read_text(encoding="utf-8")
    new = (directory / "0037_independent_qr_foundation.sql").read_text(encoding="utf-8")
    marker = "CREATE OR REPLACE FUNCTION public.sr_public_qr_projection"
    old = old[old.index(marker) :]
    old = old[: old.index("END $$;") + len("END $$;")]
    new = new[new.index(marker) :].strip()
    assert new.replace(" AND qr_codes.pair_id IS NOT NULL;", ";", 1) == old
