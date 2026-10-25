# Phase 9C — isolated local acceptance environment preparation

Date: 2026-10-24 (Asia/Karachi).

**CURRENT STATUS: approved blank local PostgreSQL cluster and empty acceptance database provisioned and running. Phase9D schema initialization is BLOCKED by missing provider-managed Supabase Auth schema/baseline roles; zero migrations applied. PostgreSQL/RLS/application-auth acceptance remains BLOCKED; all three metadata endpoints remain NOT ADMITTED.** Actual initialization results are in section9 and Phase9D isolation/dependency verification in section10. Sections1–8 retain chronological preparation findings; statements that provisioning had not occurred describe that earlier stage.

## 1. Selected approach and actual tooling

Use existing workspace portable PostgreSQL **17.11** for an initial dedicated blank cluster, subject to exact local provisioning authorization. No new infrastructure framework, download, system service, Docker image or global PATH/configuration change is needed for that limited step. This is preparation for PostgreSQL testing, **not a complete substitute for Supabase Auth**. A genuine local Supabase-compatible auth stack remains a separately blocked portion.

| Discovery | Actual evidence |
|---|---|
| Portable PostgreSQL | `.local-tools/pg17-core/pgsql/bin/{postgres,initdb,pg_ctl,psql}.exe` all returned version17.11 via `--version`. Another tool tree exists at `.local-tools/pg17/pgsql/bin`; it was not selected or started. |
| Existing convention | `docs/LOCAL_FRONTEND_BACKEND_PHASE8.md` records prior approved portable17.11 use and checksum provenance. Its past remote development-upgrade approval is not authorization for this new cluster or use of its real-data archive. |
| Version requirements | Technical/database design requires PostgreSQL/Supabase but supplies no overriding phase-specific major pin found in the reviewed requirements. Runbook contains a postgres:16 example; it is not proof of an active local stack.17.11 matches the existing portable/development precedent and is an explicit proposed local target, not a newly claimed universal minimum. |
| Docker/Supabase/PostgreSQL tools on PATH | docker, supabase, postgres, pg_ctl, psql and podman not found. wsl is on PATH; no distribution was started or assumed to contain usable DB/auth tooling. |
| Common installation paths | Docker Desktop executable, Program Files PostgreSQL/Podman and Chocolatey Supabase executable absent at inspected paths. This does not prove no other installations exist. |
| Existing local stack config | No Compose/Supabase config found in reviewed repository paths. No local database identified/adopted. Port55439 availability remains unverified. |
| Existing environment | backend/.env runtime/migration/test DB and auth targets remain non-loopback/unverified. Values were parsed for classification only, not printed or used. No remote target contacted. |
| Proposed data paths | `tmp/phase9c-local` and `tmp/phase9c-local/pgdata` did not exist at preflight. No previous cluster/backup/data directory adopted. |

The prior Phase9B finding that tools were absent **on PATH** remains accurate, but is superseded as an overall tooling blocker by this deeper portable-binary discovery. Earlier development migration history is not freshly verified; no remote metadata inspection was performed here.

## 2. Prepared files and isolation design

- `ops/phase9c/local-environment.example.json`: non-secret, inert manifest. It is not automatically loaded by FastAPI, Alembic or existing tests.
- `backend/scripts/phase9c_local_preflight.py`: read-only preflight; validates the exact reviewed manifest, resolves workspace paths, rejects state-path links/junctions and reports binary versions, existing paths and presence of inherited DB settings. It **cannot** run initdb/pg_ctl start/psql connections, create directories, initialize schema, restore data or provision identities. The only subprocess argument is `--version`.
- This document and the appended integration tracker entry. Existing environment/application/security/migration files unchanged.

Proposed identity: database **safereturn_phase9c_acceptance**, listen address **127.0.0.1**, port **55439**, cluster data **E:\Projects\SafeReturn\tmp\phase9c-local\pgdata**. Bootstrap role would be `sr_phase9c_bootstrap`, confined to this new local cluster; application runtime later uses existing reviewed restricted runtime-role semantics, never bootstrap credentials. These are planned names, not created objects or enrolled users.

