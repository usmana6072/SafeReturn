"""Apply only rehearsed 0016; preserve all installed data and unrelated objects."""

from alembic.config import Config
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def fingerprint(connection, tables):
    return {
        name: connection.execute(
            text(f"""SELECT md5(COALESCE(string_agg(value::text,'' ORDER BY value::text),''))
            FROM (SELECT to_jsonb(t) AS value FROM public."{name}" t) rows""")
        ).scalar_one()
        for name, _ in tables
    }


def main():
    load_dotenv(".env")
    s = Settings()
    db = Database.from_settings(
        s.model_copy(
            update={"database_url": s.migration_database_url or s.database_url}
        )
    )
    assert db
    try:
        with db.engine.begin() as c:
            before = metadata(c, "0015_public_catalog")
            definitions = catalog(c)
            data = fingerprint(c, before[1])
            cfg = Config("alembic.ini")
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "0016_checkout_quotes")
            after = metadata(c, "0016_checkout_quotes")
            updated = catalog(c)
            assert set(after[1]) - set(before[1]) == {("checkout_quotes", True)}
            assert after[2] == before[2]
            assert (
                all(after[3][k] == v for k, v in before[3].items())
                and after[3]["checkout_quotes"] == 0
            )
            assert fingerprint(c, before[1]) == data
            for kind in ("constraints", "indexes", "triggers", "policies", "columns"):
                assert set(definitions[kind]) <= set(updated[kind]), kind
                assert all(
                    row[0] == "checkout_quotes"
                    for row in set(updated[kind]) - set(definitions[kind])
                ), kind
            old, new = dict(definitions["functions"]), dict(updated["functions"])
            assert new.keys() - old.keys() == {
                "sr_quote_immutable",
                "sr_checkout_catalog",
                "sr_checkout_capacity",
                "sr_checkout_reserve",
            }
            assert all(new[k] == v for k, v in old.items())
            for function in (
                "sr_checkout_catalog(uuid[])",
                "sr_checkout_capacity()",
                "sr_checkout_reserve(uuid,uuid,uuid,integer)",
            ):
                for role in ("anon", "authenticated", "safereturn_worker"):
                    assert not c.execute(
                        text("SELECT has_function_privilege(:role,:fn,'EXECUTE')"),
                        {"role": role, "fn": "public." + function},
                    ).scalar_one()
            print(
                f"Applied only 0016: {len(after[1])} RLS tables; existing {sum(before[3].values())} row contents, roles and all unrelated definitions preserved; no quotes/orders seeded. 0017 remains unapplied."
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
