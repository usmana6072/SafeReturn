"""Task 3.2: minimal scan context, actor-bound intent, atomic confirmation."""

import hashlib
import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError, Authenticated, require_verified_account
from app.api.v1.inventory import _failure
from app.core.inventory_secrets import (
    InventoryCryptoUnavailable,
    activation_verifier,
    verifier_key,
)
from app.db.runtime import api_transaction


class ActivationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request: Request):
            if request.method == "POST":
                payload = bytearray()
                async for chunk in request.stream():
                    payload.extend(chunk)
                    if len(payload) > 4096:
                        return _failure(413, "FILE_TOO_LARGE", "Request is too large.")
                request._body = bytes(payload)
            try:
                return await handler(request)
            except RequestValidationError:
                # FastAPI's default validation response may echo raw input secrets.
                return _failure(400, "VALIDATION_ERROR", "Invalid activation request.")

        return safe_handler


router = APIRouter(tags=["activation"], route_class=ActivationRoute)


def rate_limit(session, request):
    # Use the direct peer only; untrusted X-Forwarded-For cannot reset the bucket.
    peer = request.client.host if request.client else "unknown"
    digest = hashlib.sha256(peer.encode()).hexdigest()
    return session.execute(
        text("SELECT public.sr_activation_rate(:digest)"), {"digest": digest}
    ).scalar_one()


class IntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scanned_token: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    activation_secret: SecretStr | None = Field(
        default=None, min_length=12, max_length=256
    )


class ConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent_id: UUID
    confirm: bool = Field(strict=True)


class PublicActivationContext(BaseModel):
    status: Literal["not_activated"]
    can_begin: Literal[True]
    tag_type: Literal["lost", "ice"]
    context_ttl_seconds: int


class IntentResponse(BaseModel):
    intent_id: UUID
    pair_id: UUID
    lost_qr_id: UUID
    ice_qr_id: UUID
    expires_at: datetime
    method: Literal["order_entitlement", "concealed_credential"]


class ActivatedQR(BaseModel):
    qr_id: UUID
    tag_type: Literal["lost", "ice"]


class ActivationResponse(BaseModel):
    pair_id: UUID
    status: Literal["active"]
    activated_at: datetime
    qr_codes: list[ActivatedQR]


def decision(result):
    status = result.pop("_status")
    if status >= 400:
        code, message = {
            400: ("VALIDATION_ERROR", "Invalid activation request."),
            403: ("FORBIDDEN", "Activation is not permitted."),
            409: ("CONFLICT", "This kit cannot be activated."),
            429: ("RATE_LIMITED", "Please try again later."),
        }[status]
        response = _failure(status, code, message)
        if status == 429:
            response.headers["Retry-After"] = "900"
        return response
    return JSONResponse(
        result, status_code=status, headers={"Cache-Control": "no-store"}
    )


@router.get(
    "/public/qr/{token}/activation-context",
    operation_id="API-207",
    response_model=PublicActivationContext,
)
def activation_context(token: str, request: Request):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", token):
        raise AccessError(404)
    database = request.app.state.database
    if database is None:
        raise AccessError(503)
    try:
        with api_transaction(database) as session:
            if not rate_limit(session, request):
                return decision({"_status": 429})
            result = session.execute(
                text("SELECT public.sr_activation_context(:token)"), {"token": token}
            ).scalar_one()
    except SQLAlchemyError:
        raise AccessError(503) from None
    if result is None:
        raise AccessError(404)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@router.post(
    "/me/tag-pairs/activation-intents",
    operation_id="API-208",
    status_code=201,
    response_model=IntentResponse,
)
def begin_activation(body: IntentRequest, context: Authenticated, request: Request):
    require_verified_account(context)
    if not rate_limit(context.session, request):
        return decision({"_status": 429})
    proof = None
    version = None
    if body.activation_secret is not None:
        settings = request.app.state.settings
        try:
            key = verifier_key(settings.activation_verifier_key)
        except InventoryCryptoUnavailable:
            raise AccessError(503) from None
        row = context.session.execute(
            text("SELECT * FROM public.sr_activation_key_context(:token)"),
            {"token": body.scanned_token},
        ).one_or_none()
        version = settings.activation_verifier_key_version
        if row is not None and row.key_version != version:
            # A missing historical key must not consume the customer's guess budget.
            raise AccessError(503)
        # Unknown tokens still traverse the durable attempt accounting command.
        pair_id = row.pair_id if row is not None else UUID(int=0)
        try:
            proof = activation_verifier(
                key, version, pair_id, body.activation_secret.get_secret_value()
            )
        except UnicodeEncodeError:
            proof = bytes(32)
    result = context.session.execute(
        text("SELECT public.sr_begin_activation(:token,:proof,:version)"),
        {"token": body.scanned_token, "proof": proof, "version": version},
    ).scalar_one()
    # Return an error response, rather than raise: attempt/lockout accounting must commit.
    return decision(result)


@router.post(
    "/me/tag-pairs/activations",
    operation_id="API-032",
    status_code=201,
    response_model=ActivationResponse,
)
def confirm_activation(
    body: ConfirmationRequest,
    context: Authenticated,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_verified_account(context)
    if (
        body.confirm is not True
        or not idempotency_key
        or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", idempotency_key)
    ):
        return decision({"_status": 400})
    digest = hashlib.sha256(
        json.dumps(
            body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return decision(
        context.session.execute(
            text("SELECT public.sr_confirm_activation(:iid,:key,:digest)"),
            {"iid": body.intent_id, "key": idempotency_key, "digest": digest},
        ).scalar_one()
    )
