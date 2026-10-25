# Phase 8 — local integration preparation

## Current status — development upgrade completed, 23 October 2026

The user explicitly approved applying the remaining development migrations, including a second informed approval after inspection found existing profiles/staff/catalog/history and explained that full backup restore verification remained incomplete. This supersedes the earlier backup/rehearsal stop for this development upgrade only. Existing records were preserved; no destructive reset was performed.

All 22 pending migrations (0022–0043) have now committed in one PostgreSQL transaction. A fresh read-only connection independently confirms installed/source head `0043_standalone_activation`, **no pending migrations**, and `single_checkout_release.enabled=false` / `standalone_owner_release.enabled=false`. Public tables increased from 45 to 111. Every previously nonempty table retained its original count: audit events 21, idempotency records 17, category 1, images 3, variants 2, products 2, staff roles 2, profiles 2. These count checks do not replace authenticated or historical workflow acceptance.

Actual PostgreSQL compilation found and fixed three pending-source migration defects:

- 0024: parenthesize CASE expressions inside cancellation IF predicates.
- 0025: parenthesize the financial decision reason CASE inside its IF predicate.
- 0043: extend the finder submission using the lock clause installed by 0014a (`FOR UPDATE OF p FOR SHARE OF q,l`), preserving that lock and explicitly rejecting an unexpected definition. The stale anchor omitted the inserted IF's terminator.

Failed attempts rolled back before the final successful commit. Focused tests passed: cancellation 51, financial disputes 55, standalone owner 22 (128 total). No environment file, seed/payment verification, notification, worker, deployment or release opening was performed. The private full backup remains available; full Supabase-compatible restoration, isolated concurrency/RLS suites, authenticated customer/admin/browser and provider/physical acceptance remain outstanding. Earlier sections below are chronological findings, not the current installed-schema status.

## Continuation — 23 October 2026

### Approved follow-up: backup obtained; full restore blocked

After the user's approval to proceed, downloaded the portable PostgreSQL 17.11 Windows binaries from EDB and verified SHA-256 against EDB's published checksum (`4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf`). No system service or environment file was installed/changed. Tools are under ignored `.local-tools/`.

Fresh read-only metadata inspection reconfirmed development PostgreSQL 17.11 and installed revision `0021_support_case_console`; source head remains `0043_standalone_activation`. The migration role has database/role creation capability but is not superuser. No customer records or credentials were printed.

A full custom-format `pg_dump` completed with exit 0. The private ignored archive is `tmp/phase8-private/development.dump`, 843,982 bytes, SHA-256 `bb8b62af60e61ad0e2f95ae79adc06f789791fa5652ece3bffc46e37660462b2`. `pg_restore --list` succeeded with 1,397 entries. The directory ACL restricts access to the task identity and local execution user. Do not commit, share, or expose the archive or private diagnostic logs.

**Restore verification failed:** a disposable PostgreSQL 17.11 cluster bound only to `127.0.0.1:55438` attempted a full restore with `--no-owner --no-acl --exit-on-error`. Restore exited 1 because the backup requires the managed **`supabase_vault` extension**, which is unavailable in the portable PostgreSQL distribution. The disposable server was stopped. Earlier local wrapper output-capture handling was corrected before this final attempt. Neither an archive listing nor a partial restore establishes recoverability; owner/ACL fidelity also remains unverified.

Required next step: provide or provision an isolated Supabase-compatible restore environment with the required extension and roles, verify backup restoration and grants there, then rehearse the entire populated migration chain and run PostgreSQL acceptance. No development schema upgrade or release-gate change is authorized until backup verification and rehearsal succeed. This continuation made no development writes, ran no workers or notifications, fabricated no payment verification, and did not run authenticated journeys or the PostgreSQL migration suites. Original legacy-preservation and integration gaps remain.

