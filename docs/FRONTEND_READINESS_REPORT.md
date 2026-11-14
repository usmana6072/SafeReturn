# SafeReturn frontend readiness report

Assessment date: 2026-10-21, Asia/Karachi. Scope: Step 1 only. **PARTIALLY VERIFIED.**

## 1. Executive summary

The existing architecture supports beginning a narrow frontend integration slice, with explicit unavailable/error states. It does not support claiming that all business workflows are operational or production ready. Database connectivity, installed schema, real Auth, provider delivery and worker operation remain unverified in this assessment. Do not enable pending capabilities to make screens appear functional.

The repository already contains substantial Next.js frontend implementation. Preserve and reuse it after this step; no frontend implementation was performed here. The working tree was already extensively modified, including pending migrations and backend/frontend features. Existing work was preserved.

Reviewed PHASE_IMPLEMENTATION.md (including recent handoffs), backend README/pyproject, application/router/auth/database/worker/provider sources, all revision declarations, 0022–0035 companion DDL, existing tests, frontend auth/transport/package configuration, CI, Docker/Railway baselines, ops/WORKER_OPERATIONS.md and the blocked-task contract review. Product/API/database/security/test/deployment documentation and relevant source handoffs provide intent; executable evidence below takes precedence over IMPLEMENTED labels. Historical development head 0021 is a handoff statement, not a fresh installed-state observation.

## 2. Backend architecture

- FastAPI factory/lifespan installs public, owner and staff routers under `/api/v1`. Current OpenAPI contains 120 paths, 142 operations and 184 component schemas.
- SQLAlchemy sessions use psycopg 3, bounded pools/timeouts, pre-ping, explicit transaction scopes and rollback on failure. Separate API, worker and migration credentials are intended. Startup does not migrate the database.
- Supabase manages Auth; JWT verification uses fixed issuer/audience and asymmetric JWKS. Application authorization additionally checks the database session/account and applies actor-scoped runtime roles, RLS, helpers and owner guards.
- Much business logic resides in SQL-backed route modules and PostgreSQL security functions/triggers, rather than a uniform service layer. New abuse/template services add separate orchestration. SQLite/scripted tests cannot establish PostgreSQL semantics.
- Private storage, Turnstile, Resend, Cloudinary, optional Google Sheets and print/font/native rendering are separate dependencies. Durable jobs have lease/retry/fencing logic; the new operations module is an offline model, not a supervisor.
- Existing frontend: Next.js 16/React 19, server-side Supabase SSR cookies and authenticated API relays. Continue the same-origin server relay design; do not introduce a second browser token transport.

## 3. Database and migration readiness

An ignored backend environment file exists and contains database/Auth/provider key names. Values are not reproduced here. No SAFERETURN variables were initially exported. Environment files are not implicitly loaded by Settings. A separate probe read the test connection setting only, attempted a read-only metadata transaction, suppressed raw exception text and failed with OperationalError before metadata was available. Network/access/service availability cannot be distinguished from that sanitized result. No persistent data, role, migration or schema was modified.

Static AST validation and Alembic heads/history agree: **36 revisions, one connected chain, head 0035_public_abuse_intake**, no missing parent/cycle. The extra 0014a notification revision explains the count. Every pending Python wrapper has its companion SQL. This proves graph/file integrity, not PostgreSQL parse/function/permission/locking compatibility.

| Revision | Required schema/capability | Integration implication |
|---|---|---|
| 0022 | Export authorities, requests, decisions, grants; active-request index | Export workflow also needs injected real storage and worker runtime |
| 0023 | shipping_addresses.is_saved/version, composite owner uniqueness, shipping_address_books, owner policies/default guards | Saved address reads/writes and saved-address checkout need these columns/table |
| 0024 | Cancellation request/reconciliation/event/consumption tables and orders changes; active cancellation uniqueness | Cancellation/release workflows remain gated |
| 0025 | Financial case authority/bindings/decisions/fences and indexes | Dispute review and protected settlement transitions |
| 0026 | Finance reconciliation helpers | Reconciliation console; no new tables |
| 0027 | Manufacturing sources/approvals/exports/events/receipts/grants/handoffs; durable_jobs change | Export UI requires authority, custody and renderer/storage integration |
| 0028 | Dashboard read helpers | Optional dashboard, default disabled |
| 0029 | Staff directory read helpers | Optional security staff directory |
| 0030 | Account security state/case bindings/custodians/approvals/events/receipts | Account lifecycle and session-state changes require real SQL/Auth verification |
| 0031 | Staff account-state projection using 0030 state | Directory lifecycle status needs parent capability |
| 0032 | Owner history and public-status command helpers | Owner disable/resume is distinct from replacement or staff containment |
| 0033 | Template/revision/asset-set/preview-command/attempt tables and indexes | Draft/preview management needs reviewed assets/runtime |
| 0034 | 13 authority/publication/binding/snapshot/hold tables and related indexes/helpers | Existing catalog/checkout/payment/print paths now include registry compatibility gates |
| 0035 | Six policy/attempt/proof/report/receipt/event tables, dedup/rate indexes, intake/triage helpers | Abuse intake intentionally disabled/unseeded |

