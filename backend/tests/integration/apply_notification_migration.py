"""Apply only the reviewed notification revision with preservation checks."""

from alembic.config import Config
from dotenv import load_dotenv
from pg_rehearsal import catalog, metadata
from sqlalchemy import text

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
            before = metadata(connection, "0014_public_finder_messages")
            definitions = catalog(connection)
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "0014a_notification_delivery")
            after = metadata(connection, "0014a_notification_delivery")
            updated = catalog(connection)
            assert before[1:] == after[1:], (
                "Tables, runtime roles or existing row counts changed"
            )
            for kind in definitions:
                if kind != "functions":
                    assert definitions[kind] == updated[kind], kind
            old_functions, new_functions = (
                dict(definitions["functions"]),
                dict(updated["functions"]),
            )
            assert new_functions.keys() - old_functions.keys() == {
                "sr_notification_recipient"
            }
            for name, definition in old_functions.items():
                if name == "sr_public_submit_finder_message":
                    assert new_functions[name] == definition.replace(
                        "FOR SHARE OF q,p,l;", "FOR UPDATE OF p FOR SHARE OF q,l;"
                    )
                elif name == "sr_outbox_relation":
                    assert (
                        "Notification recipient snapshot is write-once under lease"
                        in new_functions[name]
                    )
                    assert (
                        "Notification recipient/aggregate mismatch"
                        in new_functions[name]
                    )
                else:
                    assert new_functions[name] == definition, name
            assert connection.execute(
                text(
                    "SELECT has_function_privilege('safereturn_worker','public.sr_notification_recipient(uuid,integer,bytea,smallint)','EXECUTE')"
                )
            ).scalar_one()
            assert not connection.execute(
                text(
                    "SELECT has_function_privilege('safereturn_api','public.sr_notification_recipient(uuid,integer,bytea,smallint)','EXECUTE')"
                )
            ).scalar_one()
            assert not connection.execute(
                text(
                    "SELECT has_table_privilege('safereturn_worker','auth.users','SELECT')"
                )
            ).scalar_one()
        print(
            "Applied only 0014a; tables, roles, existing rows and unrelated functions preserved."
        )
        print(
            f"RLS tables: {len(after[1])}; preserved domain rows: {sum(after[3].values())}"
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
