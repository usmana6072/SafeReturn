from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import AccessError, access_error
from app.api.v1.account import router as account_router
from app.api.v1.activation import router as activation_router
from app.api.v1.health import health_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.profiles import router as profiles_router
from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.db.session import Database


def create_app(
    settings: Settings | None = None, *, verifier: JWTVerifier | None = None
) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = Database.from_settings(configuration)
        application.state.database = database
        application.state.jwt_verifier = verifier or JWTVerifier(configuration)
        try:
            yield
        finally:
            if database is not None:
                database.close()
            application.state.jwt_verifier.close()
            application.state.jwt_verifier = None
            application.state.database = None

    application = FastAPI(title="SafeReturn API", version="0.1.0", lifespan=lifespan)
    application.state.database = None
    application.state.jwt_verifier = None
    application.state.settings = configuration
    application.add_exception_handler(AccessError, access_error)
    application.include_router(health_router(configuration), prefix="/api/v1")
    application.include_router(account_router, prefix="/api/v1")
    application.include_router(inventory_router, prefix="/api/v1")
    application.include_router(activation_router, prefix="/api/v1")
    application.include_router(profiles_router, prefix="/api/v1")
    return application


app = create_app()