Pending SQL explicitly creates restricted policies/grants/functions and preserves history. Several downgrades refuse destructive removal or revoke admission only; code rollback is not schema rollback. Do not run downgrade/reset/stamp to resolve drift. Registry helpers probe function availability on older schemas; that compatibility branch is source/synthetic evidence only until exercised against installed 0021 and an upgraded clone.

Missing installed tables/columns/indexes/constraints cannot be conclusively listed without a successful catalog read. If handoff head 0021 remains current, all objects above are absent. Their required DDL inventory is captured in `backend/output/frontend-readiness/inspection.json` and `migration-ddl-index.txt`. Do not report them installed.

The shared PostgreSQL rehearsal metadata checker uses current-head by default but hard-codes only older table counts (44 at 0021, otherwise older branches). Adapt it to the intended isolated target before current-head testing. Some tests explicitly target 0021 and must retain that preservation baseline. Alembic target_metadata registers models/commerce/workflows, while newer capabilities include SQL-managed tables/functions/policies; inspect autogenerate differences rather than blindly accepting generated drops or treating alembic check as exhaustive SQL validation.

Next database actions: identify the exact nonproduction project and permitted test namespace/roles; restore connectivity; obtain a read-only revision/catalog/RLS/grant baseline; rehearse actual upgrade through 0035 in an isolated clone with schema/data/role preservation checks; verify restricted API/worker logins and old/new-schema application behavior. Apply reviewed migrations only after that rehearsal and explicit target confirmation. No migration application is required merely to start a read-only catalog screen.

## 4. Authentication readiness

JWT implementation checks ES256/RS256, kid/key type/strength, issuer, strict authenticated audience, expiry/issued-at, authenticated role, nonanonymous access-token type, subject/session UUIDs and bounded JWKS refresh. Foreign/unsigned/expired/anonymous/service credentials are rejected in existing synthetic tests. AMR timestamps, rather than refreshed token iat, establish recent reauthentication.

Protected transactions verify session/account state through sr_account_session_state. Staff actions require verified email, provider MFA claim plus database MFA state, and explicit nonrevoked staff roles. Owner guards scope orders, QR/pairs, payment attempts and original message recipients; concealed 404 avoids resource disclosure. Staff-security bootstrap is intentionally accessible before MFA to discover capabilities; it does not authorize privileged operations.

Signup/login/logout/recovery/MFA enrollment are Supabase flows in the existing frontend, not custom FastAPI password endpoints. Logout calls global provider signOut; backend database session validation is intended to reject revoked sessions. Real signup/email confirmation, login/refresh, logout revocation, expiration, recovery and MFA still need fresh provider plus database verification. No real user account or managed Auth row was accessed or changed.

API auth is `Authorization: Bearer <Supabase access token>`. API cookies are not the authentication mechanism. Existing SSR auth cookies are HttpOnly, SameSite=Lax and Secure in production; origin validation protects server mutations. Several newer backend workflows additionally require an exact configured Origin; a relay must preserve the approved origin. No CORSMiddleware is installed, so direct browser-to-API cross-origin credential requests are not supported. This is compatible with existing server relays and is not a reason to add wildcard CORS.

AccessError returns a concealed error envelope, request ID, no-store and a Bearer challenge for 401. Error families vary: account validation uses 400 in places, DTO validation commonly 422, stale mutations 409/412, missing/wrong origin 403, provider/config failure 503. Catalog error bodies omit some fields present in the bilingual auth envelope; default FastAPI 404/405 and documented validation responses differ again. Frontend errors must tolerate these forms, never display raw server/provider text and distinguish reauthentication, forbidden, stale state and temporary unavailability. No authentication was weakened.

## 5. Core API inventory and operational status

