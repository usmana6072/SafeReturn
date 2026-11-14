# SafeReturn admin backend integration plan — corrected, Products first

## Current Phase 13 Dashboard, Audit, My Security and Monitoring — 24 October 2026

Option A continues implementation; genuine live acceptance remains consolidated in Phase14, which has not started. This addendum supersedes older demo/live-console labels for these screens. Historical counts, corrected70 exclusions/quarantines and Products14-operation budget remain unchanged. Phase9–12 gates, quarantines/blockers, Phase4 Orders, provisioning and unapplied0044 are preserved.

| Candidate | Verified source chain and independent disposition |
|---|---|
| API-344 GET /api/v1/admin/dashboard/summary | QUARANTINED entire endpoint. main.install_dashboard -> summary ->0028 sr_dashboard_summary(fulfillment) -> sr_fulfillment_eligible legacy order_pair_units/pair_print_qa branch.0034 wrapper and0042 single_qr CASE retain legacy ELSE path. No group selector; no safe-role/payload exception. Overview shows unavailable KPIs; relay always503 before module auth/upstream, regardless of gate. |
| API-345 GET /api/v1/admin/dashboard/trends | SOURCE ELIGIBLE, live-disabled. Current five-role/email/session/MFA + dashboard_enabled ->0028 sr_dashboard_trend -> retained shipments/notification_outbox counts only; final current role/MFA/session. Fixed30 completed UTC days/daily buckets, timezone UTC or Asia/Karachi changes labels only. orders_placed is unavailable without SQL; shipments_dispatched Operations, notifications_created Operations/Security Admin. Counts0..999 exact,1000+ capped; actual as_of, chart/table, manual refresh, unavailable/empty/error states prepared. No Summary/Orders substitution. |
| API-100 GET /api/v1/admin/audit-events | SOURCE ELIGIBLE, live-disabled. Explicit security_admin/MFA + signed AMR authentication within300s (token iat insufficient) -> seven-field audit_events metadata SELECT -> documented audit.search append with no filters/private details.0003 RLS/append-only/safe_json guards; no pair or target lookup. Supported actor_id,target_id,target_type,action,start,end,limit,cursor only. Frozen seven-day default/max31-day timezone-aware window, keyset paging/refresh and bounded source-page details. Unknown labels redacted; references inert; no names/snapshots/raw JSON/export/full-text or persistent results. |
| GET /api/v1/me/staff-security | SUPPORTING / SOURCE ELIGIBLE. Current verified principal's nonrevoked staff_roles only; fixed capabilities conditional on actual MFA. Three fields roles,mfa_verified,capabilities. Current-user refresh panel prepared, separate panel gate false; existing AAL1 authentication bootstrap unchanged. Real AdminPage still requires MFA. No account selector/global role editor/grant/MFA removal/provisioning/0044 controls; no assurance/time metadata invented. |
| API-001 GET /api/v1/health/live | SOURCE ELIGIBLE public process response only, exact200 {status:ok}; no Auth/DB/provider/worker call. Manual process-observation adapter prepared, conservatively live-disabled. Existing staff/MFA/page capability checks retained; no JWT forwarded to001. Client completion time is labelled; errors clear prior success and do not diagnose an outage. Database/pool/CPU/memory/providers/email/storage/workers/backups/incidents Not Available. Never call002 readiness. |

Five independent server-only gates in lib/phase13-gate.ts are literal false. Summary also has unconditional quarantine. Browser/query/environment flags cannot admit them; existing global verifiedSession/staffState bootstrap remains active. Module relays reject writes405 before module auth/body/fetch and use fixed paths, closed queries, same-origin/CSRF checks, current roles/MFA/capabilities before/after as appropriate, no-store, redirect rejection, deadlines, streamed strict200 JSON, attachment rejection, redacted errors and minimized DTOs. Dashboard retains approved64,000-byte cap; other reads262,144bytes. No credential/result browser storage or speculative prefetch.

Existing OverviewDashboard/AdminAuditLogs/AdminStaffPermissions/AdminSystemMonitoring and AdminPage/AdminShell/shared cards/tables/badges remain the app structure. Active mock analytics/audit/staff/jobs/alerts and ?view=live legacy consoles are removed. Quarantined inventory/batches/ready-to-ship/reconciliation overview quick links are suppressed; no unrelated screen or global Auth/navigation system redesigned. New staff-permissions/api is a current-user adapter, not a backend role-management endpoint.

