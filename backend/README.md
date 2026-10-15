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
public privacy projections/reveal remain Phase 4 and editors remain Task 3.4.
