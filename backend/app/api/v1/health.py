from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings


class Liveness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"


class ReadinessUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["not_ready"] = "not_ready"
    database: Literal["unavailable"] = "unavailable"


def health_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])
    bearer = HTTPBearer(auto_error=False, scheme_name="InternalReadinessProbe")

    @router.get("/live", response_model=Liveness, operation_id="API-001")
    def live() -> Liveness:
        return Liveness()

    @router.get(
        "/ready",
        response_model=ReadinessUnavailable,
        status_code=503,
        operation_id="API-002",
        responses={401: {"description": "Probe authorization required"}},
    )
    def ready(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> ReadinessUnavailable:
        token = settings.readiness_token
        if token is None or not token.get_secret_value():
            raise HTTPException(status_code=404, detail="Not Found")
        if credentials is None or not compare_digest(
            credentials.credentials.encode(), token.get_secret_value().encode()
        ):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Database connectivity and migrations belong to Phase 1. Never claim ready.
        return ReadinessUnavailable()

    return router
