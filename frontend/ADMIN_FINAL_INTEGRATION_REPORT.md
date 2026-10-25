# SafeReturn final integration and launch-readiness assessment

Assessment updated: 25 October 2026 (Asia/Karachi). **NOT READY � EXACT BLOCKERS.**

This file did not exist at the start of the original assessment. Phase14 has now been **partially executed**, with actual authorized read-only results in section8; genuine signed-in acceptance remains incomplete. Earlier entries saying it had not started describe the state before25 October. No deployment completion record exists. The quarantine fix is recorded in section7. No accounts, credentials, cloud permissions, gate activation, migration application or deployment occurred.

## 1. Screen counts and actual integration state

Counting concrete `frontend/app/admin/**/page.tsx` files gives **43 route pages**, including list/detail/create variants and MFA. This is not the historical numbered design-screen count: Screen1 includes the shared shell and Screen26 is a review test, not a separate application page. Route existence does not establish a complete workflow.

| Source classification | Route pages | Scope |
|---|---:|---|
| Wired to real backend contracts; final live acceptance unproven | **16** | Products list/create/detail3; Templates list/create/detail3; Orders list/detail2; Payments lookup/attempt2; Print Jobs list/detail2; Shipment Item lookup/detail2; Users list/detail2. Narrow metadata or conditional operations only. |
| Implemented but module live-disabled | **15** | Overview Trends1; Support metadata2; Notifications2; Privacy metadata2; Finance Sync2; Storage metadata2; Audit2; My Staff Security1; Monitoring1. Overview Summary is additionally quarantined. |
| Other pages, not completed safe API integrations | **12** | Inventory2, Batches3, QA2, Ready-to-ship1 and Finance Reconciliation1 are now inert unavailable pages; Payment Review1 and Support Create1 remain unavailable; MFA1 is the existing authentication flow, not a business module. |

**Live-accepted end-to-end Admin screen count is not established.** The16 wired pages must not be called16 verified online workflows. Fifteen gated pages correspond to15 literal-false admission functions across five gate files; those function counts also include separate mutations/quarantines and are not a one-function-per-page mapping. The existing own staff-security authentication bootstrap remains active independently of its disabled panel.

Incomplete/unavailable functions include template publication and genuine authority/asset/physical-QA prerequisites; payment settlement/allocation; manufacturing/artifact delivery; global shipment readiness/dispatch workflows; user lifecycle commands; Support create/claim/edit/financial actions; Privacy decisions/export delivery; retention hold/release/cleanup; Dashboard Summary/order-placement trends; global staff management; and monitoring beyond process liveness. Some are intentional security exclusions or unsupported contracts, rather than missing UI code. Read-only lookups do not replace them.

## 2. Exact quarantined APIs

All paths below are prefixed `/api/v1`. These are the corrected inventory's **23 QUARANTINED operations**. Separately, its **47 QR-PAIR EXCLUDED operations remain excluded**; see the [authoritative exclusion table](ADMIN_BACKEND_API_INVENTORY.md#explicit-exclusion-and-quarantine-table). The corrected162-operation taxonomy is not a count of accepted online APIs.

| Method | Path |
|---|---|
| POST | /admin/qr-inventory/batches |
| GET | /admin/qr-inventory/batches |
| GET | /admin/qr-inventory/batches/{batch_id} |
| GET | /admin/qr-inventory/summary |
| GET | /admin/qr-inventory/codes |
| GET | /admin/qr-inventory/codes/{qr_id} |
| GET | /admin/support-cases/{case_id}/independent-qr |
| GET | /admin/orders/{order_id}/qr-allocation |
| POST | /admin/orders/{order_id}/qr-allocation/retry |
| GET | /admin/orders |
| GET | /admin/shipments |
| POST | /admin/storage/artifacts/{artifact_id}/cleanup-retry |
| POST | /admin/storage/artifacts/{artifact_id}/retention-holds |
| DELETE | /admin/storage/artifacts/{artifact_id}/retention-holds |
| GET | /admin/support-cases |
| POST | /admin/support-cases |
| PATCH | /admin/support-cases/{case_id} |
| POST | /admin/privacy/exports/{request_id}/decisions |
| GET | /admin/support-cases/{case_id}/financial-review |
| POST | /admin/support-cases/{case_id}/financial-decisions |
| GET | /admin/finance/reconciliation |
| GET | /admin/finance/reconciliation/counts |
| GET | /admin/dashboard/summary |

Independent Orders/Shipment/Support metadata contracts do not admit these mixed legacy endpoints. Template publication API-307 is separately BLOCKED; acceptance cannot override that prerequisite failure.

## 3. Concrete release blockers

1. **Quarantine containment defect FIXED in the authorized follow-up.** The originally reachable Inventory/Batches, Reconciliation and Fulfillment adapters and additional shared payment/print/customer aliases are now contained at server outbound boundaries. Nine legacy pages are inert; direct legacy API methods return403 before auth/parsing/forwarding. See section7 for exact boundaries and actual verification. This specific blocker is closed in source/local production-build tests; it does not close genuine online security acceptance.
2. **Shared genuine security acceptance is incomplete.** Approved safe actors/fixtures, verified email/live sessions, genuine MFA, role/capability denial and revocation, signed recent authentication where required, and record/assignment/case authority have not passed consolidated deployed acceptance. Installed RLS, helper ownership/search_path/ACLs, transaction/audit rollback and relevant concurrency/expiry behavior need actual enforcement evidence. Isolated JWT/scripted-SQL tests are insufficient. The existing mandatory upstream-transport acceptance item remains open; prior TLS investigations should not be repeated merely to reset it.
3. **Module/provider prerequisites remain open.** Examples: Linux template-preview isolation and genuine enrolled assets/authority/physical evidence; Cloudinary configuration/attachment acceptance; safe notification fixtures/provider suppression and retry concurrency; Privacy case-bound authority; Finance worker lease/version/replay/unknown-outcome and approved Sheets behavior. Storage metadata must stay independent of quarantined cleanup. No approved dedicated Support actor exists in the latest record.
4. **Final release acceptance remains missing.** A fresh offline frontend production build now passes (section7). Backend image/build acceptance and consolidated deployed Auth/MFA/RLS/provider/browser acceptance remain unverified. Hosting configuration and an offline build alone are not release evidence.

## 4. Supabase Cloud and deployment configuration

Last recorded verified check: development project **fhuxryfkfrvycsojkzvq**, PostgreSQL17.11, sole installed revision0043, runtime verified TLS (`verify-full`); an actual loopback FastAPI process queried Cloud metadata and then stopped. The latest readiness catalog evidence is `tmp/phase9-step2/readiness-0044-evidence.json`, recorded2026-10-24T07:00:29Z. Thus database reachability was demonstrated; it is not the same as signed-in Admin acceptance. **Current reachability was subsequently verified on25 October** using read-only catalogs and the actual runtime driver (section8). No public deployed/continuously connected application is established by these local checks. The backend README's older0021 snapshot is not the latest catalog finding.

0044 remains unapplied and its real PostgreSQL security/rollback/concurrency/expiry/replay rehearsal is NOT EXECUTED. It is a development-only provisioning exception, not a blanket production migration prerequisite. Using that exception still requires its existing isolated-rehearsal, custody/credential and separate hash-pinned execution approvals; this assessment supplies none.

`frontend/vercel.json` declares Next.js, `npm ci` and `npm run build`; `backend/Dockerfile` declares a Python3.12 nonroot Uvicorn runtime. These do not prove a configured deployment, matching origins/callback allowlists, managed secrets, accepted feature flags, an available backend or approved provider/worker operation. No deployment configuration was changed.

## 5. Build/test evidence � prior assessment and authorized fix

| Check | Latest relevant recorded evidence |
|---|---|
| Frontend TypeScript | PASSED again for the quarantine fix; production build also completed TypeScript. |
| Phase13 isolated tests |115 Node +51 browser +29 backend passed; scoped Ruff passed. Affected Trends case subsequently passed again. |
| Phase12 isolated tests |65 Node +31 browser +28 backend passed; TypeScript/Ruff passed. |
| Production frontend build | **PASSED**: fresh `npm run build -- --webpack`, Next16.4.0; offline synthetic origins and build-worker fetch prohibition. Supersedes the stale October23 artifact. No live configuration/provider acceptance inferred. |
| Backend release artifact | Wheel built offline and93 packaged Python files matched source; artifact import/liveness passed. Docker image/Python3.12 container acceptance remains unverified (section8). |
| Final real Auth/MFA/RLS/provider acceptance | PARTIAL Phase14 execution (section8); genuine signed-in Auth/MFA/RLS/provider acceptance remains incomplete. |

Earlier module test results remain in the tracker; they are neither rerun nor added into a misleading single current-release total. The legacy Screen26 review suite uses older demo interfaces/fixtures and does not establish final current integration acceptance.

## 6. Minimum remaining actions; no new development phase

