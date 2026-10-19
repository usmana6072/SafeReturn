"""Apply only the owner-approved 0021 artifact, preserving existing rows/powers."""

import hashlib
from pathlib import Path

from alembic.config import Config
from apply_notification_operations_migration import privileges
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database

BASE = "0020_notification_operations"
TARGET = "0021_support_case_console"
SHA256 = "342fc6721d0c1af2108e82e53cb55b13d3408ccedfe1f51525f5ac932c255b12"
FUNCTIONS = {
    "sr_support_finder_hold_lock()": False,
    "sr_support_context(uuid)": True,
    "sr_support_create(uuid,text,text,uuid,uuid,bytea,smallint,uuid,text)": True,
    "sr_support_change(uuid,integer,text,text,text,uuid,bytea,smallint,text)": True,
}


def rows(c, tables):
    clauses = []
    for schema, name in tables:
        assert schema in {"public", "auth"} and name.replace("_", "").isalnum()
        projection = "to_jsonb(t)"
        if (schema, name) == ("public", "support_cases"):
            projection += "-ARRAY['case_revision','priority','description_format']"
        clauses.append(
            f"(SELECT md5(coalesce(string_agg(({projection})::text,'' ORDER BY ({projection})::text),'')) FROM {schema}.\"{name}\" t)"
        )
    return tuple(c.execute(text("SELECT " + ",".join(clauses))).one())


def main():
    assert (
        hashlib.sha256(
            Path("alembic/versions/0021_support_case_console.py").read_bytes()
        ).hexdigest()
        == SHA256
    )
    load_dotenv(".env")
    settings = Settings()
    assert settings.migration_database_url
    db = Database.from_settings(
        settings.model_copy(update={"database_url": settings.migration_database_url})
    )
    assert db
    try:
        with db.engine.begin() as c:
            c.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtextextended('SafeReturn migration 0021',0))"
                )
            )
            assert (
                c.execute(
                    text("SELECT version_num FROM public.alembic_version FOR UPDATE")
                ).scalar_one()
                == BASE
            ), "Unexpected head; never replay"
            before = metadata(c, BASE)
            old = catalog(c)
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
            assert set(after[1]) - set(before[1]) == {("support_case_events", True)}
            assert set(before[1]) <= set(after[1]) and after[2] == before[2]
            assert all(after[3][name] == count for name, count in before[3].items())
            assert after[3]["support_case_events"] == 0
            assert rows(c, tables) == data, "Existing domain/Auth/factor values changed"
            new = catalog(c)
            for kind in ["indexes", "policies"]:
                assert set(old[kind]) <= set(new[kind])
                assert all(
                    row[0] == "support_case_events"
                    for row in set(new[kind]) - set(old[kind])
                )
            assert set(old["constraints"]) <= set(new["constraints"])
            case_checks = {
                "support_cases_case_revision_check",
                "support_cases_priority_check",
                "support_cases_description_format_check",
            }
            added_constraints = set(new["constraints"]) - set(old["constraints"])
            assert {
                r[1] for r in added_constraints if r[0] == "support_cases"
            } == case_checks
            assert all(
                r[0] == "support_case_events"
                or (r[0] == "support_cases" and r[1] in case_checks)
                for r in added_constraints
            )
            assert set(old["triggers"]) <= set(new["triggers"])
            assert {
                (r[0], r[1]) for r in set(new["triggers"]) - set(old["triggers"])
            } == {
                ("support_case_events", "sr_case_event_append"),
                ("retention_holds", "sr_ab_support_finder_hold"),
            }
            assert set(old["columns"]) <= set(new["columns"])
            additions = set(new["columns"]) - set(old["columns"])
            assert {r[1] for r in additions if r[0] == "support_cases"} == {
                "case_revision",
                "priority",
                "description_format",
            }
            assert all(
                r[0] in {"support_cases", "support_case_events"} for r in additions
            )
            assert set(old["functions"]) <= set(new["functions"])
            assert {r[0] for r in set(new["functions"]) - set(old["functions"])} == {
                sig.split("(")[0] for sig in FUNCTIONS
            }
            updated_acl = privileges(c)
            assert set(acl["tables"]) <= set(updated_acl["tables"])
            assert all(
                r[0] == "public" and r[1].startswith("support_case_events")
                for r in set(updated_acl["tables"]) - set(acl["tables"])
            )
            assert updated_acl["membership"] == acl["membership"]
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
                    assert allowed == (role == "safereturn_api" and api_allowed)
                assert not c.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_proc p,LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE p.oid=CAST(:fn AS regprocedure) AND a.grantee=0 AND a.privilege_type='EXECUTE')"
                    ),
                    {"fn": "public." + signature},
                ).scalar_one()
            print(
                "Precommit preservation PASS: original domain/Auth/factor values, roles, DDL, grants and memberships unchanged; only approved additive 0021 objects."
            )
        with db.engine.connect() as c:
            assert (
                c.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one()
                == TARGET
            )
            assert rows(c, tables) == data
        print(
            "COMMITTED and fresh readback PASS: 0021_support_case_console; owner finance+operations preserved; no case command or provider call."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
