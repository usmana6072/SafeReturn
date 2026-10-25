"""Independent read-only support metadata routes; content is not admitted."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.api.auth import Authenticated
from app.services import support_metadata as service

PATH = "/api/v1/admin/support-case-metadata"
HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class MetadataRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except HTTPException as exc:
                code, status = exc.detail["code"], exc.status_code
            except RequestValidationError:
                code, status = "VALIDATION_ERROR", 422
            except ResponseValidationError:
                code, status = "PROVIDER_UNAVAILABLE", 503
            return JSONResponse(
                {
                    "error": {
                        "code": code,
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
                status_code=status,
                headers=HEADERS,
            )

        return handle


router = APIRouter(route_class=MetadataRoute, tags=["support case metadata"])


def parameters(fields):
    return [
        {"name": name, "in": "query", "required": False, "schema": schema}
        for name, schema in fields.items()
    ]


PAGING = {
    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    "cursor": {"type": "string", "maxLength": 2000},
}
LIST_QUERY = {
    **PAGING,
    "case_id": {"type": "string", "format": "uuid"},
    "case_type": {
        "type": "string",
        "enum": [
            "activation",
            "lost_tag",
            "payment",
            "privacy",
            "ownership_dispute",
            "other",
        ],
    },
    "status": {
        "type": "string",
        "enum": ["open", "investigating", "resolved", "closed"],
    },
    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
    "queue": {
        "type": "string",
        "enum": ["all", "mine", "unassigned"],
        "default": "all",
    },
}


@router.get(
    "/admin/support-case-metadata",
    response_model=service.Page,
    operation_id="support_metadata_list_v1",
    openapi_extra={"parameters": parameters(LIST_QUERY)},
)
def cases(context: Authenticated, request: Request):
    return service.listing(context, request)


@router.get(
    "/admin/support-case-metadata/{case_id}",
    response_model=service.Detail,
    operation_id="support_metadata_detail_v1",
)
def case(case_id: str, context: Authenticated, request: Request):
    return service.detail(context, request, case_id)


@router.get(
    "/admin/support-case-metadata/{case_id}/history",
    response_model=service.History,
    operation_id="support_metadata_history_v1",
    openapi_extra={"parameters": parameters(PAGING)},
)
def events(case_id: str, context: Authenticated, request: Request):
    return service.history(context, request, case_id)


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def metadata_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == PATH or request.url.path.startswith(PATH + "/"):
            response.headers.update(HEADERS)
        return response