Future launcher must use a sanitized child environment, explicit executable/data-directory/host/port/database arguments and a separately approved local-only configuration file, never inherit/import backend/.env or a PG service/passfile. Exclude inherited PGHOST/PGHOSTADDR/PGPORT/PGDATABASE/PGUSER/PGPASSWORD/PGSERVICE/PGSERVICEFILE/PGPASSFILE/PGOPTIONS and SafeReturn DB/auth settings before any connection. Preflight merely reports presence; it is not an executable launcher authorization or proof that future processes are isolated.

Cluster must bind only IPv4 loopback, use SCRAM authentication, restrictive loopback-only pg_hba entries and private per-run credentials/files with task-user ACLs. No trust authentication, shared system role, non-loopback binding, worker, storage/provider adapter, production credentials, data dump or copied customer record. Do not reuse `tmp/phase8-private/development.dump` or any prior cluster; that archive contains real development records and previously required unavailable Supabase extensions. No system service/autostart registration. Verify unused port, absent target paths and local filesystem resolution again immediately before initialization. OS/network isolation beyond explicit local configuration remains an acceptance check, not a claim already established here.

### Required non-secret settings (future approved process only)

| Setting | Intended value / constraint |
|---|---|
| PGDATA | Exact new workspace data directory above; no linked or existing directory adoption |
| PGHOST / PGPORT / PGDATABASE |127.0.0.1 /55439 /safereturn_phase9c_acceptance; explicit flags override no ambient defaults |
| PostgreSQL major |17, observed tool version17.11 |
| Acceptance mode | Local only, workers/providers/mutations/frontend disabled |
| Supabase URL | **Unconfigured** until a genuine approved local HTTPS issuer/JWKS/Auth stack exists; never substitute the existing remote URL |
| Approved schema target / fixture version | **Unconfigured** until full source/execution-path and identity/fixture review completes |

SAFERETURN_DATABASE_URL, SAFERETURN_TEST_DATABASE_URL and any migration URL contain secrets and are **not included** in the public manifest. Later generate unique local credentials into a separately approved ignored/private file, never command arguments, logs or chat. Likewise profile cursor keys, local auth signing secrets, passwords and MFA secrets are separate controlled secrets, not invented evidence or hardcoded privileged tokens. No new .env file, password, token, certificate or key was generated here.

## 3. Database initialization procedure — NOT EXECUTED

The user request's section4 requires existing explicit local test authorization before creating a database/starting infra. Existing tests authorize only separately selected rehearsal targets; no existing configuration authorizes this new cluster's init/start/database creation. Therefore stop before mutation and request approval for this precise, limited operation:

> Initialize a fresh PostgreSQL17.11 cluster under E:\Projects\SafeReturn\tmp\phase9c-local\pgdata, with a new local-only bootstrap credential; start it hidden on127.0.0.1:55439; create only the empty database safereturn_phase9c_acceptance. No migrations, auth identities, support fixtures, workers, restores, remote connections or frontend changes.

After that approval, a separately reviewed local bootstrap implementation must:

1. Rerun preflight, verify binary paths/versions, state path absence/no links and unused loopback port. Refuse to adopt any existing cluster. Establish private ACLs for the dedicated new state directory. Reconfirm sanitized local child environment and target identity.
2. Generate a fresh per-cluster bootstrap secret into a private password file; run selected initdb with explicit PGDATA, `--username=sr_phase9c_bootstrap`, `--auth=scram-sha-256`, UTF8 and reviewed local locale/password-file options. Never echo the file/secret.
3. Set only the new cluster's listen address/port and reviewed local HBA. Start through pg_ctl or a hidden helper, bounded timeout and local-only private logs; no visible persistent console or system service. Verify actual data_directory, server address/port, role/DB identity and non-shared state before proceeding. A loopback hostname alone is insufficient identity proof.
4. Create only the named empty acceptance database using explicit local connection parameters and private password delivery. Record non-secret cluster/run identity and empty initial state without querying any pair table. Stop before application migrations or test records. Cluster initialization necessarily creates PostgreSQL's own system databases/catalogs; no business records are authorized by this limited approval.
5. Retain explicit status **blank local PostgreSQL only; no SafeReturn/Auth/RLS acceptance yet**. Permission for this skeleton does not authorize schema/identity/fixture writes.

