"""API-005: anonymous closed configuration, independent of runtime credentials."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core import public_configuration as public

HEADERS = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}
router = APIRouter(tags=["public configuration"])


def failure(status: int):
    error = public.ErrorResponse(
        error=public.Error(
            code="VALIDATION_ERROR" if status == 422 else "PROVIDER_UNAVAILABLE",
            message="Invalid request."
            if status == 422
            else "Service temporarily unavailable.",
            details=public.ErrorDetails(),
        )
    )
    return JSONResponse(status_code=status, content=error.model_dump(), headers=HEADERS)


@router.get(
    "/public/config",
    operation_id="API-005",
    response_model=public.PublicConfiguration,
    responses={
        422: {"model": public.ErrorResponse},
        503: {"model": public.ErrorResponse},
    },
    openapi_extra={
        "parameters": [
            {
                "name": "lang",
                "in": "query",
                "required": False,
                "schema": {"type": "string", "enum": ["en", "ur"], "default": "en"},
            }
        ]
    },
)
async def get_public_config(request: Request, response: Response):
    params = list(request.query_params.multi_items())
    if (
        any(key != "lang" for key, _ in params)
        or len(params) > 1
        or (params and params[0][1] not in ("en", "ur"))
    ):
        return failure(422)
    # Reject at the first nonempty chunk; do not buffer arbitrary caller bodies.
    async for chunk in request.stream():
        if chunk:
            return failure(422)
    locale = params[0][1] if params else "en"
    try:
        result = public.configuration(public.REVIEWED_METADATA, locale)
    except (ValidationError, ValueError, TypeError, AttributeError):
        return failure(503)
    response.headers.update(HEADERS)
    return result
