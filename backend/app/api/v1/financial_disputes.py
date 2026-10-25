"""Case-authorized independent financial review. Refund and restoration stay disabled."""

import base64
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_staff
from app.api.v1.cancellations import Confirmed
from app.api.v1.catalog import Closed, fail
from app.api.v1.privacy_exports import recent
from app.api.v1.shipping_addresses import PrivateRoute
from app.api.v1.support_cases import command
from app.core.profile_crypto import ProfileCryptoUnavailable, decrypt, encrypt

router = APIRouter(tags=["case financial review"], route_class=PrivateRoute)
DecisionKind = Literal[
    "investigate", "confirm_dispute", "resolve_no_change", "escalate"
]
Reason = Literal[
    "review_started", "settlement_disputed", "no_financial_change", "requires_review"
]


class FinancialDecision(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
    expected_order_revision: int = Field(ge=1, le=2147483646, strict=True)
    decision: DecisionKind
    settlement_review_reference: UUID | None = None
    reason_code: Reason

    @model_validator(mode="after")
    def consistent(self):
        reasons = {
            "investigate": "review_started",
            "confirm_dispute": "settlement_disputed",
            "resolve_no_change": "no_financial_change",
            "escalate": "requires_review",
        }
        if reasons[self.decision] != self.reason_code:
            raise ValueError("Decision and reason differ")
        if (
            self.decision in {"confirm_dispute", "resolve_no_change"}
            and self.settlement_review_reference is None
        ):
            raise ValueError("Review reference required")
        return self


class HistoryEntry(Closed):
    decision_id: UUID
    revision: int = Field(ge=1)
    decision: DecisionKind
    effective_decision: DecisionKind
    reason_code: Reason
    created_at: datetime


class ReviewProjection(Closed):
    case_id: UUID
    case_type: Literal["payment"]
    case_status: Literal["open", "investigating", "resolved", "closed"]
    case_revision: int = Field(ge=1)
    order_id: UUID
    order_revision: int = Field(ge=1)
    attempt_id: UUID
    amount: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    settlement_state: Literal[
        "initiated",
        "submitted",
        "under_review",
        "verified",
        "rejected",
        "expired",
        "refunded",
        "disputed",
    ]
    order_payment_status: Literal[
        "awaiting_transfer",
        "proof_submitted",
        "under_review",
        "verified",
        "rejected",
        "refunded",
    ]
    dispute_fence: Literal["active", "none"]
    exceptions: list[
        Literal["FINANCIAL_FENCE", "PACKAGE_REQUIRES_REVIEW", "ACTIVE_RETENTION_HOLD"]
    ]
    prior_decisions: list[HistoryEntry]
    next_cursor: str | None
    refund_execution_enabled: Literal[False] = False


class DecisionReceipt(Closed):
    decision_id: UUID
    case_id: UUID
    case_revision: int = Field(ge=1)
    order_id: UUID
    order_revision: int = Field(ge=1)
    decision: DecisionKind
    effective_decision: DecisionKind
    dispute_fence: Literal["active", "none"]
    next_action: Literal["await_reconciliation", "review_recorded", "escalated"]
    refund_execution_enabled: Literal[False] = False


def guard(context, request, write=False):
    require_staff(context, "finance")
    settings = request.app.state.settings
    if not settings.financial_review_enabled:
        raise AccessError(503)
    if write:
        if not settings.financial_review_web_origin or request.headers.getlist(
            "origin"
        ) != [settings.financial_review_web_origin]:
            raise AccessError(403)
        recent(context)


def load_context(context, case_id, deciding=False, reference=None):
    value = context.session.execute(
        text("SELECT public.sr_financial_case_context(:cid,:deciding,:reference)"),
        {"cid": case_id, "deciding": deciding, "reference": reference},
    ).scalar_one()
    if value is None:
        raise AccessError(404)
    # Rechecked before encrypted receipt replay, not just on a fresh command.
    authority = value.get("authority", {})
    if authority.get("can_review") is not True or authority.get("revoked") is not False:
        raise AccessError(404)
    if deciding and (
        authority.get("can_decide") is not True
        or str(context.principal.user_id) == str(authority.get("provisioned_by"))
        or str(context.principal.user_id) in value.get("verified_reviewers", [])
    ):
        raise AccessError(404)
    return value


def exact_money(value):
    if not isinstance(value, (str, Decimal)) or not re.fullmatch(
        r"[0-9]{1,10}\.[0-9]{2}", str(value)
    ):
        raise AccessError(503)
    try:
        return f"{Decimal(value):.2f}"
    except InvalidOperation:
        raise AccessError(503) from None


def evaluate(snapshot, body):
    if (
        snapshot["case"]["revision"] != body.expected_revision
        or snapshot["order"]["revision"] != body.expected_order_revision
    ):
        fail(409, "VERSION_MISMATCH")
    if snapshot["case"]["status"] in {"resolved", "closed"}:
        fail(409, "CASE_CLOSED")
    reference = snapshot.get("review_reference")
    if body.settlement_review_reference is not None and (
        not reference or reference["id"] != str(body.settlement_review_reference)
    ):
        raise AccessError(404)
    if body.decision == "confirm_dispute":
        if (
            not reference
            or reference.get("decision") != "verify"
            or reference.get("bank_verified") is not True
            or not snapshot["attempt"].get("verified_at")
        ):
            fail(409, "VERIFIED_SETTLEMENT_REQUIRED")
        if (
            exact_money(snapshot["attempt"]["amount"])
            != exact_money(snapshot["order"]["amount"])
            or snapshot["attempt"]["currency"] != snapshot["order"]["currency"]
        ):
            fail(409, "SETTLEMENT_MISMATCH")
    effective = body.decision
    dispatched = any(
        p.get("dispatched_at") or p["status"] in {"dispatched", "delivered", "returned"}
        for p in snapshot["shipments"]
    )
    if effective == "confirm_dispute" and dispatched:
        effective = "escalate"
    return {
        "effective_decision": effective,
        "activate_fence": effective in {"confirm_dispute", "escalate"},
        "package_exception_ids": [
            p["id"]
            for p in snapshot["shipments"]
            if p["status"] in {"preparing", "packed"}
        ]
        if effective in {"confirm_dispute", "escalate"} and not dispatched
        else [],
    }


def page_token(settings, case_id, revision, before):
    try:
        cipher, version = encrypt(
            settings,
            case_id,
            "finance_case_cursor",
            json.dumps({"revision": revision, "before": before}),
        )
        return (
            base64.urlsafe_b64encode(version.to_bytes(2, "big") + cipher)
            .decode()
            .rstrip("=")
        )
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None


def parse_token(settings, case_id, revision, token):
    if token is None:
        return 2147483647
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{40,2000}", token):
            raise ValueError()
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        payload = json.loads(
            decrypt(
                settings,
                case_id,
                "finance_case_cursor",
                raw[2:],
                int.from_bytes(raw[:2], "big"),
            )
        )
        if (
            set(payload) != {"revision", "before"}
            or type(payload["revision"]) is not int
            or type(payload["before"]) is not int
            or not 1 <= payload["before"] <= 2147483647
        ):
            raise ValueError()
    except (ValueError, TypeError, ProfileCryptoUnavailable):
        fail(422, "INVALID_CURSOR")
    if payload["revision"] != revision:
        fail(409, "VERSION_MISMATCH")
    return payload["before"]


@router.get(
    "/admin/support-cases/{case_id}/financial-review",
    operation_id="API-324",
    response_model=ReviewProjection,
)
def review(
    case_id: UUID,
    context: Authenticated,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2000),
):
    guard(context, request)
    snap = load_context(context, case_id)
    settings = request.app.state.settings
    before = parse_token(settings, case_id, snap["case"]["revision"], cursor)
    history = context.session.execute(
        text("SELECT public.sr_financial_case_history(:cid,:before,:lim)"),
        {"cid": case_id, "before": before, "lim": limit + 1},
    ).scalar_one()
    if history is None:
        raise AccessError(404)
    more = len(history) > limit
    history = history[:limit]
    exceptions = []
    if snap["fence_active"]:
        exceptions.append("FINANCIAL_FENCE")
    if snap["shipments"]:
        exceptions.append("PACKAGE_REQUIRES_REVIEW")
    if snap["has_active_hold"]:
        exceptions.append("ACTIVE_RETENTION_HOLD")
    try:
        return ReviewProjection(
            case_id=case_id,
            case_type=snap["case"]["type"],
            case_status=snap["case"]["status"],
            case_revision=snap["case"]["revision"],
            order_id=snap["order"]["id"],
            order_revision=snap["order"]["revision"],
            attempt_id=snap["attempt"]["id"],
            amount=exact_money(snap["attempt"]["amount"]),
            currency=snap["attempt"]["currency"],
            settlement_state=snap["attempt"]["state"],
            order_payment_status=snap["order"]["payment_status"],
            dispute_fence="active" if snap["fence_active"] else "none",
            exceptions=exceptions,
            prior_decisions=history,
            next_cursor=page_token(
                settings, case_id, snap["case"]["revision"], history[-1]["revision"]
            )
            if more
            else None,
        )
    except ValidationError:
        raise AccessError(503) from None