No runnable mutating command/script is provided as a shortcut to these pending checks. No infrastructure was started by preflight.

### Schema, migrations and passive pair schema

Preserve the existing Alembic schema, RLS, ACLs, SECURITY DEFINER ownership/search paths, triggers and function logic. Fresh passive creation of pair-related schema is distinct from querying/populating/locking pair records, as allowed by the request. Defining a function containing pair SQL is not executing its body; installing a trigger is not firing it. Conversely migration backfills, validation/default expressions, DO blocks, invocation of functions, and fixture triggers can execute data access and require full review.

No migration was applied. Complete execution-path classification of the required chain remains pending; an AST/string scan was preliminary only and is not proof that all SQL files/dynamic execution/validation paths are passive. No `alembic upgrade head`, generic rehearsal, domain count or source-head stamping is authorized. Never remove a required migration or patch RLS/functions to force a partial test schema to pass. The phase needs existing support/history/role/account/abuse-policy definitions, but their dependencies must be reconciled against the full approved chain before selecting an initialization procedure.

`0001_identity_profiles.upgrade` requires managed auth.users; `0005_account_session_guard` checks managed auth.users/auth.sessions fields; `0030_account_lifecycle.sql` checks session created_at/account admission; `0035_public_abuse_intake.sql` supplies the retained abuse readability policy required by metadata routes. Plain PostgreSQL does not create Supabase managed Auth. Handwritten substitute auth tables are not real provider/MFA acceptance and are not authorized here. No schema changes to pair tables outside passive approved fresh initialization, and no ownership/retention business logic changes.

## 4. Authentication/MFA setup — BLOCKED

Existing application is Supabase JWT/JWKS + live managed auth/session state + explicit Support role + verified email + signed/current provider AAL2. `Settings.validate_auth_origin` requires **HTTPS** even locally; `JWTVerifier` requires its existing supported asymmetric signing/JWKS path (legacy symmetric keys are unsupported). A default local HTTP endpoint, mocked JWKS, fabricated auth.sessions AAL2 row, disabled TLS verification or custom dev token is not genuine acceptance and must not be added as a production-enableable shortcut.

No usable local Supabase CLI/Compose/Auth stack or approved real enrollment fixtures were discovered. Future auth work needs explicit approved local stack/tooling/version selection, loopback-bound Auth services sharing this dedicated database, a trusted local HTTPS origin/certificate and correctly matching issuer/JWKS; exact TLS/issuer routing must be reviewed before choosing a service layout. External SMTP/storage/customer credentials and production auth are excluded. Installing/running such tooling or provisioning identities requires its own precise authorization, not this blank-PG skeleton approval.

Use actual approved local test identity mechanisms to enroll disposable verified staff, factors, challenges and provider AAL2 sessions; keep secrets in controlled local files. Negative scenarios require approved local wrong-role/unverified/expired/revoked sessions and a separate staff identity for assignment denial. Do not infer Support from frontend roles or manufacture role/enrollment provenance. Existing `pg_rehearsal.py` creates minimal synthetic auth tables and `test_support_cases.py` writes synthetic AAL2 sessions; neither demonstrates provider enrollment and neither is executed here.

## 5. Synthetic Support fixtures — prepared requirements, NO RECORDS CREATED