1. **Completed:** contain excluded/quarantined pages and server relays, preserve independent contracts and verify direct-route/method rejection. Keep this containment and its regression checks in the release.
2. Complete the already outstanding final acceptance for the permitted subset using the approved development project, authorized actors and explicitly safe fixtures: actual Auth/MFA/recent-auth/RLS/authority and module-specific rollback/concurrency/provider evidence. Resolve the existing transport-policy gate without treating verified client TLS alone as its closure. No account, migration, credential or provider mutation is authorized by this report.
3. Verify intended frontend/backend hosting, HTTPS origins/Auth callbacks, private runtime configuration and necessary approved provider/worker prerequisites. Frontend build and isolated containment browser checks now pass; backend release artifact and genuine deployed acceptance remain outstanding. Rerun only checks justified by changes or unresolved gaps.
4. Record final acceptance, approve eligible gates individually, then obtain explicit deployment authorization. Keep quarantined operations disabled. If development0044 provisioning is needed, satisfy its separate existing approvals first; do not apply it automatically.

**SafeReturn cannot currently be approved as a fully functional online Admin release.** The permitted subset can proceed only after these blockers close. Functionality that remains quarantined cannot be counted as fully functional under the present QR-pair exclusion. No new numbered phase or architecture is proposed or started.

Evidence: [integration progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md), [corrected inventory](ADMIN_BACKEND_API_INVENTORY.md), [mapping](ADMIN_FRONTEND_BACKEND_MAPPING.md), [0044 review](../docs/PHASE_9_MIGRATION_0044_DEPLOYMENT_REVIEW.md), current page/relay/gate source and deployment files named above.

## 7. Authorized quarantine containment fix � actual implementation

**Security defect fixed; overall launch status remains NOT READY for the separate live acceptance blockers.** No new numbered phase was started.

### Server boundaries and UI fixed

- `lib/api/quarantine-operations.ts` contains the exact corrected23 quarantined +47 excluded method/path operations. A regression compares all70 entries with the authoritative inventory, including ordering/content, so missing or extra rules fail the check.
- `lib/api/quarantine.ts` matches complete method/path patterns, not broad text prefixes. Dynamic IDs occupy one segment. Query parameters cannot alter the selected operation; ambiguous encoded/backslash/dot-segment/double-slash paths fail closed; HEAD inherits GET prohibitions; redirects are rejected. Independently allowed nested paths/methods remain separate (for example order payment-attempt/print metadata and shipment items). No URL forwarding authority is added.
- Every existing backend-fetching `lib/api/*relay.ts` and Next route handler now uses `guardedBackendFetch` before its actual upstream dispatch. Existing allowlisted path matrices, authentication, DTO limits, role/MFA requirements and live gates remain necessary. Fixed-path Auth bootstrap and public catalog code do not offer arbitrary operation selection; the shared transport checks its fixed operation too. The shared `qrClient` checks the same registry **before even an injected transport**, covering owner SSR/actions and old clients. Backend QR services are untouched.
- `/admin/inventory/api`, `/admin/orders/api` and `/admin/shipments/api` unconditionally reject GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS with403 and no module auth, body parsing or backend fetch. Legacy inventoryRelay/ordersRelay/qrLifecycleRelay implementations are inert too, protecting callers outside their old route handlers. Other unsupported Next methods remain framework405. A valid session, crafted parameters, legacy client, preview role or browser flag cannot admit them.
- `/admin/print-jobs/api` retains its safe GET metadata compatibility paths; all command/alternate methods reject before auth/body/fetch. Current safe `/metadata-api` and `/console-api` paths retain their existing contracts and guarded outbound calls. The obsolete admin branch of privacyRelay rejects before auth, preventing a second metadata/decision gate bypass; the existing independently gated Admin Privacy adapter remains unchanged in behavior.
- Shared `/payments/api`, `/checkout/api`, cancellation, account/customer and other mixed adapters are guarded at final outbound selection. Excluded reviews/allocation/legacy checkout/cancellation cannot forward even through those alternate URLs. Safe independent item-checkout, payment-attempt reads, evidence paths and separately approved non-pair operations are not blanket-disabled. Existing validation/auth may reject earlier; a prohibited target never reaches the fetch implementation. No new generic proxy or remote request was introduced.
- Nine pages now render AdminQuarantined with no controls, hooks, prefetch or redirect: Inventory list/detail; Batches list/detail/create; QA list/detail; Ready-to-ship; Finance Reconciliation. They ignore view=live and other enabling flags. No legacy consoles or mock mutation controls mount there. AdminShell also suppresses Inventory/Batches/QA/Ready-to-ship navigation for authenticated and preview modes; this is supplementary to server enforcement.
- Products/Templates, Phase4 independent Orders metadata, Payments reads, Print metadata, Shipment Items, User directory, Phase9 Support metadata, Notifications, Privacy metadata, Finance/Storage and Phase13 eligible read adapters preserve their independent contracts. All existing live-admission gates remain false. Their outbound calls receive the same additional exact deny check; no backend/RLS/Auth policy is weakened.

### Verification actually executed

All fixtures were read before execution. Tests use synthetic requests/SQL/JWTs and exact allowlisted upstream doubles; no prohibited backend operation, QR service, real Auth account, cloud object or migration was invoked. The local production build/server used synthetic origins/public configuration and a build-only Node preload that rejects all outbound fetches, including build workers. Ignored local configuration was not edited; no credentials were printed. The production smoke server was stopped afterward.

| Verification | Actual result |
|---|---|
| `node scripts/test-quarantine.cjs` | **131 passed**:70-operation outbound denial, inventory parity, canonical-path rejection, legacy adapters/routes/all seven methods/auth states/flags, shared injected-transport denial, mixed aliases and independently allowed operations, source coverage/no rewrites/no legacy page mounts. |
| Safe contract regressions | **697 passed checks** across existing scripts: Products55, Templates60, independent Orders34, Payments37, Print37, Shipment Items30, Users44, Support73, Notifications74, Privacy73, Finance/Storage65, Phase13 reads115. Synthetic only, zero excluded upstream requests. |
| `playwright.quarantine.config.ts` | **11 passed**: nine inert screens, browser-direct21 API requests and unsafe-page source controls/prefetch/redirect checks. |
| Fresh built production server | **40 passed**:9 actual Next pages,21 direct API method requests403,10 safe adapter unauthorized/gate-disabled outcomes. External browser requests0; upstream fetch unavailable by preload.375px unavailable screenshot visually inspected in tmp/quarantine-containment. This is local production-runtime containment, not signed-in cloud acceptance. |
| Scoped backend pytest | **57 passed** (`--noconftest`, test_phase13_frontend_contract.py + test_finance_storage_frontend_contract.py). Actual routers/synthetic JWT/scripted SQL only; no Summary/retention mutations/pair fixtures. |
| Scoped Ruff | **PASSED** for those backend tests. Backend source unchanged. |
| TypeScript | **PASSED**, both standalone and within the fresh production build. |
| Production build | **PASSED**, `npm run build -- --webpack`, Next16.4.0; compilation, TypeScript,25 static-generation tasks, optimization/tracing complete, exit0. Nonblocking existing multiple-lockfile/workspace-root warning remains. The first launch failed before compilation due to Windows preload quoting; corrected to forward-slash absolute preload path and reran successfully. |
| Protected hashes | **27 checked,0 changed**: selected backend/Auth/runtime/provisioning/migrations and all admission gates. Snapshot tmp/quarantine-containment/protected-before.json.0044 and production configuration remain unchanged. |

Safe browser regressions **all passed in their final rerun**: Orders14, Support23, Notifications25, Privacy28, Finance/Storage31 and Phase13 reads51 � **172 passed**, plus11 containment tests =183 isolated browser tests. Each output directory's .last-run.json records passed with no failed tests. The40 production-runtime checks are additional and counted separately. An initial overlap with the build failed on missing regenerated `.next` CSS before rendering; stopped and rerun. The new Webpack build also emits utility CSS in static/css, whereas old browser harnesses read only Turbopack static/chunks; this caused two Orders responsive failures with missing styles. A shared **test-only** compiled-admin-css.cjs loader now reads either actual output and refuses to test without CSS. No production Orders layout change or weakened overflow assertion was made. Final regression results contain no unresolved failures. Standalone TypeScript passed again after the test-loader changes.

### Remaining prohibited paths and next action

**No remaining frontend forwarding path to the70 listed operations was found in the inspected Next routes, shared transports, server relays, SSR/actions, legacy clients or redirects.** The operations still exist in the backend and are not deleted or modified; this frontend containment does not claim to revoke direct API privileges held outside the frontend. No current safe adapter can be admitted by query/localStorage/preview flags. Existing runtime backend authorization is still required, and all live gates remain disabled.

Exact next action: complete the already outstanding, separately authorized genuine Auth/MFA/recent-auth/RLS/authority and module/provider acceptance for the permitted subset, then verify the backend release artifact and obtain explicit gate/deployment approval. Do not re-enable the contained adapters or quarantine operations to satisfy that acceptance.0044/provisioning remains subject to its separate existing approvals. No deployment or cloud mutation is authorized by the successful containment build/tests.

## 8. Phase14 shared live acceptance execution — 25 October 2026

**PARTIALLY EXECUTED — NOT READY.** This is actual execution evidence, not an admission, deployment or another development phase. No earlier infrastructure investigation or full frontend suite was restarted. Existing development target fhuxryfkfrvycsojkzvq and FastAPI configuration were reused without alteration. Local FastAPI was started only for the checks and stopped afterward.

