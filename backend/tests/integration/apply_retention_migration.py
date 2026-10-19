"""Rehearse rollback, then apply only scoped 0019 with exact row/role preservation."""

import os
from urllib.parse import urlsplit

from alembic.config import Config
from apply_checkout_migration import fingerprint
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database, database_url

BASE = "0018_fulfillment_eligibility"
TARGET = "0019_retention_recovery"
FUNCTIONS = {
    "sr_retention_schedule",
    "sr_retention_retry",
    "sr_retention_held",
    "sr_finance_changed",
    "sr_retention_prepare",
    "sr_retention_finish",
    "sr_retention_admission",
    "sr_retention_identity",
    "sr_worker_finance",
}
TRIGGERS = {
    ("orders", "sr_finance_changed"),
    ("retention_holds", "sr_aa_retention_admission"),
    ("durable_jobs", "sr_retention_job_admission"),
    ("support_cases", "sr_retention_dispute_admission"),
    ("print_download_grants", "sr_retention_download_admission"),
    ("print_artifacts", "sr_retention_identity"),
    ("payment_evidence", "sr_retention_identity"),
}


def main():
    load_dotenv(".env")
    settings = Settings()
    target = settings.migration_database_url or settings.database_url
    assert target and settings.supabase_url
    project_host = urlsplit(settings.supabase_url).hostname
    assert project_host and project_host.endswith(".supabase.co")
    project = project_host.split(".")[0]
    test_url = database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"])
    migration_url = database_url(target.get_secret_value())
    for url in (test_url, migration_url):
        assert url.database == test_url.database
        assert url.host == f"db.{project}.supabase.co" or (
            url.host.endswith(".pooler.supabase.com")
            and url.username.endswith("." + project)
        ), "Migration target must match the authorized application/test project"
    db = Database.from_settings(
        settings.model_copy(
            update={
                "database_url": target,
            }
        )
    )
    assert db

    def upgrade(c):
        config = Config("alembic.ini")
        config.attributes["connection"] = c
        command.upgrade(config, TARGET)

    def verify(c, before, definitions, data):
        assert metadata(c, TARGET)[1:] == before[1:]
        assert fingerprint(c, before[1]) == data
        after = catalog(c)
        for key in ("constraints", "indexes", "columns"):
            assert after[key] == definitions[key], key

        def unaffected_policy(row):
            return not (
                row[0] == "finance_sheet_sync"
                and row[1]
                in {
                    "sr_safereturn_worker_select",
                    "sr_safereturn_worker_update",
                }
            )

        assert [r for r in after["policies"] if unaffected_policy(r)] == [
            r for r in definitions["policies"] if unaffected_policy(r)
        ]
        changed = [r for r in after["policies"] if not unaffected_policy(r)]
        assert len(changed) == 2 and all("sr_worker_finance" in str(r) for r in changed)
        old, new = dict(definitions["functions"]), dict(after["functions"])
        assert new.keys() - old.keys() == FUNCTIONS
        assert all(new[k] == v for k, v in old.items())
        added = set(after["triggers"]) - set(definitions["triggers"])
        assert {(r[0], r[1]) for r in added} == TRIGGERS
        assert set(definitions["triggers"]) <= set(after["triggers"])
        permissions = {
            "sr_retention_held(text,uuid)": "safereturn_api",
            "sr_retention_retry(uuid,text)": "safereturn_api",
            "sr_retention_schedule(text)": "safereturn_worker",
            "sr_retention_prepare(uuid,integer,text)": "safereturn_worker",
            "sr_retention_finish(uuid,integer)": "safereturn_worker",
            "sr_finance_changed()": None,
            "sr_retention_admission()": None,
            "sr_retention_identity()": None,
            "sr_worker_finance(uuid)": "safereturn_worker",
        }
        for function, allowed in permissions.items():
            for role in (
                "anon",
                "authenticated",
                "safereturn_api",
                "safereturn_worker",
            ):
                assert c.execute(
                    text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                    {"role": role, "fn": "public." + function},
                ).scalar_one() is (role == allowed)

    try:
        with db.engine.connect() as c:
            transaction = c.begin()
            before = metadata(c, BASE)
            definitions = catalog(c)
            data = fingerprint(c, before[1])
            upgrade(c)
            verify(c, before, definitions, data)
            transaction.rollback()
            assert metadata(c, BASE) == before
            assert catalog(c) == definitions
            assert fingerprint(c, before[1]) == data
            c.rollback()
            with c.begin():
                upgrade(c)
                verify(c, before, definitions, data)
        print(
            "Applied only 0019 after real installed-DDL rollback/retry: nine narrow functions, seven triggers and two narrowed finance worker policies; exact existing rows, roles, tables and unrelated definitions preserved. No policy approvals, deadlines or object deletions installed."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
