import asyncio
import socket
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import Database, DatabaseConfigurationError, database_url
from app.main import create_app


def test_missing_url_keeps_database_disabled():
    assert Database.from_settings(Settings(database_url=None)) is None
    assert Database.from_settings(Settings(database_url=SecretStr(""))) is None


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "sqlite:///test.db",
        "postgresql+psycopg2://u:p@localhost/db",
        "postgresql://u:p@remote.example/db?sslmode=disable",
        "postgresql://u:p@localhost",
    ],
)
def test_invalid_database_configuration_is_safe(url):
    with pytest.raises(DatabaseConfigurationError) as error:
        database_url(url)
    assert url not in str(error.value)


def test_postgres_urls_use_psycopg_and_remote_tls():
    remote = database_url("postgres://user:synthetic-secret@db.example/test")
    assert remote.drivername == "postgresql+psycopg"
    assert remote.query["sslmode"] == "require"
    assert "synthetic-secret" not in str(remote)
    assert database_url("postgresql://user@localhost/test").query == {}
    assert (
        database_url("postgresql://user@remote.example/test?sslmode=verify-full").query[
            "sslmode"
        ]
        == "verify-full"
    )


def test_engine_configuration_is_lazy_bounded_and_hides_parameters():
    settings = Settings(
        database_url=SecretStr("postgresql://user:synthetic@localhost/test")
    )
    with patch("app.db.session.create_engine") as create:
        database = Database.from_settings(settings)
    assert database is not None
    options = create.call_args.kwargs
    assert options["pool_pre_ping"] is True
    assert options["max_overflow"] == 0
    assert options["hide_parameters"] is True
    assert options["echo"] is False
    assert options["connect_args"] == {
        "connect_timeout": 3,
        "options": "-c statement_timeout=5000",
    }
    create.return_value.connect.assert_not_called()


def test_readiness_connection_returns_to_pool_and_failure_is_false():
    engine = MagicMock(spec=Engine)
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = 1
    database = Database(engine)
    assert database.is_available() is True
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"
    engine.connect.return_value.__exit__.assert_called_once()
    engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("private"))
    assert database.is_available() is False


def test_session_scope_closes_without_implicit_commit():
    database = Database(MagicMock(spec=Engine))
    sessions = MagicMock()
    database.sessions = sessions
    session = sessions.return_value.__enter__.return_value
    with database.session() as scoped:
        assert scoped is session
    sessions.return_value.__exit__.assert_called_once()
    session.commit.assert_not_called()


def test_transaction_exception_reaches_transaction_context():
    database = Database(MagicMock(spec=Engine))
    sessions = MagicMock()
    database.sessions = sessions
    with pytest.raises(RuntimeError), database.transaction():
        raise RuntimeError("synthetic failure")
    assert sessions.begin.return_value.__exit__.call_args.args[0] is RuntimeError


def test_application_lifespan_disposes_engine_even_after_failure():
    database = MagicMock(spec=Database)
    app = create_app(Settings(database_url=None))

    async def run():
        with (
            patch("app.main.Database.from_settings", return_value=database),
            pytest.raises(RuntimeError),
        ):
            async with app.router.lifespan_context(app):
                assert app.state.database is database
                raise RuntimeError("synthetic failure")
        assert app.state.database is None

    asyncio.run(run())
    database.close.assert_called_once()


def test_real_psycopg_connection_failure_is_safe_and_liveness_stays_up():
    # A bound non-listening loopback socket provides an unavailable DB destination.
    # This exercises the actual installed driver, not successful PostgreSQL access.
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        app = create_app(
            Settings(
                readiness_token=SecretStr("synthetic-probe-token"),
                database_url=SecretStr(
                    f"postgresql://synthetic:private-password@127.0.0.1:{port}/synthetic"
                ),
            )
        )

        async def run():
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client,
            ):
                live = await client.get("/api/v1/health/live")
                assert live.status_code == 200
                ready = await client.get(
                    "/api/v1/health/ready",
                    headers={"Authorization": "Bearer synthetic-probe-token"},
                )
                assert ready.status_code == 503
                assert ready.json() == {
                    "status": "not_ready",
                    "database": "unavailable",
                }
                assert "private-password" not in ready.text
                assert app.state.database.engine.pool.checkedout() == 0
            assert app.state.database is None

        asyncio.run(run())