| Scenario | Needed data / current status |
|---|---|
| Assigned, unassigned, other-assignee/outside queue | Approved disposable identities and existing-schema synthetic cases. **BLOCKED** for creation-path and identity approval. |
| Missing case | Fresh arbitrary UUID can be used as a negative request only after a real authorized environment exists; no row needed. Not executed. |
| Restricted metadata / retained abuse | Genuine approved test policy/version/triage/retention scenario and linked synthetic case; **BLOCKED**, no invented policy/duration/approval. |
| History/no history and no note/actor disclosure | Existing append-only event fixtures with valid references, including synthetic note data; **BLOCKED**, no event writer bypass or manual identity forgery. |
| Missing abuse helper/policy | Use a separately reviewed disposable isolated-schema scenario; no dropping helpers from production/shared/test data in use. **BLOCKED** pending approved setup/teardown. |
| Bad cursor / filters | Already covered by isolated suite; real PostgreSQL cases remain pending. |

Fixture creation cannot use the five original quarantined APIs, general Orders, workflow_sample or pair fixtures. Crucially, `sr_retention_dispute_admission` fires on new open/investigating support cases, and `sr_retention_admission` executes an order_pair_units query even with null pair/order references. Thus ordinary direct INSERT is not a safe setup shortcut under this task. Do not disable triggers/RLS, set replication role, fabricate closed/resolved cases to evade admission, alter the protected helper, or copy private real data. No approved independent fixture mechanism was found. Keep affected scenarios blocked until a separately approved safe fixture design preserves those protections and proves zero prohibited execution.

## 6. Safe commands and verification actually executed

From repository root, read-only preparation (no initialization/connect/start):

```
backend/.venv/Scripts/python.exe -B backend/scripts/phase9c_local_preflight.py
```

**Passed:** exact local manifest; four tools17.11; state/data directories absent; relevant inherited DB settings absent; approval required; port availability unverified; database isolation designed, not provisioned; real Auth/MFA, fixtures and migration review blocked. Preflight does not prove production cannot be reached by unrelated machine processes.

From backend, after reviewing fixture/setup/teardown:

```
.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider
```

**44 passed in2.91s.** Only isolated ASGI with synthetic signed JWT/AEAD, mocked JWKS and scripted transaction/SQL double; no DB/real provider. This checks the three registered GET shapes and covers authentication/email/MFA/Support/scope/history/content=false/filter/cursor/error/minimization and forbidden SQL/service/routes at that boundary. It is not PostgreSQL/RLS or genuine MFA enrollment evidence.

From repository root:

```
backend/.venv/Scripts/ruff.exe check backend/scripts/phase9c_local_preflight.py backend/app/api/v1/support_metadata.py backend/app/services/support_metadata.py backend/tests/test_support_metadata.py
```

**Passed.** The new preflight file alone was formatted. New JSON/document consistency and whitespace checks are performed before delivery. Existing handler/service/test application code remains unchanged.

| Verification category | Phase9C result |
|---|---|
| Static source/configuration/migration/auth/fixture review | Performed, with unresolved full migration/fixture execution proof explicitly retained |
| Portable executable version inspection/read-only preflight | Performed; no infrastructure start |
| Mocked DB/auth unit/ASGI tests |44 passed |
| Local PostgreSQL integration/RLS/lock tests | NOT EXECUTED — no provisioned/authorized local schema/data |
| Local real Auth/MFA acceptance | NOT EXECUTED — no approved local stack/enrollment |
| Remote staging / production verification | NOT EXECUTED; no remote targets contacted |
| Excluded APIs/pair services or record access | NOT EXECUTED; no prohibited operation attempted |

The three endpoints remain registered in source/isolated OpenAPI: GET `/api/v1/admin/support-case-metadata`, GET `/{case_id}`, GET `/{case_id}/history`. No content/mutation/financial API or frontend connection added. Full nested installed PostgreSQL/RLS/Auth/policy/lock/response acceptance and governance approval are still required for allowlist review. Phase9B/9C are not complete.

## 7. Cleanup and security boundaries

There is currently no created cluster/database/identity/test record to clean up. The committed manifest and preflight are inert preparation artifacts. Do not delete `.local-tools`, old local clusters, private backups or arbitrary tmp directories.

