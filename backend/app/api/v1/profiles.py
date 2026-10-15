"""Owner-scoped independent QR profiles, encrypted contacts and consent (3.3)."""

import json
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    require_qr_owner,
    require_verified_account,
)
from app.api.v1.account import failure
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt


class ProfileRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe(request):
            if request.method in ("PUT", "POST", "PATCH"):
                if (
                    request.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    return failure(415, "UNSUPPORTED_MEDIA_TYPE", "JSON required.")
                payload = bytearray()
                async for chunk in request.stream():
                    payload.extend(chunk)
                    if len(payload) > 16384:
                        return failure(413, "FILE_TOO_LARGE", "Request is too large.")
                request._body = bytes(payload)
            try:
                return await handler(request)
            except RequestValidationError:
                return failure(400, "VALIDATION_ERROR", "Invalid profile request.")
            except ProfileCryptoUnavailable:
                raise AccessError(503) from None
            except ProfileError as error:
                return failure(error.status, error.code, error.message)

        return safe


router = APIRouter(tags=["profiles"], route_class=ProfileRoute)


class ProfileError(Exception):
    def __init__(
        self, status=400, code="VALIDATION_ERROR", message="Invalid profile request."
    ):
        self.status, self.code, self.message = status, code, message


class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="after")
    @classmethod
    def plain_text(cls, value):
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str):
            if (
                "<" in raw
                or ">" in raw
                or any(ord(c) < 32 and c not in "\n\t" for c in raw)
                or "\x7f" in raw
            ):
                raise ValueError("Plain text required")
            raw = raw.strip()
            return SecretStr(raw) if isinstance(value, SecretStr) else raw
        return value

    @model_validator(mode="after")
    def meaningful(self):
        if not self.model_fields_set:
            raise ValueError("Empty request")
        for name in (
            "published",
            "show_medical_notes",
            "display_order",
            "whatsapp_enabled",
            "relationship_label",
        ):
            if name in self.model_fields_set and getattr(self, name, False) is None:
                raise ValueError("Non-null field required")
        if "relationship_label" in self.model_fields_set and not getattr(
            self, "relationship_label", None
        ):
            raise ValueError("Relationship required")
        return self


class LostEdit(Edit):
    item_label: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    reward_text: str | None = Field(default=None, max_length=200)
    return_instructions: str | None = Field(default=None, max_length=1000)
    published: bool | None = None


class ICEEdit(Edit):
    display_name: str | None = Field(default=None, max_length=120)
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] | None = None
    emergency_instructions: str | None = Field(default=None, max_length=1000)
    medical_notes: SecretStr | None = Field(default=None, max_length=1000)
    show_medical_notes: bool | None = None
    published: bool | None = None
    publication_consent_accepted: bool = False
    publication_consent_version: Literal["ice-public-v1"] | None = None


class ContactEdit(Edit):
    relationship_label: str | None = Field(default=None, min_length=1, max_length=60)
    display_name: str | None = Field(default=None, max_length=120)
    phone: SecretStr | None = Field(default=None, min_length=8, max_length=16)
    display_order: int | None = Field(default=None, ge=0, le=100)
    published: bool | None = None
    publication_consent_accepted: bool = False
    publication_consent_version: Literal["ice-contact-v1"] | None = None


class PreferenceEdit(Edit):
    whatsapp_enabled: bool
    whatsapp_phone: SecretStr | None = Field(default=None, min_length=8, max_length=16)
    public_disclosure_consent: bool = False
    consent_version: Literal["wa-public-v1"] | None = None


def phone(value):
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ProfileError(message="An international E.164 phone number is required.")
    return value


def masked(value):
    return "••••" + value[-4:]


def response(data, version, status=200):
    return JSONResponse(
        data,
        status_code=status,
        headers={"Cache-Control": "no-store", "ETag": f'"{version}"'},
    )


def audit(context, qr_id, action, version, before, after, consent_version=None):
    details = {"version": version, "from_status": before, "to_status": after}
    if consent_version is not None:
        details["reason_code"] = consent_version
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,safe_details) VALUES(:actor,'customer',:action,'qr',:qr,CAST(:details AS jsonb))"
        ),
        {
            "actor": context.principal.user_id,
            "action": action,
            "qr": qr_id,
            "details": json.dumps(details),
        },
    )


def database_now(context):
    return context.session.execute(text("SELECT clock_timestamp()")).scalar_one()


