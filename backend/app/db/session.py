from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


class DatabaseConfigurationError(ValueError):
    """A deliberately non-disclosing database configuration failure."""


def database_url(value: str) -> URL:
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise DatabaseConfigurationError("Invalid PostgreSQL configuration") from None
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise DatabaseConfigurationError("PostgreSQL with psycopg is required")
    if not url.host or not url.database or not url.username:
        raise DatabaseConfigurationError(
            "PostgreSQL host, database and user are required"
        )
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        sslmode = url.query.get("sslmode", "require")
        if sslmode not in {"require", "verify-ca", "verify-full"}:
            raise DatabaseConfigurationError("Remote PostgreSQL requires TLS")
        url = url.update_query_dict({"sslmode": sslmode})
    return url.set(drivername="postgresql+psycopg")


class Database:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.sessions = sessionmaker(
            bind=engine, expire_on_commit=False, autoflush=False
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database | None":
        if (
            settings.database_url is None
            or not settings.database_url.get_secret_value()
        ):
            return None
        url = database_url(settings.database_url.get_secret_value())
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=0,
            pool_timeout=settings.database_pool_timeout_seconds,
            connect_args={
                "connect_timeout": settings.database_connect_timeout_seconds,
                "options": f"-c statement_timeout={settings.database_statement_timeout_ms}",
            },
            echo=False,
            hide_parameters=True,
        )
        return cls(engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        # No implicit commit: read/handler scopes close and roll back unfinished work.
        with self.sessions() as session:
            yield session

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        # Feature services explicitly choose this boundary, never HTTP dependencies.
        with self.sessions.begin() as session:
            yield session

    def is_available(self) -> bool:
        try:
            with self.engine.connect() as connection:
                return connection.execute(text("SELECT 1")).scalar_one() == 1
        except SQLAlchemyError:
            return False

    def close(self) -> None:
        self.engine.dispose()


def get_database(request: Request) -> Database | None:
    return request.app.state.database


def get_session(request: Request) -> Iterator[Session]:
    database = get_database(request)
    if database is None:
        raise HTTPException(status_code=503, detail="Service unavailable")
    with database.session() as session:
        yield session