### Live verified

- Public liveness on the actual current FastAPI runtime,127.0.0.1:8030, returned200 and exact `{status:ok}`. This proves process response only.
- Nine eligible endpoints returned actual401/no-store without a token: current staff-security, Products, independent Orders metadata, Support metadata list, Notifications, Privacy metadata, Finance Sync, Storage metadata and Dashboard Trends. No protected payload, provider call or prohibited service was invoked. Real wrong-role/MFA/record-scope403 acceptance is not established by these anonymous checks.
- Existing runtime and configured catalog-inspection credentials connected to the pinned Cloud project with verified TLS. Every catalog transaction was READ ONLY and explicitly rolled back. Runtime could not read alembic_version (42501); the existing catalog-inspection connection confirmed the sole installed revision **0043_standalone_activation**. No privilege was changed to obtain it;0044 remains unapplied.
- Selected metadata:10 initial protected public tables had RLS enabled,34 policy records inspected; API/worker roles are not superusers, do not bypass RLS and cannot create roles. Six named Auth/dashboard/privacy/retention helper security records have postgres ownership and pg_catalog search_path. API EXECUTE is present for the intended public helpers; internal sr_export_authorized is not directly executable by API. These are selected metadata checks, not complete ACL equivalence or behavioral RLS proof.
- Actual `Database.from_settings` SQLAlchemy/psycopg runtime engine connected with its existing verify-full setting and confirmed PostgreSQL17.11 and permission to SET safereturn_api. A separate named catalog check confirmed privacy_exports has RLS and no direct API SELECT; its approved list uses the SECURITY DEFINER helper. The initial probe used the wrong table name privacy_export_requests; this was corrected by source inspection, not treated as a missing migration or repaired in Cloud.
- The fixed development Auth public JWKS URL returned200 over verified HTTPS, one ES256 public signing key and no private key material. This confirms the configured signing-key source, not any user's verified email/session/MFA.

Default sandbox connections initially failed; the same pinned authorized checks succeeded outside the sandbox. No TLS setting/CA/host/credential was changed and no expanded infrastructure investigation occurred. Evidence is under `tmp/live-acceptance-2026-10-25/`: evidence-network.json, runtime-engine.json, auth-public-configuration.json. Earlier failed sandbox attempts are retained separately, not reported as a Cloud outage.

### Tested offline only / release artifact

- Reused prior frontend build and697 safe contract/183 browser/57 backend results; did not rerun that suite.
- Executed only **21 focused direct-boundary checks** for Inventory/Orders/Shipments and all seven HTTP methods. All passed, zero auth/body/upstream calls. The70-operation registry/quarantine findings are reused; prohibited backend endpoints were never invoked.
- Built the backend wheel from the existing pyproject.toml configuration with pip wheel --no-deps --no-build-isolation and network index disabled. The existing backend venv lacked setuptools; reused the already installed local pgAdmin Python build tooling via a process-only PYTHONPATH, without installation/configuration/credential changes. The first attempt failed for that missing build backend; the second succeeded.
- Artifact: `tmp/live-acceptance-2026-10-25/artifacts/safereturn_backend-0.1.0-py3-none-any.whl`, SHA256 `cdb58130a4fa7f3f20417b1cb8baf1a29c425f81e9e2caa4ea8ca8f5a198cef3`. All93 packaged Python files match current app source byte-for-byte. Imported app.main from the wheel (not source fallback) and passed isolated artifact liveness. See backend-artifact.json.
- **Container artifact remains unverified.** Docker is not available; no runtime/infrastructure was installed. Local wheel smoke used existing Python3.14.8; it does not establish the Dockerfile's Python3.12/nonroot/Linux renderer/dependency acceptance.
- New runnable check: `backend/scripts/run_admin_read_acceptance.py`; scoped Ruff passed. It pins project/origin/verified CA, inspects only catalogs, performs fixed GETs, redacts failures and never records tokens or response rows. Optional --staff-token-file validates current-user security via the real backend; explicitly selected --read endpoints perform bounded GETs and cursor follow-up without fixture creation. Those optional authenticated branches have **not been exercised**. Field-name/shape observations alone are not full DTO/minimization/authority acceptance.
- All27 previously protected backend/Auth/gate hashes still match; no app backend service, migration, credentials or gate was changed. No new staff/session/role or provider operation was created.

### Authorization missing — exact current limits

No access token/cookie/browser storage-state input was supplied in the process or checked configuration, and no saved session candidate was found in the standard local test-state locations checked. This does **not** claim that no authorized staff account exists elsewhere. No Auth users, staff records or unrelated browser profiles were enumerated/adopted; no synthetic session, MFA bypass, login, token refresh or role grant was used.

The current frontend process/.env.local also does not provide its four required SAFERETURN_API_ORIGIN, SAFERETURN_WEB_ORIGIN, SAFERETURN_SUPABASE_URL and SAFERETURN_SUPABASE_PUBLISHABLE_KEY values. Prior synthetic build settings were temporary and are not genuine frontend configuration. Source may provide development defaults for some origins, but actual project/key configuration and callback acceptance are not established. See session-availability.json. Existing backend project/JWKS configuration is verified separately; it does not automatically configure the frontend.

| Endpoint/read integration | Missing independent admission evidence |
|---|---|
| Current Staff Security | Privately supplied current approved staff session; actual verified-email/MFA/capability projection and revocation. AAL1 bootstrap is not privileged acceptance. |
| Products and independent Orders metadata | Correct permitted actor/MFA, designated safe existing fixtures, positive read/role-denial/record-scope/RLS/pagination/schema/minimization checks. Existing frontend wiring does not imply acceptance. |
| Notifications | Operations/Security Admin MFA actor and designated safe outbox metadata fixture; no retries or worker/provider activity. |
| Privacy metadata | Security Admin MFA actor with existing approved case-bound authority/epoch and designated request fixture; no decisions or export generation/download. |
| Finance and Storage metadata | Correct Finance/Operations/Security roles and safe existing record scopes, actual SELECT RLS, cursors where supplied and minimized frontend projection. No finance retry, Sheets or cleanup. |
| Dashboard Trends / Templates / Directory | Genuine allowed actor plus explicit endpoint-specific backend configuration approval as needed: dashboard_enabled, print_template_management_enabled and staff_directory_enabled currently resolve false. No flag was changed. Scope requests independently; no global activation. |
| Support metadata and Audit | In addition to correct actors/MFA/case assignment/recent-auth for Audit, **successful Support list/detail/history and Audit search append mandatory access-audit events**. These authenticated reads were not executed under this read-only/no-cloud-write scope. Separately authorize the exact access-audit INSERT side effect if those reads are desired; do not disable mandatory auditing. Anonymous401 checks produced none. |

No authenticated pagination, sensitive-data redaction or cross-actor RLS result is claimed. Missing session/fixture authority is the blocker; no permission grant is inferred from schema existence. No pending migration is assumed to fix it.

### Provider acceptance pending / intentionally quarantined

Provider acceptance remains exactly as previously recorded: Cloudinary/media attachment, notification eligibility/delivery/suppression/retries, approved Sheets behavior and template physical/asset/authority/Linux isolation. Read-only acceptance cannot certify them. No providers were exercised and these are not automatic prerequisites for admitting an independently safe metadata endpoint when its own security acceptance is complete.

All23 quarantined and47 excluded operations remain denied.0044 and its separate rehearsal/approval blockers are preserved. No notification retry, settlement, Support mutation, Privacy decision, retention/cleanup or other provider/destructive action was executed. Existing mandatory upstream-transport policy acceptance remains open; verified TLS connectivity does not silently close that separate item.

### Smallest owner-controlled actions before admission

1. Supply/authorize the correct four frontend runtime values for the existing development project and intended development web origin; verify the existing permitted callback. No cloud Auth redirect/config change is implied or performed.
2. Sign in through the official flow with an **already authorized, designated staff test account**, confirm email and genuine MFA, and make its current session available privately. Do not paste tokens/passwords in chat. Roles must match each endpoint (Operations, Finance, explicit Security Admin or Support); one role does not inherit all access. If no suitable account exists, a separate approved provisioning action is required; this task did not authorize0044 or any grant.
3. Identify safe existing fixtures and authorize their exact read/RLS-negative/pagination scope. For Support/Audit, separately authorize the mandatory access-audit writes. For currently disabled backend features, authorize only the particular development feature configuration needed; keep frontend admission gates false until its evidence is accepted.
4. Complete the configured Dockerfile build/smoke checks on an existing Docker-capable build host (especially Python3.12/Linux/nonroot), then approve eligible read-only gates individually after genuine acceptance. Deployment and provider/mutation gates need separate approval.

Runnable current-user check once an existing session is privately supplied (no token value on command line):

```powershell
backend/.venv/Scripts/python.exe backend/scripts/run_admin_read_acceptance.py --staff-token-file <owner-controlled-private-existing-token-file> --output tmp/live-acceptance-2026-10-25/owner-session-evidence.json
```

