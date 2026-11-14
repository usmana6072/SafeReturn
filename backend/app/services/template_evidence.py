"""Controlled import/revocation and publication preparation; no authority enrollment."""

import hashlib
import json
import re
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from sqlalchemy import text

from app.api.auth import AccessError, authorize, require_staff
from app.api.v1.catalog import fail
from app.api.v1.privacy_exports import Confirmed
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt
from app.core.template_auth import recent_template_auth
from app.core.template_evidence import EvidenceInvalid, envelope_digest, parse, verify
from app.db.template_registry import RegistryRepository, gate


class EvidenceWithdrawal(Confirmed):
    evidence_id: UUID | None
    key_id: UUID | None
    expected_authority_version: int = Field(ge=1, strict=True)
    reason_code: str = Field(pattern=r"^(evidence_withdrawn|key_compromise)$")

    @model_validator(mode="after")
    def target(self):
        if (self.evidence_id is None) == (self.key_id is None):
            raise ValueError("One target required")
        if self.key_id is not None and self.reason_code != "key_compromise":
            raise ValueError("Key withdrawal reason required")
        if self.evidence_id is not None and self.reason_code != "evidence_withdrawn":
            raise ValueError("Evidence withdrawal reason required")
        return self


def custody(context, settings):
    require_staff(context, "security_admin")
    recent_template_auth(context)
    if not settings.print_template_management_enabled:
        raise AccessError(503)
    return RegistryRepository(context).call("custody_check", {})


def publisher(context):
    require_staff(context, "operations")
    recent_template_auth(context)
    return RegistryRepository(context).call("publisher_check", {})


def publication_proof(context, settings, template_id, revision_id, approval_id):
    publisher(context)
    repository = RegistryRepository(context)
    stored = repository.call("approval_input", {"approval_id": str(approval_id)})
    try:
        raw = decrypt(
            settings,
            UUID(stored["approval_id"]),
            "template-qa:v1",
            bytes.fromhex(stored["ciphertext"]),
            stored["key_version"],
        ).encode()
        envelope = parse(raw)
        p = envelope.payload
        if (
            str(p.revision_id) != str(revision_id)
            or str(p.template_id) != str(template_id)
            or envelope_digest(envelope) != stored["evidence_sha256"]
        ):
            raise EvidenceInvalid("evidence_not_eligible")
        ctx = repository.call(
            "context_publish",
            {
                "revision_id": str(revision_id),
                "policy_id": str(p.production_policy_id),
                "policy_version": p.production_policy_version,
                "importer_human": stored["importer_human"],
            },
        )
        summary = verify(envelope, ctx)
        return {"verified_evidence_sha256": summary["evidence_sha256"]}
    except (EvidenceInvalid, ProfileCryptoUnavailable, ValueError, KeyError):
        fail(409, "CONFLICT")


def controlled_command(context, settings, operation, idempotency_key, payload, work):
    custody(context, settings)
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", idempotency_key):
        fail(400, "VALIDATION_ERROR")
    gate(context.session, exclusive=True)
    actor = context.principal.user_id
    reference = hashlib.sha256(
        f"{actor}:{operation}:{idempotency_key}".encode()
    ).hexdigest()
    hashed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    session = context.session
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k,0))"), {"k": reference}
    )
    params = {
        "scope": str(actor),
        "actor": actor,
        "op": operation,
        "key": idempotency_key,
    }
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
            if old["request_hash"] != hashed:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            custody(authorize(session, context.principal), settings)
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "template-controlled:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        with session.begin_nested():
            value = work()
            custody(authorize(session, context.principal), settings)
            result = {"command_id": str(uuid4()), "result": value}
            cipher, kv = encrypt(
                settings, actor, "template-controlled:" + reference, json.dumps(result)
            )
            session.execute(
                text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
             VALUES(:scope,:actor,:op,:key,:hash,'completed',:status,:cipher,:kv,now()+interval '1 day')"""),
                params
                | {
                    "hash": hashed,
                    "status": 201 if operation == "template.evidence.import" else 200,
                    "cipher": cipher,
                    "kv": kv,
                },
            )
            target = UUID(value.get("approval_id", value.get("revocation_id", value.get("revision_id"))))
            session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details)
              VALUES(:actor,'staff',:op,'template_qa',:target,'controlled template evidence command',jsonb_build_object('event_id',CAST(:event AS text),'outcome','success'))"""),
                {
                    "actor": actor,
                    "op": operation,
                    "target": target,
                    "event": result["command_id"],
                },
            )
            return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


def import_evidence(context, settings, raw, idempotency_key):
    custody(context, settings)
    try:
        envelope = parse(raw)
    except EvidenceInvalid:
        fail(422, "VALIDATION_ERROR")

    def work():
        p = envelope.payload
        repository = RegistryRepository(context)
        ctx = repository.call(
            "context_import",
            {
                "revision_id": str(p.revision_id),
                "policy_id": str(p.production_policy_id),
                "policy_version": p.production_policy_version,
            },
        )
        try:
            summary = verify(envelope, ctx)
        except EvidenceInvalid:
            fail(409, "CONFLICT")
        approval = uuid4()
        cipher, kv = encrypt(
            settings,
            approval,
            "template-qa:v1",
            json.dumps(
                envelope.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ),
        )
        return repository.call(
            "import",
            {
                "approval_id": str(approval),
                "summary": summary,
                "ciphertext": cipher.hex(),
                "key_version": kv,
            },
        )

    return controlled_command(
        context,
        settings,
        "template.evidence.import",
        idempotency_key,
        envelope.model_dump(mode="json"),
        work,
    )


def revoke_evidence(context, settings, body: EvidenceWithdrawal, idempotency_key):
    return controlled_command(
        context,
        settings,
        "template.evidence.revoke",
        idempotency_key,
        body.model_dump(mode="json"),
        lambda: RegistryRepository(context).call(
            "revoke", body.model_dump(mode="json")
        ),
    )
