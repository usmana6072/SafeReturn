"""Authoritative private-object deletion confirmation; no response bodies logged."""

import logging
from urllib.parse import quote
from uuid import uuid4


class _PrivateHTTPLogFilter(logging.Filter):
    def filter(self, record):
        # HTTPX's INFO access record normally includes the full private URL.
        # Keep method/status telemetry while discarding URL and exception data.
        args = record.args if isinstance(record.args, tuple) else ()
        method = (
            args[0]
            if args
            and isinstance(args[0], str)
            and args[0] in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
            else "request"
        )
        status = args[3] if len(args) > 3 and isinstance(args[3], int) else "unknown"
        record.msg, record.args = "http.client method=%s status=%s", (method, status)
        record.exc_info = record.stack_info = None
        record.exc_text = None
        return True


logging.getLogger("httpx").addFilter(_PrivateHTTPLogFilter())
# Wire-level DEBUG includes response headers; it is inappropriate for private I/O.
logging.getLogger("httpcore").setLevel(logging.WARNING)


def object_missing(response) -> bool:
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    response.read()
    try:
        error = response.json()
    except ValueError:
        return False
    return (
        isinstance(error, dict)
        and str(error.get("statusCode")) == "404"
        and (
            error.get("code") == "NoSuchKey"
            or (
                error.get("error") == "not_found"
                and error.get("message") == "Object not found"
            )
        )
    )


def delete_private_object(client, bucket: str, key: str) -> bool:
    if (
        not key
        or key.startswith("/")
        or any(p in {"", ".", ".."} for p in key.split("/"))
    ):
        raise ValueError("invalid_object_key")
    bucket_response = client.get("bucket/" + bucket)
    if (
        bucket_response.status_code != 200
        or bucket_response.json().get("public") is not False
    ):
        raise OSError("private_bucket_unverified")
    path = bucket + "/" + quote(key, safe="/")
    response = client.delete("object/" + path)
    if response.status_code not in (200, 204) and not object_missing(response):
        raise OSError("storage_delete_failed")
    # A successful DELETE acknowledgement alone is insufficient. Authenticate
    # directly to storage; redirects, auth failures and outages are not absence.
    with client.stream(
        "GET",
        "object/info/authenticated/" + path,
        params={"verification": uuid4().hex},
        headers={"Cache-Control": "no-cache"},
    ) as verification:
        # Supabase's legacy REST gateway can wrap a storage 404 in HTTP 400.
        # Accept only its typed missing-object response, never generic 400,
        # authorization failures, or an unavailable/missing bucket.
        if object_missing(verification):
            return True
        raise OSError("storage_delete_unconfirmed")
    return True
