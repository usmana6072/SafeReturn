"""Narrow central route fence; never confers a role or alters ordinary staff."""

from sqlalchemy import text

METADATA = "/api/v1/admin/support-case-metadata"
READINESS = "/api/v1/me/support-development-readiness"
ROUTES = {METADATA, METADATA + "/{case_id}", METADATA + "/{case_id}/history"}


def enforce(context, settings, request):
    from app.api.auth import AccessError

    if not settings.support_dev_enabled:
        return
    if settings.support_dev_subject_id is None:
        raise AccessError(503)
    if context.principal.user_id != settings.support_dev_subject_id:
        return
    from app.services.support_provisioning import PROJECT

    if settings.supabase_url != f"https://{PROJECT}.supabase.co":
        raise AccessError(403)
    route = getattr(request.scope.get("route"), "path", "")
    # Installed FastAPI lazy include_router keeps a relative APIRoute template.
    if route.startswith(("/admin/", "/me")):
        route = "/api/v1" + route
    if not request.scope.get("path", "").startswith("/api/v1/"):
        raise AccessError(403)
    if request.method != "GET" or route not in ROUTES | {
        "/api/v1/me",
        "/api/v1/me/staff-security",
        READINESS,
    }:
        raise AccessError(403)
    if route not in {"/api/v1/me", READINESS}:
        state = context.session.execute(
            text("SELECT public.sr_support_dev_state(:uid)"),
            {"uid": context.principal.user_id},
        ).scalar_one()
        if state != "active":
            raise AccessError(403)
    if route in ROUTES:
        context.session.execute(
            text("SELECT set_config('safereturn.support_dev_metadata','true',true)")
        )