This command requires the existing development backend at8030 and an authorized network execution context. It does not log in, mint/refresh credentials, grant roles, start services or admit endpoints. Add --read for a named approved bounded SELECT-only endpoint only after fixture scope is approved. Do not use broad legacy integration fixtures. **No eligible frontend gate was enabled; Phase14 remains incomplete; no Phase15 was started.**

## 9. Development staff login setup —25 October2026

The owner confirmed an **already authorized staff test account exists**. No provisioning action, third-party approval, role grant or0044 is needed to sign that account in and enroll/verify its own authenticator through the existing approved flow.

### Configuration completed

Configured the following exact existing names in the ignored `frontend/.env.local`, preserving unrelated entries. Three public origins are fixed to the development setup below; the fourth value was reused from the pinned existing backend configuration without display. No private backend configuration was copied into the frontend.

| Existing variable | Required format / configured value |
|---|---|
| SAFERETURN_API_ORIGIN | Backend origin only, no path/query/credentials; `http://127.0.0.1:8030`. Nonloopback origins must use HTTPS. |
| SAFERETURN_WEB_ORIGIN | Exact browser origin only; `http://127.0.0.1:3100`. Use this same hostname and port throughout; do not mix localhost and127.0.0.1. |
| SAFERETURN_SUPABASE_URL | HTTPS project origin; `https://fhuxryfkfrvycsojkzvq.supabase.co`. |
| SAFERETURN_SUPABASE_PUBLISHABLE_KEY | Existing project's public `sb_publishable_…` key. Source requires this prefix; a legacy anon JWT, secret/service-role key or database password is not a substitute. Value not printed. |

No NEXT_PUBLIC aliases were invented. These server-read names come from lib/auth/config.ts and existing API relays. Next automatically loads frontend/.env.local; restart the frontend after changes. The configuration helper refuses a different backend project and copies only these four public settings. Existing backend .env, Cloud Auth configuration, permissions and gates are unchanged.

### Exact Windows commands

The first command is idempotent and already ran successfully. From a PowerShell terminal:

```powershell
Set-Location -LiteralPath 'E:\Projects\SafeReturn'
& .\backend\.venv\Scripts\python.exe .\frontend\scripts\configure-development-auth.py
```

Backend terminal (existing configuration; no migration startup):

```powershell
Set-Location -LiteralPath 'E:\Projects\SafeReturn\backend'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8030 --no-access-log
```

Frontend terminal:

```powershell
Set-Location -LiteralPath 'E:\Projects\SafeReturn\frontend'
$env:NEXT_TELEMETRY_DISABLED = '1'
npm run dev -- --webpack --hostname 127.0.0.1 --port 3100
```

Use one instance per port. Both processes were started for this task; don't launch duplicates while they are running. Webpack is used for this local login because the first Turbopack compilation did not finish within the login helper's navigation deadline. No production build, Auth logic or security policy was changed to address that tooling issue. The actual existing /login page subsequently compiled and returned200.

Optional owner-operated private Chromium window and existing current-user acceptance runner:

```powershell
Set-Location -LiteralPath 'E:\Projects\SafeReturn\frontend'
node .\scripts\staff-login-acceptance.cjs
```

The helper opens an ephemeral browser context, waits for manual official sign-in/MFA, verifies the current Supabase user, then passes only the existing access token through a child-process stdin pipe to `run_admin_read_acceptance.py --staff-token-stdin --session-only`. No token file, saved browser state, screenshot, trace, password/code capture or credential output. The existing runner's new session-only mode avoids repeating completed catalogs/anonymous checks. It invokes current-user staff-security only by default; no Support/Audit access-audit writes, provider actions or fixture enumeration. Optional further eligible reads remain subject to their approved scope.

### Browser steps

1. In the private window use `http://127.0.0.1:3100/login` (existing `/auth/sign-in` is an alias). Sign in with the existing authorized development account. Do not use Sign up or role preview. If the account's email is unverified, complete its normal provider verification before continuing; password sign-in itself needs no email callback exchange. A verification/recovery link, when used, must return to the existing `http://127.0.0.1:3100/auth/callback` permitted by the project. No Cloud redirect setting was changed here.
2. Normal redirect is /auth/continue. Existing staff with insufficient assurance is sent to `/admin/security/mfa?returnTo=%2Fadmin`; fully verified staff proceeds to /admin. Starting a fresh private context avoids unrelated prior activation-intent cookies.
3. If an authenticator exists, choose it and enter a fresh six-digit code. If none exists, click **Set up authenticator**, manually add the browser-displayed setup key to the owner's authenticator app, then click **Verify authenticator** with its current code. Keep that window open until verification finishes. Enable automatic phone time. The setup key is displayed only in the browser; never send it or codes to chat. Existing factors are not automatically replaced or removed.
4. Successful verification is checked against the provider and rechecked against the actual backend's current staff/MFA state. `/admin` is the success landing, not evidence that any module gate was admitted. If ordinary /account appears, staff role access was not established by the backend; do not self-grant or run SQL. A missing/lost existing authenticator requires the established owner-controlled recovery process, not a bypass through signup/password reset.
5. The secure helper writes only non-secret acceptance evidence to `tmp/live-acceptance-2026-10-25/genuine-staff-login.json` once a genuine session is available. Until that file records actual200/current MFA verification, signed-in acceptance is **PENDING**, not passed.

### Actual setup verification so far

Four settings validated, .env.local remains ignored; actual `/login` returned200; helper JavaScript syntax and scoped Python Ruff passed.27 protected backend/Auth/gate hashes match. No app Auth implementation, QR service, quarantine registry, staff privileges, migration0044 or live gate changed. Password, refresh/access token, private key and MFA secrets were not printed. The owner-operated browser was opened; genuine login result is recorded below when available. No Support/Audit successful read was invoked because mandatory audit-write authority is still absent.

### Login connectivity correction — 25 October 2026

The owner's first sign-in attempts returned the generic denied notice. A credential-free request from the sandboxed frontend runtime to the configured public Auth settings endpoint failed with EACCES. Restarted the same frontend with approved network access; the exact configured project/public key Auth settings request returned HTTP 200. No password request was synthesized, no identity inspected, and no credentials logged. This establishes public Auth connectivity, not successful authentication. Owner reports the same notice; the restarted server initially recorded GETs only, with no fresh login POST. Requested one hard refresh and manual submission at the pinned origin to obtain actual sanitized provider evidence. Genuine staff/MFA acceptance remains PENDING. All gates remain disabled.

Subsequent genuine owner submission succeeded: the running frontend recorded POST /login, /auth/continue, successful MFA action and GET /admin HTTP200. Owner confirmed the dashboard opened in the Codex side window. This verifies the live browser login/MFA workflow, but the private acceptance helper has a separate browser context and has not yet captured that session. No session was exported from the Codex window. Automated current-user acceptance evidence remains pending completion in the helper's own Chromium window; do not equate dashboard navigation with complete role/RLS/module acceptance.

The first helper timed out without receiving a session; a fresh private Chromium helper was reopened for owner completion. No automated acceptance receipt exists yet. Next.js startup emitted a dependency security warning; this task did not change dependency versions or treat the warning as resolved.

### Final verified result — 25 October 2026, 06:55:14 UTC

**Development staff login and current-user MFA acceptance PASSED.** Owner completed genuine sign-in and MFA in the private Chromium helper. Existing runner --staff-token-stdin --session-only returned GET /api/v1/me/staff-security HTTP200, exact response schema roles/mfa_verified/capabilities, mfa_verified=true and existing roles finance/operations. Capabilities included orders.read, finance.mirror, storage.metadata and notifications.manage; capability presence does not admit quarantined operations or enable gates. Evidence: tmp/live-acceptance-2026-10-25/genuine-staff-login.json. This supersedes the pending helper status above. The helper then closed its ephemeral window as designed; no global sign-out or role change was performed.

Live verified: public Auth connectivity, actual owner password sign-in, official MFA, real backend current-user staff response and existing role/capability projection. Offline only: prior module/containment suites remain as previously reported. Not executed here: module-specific authenticated RLS, pagination and redaction comparisons; Support/Audit success reads requiring audit INSERT authority; provider acceptance; quarantine operations; any mutation or deployment. Existing account has no support/audit role in this response; no extra role was requested or granted. Four runtime values are configured; no further owner action is required to fix development login. Future module read acceptance must use the existing genuine account with appropriate existing authorization and respect each endpoint's audit-write requirements. Gate activation still requires separate explicit approval and outstanding endpoint-specific acceptance. Next.js dependency security warning remains unresolved. Overall launch readiness remains NOT READY; this login prerequisite is now resolved.0044 and all disabled gates/70-operation containment remain unchanged.

### Product category selection correction — 25 October 2026

Fixed the active product editor's misleading category flow: dropdown now shows actual category slugs and disables inactive/non-qr-stickers choices; an explicit Use QR Stickers category button selects the existing eligible ID. The category manager passes its actual saved response to the editor; saving/activating the canonical category selects it and reopens editing, with an explicit product save still required. Invalid publication is rejected locally before forwarding, with instructions distinguishing category slug from product slug. Backend remains authoritative and unchanged, including active canonical category, template, image and QR restrictions. No cloud records were changed by this fix.

