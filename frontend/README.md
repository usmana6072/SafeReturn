# SafeReturn frontend

Task 2.3 adds real Next callback/open-redirect, forged-cookie/recovery and hostile
Origin Server Action checks in `tests/auth-negative.spec.ts`, plus controlled
SDK login throttling/outage, revoked refresh and rejected PKCE cases. Controlled
providers prove SDK/session failure handling, never actual email delivery.

The existing `scripts/test-live-auth.py` runner now also runs browser negatives.
For an explicitly authorized user-controlled mailbox, its opt-in
`--email <authorized-destination>` mode opens a visible Edge test window, submits
signup once and waits for the user to open confirmation and recovery links in
that same tab. Do not paste token-bearing links into chat. It verifies delivery
only when both real callbacks complete; a neutral email-request response alone
is not delivery evidence. It does not change passwords, globally revoke sessions,
delete Auth users or change provider redirect configuration. The new test account
remains controlled through the mailbox. Only newly created test sessions are
locally revoked; servers stop and installed metadata/domain counts are checked.
The runner refuses live requests if database/client UTC clocks differ by more
than 60 seconds; correct the system clock rather than weakening JWT validation.
Use `--recovery-email <authorized-destination>` to verify recovery for the same
mailbox without submitting signup again. The callback allowlist must permit
`http://127.0.0.1:3100/auth/callback`; a neutral request result does not verify
that allowlist. User mailbox interaction is required while the test window is open.

Node.js 24 was used for local verification. From this folder:

```powershell
npm ci
$env:NEXT_TELEMETRY_DISABLED="1"
npm run dev
```

Production verification: `npm run build`, `npm run typecheck`, then `npm test`.
Install test Chromium once with `npx playwright install chromium`.
Alternatively set `PLAYWRIGHT_CHANNEL=msedge` to use installed Microsoft Edge.
In restricted Windows environments, start the production server on port 3100,
set `PLAYWRIGHT_EXTERNAL_SERVER=1`, and run the tests against that server; stop
the server afterwards. This avoids blocked process-tree cleanup by the runner.

The homepage uses the approved teal mock layout, system font fallbacks, and
English/Urdu dictionaries. Language changes persist in a server-managed cookie
and set document language/direction before rendering. No font CDN is required.
Catalog shows an empty state pending Phase 5 live catalog implementation; no sample prices,
fake QR tokens, or future products are offered. Checkout
belongs to later tasks. Native mobile navigation and FAQ disclosure work without
client JavaScript. Final fonts, brand artwork and Urdu copy require release QA.

## Local API integration

Start FastAPI on localhost:8000 using the backend README, then run `npm run dev`.
Development defaults the server-only API origin to `http://127.0.0.1:8000`.
Set `SAFERETURN_API_ORIGIN` explicitly for a production build/server; it accepts
an HTTPS origin, or HTTP on loopback for local development. Set it in the process
environment; the root `.env.example` lists names only and is not loaded automatically.

`GET /api/health/live` on Next.js checks FastAPI's `/api/v1/health/live`.
It returns `{ "status": "ok" }` on success, or a generic 503 unavailable response
on configuration, timeout, network, HTTP or response-contract failures.
Responses are not cached. The API origin is server-only; readiness tokens are
never forwarded. The browser calls its own origin, so CORS changes are unnecessary.

After `npm run build`, run `npm run test:integration:local` to start the actual
backend/frontend, execute tests, stop the backend and verify the web's outage
response, then stop the remaining process. The script uses ports 8100/3100 and
refuses occupied ports. Set `PLAYWRIGHT_CHANNEL=msedge` to use installed Edge.
Unit transport tests use explicit mocked HTTP responses; integration tests use
real local servers and are skipped in ordinary browser runs without an explicit
`SAFERETURN_TEST_API_ORIGIN`. No Supabase or provider credentials are required.

## Account flows (Task 2.2)

Approved `/auth/sign-in`, `/auth/sign-up`, `/auth/verify-email`,
`/auth/forgot-password`, `/auth/reset-password` and `/auth/callback` routes use
the supplied authentication visual reference; `/login` and `/signup` also render
the forms. `/account` reads/edits the authenticated user's name and locale through
FastAPI. English/Urdu layouts and accessible password controls are included.
Phone collection waits for the approved encryption/key lifecycle; the mock's
plaintext phone field is intentionally absent from this slice.

For configured local development, start the restricted FastAPI runtime as in
backend/README.md, then from frontend:

```powershell
../backend/.venv/Scripts/python.exe scripts/run-configured.py dev
```

The launcher explicitly reads ignored backend/.env and forwards only Supabase
origin/publishable key, the web-specific recovery signing key and public API/web
origins. Database, migration, worker and test URLs are removed from its child
environment. It never prints values. Set `SAFERETURN_API_ORIGIN` and
`SAFERETURN_WEB_ORIGIN` explicitly when using different ports/hosts. The configured
web origin must exactly match the browser's origin. Add that origin's
`/auth/callback` to the development project's approved Auth redirect allowlist;
no provider configuration is changed by the launcher. Production requires HTTPS,
proper secrets management and the production callback allowlist.

