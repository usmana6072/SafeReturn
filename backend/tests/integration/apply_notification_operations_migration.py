"""Apply only the owner-approved, hash-checked 0020 migration with preservation."""

import hashlib
from pathlib import Path

from alembic.config import Config
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database

BASE = "0019_retention_recovery"
TARGET = "0020_notification_operations"
SHA256 = "393f72dbf6b9dbffec8d855e2ac47106625aab1ec1f544ac69f316611a0b8b48"
FUNCTIONS = {
    "sr_notification_safe_code(text)": False,
    "sr_notification_retry_gate(uuid,integer)": False,
    "sr_notification_metadata(integer,timestamp with time zone,uuid,text,uuid,integer,integer,integer)": True,
    "sr_notification_retry(uuid,integer,integer,text,text)": True,
}


def rows(c, tables):
    # Names are catalog-derived identifiers; return hashes, never domain/Auth data.
    clauses = []
    for schema, name in tables:
        assert schema in {"public", "auth"} and name.replace("_", "").isalnum()
        clauses.append(
            f"(SELECT md5(coalesce(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text),'')) FROM {schema}.\"{name}\" t)"
        )
    return tuple(c.execute(text("SELECT " + ",".join(clauses))).one())


def privileges(c):
    return {
        "tables": c.execute(
            text(
                "SELECT n.nspname,c.relname,c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('public','auth') ORDER BY 1,2"
            )
        ).all(),
        "membership": c.execute(
            text(
                "SELECT roleid,member,grantor,admin_option FROM pg_auth_members ORDER BY 1,2,3"
            )
        ).all(),
        "functions": c.execute(
            text(
                "SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' ORDER BY 1,2"
            )
        ).all(),
    }


def main():
    assert (
        hashlib.sha256(
            Path("alembic/versions/0020_notification_operations.py").read_bytes()
        ).hexdigest()
        == SHA256
    ), "Migration differs from approved artifact"
    load_dotenv(".env")
    settings = Settings()
    assert settings.migration_database_url, (
        "Explicit configured migration identity required"
    )
    db = Database.from_settings(
        settings.model_copy(update={"database_url": settings.migration_database_url})
    )
    assert db
    try:
        with db.engine.begin() as c:
            c.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtextextended('SafeReturn migration 0020',0))"
                )
            )
            assert (
                c.execute(
                    text("SELECT version_num FROM public.alembic_version FOR UPDATE")
                ).scalar_one()
                == BASE
            ), "Unexpected installed revision; inspect without replay"
            before = metadata(c, BASE)
            definitions = catalog(c)
            acl = privileges(c)
            tables = [("public", name) for name, _ in before[1]] + [
                ("auth", "users"),
                ("auth", "mfa_factors"),
            ]
            data = rows(c, tables)
            roles = (
                c.execute(
                    text(
                        "SELECT role FROM public.staff_roles WHERE user_id=(SELECT id FROM auth.users WHERE email=:email) AND revoked_at IS NULL ORDER BY role"
                    ),
                    {"email": "uaa007079@gmail.com"},
                )
                .scalars()
                .all()
            )
            assert roles == ["finance", "operations"]
            cfg = Config("alembic.ini")
            cfg.attributes["connection"] = c
            command.upgrade(cfg, TARGET)
            after = metadata(c, TARGET)
            assert after[1:] == before[1:], "Installed rows/table/role metadata changed"
            assert rows(c, tables) == data, "Existing domain/Auth/factor rows changed"
            updated = catalog(c)
            for kind in ["constraints", "indexes", "triggers", "policies", "columns"]:
                assert updated[kind] == definitions[kind], kind
            old, new = dict(definitions["functions"]), dict(updated["functions"])
            assert all(new.get(k) == v for k, v in old.items())
            assert new.keys() - old.keys() == {key.split("(")[0] for key in FUNCTIONS}
            updated_acl = privileges(c)
            assert (
                updated_acl["tables"] == acl["tables"]
                and updated_acl["membership"] == acl["membership"]
            )
            assert set(acl["functions"]) <= set(updated_acl["functions"])
            for signature, api_allowed in FUNCTIONS.items():
                for role in [
                    "anon",
                    "authenticated",
                    "safereturn_worker",
                    "safereturn_api",
                ]:
                    allowed = c.execute(
                        text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                        {"role": role, "fn": "public." + signature},
                    ).scalar_one()
                    assert allowed == (role == "safereturn_api" and api_allowed), (
                        signature,
                        role,
                    )
                assert not c.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_proc p,LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE p.oid=CAST(:fn AS regprocedure) AND a.grantee=0 AND a.privilege_type='EXECUTE')"
                    ),
                    {"fn": "public." + signature},
                ).scalar_one()
            print(
                "Precommit checks PASS: exact rows/Auth factors/roles, existing DDL and grants preserved; only approved four functions/two API execution grants added."
            )
        # Never rerun a mutation to obtain readback; this is a fresh read only.
        with db.engine.connect() as c:
            assert (
                c.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one()
                == TARGET
            )
        print(
            "COMMITTED and read back: "
            + TARGET
            + "; owner roles finance+operations; no event retry or worker/provider call."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
