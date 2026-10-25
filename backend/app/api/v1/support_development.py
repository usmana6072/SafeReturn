"""Own-session readiness, no role creation, business reads or audit mutation."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.api.auth import AccessError, Authenticated, require_verified_account
from app.services.support_provisioning import PROJECT

router = APIRouter()


@router.get("/me/support-development-readiness", include_in_schema=False)
def readiness(context: Authenticated, request: Request):
    settings = request.app.state.settings
    require_verified_account(context)
    if (
        not settings.support_dev_enabled
        or context.principal.user_id != settings.support_dev_subject_id
        or settings.supabase_url != f"https://{PROJECT}.supabase.co"
        or not context.mfa_verified
        or context.principal.authentication_time is None
        or not 0
        <= datetime.now(UTC).timestamp() - context.principal.authentication_time
        <= 300
    ):
        raise AccessError(403)
    fingerprint = getattr(request.app.state, "support_dev_implementation_digest", None)
    if not fingerprint:
        raise AccessError(503)
    state = context.session.execute(
        text("SELECT public.sr_support_dev_state(:uid)"),
        {"uid": context.principal.user_id},
    ).scalar_one()
    return {
        "project": PROJECT,
        "subject_id": str(context.principal.user_id),
        "implementation_sha256": fingerprint,
        "metadata_only": True,
        "state": state,
    }
