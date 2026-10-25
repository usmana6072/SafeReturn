# Temporary mobile testing on Windows

From PowerShell in `E:\Projects\SafeReturn`:

```powershell
.\backend\.venv\Scripts\python.exe .\ops\mobile-test.py
```

This builds the current Next.js frontend in a new ignored `tmp/mobile-test-*` directory, starts separate loopback FastAPI and production-mode Next servers, and creates a Cloudflare Quick Tunnel. It prints **VERIFIED MOBILE URL** only after HTTPS frontend, API liveness, unauthenticated API denial and private-file denial pass. Open that URL on Android/iPhone, including over cellular. The laptop must remain awake and connected. A new random URL is allocated each run. Existing localhost:3031/8030 services are untouched.

The project-local official Windows `cloudflared.exe` lives in ignored `tmp/local-tools`, together with its release URL/version/SHA256 manifest. The launcher verifies that checksum before execution. It installs no service and opens no LAN listener/firewall port. If absent, obtain the official Cloudflare release with permission; never execute a partial or unverified download.

To reuse a reviewed isolated build without rebuilding (it may lag current source):

```powershell
.\backend\.venv\Scripts\python.exe .\ops\mobile-test.py --build-dir .\tmp\task57n-web
```

Stop with **Ctrl+C** in the launcher console, or from another PowerShell window:

```powershell
.\backend\.venv\Scripts\python.exe .\ops\mobile-test.py --stop
```

The stop request shuts down only the latest mobile run's owned tunnel/gateway/frontend/backend. It does not stop the pre-existing localhost services. Logs, verification and process metadata remain in the run directory; no stored application objects are deleted.

## Routing and security

- React/Next.js App Router frontend: `frontend/app`, server-side Supabase SSR adapter in `frontend/lib/auth`; FastAPI entry point: `backend/app/main.py`, `app.main:app`; existing API routes remain `/api/v1/*`.
- The development-only gateway forwards `/api/*` to FastAPI and everything else to Next, preserving routes and duplicate Set-Cookie headers. It has fixed loopback destinations, exact public Host validation, trusted replacement forwarding headers, no access logging, private/no-store responses, and private dot-file/source-map rejection. It never serves repository files.
- Browsers use one HTTPS origin. No permissive CORS settings, wildcard hosts, CSRF bypasses, new permissions or disabled authentication are needed. Existing Origin checks receive the exact temporary HTTPS origin. Backend remains loopback-only, trusts no forwarded headers, and retains bearer/session/AAL/role guards.
- Next runs in production **mode locally**, so existing Secure/HttpOnly/SameSite=Lax host-only auth cookies remain enabled. This is not deployment. Only existing public Auth configuration and the server-only session signing key enter Next; database/provider credentials stay in the backend. Environment files and production deployment configuration are not edited. Existing API configuration is reused; no worker is launched and migration/worker DB URLs are excluded from the API child environment.
- This is a public temporary URL with existing application authentication, not an additional Cloudflare Access login. Share only with intended testers and stop it when finished. Use only dedicated synthetic test accounts and records. Do not perform real payment, notification, export, storage or dispatch actions.

## Supabase authentication redirects

Existing email/password sign-in is server-side and uses the same configured Supabase project; it does not require an email callback redirect. MFA and existing role guards are unchanged. No real login or credentials are used by the automated tunnel verification.

For email confirmation/recovery, the exact temporary callback is:

```text
https://<this-run-host>.trycloudflare.com/auth/callback
```

Only if using a **dedicated development Supabase project**, add that exact URL to its Authentication URL Configuration redirect allowlist, retain its Site URL/other entries, and remove the temporary entry afterward. Do not add wildcard trycloudflare URLs or modify a production project's settings. The launcher prints the exact callback but does not change managed Auth configuration or send email. If the currently configured project is production or the callback is not allowlisted, leave settings untouched: email confirmation/recovery testing remains unavailable through this URL; use an already-confirmed synthetic development account for password sign-in. Provider hostname restrictions such as Turnstile remain enforced and require separate development configuration rather than bypasses.

Logs may contain operational diagnostics; keep them local. `tmp/mobile-test-current.json` records the latest run. On failure inspect that run's `tunnel.log`, `gateway.log`, `api.log`, `frontend.log`, and (fresh builds) `build.log`. Never share environment files, credentials, raw authenticated responses or session cookies.

Some ISP resolvers temporarily return NXDOMAIN for new tunnel names. If initial Windows lookup fails, the launcher uses Cloudflare DNS-over-HTTPS only inside its verification process, still validating the original HTTPS hostname/certificate. `verification.json` records whether this fallback was needed; it changes no system or app DNS settings. If a phone cannot resolve the URL, retry after a short wait or try cellular instead of the laptop's Wi-Fi. The launcher does not claim a real phone or authenticated login was tested merely because HTTPS probes passed.
