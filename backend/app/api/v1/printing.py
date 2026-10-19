"""Paid-order private vector print orchestration and artifact-specific physical QA."""

import hashlib
import hmac
import json
import re
import secrets
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.auth import (
    AccessError,
    Authenticated,
    require_order_owner,
    require_staff,
    require_verified_account,
)
from app.api.v1.catalog import CatalogRoute, Closed, fail
from app.core.print_render import (
    PrintUnavailable,
    build_manifest,
    canonical,
    digest,
    load_bundle,
)
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.integrations.print_storage import store

router = APIRouter(tags=["printing"], route_class=CatalogRoute)


class PrintJobRequest(Closed):
    reason: str = Field(min_length=4, max_length=500)
    expected_revision: int = Field(ge=0, strict=True)


class DownloadRequest(Closed):
    grant_id: UUID
    download_token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class Observation(Closed):
    tag_type: str = Field(pattern="^(lost|ice)$")
    symbol_mm: str = Field(pattern=r"^[0-9]{2,3}(?:\.[0-9]{1,2})?$")
    copies: int = Field(ge=1, le=500, strict=True)


class JobQARequest(Closed):
    approved: bool = Field(strict=True)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed: list[Observation] = Field(min_length=1, max_length=30)
    scan_passed: bool = Field(strict=True)
    logo_quiet_zone_passed: bool = Field(strict=True)
    bilingual_passed: bool = Field(strict=True)
    cutting_packaging_passed: bool = Field(strict=True)
    actual_scale_passed: bool = Field(strict=True)
    reason: str = Field(min_length=4, max_length=1000)