All rows below have routes and underlying implementations, except explicit legacy rejection/unfinished actions. **None of the database-backed success paths is freshly verified live by this assessment.** Source and synthetic tests establish integration candidates, not provider/SQL operation. Exact paths, operation IDs, bodies, parameters, security declarations and response schemas are in the generated `backend/output/frontend-readiness/{API_CONTRACT_INVENTORY.md,contracts.json,openapi.json}`. The source index is `route-source-index.txt`.

| Workflow / APIs | Requests and responses | Authorization | Status and frontend disposition |
|---|---|---|---|
| Health API-001/002 | Minimal live status; protected database connectivity status | Live public; ready dedicated token | Offline liveness tested; live DB probe blocked. Readiness checks SELECT 1, not schema/business readiness |
| Account API-020–023 / staff-security | Account summary/version/ETag; PATCH display_name/locale; consent history; explicit deletion request | Actor session; verified/recent AMR for high-risk request | Reuse for initial account slice after Auth/DB smoke; deletion is a review request, never execution |
| Catalog API-003/004/200–202 | Public product/category/variant and SKU detail payloads, prices/availability; no write body | Public; staff writes operations/security_admin/superadmin + MFA | Best first read-only candidate; needs installed schema and published/approved catalog assets/templates. Empty catalog is not an outage |
| Checkout API-203/204 | QuoteRequest lines/QR uses/address or saved ID+version/contact confirmation; confirm accepted decimal total and PKR; 201 quote/order/reservation | Verified owner, Idempotency-Key | Implemented with transactions/locks; config, stock, crypto, migrations and registry compatibility block operational approval. API-060 POST /me/orders intentionally rejects with 409 QUOTE_REQUIRED |
| Payment API-209–212/240–241 | Sender account/reference; bounded file metadata/hash; signed upload then finalize; finance bank review | Verified order owner; finance+MFA review | Requires private evidence storage/service credentials, payment reference key and real bank reconciliation. Evidence is not settlement proof |
| Inventory/activation API-084/085/090–092/207/208/032 | Batch specs; activation context/intent/confirmation; atomic pair result | Operations+MFA inventory; public context; verified actor activation | Requires secret/crypto keys, inventory and SQL procedures. Do not collect/reveal manufacturing secrets in a generic screen |
| Owner QR/profiles API-030/031/040–049/205/206 | Pair/QR summaries; Lost/ICE/contact preferences; versions and consent fields | Verified owner; If-Match for edits | Implemented candidate; encryption keys, approved consent and PostgreSQL race/authorization checks required |
| Public scan API-010/012/013 | Token lookup; allowlisted PublicQRProfile; consent-gated contact reveal/WhatsApp link | Public with server-side restrictions/rate budget | DTO/source reviewed; needs real projection/RLS/rate-limit/consent verification. No-store/no-referrer/noindex retained |
| Finder intake API-011/015; inbox API-050–053 | FinderMessageRequest; 202 receipt; paginated summaries, decrypted recipient detail, status patch and 204 logical delete | Public anti-abuse intake; immutable original recipient inbox | Turnstile/crypto/DB required; Resend worker needed for notification delivery. Logical delete does not erase contents |
| Orders/fulfillment API-061/062/066/080/081/095/096/232/246/247 | Owner order/shipment summaries; staff filtered orders and shipment commands | Owner; operations (finance on permitted admin reads)+MFA | Candidate reads after smoke; shipment release requires settlement and complete QA/allocation. Carrier/physical packing acceptance external |
| Printing API-094/213/233–237/349/350 | Job request 202; job/QA summaries; grant/redeem private binary artifact | Operations+MFA; owner gets restricted summary | Requires print flag, immutable approved bundle/assets/fonts/native libraries, private storage, worker and physical scan QA. A queued job is not a rendered artifact |
| Support API-097–099 | Filtered cases, Intake and conditional Change, audit/idempotency | Support+MFA | Existing console source/synthetic coverage; payment/privacy/ownership resolution has separate authority. Not a public chat/contact service |
| Public config API-005 | Closed bilingual metadata, consent versions and availability | Public | Default response and unavailable metadata tested offline. Real policies/support contact registry intentionally empty |
| New optional staff/self-service modules | Privacy exports, addresses, cancellation/disputes, reconciliation, manufacturing, dashboard/directory/account lifecycle, owner status, template publication, abuse | Per-role+MFA/owner/recent-auth/origin/policy as applicable | Routes exist; pending 0022–0035, disabled flags, missing authorities/adapters/runtime remain workflow dependencies; do not advertise as usable |