## Deployment (Task 6.3)

`vercel.json` pins the Next.js framework, `npm ci` install, and production
build command. Only approved public configuration may use `NEXT_PUBLIC_`
variables; API origins, signing keys, database URLs, provider keys, and storage
credentials remain server-side in the deployment secret manager. The release
sequence is backend-compatible migration and smoke checks first, then the
frontend rollout and progressive feature-flag activation. Do not deploy from a
workstation with `.env` files or token-bearing test artifacts.

Session decision: maintained `@supabase/ssr` with a **server-only** client.
HttpOnly, SameSite=Lax cookies are Secure in production; no browser Auth client,
localStorage tokens or serialized sessions. The Next proxy refreshes cookies;
server reads verify with provider `getUser`, and FastAPI independently checks
signature and active DB session. Mutations require Next Server Actions' Origin
protection plus exact configured-origin checks. Callback exchanges only a bounded
PKCE code with the cookie verifier and redirects to fixed internal paths. Open
confirmation/recovery emails in the initiating browser. Token URLs are never
generated; callback responses remove the code and set no-referrer/no-store.

Signup with confirmation enabled returns a neutral check-email state. Resend and
recovery requests avoid account enumeration. Password recovery additionally needs
a signed 10-minute, token-bound HttpOnly ticket minted after the SDK's
PASSWORD_RECOVERY event. `SAFERETURN_SESSION_SIGNING_KEY` is a private 32-byte hex
web key (ignored development value generated locally); never expose it as
NEXT_PUBLIC configuration. Logout requests provider global-session invalidation.
Auth attempts have a bounded per-process limiter and provider throttling; a shared
limiter is required before multiple-instance production rollout.

Validation: build/typecheck, seven controlled-provider tests executing the actual
SDK adapter, seven browser Auth checks, real local API integration/outage tests,
and reviewed desktop English/mobile Urdu screenshots. Controlled provider tests
do not claim real email delivery, callback allowlist or positive live user login.
Live verification with the supplied confirmed development user also passed:
real browser login, private account read, Secure/HttpOnly/Lax session cookies,
no localStorage tokens, local test-session revocation, API 401 and return to login.
Installed metadata/domain row counts were inspected before setup and unchanged
after teardown. No profile edits, Auth user creation or email requests were made;
unrelated sessions are preserved. Run from frontend with the backend virtualenv:

```powershell
../backend/.venv/Scripts/python.exe scripts/test-live-auth.py
```

This explicit runner starts API/Next on 8100/3100 with separate environments;
only the Playwright process receives test-user credentials. It stops its own
servers and cleans the new local session even after a failed UI assertion.
`backend/auth_live_login.py` separately verifies real refresh and API session
revocation. Both read the ignored test credentials without displaying them.
Live signup/email/recovery delivery and Task 2.3's broader authorization/provider
integration matrix remain separate; no provider redirect settings were changed.

Task 3.4 customer routes: `/dashboard`, `/my-qr`, `/my-qr/[qrId]`, `/kits`,
`/kits/[pairId]`, and `/activate`. Approved legacy per-kit Lost/ICE/contact paths
resolve through the owner-authorized pair to the canonical QR editor. The QR
collection searches and filters on the server, pages without a one-pair limit,
and never expands physical copies into duplicate identities. Editors use the
existing profile/contact/preference APIs with quoted versions, explicit consent,
masked replacement phones, retained medical-note semantics, stale-save errors,
unsaved-change warnings and independent privacy disabling during key outages.

`/q/[token]` currently implements only the minimal inactive activation entry;
active Lost/ICE public experiences remain Phase 4. The activation button stores
a signed short-lived HttpOnly/Secure/Lax scan cookie. Login/signup callback
returns only to the fixed `/activate` path; actor-bound intent confirmation uses
one stable idempotency key across retries. Concealed codes are submitted in POST
bodies and never placed in redirects or cookies. Recovery still takes priority
over activation return. Expired/forged contexts require a new scan.

The new screens need no Resend credentials. Actual email delivery remains a later
worker task. `tests/integration/test_qr_browser.py` in the backend launches the
real built Next application and API with isolated PostgreSQL plus simulated
Auth; `qr-fixture-fetch.cjs` is loaded only in that test process, never by normal
development/start scripts. Test outputs remain ignored under `test-results/`.
# SafeReturn frontend

The frontend includes bilingual English/Urdu rendering with RTL direction,
responsive customer and public-scan layouts, keyboard skip links, visible
focus indicators, and no-JavaScript mobile navigation. Release acceptance
coverage is in `tests/release-accessibility.spec.ts`; it checks mobile and
desktop overflow, RTL switching, keyboard focus, unauthenticated private-route
denial, and reduced-motion/forced-colors-compatible shared styling.

