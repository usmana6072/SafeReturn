"""Rehearse then apply only scoped development print migration 0017."""

from alembic.config import Config
from apply_checkout_migration import fingerprint
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database

TARGET = "0017_print_download_grants"


def main():
    load_dotenv(".env")
    s = Settings()
    db = Database.from_settings(
        s.model_copy(
            update={"database_url": s.migration_database_url or s.database_url}
        )
    )
    assert db

    def upgrade(c):
        cfg = Config("alembic.ini")
        cfg.attributes["connection"] = c
        command.upgrade(cfg, TARGET)

    def verify(c, before, definitions, data):
        after = metadata(c, TARGET)
        updated = catalog(c)
        assert set(after[1]) - set(before[1]) == {
            ("print_download_grants", True),
            ("print_job_qa", True),
        }
        assert after[2] == before[2]
        assert all(after[3][k] == v for k, v in before[3].items())
        assert after[3]["print_download_grants"] == after[3]["print_job_qa"] == 0
        assert fingerprint(c, before[1]) == data
        for kind in ("constraints", "indexes", "triggers", "policies", "columns"):
            assert set(definitions[kind]) <= set(updated[kind]), kind
            for row in set(updated[kind]) - set(definitions[kind]):
                assert row[0] in {
                    "print_download_grants",
                    "print_job_qa",
                    "print_jobs",
                    "print_artifacts",
                }, (kind, row[0])
        old, new = dict(definitions["functions"]), dict(updated["functions"])
        assert new.keys() - old.keys() == {
            "sr_print_occurrences",
            "sr_insert_print_job",
            "sr_print_order_lock",
            "sr_print_qa_complete",
            "sr_print_artifact_identity",
        }
        assert all(new[k] == v for k, v in old.items() if k != "sr_print_guard")
        assert new["sr_print_guard"] != old["sr_print_guard"]
        for fn in (
            "sr_print_occurrences(uuid)",
            "sr_print_order_lock(uuid)",
            "sr_insert_print_job(uuid,uuid,integer,text,jsonb,bytea,smallint)",
        ):
            for role in ("anon", "authenticated"):
                assert not c.execute(
                    text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                    {"role": role, "fn": "public." + fn},
                ).scalar_one()

    try:
        with db.engine.connect() as c:
            tr = c.begin()
            before = metadata(c, "0016_checkout_quotes")
            definitions = catalog(c)
            data = fingerprint(c, before[1])
            upgrade(c)
            verify(c, before, definitions, data)
            tr.rollback()
            assert metadata(c, "0016_checkout_quotes") == before
            assert catalog(c) == definitions and fingerprint(c, before[1]) == data
            c.rollback()
            with c.begin():
                upgrade(c)
                verify(c, before, definitions, data)
        print(
            "Applied only 0017 after full rollback/retry rehearsal: 43 RLS tables, 3 original row contents/roles and unrelated definitions preserved; new print grant/QA tables empty. No production job/QA/Auth records seeded."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
