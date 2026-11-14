"""Privileged creation of paired QR inventory (API-090)."""

import hashlib
import json
import re
import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.core.inventory_secrets import (
    InventoryCryptoUnavailable,
    activation_verifier,
    create_sealed_insert,
    load_recipient_public_key,
    manifest_checksum,
    new_activation_secret,
    new_public_token,
    verifier_key,
)

router = APIRouter()
OPERATION = "admin.qr-batches.create"
TEMPLATE_KEY = "safe-return-primary"


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    pair_count: int = Field(ge=1, le=1000)
    batch_label: str = Field(min_length=3, max_length=40)
    logo_template_key: Literal["safe-return-primary"]
    qr_ecc: Literal["M", "Q"]
    print_material: str = Field(min_length=2, max_length=60)
    intended_environment: Literal["indoor", "outdoor"]
    lost_symbol_size_mm: Decimal = Field(strict=False, ge=30, le=100, decimal_places=2)
    ice_symbol_size_mm: Decimal = Field(strict=False, ge=30, le=100, decimal_places=2)

    @model_validator(mode="after")
    def enforce_environment_minimum(self):
        minimum = Decimal(35) if self.intended_environment == "outdoor" else Decimal(30)
        if self.lost_symbol_size_mm < minimum or self.ice_symbol_size_mm < minimum:
            raise ValueError("QR symbols are below the approved physical minimum")
        return self

    @field_validator("batch_label")
    @classmethod
    def valid_label(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,39}", value):
            raise ValueError("Invalid batch label")
        return value

    @field_validator("print_material")
    @classmethod
    def valid_material(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Invalid print material")
        return value


class SealedInsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["safereturn-sealed-insert-v1"]
    wrapped_key: str
    nonce: str
    ciphertext: str


class BatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: uuid.UUID
    batch_label: str
    generated_pair_count: int
    generated_qr_count: int
    status: Literal["generated"]
    sealed_insert: SealedInsert


def _failure(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "message_ur": "درخواست مکمل نہیں ہو سکی۔",
                "request_id": uuid.uuid4().hex,
                "details": {},
            }
        },
        headers={"Cache-Control": "no-store"},
    )


