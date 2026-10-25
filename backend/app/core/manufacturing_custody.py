"""Controlled custody utilities. No CLI, web writer, provider or key recovery.

The caller owns an explicitly authorized transaction; these functions never open
connections, impersonate an account, set MFA or commit. Runtime database roles
cannot execute provisioning, revocation or handoff recording SQL helpers.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.manufacturing import (
    TransportConflict,
    canonical,
    identity_snapshot,
    pack,
    sealed_bytes,
    sha,
    verify_handoff,
)


def source_record(
    settings: Settings,
    batch_id: UUID,
    generation_key: str,
    generation_request: dict[str, Any],
    pairs: list[dict[str, Any]],
    sealed: bytes,
) -> dict[str, Any]:
    count, identity = identity_snapshot(pairs)
    sealed_bytes(sealed, sha(sealed))
    if generation_request["pair_count"] != count:
        raise TransportConflict("pair_count")
    return {
        "generation_key": generation_key,
        "generation_request": canonical(generation_request),
        "printer_key_fingerprint": generation_request["printer_key_fingerprint"],
        "pair_count": count,
        "identity_sha256": identity,
        "pairs": sorted(
            [
                {
                    "pair_reference": p["pair_reference"],
                    "tags": sorted(p["tags"], key=lambda t: t["tag_type"]),
                }
                for p in pairs
            ],
            key=lambda p: p["pair_reference"],
        ),
        **pack(settings, batch_id, "source", sealed),
    }


def register_source(
    session: Session,
    settings: Settings,
    batch_id: UUID,
    generation_key: str,
    generation_request: dict[str, Any],
    pairs: list[dict[str, Any]],
    sealed: bytes,
) -> None:
    body = source_record(
        settings, batch_id, generation_key, generation_request, pairs, sealed
    )
    ok = session.execute(
        text("SELECT public.sr_mfg_register(:bid,CAST(:body AS jsonb))"),
        {"bid": batch_id, "body": canonical(body)},
    ).scalar_one()
    if not ok:
        raise TransportConflict("original_provenance_required")


def record_handoff(session: Session, record: dict[str, Any], signature: str) -> None:
    batch_id = UUID(str(record["batch_id"]))
    context = session.execute(
        text("SELECT public.sr_mfg_handoff_context(:bid)"), {"bid": batch_id}
    ).scalar_one()
    if context is None:
        raise TransportConflict("handoff_reconciliation")
    verified = verify_handoff(record, signature, context["acknowledgement_public_key"])
    for field in (
        "job_id",
        "revision",
        "delivery_id",
        "manifest_sha256",
        "printer_key_fingerprint",
    ):
        if str(getattr(verified, field)) != str(context[field]):
            raise TransportConflict("handoff_reconciliation")
    ok = session.execute(
        text("SELECT public.sr_mfg_record_handoff(:bid,CAST(:body AS jsonb))"),
        {
            "bid": batch_id,
            "body": json.dumps(
                {"record": verified.model_dump(mode="json"), "signature": signature}
            ),
        },
    ).scalar_one()
    if not ok:
        raise TransportConflict("handoff_reconciliation")
