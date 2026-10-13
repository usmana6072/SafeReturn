from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import health_router
from app.core.config import Settings
from app.db.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = Database.from_settings(configuration)
        application.state.database = database
        try:
            yield
        finally:
            if database is not None:
                database.close()
            application.state.database = None

    application = FastAPI(title="SafeReturn API", version="0.1.0", lifespan=lifespan)
    application.state.database = None
    application.include_router(health_router(configuration), prefix="/api/v1")
    return application


app = create_app()
