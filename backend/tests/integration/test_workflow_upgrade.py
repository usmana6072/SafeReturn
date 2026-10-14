"""Real upgrade preservation and COMMIT rejection with all changes rolled back."""

import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def test_upgrade_preserves_previous_private_profile_and_commit_requires_outbox():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Development PostgreSQL not configured")
    db = Database.from_settings(Settings(database_url=SecretStr(url)))
    uid = uuid.uuid4()
    marker = uuid.uuid4().hex
    try:
        with db.engine.connect() as c:
            prior = c.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            c.execute(text("INSERT INTO auth.users(id) VALUES(:id)"), {"id": uid})
            c.execute(
                text(
                    "INSERT INTO user_profiles(user_id,display_name,phone_ciphertext,phone_key_version) VALUES(:id,'existing-private-profile',decode('ab','hex'),3)"
                ),
                {"id": uid},
            )
            cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "head")
            assert c.execute(
                text(
                    "SELECT phone_ciphertext,phone_key_version FROM user_profiles WHERE user_id=:id"
                ),
                {"id": uid},
            ).one() == (bytes.fromhex("ab"), 3)
            c.execute(
                text(
                    """
DO $$
DECLARE b uuid; p uuid; q uuid;
BEGIN
 INSERT INTO qr_batches(batch_code,ecc_level) VALUES('commit-MARKER','Q') RETURNING id INTO b;
 INSERT INTO tag_pairs(pair_reference,batch_id,owner_user_id,ownership_status,activated_at)
 VALUES('commit-MARKER',b,'USER_ID','active',now()) RETURNING id INTO p;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(p,'lost','lost-MARKER','lost-MARKER','Q','active') RETURNING id INTO q;
 INSERT INTO qr_codes(pair_id,tag_type,serial_number,public_token,ecc_level,public_status)
 VALUES(p,'ice','ice-MARKER','ice-MARKER','Q','active');
 INSERT INTO finder_messages(qr_id,recipient_owner_user_id,finder_email_ciphertext,finder_contact_key_version,message_text_ciphertext,message_key_version,consent_version,consent_at)
 VALUES(q,'USER_ID',decode('ab','hex'),1,decode('cd','hex'),1,'v1',now());
END $$;
""".replace("MARKER", marker).replace("USER_ID", str(uid))
                )
            )
            with pytest.raises(IntegrityError):
                c.commit()
            c.rollback()
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == prior
            )
            assert (
                c.execute(
                    text("SELECT count(*) FROM auth.users WHERE id=:id"), {"id": uid}
                ).scalar_one()
                == 0
            )
    finally:
        db.close()
