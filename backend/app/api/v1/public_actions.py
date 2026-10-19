"""Bounded anonymous finder submissions and protected public contact actions."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import AccessError
from app.api.v1.public_contacts import ContactRoute, failure, no_cache
from app.core.profile_crypto import ProfileCryptoUnavailable, encrypt
from app.core.turnstile import ChallengeRequired, challenge_binding, verify
from app.db.runtime import api_transaction

router = APIRouter(tags=["public actions"], route_class=ContactRoute)


class FinderLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)
    consent_accepted: bool | None = None
    consent_version: Literal["location-v1", "finder-location-v1"] | None = None


class FinderMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    finder_name: str | None = Field(default=None, max_length=80)
    finder_email: str | None = Field(default=None, max_length=254)
    finder_phone: str | None = Field(default=None, max_length=16)
    preferred_contact: str | None = Field(default=None, pattern="^(email|phone)$")
    message: str = Field(min_length=10, max_length=1000)
    contact_consent_accepted: bool = False
    consent_version: str = Field(
        pattern="^(finder-public-v1|finder-v1)$",
        validation_alias=AliasChoices("contact_consent_version", "consent_version"),
    )
    location: FinderLocation | None = None
    location_consent: bool = False
    turnstile_token: SecretStr | None = Field(default=None, max_length=2048)

    @field_validator("finder_email")
    @classmethod
    def valid_email(cls, value):
        if value is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Invalid email")
        return value

    @field_validator("finder_phone")
    @classmethod
    def valid_phone(cls, value):
        if value is not None and not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Invalid phone")
        return value

    @field_validator("message")
    @classmethod
    def meaningful_message(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("Message is too short")
        return value

    @model_validator(mode="after")
    def validate_consent_and_contact(self):
        if not self.contact_consent_accepted:
            raise ValueError("Contact consent is required")
        if not self.finder_email and not self.finder_phone:
            raise ValueError("A contact method is required")
        if self.preferred_contact and not getattr(
            self, f"finder_{self.preferred_contact}"
        ):
            raise ValueError("Preferred contact is missing")
        if self.location is not None:
            if self.location.consent_accepted is not None:
                if (
                    not self.location.consent_accepted
                    or not self.location.consent_version
                ):
                    raise ValueError("Location consent is required")
            elif not self.location_consent:
                raise ValueError("Location consent is required")
        return self


class FinderReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted"]


def valid_token(token):
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,80}", token))


def rate_limit(session, request, token, action):
    peer = request.client.host if request.client else "unknown"
    binding = hashlib.sha256(f"{action}:{peer}:{token}".encode()).hexdigest()
    return session.execute(
        text("SELECT public.sr_public_finder_budget(:binding,:peer)"),
        {
            "binding": binding,
            "peer": hashlib.sha256(f"{action}:{peer}".encode()).hexdigest(),
        },
    ).scalar_one()


@router.post(
    "/public/qr/{token}/messages",
    operation_id="API-011",
    response_model=FinderReceipt,
    status_code=202,
)
@router.post(
    "/public/qr/{token}/finder-messages",
    operation_id="API-015",
    response_model=FinderReceipt,
    status_code=202,
)
def submit_finder_message(
    token: str, body: FinderMessageRequest, request: Request, response: Response
):
    no_cache(response)
    if not valid_token(token):
        raise AccessError(404)
    database = request.app.state.database
    if database is None:
        raise AccessError(503)
    settings = request.app.state.settings
    now = datetime.now(UTC)
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key is not None and not re.fullmatch(
        r"[A-Za-z0-9_-]{16,100}", idempotency_key
    ):
        return failure(
            request,
            422,
            "VALIDATION_ERROR",
            "Invalid retry key.",
            "درخواست درست نہیں ہے۔",
        )
    request_hash = hashlib.sha256(
        json.dumps(
            body.model_dump(mode="json", exclude={"turnstile_token"}),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    location_values = (None,) * 7
    try:
        with api_transaction(database) as session:
            allowed = rate_limit(session, request, token, "finder-message")
        if not allowed:
            raise AccessError(429)
        proof = (
            body.turnstile_token.get_secret_value() if body.turnstile_token else None
        )
        verify(
            settings,
            proof,
            "finder_message",
            challenge_binding("finder_message", token),
            transport=getattr(request.app.state, "turnstile_transport", None),
        )
        with api_transaction(database) as session:
            fresh = session.execute(
                text("SELECT public.sr_public_contact_proof(:proof)"),
                {"proof": hashlib.sha256(proof.encode()).hexdigest()},
            ).scalar_one()
        if not fresh:
            raise ChallengeRequired()
        with api_transaction(database) as session:
            qr_id = session.execute(
                text("SELECT public.sr_public_lost_qr_id(:token)"),
                {"token": token},
            ).scalar_one_or_none()
            if qr_id is None:
                raise AccessError(404)
            email_ciphertext = (
                encrypt(settings, qr_id, "finder_email", body.finder_email)[0]
                if body.finder_email
                else None
            )
            phone_ciphertext = (
                encrypt(settings, qr_id, "finder_phone", body.finder_phone)[0]
                if body.finder_phone
                else None
            )
            message_ciphertext, message_version = encrypt(
                settings, qr_id, "finder_message", body.message
            )
            if body.location is not None:
                latitude, _ = encrypt(
                    settings, qr_id, "finder_latitude", str(body.location.latitude)
                )
                longitude, _ = encrypt(
                    settings, qr_id, "finder_longitude", str(body.location.longitude)
                )
                location_values = (
                    latitude,
                    longitude,
                    body.location.accuracy_m,
                    "browser_geolocation",
                    now,
                    body.location.consent_version or "finder-location-v1",
                    settings.profile_data_key_version,
                )
            message_id = session.execute(
                text(
                    """
                    SELECT public.sr_public_submit_finder_message(
                        :token,:name,:email,:phone,:contact_version,:preferred,
                        :message,:message_version,:consent,:consent_at,
                        :latitude,:longitude,:accuracy,:source,
                        :location_consent_at,:location_consent_version,:location_key_version,
                        :idempotency_key,:request_hash
                    )
                    """
                ),
                {
                    "token": token,
                    "name": body.finder_name,
                    "email": email_ciphertext,
                    "phone": phone_ciphertext,
                    "contact_version": settings.profile_data_key_version,
                    "preferred": body.preferred_contact,
                    "message": message_ciphertext,
                    "message_version": message_version,
                    "consent": body.consent_version,
                    "consent_at": now,
                    "latitude": location_values[0],
                    "longitude": location_values[1],
                    "accuracy": location_values[2],
                    "source": location_values[3],
                    "location_consent_at": location_values[4],
                    "location_consent_version": location_values[5],
                    "location_key_version": location_values[6],
                    "idempotency_key": idempotency_key,
                    "request_hash": request_hash,
                },
            ).scalar_one_or_none()
            if message_id is None:
                raise AccessError(404)
            if str(message_id) == "00000000-0000-0000-0000-000000000000":
                return failure(
                    request,
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "This retry key was used for a different message.",
                    "یہ درخواست پہلے مختلف پیغام کے لیے استعمال ہو چکی ہے۔",
                )
    except AccessError:
        raise
    except (ProfileCryptoUnavailable, SQLAlchemyError):
        raise AccessError(503) from None
    return {"status": "accepted"}


# Contact security has its own bounded-body route, independent of finder submission.
from app.api.v1.public_contacts import router as contact_router

router.include_router(contact_router)