def owned(context, qr_id, kind, write=False):
    require_qr_owner(context, qr_id, tag_type=kind)
    if write:
        require_verified_account(context)
        # Row locks require UPDATE policy visibility in PostgreSQL. Keep the
        # inventory policy restricted; a narrow definer verifies ownership again.
        locked = context.session.execute(
            text("SELECT public.sr_lock_profile_qr(:id,:purpose)"),
            {"id": qr_id, "purpose": kind},
        ).scalar_one()
        if not locked:
            raise AccessError(404)


TABLES = {
    "lost": "lost_item_profiles",
    "ice": "ice_profiles",
    "preferences": "tag_contact_preferences",
}


def read(context, qr_id, kind):
    return (
        context.session.execute(
            text(f"SELECT * FROM public.{TABLES[kind]} WHERE qr_id=:id"), {"id": qr_id}
        )
        .mappings()
        .one_or_none()
    )


def version_check(row, if_match):
    if not if_match or not re.fullmatch(r'"(?:0|[1-9][0-9]{0,9})"', if_match):
        raise ProfileError(message="A quoted current If-Match version is required.")
    if int(if_match[1:-1]) != (row["profile_version"] if row else 0):
        raise ProfileError(
            412, "VERSION_MISMATCH", "Profile changed. Reload and try again."
        )


def save(context, qr_id, kind, row, changes):
    table = TABLES[kind]
    if row is None:
        context.session.execute(
            text(f"INSERT INTO public.{table}(qr_id) VALUES(:id)"), {"id": qr_id}
        )
    version = row["profile_version"] + 1 if row else 1
    # Column names are internal allowlists; request fields never form SQL identifiers.
    assignments = ",".join(f"{name}=:{name}" for name in changes)
    context.session.execute(
        text(
            f"UPDATE public.{table} SET {assignments + ',' if assignments else ''}profile_version=:version,updated_at=clock_timestamp() WHERE qr_id=:id"
        ),
        {"id": qr_id, "version": version, **changes},
    )
    return version


def profile_data(context, qr_id, kind, settings, redact_unavailable=False):
    row = read(context, qr_id, kind)
    fields = (
        (
            "item_label",
            "description",
            "reward_text",
            "return_instructions",
            "published",
            "published_at",
        )
        if kind == "lost"
        else (
            "display_name",
            "blood_group",
            "emergency_instructions",
            "show_medical_notes",
            "published",
            "publication_consent_at",
            "publication_consent_version",
        )
    )
    data = {
        name: row[name]
        if row
        else (False if name in ("published", "show_medical_notes") else None)
        for name in fields
    }
    if kind == "ice":
        data["medical_notes"] = None
        data["medical_notes_redacted"] = False
        if row and row["medical_notes_ciphertext"]:
            try:
                data["medical_notes"] = decrypt(
                    settings,
                    qr_id,
                    "medical_notes",
                    row["medical_notes_ciphertext"],
                    row["medical_notes_key_version"],
                )
            except ProfileCryptoUnavailable:
                if not redact_unavailable:
                    raise
                data["medical_notes_redacted"] = True
    data.update(
        qr_id=str(qr_id),
        version=row["profile_version"] if row else 0,
        updated_at=row["updated_at"] if row else None,
    )
    for name, value in data.items():
        if isinstance(value, datetime):
            data[name] = value.isoformat()
    return response(data, data["version"])


@router.get("/me/qr/{qr_id}/lost-profile", operation_id="API-040")
def get_lost(qr_id: UUID, context: Authenticated, request: Request):
    owned(context, qr_id, "lost")
    return profile_data(context, qr_id, "lost", request.app.state.settings)


@router.put("/me/qr/{qr_id}/lost-profile", operation_id="API-041")
def put_lost(
    qr_id: UUID,
    body: LostEdit,
    context: Authenticated,
    request: Request,
    if_match: str | None = Header(default=None),
):
    owned(context, qr_id, "lost", True)
    row = read(context, qr_id, "lost")
    version_check(row, if_match)
    changes = body.model_dump(exclude_unset=True)
    publishing = changes.get("published", row["published"] if row else False)
    label = changes.get("item_label", row["item_label"] if row else None)
    if publishing and not label:
        raise ProfileError(message="A label is required for publication.")
    if "published" in changes:
        changes["published_at"] = (
            database_now(context) if changes["published"] else None
        )
    version = save(context, qr_id, "lost", row, changes)
    audit(
        context,
        qr_id,
        "profile.lost.updated",
        version,
        "published" if row and row["published"] else "private",
        "published" if publishing else "private",
    )
    return profile_data(context, qr_id, "lost", request.app.state.settings)


