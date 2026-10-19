# SafeReturn backend

Task 2.3 auth/security verification: explicitly load the ignored environment and
run `tests/integration/test_auth_negative.py`, `test_auth_guards.py`, and
`test_account_api.py` together with pytest, `-p no:cacheprovider -W error`.
The request-level attack matrix exercises account GET/PATCH with missing,
malformed, unsigned, foreign-signature, wrong issuer/audience, expired/future,
service-role/anonymous/refresh and nonexistent/mismatched-session credentials.
It checks bilingual concealed errors, server request IDs, no-store, unchanged
profiles/audit and connection recovery. Existing owner/staff/email/MFA/RLS,
version/race/audit rollback cases complete the database boundary coverage.
Fixtures use only UUID rehearsal namespaces; installed metadata is inspected
before setup and checked after cleanup. Ban/session fixture times derive from
PostgreSQL's clock. JWT verification still uses the runtime clock and must not
be relaxed to hide host/provider clock skew. No new migration is required.

From `backend` using Python 3.12 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Public liveness: `GET /api/v1/health/live`. Readiness is disabled (404)
unless `SAFERETURN_READINESS_TOKEN` is set in the process environment.
Send that token as a Bearer credential; unauthorized probes return 401.
Authorized readiness returns 200 only after a PostgreSQL `SELECT 1` succeeds,
otherwise a generic 503. This checks connectivity, not schema/business readiness.
Environment files are not loaded implicitly. No database migrations run at startup.

Set `SAFERETURN_DATABASE_URL` in the process environment to a dedicated development
PostgreSQL URL (`postgresql://` or `postgresql+psycopg://`). Credentials stay in ignored
local configuration; never paste them in chat or put them in the example file.
For an ignored environment file, load it explicitly with Uvicorn's `--env-file`
option. Use a least-privilege runtime role; migration credentials remain separate.
Remote database URLs require TLS (`sslmode=require`, `verify-ca`, or `verify-full`);
omitting remote sslmode defaults to require. Local loopback can use plain transport.

The app creates one lazy SQLAlchemy engine per lifespan, with psycopg 3,
pre-ping, no overflow, bounded pool/connect/statement timeouts and hidden SQL
parameters. Shutdown disposes the pool. An unconfigured database leaves API
liveness available and protected readiness unavailable. Invalid configuration
fails startup without including the connection URL in the error message.

Services use `Database.transaction()` for an explicit commit/rollback scope.
`Database.session()` and `get_session` provide scopes with no implicit commit;
closing a session rolls back unfinished work. Sessions are never globally shared.
The separate worker can reuse this factory when its owning task is implemented.

Optional pool settings (prefix `SAFERETURN_`): `DATABASE_POOL_SIZE` (default 5),
`DATABASE_POOL_TIMEOUT_SECONDS` (5), `DATABASE_CONNECT_TIMEOUT_SECONDS` (3),
`DATABASE_STATEMENT_TIMEOUT_MS` (5000). These are development transport defaults.

Real PostgreSQL tests require `SAFERETURN_TEST_DATABASE_URL` pointing to an
authorized nonproduction database. Run `.venv/Scripts/python.exe -m pytest -q tests/integration`.
Session tests use SELECTs and a session-local temporary table. Schema tests run
Alembic inside an outer transaction and roll back all test DDL and synthetic data,
including a synthetic Auth user. Missing test configuration skips these checks; local mock tests are not
evidence of real PostgreSQL commit/rollback correctness.

For credentials saved in the ignored `backend/.env`, explicitly load them for tests:

```powershell
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -W error
```

This disables pytest's optional filesystem cache for restricted Windows execution;
it preserves all assertions and warning-as-error checks. Short tracebacks are the
default to avoid driver frames containing connection configuration.

Checks: `.venv/Scripts/python.exe -m pytest -q` and
`.venv/Scripts/python.exe -m ruff check app tests`.

## Deployment and release operations (Task 6.3)

The API image is built from `backend/Dockerfile` and exposes the public
`/api/v1/health/live` liveness endpoint. The checked-in `backend/railway.toml`
is a Railway API-service baseline; configure a separate worker service with the
same reviewed revision and server-only environment, rather than running worker
code in the API process. The readiness endpoint remains protected by
`SAFERETURN_READINESS_TOKEN` and checks PostgreSQL connectivity without exposing
connection details.

`ops/release-preflight.ps1` performs only HTTPS liveness and authorized
readiness checks. It does not run migrations, write application data, call
providers, or deploy. Run it against staging before any authorized promotion:

```powershell
.\ops\release-preflight.ps1 -Environment staging -ApiOrigin https://staging-api.example
```

The API emits one sanitized JSON access event per request with a generated
request ID, route template, status, duration, service, and version. It does not
log query strings, authorization headers, request bodies, tokens, phone
numbers, messages, locations, signed URLs, or provider payloads.

## Physical and pilot release gates (Task 6.4)

`ops/pilot-release-gates.example.json` is a non-secret evidence-record template
for the Lahore pilot. Copy it to an ignored working file and fill it only with
synthetic release metadata and links to controlled evidence. The record stays
blocked until both locked `lost` and `ice` templates, bilingual English/Urdu
copy, reviewed font fingerprints, the 4-module quiet zone, 30 mm indoor and
35 mm outdoor QR-symbol minimums, physical scan results, all required provider
smoke checks, and pilot sign-off are recorded as passed.

Validate a completed record without contacting providers or modifying any
service:

```powershell
python ops/validate-pilot-gates.py path\to\pilot-release-gates.json
```

This validator does not claim that a QR was scanned, an artwork file was
printed, a provider account was configured, or a pilot was approved. Physical
evidence must identify the actual printer/material, device/browser versions,
template and font fingerprints, exact QR dimensions, Lost/ICE ordering,
copy-count/unique-URL reconciliation, and the reviewer/date. Keep activation
secrets, private customer data, payment identifiers, provider credentials, and
token-bearing artifacts out of the record and its evidence links.

Promotion is expand-first: verify a tested backup/PITR and object-retention
plan, inspect migration state read-only, apply only reviewed additive changes
to staging, deploy compatible API/worker code, smoke-test, then promote the
frontend and enable approved flags progressively. Rollback reverts code and
feature flags to a schema-compatible release; it does not downgrade a
destructive migration or erase post-release orders. Restore drills must use an
isolated project and verify QR revocation, order/payment history, authorization,
and required private objects before any production recovery decision.

Task 1.2 migrations (run from `backend`, authorized development only):

```powershell
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m alembic check
```

Inspect target metadata before upgrading. Revision `0001_identity_profiles`
requires managed `auth.users.id UUID` and refuses to run over existing domain
tables; it never adopts or stamps an unknown schema. PostgreSQL transactional DDL
and a five-second lock timeout protect partial application. It adds ten tables,
indexes, RLS with no browser policies/grants, and trigger functions. No existing
table or Auth schema is changed. Runtime least-privilege roles/policies remain
Task 1.4; the development migration connection is privileged.

Every pair must commit with exactly one current Lost and ICE QR. Parent locks,
deferred checks on both parent and children, and partial uniqueness allow atomic
replacement while preserving historical QR/profile rows. QR routing identity
fields are immutable. Profiles use the full canonical `lost_item_profiles` and
`ice_profiles` names, with v1.2 instruction fields and positive profile versions;
they do not create competing abbreviated placeholder profile tables. Publication
and phone/key/consent checks are storage guards; authorization and encryption
services are future tasks. Timestamp triggers update `updated_at`; services will
own optimistic version increments.

Downgrade deliberately refuses destructive table removal. On a failed upgrade,
PostgreSQL rolls back DDL; after a successful upgrade, use a reviewed additive
forward revision for recovery. Do not edit a shared initial revision or delete
historical identities. The migration embeds frozen DDL independently of mutable
ORM mappings; `initial_guards.sql` is its readable guard source snapshot.

Task 1.3 adds revision `0002_commerce` after `0001_identity_profiles`.
It adds 16 tables: catalog categories/products/variants/images, orders and
snapshot lines, pair reservation/allocation units, tag-specific QR uses, payment
attempts/evidence/reviews, reusable addresses and order address snapshots,
shipments/shipment pairs, and physical pair-print QA. Identity/Auth tables and
the previous revision remain intact. Unknown target or legacy commerce tables
cause a reconciliation error before DDL; no automatic adoption, backfill,
replacement, or destructive downgrade is attempted.

Build checkout records in a draft order, then set `placed_at` and status in the
same transaction. Deferred guards validate line sums/currency, exact per-line
copy totals, both tag types for each new pair and a private shipping snapshot.
After placement, order price/customer/contact/line/QR-use snapshots cannot be
rewritten, including after cancellation. Account addresses remain editable;
dispatch must read `order_shipping_snapshots`, never the live source address.
Money uses Decimal/numeric(12,2); tag sizes use numeric(7,2). Copy quantity
does not create identities or determine the number of owned pairs.

Only one live reserved/allocated claim per pair is allowed by a partial unique
index. Parent locks serialize mutations. Submitted/under-review/verified/disputed
payments block release; allocated entitlements cannot be recycled or deleted.
Manual-bank verification requires a bank-confirmed, append-only review plus
matching amount/currency before deferred validation succeeds. A keyed normalized
bank-reference fingerprint must use a stable deduplication key across reviews;
key rotation/normalization policy and real bank reconciliation are service work.
Evidence metadata points only to the private bucket and never verifies payment.
Creating these DB records does not upload files or configure Storage policies.

Shipment membership requires a paid order and its allocated pairs. Packing and
dispatch require the latest physical QA approval and recorded packing actor/time.
Normal shipment-pair uniqueness preserves history; audited reshipments require
a separately approved model. Draft catalog and disabled existing-QR reuse are
safe defaults; no commercial prices, catalog products or future providers are
seeded. Approved pricing, digital-artwork versus physical QA policy, feature
flags, actor authorization, audit/outbox, retention, checkout/finance services
and broad concurrency tests remain their roadmap tasks. All new tables start
with RLS and no browser grants/policies. Run migration tests serially against
one development database; overlapping transactional DDL may hit the lock timeout.
`commerce_guards.sql` is the readable frozen source embedded in revision 0002.