After future authorized provisioning, stop only the verified Phase9C cluster using its exact recorded data path/process identity and bounded pg_ctl stop. Before any removal, resolve paths, reject links/junctions, verify the dedicated phase9c-local path remains inside this workspace, match run/cluster identity and confirm the process stopped. Cleanup authorization is not implied for unrelated state. If approved to discard this disposable run, remove only its exact private state directory with native PowerShell LiteralPath; no wildcard deletion, cross-shell path passing, shared role deletion or destructive database reset. Never terminate a server solely because it listens on55439. Local auth services/factors/records later created require an explicit recorded ownership/cleanup plan; none were created here.

## 8. Exact next action / authorization request

Approve or decline **only the blank PostgreSQL skeleton operation in section3**: new workspace-local cluster, local bootstrap secret, hidden loopback-only server on55439 and empty `safereturn_phase9c_acceptance` database. This request is required by the user's Phase9C section4, not inferred from a skill; existing rehearsal authorization does not cover a new target. It does not include migrations, real/local auth identity enrollment, policies, support records, production/shared infrastructure or any remote target.

After approval, implement and review the bounded local initializer and run its isolation checks before mutations. Separately resolve genuine local auth/TLS/MFA tooling and the protected-trigger fixture barrier before claiming real acceptance. Do not admit/connect endpoints merely because an empty PostgreSQL cluster exists.

## 9. Approved limited initialization — actual results (2026-10-24)

The owner explicitly approved a fresh17.11 cluster only at `E:\Projects\SafeReturn\tmp\phase9c-local\pgdata`, a hidden server bound only to127.0.0.1:55439 and creation of only the empty `safereturn_phase9c_acceptance` database. Approval expressly excluded application schemas/migrations, fixtures, staff identities/MFA, production/remote connections, existing databases, QR operations, APIs and frontend integration. This limited operation is now complete; broader Phase9B/9C acceptance is not.

### Preconditions and implementation

- Exact workspace paths were resolved and checked for links/junctions and containment. Both the dedicated run directory and data directory were absent; no existing cluster or state was adopted or overwritten.
- An exclusive Windows IPv4 socket bind to127.0.0.1:55439 succeeded before initialization and was repeated immediately before server startup. This check opened no PostgreSQL connection and ran no listener. A later competing port use would cause startup failure, not redirection to another cluster.
- Existing portable postgres/initdb/pg_ctl/psql/pg_controldata binaries all matched17.11. No software downloaded, installed globally or added to PATH.
- Added `backend/scripts/phase9c_initialize_local.py`, requiring an explicit approved-initialization CLI flag, exact workspace/version/path, absent run directory and free port. It refuses to adopt or reset this now-existing cluster, and must not be rerun to restart or verify it. Its database-creation helper is named `create_and_verify_empty_database`; it is not a read-only health check.
- Each child process receives a sanitized environment with inherited PG*/SAFERETURN_* variables removed. Every psql connection has explicit IPv4 host, port, local bootstrap role and database, disabled psqlrc/password prompting and a dedicated private passfile. No PG service/default target or existing .env is loaded.
- New local bootstrap secret generated without printing it, passing it on a command line or reusing production credentials. Initdb used explicit data path, UTF8/C locale and SCRAM-SHA-256 for authentication. The one-time initdb password file was removed after successful initialization; the dedicated connection passfile remains only under private ignored run state.
- Run-directory ACL inheritance was removed and access restricted to the execution account and SYSTEM. Final private-directory ACL inspection confirmed only those two inherited entries. No permissive trust rule, non-loopback host access, security bypass or staff/provider identity was created.
- PostgreSQL configuration fixes listen_addresses=127.0.0.1 and port55439; HBA permits only the dedicated cluster bootstrap role from127.0.0.1/32 using SCRAM, followed by IPv4/IPv6 rejection rules. No system service/autostart registration or worker/provider process.

### Startup handling

Initdb succeeded. The initial `pg_ctl start` attempt failed before server startup because Windows restricted-token creation returned error87 under the already restricted execution account. No postmaster PID file/server existed after that failure, and no acceptance database had been created. Private diagnostics were retained without disclosing credentials.

