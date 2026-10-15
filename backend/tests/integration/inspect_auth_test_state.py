"""Read-only Task 2.3 inspection after a rehearsal connection interruption."""

import os
from datetime import UTC, datetime

from pg_rehearsal import metadata
from sqlalchemy import create_engine, text

from app.db.session import database_url

engine = create_engine(
    database_url(os.environ["SAFERETURN_TEST_DATABASE_URL"]),
    hide_parameters=True,
    connect_args={"connect_timeout": 10},
)
try:
    with engine.connect() as connection:
        database_now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        print(
            "Database/client clock skew seconds:",
            round((database_now - datetime.now(UTC)).total_seconds()),
        )
        revision, tables, _, counts = metadata(connection)
        print(
            f"Head: {revision}; RLS tables: {len(tables)}; domain rows: {sum(counts.values())}"
        )
        print(
            "Temporary namespaces (name, owned):",
            connection.execute(
                text(
                    "SELECT nspname,pg_get_userbyid(nspowner)=current_user FROM pg_namespace WHERE starts_with(nspname,'sr15_') ORDER BY 1"
                )
            ).all(),
        )
        print(
            "Temporary table metadata:",
            connection.execute(
                text(
                    "SELECT table_schema,table_name FROM information_schema.tables WHERE starts_with(table_schema,'sr15_') ORDER BY 1,2"
                )
            ).all(),
        )
        print(
            "Task 2.3 fixture sessions (pid, state, wait):",
            connection.execute(
                text(
                    "SELECT pid,state,wait_event_type,wait_event FROM pg_stat_activity WHERE pid<>pg_backend_pid() AND usename=current_user AND query LIKE :marker"
                ),
                {"marker": "%sr15_%"},
            ).all(),
        )
finally:
    engine.dispose()
