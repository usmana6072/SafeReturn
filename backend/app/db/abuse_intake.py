"""Narrow production repository; no target lookup or direct report-table grants."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import AccessError
from app.core.abuse_intake import Policy, Unavailable, policy


def available(session: Session) -> bool:
    if "abuse_intake_available" not in session.info:
        session.info["abuse_intake_available"] = (
            session.execute(
                text(
                    "SELECT to_regprocedure('public.sr_abuse_policy(uuid,integer)') IS NOT NULL AS abuse_intake_available"
                )
            ).scalar_one()
            is True
        )
    return session.info["abuse_intake_available"]


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        value = self.session.execute(
            text("SELECT public.sr_abuse_intake(:action,CAST(:payload AS jsonb))"),
            {"action": action, "payload": json.dumps(payload)},
        ).scalar_one()
        if not isinstance(value, dict) or value.get("error") == "PROVIDER_UNAVAILABLE":
            raise Unavailable()
        if action in {"peer", "target", "proof"}:
            if set(value) != {"allowed"} or type(value["allowed"]) is not bool:
                raise Unavailable()
        elif value not in ({"status": "accepted"}, {"error": "IDEMPOTENCY_KEY_REUSED"}):
            raise Unavailable()
        return value

    def policy(self, ident: UUID, version: int) -> dict[str, Any]:
        if not available(self.session):
            raise Unavailable()
        row = self.session.execute(
            text("SELECT public.sr_abuse_policy(:id,:version)"),
            {"id": ident, "version": version},
        ).scalar_one()
        if row is None:
            raise Unavailable()
        return row


def case_policy(session: Session, case_id: UUID) -> Policy | None:
    if not available(session):
        return None
    value = session.execute(
        text("SELECT public.sr_abuse_case_policy(:id)"), {"id": case_id}
    ).scalar_one()
    if value is None:
        return None  # ordinary case or inaccessible scope, never decrypt here
    try:
        return policy(value)
    except Unavailable:
        raise AccessError(503) from None


def case_clause(session: Session) -> str:
    return " AND public.sr_abuse_case_readable(id) " if available(session) else ""