The reviewed initializer was changed to launch standard `postgres.exe` directly with Python `CREATE_NO_WINDOW`, stdin detached and stdout/stderr redirected to the private local log. This retains the same existing restricted OS identity/token; there was no elevation, token modification, authentication relaxation or visible console. The exact newly initialized path, HBA, absent postmaster and free port were revalidated before this start. No second cluster was initialized.

The first authenticated identity check stopped before CREATE DATABASE because PostgreSQL's inet-to-text representation includes `/32`. A read-only check confirmed the expected exact data directory/system identifier/listener; the check was corrected to use `host(inet_server_addr())`. Only after all identity predicates matched did creation of the one authorized empty database proceed. This was a representation correction, not a relaxed host check or failed database acceptance result.

### Actual non-destructive verification

| Check | Actual result |
|---|---|
| Server | PostgreSQL17.11, running under the local execution account, hidden launch |
| Data directory | `E:\Projects\SafeReturn\tmp\phase9c-local\pgdata` matches server-reported path |
| System identifier |7699958636828271396, matched between local pg_controldata and authenticated pg_control_system |
| Listener | netstat showed only127.0.0.1:55439 for postmaster PID1724 at verification; no wildcard/IPv6/other listener for that process |
| Database | safereturn_phase9c_acceptance exists; authenticated connections explicitly targeted it |
| Cluster databases | postgres, template0, template1 and only the one new acceptance database; the three system databases are inherent to fresh initdb, not modified pre-existing databases |
| Empty application state |0 user relations and0 user functions; only the default public user schema inherited from PostgreSQL template initialization, no explicit/application schema creation |
| Authentication | Bootstrap password verifier is SCRAM; HBA parsing errors0, configuration errors0; no verifier/password contents returned |
| Independent final check | Fresh psql process/session with default_transaction_read_only=on confirmed the exact database/address/port/data path/system ID and empty catalogs |
| Private state | `tmp/phase9c-local/private/pgpass.conf`, data and initialization report confirmed ignored by Git |

Non-secret initialization evidence is also saved in ignored/private `tmp/phase9c-local/initialization-result.json`. Local PID and port occupancy are point-in-time observations, not indefinite health guarantees. No database credentials, password, key or token were printed. Root-level metadata checks concerned only this newly created cluster; no production/shared/remote connection was used.

Ruff check and formatting check passed for the new initializer. Documentation/whitespace checks completed before delivery. No backend API/unit/ASGI/application test suite was rerun during this limited initialization continuation: after the authorized creation, only non-destructive local instance/empty-database verification was performed. The44 isolated tests earlier in this report remain historical preparation evidence, not a new PostgreSQL/RLS/auth acceptance result.

### Scope retained and stop

**No migrations applied; no application schemas, test fixtures, support/history records, staff identities, MFA factors/enrollment or policies provisioned. No auth/API/frontend integration, pair operation, restore, production/shared/remote database use or change to existing clusters.** The bootstrap PostgreSQL administrator is an inherent local cluster role, not a SafeReturn staff/customer identity. Existing protected Support/Finance and independent Phase4 Orders source remains unchanged.

This limited initialization approval has been fulfilled. The server is left running as approved; no destructive cleanup or reset was performed. Future restart/stop commands must verify the exact data directory/system identity and process, never identify a server solely by a port. The initializer intentionally refuses this existing run directory. Private run state remains under the existing ignored tmp root with restricted ACLs.

**PostgreSQL/RLS/application-auth acceptance has NOT passed; metadata endpoints remain NOT ADMITTED.** A blank cluster has no SafeReturn RLS/schema, genuine local Supabase Auth/MFA or approved support fixtures. The full migration execution-path review, managed Auth/TLS/JWKS/enrollment and retention-trigger fixture barriers in sections3–5 remain. Separate explicit authorization is required before any migration/schema work, fixture creation, staff identity or MFA provisioning. Stop here; do not execute those steps under the completed blank-cluster approval.

## 10. Phase9D — schema initialization preflight BLOCKED (2026-10-24)

