"""Owner authorization on a fresh local PostgreSQL; no real staff enrollment."""

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from independent_finance_local import local_cluster
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.api.auth import AccessError, require_staff
from app.api.v1.account import STAFF_CAPABILITIES, staff_security
from app.core.config import Settings
from app.db.runtime import api_transaction
from app.db.session import Database

pytestmark = pytest.mark.skipif(
    os.environ.get("SAFERETURN_OWNER_REHEARSAL") != "1",
    reason="Requires disposable loopback PostgreSQL",
)


def test_owner_inheritance_mfa_revocation_and_no_automatic_assignment():
    with local_cluster("0060_owner_role") as (url, _, _):
        database = Database(create_engine(url, hide_parameters=True))
        owner, finance = uuid4(), uuid4()
        try:
            with database.engine.begin() as c:
                assert (
                    c.execute(
                        text("SELECT count(*) FROM staff_roles WHERE role='owner'")
                    ).scalar_one()
                    == 0
                )
                for uid, role in ((owner, "owner"), (finance, "finance")):
                    c.execute(
                        text(
                            "INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"
                        ),
                        {"id": uid},
                    )
                    c.execute(
                        text(
                            "INSERT INTO staff_roles(user_id,role,reason) VALUES(:id,:role,'Disposable authorization test')"
                        ),
                        {"id": uid, "role": role},
                    )
                # All original explicit role locks now recognize owner as well.
                definitions = c.execute(
                    text(
                        "SELECT proname,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace AND prokind='f' AND proname NOT LIKE 'sr_support_dev_%'"
                    )
                ).all()
                for name, definition in definitions:
                    if "public.staff_roles" in definition:
                        for role in (
                            "operations",
                            "security_admin",
                            "finance",
                            "support",
                            "superadmin",
                        ):
                            assert f"role='{role}'" not in definition, name
            for uid, expected in ((owner, True), (finance, False)):
                with api_transaction(database, uid, mfa_verified=True) as session:
                    session.info["settings"] = Settings()
                    context = SimpleNamespace(
                        session=session,
                        principal=SimpleNamespace(user_id=uid),
                        email_verified=True,
                        mfa_verified=True,
                    )
                    for role in (
                        "operations",
                        "security_admin",
                        "support",
                        "superadmin",
                    ):
                        assert (
                            session.execute(
                                text("SELECT sr_is_staff(ARRAY[:role])"), {"role": role}
                            ).scalar_one()
                            == expected
                        )
                        if expected:
                            require_staff(context, role)
                        else:
                            with pytest.raises(AccessError):
                                require_staff(context, role)
                    require_staff(context, "finance")
                    result = staff_security(context)
                    assert result.roles == (["owner"] if expected else ["finance"])
                    if expected:
                        assert result.capabilities == sorted(STAFF_CAPABILITIES)
            with api_transaction(database, owner, mfa_verified=False) as session:
                assert not session.execute(
                    text("SELECT sr_is_staff(ARRAY['operations'])")
                ).scalar_one()
            with database.engine.begin() as c:
                c.execute(
                    text("UPDATE staff_roles SET revoked_at=now() WHERE user_id=:id"),
                    {"id": owner},
                )
            with api_transaction(database, owner, mfa_verified=True) as session:
                assert not session.execute(
                    text("SELECT sr_is_staff(ARRAY['operations'])")
                ).scalar_one()
                with pytest.raises(AccessError):
                    require_staff(
                        SimpleNamespace(
                            session=session,
                            principal=SimpleNamespace(user_id=owner),
                            email_verified=True,
                            mfa_verified=True,
                        ),
                        "operations",
                    )
                with pytest.raises(DBAPIError):
                    session.execute(
                        text(
                            "INSERT INTO staff_roles(user_id,role) VALUES(:id,'owner')"
                        ),
                        {"id": finance},
                    )
        finally:
            database.close()
