"""Upgrade with representative previous-revision records, always rolled back."""

import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def test_commerce_upgrade_preserves_existing_identity_and_profile():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Development PostgreSQL not configured")
    db = Database.from_settings(Settings(database_url=SecretStr(url)))
    marker = uuid.uuid4().hex
    try:
        with db.engine.connect() as c, c.begin():
            cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            cfg.attributes["connection"] = c
            # Before application, these are real 0001 rows present before 0002.
            # After application the same check exercises a populated no-op upgrade.
            c.execute(
                text(
                    """
DO $$
DECLARE b uuid; p uuid; q uuid;
BEGIN
 INSERT INTO qr_batches(batch_code,ecc_level) VALUES('upgrade-MARKER','Q') RETURNING id INTO b;
 INSERT INTO tag_pairs(pair_reference,batch_id) VALUES('upgrade-MARKER',b) RETURNING id INTO p;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(p,'lost','lost-MARKER','lost-MARKER','Q') RETURNING id INTO q;
 INSERT INTO lost_item_profiles(qr_id,item_label,profile_version) VALUES(q,'Existing profile',7);
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level)
 VALUES(p,'ice','ice-MARKER','ice-MARKER','Q');
END $$;
""".replace("MARKER", marker)
                )
            )
            c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            command.upgrade(cfg, "head")
            row = c.execute(
                text(
                    "SELECT l.item_label,l.profile_version,q.public_token FROM lost_item_profiles l JOIN qr_codes q ON q.id=l.qr_id WHERE q.serial_number=:s"
                ),
                {"s": "lost-" + marker},
            ).one()
            assert row == ("Existing profile", 7, "lost-" + marker)
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == ScriptDirectory.from_config(cfg).get_current_head()
            )
            c.rollback()
    finally:
        db.close()


def test_actual_commit_rejects_incomplete_commerce_order():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Development PostgreSQL not configured")
    db = Database.from_settings(Settings(database_url=SecretStr(url)))
    owner = uuid.uuid4()
    try:
        with db.engine.connect() as c:
            prior = c.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "head")
            c.execute(text("INSERT INTO auth.users(id) VALUES(:id)"), {"id": owner})
            c.execute(
                text(
                    "INSERT INTO orders(order_number,customer_user_id,order_status,placed_at,subtotal_pkr,total_pkr) VALUES(:number,:id,'placed',now(),0,0)"
                ),
                {"number": uuid.uuid4().hex, "id": owner},
            )
            with pytest.raises(IntegrityError):
                c.commit()
            c.rollback()
            assert (
                c.execute(
                    text("SELECT count(*) FROM auth.users WHERE id=:id"), {"id": owner}
                ).scalar_one()
                == 0
            )
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == prior
            )
    finally:
        db.close()
