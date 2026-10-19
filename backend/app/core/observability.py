"""Request correlation and sanitized structured access logging."""

import json
import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("safereturn.http")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid4().hex
        request.state.request_id = request_id
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            self._log(
                request,
                request_id,
                status_code,
                round((perf_counter() - started) * 1000, 2),
            )

    @staticmethod
    def _log(
        request: Request, request_id: str, status_code: int, duration_ms: float
    ) -> None:
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "http.request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(route, "path", None),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "service": "api",
                    "version": "0.1.0",
                },
                separators=(",", ":"),
            )
        )