**PHASE13 — IMPLEMENTED; LIVE ACCEPTANCE PENDING** applies to345/100/current-user security/001 prepared functionality only;344 is blocked individually. Isolated115 Node,51 browser and29 backend checks passed; TypeScript and scoped Ruff passed. All four requested viewports and keyboard controls checked; no actual managed Auth/MFA/RLS acceptance. Fixture budgets exclude Summary, business mutations, QR APIs, readiness, workers and providers.59 protected hashes match. Source review includes approved API/Technical/DB/Security specs, actual registrations,0028 helper role/search_path/ACLs and0003 Audit policies/triggers; no backend or migration changed.

Full32-path modified/new/removed manifest, actual test corrections/results, source chains and remaining acceptance requirements: [Phase13 progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-13--dashboard-audit-my-security-and-monitoring--24-october-2026). Recommended Phase14 evidence covers installed helper/migration/ACL/RLS equivalence, real current session/MFA/revocation and Audit recent-auth, own-user projection, safe trend precision/timezone/query budgets, Next/browser/origin and process-only liveness behavior. Recommendations do not authorize execution, infrastructure, identities, provider operations, migration0044 or lifting quarantines.



## Current Phase 12 Finance and Storage addendum — 24 October 2026

This supersedes earlier candidate or demo integration labels for these six APIs. The corrected historical inventory counts,70 excluded/quarantined operations and Products14-operation budget remain unchanged. SOURCE ELIGIBLE does not mean LIVE ADMITTED. Phase9/10/11 blockers and disabled gates remain unchanged;0044 remains unapplied.

| API | Verified path under /api/v1 | Source eligibility / current integration |
|---|---|---|
|238 | GET /admin/finance/sheet-sync | Eligible: Finance/Security Admin/Superadmin + email/session/MFA; sync/order metadata and finance.sync job state only. Typed minimized list/detail, page-local filters, limit/cursor/refresh prepared. Independent read gate literal false. |
|239 | POST /admin/finance/sheet-sync/{sync_id}/retry | Eligible finance.sync-only worker branch; no allocation/retention worker dispatch. Empty upstream POST;202 retry receipt. Controlled confirmation, double-submit guard, refusal refresh and unknown-outcome lock prepared. No backend reason/version/expected attempt/client Idempotency-Key exists. Independent retry gate literal false; real concurrency/provider acceptance pending. |
|242 | GET /admin/storage/artifacts | Independently eligible metadata read: print/payment artifacts, hold boolean and cleanup job metadata. Actual bounded items response has no cursor/total/created/updated time. Supported type/order/job/limit filters; details only search authorized result. Independent read gate literal false. |
|243 | POST /admin/storage/artifacts/{artifact_id}/retention-holds | QUARANTINED entire generic endpoint: finder resource branch reaches0021 finder hold trigger and pair locks. No print-only payload workaround. Creation gate false; relay unconditionally405. |
|244 | DELETE /admin/storage/artifacts/{artifact_id}/retention-holds | QUARANTINED: releasing active holds can admit pair-dependent destructive cleanup; safe independent contract/authority evidence missing. No source reason/version/key request requirement invented. Release gate false; relay unconditionally405. |
|245 | POST /admin/storage/artifacts/{artifact_id}/cleanup-retry | QUARANTINED:0019 retry -> retention worker prepare reads order_pair_units/disputes and provider delete/tombstone. Cleanup gate false; relay unconditionally405. |

Existing Finance/Storage pages reuse AdminPage/AdminShell and current cards/tables/badges/dialog/CSS. They no longer mount FinanceStorageAdmin, query-selected legacy consoles or mock/localStorage records. Same-origin closed-path relays enforce verifiedSession/current staff roles/capabilities/MFA before and after upstream work, origin/CSRF, no-store, redirect rejection, deadline, bounded JSON and strict request/response projections. No generic URL/body/header forwarding or arbitrary deletion. All six gates are server-only literal false; no query, environment or browser state enables them.

