"""Explicit environment loading; never put connection strings in alembic.ini."""

from alembic import context
from app.core.config import Settings
from app.db import commerce  # noqa: F401 -- register commerce mappings
from app.db.models import Base
from app.db.session import Database


def include_object(obj, name, type_, reflected, compare_to):
    return getattr(obj, "schema", None) != "auth"


def migrate(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Offline execution disabled: inspect target metadata first")
elif context.config.attributes.get("connection") is not None:
    migrate(context.config.attributes["connection"])
else:
    database = Database.from_settings(Settings())
    if database is None:
        raise RuntimeError("Load development database environment explicitly")
    try:
        with database.engine.connect() as connection:
            migrate(connection)
    finally:
        database.close()
