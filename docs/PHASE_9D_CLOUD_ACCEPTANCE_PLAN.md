# Phase 9D — existing Supabase Cloud development acceptance preparation

**Current provisioning update (2026-10-24):** owner-approved [development exception v1.1](BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md) permits the one owner-controlled Support subject without Ahmad/third-person approval. Restricted local command, owner intent/UUID binding, route/readiness fences, provider checks, expiry/revoke/audit/receipt protections and pre-grant MFA adapter are implemented and isolated-tested. Source migration0044 is **not applied**; previously verified Cloud head0043 is unchanged by this work. No real identity/email/MFA/grant or PostgreSQL acceptance is claimed. Exact cloud mutations remain pending authorization; endpoints NOT ADMITTED, Support live gate DISABLED. See current tracker and [operational runbook](../ops/SUPPORT_DEVELOPMENT_EXCEPTION.md); older custodian requirements below are historical and superseded only for this exception.

Date: 2026-10-24 (Asia/Karachi). **CURRENT: RUNTIME TLS FIX APPLIED; REAL FASTAPI→CLOUD CONNECTION AND THREE UNAUTHENTICATED401 CHECKS PASSED. SUPPORT FRONTEND IMPLEMENTED; LIVE ACCEPTANCE BLOCKED BY MISSING DEDICATED SUPPORT/MFA IDENTITY AND OTHER MANDATORY GATES.** No schema loss/reset/rebuild; see final execution result.

The owner explicitly confirms the existing Supabase Cloud project is **only for SafeReturn development/testing, not production**. Use it as the proposed Phase9 acceptance candidate, subject to project identity, installed security, data preservation and operation-specific approvals. Docker Desktop/local Supabase installation is **cancelled**, not a pending next action. Existing PostgreSQL17.11 at127.0.0.1:55439 and its data directory remain unchanged; no connection to it was needed for this assessment.

## 1. Configured identity and environment designation

Read local configuration without loading it into a server or connection tool; compared project identities in memory and printed no URLs, credentials or keys.

| Evidence | Result / limits |
|---|---|
| Backend Auth project reference | Redacted **fhux…kzvq**; SHA256 reference fingerprint prefix **17e54a8be1b7**. Full reference remains in protected local configuration; it is not a new credential or a cloud verification result. |
| Runtime/migration/test URLs | All configured references match the backend Auth project. All three select the **same configured pooler endpoint and database name**, although login identities differ. Port classification is session-pooler candidate, not a live connectivity/mode test. |
| Separate acceptance isolation | No dedicated acceptance/staging/test environment file or project configuration was found in inspected standard repository paths. TEST_DATABASE_URL points to the same configured DB, so its name does not create a disposable database. Different logins change privileges, not data isolation. |
| Environment classification | Owner's current explicit confirmation establishes intended development/test use. No dev/staging/production designation key exists in inspected backend/frontend local environment files. Project URL/ref alone does not prove actual usage or safety. |
| Frontend configuration | No matching backend-project Auth setting established from frontend/.env.local; no frontend configuration/integration changed. |

Before remote operations, owner must confirm that the redacted reference/fingerprint identifies the intended cloud development project. A Dashboard/project-name confirmation can be supplied without credentials; this assessment did not contact the Dashboard, Management API, Auth or database. Do not infer exact project identity from a shared pooler address/server IP alone.

## 2. Existing data and historical migration evidence

`docs/LOCAL_FRONTEND_BACKEND_PHASE8.md` records an owner-approved **development** upgrade on23 October2026 through `0043_standalone_activation`, all22 then-pending revisions0022–0043 committed, release gates disabled,111 public tables, existing audit/idempotency/catalog/staff/profile records preserved. Recorded populated counts included audit21, idempotency17, categories1, images3, variants2, products2, staff_roles2 and profiles2. That is historical evidence, not a new query or proof current configuration still targets exactly that historical installation.

The project is therefore **not presumed empty or disposable**. Historical profile/staff/catalog rows do not prove production use or real customer transactions, but neither are they certified synthetic. Treat all existing accounts/profile data/history as potentially personal, valuable development data. Do not inspect existing customer payloads or use any existing real account as a fixture. `ops/STAFF_PROVISIONING.md` explicitly says existing owner Operations/Finance grants are not test subjects and the runbook itself is not live provisioning authorization.

Expected cloud provider Auth schema and baseline roles should come from Supabase Cloud; required SafeReturn RLS/helpers are historically expected because head0043 includes0035. **Current presence, definitions, privileges, role membership, grant freshness and settings are unverified.** A recorded migration number does not prove correct installed functions, source equivalence or acceptance. Do not rerun migrations, stamp/reset the DB or transplant local schema to reconcile old tracker wording.

## 3. Auth/RLS and migration prerequisites

Sources: `backend/app/core/auth.py`, `core/config.py`, `api/auth.py`, `db/runtime.py`, `services/support_metadata.py`; Alembic0001/0003/0005/0021/0029/0030/0035 and their companion SQL; approved Security/Privacy requirements. Exact details remain in the Phase9A inventory addendum and earlier Phase9D schema assessment.

- Managed auth.users must expose actual UUID/verification/deletion/ban/anonymous/creation fields; auth.sessions must supply UUID/user/expiry/AAL/created_at. anon/authenticated/provider roles are expected, not manually created.
- Runtime uses existing safereturn_api_login → SET LOCAL ROLE safereturn_api, verified transaction-local actor/MFA context and current Support grant; never the migration/bootstrap/service-role login as an RLS acceptance principal.
- `sr_account_session_state`, account-epoch checks, Support-role/email/signed+provider MFA and final auth recheck must match source. `JWTVerifier` requires real HTTPS, ES256/RS256 public JWKS, exact issuer/audience/session claims. No API key as bearer token or MFA stub.
- support_cases/support_case_events and assignment predicates must preserve base/restrictive case RLS, assigned-only event policy, retained abuse policy/readability/gate/retention/triage and current policy validation. Missing helper remains503; do not disable it to obtain a passing result.
- Existing helper owners/search paths/EXECUTE and table grants, safe audit INSERT/JSON trigger and nested policy dependencies require catalog/source inspection. Querying definitions does not prove actual RLS or live Auth behavior.
- Required ordered SafeReturn dependency target is0035 via36 revisions including0014a. Historical0043 is newer and may satisfy that dependency; installed/source comparison must precede any proposal. **No cloud migration authorization exists.** The previous Phase9D migration approval targeted the local empty55439 DB and does not transfer to Cloud.

## 4. Proposed first remote operation — approval request A

**Not performed.** Request a bounded read-only metadata audit of the configured development project **fhux…kzvq / fingerprint17e54a8be1b7**:

1. Owner confirms exact project identity and authorizes use of the existing reviewed local credential for **one explicit configured session-pooler or direct DB target**, not arbitrary alternate URLs. Use the least privileged existing login capable of the listed catalog reads; no new grants or password changes. Validate TLS server identity; no implicit defaults, insecure fallback or probing another endpoint if this one fails.
2. Open a short-lived session with explicit target, connection/statement/lock time limits and enforced read-only transaction, sanitized child configuration, parameter/error logging disabled. Verify read-only mode and local-vs-remote selection before queries. Do not start FastAPI/worker/frontend or the general integration harness to discover connectivity.
3. Read **only** connection/database/version metadata; public.alembic_version revision rows; relevant schema/table/column existence/types; RLS flags/policies; specific runtime/provider role flags and memberships; relevant schema/table/function ACLs, SECURITY DEFINER owners/search paths and trigger/helper definitions/dependencies. Limit catalogs to the named Auth/support/staff/account/abuse/audit dependencies. Inspect definitions without executing business helpers or triggers; compare privately to repository source. No pg_authid/password hashes/signing secrets, Auth user/session/factor rows, staff memberships by individual, customer content, table/domain counts, policies' business records or QR/pair records.
4. Preserve the service dependency graph: source definitions of retained-policy/audit/security helpers may mention excluded relations elsewhere, but no pair helper/record operation may execute. If any new metadata path reaches such processing, stop. Do not invoke protected Support/Finance/Orders routes or metadata endpoints yet.
5. Independently authorize **one unauthenticated HTTPS GET to the same project's `/auth/v1/.well-known/jwks.json`**, bounded64KiB, certificate verification enabled and redirects rejected. Record only success/failure, supported public key algorithms/IDs and compatibility, never private keys or bearer credentials. This checks public discovery, not sign-in, enrollment, MFA or an issued token. If only DB inspection is approved, defer this GET.
6. Close/rollback the read-only session and record minimal redacted results. No migration, temporary schema/table/role, fixture, user, session or application write. Normal provider connection/access logs may be produced by a connection/GET; no application-state change is proposed.

Existing `backend/app/integration_check.py` is not automatically run: its broader release-gate queries and chosen credentials need a separate scope review. `pg_rehearsal.py` is expressly excluded because it reads domain counts, creates schemas/roles and performs migrations/cleanup. No broad legacy test suite.

## 5. Later operation-specific approvals — not covered by A

| Approval | Exact proposed work / limits |
|---|---|
| B. Auth test identity and staff authorization | After approving the actual plan/hook/email impact, create dedicated disposable provider accounts via supported Auth mechanisms, perform genuine email verification and TOTP enrollment/challenge/verification, and grant only explicitly approved Support roles through the controlled staff runbook with named approval/audit. No existing account/role changes. No automatic email-confirmed flag, auth.sessions SQL, token fabrication or service-role RLS bypass. |
| C. Fixtures/policies | Approve exact synthetic subject-free cases/history/assignment/policy/version/provenance, dedicated IDs/ownership and creation/cleanup mechanisms **only after** proving setup/teardown do not invoke pair processing or bypass protections. No current safe creation path has been established; see section6. |
| D. Focused API/PostgreSQL/Auth acceptance | Only after A/B/C gates: dedicated new identities/session tokens, restricted runtime DB login and the three new metadata GETs; allow their actual minimal support.metadata.* audit INSERTs. Include explicit approval for those audit writes even though HTTP methods are GET. No migrations, old routes, other modules or real account data as test subjects. |
| E. Any schema/security/config repair | If A finds differences, prepare an exact change/migration/configuration proposal and obtain separate approval for this cloud target. No self-approved fixes, drop/recreate, reset, RLS disablement, generic grants or changes based solely on historical version. |

Provider signup/email/hooks/notifications and resource/rate use must be reviewed before B. Do not enable tests that send mail to real users or call unrelated external hooks. MFA secrets/tokens/credentials remain protected; user/actor IDs need only be stored in a controlled fixture manifest, not console logs. New Support identities inherit the real Support queue permissions; a fixture-filtered test harness does not create a narrower backend permission boundary. Owner must accept that scope or choose the separately isolated project option.

## 6. Synthetic scenarios and the remaining creation blocker

Required dedicated records: two approved new Support operators (plus an approved wrong-role test identity if needed), verified/AAL1/AAL2/expired/revoked session states for those identities only; assigned-to-A, unassigned and assigned-to-B synthetic cases; existing-schema event history with deliberate revision gaps and with/without note payloads to prove exclusion; no-history/missing case; dedicated retained-abuse policy states and invalid cursors.

Do not use the owner's existing Operations/Finance account or profile/staff rows. Do not manufacture policy approvals/durations, verification or enrollment evidence. Full retained-policy expiry/triage tests need separately approved policy data and permissible changes; missing-helper tests must **not** drop/change a shared helper in this populated development project. Keep that negative scenario in isolated doubles or a separately authorized disposable project until safely designed.

**Case setup is still BLOCKED:** `0019:sr_retention_dispute_admission` fires on open/investigating case INSERT/status changes. `sr_retention_admission` executes order_pair_units SQL even with null pair references. Cloud ownership/non-production status does not make that operation eligible. Do not use direct INSERT, old Support APIs, generic workflow_sample, replication role/trigger disablement, altered retention logic, fabricated closed cases or manual event-table write grants as a shortcut. A safe reviewed approved fixture mechanism is required before C/D, and permission alone does not relax the QR exclusion. A fresh project alone does not remove this trigger dependency either.

After eligible fixtures exist, keep live list tests on **queue=mine** for the dedicated new operator, or exact synthetic case_id for unassigned/all/other-assignee scope tests. Default/all/unassigned list queries can include unrelated existing cases; do not enumerate them. Use several actor-owned synthetic cases for cursor/filter tests. History targets only dedicated IDs. Missing-case UUID and actor-B404 tests do not require reading real accounts. No customer association, QR/order reference or private case content is needed.

## 7. Acceptance matrix and evidence required

