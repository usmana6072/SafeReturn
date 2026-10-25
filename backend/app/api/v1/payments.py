"""Manual bank review and private evidence; never trusts screenshots as settlement."""

import base64
import hashlib
import hmac
import json
import re
import time
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import (
    AccessError,
    Authenticated,
    require_order_owner,
    require_payment_owner,
    require_staff,
    require_verified_account,
)
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.integrations.payment_storage import storage

router = APIRouter(tags=["payments"], route_class=CatalogRoute)


@router.get("/me/orders/{order_id}/payment-instructions", operation_id="order-payment-instructions")
def payment_instructions(order_id: UUID, context: Authenticated):
    require_verified_account(context)
    require_order_owner(context, order_id)
    value = context.session.execute(text("SELECT to_jsonb(o)->'payment_instructions_snapshot' FROM public.orders o WHERE id=:id"), {"id": order_id}).scalar_one_or_none()
    if value is None:
        fail(503, "PAYMENT_INSTRUCTIONS_UNAVAILABLE")
    return value


class PaymentRequest(Closed):
    provider_key: Literal["manual_bank"] = "manual_bank"
    sender_account: str = Field(min_length=4, max_length=80)
    sender_holder_name: str = Field(min_length=1, max_length=160)
    transfer_reference: str | None = Field(default=None, max_length=120)


