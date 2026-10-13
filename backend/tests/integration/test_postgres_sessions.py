"""Real PostgreSQL checks; opt in with a dedicated nonproduction test URL."""

import asyncio
import os

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import Database
from app.main import create_app


@pytest.fixture
def database():
    url = os.environ.get("SAFERETURN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Dedicated development PostgreSQL URL not configured")
    database = Database.from_settings(
        Settings(database_url=SecretStr(url), database_pool_size=1)
    )
    assert database is not None
    try:
        yield database
    finally:
        database.close()


def test_real_postgres_connection_and_read_scope(database):
    assert database.is_available() is True
    with database.session() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_real_postgres_commit_rollback_and_connection_reuse(database):
    # Session-local temporary table; no persistent schema or application data touched.
    with database.transaction() as session:
        session.execute(
            text(
                "CREATE TEMP TABLE safereturn_session_check (id integer) ON COMMIT PRESERVE ROWS"
            )
        )
        session.execute(text("INSERT INTO safereturn_session_check VALUES (1)"))
    with pytest.raises(RuntimeError), database.transaction() as session:
        session.execute(text("INSERT INTO safereturn_session_check VALUES (2)"))
        raise RuntimeError("force rollback")
    with database.session() as session:
        assert session.execute(
            text("SELECT array_agg(id ORDER BY id) FROM safereturn_session_check")
        ).scalar_one() == [1]
    assert database.engine.pool.checkedout() == 0


def test_real_postgres_protected_readiness_and_lifespan(database):
    app = create_app(
        Settings(
            database_url=SecretStr(os.environ["SAFERETURN_TEST_DATABASE_URL"]),
            readiness_token=SecretStr("synthetic-probe-token"),
        )
    )

    async def run():
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            assert (await client.get("/api/v1/health/ready")).status_code == 401
            response = await client.get(
                "/api/v1/health/ready",
                headers={"Authorization": "Bearer synthetic-probe-token"},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ready", "database": "ok"}
            assert response.headers["cache-control"] == "no-store"
            assert app.state.database.engine.pool.checkedout() == 0
        assert app.state.database is None

    asyncio.run(run())
