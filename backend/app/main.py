from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import AccessError, access_error
from app.api.v1.account import router as account_router
from app.api.v1.activation import router as activation_router
from app.api.v1.catalog import admin_router as admin_catalog_router
from app.api.v1.catalog import public_router as public_catalog_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.fulfillment import router as fulfillment_router
from app.api.v1.fulfillment_queries import router as fulfillment_queries_router
from app.api.v1.health import health_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.inventory_queries import router as inventory_queries_router
from app.api.v1.messages import router as messages_router
from app.api.v1.notification_operations import router as notification_operations_router
from app.api.v1.owner_qr import router as owner_qr_router
from app.api.v1.payments import router as payments_router
from app.api.v1.printing import router as printing_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.public_actions import router as public_actions_router
from app.api.v1.public_qr import router as public_qr_router
from app.api.v1.retention import router as retention_router
from app.api.v1.support_cases import router as support_cases_router
from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.observability import RequestObservabilityMiddleware
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
    application.add_middleware(RequestObservabilityMiddleware)
    application.state.database = None
    application.state.jwt_verifier = None
    application.state.settings = configuration
    application.add_exception_handler(AccessError, access_error)
    application.include_router(health_router(configuration), prefix="/api/v1")
    application.include_router(account_router, prefix="/api/v1")
    application.include_router(public_catalog_router, prefix="/api/v1")
    application.include_router(checkout_router, prefix="/api/v1")
    application.include_router(admin_catalog_router, prefix="/api/v1")
    application.include_router(inventory_router, prefix="/api/v1")
    application.include_router(inventory_queries_router, prefix="/api/v1")
    application.include_router(activation_router, prefix="/api/v1")
    application.include_router(profiles_router, prefix="/api/v1")
    application.include_router(owner_qr_router, prefix="/api/v1")
    application.include_router(public_qr_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    application.include_router(printing_router, prefix="/api/v1")
    application.include_router(fulfillment_router, prefix="/api/v1")
    application.include_router(fulfillment_queries_router, prefix="/api/v1")
    application.include_router(public_actions_router, prefix="/api/v1")
    application.include_router(notification_operations_router, prefix="/api/v1")
    application.include_router(messages_router, prefix="/api/v1")
    application.include_router(retention_router, prefix="/api/v1")
    application.include_router(support_cases_router, prefix="/api/v1")
    return application


app = create_app()
