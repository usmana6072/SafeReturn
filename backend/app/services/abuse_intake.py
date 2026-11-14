"""Real policy-gated intake; every claimed context is persisted blind and unverified."""

from typing import Any
from uuid import uuid4

from fastapi import Request

from app.core.abuse_intake import (
    Report,
    Unavailable,
    canonical,
    fingerprint,
    index_key,
    policy,
)
from app.core.profile_crypto import encrypt
from app.core.profile_crypto import key as encryption_key
from app.core.turnstile import ChallengeRequired, challenge_binding, verify
from app.db.abuse_intake import Repository
from app.db.runtime import api_transaction


def preflight(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    database = request.app.state.database
    if (
        not settings.abuse_reports_enabled
        or database is None
        or settings.abuse_report_policy_id is None
    ):
        raise Unavailable()
    secret = index_key(settings)
    encryption_key(settings, settings.profile_data_key_version)
    peer = request.client.host if request.client else None
    if not peer:
        raise Unavailable()
    with api_transaction(database) as session:
        repo = Repository(session)
        row = repo.policy(
            settings.abuse_report_policy_id, settings.abuse_report_policy_version
        )
        policy(row, intake=True, settings=settings)
        args = {
            "policy_id": row["policy_id"],
            "policy_version": row["version"],
            "scope": fingerprint(secret, "peer", peer),
        }
        allowed = repo.call("peer", args)
    return {"row": row, "key": secret, "args": args, "allowed": allowed["allowed"]}


def submit(
    request: Request, body: Report, retry_key: str, admission: dict[str, Any]
) -> str | None:
    settings, database = request.app.state.settings, request.app.state.database
    if not settings.abuse_reports_enabled:
        raise Unavailable()
    raw = body.semantic()
    context = {"qr_token": raw["qr_token"], "message_id": raw["message_id"]}
    secret = admission["key"]
    scope = fingerprint(
        secret, "target-peer", {"peer": admission["args"]["scope"], "target": context}
    )
    args = admission["args"] | {"scope": scope}
    with api_transaction(database) as session:
        allowed = Repository(session).call("target", args)
    if not allowed["allowed"]:
        return "RATE_LIMITED"
    proof = body.turnstile_token.get_secret_value() if body.turnstile_token else None
    verify(
        settings,
        proof,
        "abuse_report",
        challenge_binding("abuse_report", raw["qr_token"], body.message_id),
        transport=getattr(request.app.state, "turnstile_transport", None),
    )
    if not settings.abuse_reports_enabled:
        raise Unavailable()
    with api_transaction(database) as session:
        fresh = Repository(session).call(
            "proof", args | {"proof": fingerprint(secret, "proof", proof)}
        )
    if not fresh["allowed"]:
        raise ChallengeRequired()
    report_id, case_id, event_id = uuid4(), uuid4(), uuid4()
    encrypted_context, kv = encrypt(
        settings, report_id, "abuse_context:v1", canonical(context)
    )
    description = (
        "Unverified public abuse report\nCategory: "
        + body.category
        + "\n"
        + (body.message or "")
    )
    encrypted_description, desc_kv = encrypt(
        settings, case_id, "support_description", description
    )
    with api_transaction(database) as session:
        if not settings.abuse_reports_enabled:
            raise Unavailable()
        repo = Repository(session)
        row = repo.policy(
            settings.abuse_report_policy_id, settings.abuse_report_policy_version
        )
        policy(row, intake=True, settings=settings)
        result = repo.call(
            "submit",
            args
            | {
                "report_id": str(report_id),
                "case_id": str(case_id),
                "event_id": str(event_id),
                "retry": fingerprint(secret, "retry", retry_key),
                "body": fingerprint(secret, "body", raw),
                "duplicate": fingerprint(
                    secret, "duplicate", {"scope": scope, "body": raw}
                ),
                "category": body.category,
                "context_ciphertext": encrypted_context.hex(),
                "context_key_version": kv,
                "description_ciphertext": encrypted_description.hex(),
                "description_key_version": desc_kv,
            },
        )
    return result.get("error")