@router.get("/me/qr/{qr_id}/ice-profile", operation_id="API-042")
def get_ice(qr_id: UUID, context: Authenticated, request: Request):
    owned(context, qr_id, "ice")
    return profile_data(context, qr_id, "ice", request.app.state.settings)


@router.put("/me/qr/{qr_id}/ice-profile", operation_id="API-043")
def put_ice(
    qr_id: UUID,
    body: ICEEdit,
    context: Authenticated,
    request: Request,
    if_match: str | None = Header(default=None),
):
    owned(context, qr_id, "ice", True)
    row = read(context, qr_id, "ice")
    version_check(row, if_match)
    fields = body.model_fields_set - {
        "publication_consent_accepted",
        "publication_consent_version",
    }
    if not fields:
        raise ProfileError()
    changes = {name: getattr(body, name) for name in fields if name != "medical_notes"}
    published = changes.get("published", row["published"] if row else False)
    showing = changes.get(
        "show_medical_notes", row["show_medical_notes"] if row else False
    )
    if not published:
        showing = changes["show_medical_notes"] = False
    has_notes = (
        bool(body.medical_notes.get_secret_value())
        if "medical_notes" in fields and body.medical_notes is not None
        else bool(row and row["medical_notes_ciphertext"])
    )
    if "medical_notes" in fields and body.medical_notes is None:
        has_notes = False
    if showing and not has_notes:
        raise ProfileError(message="Medical notes are required before publication.")
    if published:
        if (
            not body.publication_consent_accepted
            or body.publication_consent_version != "ice-public-v1"
        ):
            raise ProfileError(
                422,
                "BUSINESS_RULE_VIOLATION",
                "Explicit ICE publication consent is required.",
            )
        if showing:
            authenticated = context.principal.authentication_time
            if (
                authenticated is None
                or not 0 <= datetime.now(UTC).timestamp() - authenticated <= 300
            ):
                raise ProfileError(
                    403,
                    "REAUTH_REQUIRED",
                    "Please sign in again before publishing medical notes.",
                )
            if "medical_notes" not in fields:
                decrypt(
                    request.app.state.settings,
                    qr_id,
                    "medical_notes",
                    row["medical_notes_ciphertext"],
                    row["medical_notes_key_version"],
                )
        changes.update(
            publication_consent_at=database_now(context),
            publication_consent_version=body.publication_consent_version,
        )
    if "medical_notes" in fields:
        value = body.medical_notes.get_secret_value() if body.medical_notes else ""
        encrypted, key_version = (
            encrypt(request.app.state.settings, qr_id, "medical_notes", value)
            if value
            else (None, None)
        )
        changes.update(
            medical_notes_ciphertext=encrypted, medical_notes_key_version=key_version
        )
    version = save(context, qr_id, "ice", row, changes)
    before = (
        "medical_published"
        if row and row["published"] and row["show_medical_notes"]
        else ("published" if row and row["published"] else "private")
    )
    after = (
        "medical_published"
        if published and showing
        else ("published" if published else "private")
    )
    audit(
        context,
        qr_id,
        "profile.ice.updated",
        version,
        before,
        after,
        body.publication_consent_version if published else None,
    )
    return profile_data(
        context, qr_id, "ice", request.app.state.settings, redact_unavailable=True
    )


def contact_phone(settings, qr_id, row, redact_unavailable):
    try:
        return masked(
            decrypt(
                settings,
                qr_id,
                "ice_phone",
                row["phone_ciphertext"],
                row["phone_key_version"],
                row["id"],
            )
        )
    except ProfileCryptoUnavailable:
        if not redact_unavailable:
            raise
        return None


def contacts_data(context, qr_id, settings, redact_unavailable=False):
    profile = read(context, qr_id, "ice")
    rows = (
        context.session.execute(
            text(
                "SELECT * FROM public.ice_contacts WHERE ice_qr_id=:id AND removed_at IS NULL ORDER BY display_order,id"
            ),
            {"id": qr_id},
        )
        .mappings()
        .all()
    )
    contacts = [
        {
            "contact_id": str(row["id"]),
            "relationship_label": row["relationship_label"],
            "display_name": row["display_name"],
            "display_order": row["display_order"],
            "published": row["published"],
            "phone_masked": contact_phone(settings, qr_id, row, redact_unavailable),
            "publication_consent_version": row["publication_consent_version"],
        }
        for row in rows
    ]
    version = profile["profile_version"] if profile else 0
    return response({"contacts": contacts, "version": version}, version)