Task 4.1 public scan acceptance is driven by the backend's isolated
`tests/integration/test_public_qr.py` controller after `npm run build`.
It runs `tests/public-qr.spec.ts` against real Next/API/PostgreSQL, using only
synthetic tokens; no sign-in or provider call is needed. The public scan keeps
its own URL on language changes, renders critical English/Urdu instructions,
and supports contact-only ICE profiles. Initial HTML/RSC contains no phone.
Screenshots remain ignored under `test-results/`.

Task 4.2 protected actions require a public
`NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY` in
frontend environment and the corresponding backend secret/expected hostname.
No key is written automatically. Initial scan HTML/RSC contains no phone;
a click mounts the compact challenge widget, then a verified POST reveals only
the selected phone or issues an explicit WhatsApp confirmation link. Failures
refresh the challenge, and no WhatsApp navigation happens automatically.
The backend `test_public_contacts.py` controller runs `public-contacts.spec.ts`
and the existing public scan regression with real Next/API/PostgreSQL and a
controlled widget/Siteverify simulator. It never sends WhatsApp/email messages.


### Task 5.1 catalog

`/` reads the backend featured endpoint without caching. `/shop` provides URL-backed
search/category filters and SKU detail links; cards show the server's Decimal price
strings. Products, variants and public media are validated before rendering. Empty
catalogs and API failures have different bilingual messages. Featured scrolling is
manual, keyboard accessible and direction-aware; it never autoplays.

`/admin/products` requires a verified Auth session; the API independently checks the
existing staff role, account, MFA and RLS for every request. Draft/create/edit/archive,
categories, variant edits and public-image attach/unlink are available. Browser writes
use a same-origin server relay so API bearer credentials stay server-side. Versions
and Idempotency-Key protect concurrent updates and unchanged retries.

Public images can be selected from existing approved Cloudinary assets or uploaded
via API-225's signed authorization, browser upload and server-verified finalization.
Configure the backend's controlled Cloudinary account/folder and signed upload preset
with raster formats and 5 MB maximum; missing provider config fails closed. Signing
never returns the API secret. The grant uses generated product-scoped public IDs,
no overwrite and a one-hour provider validity. Upload failures leave the form intact;
if upload succeeds but finalization fails, the returned public ID can be retried.
Only public product photos belong here; private proofs and print artifacts do not.
Provider-side preset/account acceptance remains a release check.

Build with `npm run build`; the isolated PostgreSQL controller runs
`tests/catalog.spec.ts` against real local Next/API and simulated Auth/Cloudinary.
Run through `backend/tests/integration/test_catalog.py`, with explicit development
DB configuration and `SAFERETURN_CATALOG_BASE_REVISION=0015_public_catalog` after
migration installation. Never point its provider fixtures at a live account.
`ops/run-task51-local.py` starts fresh API/web processes on free loopback ports
without stopping existing applications and reports the verified URL.


### Task 5.2 cart and checkout

The SKU detail configurator collects independent Lost/ICE copy counts by active
variant. `/cart` stores only variant IDs/counts in localStorage, validates them again
and preserves the cart through sign-in; no price, token, address or credential is
stored there. The backend is authoritative for prices, publication and stock.
`/checkout` requires a verified session, collects private shipping details and an
explicit contact confirmation, then obtains an encrypted server quote. Review shows
exact server money strings and expiry; explicit total acceptance is required to
confirm. Same-origin server relay keeps bearer tokens server-only. Unchanged failed
requests retain their idempotency key; expired quotes can be refreshed with a fresh
key. Failed stock/provider/validation responses preserve counts and private fields.
A saved order awaits separate payment verification; this flow makes no payment claim.

Controlled acceptance: `tests/checkout.spec.ts` runs through the isolated PostgreSQL
controller in `backend/tests/integration/test_checkout.py`, with simulated Auth and
real Next/API/database. It covers guest cart continuity, independent counts, quote,
confirm, lost-response retry, expiry, no stock, CSRF and mobile/Urdu/RTL keyboard flow.

For the completed local app use `ops/run-task52-local.py`. It reads existing ignored
backend/frontend configuration and bridges only the public Supabase URL/publishable
key into the web process when needed; database, Cloudinary and email secrets are not
forwarded by this bridge. Files remain unchanged. Startup checks home/catalog/shop/cart;
final anonymous checkout smoke returns 307 to login (not a generic configuration 500).


For the current local staff console, preserve the explicit origins and use the
configured launcher (plain `next start` does not load backend Auth settings):

```powershell
$env:SAFERETURN_WEB_ORIGIN="http://localhost:3031"
$env:SAFERETURN_API_ORIGIN="http://127.0.0.1:8030"
../backend/.venv/Scripts/python.exe scripts/run-configured.py start --hostname 127.0.0.1 --port 3031
```
