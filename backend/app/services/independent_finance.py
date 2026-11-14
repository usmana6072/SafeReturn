"""Independent-only finance implementation, not exposed by the application.

Release requires separate review of the unmounted router and SQL grants. No
legacy reconciliation or review dispatcher is invoked by this service.
"""

import hashlib
import hmac
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from app.api.auth import AccessError, require_staff
from app.api.v1.catalog import fail
from app.api.v1.payments import finance_attempts, record, typed_result
from app.api.v1.privacy_exports import recent


def authorize(context, *, write=False):
    require_staff(context, "finance")
    if write:
        recent(context)


def snapshot(context, request, order_id):
    authorize(context)
    value = typed_result(
        context.session.execute(
            text("SELECT public.sr_independent_finance_snapshot(:sid,:oid)"),
            {"sid": context.principal.session_id, "oid": order_id},
        ).scalar_one()
    )
    # Existing finance-only decrypt/evidence metadata read; no private URLs.
    value["attempts"] = finance_attempts(order_id, context, request)["items"]
    return value


def mutation_authority(context, request, *, attempt_id=None, order_id=None):
    authorize(context, write=True)
    origin = request.app.state.settings.financial_review_web_origin
    if not origin or request.headers.getlist("origin") != [origin]:
        raise AccessError(403)
    target = (
        "(SELECT order_id FROM public.payment_attempts WHERE id=:aid)"
        if attempt_id
        else ":oid"
    )
    permitted = context.session.execute(
        text(
            f"SELECT public.sr_independent_finance_authorize(:sid,:auth_time,{target})"
        ),
        {
            "sid": context.principal.session_id,
            "auth_time": context.principal.authentication_time,
            "aid": attempt_id,
            "oid": order_id,
        },
    ).scalar_one()
    if permitted is not True:
        raise AccessError(403)


def review(context, request, attempt_id, body):
    authorize(context, write=True)
    # Validate before receipt replay as well as inside the DB lock boundary.
    if body.decision == "verify":
        if (
            not body.bank_verified
            or not body.bank_match_reference
            or body.settled_amount is None
            or body.settled_currency is None
        ):
            fail(422, "BANK_VERIFICATION_REQUIRED")
    elif body.bank_verified or any(
        v is not None
        for v in (body.bank_match_reference, body.settled_amount, body.settled_currency)
    ):
        fail(422, "INVALID_BANK_VERIFICATION")
    mutation_authority(context, request, attempt_id=attempt_id)

    def work(settings):
        authorize(context, write=True)
        fingerprint = None
        if body.decision == "verify":
            if not settings.payment_reference_key:
                raise AccessError(503)
            fingerprint = hmac.new(
                settings.payment_reference_key.get_secret_value().encode(),
                body.bank_match_reference.casefold().strip().encode(),
                hashlib.sha256,
            ).digest()
        value = typed_result(
            context.session.execute(
                text("""SELECT public.sr_independent_finance_review(
            :sid,:auth_time,:aid,:decision,:bank_verified,:amount,:currency,:fingerprint,:reason)
        """),
                {
                    "sid": context.principal.session_id,
                    "auth_time": context.principal.authentication_time,
                    "aid": attempt_id,
                    "decision": body.decision,
                    "bank_verified": body.bank_verified,
                    "amount": Decimal(body.settled_amount)
                    if body.settled_amount
                    else None,
                    "currency": body.settled_currency,
                    "fingerprint": fingerprint,
                    "reason": body.reason,
                },
            ).scalar_one()
        )
        context.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        context.session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return value, UUID(value["review_id"])

    return record(
        context,
        request,
        "payment.review",
        {"attempt_id": str(attempt_id), **body.model_dump()},
        work,
    )


def retry(context, request, order_id, body):
    mutation_authority(context, request, order_id=order_id)

    def work(settings):
        authorize(context, write=True)
        result = typed_result(
            context.session.execute(
                text(
                    "SELECT public.sr_independent_finance_retry(:sid,:auth_time,:oid)"
                ),
                {
                    "sid": context.principal.session_id,
                    "auth_time": context.principal.authentication_time,
                    "oid": order_id,
                },
            ).scalar_one()
        )
        context.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        context.session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return result, order_id

    return record(
        context,
        request,
        "allocation.retry",
        {"order_id": str(order_id), **body.model_dump()},
        work,
    )
