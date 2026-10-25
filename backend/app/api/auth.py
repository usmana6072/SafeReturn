"""Reusable protected-route dependencies and explicit object guards (Task 2.1)."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import AuthRequired, AuthUnavailable, Principal
from app.db.runtime import api_transaction
from app.db.session import Database, get_database

logger = logging.getLogger("safereturn.auth")


class AccessError(Exception):
    def __init__(self, status: int):
        self.status = status


async def access_error(request: Request, error: AccessError):
    messages = {
        401: ("AUTH_REQUIRED", "Authentication required.", "تصدیق درکار ہے۔"),
        403: ("FORBIDDEN", "Access denied.", "رسائی کی اجازت نہیں ہے۔"),
        429: (
            "RATE_LIMITED",
            "Please try again later.",
            "براہ کرم کچھ دیر بعد دوبارہ کوشش کریں۔",
        ),
        404: ("NOT_FOUND", "Resource not found.", "مطلوبہ معلومات دستیاب نہیں ہیں۔"),
        503: (
            "PROVIDER_UNAVAILABLE",
            "Service temporarily unavailable.",
            "سروس عارضی طور پر دستیاب نہیں ہے۔",
        ),
    }
    code, message, urdu = messages[error.status]
    request_id = getattr(request.state, "request_id", uuid4().hex)
    headers = {"Cache-Control": "no-store", "X-Request-ID": request_id}
    if error.status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {
                "code": code,
                "message": message,
                "message_ur": urdu,
                "request_id": request_id,
                "details": {},
            }
        },
        headers=headers,
    )


bearer = HTTPBearer(auto_error=False, scheme_name="SupabaseAccessToken")


def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None or len(request.headers.getlist("authorization")) != 1:
        raise AccessError(401)
    verifier = request.app.state.jwt_verifier
    if verifier is None:
        raise AccessError(503)
    try:
        return verifier.verify(credentials.credentials)
    except AuthRequired:
        raise AccessError(401) from None
    except AuthUnavailable:
        raise AccessError(503) from None


@dataclass(frozen=True)
class AuthContext:
    session: Session
    principal: Principal
    email_verified: bool
    mfa_verified: bool


def authorize(session: Session, principal: Principal) -> AuthContext:
    """Called inside an API transaction with verified subject, never body IDs."""
    row = session.execute(
        text(
            "SELECT email_verified,mfa_active FROM public.sr_account_session_state(:sid)"
        ),
        {"sid": principal.session_id},
    ).one_or_none()
    if row is None:
        raise AccessError(401)
    mfa = principal.mfa_claim and row.mfa_active is True
    session.execute(
        text("SELECT set_config('safereturn.mfa_verified',:mfa,true)"),
        {"mfa": "true" if mfa else "false"},
    )
    return AuthContext(session, principal, row.email_verified is True, mfa)


def get_auth_context(
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    database: Annotated[Database | None, Depends(get_database)],
    response: Response,
) -> Iterator[AuthContext]:
    response.headers["Cache-Control"] = "no-store"
    if database is None:
        raise AccessError(503)
    try:
        with api_transaction(database, principal.user_id) as session:
            session.info["settings"] = request.app.state.settings
            context = authorize(session, principal)
            from app.services.support_development_access import enforce

            enforce(context, request.app.state.settings, request)
            yield context
    except SQLAlchemyError as error:
        original = getattr(error, "orig", None)
        sqlstate = getattr(original, "sqlstate", None)
        diagnostic = getattr(getattr(original, "diag", None), "message_primary", None)
        reason = diagnostic if sqlstate == "23514" else None
        logger.warning(
            "Protected API database operation unavailable (error_type=%s sqlstate=%s constraint=%s reason=%s)",
            type(original).__name__ if original is not None else type(error).__name__,
            sqlstate,
            getattr(getattr(original, "diag", None), "constraint_name", None),
            reason,
        )
        raise AccessError(503) from None


# Commit/rollback finishes before FastAPI sends the protected response.
Authenticated = Annotated[AuthContext, Depends(get_auth_context, scope="function")]


def require_verified_account(context: AuthContext):
    if not context.email_verified:
        raise AccessError(403)


STAFF_ROLES = frozenset(
    {"support", "operations", "finance", "security_admin", "superadmin"}
)


def require_staff(context: AuthContext, *allowed_roles: str):
    if not allowed_roles or not set(allowed_roles).issubset(STAFF_ROLES):
        raise ValueError("Guard requires explicit supported staff roles")
    require_verified_account(context)
    if not context.mfa_verified:
        raise AccessError(403)
    settings = context.session.info.get("settings")
    if (
        settings
        and settings.support_dev_enabled
        and context.principal.user_id == settings.support_dev_subject_id
        and (
            allowed_roles != ("support",)
            or context.session.execute(
                text("SELECT public.sr_support_dev_state(:uid)"),
                {"uid": context.principal.user_id},
            ).scalar_one()
            != "active"
        )
    ):
        raise AccessError(403)
    role = context.session.execute(
        text(
            "SELECT 1 FROM public.staff_roles WHERE user_id=:uid AND role=ANY(:roles) AND revoked_at IS NULL LIMIT 1"
        ),
        {"uid": context.principal.user_id, "roles": list(allowed_roles)},
    ).scalar_one_or_none()
    if role is None:
        raise AccessError(403)


def _owned(context: AuthContext, query: str, resource_id: UUID, **extra):
    if not isinstance(resource_id, UUID):
        raise AccessError(404)
    row = context.session.execute(
        text(query), {"uid": context.principal.user_id, "id": resource_id, **extra}
    ).scalar_one_or_none()
    if row is None:
        raise AccessError(404)


def require_pair_owner(context: AuthContext, pair_id: UUID):
    _owned(
        context,
        "SELECT 1 FROM public.tag_pairs WHERE id=:id AND owner_user_id=:uid",
        pair_id,
    )


def require_qr_owner(context: AuthContext, qr_id: UUID, *, tag_type: str | None = None):
    if tag_type not in (None, "lost", "ice"):
        raise ValueError("Invalid QR purpose guard")
    _owned(
        context,
        "SELECT 1 FROM public.qr_codes q LEFT JOIN public.tag_pairs p ON p.id=q.pair_id WHERE q.id=:id AND (p.owner_user_id=:uid OR (q.pair_id IS NULL AND public.sr_owns_qr(q.id))) AND q.is_current AND (CAST(:kind AS text) IS NULL OR q.tag_type=:kind)",
        qr_id,
        kind=tag_type,
    )


def require_order_owner(context: AuthContext, order_id: UUID):
    _owned(
        context,
        "SELECT 1 FROM public.orders WHERE id=:id AND customer_user_id=:uid",
        order_id,
    )


def require_payment_owner(context: AuthContext, attempt_id: UUID):
    _owned(
        context,
        "SELECT 1 FROM public.payment_attempts p JOIN public.orders o ON o.id=p.order_id WHERE p.id=:id AND o.customer_user_id=:uid",
        attempt_id,
    )


def require_message_recipient(context: AuthContext, message_id: UUID):
    _owned(
        context,
        "SELECT 1 FROM public.finder_messages WHERE id=:id AND recipient_owner_user_id=:uid",
        message_id,
    )