@router.get("/me/qr/{qr_id}/ice-contacts", operation_id="API-044")
def get_contacts(qr_id: UUID, context: Authenticated, request: Request):
    owned(context, qr_id, "ice")
    return contacts_data(context, qr_id, request.app.state.settings)


def change_contact(context, qr_id, body, settings, if_match, contact_id=None):
    owned(context, qr_id, "ice", True)
    profile = read(context, qr_id, "ice")
    version_check(profile, if_match)
    current = None
    if contact_id is not None:
        current = (
            context.session.execute(
                text(
                    "SELECT * FROM public.ice_contacts WHERE id=:cid AND ice_qr_id=:qr AND removed_at IS NULL"
                ),
                {"cid": contact_id, "qr": qr_id},
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            raise AccessError(404)
    else:
        count = context.session.execute(
            text(
                "SELECT count(*) FROM public.ice_contacts WHERE ice_qr_id=:qr AND removed_at IS NULL"
            ),
            {"qr": qr_id},
        ).scalar_one()
        if count >= 3:
            raise ProfileError(
                422, "BUSINESS_RULE_VIOLATION", "At most three contacts are supported."
            )
    fields = body.model_fields_set - {
        "publication_consent_accepted",
        "publication_consent_version",
    }
    if not fields or (
        current is None and (not body.relationship_label or body.phone is None)
    ):
        raise ProfileError()
    changes = {name: getattr(body, name) for name in fields if name != "phone"}
    publishing = changes.get("published", current["published"] if current else False)
    if publishing:
        if (
            not body.publication_consent_accepted
            or body.publication_consent_version != "ice-contact-v1"
        ):
            raise ProfileError(
                422,
                "BUSINESS_RULE_VIOLATION",
                "Explicit contact publication consent is required.",
            )
        if current is not None and "phone" not in fields:
            decrypt(
                settings,
                qr_id,
                "ice_phone",
                current["phone_ciphertext"],
                current["phone_key_version"],
                current["id"],
            )
        changes.update(
            publication_consent_at=database_now(context),
            publication_consent_version=body.publication_consent_version,
        )
    contact_id = contact_id or uuid4()
    if "phone" in fields:
        if body.phone is None:
            raise ProfileError()
        encrypted, key_version = encrypt(
            settings,
            qr_id,
            "ice_phone",
            phone(body.phone.get_secret_value()),
            contact_id,
        )
        changes.update(phone_ciphertext=encrypted, phone_key_version=key_version)
    version = save(context, qr_id, "ice", profile, {})
    if current is None:
        names = list(changes)
        context.session.execute(
            text(
                f"INSERT INTO public.ice_contacts(id,ice_qr_id,{','.join(names)}) VALUES(:cid,:qr,{','.join(':' + name for name in names)})"
            ),
            {"cid": contact_id, "qr": qr_id, **changes},
        )
    else:
        context.session.execute(
            text(
                "UPDATE public.ice_contacts SET "
                + ",".join(f"{name}=:{name}" for name in changes)
                + ",updated_at=clock_timestamp() WHERE id=:cid AND ice_qr_id=:qr"
            ),
            {"cid": contact_id, "qr": qr_id, **changes},
        )
    audit(
        context,
        qr_id,
        "profile.ice_contact.updated",
        version,
        "published" if current and current["published"] else "private",
        "published" if publishing else "private",
        body.publication_consent_version if publishing else None,
    )
    return contact_id


@router.post("/me/qr/{qr_id}/ice-contacts", operation_id="API-045", status_code=201)
def add_contact(
    qr_id: UUID,
    body: ContactEdit,
    context: Authenticated,
    request: Request,
    if_match: str | None = Header(default=None),
):
    cid = change_contact(context, qr_id, body, request.app.state.settings, if_match)
    data = json.loads(
        contacts_data(context, qr_id, request.app.state.settings, True).body
    )
    result = next(
        contact for contact in data["contacts"] if contact["contact_id"] == str(cid)
    )
    return response({**result, "version": data["version"]}, data["version"], 201)


@router.patch("/me/qr/{qr_id}/ice-contacts/{contact_id}", operation_id="API-046")
def edit_contact(
    qr_id: UUID,
    contact_id: UUID,
    body: ContactEdit,
    context: Authenticated,
    request: Request,
    if_match: str | None = Header(default=None),
):
    change_contact(
        context, qr_id, body, request.app.state.settings, if_match, contact_id
    )
    data = json.loads(
        contacts_data(context, qr_id, request.app.state.settings, True).body
    )
    result = next(
        contact
        for contact in data["contacts"]
        if contact["contact_id"] == str(contact_id)
    )
    return response({**result, "version": data["version"]}, data["version"])


@router.delete(
    "/me/qr/{qr_id}/ice-contacts/{contact_id}", operation_id="API-047", status_code=204
)
def remove_contact(
    qr_id: UUID,
    contact_id: UUID,
    context: Authenticated,
    if_match: str | None = Header(default=None),
):
    owned(context, qr_id, "ice", True)
    profile = read(context, qr_id, "ice")
    version_check(profile, if_match)
    removed = context.session.execute(
        text(
            "UPDATE public.ice_contacts SET published=false,removed_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=:cid AND ice_qr_id=:qr AND removed_at IS NULL RETURNING id"
        ),
        {"cid": contact_id, "qr": qr_id},
    ).scalar_one_or_none()
    if removed is None:
        raise AccessError(404)
    version = save(context, qr_id, "ice", profile, {})
    audit(context, qr_id, "profile.ice_contact.removed", version, "present", "removed")
    return Response(
        status_code=204, headers={"Cache-Control": "no-store", "ETag": f'"{version}"'}
    )


def preference_data(context, qr_id, settings):
    row = read(context, qr_id, "preferences")
    enabled = row["whatsapp_enabled"] if row else False
    value = (
        masked(
            decrypt(
                settings,
                qr_id,
                "whatsapp_phone",
                row["whatsapp_phone_ciphertext"],
                row["whatsapp_phone_key_version"],
            )
        )
        if enabled
        else None
    )
    version = row["profile_version"] if row else 0
    return response(
        {
            "whatsapp_enabled": enabled,
            "whatsapp_phone_masked": value,
            "consent_recorded_at": row["whatsapp_consent_at"].isoformat()
            if enabled
            else None,
            "consent_version": row["whatsapp_consent_version"] if enabled else None,
            "version": version,
        },
        version,
    )


@router.get("/me/qr/{qr_id}/contact-preferences", operation_id="API-048")
def get_preferences(qr_id: UUID, context: Authenticated, request: Request):
    owned(context, qr_id, "lost")
    return preference_data(context, qr_id, request.app.state.settings)


@router.put("/me/qr/{qr_id}/contact-preferences", operation_id="API-049")
def put_preferences(
    qr_id: UUID,
    body: PreferenceEdit,
    context: Authenticated,
    request: Request,
    if_match: str | None = Header(default=None),
):
    owned(context, qr_id, "lost", True)
    row = read(context, qr_id, "preferences")
    version_check(row, if_match)
    changes = {"whatsapp_enabled": body.whatsapp_enabled}
    if body.whatsapp_enabled:
        if not body.public_disclosure_consent or body.consent_version != "wa-public-v1":
            raise ProfileError(
                422,
                "BUSINESS_RULE_VIOLATION",
                "Explicit public phone disclosure consent is required.",
            )
        if body.whatsapp_phone is not None:
            encrypted, key_version = encrypt(
                request.app.state.settings,
                qr_id,
                "whatsapp_phone",
                phone(body.whatsapp_phone.get_secret_value()),
            )
            changes.update(
                whatsapp_phone_ciphertext=encrypted,
                whatsapp_phone_key_version=key_version,
            )
        elif row is None or row["whatsapp_phone_ciphertext"] is None:
            raise ProfileError(message="A phone number is required.")
        else:
            decrypt(
                request.app.state.settings,
                qr_id,
                "whatsapp_phone",
                row["whatsapp_phone_ciphertext"],
                row["whatsapp_phone_key_version"],
            )
        changes.update(
            whatsapp_consent_at=database_now(context),
            whatsapp_consent_version=body.consent_version,
        )
    version = save(context, qr_id, "preferences", row, changes)
    audit(
        context,
        qr_id,
        "profile.whatsapp.updated",
        version,
        "enabled" if row and row["whatsapp_enabled"] else "disabled",
        "enabled" if body.whatsapp_enabled else "disabled",
        body.consent_version if body.whatsapp_enabled else None,
    )
    return preference_data(context, qr_id, request.app.state.settings)
