from fastapi import FastAPI

from app.api.v1.health import health_router
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(title="SafeReturn API", version="0.1.0")
    application.include_router(health_router(settings or Settings()), prefix="/api/v1")
    return application


app = create_app()