Contract findings: OpenAPI generation emits no warnings/duplicate operation IDs; local references resolve in regression coverage. **92 operations have an empty or unspecified 200 JSON response schema** (including endpoints whose real success is another status or binary). Several manually parsed bodies/headers and runtime errors are not fully described. Do not generate an unchecked client and assume complete DTOs. Document narrow response parsers from actual schemas, route outputs and tests, then validate against a real authorized environment. API-060 previously advertised 200 despite deliberately returning 409; this assessment corrected its decorator to document 409 without changing runtime behavior and added a focused regression test. A reviewable generated route/body/status appendix is [FRONTEND_API_CONTRACT_INVENTORY.md](FRONTEND_API_CONTRACT_INVENTORY.md).

Screen contract rules: pass If-Match/expected_version or expected_revision exactly as the relevant endpoint requires; keep money as server-provided decimal strings; reuse Idempotency-Key across retries of the same mutation; respect opaque cursors, 201/202/204 semantics and null/unavailable states. Never treat 202 as completed delivery or a 204 delete as physical erasure.

## 6. Verification evidence

Local evidence directory: `backend/output/frontend-readiness/`. Python runtime: existing Windows Python 3.14 virtual environment; project minimum/hosted CI target is 3.12. No dependencies installed. No backend typechecker is configured.

| Check | Actual result | Evidence / limitation |
|---|---|---|
| Default pytest -q -p no:cacheprovider | Collection failed: 3 errors, 10.75 s | pytest.log/xml: duplicate test_finance_retention module name, missing guarded task62a_harness import, inaccessible tests/tmp directory |
| Existing Task61a guarded runner | 254 passed; zero failed/errors/skips; preservation passed; 58.054 s | guarded.log and existing output/task61a latest evidence. Seven-file synthetic subset only |
| Broad explicit top-level unit selection | 1,304 passed, 8 failed; 478.93 s | unit.log/xml and unit-by-module.json; importlib mode, explicit test files and writable basetemp; excludes guarded Task61a/62a and worker-operations modules, which require their own runners. Run preceded the one-line API-060 documentation correction |
| Integration directory without loaded environment | 2 passed, 3 failed, 184 skipped, 385 errors; 48.25 s | integration.log/xml. Failures: missing API/test database env and unset Supabase origin; setup errors demand explicit PostgreSQL env. These are not observed business failures or passing real DB checks |
| New frontend-boundary regression tests, final | 10 passed, 6.50 s, warnings treated as errors | baseline-final.log/xml: OpenAPI IDs/refs, six protected reads, default public metadata, no implicit credentialed CORS and corrected legacy order status/runtime rejection. Earlier nine-case run also passed |
| Existing guarded Task63a worker model tests | 49 passed, zero failures/errors/skips; source preservation passed | worker-model.log; synthetic model only, no real workers/signals/providers |
| Ruff app tests | Passed | ruff.log, includes new tests; new test file format check passed |
| Static migration graph + Alembic heads/history | Passed; 36 revisions, connected head 0035 | inspection.json, alembic-history.txt; no upgrade/DDL executed |
| Read-only configured test database probe | Blocked: OperationalError | database-readonly.json. No installed schema/auth/catalog claim |
| Real providers, worker deployment, native/physical print acceptance | Not run | No provider mutations, worker activation, deployment or frontend implementation. Broad backend selection unexpectedly includes one synthetic catalog browser test; it ran and failed as detailed below |

Reproduction from backend: `.venv/Scripts/python.exe -m ruff check app tests`; `.venv/Scripts/python.exe -m pytest tests/test_frontend_baseline.py -q -p no:cacheprovider`; `.venv/Scripts/python.exe ../ops/run-task61a-backend.py`. Raw whole-suite commands currently need collection/environment repair; do not silently convert setup failures into skips or present subset results as a full-suite pass.

Broad-run failures, all retained rather than hidden:

- `test_catalog_readiness.py::test_catalog_browser`: backend test invokes a synthetic local Next/Playwright fixture; expected `Catalog template` control was absent. This is a browser contract/build-fixture issue to reconcile before the catalog administration workflow, not proof of a failed public product API. No frontend source was edited.
- `test_financial_disputes.py::test_real_worker_recheck_stops_before_render_upload_and_records_safe_failure`: mocked fence lambda does not accept the newer `admit=False` keyword; execution stops at the test double rather than proving the expected worker failure record. Update the mock signature and rerun without relaxing finance fences.
- `test_health.py::test_contract_and_unimplemented_routes`: an exact old path-set assertion omits the new routes. Refresh the explicit contract snapshot and retain operation/security assertions.
- `test_inventory_console.py::test_pair_qa_replay_conflicting_round_and_negative_not_quarantine`, `test_pair_qa_atomic_rollback[qa/audit/commit]`, `test_false_observation_and_ineligible_pair_fail`: Memory session double lacks SQLAlchemy `session.info`, now required by the template registry compatibility gate. Model capability detection/transaction state in the fixture and retain QA/rollback assertions; do not bypass the production gate.