@router.post(
    "/admin/support-cases/{case_id}/financial-decisions",
    operation_id="API-323",
    response_model=DecisionReceipt,
)
def decide(
    case_id: UUID, body: FinancialDecision, context: Authenticated, request: Request
):
    guard(context, request, True)
    # The context takes parent/case/grant locks before replay and keeps them to commit.
    snapshot = load_context(context, case_id, True, body.settlement_review_reference)

    def work(_settings):
        plan = evaluate(snapshot, body)
        value = context.session.execute(
            text(
                "SELECT public.sr_financial_case_apply(:cid,CAST(:body AS jsonb),CAST(:plan AS jsonb))"
            ),
            {"cid": case_id, "body": body.model_dump_json(), "plan": json.dumps(plan)},
        ).scalar_one()
        if value is None:
            raise AccessError(404)
        if "error" in value:
            return value
        try:
            return DecisionReceipt.model_validate(value).model_dump(mode="json")
        except ValidationError:
            raise AccessError(503) from None

    return command(context, request, "finance.case:" + str(case_id), body, work, 200)


def require_order_clear(session, order_id, settings=None, *, lock=True):
    settings = settings or session.info.get("settings")
    function = "sr_financial_order_lock_clear" if lock else "sr_financial_order_clear"
    if (
        settings is not None
        and settings.financial_review_enabled
        and not session.execute(
            text(f"SELECT public.{function}(:oid)"), {"oid": order_id}
        ).scalar_one()
    ):
        fail(409, "FINANCIAL_REVIEW_REQUIRED")


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def financial_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.endswith(("/financial-review", "/financial-decisions")):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