def record(context, request, operation, payload, work):
    require_verified_account(context)
    s = request.app.state.settings
    session = context.session
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
                    "print:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with session.begin_nested():
            result, target = work(s)
            result = jsonable_encoder(result, custom_encoder={Decimal: str})
            cipher, version = encrypt(
                s, actor, "print:" + reference, json.dumps(result)
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
   VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:version,now()+interval '1 day')"""),
                {
                    **params,
                    "hash": digest,
                    "cipher": cipher,
                    "version": version,
                    "status": 202
                    if operation == "print.enqueue"
                    else 201
                    if operation in {"print.grant", "print.pair_qa"}
                    else 200,
                },
            )
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
   VALUES(:actor,:kind,:op,:target_type,:target,:rid,'authorized print command',jsonb_build_object('event_id',CAST(:reference AS text),'outcome','success'))"""),
                {
                    "actor": actor,
                    "kind": "staff",
                    "op": operation,
                    "target_type": {
                        "print.grant": "print_download_grant",
                        "print.qa": "print_job_qa",
                        "print.pair_qa": "pair_print_qa",
                    }.get(operation, "print_job"),
                    "target": target,
                    "rid": getattr(request.state, "request_id", None),
                    "reference": reference,
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    except IntegrityError:
        fail(409, "PRINT_CONFLICT")


def occurrences(session, oid):
    return (
        session.execute(
            text("SELECT * FROM public.sr_print_occurrences(:id)"), {"id": oid}
        )
        .mappings()
        .all()
    )


def frozen(session, s, job):
    payload = (
        session.execute(
            text(
                "SELECT payload_ciphertext,payload_key_version FROM public.durable_jobs WHERE print_job_id=:id AND job_kind='print.render'"
            ),
            {"id": job["id"]},
        )
        .mappings()
        .one()
    )
    return json.loads(
        decrypt(
            s,
            job["order_id"],
            "print-render",
            payload["payload_ciphertext"],
            payload["payload_key_version"],
        )
    )


def enqueue(session, s, oid, expected_revision, reason):
    order = session.execute(
        text("SELECT public.sr_print_order_lock(:id)"), {"id": oid}
    ).scalar_one()
    if order is None:
        raise AccessError(404)
    rows = occurrences(session, oid)
    if not rows:
        fail(409, "PRINT_REQUIRES_PAID_ALLOCATION")
    previous = (
        session.execute(
            text(
                "SELECT * FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC LIMIT 1 FOR UPDATE"
            ),
            {"id": oid},
        )
        .mappings()
        .one_or_none()
    )
    if expected_revision != (previous["job_revision"] if previous else 0):
        fail(409, "VERSION_MISMATCH")
    if previous and previous["status"] in {"queued", "rendering"}:
        state = session.execute(
            text(
                "SELECT status FROM public.durable_jobs WHERE print_job_id=:id AND job_kind='print.render'"
            ),
            {"id": previous["id"]},
        ).scalar_one()
        if state != "dead":
            fail(409, "PRINT_ALREADY_ACTIVE")
    if previous:
        manifest = frozen(session, s, previous)
        if [
            (str(r["use_id"]), str(r["qr_id"]), int(r["copies"]), r["public_token"])
            for r in rows
        ] != [
            (o["use_id"], o["qr_id"], o["copies"], o["url"].rsplit("/", 1)[1])
            for o in manifest["occurrences"]
        ]:
            fail(409, "PRINT_BINDING_CHANGED")
        session.execute(
            text("UPDATE public.print_jobs SET status='superseded' WHERE id=:id"),
            {"id": previous["id"]},
        )
    else:
        manifest = build_manifest(load_bundle(s), rows)
    jid = uuid4()
    revision = expected_revision + 1
    cipher, version = encrypt(s, oid, "print-render", canonical(manifest))
    session.execute(
        text(
            "SELECT public.sr_insert_print_job(:jid,:oid,:rev,:fp,CAST(:cfg AS jsonb),:cipher,CAST(:kv AS smallint))"
        ),
        {
            "jid": jid,
            "oid": oid,
            "rev": revision,
            "fp": digest(manifest),
            "cfg": canonical(
                {
                    "template_key": "safereturn-locked-v1",
                    "template_version": 1,
                    "locale": "en-ur",
                    "page_size": "A4",
                    "margin_mm": 10,
                }
            ),
            "cipher": cipher,
            "kv": version,
        },
    )
    return {"job_id": str(jid), "revision": revision, "status": "queued"}, jid


@router.post(
    "/admin/orders/{order_id}/print-jobs", operation_id="API-234", status_code=202
)
def create_print_job(
    order_id: UUID, body: PrintJobRequest, context: Authenticated, request: Request
):
    require_staff(context, "operations")

    def work(s):
        if not s.print_enabled:
            raise AccessError(503)
        try:
            return enqueue(
                context.session, s, order_id, body.expected_revision, body.reason
            )
        except PrintUnavailable:
            raise AccessError(503) from None

    return record(
        context,
        request,
        "print.enqueue",
        {"order_id": str(order_id), **body.model_dump()},
        work,
    )


@router.get("/admin/orders/{order_id}/print-jobs", operation_id="API-233")
def list_print_jobs(order_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    rows = (
        context.session.execute(
            text(
                "SELECT id,job_revision,status,template_fingerprint,failure_code FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC"
            ),
            {"id": order_id},
        )
        .mappings()
        .all()
    )
    return {"items": [dict(r) for r in rows]}


@router.get("/admin/print-jobs/{job_id}", operation_id="API-235")
def get_print_job(job_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    r = (
        context.session.execute(
            text(
                "SELECT id,order_id,job_revision,status,template_fingerprint,attempt_count,failure_code FROM public.print_jobs WHERE id=:id"
            ),
            {"id": job_id},
        )
        .mappings()
        .one_or_none()
    )
    if r is None:
        raise AccessError(404)
    artifacts = (
        context.session.execute(
            text(
                "SELECT id,format,size_bytes,sha256_hex,deleted_at FROM public.print_artifacts WHERE print_job_id=:id"
            ),
            {"id": job_id},
        )
        .mappings()
        .all()
    )
    return dict(r, artifacts=[dict(a) for a in artifacts])


def artifact(session, aid, *, check_binding=True):
    a = (
        session.execute(
            text(
                "SELECT a.*,j.order_id,j.status FROM public.print_artifacts a JOIN public.print_jobs j ON j.id=a.print_job_id JOIN public.orders o ON o.id=j.order_id WHERE a.id=:id AND o.payment_status='verified' AND o.order_status='placed'"
            ),
            {"id": aid},
        )
        .mappings()
        .one_or_none()
    )
    if a is None:
        raise AccessError(404)
    if a["deleted_at"] is not None:
        fail(410, "ARTIFACT_DELETED")
    if a["status"] not in {"ready", "downloaded", "qa_passed"}:
        fail(409, "ARTIFACT_UNAVAILABLE")
    if (
        a["retention_until"] is not None
        and session.execute(
            text("SELECT :expiry<=clock_timestamp()"), {"expiry": a["retention_until"]}
        ).scalar_one()
    ):
        fail(410, "ARTIFACT_EXPIRED")
    if check_binding and not occurrences(session, a["order_id"]):
        fail(409, "PRINT_BINDING_CHANGED")
    return a


@router.post(
    "/admin/print-artifacts/{artifact_id}/download-grants",
    operation_id="API-236",
    status_code=201,
)
def create_download_grant(artifact_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "operations")

    def work(s):
        a = artifact(context.session, artifact_id)
        token = secrets.token_urlsafe(32)
        gid = uuid4()
        expiry = context.session.execute(
            text(
                "INSERT INTO public.print_download_grants(id,artifact_id,granted_to,token_hash,expires_at) VALUES(:id,:aid,:uid,:hash,clock_timestamp()+interval '5 minutes') RETURNING expires_at"
            ),
            {
                "id": gid,
                "aid": artifact_id,
                "uid": context.principal.user_id,
                "hash": hashlib.sha256(token.encode()).digest(),
            },
        ).scalar_one()
        return {
            "grant_id": str(gid),
            "download_token": token,
            "download_url": "/api/v1/admin/print-downloads",
            "expires_at": expiry.isoformat(),
            "filename": "SR-" + str(a["order_id"]) + "-print.pdf",
        }, gid

    return record(
        context, request, "print.grant", {"artifact_id": str(artifact_id)}, work
    )


@router.post("/admin/print-downloads", operation_id="print-download-redeem")
def redeem_download(body: DownloadRequest, context: Authenticated, request: Request):
    require_staff(context, "operations")
    params = {"id": body.grant_id, "uid": context.principal.user_id}
    grant = (
        context.session.execute(
            text(
                "SELECT * FROM public.print_download_grants WHERE id=:id AND granted_to=:uid AND expires_at>clock_timestamp() AND used_at IS NULL"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    if grant is None or not hmac.compare_digest(
        bytes(grant["token_hash"]),
        hashlib.sha256(body.download_token.encode()).digest(),
    ):
        raise AccessError(404)
    a = artifact(context.session, grant["artifact_id"], check_binding=False)
    try:
        data = store(request).download(
            a["object_key"], a["sha256_hex"], a["size_bytes"]
        )
    except PrintUnavailable:
        raise AccessError(503) from None
    # Provider I/O precedes the serialized consume/revalidation transaction section.
    context.session.execute(
        text("SELECT id FROM public.orders WHERE id=:id FOR UPDATE"),
        {"id": a["order_id"]},
    )
    artifact(context.session, grant["artifact_id"])
    used = context.session.execute(
        text(
            "UPDATE public.print_download_grants SET used_at=clock_timestamp() WHERE id=:id AND granted_to=:uid AND used_at IS NULL AND expires_at>clock_timestamp() RETURNING id"
        ),
        params,
    ).scalar_one_or_none()
    if used is None:
        fail(409, "DOWNLOAD_GRANT_CONSUMED")
    context.session.execute(
        text(
            "UPDATE public.print_jobs SET status='downloaded' WHERE id=:id AND status='ready'"
        ),
        {"id": a["print_job_id"]},
    )
    audit(context, "print.download", body.grant_id)
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="SR-print.pdf"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


def audit(context, action, target):
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(:uid,'staff',:action,'print_download_grant',:target,'authorized print operation','{}'::jsonb)"
        ),
        {"uid": context.principal.user_id, "action": action, "target": target},
    )


@router.post("/admin/print-jobs/{job_id}/qa", operation_id="API-237")
def record_job_qa(
    job_id: UUID, body: JobQARequest, context: Authenticated, request: Request
):
    require_staff(context, "operations")

    def work(s):
        job = (
            context.session.execute(
                text("SELECT * FROM public.print_jobs WHERE id=:id FOR UPDATE"),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if job is None:
            raise AccessError(404)
        if job["status"] not in {"ready", "downloaded", "qa_passed"}:
            fail(409, "PRINT_NOT_READY")
        a = (
            context.session.execute(
                text(
                    "SELECT * FROM public.print_artifacts WHERE print_job_id=:id AND deleted_at IS NULL AND format='pdf'"
                ),
                {"id": job_id},
            )
            .mappings()
            .one()
        )
        artifact(context.session, a["id"])
        manifest = frozen(context.session, s, job)
        expected = {}
        for o in manifest["occurrences"]:
            key = (o["template"]["tag_type"], Decimal(str(o["template"]["symbol_mm"])))
            expected[key] = expected.get(key, 0) + o["copies"]
        actual = {}
        for o in body.observed:
            key = (o.tag_type, Decimal(o.symbol_mm))
            actual[key] = actual.get(key, 0) + o.copies
        checks = (
            body.scan_passed,
            body.logo_quiet_zone_passed,
            body.bilingual_passed,
            body.cutting_packaging_passed,
            body.actual_scale_passed,
        )
        if (
            body.artifact_sha256 != a["sha256_hex"]
            or body.approved
            and (actual != expected or not all(checks))
        ):
            fail(422, "PHYSICAL_QA_MISMATCH")
        qid = uuid4()
        context.session.execute(
            text(
                "INSERT INTO public.print_job_qa(id,print_job_id,inspected_by,approved,artifact_sha256,observations,reason) VALUES(:id,:jid,:uid,:approved,:hash,CAST(:obs AS jsonb),:reason)"
            ),
            {
                "id": qid,
                "jid": job_id,
                "uid": context.principal.user_id,
                "approved": body.approved,
                "hash": body.artifact_sha256,
                "obs": canonical(body.model_dump()),
                "reason": body.reason,
            },
        )
        context.session.execute(
            text(
                "UPDATE public.print_jobs SET status=:status,failure_code=:code WHERE id=:id"
            ),
            {
                "id": job_id,
                "status": "qa_passed" if body.approved else "failed",
                "code": None if body.approved else "physical_qa_failed",
            },
        )
        return {
            "qa_id": str(qid),
            "approved": body.approved,
            "status": "qa_passed" if body.approved else "failed",
        }, qid

    return record(
        context, request, "print.qa", {"job_id": str(job_id), **body.model_dump()}, work
    )


class PrintQARequest(Closed):
    qa_round: int = Field(ge=1, le=1000, strict=True)
    lost_scan_passed: bool = Field(strict=True)
    ice_scan_passed: bool = Field(strict=True)
    pair_match_passed: bool = Field(strict=True)
    credential_concealed: bool = Field(strict=True)
    bilingual_label_passed: bool = Field(strict=True)
    quiet_zone_passed: bool = Field(strict=True)
    indoor_size_passed: bool = Field(strict=True)
    outdoor_size_passed: bool = Field(strict=True)
    packaging_method: str = Field(pattern="^(scratch_off|sealed_sleeve|peel_seal)$")
    tamper_evidence_passed: bool = Field(strict=True)
    approved: bool = Field(strict=True)
    notes: str | None = Field(default=None, max_length=2000)


@router.post(
    "/admin/tag-pairs/{pair_id}/print-qa", operation_id="API-094", status_code=201
)
def record_print_qa(
    pair_id: UUID, body: PrintQARequest, context: Authenticated, request: Request
):
    require_staff(context, "operations")

    def work(s):
        if body.approved and not all(
            getattr(body, x)
            for x in (
                "lost_scan_passed",
                "ice_scan_passed",
                "pair_match_passed",
                "credential_concealed",
                "bilingual_label_passed",
                "quiet_zone_passed",
                "indoor_size_passed",
                "outdoor_size_passed",
                "tamper_evidence_passed",
            )
        ):
            fail(422, "PHYSICAL_QA_MISMATCH")
        pair = context.session.execute(
            text(
                "SELECT id FROM public.tag_pairs WHERE id=:id AND inventory_status IN('generated','qa_pending','qa_passed') AND owner_user_id IS NULL FOR UPDATE"
            ),
            {"id": pair_id},
        ).first()
        if pair is None:
            fail(409, "PAIR_QA_NOT_ELIGIBLE")
        qid = uuid4()
        values = {
            "id": qid,
            "pair": pair_id,
            "uid": context.principal.user_id,
            **body.model_dump(),
        }
        context.session.execute(
            text(
                "INSERT INTO public.pair_print_qa(id,pair_id,inspected_by,qa_round,lost_scan_passed,ice_scan_passed,pair_match_passed,credential_concealed,bilingual_label_passed,quiet_zone_passed,indoor_size_passed,outdoor_size_passed,packaging_method,tamper_evidence_passed,approved,notes) VALUES(:id,:pair,:uid,:qa_round,:lost_scan_passed,:ice_scan_passed,:pair_match_passed,:credential_concealed,:bilingual_label_passed,:quiet_zone_passed,:indoor_size_passed,:outdoor_size_passed,:packaging_method,:tamper_evidence_passed,:approved,:notes)"
            ),
            values,
        )
        if body.approved:
            context.session.execute(
                text(
                    "UPDATE public.tag_pairs SET inventory_status='qa_passed' WHERE id=:id"
                ),
                {"id": pair_id},
            )
        return {
            "qa_id": str(qid),
            "pair_id": str(pair_id),
            "approved": body.approved,
        }, qid

    return record(
        context,
        request,
        "print.pair_qa",
        {"pair_id": str(pair_id), **body.model_dump()},
        work,
    )


@router.get("/me/orders/{order_id}/print-summary", operation_id="API-213")
def owner_print_summary(order_id: UUID, context: Authenticated):
    require_verified_account(context)
    require_order_owner(context, order_id)
    job = context.session.execute(
        text(
            "SELECT status FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC LIMIT 1"
        ),
        {"id": order_id},
    ).scalar_one_or_none()
    counts = context.session.execute(
        text(
            "SELECT u.tag_type_snapshot,sum(u.copies) AS copies FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=:id GROUP BY u.tag_type_snapshot"
        ),
        {"id": order_id},
    ).all()
    fulfillment = context.session.execute(
        text("SELECT fulfillment_status FROM public.orders WHERE id=:id"),
        {"id": order_id},
    ).scalar_one()
    return {
        "print_status": job or "not_requested",
        "fulfillment_status": fulfillment,
        "copies": dict(counts),
    }
