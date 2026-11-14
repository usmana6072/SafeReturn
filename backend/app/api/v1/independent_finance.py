"""Replacement router deliberately NOT installed in app.main.

Reuses quarantined paths, never alternative URLs. Mounting this router and
changing admission both require a separately approved release. Existing
routers and the frontend 70-operation quarantine remain untouched.
"""

from uuid import UUID

from fastapi import APIRouter, Request

from app.api.auth import Authenticated, require_staff
from app.api.v1.catalog import fail
from app.api.v1.independent_finance_contract import Reconciliation
from app.api.v1.payments import AllocationRetry, ReviewRequest
from app.api.v1.shipping_addresses import PrivateRoute
from app.services import independent_finance as service

router = APIRouter(route_class=PrivateRoute, tags=["independent finance replacement"])


def admission(context):
    require_staff(context, "finance")
    # Deliberate release boundary, not an environment switch or an alternate API.
    fail(503, "INDEPENDENT_FINANCE_NOT_RELEASED")


@router.get("/admin/finance/reconciliation", response_model=Reconciliation)
def reconciliation(order_id: UUID, request: Request, context: Authenticated):
    admission(context)
    return service.snapshot(context, request, order_id)


@router.post("/admin/payment-attempts/{attempt_id}/reviews")
def review(
    attempt_id: UUID, body: ReviewRequest, request: Request, context: Authenticated
):
    admission(context)
    return service.review(context, request, attempt_id, body)


@router.post("/admin/orders/{order_id}/qr-allocation/retry")
def retry(
    order_id: UUID, body: AllocationRetry, request: Request, context: Authenticated
):
    admission(context)
    return service.retry(context, request, order_id, body)