Validation: TypeScript passed. Focused products browser suite initially13 passed/1 failed because Playwright's toBeDisabled did not recognize a disabled option despite its disabled attribute; replaced that assertion with the native disabled property check. The affected test rerun passed, yielding all14 cases passed across the runs. Includes existing unsupported category replacement, inactive-category activation, canonical category creation/returned-ID selection, explicit product-save persistence, invalid publication no-forward and eligible publication forwarding against an isolated synthetic backend. These are offline tests, not live publication acceptance. No gates, schema,0044 or quarantine changed.

## Print Template development activation — actual execution, 25 October 2026

**Development live gate: ENABLED for the existing backend; metadata acceptance PASSED. Full printable-design/approval/product-publishing acceptance remains BLOCKED.** This supersedes earlier statements that all template operations are disabled, not the separate publication prohibition or remaining acceptance gaps. Scope is only project fhuxryfkfrvycsojkzvq and the local backend/frontend at127.0.0.1:8030/3100. No production deployment/configuration changed.

### Exact diagnosis and changes

Read-only, verified-TLS aggregate inspection found installed0043, template count0, enrolled assets0, valid authorities0, QA approvals0. Local management flag was false, template web origin did not match the frontend, asset root was absent, runtime Windows. Existing Operations+MFA staff is sufficient for listing and metadata creation; no role grant was needed. A stale or absent signed authentication event independently triggers REAUTH_REQUIRED after300seconds; refreshed token iat is not accepted as reauthentication.

Enabled only SAFERETURN_PRINT_TEMPLATE_MANAGEMENT_ENABLED=true and SAFERETURN_PRINT_TEMPLATE_WEB_ORIGIN=http://127.0.0.1:3100 in ignored backend/.env, after candidate live metadata acceptance passed. Restarted the existing backend; candidate loopback8032 was stopped. No frontend template gate needed changing. Other feature gates unchanged. No migrations, asset/authority enrollment, privileged credentials, QA approval, product bindings or publication occurred.

Added distinct bounded error codes to the existing template error envelope/relay/client: TEMPLATE_MANAGEMENT_DISABLED, TEMPLATE_ORIGIN_MISMATCH, TEMPLATE_ASSETS_UNAVAILABLE, PREVIEW_ISOLATION_UNAVAILABLE. REAUTH_REQUIRED remains separate. Preview rejects a missing asset root/unsupported platform before preview admission. Existing isolated renderer remains mandatory. Draft/create/details/binding error notices offer the official MFA page in a separate tab on recent-auth failure, retaining input and intent key without automatic retry. Added /admin/templates to the closed MFA return list. Added direct product-editor navigation explaining that an approved applicable binding, not a draft key, is required. Corrected template mobile grid/box sizing.

### API and workflow status

| API | Existing exact operation (under /api/v1) | Actual status |
| --- | --- | --- |
|300|GET /admin/print-templates|Live200; real actor/MFA, bounded response, frontend relay and visible fixture verified.|
|301|POST /admin/print-templates|Live201 for exactly one owner-approved synthetic metadata key; audit/idempotency writes only.|
|302|GET /admin/print-templates/{id}|Live200 for that fixture; no revisions, ETag1, private/no-store.|
|303/304|POST .../{id}/revisions; PATCH .../{id}/revisions/{revision}|Implemented/isolated tests passed; live design editing unaccepted because no enrolled assets exist.|
|305/306|POST .../{id}/revisions/{revision}/preview or /submit-qa|Synthetic orchestration tested offline; live preview/submission blocked by missing assets/root and Windows isolation. No real worker proof.|
|307|POST .../{id}/revisions/{revision}/publish|Still deliberately unavailable through frontend relay/UI. No evidence/publisher discovery or approvals fabricated.|
|308/309|POST/GET /admin/print-template-bindings|Existing contracts preserved; no live binding exercised. No published applicable revision exists.|
|310|POST .../{id}/revisions/{revision}/retire|Existing publisher/lifecycle restrictions intact; no live mutation attempted.|

Supported design contract remains fixed renderer/preset, dimensions/QR placement, plain English/Urdu text, enrolled font/logo assets and material codes. No arbitrary uploaded artwork, remote URLs, executable layouts, real QR identities or fabricated asset UUIDs are accepted. Review approval uses the existing independently signed evidence/custody/publisher backend process, not a new approve button. Product server checks still require published compatible revision/binding, purpose/size/material/template match, permitted category and verified image. Draft/rejected/unbound content does not satisfy those checks. Price-per-copy/size rules unchanged.

### Real acceptance evidence

Owner explicitly approved one persistent synthetic fixture: key dev-acceptance-20261025, name Development acceptance fixture, purpose lost, ID7ecda35e-4e0a-4f65-8f20-6f8b2d1e1ce8. Genuine owner login/MFA was used via in-memory token stdin. Candidate backend verified anonymous401, list200, create201, exact encrypted idempotent replay201, changed-intent409, detail200, revision list empty, ETag1 and no-store. Normal backend gate was then enabled. Authenticated frontend /admin/templates/api returned200 and the real page displayed the fixture. Helper closed its private browser normally; no token/password/MFA secret file or output. Final aggregate check: one template, zero enrolled assets/valid authorities/QA approvals, unchanged0043. Receipts: tmp/template-activation/prerequisites-before.json, prerequisites.json, live-acceptance.json, browser-acceptance.json.

Negative MFA/role/recent-auth/concurrency/approval tests are **offline**, using real application verification with scripted repositories/providers. No live staff role, MFA setting or session was forged/changed to manufacture negative cases. Live design edits/preview/QA/approval/binding and physical print checks were not executed.

### Validation and limits

- Template/security backend selected run:202 passed,4 preview orchestration failures,1 browser test deselected. New early platform rejection exposed that the scripted preview tests needed an explicit simulated supported-platform flag. Corrected those test fixtures; all13 preview tests then passed, including rejection before admission on unsupported OS. Across those runs207 distinct selected backend cases passed; actual Linux isolation is not claimed.
- Product publishing/size/copy-price/assets validation:57 passed. These are offline; no product publication executed.
- Template relay/contracts:60 checks passed,18 strictly allowed synthetic upstream requests, zero excluded requests.
- Quarantine:131 passed;70-operation deny registry unchanged.27 previously recorded protected hashes matched.
- Template browser suite initially14 passed/1 mobile overflow failed; fixed scoped sizing and mobile rerun passed. Four new precise-error browser cases passed. Total19 distinct browser cases passed across runs.
- TypeScript and scoped Ruff passed. Fresh offline-network frontend production webpack build passed. An initial unsupported --distDir CLI attempt failed; reran supported build successfully. An initial quarantine script filename was incorrect; corrected command passed. Existing catalog test_picker_browser could not run because its fixed3100 port is occupied by the owner's real dev frontend; it was not rerun against that live port. Separate source-bundled template/product browser evidence is recorded above.
- Next.js startup dependency security warning remains unresolved; no dependency upgrade or general deployment claim.

### Exact remaining owner actions and recovery

Metadata listing/create/details now need no further activation approval. To complete printable design and publishing: provide the actual licensed/reviewed font and permitted logo files and their review provenance for enrollment by the existing controlled asset process; authorize the identified asset-set/local-root configuration after review; provide a supported isolated Linux runtime for the existing preview worker; complete actual physical print/scan, copy-safety/license reviews and the existing separate authority/key/policy/evidence enrollment process. Operations role is not publisher enrollment. No valid authorities currently exist; no unrestricted role grant or signing credential creation is implied. Then run the bounded design/preview/review/binding acceptance against explicitly approved synthetic development fixtures. No approval or publication will be automated.

Rollback is executable: from backend run `.venv\Scripts\python.exe scripts\configure_template_development.py --rollback`, then restart only this local backend. It restores/removes only the two public local settings using tmp/template-activation/local-settings-before.json. It does not delete the approved fixture, audit history or customer data. Replaying the identical acceptance intent uses its original idempotency key while the receipt remains valid; do not create a new intent or delete records after an unknown outcome. Check the stored fixture/detail first. Five-minute expiry requires genuine reauthentication; no timeout override. Synthetic fixture has no delete endpoint and intentionally remains draft metadata.

**Overall: eligible metadata ENABLED; complete template approval/product publishing BLOCKED by the exact prerequisites above.**0044 remains unapplied, QR-pair services untouched,70-operation quarantine preserved, no new phase.

### Branding preparation — 25 October 2026

Inspected owner-provided branding folder locally only. logo.svg rejected by the strict print SVG subset because of defs/linearGradient/stop and paint URL references. Created separate branding/logo-print-candidate.svg with gradient replaced by solid #0EA5A4; original untouched. Candidate passed checked_logo; visual/owner approval remains pending. Raleway-Regular.ttf130128bytes has English sample coverage but lacks Urdu sample glyphs. Jameel Noori Nastaleeq.ttf13857268bytes covers both samples but exceeds the immutable5000000-byte asset limit. Its embedded free-of-charge statement/fsType4 is not verified license provenance or authority to modify/subset. No font was modified. Current asset schema/renderer accepts one font per asset set, shared by English/Urdu; two separate font files cannot simply be enrolled as a pair without a contract change. No renderer limit/schema/security restriction changed. No cloud enrollment occurred. Receipts: tmp/template-activation/branding-inspection.json and logo-candidate.json. Need permitted compatible bilingual font within limit, exact approved copy/dimensions/material and asset provenance before preparation can become an enrollment approval packet. Prior print/QA/Linux/authority blockers remain.