Task 1.4 adds `0003_workflows_security`: finder messages, encrypted optional
location, notification outbox/attempts, append-only audit, idempotency, scan
contexts, activation intents, typed durable jobs, print jobs/private artifacts,
finance mirror state, retention holds and encrypted support cases. Ciphertext
columns require positive key versions; encryption, coordinate validation and
provider calls belong to the later service tasks. No provisional retention
duration is enabled. A finder-message commit must include its matching durable
notification event. Ownership transfer never changes its recipient snapshot.
Forward revision `0004_runtime_privacy` further limits historical shipping
snapshots to the owner and fulfillment/security staff. Finance retains order
billing and settlement access, with no other customer's address/contact snapshot.

The revision creates `safereturn_api` and `safereturn_worker` NOLOGIN roles plus
separate `safereturn_api_login`/`safereturn_worker_login` roles without passwords.
All are non-superuser, non-bypass-RLS, non-creating roles. Browser roles receive
no table grants or membership. API RLS uses server-controlled subject/MFA context,
ownership joins and original message recipients; finance/operations/support
roles come from non-revoked `staff_roles`, not user-editable profile fields.
Ordinary API writes cannot assign pair ownership; reviewed atomic activation and
transfer procedures belong to Task 3.2/3.5. Staff provisioning also remains a
separate authorized operation, outside ordinary API table grants.

Runtime credentials are provisioned only after the migration is verified:

```powershell
.venv/Scripts/python.exe -m app.db.provision_runtime --env-file .env
```