Finance projection drops sheet_row_key, amounts/currency/payment/fulfillment data. Storage projection drops bucket/object_key/checksum/private hold reason; errors map to finite safe codes. No provider credentials, signed URLs, private files, Orders enrichment or speculative prefetch. Queue receipt is not sheet completion; hold absence/elapsed retention/job completion is not deletion eligibility or provider deletion proof.

Source review: main.py -> api/v1/retention.py; finance.sync row locks/active-job coalescing/audit -> finance_retention.py finance-only claim/process/masked approved Sheets upsert;0003/0019 RLS/lease guards; API242 sr_retention_held helper;0021 finder hold trigger and0019 cleanup prepare establish quarantine. No backend/protected implementation, schema, Auth or migration changed. Source inspection does not establish installed RLS/ACL/transaction or provider acceptance.

**PHASE12 — IMPLEMENTED; LIVE ACCEPTANCE PENDING** covers238/239/242 implementation only.243/244/245 are blocked individually and not claimed complete. Isolated checks:65 Node,31 browser,28 backend tests passed; TypeScript and scoped Ruff passed. All four requested viewport sizes passed list/detail overflow checks; mobile dialog keyboard/double-submit check passed.39 protected hashes match. Tests use exact allowed synthetic requests, signed synthetic JWT/JWKS and scripted SQL; no actual DB/provider/worker or retention mutation endpoint was invoked. Superseded mock-only screen21/22 suites were replaced with phase12-finance-storage.spec.ts. Full contracts, file manifest, results and Phase14 prerequisites: [integration progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-12--finance-sheet-sync-and-storageretention--24-october-2026). Phase13 is not started.



## Current scope override: Phase 11 Privacy — 24 October 2026

Owner selected OptionA: implement remaining Admin modules and consolidate live acceptance in Phase14. Phase11 alone is authorized now. Preserve Phase9 Support/Phase10 Notifications implementation and disabled gates, Phase4 Orders, all QR quarantines and unapplied0044; no new database infrastructure or earlier acceptance work.

API-330 GET `/api/v1/admin/privacy/exports` was independently source-traced through current Auth/MFA/Security Admin and case-bound authority/epoch helpers. Only stored minimized metadata is reached. Implemented the existing list/details screens using a closed eight-field relay, backend limit/cursor paging, refresh, honest page-local filters and a source-page detail view. Keep the literal server live-read gate false pending Phase14. Do not invent updated timestamps, totals, backend status/ID filters or a general privacy/deletion queue.

API-327 remains quarantined: approve enables the worker whose sr_export_page reads tag_pairs and order_item_qr_uses;0043 adds standalone categories without removing pair exports. No reject/escalate payload exception, decision dialog, customer export/download, Support/Finance case lookup, notes or authority provisioner. Non-GET admin relay calls fail405 before Auth/upstream. This is a read-only phase implementation, not an export activation.

Complete files/tests/minimization/security/source trace and remaining installed-function/RLS/authority/session acceptance: [Phase11 progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-11--privacy-requests--export-review-2026-10-24). No backend handler/schema/migration, live Cloud setting, earlier module or customer privacy flow changed. **PHASE11 — IMPLEMENTED; LIVE ACCEPTANCE PENDING** applies only to tested metadata functionality; decisions remain blocked by policy. Recommend Storage metadata for a separately requested Phase12 review; do not start Phase12. Historical budgets below remain valid for their recorded phases.

## Current scope override: Phase 10 Notifications — 24 October 2026

The owner paused Phase9: **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED**. Preserve its Support endpoint/frontend/gate/non-admission/0044/provisioning state; do not restart its infrastructure or acceptance. This is the requested Notifications implementation record, not a new planning subdivision or permission to deploy.

The only new module-specific candidate budget is exact API-101 GET `/api/v1/admin/notification-outbox` and API-102 POST `/api/v1/admin/notification-outbox/{id}/retry`, plus existing own `/api/v1/me/staff-security` bootstrap. Both candidates were freshly source-traced through authorization, SQL definers, RLS/trigger dependencies, retry gate and worker recipient/delivery chain; no prohibited QR/pair operation is reachable in the reviewed source. Their eligibility is retained, but **live admission remains denied** by literal server-side read/retry gates. Retry may queue an actual email and needs independent mutation/side-effect acceptance before activation.