The owner now authorizes existing approved non-destructive migrations only on the verified empty local acceptance DB, preserving order/RLS/grants/triggers/functions, with no migration-source edits, invented replacement schema, identities or fixtures. **That authorization is sufficient for eligible SafeReturn migrations; it does not supply the missing managed Auth prerequisite. No repeat approval of the already authorized migration command is requested.** No schema installation was attempted because the first migration's prerequisite is demonstrably absent.

### Isolation verified before any database write

Fresh psql sessions used the existing private local passfile, explicit127.0.0.1,55439,safereturn_phase9c_acceptance and local bootstrap role, with inherited PG*/SAFERETURN_* removed. No existing .env/default service/remote setting was loaded. `default_transaction_read_only=on` enforced catalog-only inspection. Verified:

- server address127.0.0.1/port55439/database exactly approved;
- PostgreSQL server_version_num170011, exact Phase9C data directory and system identifier7699958636828271396;
- zero application relations/functions and no public.alembic_version;
- auth schema absent, auth.users and auth.sessions absent;
- anon/authenticated and the four expected safereturn runtime roles absent;
- required support/staff/audit/account/abuse tables and functions absent; expected support policy count0.

Only PostgreSQL catalogs/information about this local instance were read. No application data, pair record, existing/shared/remote DB, migration or DDL was accessed/executed. The initialized cluster was neither restarted nor reset.

### Migration framework and dependency sequence

Existing framework: SQLAlchemy2 + Alembic, `backend/alembic.ini`, `backend/alembic/env.py`, and frozen version files under `backend/alembic/versions`. env.py supports an explicitly injected reviewed connection via Config.attributes; its fallback Settings path must not load the existing unverified remote settings. It excludes managed auth objects from migration metadata. No `Base.metadata.create_all`, standalone replacement DDL, autogeneration, stamping or SQL patch is permitted/used.

Static revision/down_revision inspection identifies the minimum retained-abuse-policy target as **0035_public_abuse_intake**, with **36 ordered ancestors including that revision**. Source head is0043_standalone_activation, not a reason to apply unrelated later revisions. Do not cherry-pick later helpers or skip their ordered ancestors:

```
0001_identity_profiles → 0002_commerce → 0003_workflows_security
→ 0004_runtime_privacy → 0005_account_session_guard
→ 0006_qr_batch_template → 0007_qr_batch_environment
→ 0008_atomic_activation → 0009_activation_rechecks
→ 0010_profile_consent → 0011_profile_owner_locks
→ 0012_public_qr_projection → 0013_public_contact_actions
→ 0014_public_finder_messages → 0014a_notification_delivery
→ 0015_public_catalog → 0016_checkout_quotes
→ 0017_print_download_grants → 0018_fulfillment_eligibility
→ 0019_retention_recovery → 0020_notification_operations
→ 0021_support_case_console → 0022_privacy_exports
→ 0023_saved_shipping_addresses → 0024_order_cancellations
→ 0025_financial_disputes → 0026_finance_reconciliation
→ 0027_manufacturing_exports → 0028_dashboard_reads
→ 0029_staff_directory → 0030_account_lifecycle
→ 0031_staff_account_state → 0032_owner_qr_lifecycle
→ 0033_print_template_drafts → 0034_print_template_publication
→ 0035_public_abuse_intake
```

Relevant source dependencies and expected installation (all currently absent):