| Area | Required actual evidence after the relevant approvals |
|---|---|
| Auth/email/MFA | Genuine provider-issued verified account/live session; signed and current provider AAL2 agree; unverified/wrong-role/AAL1/revoked/expired negatives on dedicated identities only. JWKS discovery alone is insufficient. |
| RLS/assignment | Restricted runtime role, explicit trusted actor context and actual policy enforcement; actor-A assigned/unassigned visibility, actor-B case denial, assigned-only history. Never test as migration/service_role. |
| Retained policy/fail closed | Installed definition/ACL plus authorized synthetic-policy scenarios; helper/dependency absence isolated from shared data. No inferred policy validity from a row count. |
| Projections/history | Exact closed DTOs; no customer/assignee/actor identity/note/description/pair/order/evidence content; content_available=false; no fabricated history. |
| Filters/pagination | Actual supported exact filters, stable keyset ordering/ties, actor/filter/purpose-bound cursor, stale history revision handling. Scoped synthetic records only. |
| Pair independence | Inspect deployed transitive definitions and an approved bounded nested-SQL/lock observation strategy under actual runtime/definer roles; application-level denylist/mock success alone is insufficient. No pair-row reads to prove absence. |
| Read audits/preservation | Approve the exact minimal audit writes and verify transaction behavior. Existing development records untouched; failure scenarios never mutate unrelated sessions/roles/policies. |

All44 prior isolated checks remain useful historical unit evidence; none was rerun or promoted to live acceptance here. No cloud acceptance result exists. Frontend integration requires actual acceptance evidence plus recorded governance admission for the three exact GET paths.

## 8. Existing project versus a separate cloud development project

**Current choice:** the confirmed existing development project is the proposed target for the bounded read-only audit A. Do not silently replace the owner's selection or create a new project.

**Safer for write-heavy/negative/disposable acceptance:** a separately approved fresh Supabase Cloud acceptance/development project avoids co-locating test staff sessions/cases/policy changes with the existing populated development records, makes resource ownership/cleanup clearer and can contain global failure scenarios. It needs separate project creation/configuration/cost and migration/identity/fixture approvals; do not clone real data or assume provider branching isolates users/settings. Neither a TEST_DATABASE_URL alias nor a different SQL login is that isolation. A separate project still requires the full migration audit and safe pair-free fixture design.

On the existing project, additive test users/grants/events/audits and quotas can affect shared development use even without deletes. Case/history audit records may be append-only or retention-bound; do not promise rollback/deletion cleanup. Record approved IDs and retention/cleanup plan before writes. No broad reset/delete/prune/role cleanup. No read-only operation here certifies that later write scenarios are safe. If protected fixtures/global dependency tests cannot be isolated appropriately, propose the separate project before B–D rather than altering existing development security.

## 9. Exact next action and approval boundary

Request authorization for **A only**: confirm project fhux…kzvq/fingerprint17e54a8be1b7; use its already configured credential for a short, TLS-verified, enforced-read-only catalog/installed-Alembic/security-definition audit, plus the separately enumerated public JWKS GET if approved. No customer/Auth/session/staff/policy/case records or domain counts, no pair processing, no API acceptance/audit writes, and no remote changes. Failure to connect/verify identity stops; no automatic repair or endpoint fallback.

The owner's development/test declaration is **not** remote-access approval. Do not run A until explicitly authorized. B–E, any new cloud project and frontend admission remain separate decisions. Docker Desktop/local Supabase workflow is stopped; the old local PostgreSQL cluster stays unchanged. No next phase started.

## 10. Work performed / documentation

Only local file/source/document inspection and redacted in-memory configuration comparisons were executed; no Supabase Cloud/public JWKS/Dashboard/Management API/DB connection, DNS/connectivity probe, installation or test suite. No local cluster connection or infrastructure change. Current plan derives non-production designation from explicit owner confirmation and historical facts from repository records, with their provenance and uncertainty retained.

Updated this plan, Phase9B acceptance status, the superseded local bootstrap proposal notice and the integration tracker. No application/handler/migration/frontend/environment or allowlist change. Historical local migration approval and staff runbooks do not authorize cloud changes. All three endpoints remain **NOT ADMITTED**.


## 11. Authorized read-only Cloud audit — actual results (2026-10-24)

The owner authorized the existing development/testing project fhux…kzvq, reference fingerprint17e54a8be1b7, for a TLS-verified metadata-only database audit and one public JWKS GET. This supersedes pending approval A above. No repair, migration, identity, fixture, MFA, application operation or frontend admission was authorized.

### Reviewed scope and connection safety

Compared the protected Auth HTTPS project host and runtime database login project suffix in memory against the approved reference fingerprint. Required the exact configured Supabase pooler hostname, port5432, database and runtime credential; no alternate endpoint/login or default settings. Owner confirmation establishes development intent; successful database-side identity verification remains blocked.

Prepared a fixed, reviewed query allowlist in ignored tmp/phase9-cloud-audit/audit.py: pg_catalog schema/column/extension/role/membership/ACL/RLS/policy/trigger metadata, selected function signatures/security/definitions without execution, and public.alembic_version.version_num only. No domain counts, Auth/user/session/staff/customer/case/order/payment/QR records, pg_authid or private signing material. The runtime login is not independently proven metadata-only; therefore only the reviewed static statements were eligible, never arbitrary SELECTs or application functions. A read-only transaction alone was not treated as sufficient.

Explicit connection settings: verify-full, installed Certifi trust bundle, explicit host/port/database/user, no inherited PG defaults, default_transaction_read_only=on, search_path=pg_catalog,10-second connection/statement timeout,2-second lock timeout and20-second idle-transaction timeout. The configured sslmode was overridden with verify-full. Planned BEGIN READ ONLY and own-connection TLS/read-only checks precede other catalog statements; no service lookup or insecure fallback.

The initial sandboxed connection attempts failed before database or HTTPS connection establishment. A network-permitted retry used the same reviewed settings. **Database certificate verification failed: OperationalError, no SQLSTATE. No database connection was established; no BEGIN, catalog query, migration query or function execution occurred.** Read-only enforcement and server identity could not be verified, so the database audit stopped. No alternate CA/host, weaker TLS or configuration change was attempted. Error messages were classified privately to avoid printing endpoint/login/credential details. The evidence does not identify whether the cause is a missing CA/intermediate or another validation problem.

### Findings

| Requested evidence | Actual result |
|---|---|
| Installed migration head/history | UNVERIFIED. Historical repository evidence remains0043_standalone_activation; this is not a freshly observed installed head. No migration metadata retrieved. Alembic revision rows alone would not constitute a complete execution ledger. |
| Supabase Auth schema readiness | UNVERIFIED: no table/column metadata or Auth records retrieved. |
| Extensions, required roles/memberships/grants | UNVERIFIED: configured role names are not privilege evidence. |
| Support/staff/account/abuse tables, RLS and policies | UNVERIFIED; neither existence nor enforcement acceptance established. |
| Authorization functions/owners/ACLs/search paths/triggers | UNVERIFIED; repository requirements are not installed-definition evidence. No application/security-definer function executed. |
| JWKS discovery | One HTTPS GET completed,200; verified TLS, trust_env=False, redirects disabled,64KiB bound, no Authorization/API-key header. Initial connection failure produced no completed HTTP request. No repeat discovery after success. |
| Public key metadata | One ES256 / EC / P-256 key, use=sig, key_ops=[verify], kid00c448d4-52cd-460d-97bb-c40c100d9d43. No private JWK fields observed. Public coordinates not logged/retained. |
| JWT compatibility | Discovery metadata matches backend/app/core/auth.py algorithm/curve/usage expectations. No issued token, signature/claims, email verification, session validity or signed/provider AAL2 tested. |
| Preservation | No existing records read; no QR records/functions/APIs or protected routes called; no migrations/writes/fixtures/identities/MFA; local PostgreSQL cluster untouched. |

No tests or Ruff were run for this documentation/audit task.44 isolated tests remain historical evidence only. Ignored local artifacts hold reviewed script and redacted result summary without credentials or application contents. No application code/environment/frontend/allowlist changed; Docker/local Supabase installation stays cancelled. All three Support Metadata endpoints remain **IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED**.

### Remaining prerequisites and exact next approval

Obtain authoritative Supabase database CA-chain/fingerprint and connection guidance for this same configured pooler target, preferably owner-supplied from the intended project's trusted Dashboard/provider channel. No credentials/private keys should be supplied in chat. Validate provenance, scope and hostname coverage locally; do not trust a certificate solely because an unverified server presents it. The current failure does not establish which trust correction is appropriate.

**Next approval request:** authorize obtaining/verifying provider certificate material if remote retrieval is needed, staging an audit-only trust file without changing application/system trust or infrastructure, and retrying the same reviewed metadata allowlist against the same project/endpoint with verify-full and enforced read-only access. No weaker TLS, alternate project, migrations or grants. Do not repeat JWKS discovery: the single completed GET is already used. Stop again if verification fails.

After a successful catalog audit, compare installed/source definitions before proposing any repair. Separate approvals remain necessary for genuine dedicated email-verified Support identities, real MFA/session assurance, safe synthetic assignment/history/abuse fixtures, restricted-role RLS execution and the metadata GETs' minimal audit writes. Section6's case-creation/retention QR dependency remains unresolved; this attempt supplied no deployed-schema evidence. No frontend admission or next phase started.


## Phase 9 TLS trust preparation and same-target retry (2026-10-24)

**STOPPED: verify-full still fails; no database audit executed.** This entry supersedes the prior request for permission to stage an audit trust file: the owner explicitly authorized that preparation and same-target metadata retry. No JWKS request was repeated.

### Diagnosis and independently trusted source

Original retained evidence: psycopg OperationalError, TLS certificate-verification category, no SQLSTATE. The previous script intentionally discarded raw libpq messages; a more specific original root cause cannot be reconstructed from that artifact. Configuration inspection confirmed an explicit pooler hostname/port5432 and verify-full with the installed Certifi CA file, rather than automatic Windows trust. The configured URL's sslmode is not forwarded; the audit explicitly strengthens it to verify-full. Runtime versions: psycopg3.3.6, libpq18.4 (180004), Python ssl OpenSSL3.5.9. Python's ssl version is not asserted to be libpq's linked OpenSSL version. No evidence establishes unsupported client behavior or a particular hostname mismatch.