class UploadRequest(Closed):
    filename: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}\.(?:png|jpg|jpeg|pdf)$")
    content_type: Literal["image/png", "image/jpeg", "application/pdf"]
    bytes_size: int = Field(gt=0, le=5_000_000, strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceRequest(Closed):
    upload_token: str = Field(min_length=40, max_length=4000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReviewRequest(Closed):
    decision: Literal["verify", "reject", "request_more_info"]
    bank_verified: bool = Field(default=False, strict=True)
    bank_match_reference: str | None = Field(default=None, min_length=4, max_length=120)
    settled_amount: str | None = Field(default=None, pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    settled_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    reason: str = Field(min_length=4, max_length=1000)


class AllocationRetry(Closed):
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def confirmation(cls, value):
        if not value:
            raise ValueError("Explicit allocation confirmation required")
        return value


def typed_result(value):
    if value is None:
        raise AccessError(404)
    if "error" in value:
        code = value["error"]
        if code in {"FORBIDDEN", "NOT_FOUND"}:
            raise AccessError(403 if code == "FORBIDDEN" else 404)
        fail(422 if code == "BANK_VERIFICATION_REQUIRED" else 409, code)
    return value


def lock_order(context, order_id):
    return (
        context.session.execute(
            text("SELECT * FROM public.orders WHERE id=:id FOR UPDATE"),
            {"id": order_id},
        )
        .mappings()
        .one()
    )


def lock_attempt(context, attempt_id):
    # Consistent order -> attempt -> reservation -> pair lock ordering.
    oid = context.session.execute(
        text("SELECT order_id FROM public.payment_attempts WHERE id=:id"),
        {"id": attempt_id},
    ).scalar_one_or_none()
    if oid is None:
        raise AccessError(404)
    order = lock_order(context, oid)
    attempt = (
        context.session.execute(
            text("SELECT * FROM public.payment_attempts WHERE id=:id FOR UPDATE"),
            {"id": attempt_id},
        )
        .mappings()
        .one()
    )
    return order, attempt


def record(context, request, operation, payload, work):
    require_verified_account(context)
    s = request.app.state.settings
    session = context.session
    from app.db.template_registry import gate
    gate(session)
    actor = context.principal.user_id
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    canonical = json.dumps(
        jsonable_encoder(payload), sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    reference = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {
            "key": f"{actor}:{operation}"
            if operation.startswith("evidence.upload:")
            else reference
        },
    )
    params = {"scope": str(actor), "actor": actor, "op": operation, "key": key}
    old = (
        session.execute(
            text(
                "SELECT * FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    s,
                    actor,
                    "payment:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with session.begin_nested():
            result, target = work(s)
            result = jsonable_encoder(result, custom_encoder={Decimal: str})
            cipher, version = encrypt(
                s, actor, "payment:" + reference, json.dumps(result)
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
   VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:version,now()+interval '1 day')"""),
                {
                    **params,
                    "hash": digest,
                    "cipher": cipher,
                    "version": version,
                    "status": 201 if operation == "payment.create" else 200,
                },
            )
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
   VALUES(:actor,:kind,:op,:target_type,:target,:rid,'payment command',jsonb_build_object('event_id',CAST(:reference AS text),'outcome','success'))"""),
                {
                    "actor": actor,
                    "kind": "staff" if operation in {"payment.review", "allocation.retry"} else "customer",
                    "target_type": "order" if operation == "allocation.retry" else "payment",
                    "op": operation,
                    "target": target,
                    "rid": getattr(request.state, "request_id", None),
                    "reference": reference,
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "PAYMENT_CONFLICT")


@router.post(
    "/me/orders/{order_id}/payment-attempts", operation_id="API-210", status_code=201
)
def create_payment_attempt(
    order_id: UUID, body: PaymentRequest, context: Authenticated, request: Request
):
    require_verified_account(context)
    require_order_owner(context, order_id)

    def work(s):
        order = lock_order(context, order_id)
        if (
            order["payment_status"] in {"verified", "refunded"}
            or order["order_status"] != "placed"
        ):
            fail(409, "PAYMENT_CLOSED")
        active = context.session.execute(
            text(
                "SELECT 1 FROM public.payment_attempts WHERE order_id=:id AND state IN ('initiated','submitted','under_review','disputed')"
            ),
            {"id": order_id},
        ).first()
        if active:
            fail(409, "PAYMENT_ALREADY_PENDING")
        aid = uuid4()
        account, version = encrypt(s, aid, "sender_account", body.sender_account)
        holder, _ = encrypt(
            s,
            aid,
            "sender_holder",
            json.dumps(
                {
                    "holder": body.sender_holder_name,
                    "transfer_reference": body.transfer_reference,
                }
            ),
        )
        context.session.execute(
            text("""INSERT INTO public.payment_attempts(id,order_id,provider_key,idempotency_key,amount,currency_code,state,sender_account_ciphertext,sender_holder_ciphertext,sender_key_version,sender_reference_masked)
        VALUES(:id,:oid,'manual_bank',:key,:amount,:currency,'submitted',:account,:holder,:version,:masked)"""),
            {
                "id": aid,
                "oid": order_id,
                "key": hashlib.sha256(
                    f"{context.principal.user_id}:{request.headers['idempotency-key']}".encode()
                ).hexdigest(),
                "amount": order["total_pkr"],
                "currency": order["currency_code"],
                "account": account,
                "holder": holder,
                "version": version,
                "masked": "****" + body.sender_account[-4:],
            },
        )
        context.session.execute(
            text(
                "UPDATE public.payment_attempts SET state='under_review' WHERE id=:id"
            ),
            {"id": aid},
        )
        context.session.execute(
            text("UPDATE public.orders SET payment_status='under_review' WHERE id=:id"),
            {"id": order_id},
        )
        return {
            "attempt_id": str(aid),
            "state": "under_review",
            "sender_account_masked": "****" + body.sender_account[-4:],
            "evidence_upload_allowed": True,
            "payment_due": f"{order['total_pkr']:.2f}",
            "currency_code": order["currency_code"],
        }, aid

    return record(
        context,
        request,
        "payment.create",
        dict(order_id=str(order_id), **body.model_dump()),
        work,
    )


@router.get("/me/orders/{order_id}/payment-attempts", operation_id="API-209")
def list_payment_attempts(order_id: UUID, context: Authenticated):
    require_verified_account(context)
    require_order_owner(context, order_id)
    rows = context.session.execute(
        text(
            "SELECT id,provider_key,state,amount,currency_code,sender_reference_masked,created_at FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC"
        ),
        {"id": order_id},
    ).mappings()
    return {"items": [dict(r, amount=f"{r['amount']:.2f}") for r in rows]}


@router.post(
    "/me/payment-attempts/{attempt_id}/evidence-uploads", operation_id="API-211"
)
def authorize_evidence_upload(
    attempt_id: UUID, body: UploadRequest, context: Authenticated, request: Request
):
    require_verified_account(context)
    require_payment_owner(context, attempt_id)

    def work(s):
        a = (
            context.session.execute(
                text("SELECT state FROM public.payment_attempts WHERE id=:id"),
                {"id": attempt_id},
            )
            .mappings()
            .one()
        )
        if a["state"] not in {"under_review", "submitted", "initiated"}:
            fail(409, "PAYMENT_CLOSED")
        count = context.session.execute(
            text(
                "SELECT count(*) FROM public.idempotency_records WHERE actor_user_id=:uid AND operation=:op"
            ),
            {
                "uid": context.principal.user_id,
                "op": "evidence.upload:" + str(attempt_id),
            },
        ).scalar_one()
        if count >= 5:
            fail(429, "RATE_LIMITED")
        object_key = f"payment-evidence/{attempt_id}/{uuid4()}"
        # Provider request is bounded; upload capability cannot overwrite an existing object.
        url = storage(request).authorize(object_key)
        payload = dict(
            body.model_dump(),
            object_key=object_key,
            expires=int(time.time()) + 300,
            attempt_id=str(attempt_id),
        )
        token, version = encrypt(
            s, context.principal.user_id, "evidence-upload", json.dumps(payload)
        )
        return {
            "upload_token": str(version)
            + "."
            + base64.urlsafe_b64encode(token).decode(),
            "upload_url": url,
            "expires_in_seconds": 300,
            "max_bytes": 5_000_000,
        }, attempt_id

    return record(
        context, request, "evidence.upload:" + str(attempt_id), body.model_dump(), work
    )


@router.post(
    "/me/payment-attempts/{attempt_id}/evidence-finalize", operation_id="API-212"
)
def finalize_evidence(
    attempt_id: UUID, body: EvidenceRequest, context: Authenticated, request: Request
):
    require_verified_account(context)
    require_payment_owner(context, attempt_id)
    try:
        version, encoded = body.upload_token.split(".", 1)
        payload = json.loads(
            decrypt(
                request.app.state.settings,
                context.principal.user_id,
                "evidence-upload",
                base64.urlsafe_b64decode(encoded),
                int(version),
            )
        )
    except (ValueError, KeyError, ProfileCryptoUnavailable):
        fail(422, "INVALID_UPLOAD_TOKEN")
    if payload["attempt_id"] != str(attempt_id) or payload["sha256"] != body.sha256:
        fail(422, "INVALID_UPLOAD_TOKEN")

    # Retry receipts are checked before expiry or provider access.
    def work(s):
        if payload["expires"] < time.time():
            fail(409, "UPLOAD_EXPIRED")
        storage(request).verify(payload)
        _, a = lock_attempt(context, attempt_id)
        if a["state"] not in {"under_review", "submitted", "initiated"}:
            fail(409, "PAYMENT_CLOSED")
        old = context.session.execute(
            text("SELECT id FROM public.payment_evidence WHERE object_key=:key"),
            {"key": payload["object_key"]},
        ).scalar_one_or_none()
        eid = old or uuid4()
        if not old:
            context.session.execute(
                text(
                    "INSERT INTO public.payment_evidence(id,attempt_id,object_key,sha256_hex,content_type,bytes_size) VALUES(:id,:aid,:key,:hash,:type,:size)"
                ),
                {
                    "id": eid,
                    "aid": attempt_id,
                    "key": payload["object_key"],
                    "hash": body.sha256,
                    "type": payload["content_type"],
                    "size": payload["bytes_size"],
                },
            )
        return {
            "evidence_id": str(eid),
            "received": True,
            "payment_state": a["state"],
        }, eid

    return record(
        context,
        request,
        "evidence.finalize",
        dict(attempt_id=str(attempt_id), **body.model_dump()),
        work,
    )


@router.post("/admin/payment-attempts/{attempt_id}/reviews", operation_id="API-241")
def review_payment(
    attempt_id: UUID, body: ReviewRequest, context: Authenticated, request: Request
):
    require_staff(context, "finance")

    def work(s):
        order, a = lock_attempt(context, attempt_id)
        if (
            a["state"] not in {"under_review", "submitted"}
            or order["payment_status"] == "verified"
        ):
            fail(409, "PAYMENT_CLOSED")
        fingerprint = None
        if body.decision == "verify":
            typed = order.get("commerce_model", "legacy_pair") == "single_qr"
            from app.api.v1.financial_disputes import require_order_clear

            if not typed:
                require_order_clear(context.session, order["id"], s)
            if order["order_status"] != "placed":
                fail(409, "ORDER_RECONCILIATION_REQUIRED")
            if (
                not body.bank_verified
                or not body.bank_match_reference
                or body.settled_amount is None
                or body.settled_currency is None
            ):
                fail(422, "BANK_VERIFICATION_REQUIRED")
            if (
                Decimal(body.settled_amount) != a["amount"]
                or a["amount"] != order["total_pkr"]
                or body.settled_currency != a["currency_code"]
                or a["currency_code"] != order["currency_code"]
            ):
                fail(409, "SETTLEMENT_MISMATCH")
            # Stable key required across rotations; never store the raw bank reference.
            if not s.payment_reference_key:
                raise AccessError(503)
            fingerprint = hmac.new(
                s.payment_reference_key.get_secret_value().encode(),
                body.bank_match_reference.casefold().strip().encode(),
                hashlib.sha256,
            ).digest()
            if typed:
                value = typed_result(context.session.execute(text("""SELECT public.sr_typed_settle(
                    :sid,:aid,:bank_verified,:amount,:currency,:fingerprint,:reason)"""),
                    {"sid": context.principal.session_id, "aid": attempt_id, "bank_verified": body.bank_verified,
                     "amount": Decimal(body.settled_amount), "currency": body.settled_currency,
                     "fingerprint": fingerprint, "reason": body.reason}).scalar_one())
                # Existing legacy worker cannot consume the typed handoff. The
                # DB helper persists bank truth, all claims, audit and durable
                # events atomically; print admission stays closed in Phase 5.
                context.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
                context.session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
                return value, UUID(value["review_id"])
            units = context.session.execute(
                text(
                    "SELECT id,status FROM public.order_pair_units WHERE order_id=:id ORDER BY id FOR UPDATE"
                ),
                {"id": order["id"]},
            ).all()
            if not units or any(u.status != "reserved" for u in units):
                fail(409, "RESERVATION_RECONCILIATION_REQUIRED")
        elif body.bank_verified:
            fail(422, "INVALID_BANK_VERIFICATION")
        rid = uuid4()
        context.session.execute(
            text(
                "INSERT INTO public.payment_reviews(id,attempt_id,reviewed_by,decision,bank_verified,bank_reference_fingerprint,bank_reference_key_version,reason) VALUES(:id,:aid,:uid,:decision,:verified,:fingerprint,:version,:reason)"
            ),
            {
                "id": rid,
                "aid": attempt_id,
                "uid": context.principal.user_id,
                "decision": body.decision,
                "verified": body.bank_verified,
                "fingerprint": fingerprint,
                "version": 1 if fingerprint else None,
                "reason": body.reason,
            },
        )
        state = {
            "verify": "verified",
            "reject": "rejected",
            "request_more_info": "under_review",
        }[body.decision]
        context.session.execute(
            text(
                "UPDATE public.payment_attempts SET state=:state,reviewed_by=:uid,verified_at=CASE WHEN :state='verified' THEN now() ELSE NULL END WHERE id=:id"
            ),
            {"state": state, "uid": context.principal.user_id, "id": attempt_id},
        )
        context.session.execute(
            text("UPDATE public.orders SET payment_status=:state WHERE id=:id"),
            {"state": state, "id": order["id"]},
        )
        if state == "verified":
            context.session.execute(
                text(
                    "UPDATE public.order_pair_units SET status='allocated',allocated_at=now(),allocated_by=:uid WHERE order_id=:id AND status='reserved'"
                ),
                {"uid": context.principal.user_id, "id": order["id"]},
            )
            context.session.execute(
                text(
                    "UPDATE public.orders SET fulfillment_status='allocated' WHERE id=:id AND fulfillment_status='unallocated'"
                ),
                {"id": order["id"]},
            )
            context.session.execute(
                text(
                    "INSERT INTO public.finance_sheet_sync(order_id, status) VALUES(:id, 'pending') "
                    "ON CONFLICT (order_id) DO UPDATE SET status='pending', updated_at=clock_timestamp()"
                ),
                {"id": order["id"]},
            )
            context.session.execute(
                text(
                    "INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key) VALUES('finance.sync','order',:id,:id,:key) "
                    "ON CONFLICT (idempotency_key) DO NOTHING"
                ),
                {"id": order["id"], "key": "payment.finance:" + str(order["id"])},
            )
        if state == "verified" and s.print_enabled:
            context.session.execute(
                text(
                    "INSERT INTO public.durable_jobs(job_kind,aggregate_type,aggregate_id,order_id,idempotency_key) VALUES('allocation.finalize','order',:id,:id,:key)"
                ),
                {"id": order["id"], "key": "print.request:" + str(order["id"])},
            )
        return {
            "attempt_id": str(attempt_id),
            "state": state,
            "order_id": str(order["id"]),
            "fulfillment_eligible": state == "verified",
            "review_id": str(rid),
        }, rid

    return record(
        context,
        request,
        "payment.review",
        dict(attempt_id=str(attempt_id), **body.model_dump()),
        work,
    )


@router.get("/admin/orders/{order_id}/qr-allocation", operation_id="typed-allocation-status")
def allocation_status(order_id: UUID, context: Authenticated):
    require_staff(context, "finance", "operations")
    return typed_result(context.session.execute(text("SELECT public.sr_typed_allocation_status(:id)"), {"id": order_id}).scalar_one())


@router.post("/admin/orders/{order_id}/qr-allocation/retry", operation_id="typed-allocation-retry")
def retry_allocation(order_id: UUID, body: AllocationRetry, context: Authenticated, request: Request):
    require_staff(context, "finance", "operations")

    def work(settings):
        value = typed_result(context.session.execute(text("SELECT public.sr_typed_allocation_retry(:sid,:id)"),
                            {"sid": context.principal.session_id, "id": order_id}).scalar_one())
        context.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        context.session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return value, order_id

    return record(context, request, "allocation.retry", {"order_id": str(order_id), **body.model_dump()}, work)


@router.get(
    "/admin/payment-evidence/{evidence_id}", operation_id="payment-evidence-read"
)
def read_evidence(evidence_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "finance")
    row = (
        context.session.execute(
            text(
                "SELECT * FROM public.payment_evidence WHERE id=:id AND deleted_at IS NULL"
            ),
            {"id": evidence_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    data = storage(request).verify(
        {
            "object_key": row["object_key"],
            "bytes_size": row["bytes_size"],
            "content_type": row["content_type"],
            "sha256": row["sha256_hex"],
        }
    )
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(:actor,'staff','payment.evidence.read','payment_evidence',:id,'finance evidence retrieval','{}'::jsonb)"
        ),
        {"actor": context.principal.user_id, "id": evidence_id},
    )
    return Response(
        data,
        media_type=row["content_type"],
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="payment-evidence"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/admin/orders/{order_id}/payment-attempts", operation_id="API-240")
def finance_attempts(order_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "finance")
    rows = (
        context.session.execute(
            text(
                "SELECT * FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC LIMIT 100"
            ),
            {"id": order_id},
        )
        .mappings()
        .all()
    )
    items = []
    try:
        for a in rows:
            holder = (
                json.loads(
                    decrypt(
                        request.app.state.settings,
                        a["id"],
                        "sender_holder",
                        a["sender_holder_ciphertext"],
                        a["sender_key_version"],
                    )
                )
                if a["sender_holder_ciphertext"]
                else {}
            )
            account = (
                decrypt(
                    request.app.state.settings,
                    a["id"],
                    "sender_account",
                    a["sender_account_ciphertext"],
                    a["sender_key_version"],
                )
                if a["sender_account_ciphertext"]
                else None
            )
            evidence = (
                context.session.execute(
                    text(
                        "SELECT id,content_type,bytes_size FROM public.payment_evidence WHERE attempt_id=:id AND deleted_at IS NULL ORDER BY created_at DESC"
                    ),
                    {"id": a["id"]},
                )
                .mappings()
                .all()
            )
            items.append(
                {
                    "attempt_id": a["id"],
                    "state": a["state"],
                    "amount": f"{a['amount']:.2f}",
                    "currency_code": a["currency_code"],
                    "sender_account": account,
                    "sender_holder": holder,
                    "evidence": [dict(e) for e in evidence],
                }
            )
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(:actor,'staff','payment.finance.read','order',:id,'finance settlement review','{}'::jsonb)"
        ),
        {"actor": context.principal.user_id, "id": order_id},
    )
    return {"items": items}