### Selected local sticker candidate — 25 October 2026

Owner selected40x60mm total sticker with30x30mm QR and delegated short wording. Prepared local Content-validated Lost candidate using unmodified Amiri Regular431116bytes (official Google Fonts download, SIL OFL1.1 retained alongside font), header SafeReturn, English Found? Scan me., Urdu ملا ہے؟ اسکین کریں. Font cmap covers selected characters. Layout x5/y18mm, font8pt, logo4mm; vinyl remains a proposed material, not a physically verified choice. Proposed asset UUID is explicitly NOT enrolled; do not use as a live asset ID. Packet tmp/template-activation/design-candidate.json preserves local file hashes and source/license references. Offline render_synthetic produced lost-sticker-40x60-synthetic.pdf using only preview.invalid synthetic content. Poppler PNG visual check confirms visible English/Urdu, QR/layout/logo within bounds; Poppler emitted ExtGState/font fallback warnings, so cross-viewer/PDF compatibility remains unaccepted. No real QR, cloud asset enrollment, live revision, approval, physical QA, binding or publication. Existing isolated Linux worker/authority prerequisites still apply.

### Render container dependency correction — 25 October 2026

Owner's actual Render build failed during pycairo metadata generation because python:3.12-slim has no C compiler. backend/Dockerfile now uses a builder stage with build-essential, pkg-config and libcairo2-dev; installs the project into /install; copies installed dependencies into a clean runtime stage with libcairo2 only. Compiler/headers stay out of the final image. Existing non-root user, application code, port command, migration behavior and gates are unchanged. A final-image non-root import check loads cairo, app.main and the Linux preview worker module at build time. It performs no rendering, network/database calls or migration. git diff --check passed. Full Linux container rebuild remains unverified locally because Docker is unavailable; the next Render build must establish native dependency success. This does not resolve missing asset enrollment, real isolated preview/QA or publication acceptance.

## Local frontend connected to Render development backend — 25 October 2026

Owner authorized using https://safereturn-backend-dev.onrender.com for testing. Updated only SAFERETURN_API_ORIGIN in ignored frontend/.env.local; preserved local web origin127.0.0.1:3100, existing Supabase project fhuxryfkfrvycsojkzvq/public key and all gates. Started local webpack development frontend with network access. Direct HTTPS Render liveness200/exact ok and anonymous staff-security401/no-store passed. Actual frontend /api/health/live returned200/exact ok through Render; /login200; anonymous catalog relay401. No browser-to-backend unrestricted proxy or CORS exception added.

Genuine owner sign-in/MFA in ephemeral Chromium reached /admin. At2026-10-25T09:37:18Z the existing stdin/session-only acceptance runner called Render /api/v1/me/staff-security and received200, mfa_verified=true, existing finance/operations roles and expected capabilities. No token persisted or exposed. Receipt tmp/render-acceptance-2026-10-25/genuine-staff-login.json; frontend connectivity receipt alongside. Helper closed normally. Remote module flags are explicitly unknown/null, not inferred from local backend/.env. No module-specific authenticated pagination/RLS/redaction, provider or template preview/publication acceptance is claimed.

Helper and runner now accept exactly the existing local origin or this named Render origin. Remote runner is restricted to session-only mode; synthetic template mutation helper remains local-candidate-only. Development public-config helper preserves an already configured approved Render origin rather than resetting it to localhost. JavaScript syntax and scoped Python Ruff passed. Existing suites/build evidence reused; no app source changed. Next.js regenerated its development route type references as expected. No remote writes, credentials, permissions, migrations, gate changes or deployments performed. Local frontend testing URL http://127.0.0.1:3100/login. Render cold starts may exceed existing strict request timeouts: allow the backend to wake via public liveness, then retry without weakening protections. Template asset/Linux-preview/QA prerequisites remain outstanding.

## Selected template form and asset registration — 25 October 2026

Owner requested implementation rather than manual JSON setup, then explicitly approved one development asset-set registration. Prepared ops/enroll-development-print-assets.sql, canonical LF SHA256 c115c52ab30b3cc73c2a626ae637668db8c052ec06f3ca54e724f1ee22d5be1c. Existing verified-TLS catalog connection pinned project fhuxryfkfrvycsojkzvq and installed0043, executed the exact transaction, then verified record0a7c508b-fc96-42d6-ba58-e367dbb8d08b. It registers only /app/print-assets/Amiri-Regular.ttf and /app/print-assets/logo.svg with exact selected hashes. No roles/schema/credentials/template revisions/QA approval/bindings/publication/customer/QR mutation. Initial hash check caught Windows newline conversion before DB access; canonical LF verification then passed. Receipt tmp/template-activation/asset-enrollment-receipt.json. Hash-pinned replay script backend/scripts/enroll_development_print_assets.py is a narrow operator invocation, not an automatic migration or startup action. Replay preserves exact existing row and rejects incompatible/withdrawn assets.

Packaged immutable selected font, its OFL license, solid-logo candidate, manifest and40x60 design in backend/print-assets. .gitattributes preserves their exact bytes across Windows/Linux checkout. Docker copies the package, sets only its non-secret asset-root default, verifies hashes as nobody, and runs app.template_asset_check using the real isolated Linux preview worker and synthetic preview.invalid content. That worker build check is pending the next Render deployment; no local Windows test is represented as Linux acceptance. Existing management gate, real MFA/recent auth, conditional QA/publisher and product security remain enforced.

Replaced the default large JSON editor with dimensions/QR position/logo/font/English/Urdu/material/asset-ID fields plus an explicit Use selected40x60mm design control, using the actually registered ID. Existing revisions and unsaved text are retained; replacing nonempty editor contents requires confirmation. Raw JSON is optional under Advanced design JSON; unsupported field types cannot crash the form. Saved draft/revision/version/idempotency and preview fingerprint logic still uses existing APIs303/304/305. No publish action or unsupported endpoint added. ICE does not inherit Lost wording. Product copy-price and size rules unchanged.

Validation:20 focused template browser cases passed, plus one new malformed-advanced-types case passed after defensive field handling. Includes selected-layout save through the real source relay against a synthetic repository, no manual JSON, enrolled ID payload, draft status, existing denied authority/reauth/concurrency paths and mobile layout. TS/scoped Ruff passed; frontend production webpack build passed, with final small field-type guard covered by fresh TS/browser check. Container/native Linux worker and live Render revision/preview remain pending deployment; no full template/publishing completion claim. Final owner step: manually deploy the pushed development commit on Render; then use selected-design button, version note, genuine MFA and Save draft/Generate synthetic PDF. No new phase or unrelated gate.

## Template authentication policy correction — 25 October 2026

Owner authorized15-minute drafting/synthetic preview, retaining5-minute sensitive actions. Backend guard now applies900seconds only create/revision/edit and direct preview, including replay/final authorization. QA submit proof explicitly uses300seconds; publish/bind/retire unchanged. Provider-signed AMR required; no token/session fabrication or gate bypass. Source-checked development SQL replaces ONLY sr_template_draft_service_v33 and sr_template_preview_admit. First attempt rejected before mutation because0034 wraps/renames0033 service; revised patch targets original internal helper and preserves installed public provenance wrapper. Exact canonical hash a23662d7c68ed8066fbba25843672d82311eaf4829e803281dc3591d12c6d8d6. Executed successfully in fhuxryfkfrvycsojkzvq with0043 check, verified owners/ACL/search_path unchanged. No0044 or original migration file modified. Rollback SQL ops/template-draft-auth-window-rollback.sql restores300seconds; narrow executor backend/scripts/update_template_auth_window.py records tmp/template-activation/auth-window-update.json. Render backend still needs deployment to use900-second Python guard.

Preview timeout/busy/worker failure now have explicit bounded codes preserved through relay/client; dev-only sanitized status/code/request-id logging contains no design or credential values. This diagnoses rather than certifies correction of the original generic503. Latest live retry proved403 REAUTH_REQUIRED; earlier8.4s failure might include5s worker deadline, not established. No resource isolation limits weakened. After deploy, one genuine-MFA same-intent preview is required to identify remaining runtime cause. Existing59e9f64 Docker worker check reportedly passed per owner; actual request failure remains unresolved until new receipt.

Validation:85 backend cases initially passed,1 near899s boundary failed due runtime delay; changed test point to850s,4 auth-window cases rerun passed.86 distinct selected template/preview cases passed across runs. New tests prove301/850s draft permitted,901s denied,400s QA submit denied. TS/Ruff and60 relay checks passed. Full frontend build reused; no production success or original preview resolution claimed.

## Throttled-host preview deadline correction — 25 October 2026

