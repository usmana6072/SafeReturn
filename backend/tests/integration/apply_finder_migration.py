"""Apply only the rehearsed finder revision, with development preservation checks."""

from alembic.config import Config
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata

from alembic import command
from app.core.config import Settings
from app.db.session import Database


def main():
    load_dotenv(".env")
    settings = Settings()
    settings = settings.model_copy(
        update={
            "database_url": settings.migration_database_url or settings.database_url
        }
    )
    database = Database.from_settings(settings)
    assert database is not None, "Explicit development configuration required"
    try:
        with database.engine.begin() as connection:
            before = metadata(connection, "0013_public_contact_actions")
            definitions = catalog(connection)
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "0014_public_finder_messages")
            after = metadata(connection, "0014_public_finder_messages")
            updated = catalog(connection)
            assert before[1:] == after[1:], "Table, runtime role or row counts changed"
            for kind in definitions:
                if kind != "functions":
                    assert definitions[kind] == updated[kind], kind
            old_functions = dict(definitions["functions"])
            new_functions = dict(updated["functions"])
            assert new_functions.keys() - old_functions.keys() == {
                "sr_public_lost_qr_id",
                "sr_public_submit_finder_message",
                "sr_public_finder_budget",
            }
            for name, definition in old_functions.items():
                expected = definition
                if name == "sr_public_qr_projection":
                    for flag in ("finder_form_enabled", "location_sharing_available"):
                        expected = expected.replace(
                            f"'{flag}', false",
                            f"'{flag}', EXISTS(SELECT 1 FROM public.lost_item_profiles WHERE qr_id=qr.id AND published)",
                        )
                assert new_functions[name] == expected, name
        print("Applied only 0014; catalog, runtime roles and existing rows preserved.")
        print(
            f"RLS tables: {len(after[1])}; preserved domain rows: {sum(after[3].values())}"
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
