"""Apply only rehearsed 0015 to the authorized development database."""

from alembic.config import Config
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def fingerprint(c, tables):
    result = {}
    for name, _ in tables:
        result[name] = c.execute(
            text(
                f"SELECT md5(COALESCE(string_agg(row_value::text,'' ORDER BY row_value::text),'')) FROM (SELECT to_jsonb(t)-'catalog_version'-'verified_public_url' AS row_value FROM public.\"{name}\" t) rows"
            )
        ).scalar_one()
    return result


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
    assert db is not None
    try:
        with db.engine.begin() as c:
            before = metadata(c, "0014a_notification_delivery")
            definitions = catalog(c)
            data = fingerprint(c, before[1])
            cfg = Config("alembic.ini")
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "0015_public_catalog")
            after = metadata(c, "0015_public_catalog")
            updated = catalog(c)
            assert before[1:] == after[1:]
            assert fingerprint(c, after[1]) == data, "Existing row contents changed"
            for kind in ("indexes", "triggers"):
                assert definitions[kind] == updated[kind], kind
            old, new = dict(definitions["functions"]), dict(updated["functions"])
            assert new.keys() - old.keys() == {"sr_public_catalog"}
            assert all(new[k] == v for k, v in old.items())
            additions = set(updated["columns"]) - set(definitions["columns"])
            assert {(r[0], r[1]) for r in additions} == {
                ("products", "catalog_version"),
                ("product_variants", "catalog_version"),
                ("product_categories", "catalog_version"),
                ("product_images", "verified_public_url"),
            }
            assert not set(definitions["columns"]) - set(updated["columns"])
            added_constraints = set(updated["constraints"]) - set(
                definitions["constraints"]
            )
            assert {(r[0], r[1]) for r in added_constraints} == {
                (t, t + "_catalog_version_check")
                for t in ("products", "product_variants", "product_categories")
            }
            assert not set(definitions["constraints"]) - set(updated["constraints"])
            assert len(set(updated["policies"]) - set(definitions["policies"])) == 1
            assert not set(definitions["policies"]) - set(updated["policies"])
            for role in ("anon", "authenticated", "safereturn_worker"):
                assert not c.execute(
                    text(
                        "SELECT has_function_privilege(:role,'public.sr_public_catalog(text)','EXECUTE')"
                    ),
                    {"role": role},
                ).scalar_one()
            assert c.execute(
                text(
                    "SELECT has_function_privilege('safereturn_api','public.sr_public_catalog(text)','EXECUTE')"
                )
            ).scalar_one()
        print(
            f"Applied only 0015: {len(after[1])} RLS tables; {sum(after[3].values())} existing rows and contents preserved; roles, indexes, triggers and unrelated functions unchanged. Added only four catalog columns, three positivity checks, image-unlink policy/grant and public projection."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