Owner reported the explicit PREVIEW_TIMEOUT from deployed worker and authorized bounded timeout adjustment. Raised only worker elapsed-time deadline5→60seconds; template preview/QA-submit relay20→75seconds; corresponding browser25→90seconds. Other operations keep existing timeouts. This accommodates CPU throttling without changing the worker's5CPU-second hard limit,256MiB address-space limit, file/core limits, credential-free subprocess environment, network denial, one-preview semaphore,2MiB output cap or rate/admission audit. No automatic retry, MFA/recent-auth change, approval/binding/publication or DB/schema change. Worker kill/drain/semaphore cleanup still runs on timeout; regression now asserts60seconds.13 backend preview tests,60 relay/contract checks, TypeScript/scoped Ruff/diff checks passed. Actual Render rendering success remains unverified until redeployment and a genuine same-intent preview. Existing isolated worker build check uses the same bounded implementation. No full-suite or unrelated build repeated for timeout constants.

## Owner-approved 20-minute template policy — 25 October 2026

Owner explicitly changed the previous15-minute draft/5-minute sensitive template policy to20minutes for all Print Template operations. Added template-only recent_template_auth requiring genuine verified account/signed AMR within1200seconds, used by route guards and template custody/publisher checks. Other modules' shared privacy_exports.recent remains300seconds. MFA, current roles, publisher/custody enrollment, independent QA evidence, provenance, concurrency, rate limits and quarantine unchanged;20minutes is recency only, never approval. Preview wall/CPU/memory limits unchanged. Error text now states20minutes for all template actions; cursor expiry remains900seconds independently.

Executed source-verified development-only SQL ops/template-auth-window-20min.sql, canonical SHA2566a926295f55089dcd318b3230fac8a0ed76c1648f6e74c460a7cdbeead47566d, using existing pinned verified-TLS connection. Only sr_template_draft_service_v33, sr_template_preview_admit and sr_template_lifecycle recency expressions changed to1200. Owners/ACL/search_path checked identical before/after; public provenance wrapper unchanged; installed0043/0044 unapplied. Receipt tmp/template-activation/auth-window-20min-update.json. Rollback SQL restores the immediately prior15-minute draft/5-minute lifecycle policy. No schema/table/data/role changes or automatic QA/publication. Backend template/publication101 passed; relay60 checks/TS/scoped Ruff passed. Sensitive QA tests permit400/1150-second authentication past the recency guard and reject1201seconds; draft tests likewise. Actual Render routes need new deployment; no remote live action fabricated. Existing local frontend uses updated text immediately.

## Admin Template QA implementation — 25 October 2026

Implemented `/admin/template-qa` with an Admin navigation entry, existing staff/MFA page guard and template relay. Lists pending revisions across template and revision cursors; opens revision identity/content details; generates the existing synthetic PDF with If-Match, expected_revision and reusable idempotency key; checks returned fingerprint against the submitted revision. Loading, empty, unauthorized, service and revision-conflict errors use existing protected contracts. Local review-note draft is explicitly unsaved. Approve QA / Reject QA remain disabled with the contract gap shown. No optimistic decisions, invented statuses, publication or assignment actions.

Contracts reused: GET /admin/print-templates, GET /admin/print-templates/{id}, POST /admin/print-templates/{id}/revisions/{id}/preview through /admin/templates/api. No backend extension or schema change: existing approval is an encrypted signed-evidence import (app.services.template_evidence), not a note-only review. Existing revision states draft/pending_qa/published/retired cannot safely be presented as Approved/Rejected. There is no protected reviewer-eligibility/decision-history/rejection contract. Supporting actual decisions needs a separately reviewed backend/schema extension, preserving mandatory evidence, provenance, audit and revision checks; this implementation does not bypass those requirements. Confirmation submission is consequently unavailable too.

Read-only, project-pinned verified-TLS prerequisite check succeeded against fhuxryfkfrvycsojkzvq: installed 0043_standalone_activation, 0044 unapplied; two templates, one enrolled asset set, zero valid authorities and zero QA approvals. Migration 0044 unchanged. No role, grant, RLS, persistent fixture, QA decision or deployment performed. QR-pair exclusion and 70-operation quarantine untouched. Local Windows configuration lacks asset root and supported Linux preview isolation; deployed preview success has not been verified.

Owner authorization requirement (not applied): zero active authorities means no staff account currently has enrolled template authority. Existing enrollment maps verified auth.users UUID via template_people(user_id,human_id,enrollment_reference), template_authorities(authority_id,human_id,scopes,valid_from,expires_at,enrollment_reference), and witnessed Ed25519 template_issuer_keys. Proposed minimum review enrollment requires explicitly approved physical_scan/copy_safety/licenses scope assignments, verified human identity, approved independent signers, public keys, witnesses, references and validity periods; contribution independence and production-policy scope-consolidation rules still apply. Security-admin custody import and operations publisher authority are distinct. No exact executable enrollment can be safely populated until those real values and policy choices are supplied; no self-grant or guessed identity/key is proposed.

Preserved existing 1200-second genuine authentication recency for all template operations (not a global session lifetime); corrected a stale relay comment. Backend auth tests cover acceptance within and denial beyond this window. No auth/MFA policy weakened.

Validation: backend test_print_templates.py, test_template_publication.py, test_template_evidence.py: 162 passed (83.34s), covering auth, evidence, state/version and publication restrictions. Frontend typecheck passed; production build passed and includes /admin/template-qa. Five Playwright component/relay browser cases passed: pending details/local note/disabled decisions, empty queue, 401, 403 and 503 failures. All browser requests intercepted with synthetic fixtures; no database mutations. Live prerequisite check is read-only evidence only. Actual authenticated page/preview and decision end-to-end verification remain unverified/blocked as described above.

Files: app/admin/template-qa/page.tsx; components/admin-template-qa.tsx; lib/admin-navigation.ts; lib/api/template-relay.ts (comment); playwright.template-qa.config.ts; tests/template-qa.spec.ts; this report. Existing unrelated dirty auth/acceptance scripts excluded from commit.

## Template QA decision contract follow-up — 25 October 2026

Replaced the permanently-disabled review stub with a protected review contract and functional decision UI. GET API-311 `/admin/print-templates/{template_id}/revisions/{revision_id}/qa` returns current Pending/Approved/Rejected status, backend reviewer eligibility, optimistic review version and the latest 20 decision records. POST API-312 `.../qa-decision` requires a 4–500 character plain-text reason, explicit confirmation, If-Match revision version, expected_review_version and an idempotency key. Approvals additionally require the existing signed evidence envelope; rejection must exclude that envelope. Typed response DTOs and closed relay parsers prevent unrelated registry fields reaching the browser. Browser approval/rejection is available only when the backend returns can_review; after every receipt the page reloads canonical status/history so an old replay receipt cannot overwrite a newer decision. Notes and signed input remain available after errors; conflicts disable decisions pending refresh. Product copy now describes the review task and gives a short availability message rather than presenting implementation history.

Both mutations reuse genuine staff/MFA, 1200-second recency, security_admin plus existing enrolled custody authority, exclusive registry admission, encrypted idempotency receipts and audit insertion. Approval calls the existing signature/provenance/material/scan/copy/license/policy verification and encrypted evidence import inside the decision transaction. The database extension additionally requires mapped independent contributor provenance for reviewers. Custody does not replace independent physical_scan/copy_safety/licenses signers. No frontend-claimed physical or cryptographic evidence is generated. Rejection records a terminal QA decision for that revision, revokes unconsumed evidence approvals and blocks subsequent evidence imports and publication; a corrected design needs a new revision. QA state is a separate review overlay; existing template revision lifecycle states and assignment/publication APIs are unchanged.

Prepared **source-only** migration `0045_template_qa_reviews` (Python + SQL), following unchanged0044. It adds an append-only review table, enables RLS on that new table with no runtime table privileges, and extends the existing SECURITY DEFINER lifecycle function while preserving its existing owner/ACL/search_path and other branches. Existing300-second template source is narrowly normalized to the owner-approved1200-second policy; already1200-second installs remain so. No existing RLS policy, database role, grant, reviewer enrollment, production data or migration0044 was modified/applied. The new table REVOKE/RLS statements are proposals in unapplied source, not executed permissions changes. Function-source anchors and recency are checked before replacement; unexpected source aborts the migration transaction.

Activation boundary: installed development state remains the previously read-only-verified0043;0044 remains unapplied. **Do not run upgrade head or apply0044/0045 from this change.** Review/rehearse the exact additive0045 SQL and obtain separate migration/RLS activation authorization for a path respecting0044's existing gates. No schema rehearsal or positive database mutation was authorized here, so PostgreSQL compilation, actual RLS/ACL behavior, locking/concurrency, terminal rejection enforcement and durable decision/audit atomicity remain unverified against a database. HTTP SQL responses are scripted test doubles, not proof of those database properties. The API returns503 when the review table is absent; a deployed frontend alone cannot activate decisions. Existing owner enrollment requirements are described in the previous entry and remain unchanged; no authority was self-granted. Approved-state history is historical review evidence, not a guarantee that evidence is currently unexpired/unrevoked; publication independently revalidates it.

