"""Explicit anonymous contact actions: committed budgets, challenge, locked read."""

import base64
import hashlib
import re
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt
from app.core.turnstile import (
    ChallengeRequired,
    ChallengeUnavailable,
    challenge_binding,
    verify,
)
from app.db.runtime import api_transaction


def failure(request, status, code, en, ur):
    return JSONResponse(
        status_code=status,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Pragma": "no-cache",
        },
        content={
            "error": {
                "code": code,
                "message": en,
                "message_ur": ur,
                "request_id": getattr(request.state, "request_id", ""),
                "details": {"challenge": "turnstile"}
                if code == "CHALLENGE_REQUIRED"
                else {},
            }
        },
    )


class ContactRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe(request):
            if (
                request.headers.get("content-type", "").split(";")[0]
                != "application/json"
            ):
                return failure(
                    request,
                    415,
                    "UNSUPPORTED_MEDIA_TYPE",
                    "JSON required.",
                    "درخواست درست نہیں۔",
                )
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > 8192:
                    return failure(
                        request,
                        413,
                        "FILE_TOO_LARGE",
                        "Request is too large.",
                        "درخواست بہت بڑی ہے۔",
                    )
            request._body = bytes(data)
            try:
                return await handler(request)
            except RequestValidationError:
                return failure(
                    request,
                    400,
                    "VALIDATION_ERROR",
                    "Invalid contact request.",
                    "رابطے کی درخواست درست نہیں۔",
                )
            except ChallengeRequired:
                return failure(
                    request,
                    429,
                    "CHALLENGE_REQUIRED",
                    "Complete verification and try again.",
                    "تصدیق مکمل کر کے دوبارہ کوشش کریں۔",
                )
            except ChallengeUnavailable:
                raise AccessError(503) from None
            except ContactUnavailable:
                return failure(
                    request,
                    409,
                    "TAG_UNAVAILABLE",
                    "This tag is unavailable.",
                    "یہ ٹیگ فی الحال دستیاب نہیں۔",
                )

        return safe


class ContactUnavailable(Exception):
    pass


router = APIRouter(tags=["public actions"], route_class=ContactRoute)


class ContactRevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contact_id: UUID
    turnstile_token: SecretStr | None = Field(default=None, max_length=2048)


class WhatsAppRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal["open_chat"]
    turnstile_token: SecretStr | None = Field(default=None, max_length=2048)


class ContactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str
    tel_uri: str


class WhatsAppResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    disclosure: str


def contact_phone(request, token, proof, action, contact_id=None):
    database = request.app.state.database
    if database is None:
        raise AccessError(503)
    peer = request.client.host if request.client else "unknown"
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    try:
        # Commit attempts even when later validation, challenge, membership or
        # decryption fails. Do not borrow the activation/finder budget.
        with api_transaction(database) as session:
            allowed = session.execute(
                text("SELECT public.sr_public_contact_budget(:peer,:tag,:contact)"),
                {
                    "peer": digest(peer),
                    "tag": digest(f"{peer}:{token}"),
                    "contact": digest(f"{peer}:{token}:{contact_id or action}"),
                },
            ).scalar_one()
        if not allowed:
            raise AccessError(429)
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", token):
            raise AccessError(404)
        value = proof.get_secret_value() if proof else None
        verify(
            request.app.state.settings,
            value,
            action,
            challenge_binding(action, token, contact_id),
            transport=getattr(request.app.state, "turnstile_transport", None),
        )
        with api_transaction(database) as session:
            fresh = session.execute(
                text("SELECT public.sr_public_contact_proof(:proof)"),
                {"proof": digest(value)},
            ).scalar_one()
        if not fresh:
            raise ChallengeRequired()
        with api_transaction(database) as session:
            if contact_id is not None:
                result = session.execute(
                    text("SELECT public.sr_public_ice_contact(:token,:contact)"),
                    {"token": token, "contact": contact_id},
                ).scalar_one()
            else:
                result = session.execute(
                    text("SELECT public.sr_public_whatsapp_link(:token)"),
                    {"token": token},
                ).scalar_one()
            if result is None:
                raise AccessError(404)
            if result.get("unavailable"):
                raise ContactUnavailable()
            qr_id = UUID(result["qr_id"])
            ciphertext = base64.b64decode(result["ciphertext"], validate=True)
            phone = decrypt(
                request.app.state.settings,
                qr_id,
                "ice_phone" if contact_id else "whatsapp_phone",
                ciphertext,
                result["key_version"],
                contact_id,
            )
            if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
                raise ProfileCryptoUnavailable()
        return phone
    except (SQLAlchemyError, ProfileCryptoUnavailable, ValueError, KeyError, TypeError):
        raise AccessError(503) from None


def no_cache(response):
    response.headers.update(
        {
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Pragma": "no-cache",
            "X-Robots-Tag": "noindex, nofollow",
        }
    )


@router.post(
    "/public/qr/{token}/contact-reveals",
    operation_id="API-012",
    response_model=ContactResponse,
)
def reveal_contact(
    token: str, body: ContactRevealRequest, request: Request, response: Response
):
    no_cache(response)
    phone = contact_phone(
        request, token, body.turnstile_token, "ice_reveal", body.contact_id
    )
    return {"phone": phone, "tel_uri": f"tel:{phone}"}


@router.post(
    "/public/qr/{token}/whatsapp-link",
    operation_id="API-013",
    response_model=WhatsAppResponse,
)
def whatsapp_link(
    token: str, body: WhatsAppRequest, request: Request, response: Response
):
    no_cache(response)
    phone = contact_phone(request, token, body.turnstile_token, "whatsapp")
    return {
        "url": f"https://wa.me/{phone[1:]}?text={quote('Hello, I found your item')}",
        "disclosure": "This opens WhatsApp and reveals the owner's chosen contact number.",
    }