Implemented within existing Notifications list/details/Admin design: minimized metadata, status/exact-ID filters, cursor pagination, refresh/history, page-local derived channel filter, redacted loading/error/role states, controlled confirmation/reason/count/key retry protocol. Active pages no longer mount the old console or mock records. Actual contracts and fixed server relay deny all other methods/paths/fields; old `view=live`/UUID/browser flags cannot open gates. No backend handler/schema/migration/TLS/auth setting or Phase4 Orders/Support/Finance/QR module changed.

No new testing environment, live outbox/identity enumeration or real provider send was attempted. Isolated actual-router/React/relay tests are recorded in [Phase10 progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-10--notifications-management-2026-10-24). Required deployed helper/role/RLS/concurrency/fixture/provider acceptance remains outstanding; mark IMPLEMENTED — LIVE ACCEPTANCE BLOCKED, not live-complete. Recommend Audit Logs metadata for a separately requested next module; do not begin Phase11. Historical Products budgets and all70 exclusions below remain unchanged.

Correction date: 23 October 2026 (Asia/Karachi). **Audit/report correction only. Stop before implementation.** Only the three existing reports were updated. No application/backend/environment/database change, service, worker, API request, excluded test, page render or background prefetch was performed.

## Corrected decision

Recommend **Products Management as the first module**. Its individual catalog routes were traced through role dependencies, service helpers, RLS/policies, SQL functions, relevant triggers, encrypted command receipts, provider reads and audit writes. No reachable prohibited pair generation, allocation, reservation, assignment, activation, inspection, credential export or ownership/lifecycle mutation was found in the strict catalog chain. This is source-level evidence, not a claim that deployment/provider behavior was tested.

The previous independent-QR exception, optional typed inventory/generation proposal, independent support panel, allocation-status recommendation, generic support/financial case recommendation, and Overview-first rollout are withdrawn. Independent/typed naming is not authorization. No unsafe branch becomes permitted merely by hiding a button or forcing a frontend payload/role. No backend business rule will be bypassed or modified.

Corrected source inventory totals (mutually exclusive):

| Class | Count | Meaning |
|---|---:|---|
| ELIGIBLE | 42 | Generally admin-suitable after source-chain review; only 11 are first-phase catalog operations. |
| SUPPORTING | 10 | Supporting functionality; only 3 first-phase lookups/bootstrap. |
| QR-PAIR EXCLUDED | 47 | Prior explicit/mixed pair restrictions retained. |
| QUARANTINED | 23 | Eight exact owner exclusions, allocation retry, and fourteen additional indirect/mixed operations. |
| BLOCKED | 1 | POST /api/v1/me/orders is deliberate 409 QUOTE_REQUIRED compatibility stub. |
| NOT ADMIN | 39 | Customer/public/internal; no direct admin authorization. |
| Total registered operations | 162 | Prior registered/OpenAPI comparison; not reimported or called in correction. |

**Combined excluded/quarantined: 70.** Generally eligible/supporting: 52. **First phase: 14 exact operations; everything else denied**, including safe future modules. Framework docs routes are outside the business-operation count. Missing APIs are gaps and are not added to these totals.

## Strict first-phase allowlist



No prefix/router wildcard. Match method + exact path shape + validated IDs + allowed query/body keys. Authentication-provider sign-in/refresh/MFA traffic uses existing SDK/config; it does not authorize another SafeReturn API. The only SafeReturn backend calls for Phase 1 are:

| Method | Exact backend URL | Source | Verified service chain / constraints |
|---|---|---|---|
| GET | `/api/v1/me/staff-security` | `backend/app/api/v1/account.py:52` | Authenticated bootstrap -> current user staff_roles and capabilities/MFA state only; no QR call. Privileged product requests still enforce verified email and active MFA. |
| GET | `/api/v1/admin/products` | `backend/app/api/v1/catalog.py:491` | guard -> SELECT products + product_variants + product_images; product price projected to variants. UUID cursor, limit 1-100; no stock query. |
| GET | `/api/v1/admin/products/{product_id}` | `backend/app/api/v1/catalog.py:534` | guard -> SELECT product and its variants/images; 404 if missing. Does not call order detail/allocation. |
| GET | `/api/v1/admin/catalog/categories` | `backend/app/api/v1/catalog.py:548` | guard -> SELECT product_categories ordered sort_order/id, capped 100; no pagination token. |
| POST | `/api/v1/admin/catalog/categories` | `backend/app/api/v1/catalog.py:563` | mutation -> insert product_categories -> encrypted idempotency receipt + audit. No pair helper or worker. |
| PATCH | `/api/v1/admin/catalog/categories/{category_id}` | `backend/app/api/v1/catalog.py:574` | mutation -> lock category using category.catalog_version -> update category -> receipt/audit. No pair helper. |
| POST | `/api/v1/admin/products` | `backend/app/api/v1/catalog.py:597` | mutation -> registry gate (advisory lock only) -> INSERT draft product, commerce_model=single_qr/allows_new_pair=false -> receipt/audit. Product metadata is not identity allocation. |
| PATCH | `/api/v1/admin/products/{product_id}` | `backend/app/api/v1/catalog.py:609` | mutation -> registry gate -> lock product -> update metadata -> publishable -> template catalog eligibility/approval checks only -> receipt/audit. |
| POST | `/api/v1/admin/products/{product_id}/variants` | `backend/app/api/v1/catalog.py:641` | mutation -> registry gate -> lock parent at product version -> insert variant with parent price -> bump parent version -> publishable -> receipt/audit. |
| PATCH | `/api/v1/admin/product-variants/{variant_id}` | `backend/app/api/v1/catalog.py:671` | mutation -> registry gate -> find/lock parent -> lock variant at variant version -> update variant with parent price -> bump parent -> publishable -> receipt/audit. |
| POST | `/api/v1/admin/products/{product_id}/images` | `backend/app/api/v1/catalog.py:711` | mutation -> authorize_upload=true: lock parent, sign public catalog raster upload; normal branch: verified_asset Cloudinary read -> lock parent -> image insert/primary adjustment -> bump parent -> receipt/audit. Both branches reviewed. |
| PATCH | `/api/v1/admin/products/{product_id}/images/{image_id}` | `backend/app/api/v1/catalog.py:761` | mutation -> lock parent at product version -> lock image within product -> adjust primary/alt/order -> bump parent -> publishable -> receipt/audit. |
| DELETE | `/api/v1/admin/products/{product_id}/images/{image_id}` | `backend/app/api/v1/catalog.py:778` | mutation -> lock parent at product version -> DELETE product image link within product -> bump parent -> publishable -> receipt/audit. Does not delete provider media or QR credentials. |
| GET | `/api/v1/admin/catalog/approved-templates` | `backend/app/api/v1/catalog_templates.py:65` | guard -> read configured catalog_approved_templates -> validate key@version -> TemplateChoices; local pairs variable is a set of key/version tuples, not QR-pair data. |


This is the complete SafeReturn API request budget for Products. Validate exact method/path combination, UUID segments and query/body schemas; never authorize a router prefix. `/me/staff-security` is existing auth bootstrap, not a product privilege grant. Public catalog comparison, /health/live, general template management/binding, dashboard, orders, payments, stock, allocation, support, privacy, finance and storage are not implicitly included.

Only existing configured Supabase auth SDK sign-in/refresh/MFA traffic and an exact scoped signed public Cloudinary raster upload are separate infrastructure requests; they do not authorize other SafeReturn APIs, a generic signed URL or a QR export. No request is made during this audit.

## Product service-chain findings and individual constraints

The inventory supplies a separate proof row for every catalog method/path, not a router-wide safety assertion. GET product list/detail reads catalog products/variants/images; category lookup reads categories; approved-template choices reads configuration only. There is no stock/count/allocation call after a read.

Nine mutations are separately admitted: category create/edit; draft product create/edit; variant create/edit; image authorize/attach; image metadata edit; image unlink. Shared mutation -> guard -> scoped idempotency lock/replay -> specific work -> encrypted receipt/audit. Product/variant operations acquire a registry advisory gate; no job is created. Product creation sets commerce_model=single_qr/allows_new_pair=false as metadata and does not create a QR identity.