Validation:18 new HTTP tests passed with real signed-evidence verification/AEAD and scripted SQL: approval/replay/audit, rejection, denied roles, missing migration, conflict rollback, note-bound idempotency, invalid confirmation/note/version/evidence, forged signature, wrong revision evidence,1150/1201-second authentication and required matching Origin. Combined prior template/publication/evidence run had175 passed/1 failed solely because the explicit OpenAPI inventory expected11 rather than13 template operations; updated that inventory for the two new endpoints and its focused rerun passed (15 cases including the then14 new review cases). Thus all162 pre-existing selected cases and18 new review cases passed across runs; no failed security test was weakened. Ten Playwright component/relay tests passed for protected/mock decision flows, history identity/note, cancellation, conflicts, unavailable/401/403 states and mobile fit.60 existing relay/quarantine checks passed with zero excluded requests. TypeScript, production build and scoped Ruff passed. Final rerun results recorded below when complete.

Changed files: backend/app/api/v1/print_templates.py; backend/app/services/template_evidence.py (allow review revision as audit target); backend/alembic/versions/0045_template_qa_reviews.py + .sql; backend/tests/test_template_qa_api.py; backend/tests/test_print_templates.py (explicit endpoint inventory); frontend/components/admin-template-qa.tsx; frontend/lib/admin-templates-contract.ts; frontend/lib/api/template-relay.ts; frontend/tests/template-qa.spec.ts; frontend/tests/templates-fixture.cjs; this report. Original three dirty auth/acceptance scripts remain excluded. QR-pair exclusion,70-operation quarantine, publication/product-assignment separation and0044 source hashes preserved.

Final validation rerun: production build (including TypeScript) passed; all10 browser cases passed in27.0s after canonical status refresh was added;18 HTTP QA cases passed in27.19s. Alembic source graph reports one head0045_template_qa_reviews (no database connection/upgrade); scoped Ruff and diff checks passed. Migration0044 SHA256 remains17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d (SQL) and67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30 (Python). No migration execution, grant/enrollment, live QA decision or deployment occurred.

## Owner-authorized QA migration activation — 25 October 2026

This entry supersedes the previous0045 migration-activation blocker. After the owner requested execution, rechecked fhuxryfkfrvycsojkzvq: installed0043, zero active authorities and zero approvals. Rehearsed the exact0045 SQL in a transaction that was always rolled back: PostgreSQL compilation passed, lifecycle owner/ACL/config/security-definer metadata remained identical, new-table RLS was enabled, anon/authenticated/API/worker roles had no direct table privileges, and rollback removed the new table while retaining0043. This is actual database DDL/permission evidence, not positive reviewer/QA-state fixture testing.

Corrected the unnecessary0045 dependency on protected0044: QA DDL only depends on0043 objects.0045 now branches from0043 with branch label `template_qa`;0044 is unchanged on its independent Support branch. Applied **only exact revision0045_template_qa_reviews** using an injected verified-TLS connection and guarded transaction. No `upgrade head`, stamping,0044 execution, Support role creation, staff enrollment/grant, persistent synthetic fixture, actual QA decision or application deployment occurred. The script asserts the starting0043 state, unchanged0044 artifact hashes, exact0045 SQL digest, absent review table, and unchanged Support schema/role state before committing. Owner-authorized0045 creates only the new empty review table/RLS and the previously-reviewed lifecycle extension; function owner/ACL/search_path remain unchanged.

Committed state freshly verified: sole installed revision `0045_template_qa_reviews`, review table exists with RLS, review count0, direct runtime table access denied, lifecycle function metadata preserved, Support migration unapplied. SQL SHA256 `3e93890cfd445b4240010c048440294ef6cfe0813357d8a88c494d1ea23272f5`. Execution receipt: `tmp/template-activation/qa-migration-applied.json`; rollback rehearsal receipt: `tmp/template-activation/qa-migration-rehearsal.json`. No template/order/QR allocation data was changed. The existing three dirty auth/acceptance scripts remain excluded.

Migration graph now intentionally has independent Support0044 and QA0045 heads. Future migrations/runners must select the authorized branch explicitly; do not use unqualified `upgrade head` or merge/apply Support0044 under QA authorization. New regression test proves the0043→0045 path contains only0045 and verifies the exact preserved0044 hashes. This path test passed; scoped Ruff and diff checks passed. SQL compilation/RLS/permission checks passed live in rehearsal and committed verification. Positive database tests of enrolled reviewers, signed evidence decisions, terminal rejection and concurrent publication remain unperformed because no reviewer enrollment/fixtures/actual decisions were authorized. Existing HTTP/browser results from the prior entry remain applicable to unchanged endpoint/UI code.

Files added: backend/scripts/rehearse_template_qa_migration.py; backend/scripts/apply_template_qa_migration.py; backend/tests/test_template_qa_migration_path.py. Modified0045 Python wrapper for the independent QA branch and updated this report. Owner authorization/enrollment and evidence requirements from the implementation entry remain; installing schema alone grants no reviewer authority. No application deployment was performed.

## Owner-requested manual print QA — 25 October 2026

The owner clarified that staff should receive a PDF, print/check it and click Approve QA, without signing tools, evidence uploads or another review enrollment workflow. This supersedes the signed-evidence requirement **for this QA page's decision only**. Implemented Get PDF for printing (generates and downloads the existing synthetic PDF), an optional note tucked into details, and direct Approve QA / Reject QA buttons after PDF generation. No extra confirmation dialog, checkbox, signed-envelope field or required note remains. Clicking approval records the staff member's manual print-review attestation. The system does not claim to have observed printing, scanning or measurements. It records actual authenticated reviewer UUID, exact revision/row version, returned PDF fingerprint and backend decision timestamp/history. No human mapping or cryptographic authority identity is fabricated.

Existing Operations staff with genuine MFA, template capability and authentication within1200seconds can perform manual QA; Security Admin/Superadmin alone are not implicitly promoted to Operations. No staff-role assignments or database grants changed. Removed custody/signer enrollment as prerequisites for this manual-only decision path; signed evidence import, publication requirements and product assignment remain separate and unchanged. Manual approval creates no template_qa_approvals evidence record and cannot serve as signed publication evidence. Existing independent signed evidence/provenance/publisher checks continue to apply to publication. Rejection still revokes unconsumed signed approvals and blocks later publication/import for that revision. The request checks If-Match, current review version and preview fingerprint under exclusive registry admission; current revision changes or replay collisions fail closed. Encrypted idempotency receipts, audit insertion, required matching Origin and server validation remain.

Added migration0046_manual_template_qa on the independent QA branch, following0045 and excluding0044. It adds evidence_kind and preview_fingerprint to review history, allows an absent human-authority mapping for manual staff reviews, and replaces only the old review-evidence constraint to distinguish manual attestations from signed evidence. It injects new manual_review_status/manual_review_decide branches into the existing lifecycle function without replacing the publication/evidence branches. Existing review rows default to signed_evidence. Existing function owner/ACL/config/security-definer metadata and review-table RLS/privileges remain unchanged.0044's pinned source and unapplied state are preserved.

Rehearsed0046 against only fhuxryfkfrvycsojkzvq in a rollback-only transaction, then applied the exact rehearsed SQL after checks. Both completed successfully. Fresh commit verification shows installed0046_manual_template_qa, unchanged lifecycle metadata, enabled review-table RLS, no direct table access for anon/authenticated/API/worker, unchanged Support role/schema state and zero review records. No persistent synthetic fixtures, actual QA decisions, staff grants or application deployment occurred. SQL SHA256cd8b76d92ce829c466349975e31c12218deff37dbbf73de18ae7d572dfc79a5c. Receipts: tmp/template-activation/manual-qa-rehearsal.json and manual-qa-applied.json. The runner defaults to rollback rehearsal; only --apply commits. Alembic remains intentionally branched; select the QA revision explicitly and do not apply Support0044 under this workflow's authorization.

Validation:19 focused manual-QA HTTP tests passed (16.72s): no-upload approval/default note, encrypted replay/audit, role denials, unavailable schema, conflicts, note-bound idempotency, malformed requests, fingerprint format,1150/1201-second recency and required matching Origin.163 existing template/publication/evidence plus migration-path cases passed (94.89s), preserving cryptographic and publication security tests.10 browser tests passed (28.4s), including get-PDF→approve with no note/upload/dialog, optional note/history, stale decisions, unavailable/unauthorized and mobile layout.60 existing relay/quarantine checks passed with zero excluded requests. TypeScript/production build/scoped Ruff/diff checks passed. Browser/HTTP protected decisions were mocked; no genuine staff decision or deployed page/physical-print end-to-end success is claimed. Database evidence covers SQL compilation and migration/metadata enforcement; positive review/publication fixture testing remains unperformed.

Files changed: backend/app/api/v1/print_templates.py; backend/app/db/print_templates.py; backend/alembic/versions/0046_manual_template_qa.py + .sql; backend/scripts/activate_manual_template_qa.py; backend/tests/test_template_qa_api.py; backend/tests/test_template_qa_migration_path.py; frontend/components/admin-template-qa.tsx; frontend/lib/admin-templates-contract.ts; frontend/lib/api/template-relay.ts; frontend/tests/template-qa.spec.ts; frontend/tests/templates-fixture.cjs; this report. The three pre-existing dirty auth/acceptance scripts are excluded. No QR-pair/quarantine/order/QR-allocation changes were made.
