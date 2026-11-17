PUBLIC_WEB_HOST = "www.safereturnqr.me"
PUBLIC_WEB_ORIGIN = f"https://{PUBLIC_WEB_HOST}"
PREVIOUS_WEB_HOSTS = {"safe-return-frontend.vercel.app", "safereturnqr.me"}
PREVIOUS_WEB_ORIGINS = {f"https://{host}" for host in PREVIOUS_WEB_HOSTS}


def canonical_web_origin(origin: str | None) -> str | None:
    return PUBLIC_WEB_ORIGIN if origin in PREVIOUS_WEB_ORIGINS else origin
