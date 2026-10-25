"""Reviewed cancellation requests and independently reconciled release; no refunds."""

import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, field_validator, model_validator
from sqlalchemy import text

from app.api.auth import (
    AccessError,
    Authenticated,
    require_staff,
    require_verified_account,
)
from app.api.v1.catalog import Closed, fail
from app.api.v1.shipping_addresses import PrivateRoute
from app.api.v1.support_cases import command

router = APIRouter(tags=["cancellation review"], route_class=PrivateRoute)


class Confirmed(Closed):
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def explicit(cls, value):
        if value is not True:
            raise ValueError("Confirmation required")
        return value


class CancellationRequest(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
    reason_code: Literal["ordered_by_mistake", "no_longer_needed", "other"]


class ReviewBinding(Confirmed):
    request_id: UUID
    expected_order_revision: int = Field(ge=1, le=2147483646, strict=True)
    expected_request_revision: int = Field(ge=1, le=2147483646, strict=True)


class Reconciliation(ReviewBinding):
    outcome: Literal["clear", "escalate"]
    reason_code: Literal["no_settlement_pending", "settlement_requires_review"]

    @model_validator(mode="after")
    def consistent(self):
        if (self.outcome == "clear") != (self.reason_code == "no_settlement_pending"):
            raise ValueError("Outcome mismatch")
        return self


class Decision(ReviewBinding):
    decision: Literal["investigate", "approve", "reject", "escalate"]
    reason_code: Literal[
        "review_started", "eligible_unpaid", "request_declined", "requires_review"
    ]
    reconciliation_id: UUID | None = None

    @model_validator(mode="after")
    def consistent(self):
        reasons = {
            "investigate": "review_started",
            "approve": "eligible_unpaid",
            "reject": "request_declined",
            "escalate": "requires_review",
        }
        if reasons[self.decision] != self.reason_code or (
            self.decision == "approve"
        ) != (self.reconciliation_id is not None):
            raise ValueError("Decision mismatch")
        return self


class Release(ReviewBinding):
    reconciliation_id: UUID


def guard(context, request, role=None, recent=False):
    require_verified_account(context)
    if not request.app.state.settings.cancellation_enabled:
        raise AccessError(503)
    expected = request.app.state.settings.cancellation_web_origin
    if not expected or request.headers.getlist("origin") != [expected]:
        raise AccessError(403)
    if role:
        require_staff(context, role)
    if recent:
        stamp = context.principal.authentication_time
        if stamp is None or not 0 <= datetime.now(UTC).timestamp() - stamp <= 300:
            fail(403, "REAUTH_REQUIRED")


def run(context, request, order_id, action, body, *, pair_id=None, status=200):
    # Include the resource in the operation scope so a key cannot cross orders/pairs.
    operation = f"cancellation.{action}:{order_id or pair_id}"

    def work(_settings):
        payload = body.model_dump(mode="json")
        if action in {"reconcile", "release"} or (
            action == "decision" and body.decision == "approve"
        ):
            snapshot = context.session.execute(
                text("SELECT public.sr_cancellation_eligibility(:oid,:rid)"),
                {"oid": order_id, "rid": body.request_id},
            ).scalar_one()
            clear = release_eligible(snapshot)
            if action == "reconcile" and body.outcome == "clear" and not clear:
                fail(409, "RECONCILIATION_REQUIRED")
            payload["application_clear"] = clear
        result = context.session.execute(
            text(
                "SELECT public.sr_cancellation_command(:oid,:pid,:action,CAST(:payload AS jsonb))"
            ),
            {
                "oid": order_id,
                "pid": pair_id,
                "action": action,
                "payload": json.dumps(payload),
            },
        ).scalar_one()
        if result.get("error") == "FORBIDDEN":
            raise AccessError(403)
        # JSON-safe UUID/timestamps are produced by the database command.
        return result

    return command(context, request, operation, body, work, status)


def release_eligible(snapshot):
    """Fail-closed application check; SQL independently rechecks under its locks."""
    return bool(
        snapshot
        and snapshot.get("order_status") == "placed"
        and snapshot.get("payment_status") in {"awaiting_transfer", "rejected"}
        and snapshot.get("fulfillment_status") == "unallocated"
        and not snapshot.get("production", True)
        and not snapshot.get("shipment", True)
        and snapshot.get("units")
        and all(
            unit.get("status") == "reserved"
            and unit.get("ownership_status") == "unclaimed"
            and unit.get("owner_user_id") is None
            and unit.get("activated_at") is None
            and unit.get("inventory_status")
            in {"generated", "printed", "qa_passed", "reserved"}
            for unit in snapshot["units"]
        )
        and isinstance(snapshot.get("attempt_states"), list)
        and all(
            state in {"rejected", "expired"} for state in snapshot["attempt_states"]
        )
    )


@router.post("/me/orders/{order_id}/cancel", operation_id="API-065", status_code=202)
def request_cancel(
    order_id: UUID, body: CancellationRequest, context: Authenticated, request: Request
):
    guard(context, request)
    return run(context, request, order_id, "request", body, status=202)


@router.post(
    "/admin/orders/{order_id}/cancellation-reconciliations", operation_id="API-340"
)
def reconcile(
    order_id: UUID, body: Reconciliation, context: Authenticated, request: Request
):
    guard(context, request, "finance")
    return run(context, request, order_id, "reconcile", body)


@router.post("/admin/orders/{order_id}/cancellation-decisions", operation_id="API-341")
def decide(order_id: UUID, body: Decision, context: Authenticated, request: Request):
    guard(context, request, "operations")
    return run(context, request, order_id, "decision", body)


@router.post("/admin/tag-pairs/{pair_id}/release-allocation", operation_id="API-087")
def release(pair_id: UUID, body: Release, context: Authenticated, request: Request):
    guard(context, request, "operations", recent=True)
    return run(context, request, None, "release", body, pair_id=pair_id)


def projection(context, order_id):
    """Minimal owner/staff status, never finance attestation or raw evidence."""
    value = context.session.execute(
        text(
            "SELECT jsonb_build_object('order_revision',o.revision,'cancellation_request',(SELECT jsonb_build_object('request_id',r.id,'request_status',r.status,'request_revision',r.revision) FROM public.order_cancellation_requests r WHERE r.order_id=o.id ORDER BY r.created_at DESC,r.id DESC LIMIT 1)) FROM public.orders o WHERE o.id=:id"
        ),
        {"id": order_id},
    ).scalar_one()
    return value if isinstance(value, dict) else json.loads(value)


def install(application):
    application.include_router(router, prefix="/api/v1")

    @application.middleware("http")
    async def private_cancellations(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.endswith(
            (
                "/cancel",
                "/cancellation-reconciliations",
                "/cancellation-decisions",
                "/release-allocation",
            )
        ) or path.startswith(("/api/v1/me/orders/", "/api/v1/admin/orders/")):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