Publication checks read category/variants/verified images and template eligibility. `catalog_eligibility -> sr_template_catalog_(type_)eligible -> sr_template_revision_clear` validates published revision, approved assets, evidence and signing authority. Signing-key metadata here is print-template authority, not QR-pair credentials. Unrelated order manifest helpers in template_registry.py are not called on these catalog paths.

Checked source boundaries: api/v1/catalog.py and catalog_templates.py; db/template_registry.py; api/auth.py and db/runtime.py; migrations 0003_workflows_security.py (RLS/roles), 0015_public_catalog.py (catalog versions/media/delete policy), 0034_print_template_publication.sql (registry/catalog guard/revision-clear), 0036_product_copy_pricing.sql (required price), 0039_single_qr_catalog.sql (immutable model/deferred completeness). Catalog constraint triggers read catalog/template records, not live pair stock; product-model guard checks historical order_items only to prevent type rewrites.

Use the correct If-Match version: category version for category PATCH; product version for product PATCH, variant POST and image commands; variant version for variant PATCH. Image authorize_upload=true and attachment share a route but are different idempotent intents. Normal attachment verifies a public Cloudinary asset before catalog locking; audit/receipt replay occurs before redoing provider work. Image unlink deletes the catalog link, not provider media or a QR credential.

Preserve full ProductRequest/VariantRequest fields even on PATCH; do not serialize a partial UI object that resets defaults/unrelated metadata. Server variant writes use parent price_per_copy. PKR price-per-copy/max_order_copies controls already exist in visible forms; map them correctly, do not create a second pricing model. Never recalculate historical order snapshots or accept a client checkout price as truth. Customer checkout/allocation behavior remains outside this task.

## Indirect dependencies that changed decisions

| Endpoint/family | Reachable prohibited dependency | Corrected action |
|---|---|---|
| Eight owner-named endpoints | QR stock/generation, allocation status, independent support context explicitly quarantined regardless of standalone code | Deny all eight exact operations. |
| Allocation retry | Allocation-related mutation; prior blocked label implied future admission | Quarantine, no retry shortcut or setup call. |
| Dashboard summary | operations group -> sr_dashboard_summary(fulfillment) -> sr_fulfillment_eligible -> pair allocation/QA | Quarantine summary; do not assume catalog-only group for all staff. GET trends remains a later safe candidate. |
| Orders list | auto-selected operations projection -> sr_fulfillment_eligible; mixed finance/operations accounts take unsafe branch | Quarantine generic list; no role-preview isolation or finance-only workaround. |
| Shipments list | SHIP_COUNTS reads shipment_pairs plus fulfillment eligibility | Quarantine even though read-only. Typed item metadata is separate/future only. |
| Support create/detail/change | sr_support_create validates tag_pairs; INSERT retention-admission trigger queries order_pair_units; sr_support_change (0035 wrapper -> v34) locks tag_pairs and calls sr_support_context | Quarantine all three generic operations, including claim/note actions. No independently safe backend case metadata endpoint identified. |
| Financial case review/decision | load_context -> latest sr_financial_case_context in 0030 locks order_pair_units/tag_pairs | Quarantine review and decision; no generic financial tab proposed. |
| Finance reconciliation/counts | sr_finance_reconciliation_rows computes VERIFIED_ALLOCATION_MISMATCH from order_pair_units | Quarantine both; reason filtering is not a separate safe endpoint. |
| Privacy export decision | approve -> sr_export_decide -> approved queue -> privacy worker claim/snapshot -> sr_export_page includes pairs/occurrences | Quarantine whole decision operation; reject/escalate not separately exposed. Admin list metadata remains future eligible. |
| Cleanup retry | sr_retention_retry -> worker cleanup -> sr_retention_prepare reads pair-linked disputes | Quarantine indirect worker admission. |
| Generic retention hold | finder_message -> retention_holds trigger sr_support_finder_hold_lock reads qr_codes.pair_id and locks tag_pairs | Quarantine whole generic hold endpoint, no resource-type UI workaround. |
| Generic hold release | releases hold that can permit scheduled cleanup through pair-inspecting sr_retention_prepare | Conservative quarantine; not claimed to directly mutate/inspect pairs on every release. |
| Existing payment/cancellation/print/shipment mutations | pair allocation/reservations/QA/manifests/credentials or mixed pair membership | All prior exclusions retained; no split branch or backend bypass. |