Selected broad-run module counts: auth 57 passed; staff_security 17; database 13; checkout_validation 16; critical_workflow_boundaries 6; payment_storage 13; profile_crypto 10; messages 12; public_configuration 41. These are included in 1,304, not additional independent successes or live verification. Native rendering unit assertions, where exercised, do not constitute actual configured manufacturing/physical acceptance. Existing broad CI currently runs only the guarded seven-file subset, not all these modules.

Integration skip reasons (184 total): 150 development PostgreSQL not configured, 3 dedicated test PostgreSQL not configured, 26 dedicated runtime login not provisioned, and 5 explicit live-provider/storage/PDF opt-in gates. All 385 setup errors have the same explicit-development-environment prerequisite. No skipped case counts as passed. The read-only connection attempt was separate from this intentionally unconfigured integration run.

## 7. Missing configuration and external dependencies

Presence of an ignored key name is not proof of valid credentials, provider permissions or an approved environment. Startup must explicitly load reviewed configuration and use the API login, not migration credentials. Verify remote PostgreSQL TLS (enforced by URL parser), runtime RLS/grants, Supabase origin/JWKS/session functions, redirect allowlists, web/API origins and HTTPS cookie behavior.

Checkout defaults disabled and requires shipping/tax amounts, crypto/payment keys, approved sellable stock/templates. Printing defaults disabled and requires a pinned approved bundle/hash, recipient keys, fonts/native renderer and private object storage. New workflow flags default off; per-feature origins, policy IDs/HMAC keys, authorities, evidence and storage injection are additional gates. Worker URL being present does not establish a scheduled worker. Retention approvals, actual cutoff policy and Sheets approval/permissions must remain separate from generic provider credentials.

## 8. Prioritized gaps

See BACKEND_GAP_TRACKER.md for severity, status, workflow/fix and launch impact. BLOCKING NOW applies to claiming verified live integration; it does not prohibit developing a read-only screen against reviewed contracts. Most newer pending capabilities are INTEGRATION DEPENDENCY only when their corresponding screen is selected. Workers/alerts, erasure policy/execution, security containment and manufacturing authority are PRE-LAUNCH BLOCKER items. No known approved safety capability was reclassified as future scope merely to reduce this step.

## 9. Frontend workflows ready to begin

Ready for implementation against reviewed contracts: public read-only catalog/detail, public configuration/unavailable states, and the existing same-origin transport/error boundary. Ready conditionally after successful real Auth/DB smoke: account summary/edit, owner QR/profile/contact controls, owner inbox and order tracking. Checkout/payment/print/fulfillment transactions need their specific live success/rollback/authorization/provider gates before being called functional. Keep deferred screens unavailable rather than inventing backend responses.

## 10. Recommended first workflow

Continue the existing **public catalog → product detail** slice using API-003/004 and the category/variant reads. Reuse current frontend transport/components, validate runtime responses, show genuine empty/unavailable states, and do not take payment or reserve inventory. It avoids provider login, private uploads and worker execution while validating routing, English/Urdu content, data parsing and failure handling. Then verify Supabase signup/login/logout/session expiry and integrate GET/PATCH /me with If-Match before any checkout flow.

## 11. Exact next actions and completion boundary

1. Restore access to an identified authorized nonproduction database and obtain read-only installed revision/catalog/grants evidence; never reset an unknown target.
2. Repair/review full-suite collection and current-head rehearsal assumptions, retaining separately guarded test entry points. Run restricted-login auth/owner/staff/MFA/negative cases and actual migration preservation/constraint races on an isolated target.
3. Verify catalog/account happy paths and auth failure/expiration/logout against real development Supabase and the least-privilege runtime login. Record exact results without tokens or user data.
4. Complete narrow frontend response/header contracts and advertised status documentation for the first selected workflows; retain default-off newer modules.
5. Implement frontend catalog/detail only in a subsequent step. Schedule worker/provider/privacy/manufacturing acceptance alongside frontend work before activating dependent screens or launch.

The repository review, offline checks and prioritization are delivered. Essential live verification remains blocked; **Step 1 is PARTIALLY VERIFIED**, not fully complete or production approved.