Official guidance reviewed over HTTPS: [Supabase SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement), [connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres), and [PostgreSQL verify-full](https://www.postgresql.org/docs/17/libpq-ssl.html). Supabase identifies the project's Dashboard Database Settings / SSL Configuration as the source for its database CA certificate. No Dashboard/Management API access or arbitrary CA download occurred.

Inspected Windows ROOT (35 entries) and CA (3 entries) stores. Prepared a dedicated bundle from **21 Windows ROOT certificates already trusted for TLS server authentication**, filtered to CA basic constraints, current validity and positive serial numbers. Windows CA/intermediate entries, server-presented certificates, JWKS keys and newly created CAs were not imported as trust anchors. This independently establishes local OS trust provenance; it does not assert that those roots validate the Supabase chain. Export parsing warned about legacy nonpositive serial numbers; such certificates were excluded. System and application trust settings were unchanged.

Trust file: `E:\Projects\SafeReturn\tmp\phase9-cloud-audit\windows-roots.pem`, ignored by Git. SHA256 `9429df27238c6854038c3bed707c52e5726e30f02e5e05dc0cd06f0003a37245`. Manifest and reviewed retry script remain alongside it, outside version control. Checked the file ACL, disabled inherited grants and replaced content-write grants with read access; public certificate reads are allowed to local users, with no ordinary content-write grant. The owner can still manage its ACL. The retry pins the bundle checksum before networking. Initial local ACL-read failures were corrected using file-scoped read grants only; those attempts stopped before any remote connection. No system-wide ACL/trust change.

### Same-target result and scope preservation

Revalidated approved fhux…kzvq / reference fingerprint17e54a8be1b7 against the protected Auth host and configured database login project suffix, exact configured pooler host, port and database. Used the same runtime credential; no migration/test login, alternate hostname, insecure mode or credential fallback. The runtime credential is not independently certified metadata-only, so the reviewed static catalog allowlist remains mandatory. The retry excludes HTTP/JWKS code entirely and narrows function inspection to signatures/security attributes, without executing application functions or retrieving function bodies.

One remote retry reached TLS verification with the independently sourced Windows bundle and **failed: OperationalError, no SQLSTATE; safe client detail: certificate verify failed**. No verified TLS/database session, BEGIN, read-only setting check, catalog query, Alembic query or application function execution occurred. No raw connection string, password or libpq error was printed. No further remote attempts followed this failure.

The available error does **not** distinguish a missing trusted issuer, incomplete presented chain or another validation error. Correct server chain and hostname compatibility remain unverified. Neither an unsupported client nor a specific hostname mismatch is proven. Do not treat the OS bundle as a successful repair or disable verification to diagnose further.

| Acceptance metadata | Result after retry |
|---|---|
| Actual installed migration head/history | UNVERIFIED; historical0043_standalone_activation is still historical only. |
| Required Auth schemas/tables/columns/MFA structure | UNVERIFIED. |
| Baseline/runtime roles, memberships and grants | UNVERIFIED. |
| Support/staff/account/abuse table structure, RLS and policies | UNVERIFIED; no RLS acceptance result. |
| Authorization function signatures/security attributes | UNVERIFIED; no application/security-definer function executed. |
| JWT/JWKS | Previous verified ES256/P-256 discovery retained; no new GET or token/auth acceptance. |

No existing application/Auth/session/customer/case/order/payment/QR records read. No migrations, writes, role/grant/RLS/schema changes, identities, MFA, fixtures, protected APIs or QR operations. No local PostgreSQL cluster connection/change, application code change, Phase4 Orders change or frontend/allowlist change. No tests/Ruff run; earlier44 isolated tests remain historical. All three endpoints remain **IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED**.

### Exact missing information and next recommended action

The owner must supply the **public database CA certificate downloaded from the intended development project's authenticated Supabase Dashboard → Database Settings → SSL Configuration**, plus authoritative confirmation that the configured session-pooler hostname is the intended endpoint. Do not supply passwords, service keys or signing keys. The certificate must have traceable provider provenance; a certificate copied from the failed connection is insufficient. No new root or arbitrary downloaded certificate will be trusted.

After this missing evidence is available, validate the certificate's CA attributes/validity/fingerprint and endpoint guidance locally before considering another verify-full attempt. The current task stops here; no repair, installation or alternative project is proposed. Dedicated genuine verified Support identities/MFA, safe synthetic cases/assignment/history/abuse scenarios, resolution of the retention-trigger QR fixture dependency, real restricted-role RLS/auth acceptance and approved metadata-GET audit writes remain subsequent prerequisites under their separate scopes. No frontend admission.


## Phase 9 — requested live check after offline frontend completion (2026-10-24)

After completing and documenting offline frontend work, the owner confirmed the project was resuming and requested the limited live check. Reused the reviewed metadata-only script, pinned Windows CA bundle checksum and exact previously configured session-pooler hostname/port/database/runtime login; checked approved reference fingerprint17e54a8be1b7 (fhux…kzvq). Explicit verify-full, no inherited PG defaults, short timeouts and planned read-only/catalog allowlist were retained. No alternate host/credential or TLS downgrade, application function execution or JWKS request.

**Actual result: BLOCKED at TLS certificate verification**, OperationalError, no SQLSTATE, safe detail `certificate verify failed`. One same-target remote attempt; no verified database connection, BEGIN, read-only confirmation, migration/security metadata query or application API call. Raw errors/credentials were not printed. The owner's resumption statement does not independently establish project readiness and does not resolve/prove the cause of the TLS error.

Actual migration head, Auth schema readiness, baseline/runtime roles/grants/RLS/policies/function attributes remain **UNVERIFIED**. Historical0043 and previous public JWKS metadata are not promoted to fresh database/auth acceptance. No cloud data or local-cluster changes, identities, MFA, fixtures, migrations, Support/Finance/Orders/QR requests or frontend admission. Frontend remains **READ-ONLY FRONTEND IMPLEMENTED — LIVE INTEGRATION DISABLED — ACCEPTANCE PENDING**; all three APIs remain **NOT ADMITTED**.

Next missing evidence remains the public database CA certificate from the intended project's authenticated Dashboard Database Settings / SSL Configuration and authoritative confirmation of the configured pooler endpoint. Validate provenance/CA attributes/validity/hostname guidance before any future verify-full retry; do not trust server-presented material automatically or repeat JWKS discovery. Genuine verified Support/MFA synthetic identity and safe fixture provisioning, retention-trigger QR dependency resolution, controlled RLS/auth/API acceptance including approved minimal audit writes, recorded exact endpoint admission and reviewed server-controlled activation remain separate prerequisites. No further infrastructure troubleshooting or Phase10 was started.


## Phase 9 — supplied CA verification and read-only catalog results (2026-10-24)

**CLIENT TLS VERIFIED; SECURITY CATALOG AUDIT EXECUTED; CURRENT MIGRATION REVISION BLOCKED BY TABLE PRIVILEGES.** This supersedes the earlier generic-CA TLS failures. It is not full database/RLS/auth/API acceptance. All three endpoints remain **NOT ADMITTED**; frontend remains **READ-ONLY FRONTEND IMPLEMENTED — LIVE INTEGRATION DISABLED — ACCEPTANCE PENDING**.

### Certificate and endpoint verification

Owner-supplied file `E:\Projects\SafeReturn\tmp\phase9c-local\supabase-db-ca.crt` exists (1367 bytes), is PEM containing one public X.509 certificate and no private key. Subject=issuer: `CN=Supabase Root 2021 CA,O=Supabase Inc,L=New Castle,ST=Delware,C=US`. RSA2048; SHA256-with-RSA self-signature verified. Valid2021-04-28 10:56:53 UTC through2031-04-26 10:56:53 UTC. BasicConstraints CA=true, keyCertSign/crlSign=true, no restrictive EKU. CA material is suitable as a trust anchor; actual server purpose/chain/hostname acceptance is determined by the TLS handshake, not merely these fields or a file name.

Certificate DER SHA256: `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`. Staged dedicated trust file: `E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem`; normalized PEM SHA256 `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`, pinned before each connection. Inspected owner-only ACL on source without modifying it. Staged file is Git-ignored with explicit read-only user/system/admin ACLs and no inherited content-write grants. No application/system trust, server certificate, environment or local cluster changes.

Trust provenance: explicitly owner-supplied certificate out of band, **not a root copied from the failing server**. Self-signature and CA constraints do not independently prove provider provenance. An attempted public download at `https://supabase.com/downloads/prod-ca-2021.crt` returned404 over verified HTTPS (no redirect); **no official-download fingerprint match is claimed**. [Official Supabase guidance](https://supabase.com/docs/guides/platform/ssl-enforcement) describes the authenticated Dashboard SSL Configuration CA download and verify-full workflow; that documentation does not certify this local file's fingerprint. No arbitrary third-party certificate, JWKS key or newly created root was trusted.

Exact configured hostname remains `aws-0-ap-northeast-2.pooler.supabase.com`, port5432: **Supavisor session pooler**, not a direct db.<ref>.supabase.co endpoint. The approved project reference fhux…kzvq / SHA256 prefix17e54a8be1b7 matches the protected Auth HTTPS host reference and database login tenant suffix in memory. Used the same explicit configured database/runtime login, never an alternate endpoint or privileged credential. A shared pooler certificate authenticates its hostname; project routing is also bound by the configured project's authenticated tenant login.

### Actual connection and read-only execution

Psycopg3.3.6/libpq18.4 connected successfully with explicit **sslmode=verify-full** and the supplied CA. This validates the presented server chain and exact configured pooler hostname relative to the owner-supplied trust anchor. Libpq client ssl_in_use=true was checked separately. No hostname bypass, weaker TLS or JWKS request. Success is consistent with the prior generic bundles lacking the provider root; it does not prove pausing was the cause of prior failures.

The first successful connection stopped at the old audit assertion on pg_stat_ssl. The ignored audit script had conflated client-to-pooler TLS with the database-side session. Corrected that local check to require libpq client TLS separately, retaining pg_stat_ssl as distinct metadata. Subsequent audit confirmed PostgreSQL17.11 and **transaction_read_only=on** after explicit BEGIN READ ONLY. Connection/statement/lock/idle timeouts, pg_catalog search_path, sanitized PG defaults, ROLLBACK and connection close remained enforced.

**Separate transport finding:** database-side pg_stat_ssl returned ssl=false, protocol/cipher null. Client-to-Supavisor TLS is verified; pooler-to-database TLS/end-to-end encryption and provider SSL-enforcement settings are **not** accepted by this result. Provider topology/enforcement needs a separately scoped review before acceptance. No enforcement change/reboot is authorized or performed.

Every statement was a reviewed catalog query; no arbitrary SELECT or application function execution. The selected login is not independently catalog-only, so the fixed allowlist supplements read-only mode. Queried only role flags/membership, schemas/classes/columns/extensions/ACLs/RLS/policy expressions, trigger names/enabled flags and selected function signatures/security attributes. Policy text was not evaluated against rows; function bodies were not retrieved. No SET ROLE, application/SECURITY DEFINER/volatile application function invocation or privilege changes.

### Actual metadata findings

| Area | Observed result and limits |
|---|---|
| Managed Auth | auth schema; users,sessions,mfa_factors,mfa_challenges,mfa_amr_claims exist, owned by supabase_auth_admin, RLS enabled. Required users id/email_confirmed_at/deleted_at/banned_until/is_anonymous/created_at and sessions id/user_id/not_after/aal/created_at types match source (aal=auth.aal_level). Structural readiness only: no identities/sessions/factors or values read. |
| Support dependencies | support_cases,support_case_events,staff_roles,audit_events,abuse_reports,abuse_intake_policies,account_security_state all exist, postgres-owned, RLS=true/FORCE RLS=false. No records/counts read. |
| Baseline/runtime roles | anon,authenticated,service_role,authenticator,supabase_auth_admin,safereturn_api,safereturn_api_login present. API role NOLOGIN/NOINHERIT, login LOGIN/NOINHERIT; neither has superuser/CREATEROLE/CREATEDB/replication/BYPASSRLS. Selected login flags likewise nonprivileged. Login is a non-admin member of safereturn_api. Provider service_role has BYPASSRLS and was not used. |
| Runtime ACLs | public USAGE; support_cases SELECT/INSERT/UPDATE; support_case_events SELECT; staff_roles SELECT; audit_events SELECT/INSERT. Protected Auth/abuse/account-security tables expose no direct API-role table grants in inspected ACLs; helper-mediated access remains required. Read-only UI does not imply a read-only general runtime SQL role. |
| Support RLS | Base SELECT/INSERT/UPDATE policies and restrictive SELECT sr_abuse_case_scope using sr_abuse_case_readable(id) exist. Base SELECT includes opener or Support/security_admin/superadmin: endpoint's explicit Support guard and assigned/unassigned predicate remain essential; base RLS alone is not the full endpoint assignment boundary. |
| Events/staff/audit RLS | sr_case_event_read requires Support plus a parent case assigned to sr_actor_id(); staff SELECT is actor-limited; audit SELECT/INSERT and worker INSERT policies present. Existence is not enforcement acceptance. |
| Authorization signatures | sr_actor_id()→uuid; sr_mfa()→boolean; sr_is_staff(text[])→boolean; sr_account_session_state(uuid)→TABLE(email_verified boolean,mfa_active boolean); sr_account_epoch_allows(uuid,timestamptz)→boolean; sr_account_lock_key(uuid)→bigint; sr_abuse_case_marker(uuid)→boolean; sr_abuse_case_readable(uuid)→boolean; sr_abuse_policy(uuid,integer)→jsonb; sr_abuse_gate(boolean)→void. |
| Function security | Inspected functions postgres-owned with search_path=pg_catalog. sr_is_staff/abuse marker STABLE SECURITY DEFINER; session/epoch/readability/policy helpers VOLATILE SECURITY DEFINER. Explicit API EXECUTE grants exist on these required callable helpers; no PUBLIC EXECUTE grant observed in their ACLs. Gate/lock/trigger owner-only grants reflect nested owner-context usage, not automatically missing runtime grants. None executed; no body/source equivalence established. |
| Triggers | Enabled support retention admission/abuse guard, append-only event/audit and safe audit JSON triggers present. sr_retention_dispute_admission is a trigger using sr_retention_admission(), not a missing standalone function. Existing fixture QR dependency remains unresolved; no trigger fired. |
| Extensions | pg_stat_statements1.11,pgcrypto1.3,plpgsql1.0,supabase_vault0.3.1,uuid-ossp1.1 installed; no extension changed/invoked. |
| Installed migration head | **UNVERIFIED.** public.alembic_version exists with RLS=true/FORCE=false. Protective assertion stopped before reading version rows. Catalog-only follow-up confirmed no policies and SELECT=false for both selected login and safereturn_api. No version_num SELECT, credential fallback or grants. Historical0043_standalone_activation remains historical only. |

This is a **partial metadata audit**, with verified TLS/read-only security catalogs and a precise least-privilege migration-version blocker. The ignored audit result's assertion at migration_table is not a TLS failure or a fully successful audit. Follow-up ACL/policy catalog inspection completed and rolled back. Observed features align with0003/0005/0021/0030/0035 requirements; installed migration/source equality and actual policy behavior remain unverified.

### Preservation and next safe action

No customer/user identity/session/case/order/payment/QR records, domain counts, tokens/private signing material read; Auth column names/types are catalog metadata only. No application/security/QR function, protected/quarantined API, migrations/writes/role/grant/RLS/schema changes, identities/MFA/fixtures, local PostgreSQL connection/change or frontend admission. No new JWKS request. No application code change or unrelated test/Ruff/typecheck run for this documentation/read-only task. Frontend gate rechecked and still returns false. No Phase10.

Next: obtain current Alembic revision from an owner-provided trusted Dashboard read-only result, or separately authorize a bounded version-only read using an appropriate existing credential reviewed for that exact operation. **Do not grant runtime access just for this audit or silently switch to migration/service-role credentials.** Separately review provider SSL enforcement/topology for database-side ssl=false, without changing provider settings.

Remaining acceptance prerequisites: verified installed/source compatibility; genuine dedicated email-verified Support identities and real MFA/session assurance; safe synthetic assignment/history/retained-abuse cases (retention-trigger QR setup blocker unresolved); actual restricted-role RLS/fail-closed/projection/QR-independence checks; explicit permission for metadata GETs' minimal audit writes. Then exact recorded endpoint admission and reviewed server-controlled activation. Structural Auth tables, policy presence, signatures and TLS success do not satisfy those gates. All three metadata endpoints remain **NOT ADMITTED** and live UI remains disabled.


## Phase 9E — Cloud security verification and acceptance preparation (2026-10-24)

**ASSESSMENT COMPLETE; CURRENT MIGRATION HEAD UNVERIFIED; UPSTREAM TLS AND FIXTURE DESIGN GATES OPEN.** This entry is the latest interpretation of previous audit evidence. Earlier Phase9B wording about no remote audit is historical; the supplied-CA catalog audit did execute, but genuine Auth/MFA/RLS/API acceptance did not. All three APIs remain **NOT ADMITTED**; the server-only frontend gate still returns false. No Phase10.

### 1. Evidence reviewed and migration status

Reviewed this plan, Phase9B acceptance report and progress tracker; backend/alembic.ini and alembic/env.py; docs/LOCAL_FRONTEND_BACKEND_PHASE8.md; .github/workflows/quality.yml; approved API Contract, Technical Design and Security/Privacy specification; app/core/auth.py, api/auth.py, db/runtime.py, services/support_metadata.py; migrations0005/0019/0021/0030/0035; ops/STAFF_PROVISIONING.md; isolated auth/metadata tests and existing integration rehearsal fixtures. Prior audit results were reused, not re-executed.

The migration framework is Alembic. Its env.py chooses the configured migration credential when invoked normally, excludes managed auth from autogeneration and can execute migrations. Therefore do not invoke a general Alembic/health/integration command to discover the revision in this task. The historical Phase8 deployment report records22 committed migrations0022–0043 and a fresh read-only confirmation of0043_standalone_activation at that deployment. It is legitimate **historical deployment evidence**, not a current same-target revision read or a tamper-evident deployment ledger. It does not authorize reuse of privileged credentials now. Repository head alone is not installation evidence.

Search of documentation/operations/output/workflow metadata found no newer approved current-target revision artifact; the CI workflow runs offline preparation/typecheck/build, not a Cloud migration deployment or signed installed-head attestation. No approved Dashboard connection or administrative metadata view is available in this session. Existing audit catalog evidence proves public.alembic_version is RLS-enabled, has no policies, and SELECT is denied to both selected runtime login and safereturn_api. Do not change those grants, SET ROLE, silently switch credentials or infer the revision from table presence. **Current installed head remains UNVERIFIED.**

Acceptable missing evidence: a dated owner-supplied Dashboard read-only result for `SELECT version_num FROM public.alembic_version`, bound to project fhux…kzvq / reference fingerprint17e54a8be1b7, or separate authorization for a tightly bounded read using a reviewed existing migration/administrative credential. Record zero/multiple rows or permission denial honestly; do not stamp/repair/upgrade. Full migration execution history is distinct from Alembic's current revision table.

### 2. Supavisor TLS interpretation and architecture compatibility

| Connection/evidence | Conclusion |
|---|---|
| Audit client → exact configured aws-0-ap-northeast-2.pooler.supabase.com:5432 | Previously verified chain/hostname with sslmode=verify-full, owner-supplied public CA and client libpq SSL=true. No need to repeat. Shared Supavisor session pooler, not direct PostgreSQL. |
| Supavisor/proxy → PostgreSQL backend observed by own-session pg_stat_ssl | Previously ssl=false and protocol/cipher null. PostgreSQL reports the backend connection, not the terminated client socket. This is a real observation of no PostgreSQL SSL on that backend session, not evidence that the external client used plaintext. |
| Actual tenant upstream_ssl/upstream_verify/upstream_tls_ca and managed SSL-enforcement setting | Not retrieved; no Management API/Dashboard access is newly authorized here. No configuration attestation of upstream TLS, network isolation or other compensating protection. |
| End-to-end transport acceptance | **NOT ESTABLISHED.** A potential provider-internal network mechanism cannot be presumed from this observation or substituted for the approved TLS requirement. |

Authoritative references:

- [PostgreSQL17 pg_stat_ssl](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-SSL-VIEW): the view describes a PostgreSQL backend's connection.
- [Official Supavisor tenant configuration](https://github.com/supabase/supavisor/blob/main/docs/configuration/tenants.md): client SSL enforcement is separately configurable from upstream_ssl/upstream_verify/upstream_tls_ca. This explains how verified client TLS can coexist with a non-SSL PostgreSQL connection. It does not attest the hosted project's actual tenant settings.
- [Supabase SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement): managed SSL enforcement governs both client-to-pooler and pooler-to-Postgres; changing it can reboot the database. No setting was changed or write proposed as part of this phase.

**Interpretation:** the proxy architecture explains the two observations mechanically. It does not establish that plaintext upstream is universally expected, approved, or compliant. When managed SSL enforcement is enabled, official documentation supports expecting TLS on both legs. We have not observed the setting, deployment version, routing or pool lifecycle needed to explain this tenant specifically. Do not diagnose it as disabled enforcement solely from one historical backend row.

Security/Privacy Specification section12.1 explicitly requires HTTPS/TLS for database connections; Technical Design identifies Supabase PostgreSQL as the authoritative backend. No approved exception for an unencrypted Supavisor-to-database leg was found. Current evidence is **insufficient to sign off architecture compliance**. Obtain a dated, redacted Dashboard SSL-enforcement view or separately approved metadata-only Management API GET for this exact project, plus provider clarification of upstream TLS verification/routing if the setting is enabled despite the observation. No private network/host/packet attestation is invented. Do not change SSL settings, switch endpoints, downgrade validation or accept an exception without the accountable security owner.

### 3. Genuine identity/MFA plan — not provisioning approval

Minimum proposed identity set (all new, individually controlled owner-approved test mailboxes; no existing accounts):

| Handle | Required state and purpose |
|---|---|
| P9E-A | Verified nonanonymous email; explicit unrevoked Support only; genuine provider session. Exercise initial AAL1 denial, then real TOTP enrollment/challenge/verification and signed+live-provider AAL2. Own assigned cases. |
| P9E-B | A second independently controlled verified Support operator with genuine AAL2; owns the other-assignee case. Tests cross-assignment/cursor isolation without borrowing another existing staff account. |
| P9E-C | New verified nonstaff account, genuine AAL2 but no Support grant; role-denial control. A no-role denial does not prove every privileged non-Support role is denied live: optional dedicated wrong-role identities/grants need separate least-privilege approval. |

Provider user UUIDs are assigned by Supabase, never fabricated or preinserted. Proposed mailbox local parts phase9e-a/phase9e-b/phase9e-c need an owner-controlled real test domain and named human custodians; no invented `.invalid` inbox can prove email verification. New accounts/grants must follow the named approver/custodian/executor requirements in ops/STAFF_PROVISIONING.md. That runbook is not a ready authorized grant writer; its authority/receipt/role-version/concurrency gates remain unresolved. No SQL role insertion or owner-account reuse is selected as a shortcut.

Before creation review signup hooks, profile triggers, notification/outbox/provider actions, SMTP/callbacks/rate limits and cleanup dependencies. Only approved test inboxes may receive mail. Use genuine signup/confirmation; do not set email_confirmed_at directly, weaken email settings or use an auto-confirm flag as verification evidence. Keep passwords/tokens/TOTP seeds/otpauth material/backup codes out of chat, logs, browser localStorage and committed manifests.

[Official TOTP flow](https://supabase.com/docs/guides/auth/auth-mfa/totp) uses first-factor sign-in, enroll, challenge and verify, then a current AAL2 session; [enrollment reference](https://supabase.com/docs/reference/javascript/auth-mfa-enroll) notes that verifying a factor logs out other sessions. Limit this impact to each new test subject. Human custody of its authenticator is required; no mock seed/session row or minted JWT. Existing MFA screens may be evaluated only under separately authorized identity/MFA scope; do not enable Support integration.

Backend evidence required: JWTVerifier validates issuer/audience/signature/type/session claims; authorize() combines signed AAL2 with sr_account_session_state's current provider session MFA; require_staff() requires verified email and explicit current Support; final reauthorization precedes response commit. API transactions use safereturn_api and transaction-local trusted actor/MFA context. A provider SDK's reported AAL alone is insufficient.

Negative-session plan: AAL1, missing/expired token, real subject-only logout/revocation, revoked Support grant, provider ban and account-security disabled state. Each session/role/lifecycle mutation needs explicit approval; use only dedicated accounts, perform irreversible/revocation tests last, and never restore a role/state implicitly. Provider deletion may be prevented by case/event FKs and is not a planned shortcut. If provider email-confirmation policy prevents an unverified account obtaining a session, record that; do not weaken provider configuration or fabricate an unverified staff JWT to claim live coverage. Deleted/epoch/lifecycle negatives without an approved safe writer remain blocked, even though isolated tests cover their logic.

### 4. Proposed minimum fixture manifest — no records created/reserved

Namespace: SafeReturn Phase9E acceptance v1, recorded in a future protected local manifest, not a new schema/table/column. IDs below are deterministic UUIDv5 planning identifiers; they have **not** been checked for collision or reserved in the database. All cases must have no customer/order/pair reference, no real content and approved synthetic provenance. Null references do not make insertion safe; see section5.

| Planned case UUID | Scenario |
|---|---|
| c90f3faa-d32c-579c-b5c0-a567ded5371c | A-assigned authorized case with safe recorded history; can also exercise valid dedicated abuse-policy visibility. |
| ab21415b-760c-5c2d-9782-d715dadc2ec3 | Unassigned case; metadata allowed, history404. Tests queue=mine omission and exact-ID unassigned scope. |
| 30a99c61-fa5c-5c9e-b3a2-c167b3288eae | B-assigned case; A list/detail/history must conceal it, B positive control. This supplies the unauthorized queue/other-assignee scenario without an extra case. |
| ecb5fe4b-342a-59c9-a4f9-c212f0053feb | A-assigned no-history case; empty page, no fabricated creation event. The future fixture design must explicitly justify the valid no-history state. |
| 4294248a-7a2c-5c68-98e3-6255abb96e37 | A-assigned restricted abuse case under a separately approved expired/revoked policy; omitted from list and concealed404 on detail/history. |

Missing-case probe candidate f82cc6f7-5cb7-5775-91b4-0d8c3b192ad7 is **not a record to create**. Establish absence only through a future approved exact-ID fixture preflight; otherwise it cannot prove missing-case behavior. Invalid-case probe is a syntactically malformed ID, not an existing account/record lookup.

Safe event candidates:05248517-663a-56e8-ade1-9dc129830ed4 (revision4) and97719ca1-bf16-533a-8272-a9c6e839e3d4 (revision2), linked only to the A fixture, actor FK only to approved new A/B UUIDs. Actual producer/revision semantics must be approved; do not insert arbitrary event rows through widened grants. Deliberate revision gaps prove the UI does not infer events. Any note-projection test uses approved synthetic encrypted text only, never real notes, and requires a reviewed encryption/writer path. Event IDs/revisions/types/statuses/priorities/timestamps must satisfy the real contract.

Policy planning IDs cdaa033c-6230-5b7b-a33f-f8fd96e1005f (valid),4ee715c1-40a2-5435-8a4c-c7292dcb3edb (expired/revoked),d7ce62f0-5672-5fc6-aae4-150ddc6b6330 (triage-off). Bodies/hashes/version/approval/retention/effective/expiry values require real security governance; none are invented or copied from existing records. Each abuse report/event requires its own manifest ID and approved schema mapping before execution; no runnable manifest exists yet. Policy scope must be dedicated and must not change a shared current policy merely to get a negative test.

Optional extensions for independent policy failure branches:455d933f-cfbb-5234-8ef2-3d9b188c4db1 triage-off case and12cb510a-10e6-5cdb-8c8e-a5645712b815 report/case-retention-expired case. Approve only if needed; the five core cases alone do not establish every policy/retention branch. Missing-helper fail-closed testing must remain in isolated doubles or a separately authorized disposable environment; never drop/rename/revoke shared helpers in the populated development project. No abuse-intake endpoint is implied.

### 5. Fixture safety/retention verdict

**NO EXISTING APPROVED PAIR-FREE INSERTION MECHANISM FOUND.** backend/alembic/versions/0019_retention_recovery.py:193 defines sr_retention_admission; line210 contains the order_pair_units query for support cases; line228 installs the open/investigating INSERT/status/reference trigger. Even NEW.pair_id=NULL reaches that SQL statement. Source inspection is enough to block using it; no pair query was executed to test it. Prior live catalog evidence confirmed that trigger is enabled.

Existing integration/test_support_cases.py uses workflow_sample, synthetic provider session/JWT state and legacy Support routes; pg_rehearsal and commerce/identity fixtures create schemas/roles and excluded order/pair/QR data. Integration auth migration tests can execute upgrades; auth guard tests depend on those rehearsal fixtures. They are not eligible genuine Auth or pair-independent setup/cleanup mechanisms and were not run. Isolated test_auth.py/test_support_metadata.py remain useful synthetic evidence, not live acceptance.

Direct INSERT, old Support creation, temporarily closed/resolved fake cases, DISABLE TRIGGER, replication-role tricks, RLS changes, widened event INSERT grants, disabled retention or forged sessions are rejected. A fresh Cloud project alone does not remove this trigger dependency. **Fixture provisioning needs separate architecture approval for a genuinely pair-independent creation/history/policy path preserving retention, ownership and authorization safeguards; design review precedes implementation and execution.** The plan is a reviewable scenario/identity plan, not an executable or safety-approved fixture bootstrap.

### 6. Controlled acceptance matrix — future approval only

| Area | Required test/evidence |
|---|---|
| Identity/auth | Provider-issued genuine sessions; verified email, nonanonymous/active/unbanned account, explicit current Support, signed and provider AAL2 agreement; controlled negative states above. No API key as bearer or service-role bypass. |
| Queue/API assignment | Use A queue=mine and exact planned IDs; A assigned positive/unassigned metadata positive/B case404; history only A-assigned. Default/all/unassigned lists can expose unrelated data and must not be exercised broadly in the shared project. Use exact case_id filters where necessary. |
| RLS | Use restricted runtime role with server-derived verified context, never migration/service_role. Test own staff visibility, assigned-only event policy and restrictive abuse scope using only manifest IDs. Base support_cases RLS is broader than endpoint assignment; do not falsely expect it alone to conceal other-assignee cases from a Support SQL actor. API predicate and RLS layers must both be assessed. |
| Retained abuse/fail closed | Valid policy visible; separately approved expired/revoked/triage/retention negatives concealed. Missing helper503 in a safe isolated environment. No shared policy tampering or invented validity attestations. |
| Projections/errors | Exact closed list/detail/history fields, content_available=false, no descriptions/notes/actor/customer/pair/order data, unauthorized401/403, missing/out-of-scope404, invalid filters/cursor400/422, history revision409, no-store/redacted failures. |
| Pagination/rechecks | Actor/filter/purpose-bound opaque cursors, ties/page bounds and fresh visibility; exact supported filters only. Controlled revision-change/final-role-recheck scenarios require approved synthetic mutation paths, not legacy APIs or changes to existing cases. |
| Audits/independence | Three metadata GETs insert minimal support.metadata.* audits. Explicit write authorization is required even for GET acceptance. Verify atomic commit/rollback and safe audit JSON. Review deployed transitive source plus a bounded nested-SQL/lock observation method; direct SQL denylist success does not prove nested definer independence. No pair-record reads to prove absence. |

No existing broad test command is approved for these scenarios. Prepare a scoped harness only after environment/identity/fixture approvals, review all setup/teardown, enforce exact paths/IDs and fail on any unexpected request. Any packet/query trace must exclude unrelated identity/query payloads. Shared global-helper/concurrency failure scenarios belong in a separately approved isolated target if safe scoping is impossible.

### 7. Isolation, idempotency and cleanup

Proposed manifest path `tmp/phase9e-acceptance/manifest.json` (not created this phase): project reference fingerprint, run/approval reference, purpose, proposed case/event/policy IDs, actual provider user/factor/session identifiers when legitimately provisioned, hashes of approved fixture payloads, write receipts/audit links, lifecycle state and retention/cleanup decisions. Protected local ACLs; no passwords/tokens/TOTP secrets/key material. Use this manifest rather than a made-up database namespace column.

Setup must check only exact manifest-owned IDs under later explicit read scope, abort on collision or unmatched provenance, and never adopt/update a preexisting account/case. A retry resumes only a previously committed manifest step with matching expected state; no broad upsert, list-all-users discovery, suffix-based deletion, reset or silent duplicate signup. Controlled test inbox routing must be approved before any email/provider hook.

Cleanup is **not currently executable**. support_case_events are append-only and reference cases/actors with ON DELETE RESTRICT; abuse evidence/policy references and audit retention also constrain removal. Do not promise DELETE-by-ID alone is permitted or idempotent. Each record is identifiable by the exact manifest ID plus approved provenance, but removal additionally requires an approved retention-compliant mechanism. New auth user deletion may fail because events reference that actor. Closing a case does not delete its history or authorize erasure.

Plan approved expiry/retention and subject-only session/grant revocation with named ownership, then retain minimal synthetic evidence until a reviewed removal mechanism is available. Disable/revoke actions are future mutations requiring dependency review/approval; none are run now. Physical deletion, if ever approved, must follow FK/append-only/retention rules, exact expected-state/manifest scope and a recorded absent-or-owned retry rule. No trigger bypass/cascade cleanup, broad DELETE, real data pruning or automatic teardown-on-failure. If policy requires immediate disposal, choose a separately authorized disposable project with a documented destruction/retention plan; do not silently replace the selected development project or clone its real records.

### 8. Exact approvals and next executable step

**Next narrow approval request (not executed):** authorize one version-only read through the already configured migration credential, solely against the same development project fhux…kzvq/fingerprint17e54a8be1b7 and exact verified pooler endpoint, using the pinned supplied CA, verify-full, sanitized explicit connection settings, strict timeouts and BEGIN READ ONLY. Reviewed payload is `SELECT version_num FROM public.alembic_version`, preceded only by own-connection/transaction metadata checks and followed by ROLLBACK/close. No Alembic runner, catalog expansion, application functions/data, grants, role changes, migrations or writes. Stop on any identity/TLS/read-only/permission failure. This credential is privileged and therefore **requires separate authorization**, unlike re-reading local deployment records.

For transport, preferred no-agent-credential path is owner-provided dated/redacted Dashboard SSL-enforcement evidence bound to the same project. Alternative separate approval: exactly one read-only Management API GET `/v1/projects/<approved-ref>/ssl-enforcement` through an approved existing account/channel, no token in chat/logs, no auth-user/session listing and no PATCH/PUT/reboot. Do not assume such an authenticated channel/token is available. Provider clarification may be required if settings and observations disagree.

Subsequent approvals are separate: (a) architecture-only design for pair-independent retention-safe fixture setup/history/policy handling and cleanup; (b) named authority/custodians/test inboxes, scoped genuine identity/email/MFA/Support grant provisioning with notification/hook review; (c) concrete fixture manifest/writer/retention plan after architecture approval; (d) exact runtime API/RLS acceptance, dedicated-state mutations and audit writes; (e) governance admission and server-controlled frontend release only after acceptance. No blanket approval or scope transfer from older local/Cloud tasks.

### 9. Work actually performed and stop state

Local source/document/log-metadata review, official public documentation retrieval and deterministic planning-ID generation only. **No Supabase project/DB/Auth/Dashboard/Management API connection, no JWKS repeat, no tests/rehearsals/sign-ins/fixtures/identity/MFA provisioning, no database changes and no SSL configuration change in Phase9E.** Previously passing tests/TLS/catalog checks were not repeated. Only this plan and the integration tracker were edited; existing cluster, protected handlers, Phase4 Orders and frontend gate/allowlist preserved.

Remaining blockers: current installed revision; tenant upstream transport attestation/compliance; named genuine staff authority/provisioning mechanism; safe case/history/abuse fixture writer and retention-compliant cleanup; scoped real acceptance harness/evidence. Assessment/preparation is complete; execution remains gated. All three endpoints **NOT ADMITTED**, frontend **DISABLED**, no Phase10.


## Phase 9F — privileged version-only verification (2026-10-24)

**SUCCESS: installed Alembic revision0043_standalone_activation matches the approved repository's sole head.** This resolves the earlier migration-version access blocker through the owner's separate explicit Phase9F authorization; no permissions were changed and no migration was applied. Earlier UNVERIFIED entries remain historical.

### Exact scope and safeguards actually used

- Validated locally the approved development project fhux…kzvq / reference SHA256 prefix17e54a8be1b7; protected Auth hostname reference and migration login tenant suffix match. Migration URL selects the same exact configured database/hostname/port as the runtime URL: aws-0-ap-northeast-2.pooler.supabase.com:5432 (Supavisor session pooler). No direct/alternate project or endpoint fallback.
- Retrieved only the existing migration credential in memory from the existing protected backend/.env configuration using dotenv parsing. Credential was not printed, exported, logged, written into source or copied into a new secret file. Missing credential/identity/trust validation would stop execution before connecting. No alternate credential was attempted.
- Used the previously validated owner-supplied CA staged at E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem, with pinned PEM SHA256700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7. Explicit sslmode=verify-full and host/port/database/login; libpq client SSL=true. **TLS chain and exact pooler hostname verification succeeded.** Trust provenance/limits from the supplied-CA assessment remain unchanged; no trust setting or CA file changed.
- Removed inherited PG defaults; connection timeout10s; startup options set default_transaction_read_only=on, statement_timeout10s, lock_timeout2s, idle_in_transaction_session_timeout20s and search_path=pg_catalog. Explicit BEGIN READ ONLY was acknowledged; client protocol transaction state confirmed INTRANS without another SQL query.
- Executed exactly **one data-query statement**: `SELECT version_num FROM public.alembic_version;`. Only required transaction control accompanied it: BEGIN READ ONLY and ROLLBACK to close the read-only transaction, then connection close. No additional catalog/connection-state SELECT, SET ROLE, application/security function, Alembic command or other privileged query. Transaction rollback was not a migration rollback.

### Returned result and comparison

| Item | Actual result |
|---|---|
| Query attempted/succeeded | Yes / yes; no retry or alternative privileged query. |
| Installed revision rows | Exactly one:0043_standalone_activation. |
| Approved repository head |0043_standalone_activation; determined by locally parsing literal revision/down_revision assignments, not importing migration files or invoking migration tooling. |
| Comparison | Matches sole repository head; no discrepancy or repair required by this comparison. |
| Client TLS | verify-full succeeded with the pinned supplied CA and exact configured Supavisor hostname. |
| Transaction/connection | Read-only transaction ended; connection closed. |

Version equality is current revision metadata evidence only. It does not prove every deployed schema/function body matches source, provide a full execution ledger, or establish functional Auth/RLS acceptance. Ignored local audit script/result contain no credentials or application rows; only the authorized revision result and redacted safety metadata were retained. The script received a local syntax check; no application test/rehearsal suite was run for this narrow task.

### Transport and remaining acceptance gates

The prior database-side pg_stat_ssl=false observation remains unresolved; **no TLS/backend catalog query was repeated in Phase9F**. This verified client-to-Supavisor connection does not prove pooler-to-PostgreSQL TLS or end-to-end encryption. Obtain dated same-project Dashboard SSL-enforcement evidence or a separately authorized metadata-only provider setting read, with provider clarification if needed. Do not change SSL settings or switch endpoints in this scope.

Remaining prerequisites: approved transport-security evidence; installed/source security-definition compatibility; named authority/custodians and genuinely verified dedicated Support identities; genuine TOTP enrollment and signed/provider AAL2/session checks; architecture-approved pair-independent retention-safe synthetic case/history/abuse fixture path; retention-compliant idempotent setup/cleanup; controlled runtime RLS/assignment/fail-closed/projection/QR-independence acceptance with explicit approval for minimal metadata GET audit writes. Phase9E's fixture IDs are proposals only, not provisioned records. No grant, identity, MFA, fixture, migration, schema, role or application change was performed here.

Next safe step is owner-provided dated/redacted SSL-enforcement evidence for the exact project, or separate authorization for the exact read-only provider-setting operation described in Phase9E. Architecture-only fixture design and later identity/provisioning/API acceptance remain separate scopes. Do not rerun the migration revision query just because other acceptance gates remain open.

All three Support Metadata endpoints remain **NOT ADMITTED** and frontend live gate remains **DISABLED**. Existing local PostgreSQL17.11 cluster, backend/frontend application code, Phase4 Orders and protected Support/Finance handlers unchanged. No user/session/customer/case/order/payment/QR records, prohibited APIs or application security functions accessed; no migrations applied or rolled back; no Phase10. **STOP after Phase9F verification.**


## Phase 9G — SSL-enforcement inspection-only assessment (2026-10-24)

**Project SSL enforcement: UNVERIFIED. Supavisor-to-PostgreSQL TLS: UNVERIFIED / OPEN for acceptance, with prior positive evidence of a non-SSL backend session. Transport requirements: NOT ESTABLISHED AS SATISFIED.** This is an evidence/permission boundary, not a finding that the Dashboard toggle is disabled. Phase9F installed0043_standalone_activation/source-head match and audit-client verify-full success remain valid prior evidence; neither query nor handshake was repeated.

### Evidence access and actual project-setting status

Reviewed the current Cloud plan/tracker, Security and Privacy Specification section12.1, backend/app/db/session.py, non-secret URL/TLS projections from existing local configuration and prior redacted catalog/Phase9F artifacts. Tool discovery found no exposed authenticated Supabase Dashboard/browser/Management API connector. No owner-supplied dated Dashboard setting or authenticated provider-setting response exists in the reviewed Phase9 evidence. No new tool connection, provider login or privileged credential was used.

The owner permits available authorized Dashboard inspection, but explicitly excludes newly privileged credentials/additional remote endpoints without specific prior authorization. Phase9F approved only its now-completed single SQL query; it did not authorize Management API access. Prior proposed GET approval requests are not approvals. Consequently **no call to the project's Management API/Dashboard was made** and no project SSL-enforcement enabled/disabled value can honestly be recorded. Absence of a local declaration is not disabled enforcement. No Supabase connector was installed or account permissions broadened just to remove this uncertainty.

### Verified versus unverified connection legs

| Leg or control | Evidence and conclusion |
|---|---|
| Prior audit client → configured Supavisor session pooler | VERIFIED relative to the owner-supplied CA: sslmode=verify-full, exact hostname aws-0-ap-northeast-2.pooler.supabase.com:5432 and client SSL=true. Approved tenant reference fhux…kzvq / SHA256 prefix17e54a8be1b7. This is the audit connection, not a new FastAPI runtime handshake. |
| FastAPI's inspected local connection configuration | Runtime and migration URL TLS parameters are sslmode=require, no explicit sslrootcert URL parameter. backend/app/db/session.py accepts/preserves require rather than forcing verify-full. Both target the expected same session pooler. This config was inspected locally only; no FastAPI server started or connection tested. Effective deployed overrides/default trust files are not established. |
| Meaning of require versus prior audit verification | require requests encrypted client transport but does not enforce hostname verification. Libpq can additionally validate a CA with an existing default root file, so absence of an explicit root parameter is not proof of no CA checks; it still does not make require equivalent to verify-full. The audit explicitly overrode this local mode with verify-full and pinned CA. Do not promote audit success to a verified FastAPI deployment configuration. |
| Supavisor → underlying PostgreSQL | Earlier own-session pg_stat_ssl showed ssl=false and protocol/cipher null. That describes PostgreSQL's backend connection after the proxy, not the original client's socket. The observed backend leg was not using PostgreSQL SSL at that time. No new SQL/probe was issued, so current upstream settings/state are unverified. |
| Actual managed enforcement/tenant TLS controls | No authenticated setting read. upstream_ssl/upstream_verify/upstream_tls_ca, provider routing/deployment/pool state and any additional transport/network protection are unverified. No compensating-control attestation inferred from generic hosted architecture. |
| End-to-end acceptance | OPEN. Client-side successful encryption/verification does not prove server enforcement against plaintext clients or encryption/authentication on a separate upstream leg. |

### Authoritative provider interpretation

[Supabase SSL-enforcement documentation](https://supabase.com/docs/guides/platform/ssl-enforcement) identifies Dashboard Database Settings → SSL Configuration → Enforce SSL on incoming connections, and documents that managed enforcement governs both client-to-Supavisor and Supavisor-to-Postgres. A client voluntarily using TLS therefore cannot establish the setting. The same documentation warns that updating enforcement can reboot the database; no update is authorized here.

[Official Supavisor tenant configuration](https://github.com/supabase/supavisor/blob/main/docs/configuration/tenants.md) distinguishes enforce_ssl for incoming clients from upstream_ssl, upstream_verify and upstream_tls_ca for database connections. These separately terminated connections explain how verified downstream TLS and a non-SSL backend observation can coexist. Repository documentation describes capabilities, not this hosted tenant's actual values or a universal hosted plaintext policy.

[PostgreSQL pg_stat_ssl documentation](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-SSL-VIEW) describes a row per backend connection; it does not trace an original client through a TLS-terminating pooler. [Libpq SSL documentation](https://www.postgresql.org/docs/17/libpq-ssl.html) distinguishes require from certificate-and-hostname verification with verify-full. No unrelated community discussion was used as provider attestation.

Security/Privacy Specification section12.1 requires HTTPS/TLS for database connections and prefers TLS1.2+. No approved exception for a non-TLS Supavisor upstream was identified. Thus the project **cannot be signed off as satisfying transport requirements from present evidence**. This does not assert the current setting is disabled, establish current deployed client behavior, or authorize a change. If the setting proves enabled while backend ssl=false remains relevant, provider clarification is necessary rather than dismissing that observation or claiming private routing automatically satisfies TLS.

### Exact missing evidence and next authorized action

The next action within current authority is to **inspect owner-supplied, dated and redacted authenticated Dashboard evidence** showing the SSL-enforcement control for this exact project. Include sufficient project context to bind it to fhux…kzvq/fingerprint17e54a8be1b7 and capture current/effective state if the provider distinguishes requested or pending state. No password, token, full connection string or private certificate/key should be included. Providing this evidence does not authorize a setting change.

If the owner prefers agent retrieval, separate exact approval is needed for **one HTTPS GET to `https://api.supabase.com/v1/projects/<approved-project-ref>/ssl-enforcement`**, via a specifically approved existing authenticated channel, TLS verified, redirects rejected, bounded response, metadata-only output and no credential logging. Do not ask for a token in chat, search unrelated credential stores, reuse a DB/service-role credential as a Management API token, call project/user/session listings, or install/connect a tool without permission. No such channel or credential availability is assumed. This GET was **not** executed in Phase9G.

After authoritative setting evidence, request provider confirmation if necessary of the intended tenant's effective upstream_ssl and certificate verification behavior, route/deployment/time applicability, and why the observed PostgreSQL session lacked SSL. Any repeat SQL/transport probe, endpoint switch, enforcement update/reboot or application config hardening requires its own reviewed scope. No assertion that a Dashboard toggle alone retroactively proves every connection was protected.

### Remaining security acceptance tasks and preservation

1. Obtain authoritative project enforcement evidence; reconcile upstream SSL observation and the approved TLS requirement with provider/security-owner review.
2. Review the actual deployment's client connection policy: local URL mode require is weaker than audit verify-full for hostname authentication. Prepare a separately approved configuration/deployment plan if hardening is required; do not alter local/production defaults here.
3. Continue Phase9E's architecture review for pair-independent retention-safe fixture setup/history/abuse-policy handling and compliant cleanup. Named genuine verified Support identity/MFA provisioning, dedicated synthetic fixtures, scoped real RLS/auth/fail-closed/minimized-response/QR-independence acceptance and explicit minimal GET audit-write approval remain pending. Do not repeat the now-verified migration-head query.
4. Only after those acceptance gates and recorded exact admission may a reviewed server-controlled frontend release be considered. All three endpoints remain **NOT ADMITTED**; live gate **DISABLED**.

Actual Phase9G work: local non-secret configuration/source/evidence inspection and published official provider/PostgreSQL documentation only. No SQL, migration/JWKS repeat, project DB/Auth/Dashboard/Management API request, certificate download/rotation, identity/MFA/fixture creation, RLS/grant/SSL/configuration change, protected/quarantined/QR API, local-cluster modification or application code change. No test suite run for this documentation assessment. Only Cloud plan and integration tracker updated. Prior historical results remain clearly distinguished from current unknowns. No Phase10; STOP after assessment.


## Phase 9 — Original Step 2: Consolidated Security Acceptance (2026-10-24)

**STEP 2 BLOCKED — NOT PASSED.** This is the consolidated status for the original four-step Phase9 plan. No new phase/step is created and the roadmap is not renumbered. Earlier lettered entries are retained solely as evidence history. Source/offline verification is complete for the authorized scope; genuine PostgreSQL/Auth/MFA/RLS acceptance has not passed. All three Support Metadata GETs remain **NOT ADMITTED** and live frontend gate **DISABLED**.

### One consolidated requirement matrix

Statuses: PASSED means only the stated evidence scope passed; FAILED identifies a demonstrated requirement mismatch, not an invented failed live test; BLOCKED means missing evidence/authority/design; NOT EXECUTED means deliberately withheld operations. Historical versus fresh results are explicit.

| Requirement | Status | Actual evidence / remaining condition |
|---|---|---|
| Installed migration revision equals approved head | **PASSED** | Prior explicitly authorized single query returned0043_standalone_activation, matching the sole source head. Reused Phase9F artifact; query not repeated. Version equality is not full schema/body equivalence. |
| Audit-client certificate/hostname TLS | **PASSED** | Prior same-target verify-full with owner-supplied validated CA. No new handshake/JWKS in this Step2 continuation. |
| Current local FastAPI configuration requires hostname verification | **FAILED — configuration requirement** | Actual runtime URL uses sslmode=require and no explicit rootcert; db/session.py preserves that mode. This does not require hostname verification. No failed live connection/test is claimed; no claim about uninspected deployed overrides. |
| Minimal runtime TLS change prepared and reviewed offline | **PASSED** | Concrete non-secret proposal at tmp/phase9-step2/runtime-tls-proposal.json; actual SQLAlchemy/psycopg parameter construction checked with psycopg.connect forbidden; zero connection calls and environment file unchanged. Not applied or activated. |
| Project-specific SSL enforcement | **BLOCKED / UNVERIFIED** | No dated redacted authenticated Dashboard evidence or approved Management API response available in reviewed local artifacts. No API request or new connection permission used. Do not infer disabled/enabled from client TLS. |
| Supavisor→PostgreSQL TLS / full transport compliance | **BLOCKED / OPEN** | Prior own-backend pg_stat_ssl=false/protocol and cipher null. Proxy separation explains different legs; actual enforcement/tenant upstream settings and reconciliation remain missing. No new SQL, endpoint switch or setting change. |
| Required managed Auth/MFA and Support security schema metadata | **PASSED — structural only** | Prior catalog audit found Auth/MFA tables/required column types, support_cases/events, staff/audit/account/abuse dependencies, roles/ACL/RLS and function security attributes. Not actual factor/session or policy enforcement evidence. |
| Three closed metadata contracts and minimized projections | **PASSED — source/isolated** | Fresh review and tests: exact list/detail/history schemas/queries, content_available=false; no case content, notes, actor identities, customer/order/pair enrichment. Deployed response acceptance still pending. |
| Explicit Support, verified email, signed/current provider MFA and final recheck | **PASSED — source/isolated** | require_staff plus authorize/session guard; exact Support, no Finance/security/superadmin inheritance; signed AAL2 and provider MFA must agree; final auth recheck. Isolated doubles do not prove genuine provider behavior. |
| Queue/case/history and retained-abuse authorization | **PASSED — source/isolated** | Case list/detail restrict to mine/unassigned and sr_abuse_case_readable; history requires current assignee. Guard fails503 if helper absent; policy filtering preserved on continuation. Base case RLS is broader than the API assignment predicate; assigned-only event policy and restrictive abuse policy remain essential. |
| Fresh focused offline/frontend/backend tests | **PASSED** |44 backend +73 relay/contract +23 browser = **140** checks freshly passed. TypeScript and scoped Ruff passed separately; TLS proposal review is additional offline evidence, not added to the140. |
| Real verified-email Support identities and provider session controls | **BLOCKED** | No acceptance accounts provisioned/approved; named human custody, signup/email/hooks and staff-grant governance/writer not established. No real account may be adopted. |
| Genuine MFA/AAL2, ban/revocation/disabled-account acceptance | **BLOCKED** | Requires approved dedicated accounts, genuine enrollment/challenge/verification and scoped state changes. No synthetic JWT/session row can satisfy it. |
| Smallest synthetic case/history/abuse set | **BLOCKED — design/approval** | No approved executable fixture set. Three identity and five core-case proposals below; retention trigger reaches order_pair_units even for null references. No bypass or fake closed-case shortcut. |
| Actual PostgreSQL RLS/assignment/policy behavior | **BLOCKED** | Need safe fixtures, restricted runtime context and scoped harness/approved audit writes. Catalog policy existence is not enforcement acceptance. |
| Installed function-body/source equivalence and nested QR independence | **BLOCKED** | Function signatures/owners/ACL/search_path were inspected, not full deployed body graph or nested query/lock behavior. Future approved observation must exclude unrelated data and all QR operations. |
| Runtime config edit/restart/deployment | **NOT EXECUTED** | Exact edit proposal requires confirmation/authorization; no process restart, service launch or live verification in this task. |
| Management API / enforcement changes | **NOT EXECUTED** | No GET authorization, no authenticated channel established; no PUT/PATCH/reboot. Owner evidence remains preferred. |
| Identity, MFA, fixture, role/RLS/schema/cloud mutations | **NOT EXECUTED** | Explicitly outside current authority. No migrations, sign-ins/enrollment or cleanup executed. |
| Live metadata GET acceptance including read audits | **NOT EXECUTED** | GETs insert minimal audit rows; require explicit audit-write permission and synthetic scope. Neither HTTP GET nor offline140 means no live mutation. |
| Protected handlers/Phase4 Orders and disabled frontend | **PASSED — preservation** | Protected Support/Finance/independent Order metadata SHA256 hashes match prior baselines; server gate still returns false; old relay remains blocked. No application code or allowlist changes. |

### Runtime driver and exact configuration proposal — NOT APPLIED

Inspected actual `backend/app/db/session.py`: SQLAlchemy normalizes PostgreSQL URL to postgresql+psycopg; psycopg3 DBAPI uses libpq. Installed local versions: SQLAlchemy2.1.4, psycopg/psycopg-binary3.3.6, libpq18.4 (180004). Database.from_settings preserves URL TLS query parameters and does not enforce verify-full globally. Pool/statement timeout behavior is unchanged by the proposal.

**Exact proposed target:** `E:\Projects\SafeReturn\backend\.env`, only query parameters within **SAFERETURN_DATABASE_URL**, local development target fhux…kzvq/fingerprint17e54a8be1b7, same pooler aws-0-ap-northeast-2.pooler.supabase.com:5432 and existing database/login/password. No complete URL or secret is copied into the proposal/report.

| Query parameter | Current | Proposed |
|---|---|---|
| sslmode | require | verify-full |
| sslrootcert | not explicit in URL | E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem |

CA PEM SHA256:700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7. Previously validated public root; this review rechecked the pinned bytes only to validate the proposed parameter source. Use URL-aware encoding for the path; do not concatenate an unescaped Windows path/full secret URL in a shell. The actual driver construction confirmed the decoded file path is passed to libpq, verify-full survives existing normalization, and hostname/port/database/username/password and every other URL parameter are unchanged.

Ignored review artifacts: `tmp/phase9-step2/review_runtime_tls.py`, `runtime-tls-proposal.json`, `isolated-results.json`. The review script parsed existing protected configuration in memory, built an engine without connecting, blocked psycopg.connect, inspected actual dialect arguments, disposed the unused engine and verified the environment file's bytes were unchanged. No credential in any output/artifact. This is a concrete, reviewable two-parameter edit, not a blanket backend code hardening patch.

This path exists on the current Windows development host and is not an approved production/container path. No CA was copied/rotated and no system trust changed. Before applying confirm that backend/.env is the intended persistent runtime input: ops/start-local-backend.ps1 only loads a supplied -EnvFile and an already running process may use other environment settings. Do not assume changing a file changes an active process. Migration/test/worker URL settings and frontend configuration are explicitly outside this minimal edit. For another deployment, first approve its exact environment/CA mount/path; do not deploy a tmp path blindly or weaken verification if the file is missing.

If subsequently approved, change only these parameters using a secret-preserving URL-aware edit, preserve file ACLs/other entries and verify the diff in memory without logging secrets. File edit, backend restart/deployment and remote verification remain separately controllable actions. On activation failure stop with gate disabled; do not silently roll back to require or fall back to another endpoint. No application code edit is necessary for this proposed local setting change.

### Contract and security review consolidated

Paths are GET `/api/v1/admin/support-case-metadata`, GET `/{case_id}`, GET `/{case_id}/history` only. List accepts case_id/case_type/status/priority/queue/limit/cursor; detail no query; history limit/cursor only. Strict enums, UUIDs, limit1–100 and opaque AEAD cursor binding to actor/filter/purpose/case and history revision are retained. UTC closed projections expose metadata only.404 conceals missing/foreign/other-assignee cases/history; stale history409, invalid input400/422, helper/dependency failure503. Backend role/email/MFA/current session and final reauthorization remain authoritative.

Relevant prior policies: case SELECT base policy plus restrictive sr_abuse_case_scope; event SELECT sr_case_event_read (Support/current assignee); own-row staff SELECT; audit SELECT/INSERT guards; auth/session/account helpers and pinned search_path/owners/EXECUTE ACLs. RLS cannot be accepted using migration/service_role; API-role local actor/MFA context must come from genuine authenticated server context. Do not claim base case RLS alone enforces the API's mine/unassigned restriction.

Retained abuse requires valid unrevoked current approved policy/version, triage enabled and report/case retention not expired. Unlinked ordinary cases are distinct from linked cases with invalid policy. Missing helper fails closed. Deployed helper-body equivalence and actual policy values were not retrieved or executed here. Read audit inserts are minimal but still writes and need future permission.

### Minimum real acceptance proposal — NOT APPROVED FOR PROVISIONING

There is **no currently approved/provisioned acceptance fixture set**. Smallest core proposal reuses the exact IDs and constraints from the earlier assessment, without creating or reserving anything:

| Subject/record | Required state or proposed identifier |
|---|---|
| A | New individually controlled verified-email Support operator; genuine AAL1 negative then real TOTP/AAL2 positive. |
| B | Second new verified Support/AAL2 operator, owns other-assignee case; no shared owner account. |
| C | New verified nonstaff/AAL2 account with no Support for role denial. Specific Finance/security/superadmin live negatives require separate optional scoped role subjects; this no-role control does not prove them all. |
| A-assigned case with safe history | c90f3faa-d32c-579c-b5c0-a567ded5371c; may also exercise dedicated valid abuse-policy visibility. |
| Unassigned metadata-only case | ab21415b-760c-5c2d-9782-d715dadc2ec3; exact-ID list/detail positive, history404. |
| B-assigned / A unauthorized case |30a99c61-fa5c-5c9e-b3a2-c167b3288eae; also tests wrong queue visibility. |
| A-assigned no-history case | ecb5fe4b-342a-59c9-a4f9-c212f0053feb; valid provenance/producer semantics must be approved. |
| A-assigned restricted retained-abuse case |4294248a-7a2c-5c68-98e3-6255abb96e37 under dedicated approved invalid/expired/revoked policy scenario. |

Two safe history-event candidates and dedicated valid/invalid policy IDs are specified in the existing plan. Provider actor UUIDs must come from actual signup; no fake IDs or email/MFA attestations. Five core cases permit list cursor tests using limit1 and two A-owned records; two events permit history cursor tests using limit1. This does not require21 fake cases just to trigger default20 pagination. Additional independent triage/retention branches and wrong-role states need explicitly approved small extensions, not shared-policy changes. Malformed ID uses no record; proposed missing ID must be checked only through an authorized exact-ID scope before claiming absence.

Existing0019 sr_retention_admission/trigger (lines193/210/228) reaches order_pair_units on open/investigating case insertion even if pair_id/order_id are null. No approved pair-free writer exists. Existing workflow_sample/pg_rehearsal/legacy Support/auth integration setup creates excluded data or synthetic sessions and cannot be used. No protected creation API, direct INSERT shortcut, fake closed case, trigger/RLS disablement, role expansion or retention weakening is allowed. A separately approved pair-independent fixture-creation/history/policy architecture is necessary before any fixture execution. A fresh project alone does not remove this dependency.

Identity provisioning likewise requires named owner authority, independent custodian/executor/test inboxes, supported email verification and genuine enroll/challenge/verify. Existing staff runbook is a governance proposal, not a preapproved SQL grant writer. Review signup/profile/outbox/hooks before allowing new accounts. Unverified/expired/revoked/disabled negative cases need provider-real supported states and explicit scoped mutation permission; do not fabricate JWTs/session rows or modify real accounts.

Use uniquely recorded manifest IDs, owned test inboxes and approved payload hashes, not made-up DB namespace columns. No current collision check/reservation or runnable fixture manifest. Future setup must abort on unmatched provenance, use idempotent step receipts, and never adopt preexisting data. Append-only history/audit and auth/case/policy FKs prevent assuming blanket deletion. Cleanup must preserve retention; no delete-all/upsert/cascade/trigger bypass. Where immediate cleanup is not lawful/supported, retain approved minimal synthetic evidence with subject-only revocation under separate approval. This cleanup design is a remaining blocker, not a promise of reversibility.

### Focused safe tests actually executed in this Step2 continuation

Inspected setup/teardown before running: backend metadata tests construct a private FastAPI app, `_env_file=None`, fake SQL Database, httpx mock JWKS/ASGI transport and local cryptographic fixtures; teardown closes only the mock verifier. Frontend fixture uses a TS VM with synthetic token/role stubs; browser suite intercepts every request, fulfills only synthetic navigation/metadata dispatch and aborts unexpected traffic; no webServer in its dedicated Playwright configuration. No real environment, DB, Auth identity/session, API server or old rehearsal/Support/Finance/QR suite was executed by these tests. Test mock injection stays exclusively in test infrastructure.

| Executed command / review | Actual result |
|---|---|
| backend `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider` | **44 passed in7.50s** |
| frontend `node scripts/test-support-metadata.cjs` | **73 checks passed**, disabled gate zero auth/staff/upstream calls, strict permitted GET paths, error/projection/grant/MFA/final recheck cases |
| frontend `node node_modules/@playwright/test/cli.js test --config playwright.support-metadata.config.ts --max-failures=1` | **23 passed in41.9s**; includes disabled SSR/hydration, effects, link-prefetch intent, list/detail/history, errors/empty/loading/filter/cursor/responsive/keyboard cases |
| frontend `npm run typecheck` | **PASSED** |
| backend scoped Ruff router/service/metadata tests | **PASSED** |
| Local actual-driver TLS proposal construction with network forbidden | **PASSED**, target/credential/non-TLS parameters preserved, zero connects, environment bytes unchanged |

**140 focused tests/checks freshly passed; no failed test run in this continuation.** The FAILED table row is the observed current TLS configuration requirement mismatch. Browser tests stub Next Link as an anchor, so actual deployed Next/browser prefetch acceptance is not claimed; source links explicitly have prefetch=false. Scoped backend Ruff is not a frontend lint pass: no frontend lint command/executable is configured. No package installation or broad build/live suite run. Test artifacts/screenshots are synthetic local files only.

### Exact remaining approval requests — one dependency-ordered list

**A — minimal local runtime config edit only.** Confirm and authorize modifying only SAFERETURN_DATABASE_URL's sslmode=require→verify-full and adding sslrootcert=E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem in E:\Projects\SafeReturn\backend\.env for the same approved development database. Preserve every credential/target/other entry and ACL; no migration/test/worker URL, backend/frontend code or gate change. This approval does not authorize restart/deployment, live checks or cloud writes; name any later process/deployment explicitly. This request is required by the user's Step2 instruction to confirm the exact file/configuration before modification. The non-secret proposal is ready for review now.

**B — project enforcement evidence.** Provide dated redacted authenticated Dashboard Database Settings→SSL Configuration evidence for the same project, current/effective state where available. Alternatively explicitly authorize one TLS-verified/no-redirect/bounded HTTPS GET `https://api.supabase.com/v1/projects/<approved-ref>/ssl-enforcement` using an approved existing authenticated channel. No token in chat/logs, account enumeration, PUT/PATCH/reboot or other endpoints. Current task does not authorize that GET and no usable approved channel is assumed. Provider clarification of effective upstream_ssl/certificate verification/routing is needed if enabled settings conflict with prior backend ssl=false; no inference of encryption from private network assumptions.

**C — retention-safe fixture architecture and cleanup review.** Approve design review of a pair-independent synthetic case/history/abuse writer that preserves existing retention/ownership/authorization protections, including idempotent manifest ownership and append-only/FK-compliant cleanup. No implementation/migration/fixture insert is authorized by a design review. No already approved safe insertion mechanism can simply be executed today.

**D — concrete genuine identity/MFA/staff provisioning.** Only after exact named authority/custodians/inboxes, signup/hook/notification impact and controlled grant writer are reviewed: separately approve dedicated A/B/C creation/email verification, real TOTP enrollment/challenge/verification, explicit A/B Support grants and precisely listed disposable negative-state changes. No existing identities or provider auto-confirm/MFA bypass; no implicit broad privileged role grants. This is not approved now.

**E — scoped real acceptance and permitted writes.** After A/B transport/driver and C/D setup gates, approve the actual manifest/writer and exact list/detail/history API/RLS test matrix with approved synthetic IDs, minimal audit INSERTs, scoped fixture state/concurrency changes and nested independence observation. Explicitly review setup/teardown and retention. No broad queue enumerations, production data, pair operations, old routes or migrations. Test failure must stop or report truthfully; never waive missing live evidence.

Admission/front-end activation remains a later decision in the **existing** four-step roadmap, after Step2 genuinely passes; no new roadmap stage or automatic activation is introduced. None of A–E is inferred from this reporting task.

### Stop state / scope preserved

Only this Cloud plan and progress tracker were edited, plus ignored non-secret offline review/test artifacts. No active .env edit, process restart, service launch, deployment, cloud SQL/API/JWKS/Management request, identity/MFA/fixture operation, schema/RLS/grant/enforcement change, protected Support/Finance/Phase4 Orders edit or local PostgreSQL cluster operation. Protected source hashes match prior baselines. Earlier approved migration/TLS/catalog evidence was reused rather than re-run. No new dated project SSL evidence was found; that absence is recorded, not replaced by a guess.

**Original Phase9 Step2 remains BLOCKED / NOT PASSED.** Authorized offline verification/proposal/consolidation is complete. Exact blockers/requests are all above; stop for those decisions. Endpoints **NOT ADMITTED**; live gate **DISABLED**; no later step started.


## Phase 9 read-only Support integration — actual execution result (2026-10-24)

**PHASE 9 READ-ONLY SUPPORT FRONTEND — IMPLEMENTED; LIVE ACCEPTANCE BLOCKED.** Existing four-step roadmap unchanged. The Cloud database is intact as the owner now confirms. No recovery/reset/rebuild/migration is needed or authorized from the reported data-loss concern; no recovery operation was performed. No new Phase9 subdivision or Phase10.

### Working connection changes and actual checks

Applied the existing reviewed runtime TLS proposal to **backend/.env → SAFERETURN_DATABASE_URL only**. Changed sslmode=require to verify-full and added sslrootcert pointing to the proposal's normalized validated public CA copy: `E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem` (PEM SHA256700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7). That is the reviewed audit copy of the Supabase CA originally supplied at `E:\Projects\SafeReturn\tmp\phase9c-local\supabase-db-ca.crt`; no root rotation, new certificate or trust downgrade. The latest authorization to use the reviewed proposal superseded the earlier stop-only request, and the actual environment now matches the reviewed proposal exactly. The source certificate was not altered.

Before editing verified exact same pooler aws-0-ap-northeast-2.pooler.supabase.com:5432 and approved project fhux…kzvq / fingerprint17e54a8be1b7. The edit preserved raw URL prefix/credentials and every other query component, all other environment entries and file ACL through an in-place update. No credential/complete URL printed or stored in audit artifacts. Offline actual-driver checks passed without a connection before applying. No migration/test/worker URL, frontend environment or application source changed.

Then started the **real FastAPI application with its actual lifespan on a temporary127.0.0.1 listener**, loading the corrected backend environment. Used app.state.database's real SQLAlchemy/psycopg engine, not a replacement fake: verify-full and the pinned CA passed to the driver; actual client SSL=true; the same Cloud development database connected successfully. Inside BEGIN READ ONLY inspected only named pg_catalog schema metadata. Confirmed support_cases,support_case_events,staff_roles,audit_events,abuse_reports,abuse_intake_policies,account_security_state plus Auth users/sessions/MFA tables exist, with RLS enabled. Rolled back metadata transaction/closed connection. No application/QR records read.

Sent real loopback unauthenticated HTTP GET requests to the three independent metadata routes. **List401, detail401, history401** as required. No token/JWKS/sign-in/session/authorization function/case data/audit INSERT was used: get_principal rejects missing credentials before those operations. This establishes actual unauthenticated route denial, not positive Support/MFA/RLS acceptance. The temporary backend server exited normally and is **stopped**; no public listener/deployment/worker was started or existing server restarted.

The subsequent authorized read-only recovery catalog inspection (before the owner corrected the data-loss report) found **111 public tables,27 Auth tables,8 Storage tables and239 public functions** on the same TLS-verified development target. This is schema-object metadata, not counts of users/cases/objects. Runtime privileges/RLS prevented safe full aggregate and bucket metadata reads, so **no application/Auth row counts, storage object names or QR records were read**, and no zero-data conclusion was inferred. That connection closed normally. Supabase Dashboard operational status/backups were not contacted. The present task does not require another recovery investigation.

Installed0043_standalone_activation/source-head match and prior catalog role/grant/policy/function-security evidence reused from the explicitly authorized earlier checks. No privileged version query repeated. The 111-table observation independently contradicts total public-schema loss, but says nothing about whether individual earlier records/files exist; no private record enumeration to establish that.

### Concrete application status

| Question | Actual outcome |
|---|---|
| Is the Supabase Cloud database reachable? | **YES**, using the actual corrected runtime credential/driver with verify-full. |
| Required Support/Auth/security tables present? | **YES**, fresh named-table catalog verification; no schema recreation needed. |
| Is FastAPI connected? | **YES during the real loopback verification**; its actual app database engine queried Cloud metadata. Temporary process stopped afterward. |
| Runtime TLS corrected? | **YES**, persistent local runtime setting now requires CA/hostname verification; no other credentials/connection settings changed. |
| Genuine Support authentication/MFA/permission acceptance? | **BLOCKED. Owner explicitly confirmed no dedicated Support test account exists.** No existing customer/owner Operations/Finance account was repurposed; no account/grant was created. |
| Real unauthenticated API rejection? | **PASSED**, three401 responses from the actual loopback backend. Wrong-role/MFA/queue/policy positive/negative scenarios are still isolated evidence only. |
| Actual PostgreSQL/RLS assignment/policy acceptance? | **NOT PASSED**, needs approved real actor/session and safe synthetic case/history/policy scenarios. Policy presence alone is insufficient. |
| Eligible for allowlist admission now? | **NO**, mandatory genuine auth/MFA/RLS/fixture/transport acceptance missing. No admission occurred. |
| Live gate enabled? | **NO**; supportMetadataAdmitted() still returns false. No client/development bypass introduced. |
| Real signed-in Admin Support UI working? | **NOT VERIFIED / NOT LIVE-CONNECTED**. Existing UI/relays are implemented; cannot activate or claim signed-in list/detail/history without the missing authorized identity and acceptance evidence. No frontend rebuild or live browser sign-in run. |

Existing relay/source review confirms exact independent GET paths, verifiedSession + staffState, explicit Support/capability/MFA, backend verified-email/live provider assurance and final role/session recheck. Closed DTO validation, no-store/bounded bodies, filters/keyset cursors, assigned-only history, mandatory retained-abuse readability and no legacy fallback remain intact. No old Support/Finance console or general Orders route was mounted/called. Restricted Create/Claim/Note/Priority/Status/Financial/QR actions stay unavailable.

### Test evidence and scope

Prior fresh focused run on unchanged application code remains **73 relay/contract +23 isolated browser +44 backend =140 checks PASSED**, plus TypeScript and scoped Ruff PASSED. No redundant rerun after a two-parameter environment edit; the changed real connection was instead verified with the actual FastAPI engine and the three real401 requests above. Local post-edit driver checks and CA/target checks passed. There has been **no genuine signed-in API/RLS acceptance or live signed-in frontend browser acceptance**. No fabricated successful responses, synthetic JWTs promoted to live evidence or silent fake data fallback.

Protected Support/Finance/independent Phase4 Order metadata SHA256 hashes still match prior baselines. Gate remains disabled. SQL recovery/connection inspection touched catalogs only and issued no database mutation. The only persistent application-configuration change is the two runtime URL TLS parameters. No server left running by this task, no public deployment and no hidden frontend activation.

### Exact remaining execution blockers / next permissions

1. **Dedicated genuine identity:** owner confirmed none exists. Obtain explicit approval for dedicated test inbox/account creation through official Supabase Auth, genuine email confirmation and TOTP enrollment/challenge/verification with a named human custodian, plus controlled explicit Support grant through a reviewed authorized provisioner. No auto-confirm, direct auth.users/session insert or forged MFA. Two independent Support operators plus one nonstaff control remain the smallest core full-scope proposal; a single verified Support/MFA identity is the first positive-auth prerequisite. No privileged identity creation is authorized by the completion request.
2. **Safe cases/history/policy fixtures:** no approved fixture set exists. Existing retention-admission trigger can query order_pair_units even with null pair references; no protected creation/direct INSERT/fake-closed/trigger/RLS bypass. The previously proposed five core case IDs and dedicated policy/history manifest remain plan-only. Architecture-approved pair-independent setup and compliant cleanup, followed by exact cloud-write authorization, are still required. Do not assume the existing development records are authorized synthetic data or reuse real cases.
3. **Frontend session configuration for the local run:** inspected standard frontend/.env.local has none of SAFERETURN_SUPABASE_URL,SAFERETURN_SUPABASE_PUBLISHABLE_KEY,SAFERETURN_WEB_ORIGIN,SAFERETURN_API_ORIGIN populated. A running process's overrides were not inspected/assumed. Before a genuine signed-in run load the approved same-project public Auth settings and exact loopback frontend/backend origins through server-side local configuration; no service-role secret in frontend. No frontend environment was silently persisted or browser authentication bypass added here.
4. **Remaining mandatory acceptance:** signed/provider AAL2, current verified Support/queue/assignment/retained-abuse behavior under real restricted role, minimized DTOs and nested QR independence, plus scoped minimal GET audit writes. Then recorded exact three-route admission before any server gate activation and real browser acceptance. The completion request expressly keeps these conditions; no self-admission.
5. **Upstream transport:** retain the existing unresolved infrastructure acceptance item. No additional SSL investigation, Management API call, backend pg_stat_ssl probe, enforcement change or certificate download in this execution. It remains a mandatory admission issue unless the accountable established policy explicitly resolves it; client TLS success does not resolve it automatically.

**Next actionable approval:** identify the dedicated test mailbox/custodian and authorize the supported verified-email/MFA Support provisioning operation with its exact grant executor. Fixture creation and live API audit writes require their own concrete safe mechanism/approval; no blanket cloud writes are inferred. Existing application functionality cannot truthfully be marked complete while these prerequisites are missing.

Outcome: **PHASE 9 READ-ONLY SUPPORT FRONTEND — IMPLEMENTED; LIVE ACCEPTANCE BLOCKED.** Original Step2 remains not passed. No unsupported mutations, no QR operations, no frontend admission/activation and no later phase started.


## Phase9 final implementation result under v1.1 (2026-10-24)

No remote/database/Auth/Management/JWKS/SMTP call, migration application, permission/login creation, identity/factor/grant/fixture write or local PostgreSQL change occurred in this task. Actual Cloud connection/111-table/head0043/TLS results remain previous evidence; no unnecessary repeat audit. The new source head0044 requires exact review/application authorization. New role/table/function/policy definitions are source findings, not installed metadata.

Executed isolated checks:151 focused backend (73 new +44 metadata +34 rehearsal),142 Auth/lifecycle regressions,73 frontend metadata,12 onboarding and23 browser checks; TypeScript and scoped Ruff passed.401 distinct checks, including existing174, do not prove real PostgreSQL ACL/RLS/locks/commit rollback or genuine provider/MFA acceptance. SQL provider predicates were exercised only after explicit SQLite dialect adaptation; transaction tests use scripted SQL and real local AEAD. Safe offline CLI preparation/check correctly fails before network when owner trust/UUID/permit is absent.

The current operator packet has no live decision/subject UUID or secrets. Ahmad is not a gate. Required next authorization is the exact reviewed0044 migration and narrow safereturn_support_command appointment on the fixed development project, followed by user-operated official Auth/email/MFA and exact identity binding/readiness, scoped rollback-only PG checks, then one explicitly approved <=24h grant with audit/encrypted receipt and authorized fixture/access-audit acceptance. No production/general role power or QR changes; no unsafe use of existing people/cases, no RLS/TLS bypass. Upstream transport evidence remains an existing acceptance item. Formal admission and real UI activation remain conditional; Phase9 not complete.