The inventory has an explicit table for all 70 operations: why, read/mutation, indirect dependencies, frontend references and accidental invocation risks. The correction also reviews **all 30 previously eligible mutations**, including those retained. No absence-of-string-match is treated as proof against dynamic frontend requests.

## Legitimate functionality preserved for later phases

Safe template metadata/drafts, synthetic preview/submit, evidence-backed publication/variant binding/retirement remain candidates: TemplateRepository -> draft service or registry lifecycle changes template/catalog records; synthetic render uses fixed preview.invalid input, not real pair tokens. Preview/submit fail closed on Windows because isolated_preview currently requires Linux; do not weaken isolation or change backend for convenience. General template management remains outside Products allowlist; approved-template choices does not supply publication evidence.

Notification metadata/retry remains eligible after tracing retry_gate and worker recipient preparation through outbox, finder-message and auth-user records, not QR/pair rows. Finance Sheet Sync metadata/retry remains eligible: only finance.sync jobs, order/sync masked reporting and Google Sheets; relation/retention trigger guards do not turn it into allocation.finalize. These are useful real admin capabilities, not quarantined simply because of the names finder or finance. Providers/worker approvals are release prerequisites; no worker ran.

Account directory and approved suspension/restoration/recovery escalation remain eligible. The account lifecycle SQL changes account state/session epoch/events/approvals, not pair ownership or activation; case authorization alone is not a pair operation. All security_admin/custodian/recent-auth/Origin/revision constraints remain mandatory. Audit metadata, storage metadata, privacy list metadata, print-job metadata, payment attempt/evidence reads, typed shipment item metadata, liveness and dashboard trends remain future candidates. Future screens must avoid generic client actions or hooks that also reach quarantined routes.

## Authentication, deployment and architecture requirements

Keep existing Next application at frontend/app/admin, actual admin layouts/components and current admin session/MFA flow. verifiedSession first validates provider user, then transports access token server-side; HttpOnly Supabase SSR cookies, Secure in production, SameSite and proxy refresh remain. Backend verifies bearer JWT, live session, email/MFA, explicit roles and RLS independently. Catalog roles: operations/security_admin/superadmin. Frontend catalog.manage and role preview never grant a backend privilege.

Preserve independent customer/admin deployment settings: origin allowlists, web/API origins, redirect/MFA return targets, cookie boundaries and auth provider settings belong to each deployment; do not force a shared browser origin, change callbacks or merge cookies. API origin stays server-only with existing validateOrigin. Do not use customer checkout/payment relays as admin product transport. No browser service role, readiness key, database URL, signing/encryption key or privileged token persistence. Auth provider publishable key and scoped public raster upload parameters are not production secret exports.

Reuse existing server relays, no new open proxy. Current catalog-api forwards bearer/key/If-Match and checks mutation POST Origin; backend enforces catalog authorization. Future task must constrain method/path/query/body combinations, validate responses and preserve Origin/CSRF failure handling rather than broadening the regex. Catalog relay does not itself fetch staffState: preserve page guards and backend checks, optionally narrow server gate without assuming current relay has a separate capability check.

## Existing frontend reuse and justified controls

Reuse current ProductsList, AddProductForm and AdminProductDetails with AdminPage/AdminShell/header/sidebar/toasts/AdminConfirmDialog. Shared mock service stays demo-only; real state must not persist into safereturn_demo_db or show synthetic success. Existing product-admin-live.tsx and catalog-admin.tsx provide request/payload/size/upload logic to inspect and reuse, not replacement screens. Current real UUID detail URLs select legacy editor, so the later task must deliberately bind those real IDs into current admin UI and avoid mounting a hidden old editor.

Reuse lib/product-admin.ts, catalog-admin-feedback.ts, catalog-template-choices.ts, catalog-template-picker.tsx/useTemplateChoices, catalog-template-relay.ts, catalog-api route and auth modules. Missing justified controls: backend category selector and optional create/edit dialogs; real qr_type, catalog versions and variant fields; image alt/order/main/unlink; publication/archive confirmation through existing PATCH status. Existing PKR/copy-limit inputs are retained and mapped. No product-delete API or invented publish/archive route exists.

## Proposed first implementation task (not executed)

