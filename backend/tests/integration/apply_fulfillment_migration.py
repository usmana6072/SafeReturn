"""Rehearse/retry the sole Task 5.5 development migration with exact preservation."""

from alembic.config import Config
from apply_checkout_migration import fingerprint
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database

BASE = "0017_print_download_grants"
TARGET = "0018_fulfillment_eligibility"


def main():
    load_dotenv(".env")
    settings = Settings()
    db = Database.from_settings(
        settings.model_copy(
            update={
                "database_url": settings.migration_database_url or settings.database_url
            }
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
        assert after[1:] == before[1:]
        assert fingerprint(c, before[1]) == data
        for key in ["indexes", "policies", "columns"]:
            assert updated[key] == definitions[key], key
        added_constraints = set(updated["constraints"]) - set(
            definitions["constraints"]
        )
        assert set(definitions["constraints"]) <= set(updated["constraints"])
        assert {(row[0], row[1]) for row in added_constraints} == {
            ("shipments", "sr_fulfillment_complete"),
            ("shipment_pairs", "sr_fulfillment_pairs_complete"),
        }, {(row[0], row[1]) for row in added_constraints}
        assert set(updated["triggers"]) - set(definitions["triggers"]) == {
            row
            for row in updated["triggers"]
            if row[0] in {"shipments", "shipment_pairs"}
            and row[1] in {"sr_fulfillment_complete", "sr_fulfillment_pairs_complete"}
        }
        assert len(updated["triggers"]) - len(definitions["triggers"]) == 2
        assert set(definitions["triggers"]) <= set(updated["triggers"])
        old, new = dict(definitions["functions"]), dict(updated["functions"])
        assert new.keys() - old.keys() == {
            "sr_fulfillment_eligible",
            "sr_fulfillment_complete",
        }
        assert all(new[k] == v for k, v in old.items() if k != "sr_shipment_guard")
        assert new["sr_shipment_guard"] != old["sr_shipment_guard"]
        for role in ["anon", "authenticated", "safereturn_worker"]:
            assert not c.execute(
                text(
                    "SELECT has_function_privilege(:role,'public.sr_fulfillment_eligible(uuid)','EXECUTE')"
                ),
                {"role": role},
            ).scalar_one()
        assert c.execute(
            text(
                "SELECT has_function_privilege('safereturn_api','public.sr_fulfillment_eligible(uuid)','EXECUTE')"
            )
        ).scalar_one()
        assert not c.execute(
            text("SELECT public.sr_fulfillment_eligible(gen_random_uuid())")
        ).scalar_one()

    try:
        with db.engine.connect() as c:
            tx = c.begin()
            before = metadata(c, BASE)
            definitions = catalog(c)
            data = fingerprint(c, before[1])
            upgrade(c)
            verify(c, before, definitions, data)
            tx.rollback()
            assert (
                metadata(c, BASE) == before
                and catalog(c) == definitions
                and fingerprint(c, before[1]) == data
            )
            c.rollback()
            with c.begin():
                upgrade(c)
                verify(c, before, definitions, data)
        print(
            "Applied only 0018 after full installed-DDL rollback/retry rehearsal: two narrow functions/two shipment triggers and the related exception-guard correction; exact existing rows, roles, tables, policies and unrelated definitions preserved."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