| Source revision / external prerequisite | Required result and security boundary |
|---|---|
| Managed Supabase Auth, external to SafeReturn chain | auth.users/auth.sessions with actual provider-managed compatible columns, and baseline anon/authenticated roles. No staff/customer identity or enrollment is required merely to install their schema, but no approved local managed-Auth bootstrap currently exists. |
|0001 | staff_roles and shared schema/FKs to auth.users. upgrade explicitly rejects missing managed auth.users before executing its DDL. |
|0003 | support_cases, audit_events, case/staff RLS, actor/MFA/staff/safe-JSON helpers; approved API/worker role separation and scoped grants. Case assignment is support_cases.assigned_staff_id, not a separate invented table. Baseline role names are referenced, not provisioned by SafeReturn. |
|0005 | sr_account_session_state; requires managed users id/email_confirmed_at/deleted_at/banned_until/is_anonymous and sessions id/user_id/not_after/aal. |
|0021 | case_revision/priority/description_format and append-only support_case_events; SELECT-only runtime event grant and assigned-Support policy sr_case_event_read. |
|0030 | account_security_state and current account-epoch/session admission; additionally requires managed auth.sessions.created_at. |
|0035 | abuse_reports/abuse_intake_policies, restrictive sr_abuse_case_scope, sr_abuse_case_readable/marker/policy/gate and approved runtime EXECUTE grants. Missing helper is503 in the metadata service. |

### Exact blocker and safety decision

`backend/alembic/versions/0001_identity_profiles.py:upgrade` checks for managed auth.users and would raise **"Managed Supabase auth.users is required"**. This is a source-proven precondition failure, **not a failed migration run**; Alembic was not invoked just to reproduce it. The approved chain does not initialize Supabase's managed Auth schema.0001 also references baseline anon/authenticated roles in grants/revocations; neither exists.0005 and0030 have further compatible managed-session requirements.

The existing `backend/tests/integration/pg_rehearsal.py` instead creates substitute minimal auth tables, translates schema/role identifiers and rehearses a different temporary namespace. That is neither the genuine managed provider schema nor an approved initializer for this acceptance DB. It also inspects cross-domain data and is excluded here. Copying its auth.users/auth.sessions stubs, bypassing the guard, omitting migrations, using fake AAL2 rows, changing a migration or issuing improvised CREATE SCHEMA/TABLE/ROLE patches would violate this task. None was done.

Passive QR table/function/trigger definitions are distinguished from executing generation/allocation/lifecycle/record access. No pair-related migration or function body ran. The revision graph and prerequisite/security sources above were inspected; **the remaining full per-revision SQL/DO/backfill/destructive/grant/trigger execution audit is not certified complete**, because execution already stops at the first missing external prerequisite. No later migration is declared safe merely from its name or an empty target. Complete that audit before any future migration execution; do not infer blanket admission of the36-revision chain from this document.

### Actual installed state, tests and stop

**Migrations executed:0. Installed revision:none (no Alembic version table). Database writes:0 in Phase9D.** Catalog inspection confirms staff_roles/support_cases/support_case_events/audit_events/account_security_state/abuse_reports/abuse_intake_policies all absent; required actor/MFA/staff/session/abuse-readability/safe-JSON functions absent; support/staff policy count0; runtime roles absent, so expected runtime grants are not installed. No test customer, staff, support/history or pair records were created. There is no RLS/auth acceptance claim from these absence checks.

After rechecking isolated fixture/setup/teardown (only own new-router ASGI app, `_env_file=None`, mock JWKS, synthetic JWT/AEAD and scripted SQL):

```
# From backend:
.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider
.venv/Scripts/ruff.exe check app/api/v1/support_metadata.py app/services/support_metadata.py tests/test_support_metadata.py
```

**44 passed in3.24s; Ruff passed.** These are fresh isolated results, not local PostgreSQL/RLS/provider authentication acceptance. No identity/MFA/case/pair fixture or excluded Support/Finance/Orders route test ran. No application/backend/frontend/business-rule/environment/migration source changed; only this report and integration tracker updated.

**Next task requiring separate approval:** design/review and authorize a genuine local Supabase-compatible Auth infrastructure/schema bootstrap supplying managed auth.users/auth.sessions and baseline roles on this exact isolated target, with no identities or fixtures. Such a bootstrap must come from its actual supported provider mechanism, preserve security and remain local; this task supplies no existing approved bootstrap and does not authorize substituting one. After that prerequisite is approved/provisioned, complete the full migration safety audit and use the existing Alembic chain with an explicitly verified local connection. Identity enrollment/MFA and safe support fixture creation remain separate later approvals. All three endpoints remain **IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED**; frontend untouched. Stop at the documented preflight blocker.