**Connect the current Products List, Add Product and Product Details/Edit screens through the existing authenticated catalog relay, using only the 14-operation allowlist.**

1. Finalize exact product/category/variant/image/choice parsers from source projections and schemas, error mapping and per-operation version/idempotency rules; no broad mutation wrapper.
2. Constrain the existing relay with the closed method/path/query matrix while preserving backend authorization, Origin/CSRF, bearer forwarding, no-store and error privacy. Keep deployment settings separate.
3. Bind current list/detail/category reads first and preserve visible UI. Add real draft save, update, variant and signed-image controls after read/error behavior is validated. No console replacement or automatic stock/order/support loads.
4. Add only API-backed controls described above. Keep mock fixtures separate, retain field values on conflict, refetch versions and reconfirm. Respect backend publication completeness; never invoke stock/generation/QA to satisfy a catalog validation error.
5. Use isolated catalog-only fixtures and a deny-by-default request harness. Permit exactly allowlisted SafeReturn calls plus auth/scoped raster infrastructure, reject every other request including mount/prefetch/setup/teardown. No QR fixtures, checkout/payment verification, migrations, flag changes, workers or forbidden endpoint tests.
6. Verify auth/roles/MFA/revocation and Origin; list UUID cursor; 400/401/403/404/409/412/422/503; replay consistency; source of If-Match; variant preservation; signed upload then verified attachment; historical price snapshots unchanged; responsive/bilingual/loading/empty/error behavior. Distinguish parser/unit mocks from live PostgreSQL/provider/browser acceptance.

## Remaining blockers and clarification points

- Runtime schema/grants/flags are unverified here. Latest repository status reports development head 0043 and closed single-checkout/standalone-owner gates; old chronological notes are stale. This is not production readiness, and Products needs no gate opening/migration in this task.
- Catalog responses include generic OpenAPI dict schemas and Decimal strings: enforce actual source shape, versions, optional values and strict field validation. Relay currently returns parsed backend JSON without complete response-schema/size checks.
- Product and variant PATCH schemas are full shapes with defaults, not generic sparse patch; partial serialization can silently reset fields. Read/merge/validate and preserve variants. Category list is capped 100, product list uses UUID cursor and lacks arbitrary backend search/global count.
- Approved-template choices is config discovery, not registry evidence. Publication requires active proper category, supported variant/material/size/currency and approved binding/evidence, verified images and deployed deferred completeness constraints. Missing evidence must remain a validation error, not a QR operation.
- Cloudinary credentials/preset/folder and profile data keys for encrypted receipts must be configured server-side; source/provider checks never prove their availability. Authorization POST still needs valid ImageRequest; signed upload and attachment are distinct replay intents; attachment does not imply cross-product/public_id ownership constraints beyond source folder checks, so do not invent a stronger guarantee.
- Deferred constraints may fail at transaction commit through SQLAlchemy/AccessError rather than the advertised 422. Document and handle actual error contract; do not change backend validation to make forms appear complete.
- Unlink/metadata/publication can fail when a published product would lose its verified main image/approved size. Keep existing immutable model and historical order constraints.
- No independently safe generic support-case, order-list operations projection, financial case or reconciliation endpoint was found; do not implement a frontend-only safe subset of a quarantined operation. Rich telemetry, full staff-role management, deletion-review, audit export/detail/global payments queue remain backend gaps, not invented URLs/buttons.
- Existing legacy UI/clients can already reference restricted routes. This correction neither disables production nor authorizes using them. Future integration must not mount allocation.tsx, legacy inventory/order/support/print/privacy/retention consoles, initialize broad clients, or prefetch linked pages as a side effect of Products.

## Verification and stop

Correction validation is documentation-only: reconcile all 162 classifications, all eight explicit quarantines, 70 denied entries, the 30 mutation-chain rows and the same 14-operation allowlist across reports. No HTTP/database/provider/renderer test or excluded setup was executed. No application code was changed.

Updated files: frontend/ADMIN_BACKEND_API_INVENTORY.md; frontend/ADMIN_FRONTEND_BACKEND_MAPPING.md; frontend/ADMIN_BACKEND_INTEGRATION_PLAN.md. Stop after these reports; no connection/implementation is included.
