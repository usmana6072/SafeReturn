# SafeReturn backend

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
