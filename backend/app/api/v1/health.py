from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings
from app.db.session import Database, get_database


class Liveness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"


class ReadinessUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["not_ready"] = "not_ready"
    database: Literal["unavailable"] = "unavailable"


class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready"] = "ready"
    database: Literal["ok"] = "ok"


def health_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])
    bearer = HTTPBearer(auto_error=False, scheme_name="InternalReadinessProbe")

    @router.get("/live", response_model=Liveness, operation_id="API-001")
    def live() -> Liveness:
        return Liveness()

    @router.get(
        "/ready",
        response_model=Readiness,
        operation_id="API-002",
        responses={
            401: {"description": "Probe authorization required"},
            404: {"description": "Probe disabled"},
            503: {"model": ReadinessUnavailable, "description": "Database unavailable"},
        },
    )
    def ready(
        response: Response,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        database: Annotated[Database | None, Depends(get_database)],
    ) -> Readiness | JSONResponse:
        response.headers["Cache-Control"] = "no-store"
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
        if database is not None and database.is_available():
            return Readiness()
        return JSONResponse(
            status_code=503,
            content=ReadinessUnavailable().model_dump(),
            headers={"Cache-Control": "no-store"},
        )

    return router