def _response(batch_id, batch_label, pair_count, sealed_insert, *, status=201):
    return JSONResponse(
        status_code=status,
        content={
            "batch_id": str(batch_id),
            "batch_label": batch_label,
            "generated_pair_count": pair_count,
            "generated_qr_count": pair_count * 2,
            "status": "generated",
            # This is ciphertext for the separately held production-printer key.
            "sealed_insert": sealed_insert,
        },
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post(
    "/admin/qr-batches",
    operation_id="API-090",
    status_code=201,
    response_model=BatchResponse,
    responses={400: {"description": "Invalid request"}, 403: {"description": "Staff/MFA required"}, 409: {"description": "Conflict"}, 503: {"description": "Secure generation unavailable"}},
)
def create_qr_batch(
    body: BatchRequest,
    context: Authenticated,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_staff(context, "operations")
    if (
        not idempotency_key
        or not 8 <= len(idempotency_key) <= 160
        or not re.fullmatch(r"[A-Za-z0-9._:-]+", idempotency_key)
    ):
        return _failure(400, "IDEMPOTENCY_KEY_REQUIRED", "A valid idempotency key is required.")

    settings = request.app.state.settings
    try:
        key = verifier_key(settings.activation_verifier_key)
        printer_key = load_recipient_public_key(settings.print_recipient_public_key)
    except InventoryCryptoUnavailable:
        return _failure(503, "PROVIDER_UNAVAILABLE", "Inventory generation is unavailable.")

    actor_id = context.principal.user_id
    actor_scope = str(actor_id)
    public_key_fingerprint = hashlib.sha256(
        settings.print_recipient_public_key.get_secret_value().encode("ascii")
    ).hexdigest()
    request_model = {
        **body.model_dump(mode="json"),
        "verifier_key_version": settings.activation_verifier_key_version,
        "printer_key_fingerprint": public_key_fingerprint,
    }
    request_hash = hashlib.sha256(
        json.dumps(request_model, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    key_hash = hashlib.sha256(idempotency_key.encode("ascii")).hexdigest()
    context.session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:scope AS text),0::bigint))"),
        {"scope": f"{actor_scope}:{OPERATION}:{idempotency_key}"},
    )
    existing = context.session.execute(
        text("""
            SELECT request_hash,state,response_status,response_body_ciphertext,response_key_version
            FROM public.idempotency_records
            WHERE actor_scope=:scope AND operation=:operation AND idempotency_key=:key
            FOR UPDATE
        """),
        {"scope": actor_scope, "operation": OPERATION, "key": idempotency_key},
    ).mappings().one_or_none()
    if existing is not None:
        if existing["request_hash"] != request_hash:
            return _failure(409, "IDEMPOTENCY_CONFLICT", "This request key is already in use.")
        if existing["state"] != "completed" or existing["response_key_version"] != 1:
            return _failure(503, "PROVIDER_UNAVAILABLE", "Inventory generation is unavailable.")
        try:
            sealed_insert = json.loads(bytes(existing["response_body_ciphertext"]))
        except (TypeError, ValueError):
            return _failure(503, "PROVIDER_UNAVAILABLE", "Inventory generation is unavailable.")
        batch_id = context.session.execute(
            text("""
                SELECT target_id FROM public.audit_events
                WHERE actor_user_id=:actor AND actor_kind='staff'
                  AND action='inventory.qr_batch.generated' AND request_id=:request_id
                ORDER BY occurred_at DESC LIMIT 1
            """),
            {"actor": actor_id, "request_id": key_hash},
        ).scalar_one_or_none()
        if batch_id is None:
            return _failure(503, "PROVIDER_UNAVAILABLE", "Inventory generation is unavailable.")
        return _response(
            batch_id, body.batch_label, body.pair_count, sealed_insert, status=201
        )

    context.session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:label AS text),0::bigint))"),
        {"label": body.batch_label},
    )
    if context.session.execute(
        text("SELECT 1 FROM public.qr_batches WHERE batch_code=:code"),
        {"code": body.batch_label},
    ).scalar_one_or_none():
        return _failure(409, "BATCH_LABEL_CONFLICT", "This batch label already exists.")

    context.session.execute(
        text("""
            INSERT INTO public.idempotency_records(
                actor_scope,actor_user_id,operation,idempotency_key,request_hash,expires_at
            ) VALUES(:scope,:actor,:operation,:key,:request_hash,clock_timestamp()+interval '1 day')
        """),
        {
            "scope": actor_scope,
            "actor": actor_id,
            "operation": OPERATION,
            "key": idempotency_key,
            "request_hash": request_hash,
        },
    )

    batch_id = uuid.uuid4()
    verifier_version = settings.activation_verifier_key_version
    pair_rows = []
    qr_rows = []
    credential_rows = []
    manifest_pairs = []
    for index in range(1, body.pair_count + 1):
        pair_id = uuid.uuid4()
        pair_reference = f"SRP-{batch_id.hex[:8]}-{index:06d}"
        pair_rows.append({"id": pair_id, "reference": pair_reference, "batch": batch_id})
        tags = []
        for tag_type, suffix, size_mm in (
            ("lost", "L", body.lost_symbol_size_mm),
            ("ice", "I", body.ice_symbol_size_mm),
        ):
            token = new_public_token()
            qr_id = uuid.uuid4()
            qr_rows.append(
                {
                    "id": qr_id,
                    "pair": pair_id,
                    "tag_type": tag_type,
                    "serial": f"SR-{batch_id.hex[:10]}-{index:06d}-{suffix}",
                    "token": token,
                    "ecc": body.qr_ecc,
                    "size": size_mm,
                }
            )
            tags.append({"tag_type": tag_type, "public_token": token})
        secret = new_activation_secret()
        credential_rows.append(
            {
                "pair": pair_id,
                "verifier": activation_verifier(key, verifier_version, pair_id, secret),
                "version": verifier_version,
            }
        )
        manifest_pairs.append(
            {"pair_reference": pair_reference, "tags": tags, "activation_secret": secret}
        )

    manifest = {
        "format": "safereturn-production-insert-v1",
        "batch_id": str(batch_id),
        "batch_label": body.batch_label,
        "qr_ecc": body.qr_ecc,
        "logo_template_key": TEMPLATE_KEY,
        "print_material": body.print_material,
        "intended_environment": body.intended_environment,
        "lost_symbol_size_mm": str(body.lost_symbol_size_mm),
        "ice_symbol_size_mm": str(body.ice_symbol_size_mm),
        "pairs": manifest_pairs,
    }
    sealed_insert = create_sealed_insert(printer_key, manifest)
    checksum = manifest_checksum(sealed_insert)
    response_body = json.dumps(sealed_insert, sort_keys=True, separators=(",", ":")).encode()

    context.session.execute(
        text("""
            INSERT INTO public.qr_batches(id,batch_code,print_material,ecc_level,
                logo_template_key,intended_environment,print_manifest_checksum,status)
            VALUES(:id,:code,:material,:ecc,:template,:environment,:checksum,'generated')
        """),
        {
            "id": batch_id,
            "code": body.batch_label,
            "material": body.print_material,
            "ecc": body.qr_ecc,
            "template": TEMPLATE_KEY,
            "environment": body.intended_environment,
            "checksum": checksum,
        },
    )
    context.session.execute(
        text("""
            INSERT INTO public.tag_pairs(id,pair_reference,batch_id)
            VALUES(:id,:reference,:batch)
        """),
        pair_rows,
    )
    context.session.execute(
        text("""
            INSERT INTO public.qr_codes(id,pair_id,tag_type,serial_number,public_token,
                ecc_level,printed_size_mm)
            VALUES(:id,:pair,:tag_type,:serial,:token,:ecc,:size)
        """),
        qr_rows,
    )
    context.session.execute(
        text("""
            INSERT INTO public.pair_activation_credentials(pair_id,secret_verifier,verifier_key_version)
            VALUES(:pair,:verifier,:version)
        """),
        credential_rows,
    )
    context.session.execute(
        text("""
            INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,
                target_id,request_id,safe_details)
            VALUES(:actor,'staff','inventory.qr_batch.generated','qr_batch',:batch,:request_id,
                jsonb_build_object('outcome','success','reason_code','api_090'))
        """),
        {
            "actor": actor_id,
            "batch": batch_id,
            "request_id": key_hash,
        },
    )
    context.session.execute(
        text("""
            UPDATE public.idempotency_records
            SET state='completed',response_status=201,response_body_ciphertext=:body,
                response_key_version=1
            WHERE actor_scope=:scope AND operation=:operation AND idempotency_key=:key
        """),
        {
            "body": response_body,
            "scope": actor_scope,
            "operation": OPERATION,
            "key": idempotency_key,
        },
    )
    if settings.manufacturing_exports_enabled:
        from app.core.manufacturing import TransportConflict
        from app.core.manufacturing_custody import register_source
        from app.core.profile_crypto import ProfileCryptoUnavailable

        try:
            register_source(
                context.session,
                settings,
                batch_id,
                idempotency_key,
                request_model,
                [
                    {"pair_reference": p["pair_reference"], "tags": p["tags"]}
                    for p in manifest_pairs
                ],
                response_body,
            )
        except (TransportConflict, ProfileCryptoUnavailable):
            raise AccessError(503) from None
    return _response(batch_id, body.batch_label, body.pair_count, sealed_insert)
