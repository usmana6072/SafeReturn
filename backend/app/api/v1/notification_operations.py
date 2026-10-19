"""Canonical metadata-only notification operations. Provider calls remain worker-only."""

import hashlib
import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, field_validator
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.api.v1.fulfillment import bounds, page_cursor, paged
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.workers.notifications import HTML, SUBJECT

router = APIRouter(tags=["notification operations"], route_class=CatalogRoute)
Status = Literal["pending", "leased", "retry", "sent", "dead"]


class Retry(Closed):
    expected_attempt_count: int = Field(ge=1, le=2147483647, strict=True)
    reason: Literal["provider_recovered", "recipient_reverified"]
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value


def budget(request):
    return request.app.state.settings.notification_max_attempts


@router.get("/admin/notification-outbox", operation_id="API-101")
def notifications(
    context: Authenticated,
    request: Request,
    limit: int = 20,
    cursor: str | None = None,
    status: Status | None = None,
    id: UUID | None = None,
    attempt_limit: int = 20,
    attempt_before: int | None = None,
):
    require_staff(context, "operations", "security_admin")
    bounds(limit)
    bounds(attempt_limit)
    if attempt_before is not None and not 1 <= attempt_before <= 2147483647:
        fail(422, "INVALID_ATTEMPT_CURSOR")
    stamp, ident = page_cursor(cursor)
    items = context.session.execute(
        text("""SELECT public.sr_notification_metadata(
      :lim,:stamp,:ident,:status,:id,:attempt_lim,:before,:budget)"""),
        {
            "lim": limit + 1,
            "stamp": stamp,
            "ident": ident,
            "status": status,
            "id": id,
            "attempt_lim": attempt_limit,
            "before": attempt_before,
            "budget": budget(request),
        },
    ).scalar_one()
    # SQL JSON has ISO strings; paging helper expects typed timestamps.
    for item in items:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
    result = paged(items, limit)
    result["current_template"] = {
        "identifier": "finder-message/v1",
        "fingerprint": hashlib.sha256((SUBJECT + "\n" + HTML).encode()).hexdigest(),
        "historical_version": "not_recorded",
        "review": "4.4C_pending",
    }
    return result


@router.post(
    "/admin/notification-outbox/{id}/retry", operation_id="API-102", status_code=202
)
def retry(id: UUID, body: Retry, context: Authenticated, request: Request):
    require_staff(context, "operations", "security_admin")
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    actor = context.principal.user_id
    operation = f"notification.retry:{id}"
    reference = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    session = context.session
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:reference,0))"),
        {"reference": reference},
    )
    params = {"scope": str(actor), "actor": actor, "op": operation, "key": key}
    old = (
        session.execute(
            text(
                "SELECT request_hash,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    settings = request.app.state.settings
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "notification:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        result = session.execute(
            text(
                "SELECT public.sr_notification_retry(:id,:expected,:budget,:reason,:request_id)"
            ),
            {
                "id": id,
                "expected": body.expected_attempt_count,
                "budget": budget(request),
                "reason": body.reason,
                "request_id": getattr(request.state, "request_id", None),
            },
        ).scalar_one()
        if "error" in result:
            fail(
                {"NOT_FOUND": 404, "STALE_ATTEMPT": 412, "INVALID_REQUEST": 422}.get(
                    result["error"], 409
                ),
                result["error"],
            )
        ciphertext, version = encrypt(
            settings, actor, "notification:" + reference, json.dumps(result)
        )
        session.execute(
            text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
        VALUES(:scope,:actor,:op,:key,:hash,'completed',202,:cipher,:version,now()+interval '1 day')"""),
            {**params, "hash": digest, "cipher": ciphertext, "version": version},
        )
        return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
