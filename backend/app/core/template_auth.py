"""Recent authentication policy scoped exclusively to Print Template operations."""
from datetime import UTC, datetime

from app.api.auth import require_verified_account
from app.api.v1.catalog import fail

MAX_TEMPLATE_AUTH_AGE_SECONDS = 3600 * 60


def recent_template_auth(context):
    require_verified_account(context)
    stamp = context.principal.authentication_time
    if (
        stamp is None
        or not (
            0
            <= datetime.now(UTC).timestamp() - stamp
            <= MAX_TEMPLATE_AUTH_AGE_SECONDS
        )
    ):
        fail(403, "REAUTH_REQUIRED")