This explicit development command requires a Git-ignored file, assigns initial
passwords only to the new login roles, verifies both real logins and role
separation, and stores secrets without printing them. It preserves the previous
privileged URL as `SAFERETURN_MIGRATION_DATABASE_URL` and test URL unchanged,
then switches `SAFERETURN_DATABASE_URL` to the restricted API login. The worker
uses `SAFERETURN_WORKER_DATABASE_URL`. Saved API provisioning configuration uses
`SAFERETURN_API_DATABASE_URL`; no URL belongs in Git or browser code. Alembic
explicitly prefers the migration URL. For the shared Supabase pooler, the command
preserves the inspected project suffix in the custom-role username, following
[Supabase's custom-role connection guidance](https://supabase.com/docs/guides/troubleshooting/tenant-or-user-not-found).
Do not rerun to rotate credentials: an interrupted/partial setup needs deliberate
recovery; an already-provisioned setup verifies existing credentials.

Business services must use `app.db.runtime.api_transaction()` **after** JWT,
ownership and MFA verification, supplying only server-derived UUIDs and verified
booleans. Public message creation supplies a freshly generated submission UUID;
scan continuation supplies a verified session-binding digest. The pending scan
context does not grant activation entitlement or prove the concealed credential.
Use `worker_transaction()` with the separate worker connection and an instance
ID. Context and role are local to the transaction and cleared on pool return.
The original `Database.transaction()` remains available for privileged migrations
and synthetic tests; an unscoped runtime login has no business-table privileges.
JWT verification/request dependency integration is Task 2.1, not implemented here.

Worker grants permit claims/retries/acks and immutable production projections
only for claimed order jobs. Financial reads expose selected settlement metadata,
never sender ciphertext. Workers cannot read Auth, shipping addresses, ICE,
activation verifiers or finder location; notification templates must use the
encrypted outbox snapshot or a later separately reviewed narrow projection.
Claims increment attempts and require due/reclaimable events; ack/failure needs
the worker's unexpired lease. Lease TTL/batch/backoff/provider idempotency and
typed external handlers remain Task 4.4/5.x. Durable processing is at least once.

Private print metadata requires paid allocation, immutable render configuration,
correct order/job references and an artifact before `ready`. Render configuration
and audit JSON are constrained metadata allowlists. Retention tombstones require
an explicitly approved due date and no resource/order hold; hold placement and
deletion lock the same resource. Holds are released with recorded identity and
kept as history. No Storage bucket, upload, deletion, email, Sheet write, print
rendering, automated allocation or retention period is activated by this schema.

Existing cross-table integrity triggers are hardened as fixed-search-path
definers so hidden RLS parents cannot skip the pair/order/payment/QA checks.
All table references are qualified; trigger functions and boolean policy helpers
are unavailable to browser RPC. Only the designated runtime roles can execute
their required context/policy helpers. Frozen SQL source snapshots are in
`workflow_guards.sql`, `runtime_helpers.sql` and `runtime_policies.sql`; previous
revisions are unchanged. Test migrations serially with rollback-only DDL/data and
run real-login checks after provisioning. A safe repeat upgrade is a no-op;
unknown role/table collisions require reconciliation, and destructive downgrade
is refused. Future cleanup/role changes need reviewed additive revisions.

Task 1.5 verifies the actual Alembic chain against development PostgreSQL in
UUID-named temporary domain/Auth schemas and four temporary NOLOGIN roles.
`tests/integration/pg_rehearsal.py` reads the installed revision, tables, RLS,
role flags, row counts and structural catalog before setup. The rehearsal
translates only schema/role identifiers at the driver boundary and disables
temporary login capability; it does not rewrite migration files, constraints,
triggers or policies. The Auth fixture models only the provider fields needed
by the migration chain. This
is a fresh namespace installation on the same PostgreSQL server, not a separate
Supabase project or a managed Auth migration. Its minimal Auth reference fixture
now also includes the account/session fields required by revision 0005.
Existing real-login tests exercise
the installed API/worker credentials separately.

The new verification module checks clean installation, populated 0001→0002→head
upgrades, exact catalog equality, failed transactional DDL and retry, deferred
COMMIT rejection, savepoint/client-close recovery, concurrent QR retirement and
replacement, last-pair reservations, paid allocation, and both outbox/job lease
claim/reclaim/ack fencing (including `FOR UPDATE SKIP LOCKED`). Races use separate
backend sessions, synchronized starts, bounded timeouts and committed-state
assertions. Synthetic rows commit only inside the temporary schemas.

Run serially from `backend`, explicitly loading the ignored environment:

```powershell
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe tests/integration/pg_rehearsal.py
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m pytest -q tests/integration/test_postgres_verification.py -p no:cacheprovider -W error
```

Cleanup verifies that each fresh schema is owned by the setup user, removes only
the generated namespaces and their temporary roles, then asserts the installed
metadata/catalog/row counts are unchanged and the generated objects are absent.
No installed domain/Auth rows or runtime passwords are changed. If a process is
forcibly terminated before teardown, inspect its exact `sr15_` UUID objects and
dependencies before any manual cleanup; never sweep namespaces by prefix. No
providers, feature services, production deployment or backup/restore claims are
part of this database verification.

Task 2.1 provides reusable protected-route dependencies in `app/api/auth.py`.
Account routes, signup/login screens and browser sessions remain Task 2.2; no
new public application endpoint is exposed by this task. Controllers use the
`Authenticated` dependency, whose API transaction commits or rolls back before
the response is sent. Use its session for the authorized operation, return only
the approved DTO, and call `require_pair_owner`, `require_qr_owner` (with the
requested purpose), `require_order_owner`, `require_payment_owner`, or
`require_message_recipient` before accessing an owner resource. Mutation services
must lock/revalidate their target and write within that same transaction.

Configure `SAFERETURN_SUPABASE_URL` as the project's HTTPS origin in ignored
`backend/.env`. The development origin was derived from the existing inspected
pooler project reference and its live ES256 public key endpoint was verified;
database passwords, login roles and privileged/runtime URLs were preserved.
No JWT secret or service-role API key is needed. `app/core/auth.py` uses PyJWT
with cryptography to verify ES256/P-256 or RS256/2048+ signatures against only
the configured `/auth/v1/.well-known/jwks.json` endpoint. Issuer, authenticated
audience/role, expiry, issue/not-before time, UUID subject/session, assurance and
access-token purpose are checked. Anonymous, service-role, refresh, unsigned,
malformed, wrong-signature and HS256 credentials fail closed; the inspected
project uses asymmetric keys. Legacy symmetric projects require a separately
reviewed verifier, never substitution of a publishable key as an HMAC secret.

JWKS requests have HTTP timeouts, no redirects/proxy inheritance, a 64 KiB/32-key
limit, one coalesced fetch and a five-second refresh cooldown. The cache defaults
to 60 seconds (`SAFERETURN_AUTH_JWKS_CACHE_SECONDS`, 5–600); expired keys are never
used during an outage. Unknown keys trigger a refresh when the cooldown permits,
then remain rejected if absent. Provider edge caching also affects key rotation;
follow [Supabase's signing-key guidance](https://supabase.com/docs/guides/auth/signing-keys).
The verifier/client is owned and disposed by application lifespan. It retains
public keys only, never access tokens or private user claims.

Additive `0005_account_session_guard` exposes only email-confirmed and current
session-assurance booleans for the transaction's verified actor and exact
session ID. Its pinned-search-path definer reads managed Auth metadata without
changing Auth tables or granting direct reads. Deleted/banned/anonymous accounts,
missing/mismatched/revoked sessions and elapsed `not_after` are denied on each
request. Database email confirmation gates ownership-sensitive actions. Staff
guards require confirmation, both signed `aal2` and current session `aal2`, and
an explicit non-revoked role read from `staff_roles`; custom JWT metadata cannot
grant staff access and superadmin is not an implicit bypass. Browser/worker roles
cannot execute the projection; API/worker logins still cannot read Auth tables.

Authorization errors use the documented bilingual envelope, server-generated
request IDs and `no-store`: 401 `AUTH_REQUIRED`, 403 `FORBIDDEN`, concealed 404
`NOT_FOUND`, and 503 `PROVIDER_UNAVAILABLE`. Readiness retains its separate probe
credential and liveness remains public. Current role/owner checks and RLS operate
together; do not treat a prechecked ID as authority in a later transaction.

Verification uses real cryptographic signatures with controlled JWKS fixtures,
signed JWTs through test-only ASGI routes against isolated real PostgreSQL,
actual restricted-login denial checks, a rollback-only migration rehearsal and
the live development public-key endpoint rejecting a foreign signature. Synthetic
Auth users/sessions stay inside the temporary reference schemas. A real user
signup/login token, provider-managed revocation/MFA lifecycle and cookie/CSRF
integration are verified separately from these Task 2.1 checks; see Task 2.2 below.

## Account API and live login verification (Task 2.2)

`GET /api/v1/me` (API-020) returns the own account resource directly: user UUID,
display name, preferred locale, live email-verification state, fully redacted
phone presence and opaque `version`. It never creates a profile on GET and never
returns Auth internals/tokens/ciphertext. Both account methods use the Task 2.1
signature/session dependency and restricted API transaction; responses are no-store.

`PATCH /api/v1/me` (API-021) accepts only optional `display_name` (trimmed,
1–120 characters or null to clear) and `preferred_locale` (`en`/`ur`). Invalid,
empty, unknown/privilege fields and unsafe bodies receive a safe 400 envelope.
JSON is capped at 2 KiB. Supply the current quoted ETag in `If-Match`; missing or
malformed versions receive 400 and stale versions 412. Version is opaque text
derived from the existing UTC `updated_at` with microsecond precision; `0`
represents a missing profile. Conditional insert/update and monotonically advanced
timestamps fence concurrent edits. An append-only minimal version audit commits
atomically with the edit. No additional migration or managed Auth writes are needed.
Phone changes, privacy consents and reviewed deletion remain later tasks.

Sixteen real PostgreSQL endpoint checks use signed JWTs and isolated rehearsal
namespaces: direct DTOs, own reads, committed edits, validation, cross-user denial,
concurrent initial saves/updates, one audit per winning edit, injected audit
failure rollback and connection recovery. Final result: 16 passed in 154.36s.

For live positive login verification, add `SAFERETURN_AUTH_TEST_EMAIL` and
`SAFERETURN_AUTH_TEST_PASSWORD` for a dedicated email-confirmed development user
to ignored backend/.env (never chat/source), then run from backend:

```powershell
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe auth_live_login.py
```

The helper first inspects the installed revision, then creates only a managed
provider test session, verifies real signed identity and restricted `/me`, refreshes
and locally revokes that new session, and checks API denial after revocation. It
does not create users, send email, edit domain rows or revoke unrelated sessions.
Credentials/provider bodies are never printed. The live login, signed identity,
restricted account API, refresh and local-session revocation checks passed with
the supplied confirmed development user. Positive live signup/email delivery is
not claimed from SDK fixture tests. The supplied publishable key was accepted by
read-only real provider settings; signup enabled and email auto-confirm disabled.

## Paired inventory generation (Task 3.1)

`POST /api/v1/admin/qr-batches` requires an authenticated, email-confirmed
operations account with current MFA and an `Idempotency-Key`. The request fixes
the batch label, pair count, template, ECC, print material, intended indoor or
outdoor use, and full QR symbol sizes (minimum 30 mm indoors, 35 mm outdoors).
Generation creates one current Lost QR and one current
ICE QR per pair in a single database transaction. Public tokens are independent
CSPRNG values; activation credentials use a dedicated versioned HMAC verifier.
The response contains batch metadata and a sealed insert encrypted to the
configured printer RSA public key. Plaintext credentials and private printer
keys never enter the database, routine logs, or browser configuration.
Identical retries replay only the same ciphertext.

Set `SAFERETURN_ACTIVATION_VERIFIER_KEY` to a dedicated base64url-encoded
32-byte key and configure its version. Set
`SAFERETURN_PRINT_RECIPIENT_PUBLIC_KEY` to the printer-held RSA public key
(3072 bits or stronger). Keep the matching private key outside SafeReturn and
provide it only to the authorized production printer. Generation fails closed
if either key is missing or invalid. Back up and rotate the verifier key by
version; never reuse a JWT, database, or web-session key for activation HMACs.

## Anonymous QR projections and bilingual scan pages (Task 4.1)

`GET /api/v1/public/qr/{token}` returns the allowlisted public projection for
the current QR identity. Unknown tokens return a non-disclosing 404. Inactive
or revoked tokens return only their safe status and locale options. Active Lost
responses contain only published item fields; active ICE responses contain
published display fields and contact labels, never phone numbers, medical
ciphertext, owner identifiers or activation secrets. The projection is exposed
through a security-definer database function so anonymous reads do not weaken
owner-only RLS policies.

The Next.js `/q/{token}` page renders active, inactive, invalid and unavailable
states in English or Urdu with RTL support and a visible language switch. Finder messages, protected contact reveals, WhatsApp and location sharing are
implemented as separate explicit actions.

## Protected ICE reveal and opt-in WhatsApp (Task 4.2)

`POST /api/v1/public/qr/{token}/contact-reveals` accepts a published ICE
contact ID and returns the decrypted phone only after the server confirms the
current active ICE QR, published profile, published contact membership and
rate-limit decision. The phone is absent from the initial QR projection and
the response is non-cacheable by the existing API transaction boundary.

`POST /api/v1/public/qr/{token}/whatsapp-link` requires the explicit
`open_chat` intent and an owner-enabled, consented Lost preference. It returns
an encoded `wa.me` link and disclosure text; it does not redirect, send a
WhatsApp message, create a finder message or claim delivery. Both endpoints
use generic unavailable/rate-limited errors and do not log returned phone
numbers or URLs.

## Finder messages and optional location (Task 4.3)

`POST /api/v1/public/qr/{token}/finder-messages` accepts a bounded finder
message and at least one validated email or E.164 phone contact. Contact
details and the message are encrypted before persistence. A one-time browser
location may be included only after explicit finder consent; coordinates are
validated and stored in the privacy-isolated location table.

The message, optional location, and `finder_message.created` notification
outbox event are inserted in one database transaction. The request never calls
an email provider, exposes the owner identity, or claims delivery. The public
page provides bilingual submission controls and optional browser geolocation.

## Durable notification worker and mobile privacy checks (Task 4.4)

`app.workers.notifications.process_one` handles only finder notification events.
A short worker-role transaction claims a due event with `FOR UPDATE SKIP LOCKED`,
records its numbered attempt, resolves the original recipient's verified account
through a lease-scoped function, and freezes an AES-GCM encrypted email snapshot.
The claim commits before Resend is called. Finder content, contact details,
coordinates, QR tokens and medical information are excluded from the generic mail.

Completion checks the current worker, attempt number and unexpired lease in a
second transaction. Expired claims can be reclaimed; late acknowledgements cannot
finish a newer claim even when worker IDs are reused. A stable provider
idempotency key and frozen recipient preserve the request across crash recovery.
`sent` records provider acceptance, not delivery to an inbox or an owner read.

Transient errors use capped exponential backoff with jitter and bounded
`Retry-After`; permanent failures and exhausted attempts become `dead`.
Concurrent Resend idempotency requests retry; a changed-payload conflict does not.
Ambiguous sends older than 23 hours stop for manual review, within
[Resend's 24-hour idempotency window](https://resend.com/docs/dashboard/emails/idempotency-keys).
Do not automatically replay old ambiguous events with a fresh key.

Migration `0014a_notification_delivery` follows applied revision 0014. It adds only
the worker-only leased recipient helper and scoped snapshot/parent-lock fixes.
It grants no direct Auth-table access and changes no domain tables. The still
unapplied catalog revision 0015 now follows it; never upgrade to head for this task.

Run a worker with a separately provisioned worker-only environment:

```powershell
.venv/Scripts/python.exe -m app.workers.notifications --env-file .env.worker --once
.venv/Scripts/python.exe -m app.workers.notifications --env-file .env.worker
```

`--once` processes at most one due finder event. The continuous command polls
when idle. Required runtime settings are `SAFERETURN_WORKER_DATABASE_URL`,
`SAFERETURN_RESEND_API_KEY`, `SAFERETURN_NOTIFICATION_FROM_EMAIL` and the existing
profile keyring. It never falls back to an API/migration login. Lease duration must
exceed the HTTP timeout by five seconds. Keep migration credentials out of the
deployed worker environment; neither a public frontend key nor a Supabase browser
session supplies worker access.

After building the frontend, explicitly load the authorized development test URL:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_notification_delivery.py -q
```

Before applying 0014a at installed 0014, set
`SAFERETURN_NOTIFICATION_BASE_REVISION=0014_public_finder_messages`.
The suite uses owned disposable schemas, synthetic recipients, mock provider
calls, real lease contention and local browser checks. A separate
`test_notification_live.py` is skipped unless both an explicitly authorized
`SAFERETURN_NOTIFICATION_SMOKE_RECIPIENT` and stable
`SAFERETURN_NOTIFICATION_SMOKE_KEY` are injected. Never supply a real recipient
to ordinary automated tests.

The finder form explains optional one-time location, remains usable after denied
permission, preserves fields after failure, supports keyboard/RTL phone layouts,
and states that a saved message does not guarantee an email notification.

## Catalog and featured storefront (Task 5.1)

Migration `0015_public_catalog` adds the explicit `safereturn_api` projection
used by anonymous `GET /api/v1/public/products` and
`GET /api/v1/public/products/{sku}`. It returns only published products,
active variants, and approved Cloudinary image metadata; unknown or inactive
SKUs return 404. Operations staff with a verified account and MFA can create
categories via `/api/v1/admin/catalog/categories` and manage products/variants/images
via canonical API-220–229 `/api/v1/admin/products*` routes. See Task 5.1 verification
and configuration details below. The homepage renders the published
featured products server-side when the API is configured.

## Decimal checkout quotes (Task 5.2)

`POST /api/v1/me/checkout/quotes` validates every QR copy count against its
line quantity and stores server-side product, variant, price, and template
snapshots for 15 minutes. `POST
/api/v1/me/checkout/quotes/{quote_id}/confirm` locks the quote, encrypts the
shipping address, creates immutable order snapshots, and reserves exclusive
QA-passed new pairs with `FOR UPDATE SKIP LOCKED`; existing QR reuse is
validated against the authenticated owner. Money remains Decimal/NUMERIC
throughout and expired or already-confirmed quotes cannot be reused.

## Payment evidence and finance review (Task 5.3)

Payment APIs use the existing immutable commerce tables and fail closed around
private storage. Customers can create idempotent `manual_bank` attempts only
for their own placed order, receive a bounded private-evidence upload
authorization, finalize validated evidence metadata, and list their attempts.
Finance staff with verified MFA can append a bank-verified review. Verification
requires an independent bank reference and exact Decimal amount/currency
matching; the database's deferred guards prevent an invalid manual attempt or
order from becoming verified. Successful review updates the order once and
allocates its reserved pair units under the same transaction.

## Private print jobs, downloads, and physical QA (Task 5.4)

Operations staff can enqueue one idempotent `print.render` job for a verified
paid order, inspect its status, and issue a five-minute token grant only for a
retained private PDF/SVG artifact. Render configuration is encrypted in the
durable job payload; raw activation secrets are never reconstructed or returned
by these endpoints. The print-QA endpoint records the required Lost/ICE scan,
pair-match, concealment, bilingual-label, quiet-zone, physical-size,
packaging, and tamper checks, and only promotes a pair to `qa_passed` when all
checks pass.

## Orders, copies, and fulfillment (Task 5.5)

Customers can view their own paginated orders, immutable line/copy snapshots,
reserved pair units, and sanitized shipment status. Operations staff can view
verified-paid allocated orders ready to ship, create shipments from the stored
shipping address reference, and advance shipment metadata without exposing
customer address ciphertext or finance notes. Shipment transitions remain
subject to the existing database payment, allocation, and print-QA guards.

## Finance mirror and private retention (Task 5.6)

Finance Sheet synchronization is asynchronous and treats the database as the
source of truth. The worker upserts by stable order ID, increments a monotonic
export version, and sends only masked payment status/amount metadata; sender
accounts, raw profile data, and evidence links are never projected. Finance can
inspect sync status and enqueue a retry without editing payment state.

Operations and security staff receive metadata-only private-artifact inventory.
Retention holds are reasoned and audited, and cleanup removes the private
object before recording its deletion tombstone. Expired artifacts are skipped
when an active hold exists; provider failures leave durable retry state intact.

## Finder inbox and customer support screens (Task 5.7)

Finder messages are recipient-scoped to the original owner, with summaries that
omit decrypted contact/location data. Authorized detail reads decrypt the
message and consented location only for that owner. Status changes are limited
to viewed, archived, and flagged; deletion is a soft delete so retention and
legal-hold policy can be applied without exposing exceptions.

The customer shell includes bilingual inbox, account settings, and help
surfaces. These pages do not expose finder data until the protected API
confirms the authenticated recipient.

## Critical workflows and recovery checks (Task 6.1)

The rollback-only PostgreSQL acceptance suite now rehearses the critical
customer-to-fulfillment path: placed order, verified payment and allocation,
private print artifact readiness, physical QA, packing, and dispatch. It also
proves that a failed print write does not release verified allocation and that
provider retry state and active retention holds survive an outage. These checks
use synthetic records inside nested transactions and do not alter persistent
development data.

## Scan intent and atomic activation (Task 3.2)

API-207 `GET /api/v1/public/qr/{token}/activation-context` returns only the
unactivated purpose/availability and 900-second UX TTL. It grants no ownership.
API-208 `POST /api/v1/me/tag-pairs/activation-intents` accepts `scanned_token`
and optional `activation_secret`, and requires a live, email-confirmed account.
It creates a 15-minute actor-bound intent using verified paid allocation or a
separate concealed credential. Concealed credentials cannot bypass any live
reservation/allocation. Only eligible inventory with two current unactivated
children is accepted. No legacy Pair-ID-only claim endpoint is enabled.
Third-party claims against an already allocated purchase remain gated by the
security review in PRD12-DEC-04; possession of a gift credential does not override
the existing purchaser allocation. Offline/unallocated concealed claims work.

API-032 `POST /api/v1/me/tag-pairs/activations` requires `intent_id`, explicit
`confirm: true`, and `Idempotency-Key`. Restricted definer procedures recheck
eligibility/entitlement and atomically consume intent/credential, assign owner,
activate both QRs, and insert audit/outbox/idempotency records. Profile publication
and consent are unchanged. Same actor/key/body replays the original decision;
changed bodies conflict. Failed transactions can retry the same key. Intent
creation records failed attempts in its own committed command, before the later
confirmation transaction; an activation failure cannot erase lockout accounting.

Limits are durable across API processes: 20 intent attempts/account/15 minutes,
100 scan/intent requests/direct peer/15 minutes, and five failed proofs lock a
credential for 15 minutes. Forwarded IP headers are deliberately untrusted;
deployment proxy/IP policy belongs to the release configuration. Validation is
bounded to 4 KiB and never echoes raw input. Verifiers use the dedicated versioned
HMAC key and a fixed-length constant-time comparison; missing/historical keys
fail closed without charging a failed proof. Browser auth-return continuation is
Task 3.4; these bearer APIs never auto-activate from a GET or scan.

Forward revisions 0008/0009 add only procedures and tighten runtime intent INSERT
permissions; previous revisions and runtime credentials remain intact. Run the
focused real PostgreSQL checks with explicitly loaded development test settings:

```powershell
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_activation.py tests/integration/test_runtime_logins.py -q
```

Endpoint fixtures use UUID-isolated synthetic namespaces and NOLOGIN roles;
runtime-login checks use the real restricted API/worker credentials. Existing
domain/Auth records are never used as endpoint fixtures or changed.

## Independent QR profiles and consent (Task 3.3)

API-040–049 implement owner-only Lost/ICE profile reads/updates, masked ICE
contacts, and opt-in WhatsApp preferences under `/api/v1/me/qr/{qr_id}`. Writes
require a verified account and quoted `If-Match` ETag. Missing resources read as
unpublished defaults with version `0`; GET creates no rows. PUT preserves omitted
fields and clears nullable values only when explicitly submitted. Each profile
has an independent integer version; contacts share their ICE profile's version,
while WhatsApp preferences have a separate version. Contact POST/PATCH return a
masked contact and updated collection version; DELETE unpublishes and soft-removes
the contact, retaining encrypted history. At most three non-removed ICE contacts
are supported. Other QR identities, pairs, and printed copies are untouched.

Publishing ICE requires `publication_consent_accepted: true` and
`publication_consent_version: "ice-public-v1"`. Published medical notes additionally
require a signed provider authentication event within five minutes. A refreshed
JWT `iat` alone does not qualify. Contacts use `ice-contact-v1`; WhatsApp uses
`public_disclosure_consent: true` and `consent_version: "wa-public-v1"`. Edits to
published sensitive data require renewed consent. Disabling publication remains
available without encryption keys. Medical write responses indicate
`medical_notes_redacted: true` if retained notes cannot be decrypted; contact
write responses may return `phone_masked: null` in that case. Editors must retain
these existing secrets rather than treating redaction as an instruction to clear.

Configure **a new server-only secret**, `SAFERETURN_PROFILE_DATA_KEYS`, as a JSON
mapping from version strings to base64url-encoded independent random 32-byte keys,
and set `SAFERETURN_PROFILE_DATA_KEY_VERSION=1` initially. Keep previous versions
for reads during rotation. Keys must not reuse database/auth/session/activation or
printer secrets. Runtime defaults are intentionally unset: new sensitive writes
and protected decryption fail with safe 503 responses until configured. Tests
inject ephemeral dummy keys only into isolated applications; no real `.env` key
is generated or overwritten. No new external provider API key is needed.

Medical notes and phones use AES-256-GCM with fresh 96-bit nonces and authenticated
QR/field/contact/key-version binding. Phone reads are masked; medical plaintext is
available only in the authenticated owner representation. Responses are no-store,
validation is capped at 16 KiB without echoed input, and audit records store only
actor/object/version/publication states and accepted consent identifiers. Consent
timestamps come from PostgreSQL. A narrow API-only definer locks the owner pair
and current QR without granting customers inventory UPDATE privileges.

Forward revisions `0010_profile_consent` and `0011_profile_owner_locks` add only
nullable consent/removal fields, preference versions and a restricted locking
function. Earlier revisions, existing rows and runtime credentials are preserved.
Focused verification:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/test_profile_crypto.py -q
.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_profiles.py tests/integration/test_runtime_logins.py -q
```

No public reveal/WhatsApp link endpoint or external message sending is included;
public privacy projections/reveal remain Phase 4.

Task 3.4 adds owner-only `GET /me/tag-pairs`, `/me/tag-pairs/{pair_id}`,
`/me/qr` and `/me/qr/{qr_id}` (API-030/031/205/206). Collections use bounded
cursor pages with timestamp/UUID ordering; QR search, purpose, pair, public-status
and publication filters execute inside the authenticated owner scope. Summaries
exclude medical notes, phones, ciphertext and activation material. Detail links
to the exact current QR and includes only the caller's linked order-product
snapshots/copy counts, never another purchaser's order data. No migration or
runtime-grant change is required.

For isolated real PostgreSQL/browser acceptance, build the frontend, then load
only the development test/runtime database URLs explicitly and run:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_owner_qr.py tests/integration/test_qr_browser.py -q -s
```

The browser controller uses installed Edge, synthetic signed identities in UUID
rehearsal schemas, and a simulated Auth provider. It starts only its own local
8115/3100 runtimes, excludes database/encryption credentials from Next, blocks
external web fetches, and stops those runtimes in cleanup. It does not prove
live Supabase confirmation/recovery or email delivery and never sends email.

Task 3.5 adds `tests/integration/test_phase3_integrity.py`: foreign-customer and
staff mutation denial with unchanged-state snapshots, wrong-purpose/contact-ID
isolation, encrypted profile/contact/preference audit rollback, synchronized
version/contact-limit/independent-profile races, actor-scoped activation replay,
child/audit/deferred-COMMIT activation rollback, and real lock waits against
synthetic disputes or QR retirement. The race barrier runs at the protected SQL
command on distinct server-reported PostgreSQL process IDs; connections are
established before contention, and administrative interleavings verify actual
`pg_blocking_pids` before releasing the fixture transaction. Every wait is bounded.

Pair detail now returns a concealed 404 if ownership is revoked between its
guard and representation read. No schema, grant, credential, public projection
or ownership-transition rule changes. Fault hooks and administrative mutations
are confined to UUID rehearsal namespaces; installed metadata/data are checked
before setup and after cleanup. No new provider credential is required.

With only the development test/API/worker URLs explicitly loaded from ignored
configuration, run the Phase 3 PostgreSQL regression slice from `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_phase3_integrity.py tests/integration/test_inventory_generation.py tests/integration/test_activation.py tests/integration/test_profiles.py tests/integration/test_owner_qr.py tests/integration/test_runtime_logins.py -q
```

### Task 4.1 public projection verification

API-010 uses the API-only fixed-search-path projection from revision
`0012_public_qr_projection`. It returns only published per-tag allowlists,
minimal unavailable states and no initial phone/ciphertext/private identifiers.
Medical notes remain null under the approved API-010 DTO. Missing profiles are
safe empty states. The dedicated public-scan budget counts unknown/invalid
lookups separately from activation (100 requests per direct peer / 15 minutes);
only a SHA-256 peer digest and minimal outcome are stored in audit. Untrusted
forwarded headers are ignored. Trusted proxy/IP policy remains a release gate.
No-store, no-referrer and noindex headers protect successful public responses.

After explicitly loading the development `SAFERETURN_TEST_DATABASE_URL`, run
from `backend` after building the frontend:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_public_qr.py -q
```

This targets **only 0012**, including a real transactional DDL rollback/retry.
Its default installed-head expectation is 0012; for the pre-application rehearsal
at 0011, explicitly set `SAFERETURN_PUBLIC_QR_BASE_REVISION=0011_profile_owner_locks`.
The rehearsal helper's optional expected revision does not loosen metadata or
cleanup checks. It preserves installed catalog, row counts and runtime roles;
all synthetic rows/rate events live in owned UUID namespaces.
The final case starts isolated Next/API runtimes on 3100/8115 and runs
`frontend/tests/public-qr.spec.ts` against real PostgreSQL. No Auth, Resend,
contact reveal, WhatsApp, finder submission or other provider acceptance is
claimed by this task. Later unapplied migrations, including 0014's replacement
projection, must be re-reviewed against these invariants before application.

### Task 4.2 protected contact actions

`public_contacts.py` owns API-012/013; `public_actions.py` composes that router
while preserving the separate, unverified Task 4.3 finder implementation.
Revision `0013_public_contact_actions` supplies API-only ciphertext/QR-context
projections with publication, current-tag, consent-version and membership checks
under row locks. It also updates API-010's WhatsApp availability without changing
any applied revision or exposing phone data on the initial scan.

Every deliberate contact action requires server-verified Turnstile. Verification
uses the fixed HTTPS Siteverify endpoint, bounded timeout, no redirects, and
checks success, hostname, action, hashed QR/contact cData and token age. No raw
IP, QR token or phone is sent in that validation request. A committed SHA-256
proof digest prevents replay across concurrent application requests. Provider
verification happens without a database transaction or row lock held.

Independent committed attempt budgets are 20 per direct peer, 10 per peer/QR,
and 5 per peer/QR/contact (or WhatsApp action), per 15 minutes. Denied requests
and provider/key outages consume attempts; changing QR tokens or spoofing
forwarded headers does not reset the peer budget. Only digests and minimal
outcomes are stored in append-only audit. No activation budget, finder message
or notification outbox is used. Proxy aggregation/trusted peer forwarding remains
a release configuration gate, not a reason to trust arbitrary public headers.

Missing/invalid challenge yields CHALLENGE_REQUIRED; configuration/provider/key
outage fails closed with a safe unavailable state. Public emergency information
remains anonymous and readable. **No emergency outage bypass is enabled:**
Security specification section 8.4 reserves fallback thresholds/expiry for founder
approval. Live widget/provider acceptance and production host/proxy configuration
remain release gates; controlled provider/browser tests are not a live-provider claim.

Required runtime configuration (no real values are written by this task):

- Backend ignored `.env`: `SAFERETURN_TURNSTILE_SECRET_KEY` and
  `SAFERETURN_TURNSTILE_EXPECTED_HOSTNAME` (hostname only, without scheme/port).
- Frontend ignored environment: `NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY` (public widget key).
- Existing profile encryption keyring remains separate; no Resend or Meta API
  credential is needed for contact reveal or click-to-chat.

Widget loads only after a click, uses the compact dimensions and provider-supported
language selection, and refreshes after each failed attempt. WhatsApp shows a
second explicit external link with noopener/noreferrer; it never auto-redirects.
The application's surrounding disclosure/error/critical instructions are English/Urdu.

Provider references: [server validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/),
[widget configuration](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/),
and [supported languages](https://developers.cloudflare.com/turnstile/reference/supported-languages/).

After frontend build and explicitly loading the development test/API/worker URLs,
run the scoped suite from `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_public_contacts.py tests/integration/test_runtime_logins.py -q
```

The contact suite defaults to installed head 0013 and rehearses only through 0013.
Before application at 0012, set `SAFERETURN_CONTACT_BASE_REVISION=0012_public_qr_projection`.
It verifies DDL rollback/retry, encrypted synthetic contacts, consent, attempt
persistence, replay races, real lock-wait revocation and local browser action flows.
Siteverify and widget delivery are simulated; real Next/API/PostgreSQL are used.
For the standalone Task 4.1 regression at installed 0013, explicitly set
`SAFERETURN_PUBLIC_QR_BASE_REVISION=0013_public_contact_actions`; its rehearsal
continues to target 0012. Later migrations stay unapplied and must be reviewed
against the 4.1/4.2 privacy protections before application.

### Finder Submission (Task 4.3)

`POST /api/v1/public/qr/{token}/messages` (API-011) and the existing
`/finder-messages` compatibility route accept explicit contact consent, a
10-1,000 character message, a valid email or ASCII E.164 phone, and optional
consented location. Documented `contact_consent_version=finder-v1` and nested
location consent fields are supported alongside the existing finder form fields.
Denied or withdrawn browser location consent does not prevent sending a message.

Submissions require a server-verified `finder_message` Turnstile proof bound to
the scanned token. Proof digests prevent reuse, and failed verification consumes
a committed finder budget independent of activation and protected contacts.
The browser generates an `Idempotency-Key` retained for unchanged retries;
changed content under the same key returns 409. Message, encrypted location,
idempotency record and minimal notification outbox entry commit together.
202 means accepted, without promising email delivery or an owner response.

Migration `0014_public_finder_messages` preserves the previous ICE/WhatsApp
projection protections and enables finder/location flags only for published Lost
profiles. Rehearse this exact revision before applying it; do not upgrade to head.
Tests use synthetic data in isolated schemas and simulated challenge responses:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/integration/test_finder_submission.py -q
```

Explicitly load the authorized development `SAFERETURN_TEST_DATABASE_URL` first.
Build the frontend before the browser wrapper. Runtime Turnstile settings use the
same backend keys and `NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY` as Task 4.2.
Presence of these values does not establish live provider acceptance.

Development acceptance on 2026-10-16: 12 integration checks (including the browser
wrapper), 3 browser checks, 14 restricted-login checks and 146 local tests passed.
Only revision 0014 was applied; existing tables, roles and three domain rows were
preserved. The finder suite defaults to installed revision 0014; before applying
it at 0013, set `SAFERETURN_FINDER_BASE_REVISION=0013_public_contact_actions`.
Email delivery/worker acceptance was subsequently verified in Task 4.4.

Task 4.4 development acceptance (2026-10-16): 17 integration checks across focused
runs, 6 final browser checks, 16 restricted-login checks and 159 local tests passed;
production build/typecheck, focused Ruff/format, pip and diff checks passed. One
explicitly authorized synthetic Resend email was accepted and the user confirmed
receipt. Do not repeat that live smoke without new authorization. No continuous
worker was started. Only 0014a was applied, preserving 40 RLS tables, three original
domain rows, roles and unrelated functions. Later migrations remain unapplied.
Live Turnstile and security/production/physical release acceptance remain separate
gates; this is development verification, not production readiness.


### Catalog verification (Task 5.1)

Canonical API-200–202 and API-220–229 now cover published featured/category/variant
reads and catalog administration. The old Copilot API-110–113 routes were not the
approved contract and were replaced. Operations + verified MFA is the existing
explicit delegated catalog permission; security_admin/superadmin are also checked.
No new role or role grants are provisioned. A separate catalog role remains a
future authorization decision.

Create products as drafts. All mutations require Idempotency-Key; updates and
child/image writes also require quoted If-Match catalog_version (parent version
for creating children/unlinking images; variant version for variant edits).
Retry receipts are encrypted in existing idempotency_records; audit remains minimal
and append-only. Product/variant history snapshots are never rewritten. Requests
and storefront reads are no-store, so publication changes need no stale-cache purge.
PATCH accepts the complete editable form; omitted fields take documented defaults.

Only the active `qr-stickers` category with active PDF-label variants, PKR prices,
QR-symbol size >=30 mm and approved `template_key@version` configuration can be
published. `size_mm` means symbol including quiet zone, not outer branded wrapper.
`SAFERETURN_CATALOG_APPROVED_TEMPLATES` defaults to `[]`: publishing is blocked until
founder/physical template approval. This positivity/minimum check does not establish
physical scan QA. Future categories, manual/manufacturer fulfillment and QR reuse
remain unavailable publicly. No sample products/prices are seeded into development.

Public media attachment uses existing approved assets: server verifies resource
metadata through the fixed Cloudinary Admin API, controlled public folder, upload
image type and raster format. Only the verified versioned delivery URL is persisted.
Configure server-only SAFERETURN_CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET and optional
PUBLIC_FOLDER (default safereturn/catalog/). Without them attachment fails closed.
Private proofs, QR customer print files, authenticated assets and SVG/raw uploads
are rejected. Unlink removes only product association; no provider delete is called.
Signed direct-browser upload is supported by API-225 with `?authorize_upload=true`:
operations/MFA plus parent If-Match authorize a generated folder/product/UUID public ID,
non-overwriting raster upload and encrypted idempotent signature receipt. Browser posts
the signed form directly to the fixed provider endpoint, then calls normal API-225 to
verify resource metadata before attaching. Provider failure never creates an image row;
a successful upload with failed attachment retains the public ID for retry. No remote
cleanup/delete is automatic. Configure a signed SAFERETURN_CLOUDINARY_UPLOAD_PRESET
for permitted raster formats and public product-media policy; the app enforces 5 MB before attachment;
without that preset authorization fails closed. Cloudinary signatures expire after one
hour; the API secret never leaves the backend. Real account/preset/upload acceptance
remains unverified. Controlled acceptance uses simulated provider replies.
See [Cloudinary signature protocol](https://cloudinary.com/documentation/authentication_signatures)
and [signed uploads](https://cloudinary.com/documentation/upload_images).

`/admin/products` provides authenticated draft/category/variant/media forms and
versioned edit/archive controls; FastAPI enforces staff/MFA independently. `/shop`
has URL-backed search/category filtering, SKU details, and safe empty/outage states.
The featured homepage is manual, keyboard/RTL accessible and reads API-201.

Build frontend, explicitly load the development test DB URL, then run
`pytest tests/integration/test_catalog.py -q -s -p no:cacheprovider`.
Before application its base is 0014a; after application set
`SAFERETURN_CATALOG_BASE_REVISION=0015_public_catalog`. Rehearsal creates isolated
UUID schemas/nonlogin roles, checks migration rollback/retry, and verifies installed
metadata/data preservation on teardown. Apply only `0015_public_catalog` using the
reviewed `tests/integration/apply_catalog_migration.py`; never upgrade to head for
this task. Migrations 0016–0017 and checkout Task 5.2 remain outside this scope.

Task 5.1 final development evidence (2026-10-16): coherent **11 integration checks
PASS (273.23s)**, including migration rollback/retry, concurrency, historical order
preservation and the browser wrapper; **all 9 browser checks PASS (1.2m)** with
synthetic Auth/Cloudinary; **174 local tests PASS (8.65s)**; **18 actual restricted-login
checks PASS (49.65s)**. Final production build/typecheck, scoped Ruff/format, pip and
diff checks pass. Only 0015 installed, preserving 40 RLS tables, three original row
contents, roles, indexes/triggers and unrelated functions. No live provider upload,
email, Auth/customer data change, worker daemon or production action. Real Cloudinary
account/preset/upload and founder SKU/template/physical/Turnstile/release gates remain.
Task 5.2 has not been started; 0016–0017 remain unapplied.


### Task 5.2 checkout verification

API-203 accepts a bounded new-pair cart, inline private `address` and explicit
`contact_phone_confirmation`. Inline address entry is the implemented extension;
saved-address management is deferred (unsupported fields fail closed). Address JSON
is encrypted with quote-specific AAD; only city and masked phone appear in receipts.
API-204 accepts exactly `accept_total` (two-decimal string) and `accept_currency=PKR`.
Legacy API-060 `POST /me/orders` rejects with 409 QUOTE_REQUIRED; there is no
competing order creation path. Both writes require Idempotency-Key. Same actor/key/body returns the encrypted saved
receipt; changed content returns 409. Confirm retries return the same order even
after the quote is consumed. Anonymous/cross-owner reads and confirmation are denied.

Enable only with SAFERETURN_CHECKOUT_ENABLED=true plus explicitly approved
CHECKOUT_SHIPPING_PKR, CHECKOUT_TAX_PKR and CATALOG_APPROVED_TEMPLATES settings.
Defaults disable checkout; no assumed free shipping/tax or sample retail data is
installed. Totals use Decimal/NUMERIC; discount is zero because coupons are disabled.
Quote lifetime is 15 minutes; reservation defaults to 30 minutes (configurable 5–120).
Unexpired quotes retain quoted prices, sizes, names and template versions after a
catalog price edit; publication, permitted template and current identity policy are
rechecked. A withdrawn template/category/product cannot be newly confirmed.

P0 supports one explicit new-pair group per checkout, with at least one Lost and
one ICE copy; quantities do not mint identities. Additional sizes/lines share the
same full pair. Future multiple groups, non-sticker products and reuse are disabled.
Future reuse authorization exists behind CHECKOUT_EXISTING_QR_REUSE_ENABLED=false;
when enabled in isolated tests it checks owner/current identity/tag/public status at
quote and confirmation, with final trigger locks/rechecks before commit.

Only migration 0016_checkout_quotes belongs to this task. It adds owner quote RLS,
immutable encrypted snapshots and API-only narrow catalog/capacity/reserve helpers.
Catalog helpers lock product→variant→category; reservation uses FOR UPDATE SKIP LOCKED
and existing exclusive live reservation constraints. Orders are built as drafts,
then immutable line/use/shipping snapshots, then placed. Deferred constraints run
before receipt completion. Crypto/stock/constraint failures roll back order, address,
reservation, quote change, audit and receipt together. Existing payment/reconciliation
hold guards are preserved; checkout never auto-recycles an expired reservation.
Only the separate verified-payment flow can allocate ownership; this task neither
verifies payment nor sends email or starts a notification worker.

Run `tests/integration/test_checkout.py` against explicitly loaded development test
credentials. Its default installed base is 0015; after applying set
SAFERETURN_CHECKOUT_BASE_REVISION=0016_checkout_quotes. Build frontend before browser
checks. Rehearsal verifies DDL rollback/retry and exact installed structure/count
preservation using UUID namespaces and NOLOGIN roles. Apply only the rehearsed target
using `tests/integration/apply_checkout_migration.py`; never upgrade to head.

Cloudinary follow-up: the newly supplied account was reached and the missing named
preset was created signed-only with raster formats and safereturn/catalog asset folder.
Cloudinary did not retain max_file_size through this preset API, so no provider-side
5 MB enforcement is claimed. The browser rejects oversize files and server resource
metadata rejects >5 MB before attachment. No live image upload/delete was performed;
real upload acceptance remains a gate. Ignored env values were not modified; dotenv
reports an unparseable entry starting at line 12, left owner-managed without disclosure.

Task 5.2 development evidence (2026-10-16): 17 integration checks passed (417.69s),
all 7 final browser checks passed (1.3m), 192 local tests passed (8.34s), and 20 actual
restricted-login checks passed (70.31s). Final production build/typecheck, focused
Ruff/format, pip and diff checks pass. Applied only 0016: 41 RLS tables, no seeded
orders/quotes and full original row contents/roles/unrelated definitions preserved.
0017 remains unapplied. Checkout remains disabled pending approved cost/template
configuration. No email, payment, production deployment, commit or push.


### Task 5.3 payment verification scope (2026-10-16)

Payment API-210 derives amount/currency from the immutable placed order, encrypts sender account/holder/reference, and protects reservations immediately with `under_review`. API-209 exposes only masked owner-scoped history. API-211 requires filename, MIME, byte count (maximum 5 MB) and SHA-256; API-212 accepts an encrypted actor/attempt-bound upload token and SHA-256. The backend downloads and validates actual bytes before recording evidence. A finalized screenshot never verifies settlement.

API-240 (`GET /admin/orders/{order_id}/payment-attempts`) requires finance + MFA, decrypts restricted sender details and audits access. The additive retrieval route `GET /admin/payment-evidence/{evidence_id}` requires the same guard on every download, revalidates the private object's hash/size/signature, audits access and returns an attachment with no-store/nosniff. It never exposes a public URL. Raw bank references are excluded from receipts/audits; a stable keyed HMAC enforces settlement deduplication.

API-241 requires idempotency, reason and, for verification, `bank_verified=true`, `bank_match_reference`, exact `settled_amount` (decimal string) and `settled_currency`. It locks order before attempt/reservations, rejects closed payments and unavailable/released reservations, and atomically appends review, verifies payment/order, allocates reserved pairs and enqueues one durable `finance.sync` event. Request-more-info retains review protection; rejection does not automatically release or recycle inventory. Same-key retries replay the encrypted receipt. No real settlement verification, email, print generation or worker execution is performed by acceptance tests.

Server-only configuration names: `SAFERETURN_SUPABASE_STORAGE_SERVICE_KEY` and `SAFERETURN_PAYMENT_REFERENCE_KEY` (stable high-entropy secret; changing it requires an explicit reconciliation/migration plan). Existing profile encryption keys are also required. Do not paste these keys into chat, expose them to Next/browser, or replace existing credentials. Bucket `private-payment-evidence` must already exist, private, with a maximum 5,000,000-byte upload limit and a nonempty allowlist limited to PNG/JPEG/PDF. No anonymous/authenticated direct object reads or mutations should be granted. Provision buckets through the Storage API/dashboard, never direct SQL writes to managed storage tables.

Supabase signed upload capability lifetime is **two hours**, while the application finalization token expires after **five minutes**; both durations are explicit in the API response. Reference: https://supabase.com/docs/reference/javascript/file-buckets-createsigneduploadurl . Unfinalized/orphan objects need the later retention policy. Signature/active-PDF checks are defense in depth, not a malware scanner; dedicated malware scanning and live provider ACL/overwrite/expiry/size acceptance remain release gates.

Customer `/payments/{orderId}` and `/admin/payments` use the authenticated same-origin relay `/payments/api`; POSTs require exact Origin and allowlisted paths. In-memory retry keys preserve lost-response retries without persisting payer details or capabilities in browser storage. Checkout links to payment submission. Reload resumes a pending attempt through API-209. Finance uses an order ID to load restricted details, then records an independently checked review. Complete bilingual finance/payer screen acceptance and approved bank instructions remain gated; no bank recipient/account values are invented.

Reproduce synthetic acceptance from `backend`, explicitly loading the ignored development `.env`: set `SAFERETURN_CHECKOUT_BASE_REVISION=0016_checkout_quotes`, then run `pytest tests/integration/test_payments.py -q -p no:cacheprovider`. The test fixture needs the existing test/migration URL, creates fresh UUID schemas and NOLOGIN roles, uses real PostgreSQL/constraints/RLS and signed synthetic JWTs, and cleans up only its own fixtures. Storage/Auth browser provider endpoints are simulated. Build frontend first; do not rebuild `.next` while the isolated browser server is running. Run local tests with `pytest tests --ignore=tests/integration -q -p no:cacheprovider` and actual restricted-login checks with `pytest tests/integration/test_runtime_logins.py -q -p no:cacheprovider`.

Migration review: 0017 contains only print-download grants and depends on 0016; Task 5.3 has no dependency on it. No installed migration or domain data change is necessary for these API fixes. Stop before Task 5.4.


Task 5.3 final acceptance: **9 integration checks PASS (400.70s), including 4/4 browser checks and opt-in live Storage acceptance; 205 local tests and 20 restricted-login checks PASS.** Set `SAFERETURN_PAYMENT_LIVE_STORAGE=1` explicitly to enable the live synthetic storage test; it uses only isolated PostgreSQL metadata and deletes only its freshly generated evidence object keys in `finally`. The user supplied server configuration and created the private bucket; its size limit was aligned through Storage API from 5 MiB to 5,000,000 bytes. Live upload/finalize/hash, duplicate overwrite/public/anonymous access denial, provider MIME/size enforcement and exact-key cleanup passed. No real payments or emails. The five-grant cap serializes concurrent authorization requests for one actor/attempt. Dedicated malware scanning and delayed-expiry/orphan retention remain release gates. Current app: http://localhost:3032 (API 8031); prior runtime processes preserved. Migration 0017 remains unapplied; stop before Task 5.4.


### Task 5.4 — private vector PDFs, fenced render jobs and physical QA

`0017_print_download_grants` is the only schema revision for this task. It adds actor-scoped, five-minute, single-use download grants and append-only artifact-specific `print_job_qa`; private PDF uniqueness/identity and QA release guards; and narrowly authorized occurrence/enqueue helpers. It preserves the existing scalar-only `render_config` allowlist. The complete immutable manifest is encrypted in the existing `print.render` durable payload; its digest is the print job fingerprint. Main PDF rendering never queries activation credentials or reconstructs concealed secrets.

Production rendering defaults **disabled**. An externally reviewed immutable P0 bundle and its exact SHA-256 are required via `SAFERETURN_PRINT_TEMPLATE_BUNDLE_PATH`, `SAFERETURN_PRINT_TEMPLATE_BUNDLE_SHA256` and explicit `SAFERETURN_PRINT_ENABLED=true`. The bundle is not an approval process: its `approval_ref`, licensed font, SafeReturn logo, English/Urdu copy, dimensions, material/scan reports and verified canonical HTTPS origin must first be approved by the responsible humans. No retail bundle, native-copy/font/artwork approval or physical scan pass was invented or enabled in the installed app. Proposed P1 template-design/publication tables/UI from the print amendment remain out of scope.

The strict bundle object has `renderer: safereturn-vector-v1`, `approval_ref`, HTTPS `origin`, `font` and `logo` (`path`, `sha256`), and `templates`. Each template binds immutable catalog `key`, `version`, `tag_type` (`lost|ice`) and `symbol_mm`, with separate `width_mm`/`height_mm`, `qr_x_mm`/`qr_y_mm`, bounded `logo_mm`, approved `min_pitch_mm`, readable `font_pt`, `header`, `english_lines`, `urdu_lines`. Bundle-relative asset paths resolve against the bundle file; asset hashes are checked again on every render. Keep old approved assets available for historical reprints. The fixed white-background P0 layout uses A4 with 10 mm sheet margins, 5 mm between trim rectangles, a four-module quiet zone and purpose-specific header/caption regions. This profile does not claim arbitrary full-bleed/canvas support; print-house bleed/trim/material approval remains a release gate. `size_mm_snapshot` is the complete QR symbol including quiet zone, not the outer label. Unknown bindings, changed files, missing glyphs, overflow, excessive module density or unsupported QR versions fail closed.

ReportLab emits compressed vector PDFs, reusing identical label forms. Segno produces ECC Q matrices; HarfBuzz/FontTools produce joined Urdu vector outlines, avoiding silent missing-bidi fallbacks. Approved separate Urdu runs are required; mixed Latin/Urdu caption lines are rejected. Synthetic acceptance uses installed licensed Arial only for tests; this is not approval of a production Urdu font. Preview `output/pdf/task54-synthetic-labels.pdf` contains 3 Lost then 2 ICE copies at a 35 mm QR size, only two distinct synthetic URLs, and a conspicuous nonproduction notice. It was rasterized and visually reviewed; all five branded symbols decoded, there are no raster images in the PDF, output is deterministic, and measured size is 119,142 bytes. Digital decoding does not replace real phone/material/lamination/low-light tests.

API-234 now uses the canonical audited `reason` + `expected_revision` request. It never accepts an arbitrary renderer/template override or mints new tokens. Reprints preserve the frozen manifest and revalidate current QR/entitlement bindings. API-233/235 return private status/metadata; API-213 returns owner-only counts/status with no staff artifact access. When printing is enabled, payment verification atomically emits one `print.request:<order_id>` durable `allocation.finalize` request alongside the existing finance event; missing renderer configuration causes print retry, not rollback of a trusted paid status. An automatic request creates one immutable `print.render` job. No worker daemon was started.

Run a bounded worker iteration only with explicitly loaded ignored configuration and the dedicated worker database URL: `python -m app.workers.printing --once`. Claims use SKIP LOCKED, unique per-claim owner and attempt fencing, bounded leases/retries/dead letters. CPU rendering/provider I/O runs outside critical database locks. Publication rechecks current paid/QR bindings and lease before artifact/job/event completion commits. A stale worker cannot publish; an uploaded-but-unacknowledged deterministic object is recovered only if its bytes/hash match. Private Storage uploads never overwrite, declare no-store/zero-age cache control, and reads bypass provider cache with `cacheNonce`. The configured `private-order-print` bucket is private, PDF-only and has a 20,000,000-byte technical resource ceiling; actual fixture bytes are measured rather than advertised as a universal PDF size. Existing payment bucket configuration remains unchanged.

API-236 returns a short-lived **application** grant: `grant_id`, `download_token`, `download_url=/api/v1/admin/print-downloads`, expiry and safe filename. POST that grant/token to the download URL with the same authenticated operations+MFA session. The extra redemption endpoint rechecks actor, role, account, expiry, paid/current QR binding, artifact retention and exact content hash, then consumes the grant atomically and audits access. It returns a no-store/nosniff attachment; it never exposes a persistent Storage URL. Creating a grant does not mark the job downloaded; successful redemption does. Concurrent redemptions release bytes to only one caller. Private object URLs and capabilities never enter localStorage or access logs.

API-237 records actual physical counts by QR type/size, observed artifact SHA-256, scanner/quiet-zone/logo/bilingual/cut/packaging/actual-scale confirmations and a reason. Approval requires exact immutable order sizes/counts and every check. QA records append only; a failed physical QA cannot release the job. Existing API-094 remains separate pair/concealed-insert QA and cannot be replaced by a PDF download. Production physical inspection has not been performed or approved by these tests. Staff UI uses canonical `/admin/print-jobs/[jobId]`; its same-origin relay is `/admin/print-jobs/api`, with server auth, Origin/CSRF checks, path allowlists and memory-only retry keys. Checkboxes start unchecked. This task does not implement shipping (5.5).

Reproduce from `backend` after building frontend, explicitly loading `.env`: set `SAFERETURN_CHECKOUT_BASE_REVISION` to the inspected installed revision (`0017_print_download_grants` now) and run `pytest tests/integration/test_printing.py -q -p no:cacheprovider`. Use a fresh workspace-owned `--basetemp` under `../tmp/` on this Windows host; ensure its parent exists. Opt in to the disposable live Storage test with `SAFERETURN_PRINT_LIVE_STORAGE=1`; every newly generated remote object key is tracked before upload and deleted in `finally`. No installed order/payment/Auth/QA records are seeded. Rehearsal operates only in fresh UUID schemas/NOLOGIN roles and verifies installed baseline metadata unchanged on cleanup.

Provider cleanup uses authoritative object-info absence and metadata checks, not an immediately repeated cached content URL. Supabase documents asynchronous CDN invalidation: https://supabase.com/docs/guides/storage/cdn/smart-cdn . A live probe verified fresh-origin content denial after deletion. Byte erasure/retention/hold/cache propagation policy remains Task 5.6/release work; the application grant proxy rechecks DB authorization independently of provider cache state. Linux native PDF dependency/build, approved production artwork/fonts/copy/domain, real physical scan/scale/packaging acceptance and worker deployment remain release gates. No production deployment, real payment or email occurred.


Task 5.4 final evidence (2026-10-17): **11 distinct integration scenarios verified across focused runs**, including corrected live/concurrency cases (2 PASS, 177.86s) and a late-completion fault-injection/recovery case (1 PASS, 151.28s); the other 8 scenarios passed in the broader 456.12s run. **3/3 browser checks PASS**, with the canonical-route wrapper reverified after route alignment (161.83s). **22 actual restricted-login tests PASS (61.94s), 213 local tests PASS (10.81s)**; frontend build/typecheck, scoped lint/format, pip/diff PASS. Applied only 0017 after full DDL rollback/retry: 43 RLS tables, all 3 original row contents, roles and unrelated definitions preserved; grant/QA tables and installed print/order/payment records remain unseeded. Final Storage/readback had no PDF objects or rehearsal schemas. Current app http://localhost:3031 / API 8030; private route/API denial checked. Original launcher had a transient DNS startup error, then health/catalog recovered. No daemon, real payment, email, production deployment, commit or push. Production printing stays disabled pending the documented approvals. Stop before 5.5.


### Task 5.5 — order history and operations fulfillment

Customer API-061 uses a bounded, opaque `(created_at,id)` cursor, including ties; malformed cursors return 422. API-062 returns immutable names/SKU/size/material/prices, independent Lost/ICE uses and copy counts, distinct pair count, current print status and the encrypted-at-rest purchase shipping snapshot decrypted only for its owner. API-066 exposes only that owner's safe carrier/tracking/status/timestamps. No activation secret, bank details, Storage object key, PDF grant or public QR token is returned.

Operations+current MFA is required on every API-232/095/096 request, including receipt replay. API-232 defaults to paid, fully allocated orders with latest artifact-specific physical print QA and latest pair/insertion QA; withdrawn/replaced/suspended/disputed bindings fail closed. `workflow_stage=packing_pending` is distinct from `ready_to_ship` (packed). Bounded filters for dispatched/delivered/exception/returned provide explicitly labeled shipment history rather than pretending these are ready orders. The queue exposes only destination city/reference; full address retrieval is a separate audited action.

API-095 accepts `order_id`, immutable `shipping_address_id`, the **complete exact** unique `pair_ids` set, carrier and reason. It creates one preparing shipment with all memberships atomically; a different-key retry cannot create a second shipment. API-096 requires `expected_status`, next status and reason; optional tracking preserves the previous value when omitted. Both commands require canonical actor-scoped Idempotency-Key receipts, encrypted with the existing profile keyring, plus minimal append-only audit. Missing crypto or any failed write rolls the entire transaction back. Finance verification now updates the order's derived fulfillment status to allocated in the same transaction that allocates its units, without changing verification or allocation semantics.

Allowed transitions: preparing → packed/exception; packed → dispatched/exception; dispatched → delivered/exception/returned; exception → returned. Delivered and returned are terminal. Packing requires explicit `packing_confirmed=true` after actual contents/concealed-insert inspection. Dispatch requires tracking. Delivery is an audited manual operations confirmation from independently trusted information; no carrier callback/provider is enabled. Status updates preserve server timestamps and serialize on the order before the shipment; stale `expected_status` returns 412. Paid matching settlement/current print and pair QA are rechecked before positive transitions. Refund/dispute/rejected settlement never permits outbound release. Recovery/replacement after an exception is a separate authorized workflow; this API does not silently release or reallocate inventory.

Canonical API-081 `GET /api/v1/admin/orders/{id}` requires operations/finance+MFA; only operations receives the full immutable shipping snapshot, with an atomic `shipment.address.read` audit. Finance receives safe order/line/copy/status details without the recipient address. It supports legitimate address access after a page reload; no saved address-book edit can rewrite the purchase destination. Order rows, snapshots, identities and payment evidence are never deleted by fulfillment. Delivery-triggered retention scheduling, policy approval/holds and provider reconciliation remain Task 5.6; delivery performs no automatic object deletion.

UI: `/orders`, `/orders/[orderId]`, `/admin/ready-to-ship`, `/admin/shipments` and its same-origin `/admin/shipments/api` relay. English/Urdu copy, mobile layout, explicit initially-unchecked packing confirmation, fixed path/method allowlists and exact-Origin mutation checks. Retry keys and shipping address display stay in memory, with no browser persistent storage of private data. No general admin dashboard, role-aware login redirect or MFA-enrollment screen is added in Task 5.5.

Verification runner: `backend/.venv/Scripts/python.exe ops/verify-task55.py` (Windows, workspace root). It loads ignored configuration without displaying values; tests use isolated UUID schemas/NOLOGIN roles and synthetic Auth, settlement, PDF storage and shipping. It compares exact installed public row fingerprints, roles and DDL before/after. Actual runtime-login checks: append `tests/integration/test_runtime_logins.py`. Task 5.5 adds scoped migration `0018_fulfillment_eligibility`: one operations-only boolean eligibility function (no bank data), one deferred completion function and two shipment/membership triggers, plus a narrowly scoped shipment-guard correction allowing safe exception/return transitions after settlement is paused/refunded. Positive release still requires verified settlement. It does not change tables, existing policies or finance privileges. It passed isolated API/commit-guard/browser tests and full actual installed-DDL rollback/retry rehearsal, then was applied only to authorized development. Installed head is 0018; exact existing rows, roles and unrelated definitions were preserved. Physical packing, trusted carrier delivery/provider acceptance and production release remain external gates.

Task 5.5 acceptance (2026-10-17): 19 unique integration scenarios verified across focused runs, all 5 browser checks, 24 actual post-migration restricted-login checks and 222 local tests passed. The Urdu 375px owner screenshot was visually reviewed. Interrupted provider/network runs are documented in PHASE_IMPLEMENTATION.md rather than represented as a single clean full-suite pass. The local launcher also supplies the existing server-only session-ticket key to Next; ignored credentials are unchanged. App http://localhost:3031; API 8030. Stop before Task 5.6.


### Task 5.6 recovery and configuration

PostgreSQL alone authorizes payments, allocations and shipping. No Sheet value is
an input to settlement. `python -m app.workers.finance_retention --mode sync`
executes one bounded durable job using `SAFERETURN_WORKER_DATABASE_URL`; no API
login fallback or worker daemon is started. Writers use a shared session advisory
lock (released before pool return), separate from business-row locks. Each
provider call occurs outside the business transaction. Lease ownership/attempt
checks fence all authoritative results. Retries use capped exponential backoff
with jitter; terminal finance jobs remain visible as failed through API-238 and
can be replayed by finance+MFA through API-239 without changing payment state.
Fulfillment changes enqueue another durable current-state mirror event.

Google writes stay disabled until the actual restricted sheet, tab, service
account permissions and column contract are reviewed and
`SAFERETURN_GOOGLE_SHEETS_APPROVED=true` is configured. The approved tab must begin
with these exact headers in A:K: `order_id`, `order_number`, `payment_status`,
`fulfillment_status`, `currency`, `amount`, `payment_method`, `sender_account`,
`evidence`, `export_version`, `reconciliation_time`. The adapter reads before
creating, updates a unique matching order row with RAW values, refuses duplicates
or newer remote versions, and recovers an ambiguous append by looking up the
stable order ID. No real spreadsheet acceptance has been authorized by this task.
Google's value-input contract: https://developers.google.com/workspace/sheets/api/guides/values .
Manual row edits, sharing and concurrent non-application writers require operator
reconciliation; the mirror range must be reserved for the approved service.

`--mode cleanup` schedules at most 100 due objects per approved resource type and
processes one cleanup job. `SAFERETURN_PRINT_RETENTION_APPROVAL` and
`SAFERETURN_EVIDENCE_RETENTION_APPROVAL` are separate documented policy references,
not retention durations. No reference, deadline, grace period or approval is
installed by the migration; missing configuration keeps deletion disabled.
Cutoffs must be assigned by the separately approved policy process. Before
committing deletion intent, the database checks delivery confirmation, verified
settlement, finance reconciliation, active jobs/download grants, support cases,
resource and order holds. Security admin/superadmin+MFA alone can place/release
holds, consistent with existing RLS. Inventory exposes metadata and cleanup
status/errors, including the reserved `retention.deleting` recovery marker.

Migration 0019 commits an audited intent before remote deletion. Hold, reprint,
download and dispute admission serialize against that intent: a hold committed
first blocks deletion; after intent, conflicting admission is refused and requires
reconciliation. Remote failures leave the intent and original object identity
intact. Storage deletion must verify a private bucket and fresh authenticated
object info, bypassing cached downloads; a DELETE acknowledgement alone cannot
write a tombstone. Typed Supabase missing-object responses support idempotent
recovery (https://supabase.com/docs/guides/storage/debugging/error-codes).
After confirmed absence, lease-fenced finalization preserves hashes, metadata,
order/payment/QR/copy/audit history and marks a print job deleted only when its
last artifact is gone. A dead cleanup job can be replayed through security+MFA
`POST /admin/storage/artifacts/{id}/cleanup-retry` with `reason_code`; prior
attempt count is retained in an append-only audit event. Replays cannot override
a hold, pending support case or missing policy approval. Use forward recovery;
transaction rollback is rehearsed before applying 0019, and downgrade refuses to
discard committed intent/history. Files already removed remotely cannot be
restored by a database rollback; approved reprint regeneration/backup acceptance
remains governed by existing print and production release gates.


Task 5.6 verification (workspace root, Windows):
```
backend/.venv/Scripts/python.exe ops/verify-task56.py tests/integration/test_finance_retention.py -k "retention_intent_recovery or unconfirmed_delete or cleanup_stale" -x
backend/.venv/Scripts/python.exe ops/verify-task56.py --live-storage tests/integration/test_task56_storage_live.py -x
```
The live-storage opt-in creates and deletes only fresh UUID-scoped synthetic
objects in the two already configured private buckets; it never creates buckets,
changes their policy, or operates on pre-existing object keys. Default execution
skips that test. Run remaining database/browser scenarios in similarly bounded
focused groups; separate passing runs are not a single full-suite pass.


Task 5.7 inbox/account/help/settings:
- API-050 uses an opaque timestamp+UUID cursor with bounded input and one-row lookahead; summaries exclude contact/message/location ciphertext and plaintext.
- API-051 decrypts only for the immutable original recipient. Consented coordinates must be finite and geographically valid; missing keys or invalid ciphertext fail closed.
- API-052 accepts only viewed/archived/flagged. API-053 idempotently records status=deleted and hides the message; it preserves contents, consent, location, outbox and holds. deleted_at remains the physical-erasure tombstone. No message retention period, purge approval or automatic erasure worker is invented. Approve privacy-policy timing/purge separately before release.
- `/inbox` and `/inbox/[messageId]` use server-only authenticated requests and exact-Origin mutation actions with explicit deletion confirmation. No message is stored in browser storage. `/settings` links to the implemented account/per-QR/orders controls. `/help` is public bilingual static help, usable without JavaScript; no unsupported support/chat endpoint.
- Account confirmation/recovery/password-change acceptance, MFA enrollment, data export/address-management contracts and actual legal erasure timing remain release gates; this task does not assert those unfinished flows work.

Bounded synthetic DB/API/browser verification, with exact installed row/role/DDL preservation:
```
backend/.venv/Scripts/python.exe ops/verify-task56.py tests/integration/test_inbox.py tests/integration/test_runtime_logins.py -x --tb=short -s
```
The reusable preservation runner keeps its existing filename. Browser Auth is synthetic; no real messages, managed Auth edits or provider email deliveries are performed.

API-022 exposes only actor-scoped consent/publication audit metadata (latest 100, with has_more); active is the historical state at the event, explicitly marked state_scope=recorded_event. It does not expose other users' consents or claim old consent remains active now.
API-023 records reviewed account-deletion requests only: explicit boolean confirmation, verified email, signed provider AMR within the existing 300-second high-risk window, bounded JSON and encrypted optional reason (actor UUID + account_deletion_reason AAD). It atomically creates a privacy support case and minimal audit marker, serializes per-actor concurrent retries and returns the same active request. The workflow never deletes/disables/transfers accounts, orders, QR pairs or legal records, and sends no email. Manual review, erasure authority/timing and backup policies remain release gates; no migration or new credential is needed.
