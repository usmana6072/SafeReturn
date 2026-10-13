"""Real PostgreSQL migration and bypass tests; all DDL/data rolled back."""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.models import Base, ICEProfile, LostItemProfile, QRBatch, QRCode, TagPair
from app.db.session import Database


@pytest.fixture(scope="module")
def migrated():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Development PostgreSQL not configured")
    db = Database.from_settings(Settings(database_url=SecretStr(url)))
    try:
        with db.engine.connect() as connection, connection.begin():
            cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            cfg.attributes["connection"] = connection
            # Roll back even a partially failed initial migration.
            command.upgrade(cfg, "head")
            try:
                yield connection
            finally:
                connection.rollback()
    finally:
        db.close()


@pytest.fixture
def conn(migrated):
    savepoint = migrated.begin_nested()
    migrated.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    try:
        yield migrated
    finally:
        savepoint.rollback()


def pair(conn, *, children=True):
    suffix = uuid.uuid4().hex
    batch = conn.execute(
        text(
            "INSERT INTO qr_batches(batch_code,ecc_level) VALUES (:s,'Q') RETURNING id"
        ),
        {"s": suffix},
    ).scalar_one()
    pid = conn.execute(
        text(
            "INSERT INTO tag_pairs(pair_reference,batch_id) VALUES (:s,:b) RETURNING id"
        ),
        {"s": suffix, "b": batch},
    ).scalar_one()
    ids = {}
    if children:
        for kind in ("lost", "ice"):
            ids[kind] = qr(conn, pid, kind)
    return pid, ids


def qr(conn, pid, kind, **extra):
    suffix = uuid.uuid4().hex
    return conn.execute(
        text(
            "INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,is_current,replaces_qr_id) VALUES (:p,:k,:s,:s,'Q',:current,:old) RETURNING id"
        ),
        {
            "p": pid,
            "k": kind,
            "s": suffix,
            "current": extra.get("current", True),
            "old": extra.get("old"),
        },
    ).scalar_one()


def validate(conn):
    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_migration_metadata_and_repeat(conn):
    assert (
        conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        == ScriptDirectory.from_config(
            Config(str(Path(__file__).parents[2] / "alembic.ini"))
        ).get_current_head()
    )
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        if table.schema == "auth":
            continue
        actual = inspector.get_columns(table.name)
        assert {c["name"] for c in actual} == set(table.c.keys())
        assert all(c["nullable"] == table.c[c["name"]].nullable for c in actual)
    assert (
        conn.execute(
            text(
                "SELECT count(*) FROM pg_constraint WHERE conname IN ('sr_pair_exactly_two','sr_qr_exactly_two') AND condeferrable AND condeferred"
            )
        ).scalar_one()
        == 2
    )
    assert (
        conn.execute(
            text(
                "SELECT count(*) FROM pg_class WHERE relname IN ('ice_profiles','pair_activation_credentials') AND relrowsecurity"
            )
        ).scalar_one()
        == 2
    )
    assert conn.execute(
        text(
            "SELECT has_table_privilege('anon','public.ice_profiles','SELECT'),has_table_privilege('authenticated','public.pair_activation_credentials','INSERT')"
        )
    ).one() == (False, False)


@pytest.mark.parametrize("kind", [None, "lost"])
def test_missing_current_tag_rejected_at_transaction_end(conn, kind):
    pid, _ = pair(conn, children=False)
    if kind:
        qr(conn, pid, kind)
    with pytest.raises(IntegrityError):
        validate(conn)


@pytest.mark.parametrize(
    "violation", ["duplicate", "type", "token", "delete", "demote", "identity"]
)
def test_direct_sql_cannot_break_current_pair(conn, violation):
    pid, ids = pair(conn)
    validate(conn)
    conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    with pytest.raises(IntegrityError):
        if violation == "duplicate":
            qr(conn, pid, "lost")
        elif violation == "type":
            qr(conn, pid, "other")
        elif violation == "token":
            conn.execute(
                text(
                    "UPDATE qr_codes SET public_token=(SELECT public_token FROM qr_codes WHERE id=:ice) WHERE id=:lost"
                ),
                ids,
            )
        elif violation == "delete":
            conn.execute(text("DELETE FROM qr_codes WHERE id=:lost"), ids)
        elif violation == "demote":
            conn.execute(
                text("UPDATE qr_codes SET is_current=false WHERE id=:lost"), ids
            )
        else:
            conn.execute(text("UPDATE qr_codes SET tag_type='ice' WHERE id=:lost"), ids)
        validate(conn)


def test_atomic_replacement_retains_history_and_profile(conn):
    pid, ids = pair(conn)
    conn.execute(
        text(
            "INSERT INTO lost_item_profiles(qr_id,item_label) VALUES (:lost,'original')"
        ),
        ids,
    )
    conn.execute(
        text(
            "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:lost"
        ),
        ids,
    )
    new = qr(conn, pid, "lost", old=ids["lost"])
    conn.execute(
        text(
            "INSERT INTO lost_item_profiles(qr_id,item_label) VALUES (:id,'replacement')"
        ),
        {"id": new},
    )
    validate(conn)
    assert (
        conn.execute(
            text("SELECT count(*) FROM qr_codes WHERE pair_id=:p"), {"p": pid}
        ).scalar_one()
        == 3
    )
    assert (
        conn.execute(
            text("SELECT item_label FROM lost_item_profiles WHERE qr_id=:lost"), ids
        ).scalar_one()
        == "original"
    )