EDB sources: [portable binaries](https://www.enterprisedb.com/download-postgresql-binaries), [published 17.11 archive checksum](https://github.com/EnterpriseDB/edb-installers/issues/682).

The user now authorizes a verified restorable backup, isolated rehearsal, and development-only upgrade after both succeed. This supersedes the earlier read-only authorization described below; it does not authorize opening release gates.

Fresh read-only migration-role inspection confirmed installed `0021_support_case_console`, source head `0043_standalone_activation`, and 22 pending revisions. Both release-gate tables are still missing. The sandbox initially blocked the database socket (Windows 10013); an approved retry outside the sandbox succeeded without reading customer records.

**Backup prerequisite blocked:** `pg_dump`, `pg_restore`, `psql`, and Docker were unavailable on PATH; standard PostgreSQL/pgAdmin installation directories were absent. No backup was created or restore verified. No rehearsal, PostgreSQL acceptance suite, migration application, seed, notification, or gate update was performed. Development schema remains unchanged by this continuation. A compatible PostgreSQL client toolchain and an isolated restore target are required to proceed; do not treat an archive listing alone as a successful restore test.

The focused backend run had 230 passing checks and one stale migration-graph assertion expecting Phase 5 head. The assertion now follows the actual Phase 7 head; the foundation/preflight rerun passed all 37 checks (overlapping the first run). These are source checks, not PostgreSQL acceptance. Authenticated customer/admin, legacy public/profile/order/frozen-reprint preservation, worker/storage/provider and physical acceptance remain unverified.

No environment file was changed. For local frontend connection, set the server-only API origin in the launching PowerShell process after reviewing this configuration:

```powershell
Set-Location E:\Projects\SafeReturn
.\ops\start-local-backend.ps1 -EnvFile .\backend\.env
```

In a second PowerShell terminal:

```powershell
Set-Location E:\Projects\SafeReturn\frontend
$env:SAFERETURN_API_ORIGIN = 'http://127.0.0.1:8000'
npm run dev
```

These commands start local services only; the old development schema still prevents new-model integration. Preserve the frontend's existing configured browser origin/session boundaries. No authenticated journey is claimed from server startup or synthetic component tests.

## Actual database finding

Read-only inspection on 22 October 2026 found development database revision `0021_support_case_console`. Source head is `0043_standalone_activation`: **22 migrations are pending (0022–0043)**. The single-checkout and standalone-owner gate tables do not yet exist. The runtime database connection is restricted from reading migration metadata (`42501`); the explicitly selected migration connection successfully read it inside `SET TRANSACTION READ ONLY`.

No migration, seed, release-gate update, environment-file edit or deployment was performed. New independent-order flows cannot work against this installed schema yet. Liveness or a successful server boot must not be interpreted as business readiness.

## Connect the existing Next frontend

The frontend already has same-origin server relays. Configure its **server-only** local setting `SAFERETURN_API_ORIGIN=http://127.0.0.1:8000` when you are ready to change local configuration. Do not append `/api/v1` to that value: existing clients add the prefix. Keep the existing Supabase project, publishable key, web origin and session-signing configuration consistent with the backend. Never put database/service credentials into `NEXT_PUBLIC_*` variables.

Run from the repository root in a terminal:

```powershell
.\ops\start-local-backend.ps1 -EnvFile .\backend\.env
```

This explicitly loads the chosen file into the child server process using Uvicorn, binds only to loopback, and does not rewrite any environment file or parent environment. Stop with Ctrl+C. It applies no migrations, runs no workers and creates no test records. Use `-Port 8001` if needed and point the frontend at the same port. Do not use `localhost` and `127.0.0.1` interchangeably for the frontend's configured session/origin boundaries.

From a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Browser requests use the frontend relays, so this configuration does not need permissive backend CORS. A different browser frontend making direct cross-origin requests requires a reviewed explicit origin policy; wildcard CORS and client-side service credentials are not a workaround.

- API explorer: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Liveness: `http://127.0.0.1:8000/api/v1/health/live`
- Authenticated routes require a real access token from the configured Supabase project and a live database session. Staff operations also require the existing role/MFA checks. No development authentication bypass is added.

## Repeat safe preparation checks

From `backend`:

```powershell
.venv\Scripts\python.exe -m app.integration_check --env-file .env
.venv\Scripts\python.exe -m app.integration_check --env-file .env --database --metadata-role
```

The first command reads configuration presence and the local Alembic graph only. The second explicitly uses the configured migration connection for read-only revision/gate metadata. Neither command modifies process environment, creates schema, changes gates, reports URLs/credentials or reads customer records. Output always distinguishes schema/connectivity checks from integrated acceptance.

## Required next database step

The user has authorized **read-only inspection first**, not an upgrade of the configured database. Before any upgrade, identify an approved disposable clone/target and rehearse the complete chain 0022–0043 with existing data shape, Auth schema, runtime roles and history preservation. The opt-in PostgreSQL suites are available, but are not run implicitly: their fixtures create/drop isolated namespaces and roles and require explicit authorization for that target. Their cleanup is not a substitute for choosing the correct target.

After successful rehearsal, review the concrete backup, migration/application and rollback-by-stopping-admission procedure before applying it to the development database. Do not run `alembic upgrade head` simply to remove frontend errors.

New-model end-to-end testing additionally needs approved product template revisions/assets, official bank/Raast instructions, typed inventory, verified payment configuration, private evidence/print storage, worker configuration, and real purchaser/staff test accounts. Gate opening is a separate reviewed action after those checks; never substitute a screenshot for verified bank settlement. Phase 5–7 hold, replacement/repacking and physical acceptance limitations remain documented in their handoffs.

Phase 8 is **in progress, not complete**. Local launch/preflight tools are prepared; real upgrade/provider/worker acceptance and release remain pending.

Validation: temporary loopback Uvicorn startup succeeded; liveness/OpenAPI returned HTTP 200 (137 paths), anonymous independent-owner access returned 401. The temporary server was stopped. Eight preflight/liveness/readiness tests passed; scoped Ruff passed. The older exact API path-set test fails because it predates the accumulated routes; it was excluded from the focused passing run, not counted as passed.
