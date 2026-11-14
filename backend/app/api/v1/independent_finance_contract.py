"""Closed independent finance projections. No QR tokens or bank fingerprints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.api.v1.catalog import Closed


class Allocation(Closed):
    state: Literal["awaiting_verified_payment", "reconciliation_pending", "allocated"]
    reason_code: (
        Literal[
            "stock_shortage",
            "financial_review",
            "cancellation_review",
            "template_review",
        ]
        | None
    )
    requested_count: int = Field(ge=1, le=50, strict=True)
    allocated_count: int = Field(ge=0, le=50, strict=True)

    @model_validator(mode="after")
    def complete_allocation(self):
        if self.state == "allocated":
            if (
                self.allocated_count != self.requested_count
                or self.reason_code is not None
            ):
                raise ValueError("Incomplete allocation")
        elif self.allocated_count != 0 or (
            (self.state == "reconciliation_pending") != (self.reason_code is not None)
        ):
            raise ValueError("Invalid pending allocation")
        return self


class Review(Closed):
    review_id: UUID
    attempt_id: UUID
    decision: Literal["verify", "reject", "request_more_info"]
    bank_verified: bool
    reason: str = Field(max_length=1000)
    reviewed_at: datetime
    settled_amount: str | None
    settled_currency: str | None
    settlement_reference_recorded: bool


class Evidence(Closed):
    id: UUID
    content_type: Literal["image/png", "image/jpeg", "application/pdf"]
    bytes_size: int = Field(ge=1, le=5000000)


class Sender(Closed):
    holder: str | None = None
    transfer_reference: str | None = None


class Attempt(Closed):
    attempt_id: UUID
    state: str
    amount: str
    currency_code: str
    sender_account: str | None
    sender_holder: Sender
    evidence: list[Evidence]


class Reconciliation(Closed):
    order_id: UUID
    order_number: str
    order_status: str
    payment_status: str
    fulfillment_status: str
    amount_due: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    currency: Literal["PKR"]
    allocation: Allocation
    signals: list[
        Literal[
            "REVIEW_PENDING",
            "ATTEMPT_ORDER_AMOUNT_MISMATCH",
            "ATTEMPT_ORDER_CURRENCY_MISMATCH",
            "MULTIPLE_OPEN_ATTEMPTS",
            "ORDER_SETTLEMENT_MISMATCH",
            "VERIFIED_ALLOCATION_MISMATCH",
            "VERIFIED_HISTORY_MISMATCH",
            "DUPLICATE_VERIFIED_REFERENCE",
        ]
    ]
    reviews: list[Review] = Field(max_length=100)
    attempts: list[Attempt] = Field(max_length=100)
    history_limit: Literal[100]
    can_review: bool
    unavailable_checks: list[str]