def test_cross_pair_replacement_rejected(conn):
    _, first = pair(conn)
    pid, second = pair(conn)
    conn.execute(
        text(
            "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id IN (:a,:b)"
        ),
        {"a": first["lost"], "b": second["lost"]},
    )
    with pytest.raises(IntegrityError):
        qr(conn, pid, "lost", old=first["lost"])


@pytest.mark.parametrize(
    "table,kind",
    [
        ("lost_item_profiles", "ice"),
        ("ice_profiles", "lost"),
        ("tag_contact_preferences", "ice"),
    ],
)
def test_wrong_profile_purpose_rejected(conn, table, kind):
    _, ids = pair(conn)
    with pytest.raises(IntegrityError):
        conn.execute(
            text(f"INSERT INTO {table}(qr_id) VALUES (:id)"), {"id": ids[kind]}
        )


def test_orm_independent_profiles_and_multiple_pairs_per_owner(conn):
    # Managed auth is not changed persistently; synthetic row is rolled back.
    owner = uuid.uuid4()
    conn.execute(text("INSERT INTO auth.users(id) VALUES (:id)"), {"id": owner})
    with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
        batch = QRBatch(batch_code=uuid.uuid4().hex, ecc_level="Q")
        session.add(batch)
        session.flush()
        losts = []
        for _ in range(2):
            p = TagPair(
                batch_id=batch.id,
                pair_reference=uuid.uuid4().hex,
                owner_user_id=owner,
                ownership_status="active",
                activated_at=conn.execute(text("SELECT now()")).scalar_one(),
            )
            session.add(p)
            session.flush()
            for kind in ("lost", "ice"):
                q = QRCode(
                    pair_id=p.id,
                    tag_type=kind,
                    serial_number=uuid.uuid4().hex,
                    public_token=uuid.uuid4().hex,
                    ecc_level="Q",
                    public_status="active",
                )
                session.add(q)
                session.flush()
                if kind == "lost":
                    profile = LostItemProfile(qr_id=q.id, item_label="original")
                    losts.append(profile)
                else:
                    profile = ICEProfile(qr_id=q.id, display_name="independent")
                session.add(profile)
        session.flush()
        losts[0].item_label = "edited"
        losts[0].profile_version += 1
        session.flush()
        session.expire_all()
        assert losts[1].item_label == "original"
        assert losts[1].profile_version == 1
        validate(conn)
        assert (
            session.query(ICEProfile).filter_by(display_name="independent").count() == 2
        )
        session.commit()


@pytest.mark.parametrize(
    "case",
    ["credential", "ice_consent", "medical_key", "contact", "whatsapp", "active_owner"],
)
def test_private_field_and_state_constraints(conn, case):
    pid, ids = pair(conn)
    with pytest.raises(IntegrityError):
        if case == "credential":
            conn.execute(
                text(
                    "INSERT INTO pair_activation_credentials(pair_id,secret_verifier,verifier_key_version,status) VALUES (:p,decode('ab','hex'),1,'consumed')"
                ),
                {"p": pid},
            )
        elif case == "ice_consent":
            conn.execute(
                text("INSERT INTO ice_profiles(qr_id,published) VALUES (:ice,true)"),
                ids,
            )
        elif case == "medical_key":
            conn.execute(
                text(
                    "INSERT INTO ice_profiles(qr_id,medical_notes_ciphertext) VALUES (:ice,decode('ab','hex'))"
                ),
                ids,
            )
        elif case == "contact":
            conn.execute(text("INSERT INTO ice_profiles(qr_id) VALUES (:ice)"), ids)
            conn.execute(
                text(
                    "INSERT INTO ice_contacts(ice_qr_id,relationship_label,phone_ciphertext,phone_key_version,published) VALUES (:ice,'Parent',decode('ab','hex'),1,true)"
                ),
                ids,
            )
        elif case == "whatsapp":
            conn.execute(
                text(
                    "INSERT INTO tag_contact_preferences(qr_id,whatsapp_enabled) VALUES (:lost,true)"
                ),
                ids,
            )
        else:
            conn.execute(
                text("UPDATE tag_pairs SET ownership_status='active' WHERE id=:p"),
                {"p": pid},
            )


def test_user_and_batch_history_delete_restricted(conn):
    pid, _ = pair(conn)
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "DELETE FROM qr_batches WHERE id=(SELECT batch_id FROM tag_pairs WHERE id=:p)"
            ),
            {"p": pid},
        )


def test_existing_schema_and_destructive_downgrade_refused(conn, monkeypatch):
    path = Path(__file__).parents[2] / "alembic/versions/0001_identity_profiles.py"
    spec = importlib.util.spec_from_file_location("initial_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    monkeypatch.setattr(revision.op, "get_bind", lambda: conn)
    with pytest.raises(RuntimeError, match="explicit reconciliation"):
        revision.upgrade()
    with pytest.raises(RuntimeError, match="Destructive downgrade disabled"):
        revision.downgrade()
    assert inspect(conn).has_table("tag_pairs")


def test_actual_commit_rejects_incomplete_pair():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Development PostgreSQL not configured")
    db = Database.from_settings(Settings(database_url=SecretStr(url)))
    try:
        with db.engine.connect() as connection:
            if not inspect(connection).has_table("tag_pairs"):
                pytest.skip("Commit check requires applied development migration")
            connection.rollback()
            with pytest.raises(IntegrityError), connection.begin():
                pid, _ = pair(connection, children=False)
                qr(connection, pid, "lost")
                # The context manager's COMMIT must fail, not just SET CONSTRAINTS.
            connection.rollback()
            assert (
                connection.execute(
                    text("SELECT count(*) FROM tag_pairs WHERE id=:id"), {"id": pid}
                ).scalar_one()
                == 0
            )
    finally:
        db.close()
