"""Anonymous, allowlisted public QR projections (Task 4.1)."""

import hashlib
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError
from app.db.runtime import api_transaction

router = APIRouter(tags=["public QR"])


class PublicFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finder_form_enabled: bool
    whatsapp_contact_enabled: bool
    location_sharing_available: bool


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_available: bool
    disclosure_notice: str


class LostItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None
    description: str | None
    reward_text: str | None


class PublicContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID
    relationship_label: str
    display_name: str | None
    reveal_available: bool


class ICEProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None
    blood_group: str | None
    medical_notes: None = None
    contacts: list[PublicContact]
    owner_information_disclaimer: str


class PublicQRProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag_type: Literal["lost", "ice"]
    status: Literal[
        "unactivated", "active", "owner_disabled", "admin_suspended", "revoked"
    ]
    locale_options: list[Literal["en", "ur"]]
    lost_item: LostItem | None = None
    features: PublicFeatures | None = None
    whatsapp_contact: WhatsAppContact | None = None
    ice: ICEProfile | None = None


@router.get(
    "/public/qr/{token}",
    operation_id="API-010",
    response_model=PublicQRProfile,
    response_model_exclude_unset=True,
)
def get_public_qr(token: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    database = request.app.state.database
    if database is None:
        raise AccessError(503)
    try:
        # A separate committed budget counts misses too; forwarded headers are
        # untrusted until the deployment proxy boundary is explicitly configured.
        peer = request.client.host if request.client else "unknown"
        digest = hashlib.sha256(peer.encode()).hexdigest()
        with api_transaction(database) as session:
            allowed = session.execute(
                text("SELECT public.sr_public_scan_rate(:binding)"),
                {"binding": digest},
            ).scalar_one()
        if not allowed:
            raise AccessError(429)
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", token):
            raise AccessError(404)
        with api_transaction(database) as session:
            payload = session.execute(
                text("SELECT public.sr_public_qr_projection(:token)"),
                {"token": token},
            ).scalar_one()
    except SQLAlchemyError:
        raise AccessError(503) from None
    if payload is None:
        raise AccessError(404)
    return payload
