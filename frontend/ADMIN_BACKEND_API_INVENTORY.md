# SafeReturn admin backend API inventory — corrected default-deny audit

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



## Current Phase 11 Privacy addendum — 24 October 2026

OptionA continues implementation while consolidating live acceptance in Phase14. Phase9/10 implementations and disabled gates are preserved;0044 is unapplied. Historical counts and the corrected Products budget below are unchanged.

| Candidate operation | Independently verified service chain | Current disposition |
|---|---|---|
| GET `/api/v1/admin/privacy/exports` — API-330 | main.py registration -> privacy_exports.listing -> explicit Security Admin/email/MFA ->0022 sr_export_list -> sr_is_staff/sr_export_authorized (current0030)/sr_export_status. Authority reads privacy_export_authorities, case metadata, staff/Auth/account epochs. No worker/pair helper/relation or mutation. | ELIGIBLE/SOURCE-SAFE; strict read-only implementation prepared. **NOT LIVE ADMITTED**; privacyMetadataAdmitted() is literal false pending Phase14. |
| POST `/api/v1/admin/privacy/exports/{request_id}/decisions` — API-327 | Current-revision/case-bound/recent-MFA preflight, idempotency, decision+audit; approve admits privacy worker snapshot -> sr_export_page -> tag_pairs and order_item_qr_uses.0043 retains these pair branches. | **QUARANTINED**, including reject/escalate on this mixed endpoint. No dialog/transport; admin non-GET is405 before Auth/upstream. |

Exact metadata request budget is API-330 GET with limit/cursor plus existing own `/api/v1/me/staff-security` bootstrap. No status/id filter or admin detail endpoint exists; filters/details are explicitly current-authorized-page views. Dedicated admin relay forwards only request_id/case_id/status/revision/scope_version/created_at/ready_at/expires_at, discarding categories/manifest IDs/counts. No payload, customer identity, worker, customer export/download/grant/create, case lookup, Support/Finance, generic Orders or QR operation is added. No updated timestamp or complete total is invented. All70 historical exclusions/quarantines retain their force; API-327 is not counted twice.

Source/SQL/worker trace, actual isolated checks, privacy controls and Phase14 blockers: [Phase11 progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-11--privacy-requests--export-review-2026-10-24). A source-safe list is not evidence of installed RLS/authority acceptance; no Cloud call was made.

## Current Phase 10 Notifications addendum — 24 October 2026

Phase9 is **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED**. Its Support endpoints/gate, unapplied0044 and provisioning are unchanged. Historical162-operation totals and original corrected14-operation Products allowlist below are preserved.

| Exact operation | Fresh source review | Current integration boundary |
|---|---|---|
| GET `/api/v1/admin/notification-outbox` (API-101) | ELIGIBLE/SOURCE-SAFE. Actual router registration + operations/security_admin verified-email/MFA guard ->0020 sr_notification_metadata -> outbox/attempts/sr_notification_retry_gate -> finder_messages/auth.users. No QR relation/helper. | Closed Notifications contract implementation only. List, id-based detail/history and supported limit/cursor/status/id/attempt_limit/attempt_before; NOT LIVE ADMITTED, server read gate false. |
| POST `/api/v1/admin/notification-outbox/{id}/retry` (API-102) | ELIGIBLE/SOURCE-SAFE, externally consequential mutation. Actor/key serialization, encrypted receipt replay, row lock/expected count, safe reason, dead/transient/recipient/budget/window gate -> outbox update/audit/receipt. Reviewed notification triggers and later worker recipient/delivery chain use outbox/attempt/finder/Auth records only. | Controlled single-event retry implemented for isolated tests; genuine mutation/provider/concurrency acceptance pending. Separate retry gate false; no live retry executed or permitted by code. |

Existing `/api/v1/me/staff-security` remains the sole supporting SafeReturn bootstrap. No wildcard admission, additional detail endpoint, recipient lookup, channel query, Compose/Bulk Send/Email/SMS Send, worker/provider request, generic Orders/Support/Finance or QR operation is added. Channel is not supplied by API-101; the UI derives email only for the worker's supported finder event and filters the current page locally. All70 historical excluded/quarantined operations remain denied.

Complete transitive trace, actual tests, files, residual deployed/fixture/provider blockers and live non-admission: [Phase10 progress](ADMIN_BACKEND_INTEGRATION_PROGRESS.md#phase-10--notifications-management-2026-10-24). Source eligibility is not a claim of deployed RLS or live acceptance.

Correction date: 23 October 2026 (Asia/Karachi). **This corrected policy replaces the earlier independent-QR exception and Overview-first recommendation.** Audit/report edits only. No endpoint called/tested, app import/lifespan run, database connection, worker, render, hook, prefetch, secret read or application change during correction. The prior in-memory route registration comparison remains evidence from the earlier audit, not a new runtime test.

## Repository, counting and evidence

Backend `backend/app/main.py` and `backend/app/api/v1/`; admin `frontend/app/admin/`; components `frontend/components/`; server relays/contracts `frontend/lib/`. The prior audit reconciled nested FastAPI include registrations with in-memory OpenAPI: 162 business method/path operations, no duplicate or hidden application route; framework docs excluded. Existing source/contract excerpts and schemas below are retained as evidence, not authorization to invoke their endpoints. No route was proved operational.

Corrected mutually exclusive totals: **42 ELIGIBLE; 10 SUPPORTING; 1 BLOCKED; 47 QR-PAIR EXCLUDED; 23 QUARANTINED; 39 NOT ADMIN = 162**. Combined excluded/quarantined: **70**. Eligible/supporting together: 52; first-phase strict allowlist: **14** (11 eligible product/category/image/variant operations, 2 catalog lookups and 1 own staff-security bootstrap). Other endpoints remain denied to Phase 1 even when generally eligible. NOT ADMIN and BLOCKED do not grant access either.

Default-deny: an endpoint name, GET method, sanitized response, role branch, independent/typed label or absent direct pair INSERT does not authorize integration. Follow transitive service/SQL/trigger/worker paths. If any reachable branch inspects/generates/reserves/allocates/assigns/activates/exports credentials/changes ownership or pair lifecycle, deny the whole operation unless a separate permitted backend endpoint already exists. No backend bypass/splitting is proposed. The eight owner-named operations and allocation retry are quarantined irrespective of standalone behavior. Existing production functions/mocks stay untouched.

## Authentication and error requirements

Reuse Next server-only verifiedSession/staffState, Supabase SSR HttpOnly sessions, MFA and same-origin authenticated relays. Backend receives bearer token and independently verifies JWT/live session/verified email/active MFA/nonrevoked role plus RLS. Catalog permits operations, security_admin or superadmin explicitly; frontend catalog.manage and role preview cannot replace backend checks. `/me/staff-security` permits AAL1 bootstrap but product actions require MFA. Product routes do not add a new recent-login requirement; keep existing step-up requirements where defined for other modules.

Keep configured admin/customer deployment origins and auth callbacks/cookies independent; server API origin is not a browser origin and adds no /api/v1 suffix. BFF mutations need Origin/CSRF controls and per-method/path validation; no generic proxy or browser token/secrets in localStorage/NEXT_PUBLIC. Preserve no-store, bounded validation, stable Idempotency-Key, quoted If-Match and backend audit. Current catalog relay checks POST Origin and forwards permitted catalog paths but does not itself call staffState; pages do, backend remains authoritative. It needs an explicit method/path matrix and response validation in the future Products task, not an application change now.

Per-route schemas/errors below remain authoritative source metadata: distinguish 400 missing key, 401 session, 403 role/MFA, 404 missing object, 409 replay/state/constraint conflict, 412 stale If-Match, 422 body/publication validation and 503 configuration/provider/storage/key failure where implemented. Some deferred DB constraints surface as 503 via SQLAlchemy auth dependency; do not promise all business violations map to 422. No universal error body or pagination model is assumed.

## STRICT ALLOWLIST — first Products integration phase

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

Every catalog route was traced separately, including both image POST modes. Product RLS uses explicit staff membership. `mutation` writes encrypted idempotency receipt/audit and gates product/variant operations with an advisory registry lock. `publishable -> catalog_eligibility -> sr_template_catalog_(type_)eligible -> sr_template_revision_clear` reads template bindings, revisions, approved assets and signing-authority/evidence records, not live QR/pair inventory or secrets. Shared module contains order/manifest helpers but these catalog call paths do not invoke resolve/freeze/order_specs/registry_manifest.

Relevant trigger/policy review: 0003_workflows_security.py (catalog/receipt/audit role policies), 0015_public_catalog.py (versions/media/delete policy), 0034_print_template_publication.sql (registry gate, catalog guard, revision-clear), 0036_product_copy_pricing.sql (required price), 0039_single_qr_catalog.sql (immutable commerce model and deferred catalog completeness). Product-model guard may check historical order_items to prevent type rewrites; that is an item-snapshot constraint, not pair allocation/inspection. Catalog constraints touch products, variants, images, categories and template metadata only; no durable allocation/render job enqueue, pair inspection or QR secret/ownership/lifecycle call found in these reachable paths. This is source-level assurance, contingent on deployed schema matching source, not runtime acceptance.

Public catalog comparison, binding management, liveness, dashboard, orders, finance, support and all QR stock/allocation/context routes are **not** in the first-phase allowlist. A public Cloudinary raster upload URL returned by the approved image route is a separate scoped provider operation, not an additional SafeReturn API or QR export; preserve signed target/MIME/5 MB verification and never expose API secret.

## Mutation call-chain review — every prior eligible mutation

Review includes Python service helpers, source migrations/trigger branches and worker admissions where a request can enable later work. No worker or function was executed. No-effect-on-pairs refers to this reachable source chain, not merely its HTTP name.

| Previously proposed mutation | Corrected decision | Actual chain / evidence |
|---|---|---|
| `POST /api/v1/admin/catalog/categories` | ELIGIBLE; Phase 1 | mutation -> insert product_categories -> encrypted idempotency receipt + audit. No pair helper or worker. |
| `PATCH /api/v1/admin/catalog/categories/{category_id}` | ELIGIBLE; Phase 1 | mutation -> lock category using category.catalog_version -> update category -> receipt/audit. No pair helper. |
| `POST /api/v1/admin/products` | ELIGIBLE; Phase 1 | mutation -> registry gate (advisory lock only) -> INSERT draft product, commerce_model=single_qr/allows_new_pair=false -> receipt/audit. Product metadata is not identity allocation. |
| `PATCH /api/v1/admin/products/{product_id}` | ELIGIBLE; Phase 1 | mutation -> registry gate -> lock product -> update metadata -> publishable -> template catalog eligibility/approval checks only -> receipt/audit. |
| `POST /api/v1/admin/products/{product_id}/variants` | ELIGIBLE; Phase 1 | mutation -> registry gate -> lock parent at product version -> insert variant with parent price -> bump parent version -> publishable -> receipt/audit. |
| `PATCH /api/v1/admin/product-variants/{variant_id}` | ELIGIBLE; Phase 1 | mutation -> registry gate -> find/lock parent -> lock variant at variant version -> update variant with parent price -> bump parent -> publishable -> receipt/audit. |
| `POST /api/v1/admin/products/{product_id}/images` | ELIGIBLE; Phase 1 | mutation -> authorize_upload=true: lock parent, sign public catalog raster upload; normal branch: verified_asset Cloudinary read -> lock parent -> image insert/primary adjustment -> bump parent -> receipt/audit. Both branches reviewed. |
| `PATCH /api/v1/admin/products/{product_id}/images/{image_id}` | ELIGIBLE; Phase 1 | mutation -> lock parent at product version -> lock image within product -> adjust primary/alt/order -> bump parent -> publishable -> receipt/audit. |
| `DELETE /api/v1/admin/products/{product_id}/images/{image_id}` | ELIGIBLE; Phase 1 | mutation -> lock parent at product version -> DELETE product image link within product -> bump parent -> publishable -> receipt/audit. Does not delete provider media or QR credentials. |
| `POST /api/v1/admin/qr-inventory/batches` | QUARANTINED; never Phase 1 | Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. |
| `POST /api/v1/admin/notification-outbox/{id}/retry` | Retain ELIGIBLE; later only | notification command -> sr_notification_retry -> retry_gate (outbox/attempts/finder message/recipient account) -> worker process_one -> sr_notification_recipient (finder message/auth user) -> email provider; no QR/pair query. 0020_notification_operations.py, 0014a_notification_delivery.py, workers/notifications.py. |
| `POST /api/v1/admin/finance/sheet-sync/{sync_id}/retry` | Retain ELIGIBLE; later only | retry_sheet_sync -> finance_sheet_sync retry + durable_jobs finance.sync only -> relation/retention/cancellation/financial trigger guards -> finance worker order/sync projection -> Google Sheets. No allocation.finalize job, pair read or credentials export. retention.py, 0019_retention_recovery.py, workers/finance_retention.py. |
| `POST /api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry` | QUARANTINED; never Phase 1 | sr_retention_retry revives cleanup -> finance_retention worker -> sr_retention_prepare checks order_pair_units/support-case pair references before private object deletion. |
| `POST /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | QUARANTINED; never Phase 1 | Generic hold can target finder_message -> retention_holds INSERT trigger sr_support_finder_hold_lock reads qr_codes.pair_id/order_pair_units and locks tag_pairs. |
| `DELETE /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | QUARANTINED; never Phase 1 | Release can clear a finder-message/artifact/order hold, enabling existing cleanup admission whose sr_retention_prepare checks pair-linked disputes. No separately scoped release endpoint proves a pair-free background chain. |
| `POST /api/v1/admin/support-cases` | QUARANTINED; never Phase 1 | create_case -> sr_support_create validates tag_pairs/order_pair_units when pair_ref supplied; support_cases INSERT also invokes sr_retention_admission pair-link lookup. Null form fields do not establish an independent permitted endpoint. |
| `PATCH /api/v1/admin/support-cases/{case_id}` | QUARANTINED; never Phase 1 | update_case -> sr_support_change (0035 wrapper -> v34) locks order_pair_units/tag_pairs and calls sr_support_context; claim, note and status edits are all mixed. |
| `POST /api/v1/admin/privacy/exports/{request_id}/decisions` | QUARANTINED; never Phase 1 | approve -> sr_export_decide marks request approved -> privacy_exports worker claim/snapshot -> sr_export_page includes pairs/occurrences. Reject/escalate branches do not make the mixed decision endpoint eligible. |
| `POST /api/v1/admin/print-templates` | Retain ELIGIBLE; later only | command(create) -> TemplateRepository -> sr_template_service -> renamed draft_service_v33 -> template row/version + receipt/audit; no pair stock. |
| `POST /api/v1/admin/print-templates/{template_id}/revisions` | Retain ELIGIBLE; later only | command(revision) -> template draft service -> revision/content/provenance + template version; no order identity/QR DML. |
| `PATCH /api/v1/admin/print-templates/{template_id}/revisions/{revision_id}` | Retain ELIGIBLE; later only | command(edit) -> template draft service -> draft content/version + provenance trigger; no pair query. |
| `POST /api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/preview` | Retain ELIGIBLE; later only | proof -> preview_input + preview_admit -> isolated_preview -> render_synthetic with fixed preview.invalid token and enrolled assets. No real order/token/provider/pair input. Windows isolation fails closed. |
| `POST /api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa` | Retain ELIGIBLE; later only | prepare -> same synthetic proof -> command(submit) -> template draft service marks pending_qa/fingerprint. No physical pair QA or inventory change. |
| `POST /api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/publish` | Retain ELIGIBLE; later only | publication_proof -> template evidence/RegistryRepository approval_input/context/publisher_check -> sr_template_lifecycle(publish) updates template approvals/revision/key metadata. Template signing authority is not QR-pair credentials. |
| `POST /api/v1/admin/print-template-bindings` | Retain ELIGIBLE; later only | RegistryRepository bind -> sr_template_lifecycle(bind) -> variant binding, registry source, variant version; catalog guard/completeness checks. Binds print revision to product variant, never QR pair to owner/order. |
| `POST /api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/retire` | Retain ELIGIBLE; later only | RegistryRepository retire -> lifecycle(retire) verifies no active binding, updates template revision/key status only. Not QR lifecycle. |
| `POST /api/v1/admin/support-cases/{case_id}/financial-decisions` | QUARANTINED; never Phase 1 | financial decision calls load_context and sr_financial_case_apply -> sr_financial_case_context; pair locks occur even though final output is finance metadata. |
| `POST /api/v1/admin/users/{user_id}/suspensions` | Retain ELIGIBLE; later only | execute -> sr_lifecycle_context/apply/save_receipt -> approved account security state/epoch/events; reads case binding/custodians. No pair ownership/status DML or QR query. |
| `POST /api/v1/admin/users/{user_id}/restorations` | Retain ELIGIBLE; later only | Same account service chain with restore: account state/epoch and approval consumption only; no pair activation/ownership restoration. |
| `POST /api/v1/admin/users/{user_id}/recovery-escalations` | Retain ELIGIBLE; later only | Same account service chain with recovery_escalated: referral event/receipt; no QR credential retrieval or password reset. |

## Explicit exclusion and quarantine table

All 70 denied operations appear below. Read-only can still acquire locks/audit or inspect pairs; read/mutation labels describe handler intent and do not imply safety. Literal-reference absence is not proof against dynamic URLs. Frontend names are under frontend/components or frontend/lib/api unless a route is named. Existing references are recorded for avoidance, not removal.

| Endpoint | Status / why | Read or mutation | Indirect pair dependencies | Frontend references | Accidental integration risk |
|---|---|---|---|---|---|
| `POST /api/v1/me/checkout/quotes` | QR-PAIR EXCLUDED; Legacy quote/confirm inspects pair capacity and can reserve order_pair_units; never used as catalog validation/setup. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | checkout.tsx, checkout/api; customer flow, never imported for product form initialization. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/me/checkout/quotes/{quote_id}/confirm` | QR-PAIR EXCLUDED; Legacy quote/confirm inspects pair capacity and can reserve order_pair_units; never used as catalog validation/setup. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | checkout.tsx, checkout/api; customer flow, never imported for product form initialization. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/qr-batches` | QR-PAIR EXCLUDED; Legacy batch-generation handler creates paired inventory/credential material. New generation integration prohibited. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; admin-batches/admin-inventory mocks; legacy live branch exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/tag-pairs` | QR-PAIR EXCLUDED; Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; pair/batch detail routes can auto-load. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/tag-pairs/{pair_id}` | QR-PAIR EXCLUDED; Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; pair/batch detail routes can auto-load. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/qr-batches` | QR-PAIR EXCLUDED; Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; pair/batch detail routes can auto-load. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/qr-batches/{batch_id}` | QR-PAIR EXCLUDED; Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; pair/batch detail routes can auto-load. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/inventory/summary` | QR-PAIR EXCLUDED; Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx, inventory-relay.ts; pair/batch detail routes can auto-load. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/qr-inventory/batches` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Mutation / may authorize later work | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/admin/qr-inventory/batches` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/admin/qr-inventory/batches/{batch_id}` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/admin/qr-inventory/summary` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/admin/qr-inventory/codes` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/admin/qr-inventory/codes/{qr_id}` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR stock/code/generation surface; explicit owner quarantine applies regardless of independent implementation or absence of pair DML. | No qr-inventory literal reference found in frontend/app, components or lib. Existing inventory UI/relay is legacy pair-based; no new typed view permitted. | Prior optional typed inventory/generation proposal withdrawn; no registration/init/prefetch. |
| `GET /api/v1/public/qr/{token}/activation-context` | QR-PAIR EXCLUDED; Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer activate page and QR server/actions transport; legacy activation flow. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/me/tag-pairs/activation-intents` | QR-PAIR EXCLUDED; Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer activate page and QR server/actions transport; legacy activation flow. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/me/tag-pairs/activations` | QR-PAIR EXCLUDED; Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer activate page and QR server/actions transport; legacy activation flow. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr/{qr_id}/lost-profile` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PUT /api/v1/me/qr/{qr_id}/lost-profile` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr/{qr_id}/ice-profile` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PUT /api/v1/me/qr/{qr_id}/ice-profile` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr/{qr_id}/ice-contacts` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/me/qr/{qr_id}/ice-contacts` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PATCH /api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `DELETE /api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr/{qr_id}/contact-preferences` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PUT /api/v1/me/qr/{qr_id}/contact-preferences` | QR-PAIR EXCLUDED; QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | customer QR editing UI and qr-server.ts/actions; unrelated admin integration must not import it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/tag-pairs` | QR-PAIR EXCLUDED; Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | owner-collection.tsx and customer QR/kit pages and QR server transport. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/tag-pairs/{pair_id}` | QR-PAIR EXCLUDED; Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | owner-collection.tsx and customer QR/kit pages and QR server transport. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr` | QR-PAIR EXCLUDED; Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | owner-collection.tsx and customer QR/kit pages and QR server transport. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/qr/{qr_id}` | QR-PAIR EXCLUDED; Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | owner-collection.tsx and customer QR/kit pages and QR server transport. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/support-cases/{case_id}/independent-qr` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | QR support/context surface; explicit quarantine irrespective of independent implementation. | No support-cases/.../independent-qr literal reference found in frontend app/components/lib; prior recommended support panel would introduce it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/payment-attempts/{attempt_id}/reviews` | QR-PAIR EXCLUDED; Generic review verify branch allocates order_pair_units and can enqueue allocation.finalize; finance label does not isolate it. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | payments.tsx, allocation.tsx, payments/api; payment review server actions; orders-console read transport also exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/orders/{order_id}/qr-allocation` | QUARANTINED; Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize. | Read-only handler | Allocation-related surface; owner explicitly forbids status call. Do not mount allocation hook. | allocation.tsx useEffect/load -> /payments/api -> backend status; payments.tsx mounts allocation UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/orders/{order_id}/qr-allocation/retry` | QUARANTINED; Allocation retry is quarantined by default-deny, not merely waiting for release gates. Independent-QR terminology does not authorize it. | Mutation / may authorize later work | Allocation retry is quarantined by default-deny, not merely waiting for release gates. Independent-QR terminology does not authorize it. | payments.tsx, allocation.tsx, payments/api; payment review server actions; orders-console read transport also exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/tag-pairs/{pair_id}/activation-history` | QR-PAIR EXCLUDED; Activation-history/public-status workflow inspects pair history or changes pair-linked public availability/lifecycle. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | qr-lifecycle.tsx, qr-lifecycle-relay.ts; customer kit lifecycle route. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PATCH /api/v1/me/qr/{qr_id}/public-status` | QR-PAIR EXCLUDED; Activation-history/public-status workflow inspects pair history or changes pair-linked public availability/lifecycle. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | qr-lifecycle.tsx, qr-lifecycle-relay.ts; customer kit lifecycle route. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/orders/{order_id}/print-jobs` | QR-PAIR EXCLUDED; Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | printing-admin.tsx, print-console.tsx; print-jobs/api and printing-relay contain broader actions. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/print-artifacts/{artifact_id}/download-grants` | QR-PAIR EXCLUDED; Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | printing-admin.tsx, print-console.tsx; print-jobs/api and printing-relay contain broader actions. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/print-downloads` | QR-PAIR EXCLUDED; Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | printing-admin.tsx, print-console.tsx; print-jobs/api and printing-relay contain broader actions. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/print-jobs/{job_id}/qa` | QR-PAIR EXCLUDED; Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | printing-admin.tsx, print-console.tsx; print-jobs/api and printing-relay contain broader actions. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/tag-pairs/{pair_id}/print-qa` | QR-PAIR EXCLUDED; Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | printing-admin.tsx, print-console.tsx; print-jobs/api and printing-relay contain broader actions. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/me/orders/{order_id}` | QR-PAIR EXCLUDED; Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | fulfillment-admin.tsx, orders-console.tsx, shipments API; ready-to-ship page mounts live UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/orders/ready-to-ship` | QR-PAIR EXCLUDED; Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | fulfillment-admin.tsx, orders-console.tsx, shipments API; ready-to-ship page mounts live UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/shipments` | QR-PAIR EXCLUDED; Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | fulfillment-admin.tsx, orders-console.tsx, shipments API; ready-to-ship page mounts live UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PATCH /api/v1/admin/shipments/{shipment_id}` | QR-PAIR EXCLUDED; Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | fulfillment-admin.tsx, orders-console.tsx, shipments API; ready-to-ship page mounts live UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/orders/{order_id}` | QR-PAIR EXCLUDED; Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | fulfillment-admin.tsx, orders-console.tsx, shipments API; ready-to-ship page mounts live UI. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/orders` | QUARANTINED; Operations role automatically adds sr_fulfillment_eligible to order list. Finance-only branch is not a separate endpoint; mixed-role users select operations. Whole operation quarantined. | Read-only handler | Operations role automatically adds sr_fulfillment_eligible to order list. Finance-only branch is not a separate endpoint; mixed-role users select operations. Whole operation quarantined. | orders-console.tsx/orders-relay.ts; shipment-discovery.tsx/shipments API auto-load lists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/shipments` | QUARANTINED; Shipment list SHIP_COUNTS reads shipment_pairs and sr_fulfillment_eligible, even without a detail request. Read-only is not pair-free. | Read-only handler | Shipment list SHIP_COUNTS reads shipment_pairs and sr_fulfillment_eligible, even without a detail request. Read-only is not pair-free. | orders-console.tsx/orders-relay.ts; shipment-discovery.tsx/shipments API auto-load lists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/shipments/{shipment_id}` | QR-PAIR EXCLUDED; Legacy shipment detail returns shipment_pairs and pair packing QA/metadata; inspection is prohibited. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | orders-console.tsx/orders-relay.ts; shipment-discovery.tsx/shipments API auto-load lists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry` | QUARANTINED; sr_retention_retry revives cleanup -> finance_retention worker -> sr_retention_prepare checks order_pair_units/support-case pair references before private object deletion. | Mutation / may authorize later work | sr_retention_retry revives cleanup -> finance_retention worker -> sr_retention_prepare checks order_pair_units/support-case pair references before private object deletion. | finance-storage-admin.tsx, finance-storage-relay.ts; storage API; mock retention controls are separate. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | QUARANTINED; Generic hold can target finder_message -> retention_holds INSERT trigger sr_support_finder_hold_lock reads qr_codes.pair_id/order_pair_units and locks tag_pairs. | Mutation / may authorize later work | Generic hold can target finder_message -> retention_holds INSERT trigger sr_support_finder_hold_lock reads qr_codes.pair_id/order_pair_units and locks tag_pairs. | finance-storage-admin.tsx, finance-storage-relay.ts; storage API; mock retention controls are separate. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `DELETE /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | QUARANTINED; Release can clear a finder-message/artifact/order hold, enabling existing cleanup admission whose sr_retention_prepare checks pair-linked disputes. No separately scoped release endpoint proves a pair-free background chain. | Mutation / may authorize later work | Release can clear a finder-message/artifact/order hold, enabling existing cleanup admission whose sr_retention_prepare checks pair-linked disputes. No separately scoped release endpoint proves a pair-free background chain. | finance-storage-admin.tsx, finance-storage-relay.ts; storage API; mock retention controls are separate. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/support-cases` | QUARANTINED; case_id detail branch invokes sr_support_context -> order_pair_units/qr_codes/holds. No separate metadata-only backend endpoint for this mixed operation. | Read-only handler | case_id detail branch invokes sr_support_context -> order_pair_units/qr_codes/holds. No separate metadata-only backend endpoint for this mixed operation. | support-admin.tsx, support/api; admin-support-cases.tsx is mock but legacy live/detail branch exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/support-cases` | QUARANTINED; create_case -> sr_support_create validates tag_pairs/order_pair_units when pair_ref supplied; support_cases INSERT also invokes sr_retention_admission pair-link lookup. Null form fields do not establish an independent permitted endpoint. | Mutation / may authorize later work | create_case -> sr_support_create validates tag_pairs/order_pair_units when pair_ref supplied; support_cases INSERT also invokes sr_retention_admission pair-link lookup. Null form fields do not establish an independent permitted endpoint. | support-admin.tsx, support/api; admin-support-cases.tsx is mock but legacy live/detail branch exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `PATCH /api/v1/admin/support-cases/{case_id}` | QUARANTINED; update_case -> sr_support_change (0035 wrapper -> v34) locks order_pair_units/tag_pairs and calls sr_support_context; claim, note and status edits are all mixed. | Mutation / may authorize later work | update_case -> sr_support_change (0035 wrapper -> v34) locks order_pair_units/tag_pairs and calls sr_support_context; claim, note and status edits are all mixed. | support-admin.tsx, support/api; admin-support-cases.tsx is mock but legacy live/detail branch exists. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/privacy/exports/{request_id}/decisions` | QUARANTINED; approve -> sr_export_decide marks request approved -> privacy_exports worker claim/snapshot -> sr_export_page includes pairs/occurrences. Reject/escalate branches do not make the mixed decision endpoint eligible. | Mutation / may authorize later work | approve -> sr_export_decide marks request approved -> privacy_exports worker claim/snapshot -> sr_export_page includes pairs/occurrences. Reject/escalate branches do not make the mixed decision endpoint eligible. | privacy-exports.tsx, privacy-export-relay.ts; worker indirect chain; admin-privacy-requests mock is separate. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/me/orders/{order_id}/cancel` | QR-PAIR EXCLUDED; Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | cancellation-request.tsx and customer/order server paths; order consoles can fetch mixed detail. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/orders/{order_id}/cancellation-reconciliations` | QR-PAIR EXCLUDED; Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | cancellation-request.tsx and customer/order server paths; order consoles can fetch mixed detail. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/orders/{order_id}/cancellation-decisions` | QR-PAIR EXCLUDED; Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | cancellation-request.tsx and customer/order server paths; order consoles can fetch mixed detail. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/tag-pairs/{pair_id}/release-allocation` | QR-PAIR EXCLUDED; Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | cancellation-request.tsx and customer/order server paths; order consoles can fetch mixed detail. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/support-cases/{case_id}/financial-review` | QUARANTINED; load_context -> sr_financial_case_context (latest 0030 definition) locks order_pair_units and tag_pairs before financial case review. | Read-only handler | load_context -> sr_financial_case_context (latest 0030 definition) locks order_pair_units and tag_pairs before financial case review. | No dedicated financial-case frontend relay found; prior proposed tab would newly invoke it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/support-cases/{case_id}/financial-decisions` | QUARANTINED; financial decision calls load_context and sr_financial_case_apply -> sr_financial_case_context; pair locks occur even though final output is finance metadata. | Mutation / may authorize later work | financial decision calls load_context and sr_financial_case_apply -> sr_financial_case_context; pair locks occur even though final output is finance metadata. | No dedicated financial-case frontend relay found; prior proposed tab would newly invoke it. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/finance/reconciliation` | QUARANTINED; sr_finance_reconciliation -> sr_finance_reconciliation_rows checks order_pair_units for VERIFIED_ALLOCATION_MISMATCH. A reason filter does not expose a distinct independent endpoint. | Read-only handler | sr_finance_reconciliation -> sr_finance_reconciliation_rows checks order_pair_units for VERIFIED_ALLOCATION_MISMATCH. A reason filter does not expose a distinct independent endpoint. | orders-console.tsx, orders-relay.ts; finance/reconciliation page mounts live console. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/finance/reconciliation/counts` | QUARANTINED; sr_finance_reconciliation_counts -> rows helper checks legacy pair allocation; count-only response is still indirect inspection. | Read-only handler | sr_finance_reconciliation_counts -> rows helper checks legacy pair allocation; count-only response is still indirect inspection. | orders-console.tsx, orders-relay.ts; finance/reconciliation page mounts live console. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/qr-batches/{batch_id}/print-exports` | QR-PAIR EXCLUDED; Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx / legacy inventory API route expose export workflow; pair mocks remain untouched. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}` | QR-PAIR EXCLUDED; Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection. | Read-only handler | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx / legacy inventory API route expose export workflow; pair mocks remain untouched. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants` | QR-PAIR EXCLUDED; Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx / legacy inventory API route expose export workflow; pair mocks remain untouched. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `POST /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download` | QR-PAIR EXCLUDED; Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection. | Mutation / may authorize later work | Legacy/mixed pair surface; retain prior deny decision. See exact operation source/contract below. | inventory-console.tsx / legacy inventory API route expose export workflow; pair mocks remain untouched. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |
| `GET /api/v1/admin/dashboard/summary` | QUARANTINED; summary -> sr_dashboard_summary(fulfillment) -> sr_fulfillment_eligible; operations projection reads legacy pair allocation/QA. No backend group selector isolates safe groups for all roles. | Read-only handler | summary -> sr_dashboard_summary(fulfillment) -> sr_fulfillment_eligible; operations projection reads legacy pair allocation/QA. No backend group selector isolates safe groups for all roles. | admin-dashboard.tsx, dashboard-relay.ts; default admin-overview is a mock and must not silently mount API dashboard. | Yes if legacy module/detail/hook or generic client is reused; denied in corrected Phase 1. |


## Complete endpoint ledger

Every entry: Registered + in-memory OpenAPI match; runtime unverified. Source paths relative to project root. Request/response references resolve in the schema appendix. Generic `{}` is an absent useful schema, not a validated contract. Full parameters/errors and source return projections follow by operation ID.

| Method | Actual URL | Source | Authentication / permissions | Request body | Success schema | Status | Eligibility |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/health/live` | `backend/app/api/v1/health.py:34` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Liveness"}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/health/ready` | `backend/app/api/v1/health.py:38` | internal bearer | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Readiness"}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/staff-security` | `backend/app/api/v1/account.py:52` | JWT; own current staff roles; AAL1 bootstrap exception | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/StaffSecurity"}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/me` | `backend/app/api/v1/account.py:147` | JWT; own current staff roles; AAL1 bootstrap exception | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/AccountSummary"}}}} | Registered; runtime unverified | NOT ADMIN |
| PATCH | `/api/v1/me` | `backend/app/api/v1/account.py:154` | JWT; own current staff roles; AAL1 bootstrap exception | {"additionalProperties":false,"properties":{"display_name":{"anyOf":[{"maxLength":120,"type":"string"},{"type":"null"}],"title":"Display Name"},"preferred_locale":{"anyOf":[{"enum":["en","ur"],"type":"string"},{"type":"null"}],"title":"Preferred Locale"}},"title":"ProfileEdit","type":"object"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/AccountSummary"}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/privacy-consents` | `backend/app/api/v1/account.py:257` | JWT; own current staff roles; AAL1 bootstrap exception | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/account-deletion-requests` | `backend/app/api/v1/account.py:293` | JWT; own current staff roles; AAL1 bootstrap exception | {"properties":{"confirm":{"type":"boolean","const":true,"title":"Confirm"},"reason":{"anyOf":[{"type":"string","maxLength":1000},{"type":"null"}],"title":"Reason"}},"additionalProperties":false,"type":"object","required":["confirm"],"title":"DeletionRequest"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/audit-events` | `backend/app/api/v1/audit_events.py:80` | JWT; security_admin only | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__audit_events__Page"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/public/products` | `backend/app/api/v1/catalog.py:160` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{"type":"array","items":{"type":"object","additionalProperties":true},"title":"Response Api-003"}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/public/products/{sku}` | `backend/app/api/v1/catalog.py:183` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{"type":"object","additionalProperties":true,"title":"Response Api-004"}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/public/catalog/featured` | `backend/app/api/v1/catalog.py:195` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/public/catalog/categories` | `backend/app/api/v1/catalog.py:203` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/public/catalog/products/{product_id}/variants` | `backend/app/api/v1/catalog.py:209` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | SUPPORTING |
| POST | `/api/v1/me/checkout/quotes` | `backend/app/api/v1/checkout.py:280` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/QuoteRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/me/checkout/quotes/{quote_id}/confirm` | `backend/app/api/v1/checkout.py:367` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ConfirmRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/me/orders` | `backend/app/api/v1/checkout.py:566` | JWT; owner/staff guards in source | none / manual source | {} | Registered; runtime unverified | BLOCKED |
| POST | `/api/v1/me/checkout/item-quotes` | `backend/app/api/v1/item_checkout.py:168` | JWT; owner/staff guards in source | {"$ref":"#/components/schemas/ItemQuoteRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/checkout/item-quotes/{quote_id}/confirm` | `backend/app/api/v1/item_checkout.py:279` | JWT; owner/staff guards in source | {"$ref":"#/components/schemas/ConfirmRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/shipping-addresses` | `backend/app/api/v1/shipping_addresses.py:216` | JWT; owner/staff guards in source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/shipping-addresses` | `backend/app/api/v1/shipping_addresses.py:232` | JWT; owner/staff guards in source | {"$ref":"#/components/schemas/CreateAddress"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| PATCH | `/api/v1/me/shipping-addresses/{address_id}` | `backend/app/api/v1/shipping_addresses.py:270` | JWT; owner/staff guards in source | {"$ref":"#/components/schemas/UpdateAddress"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| DELETE | `/api/v1/me/shipping-addresses/{address_id}` | `backend/app/api/v1/shipping_addresses.py:315` | JWT; owner/staff guards in source | none / manual source | {"204":{}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/products` | `backend/app/api/v1/catalog.py:491` | JWT; operations, security_admin, superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/products/{product_id}` | `backend/app/api/v1/catalog.py:534` | JWT; operations, security_admin, superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/catalog/categories` | `backend/app/api/v1/catalog.py:548` | JWT; operations, security_admin, superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | SUPPORTING |
| POST | `/api/v1/admin/catalog/categories` | `backend/app/api/v1/catalog.py:563` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/CategoryRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| PATCH | `/api/v1/admin/catalog/categories/{category_id}` | `backend/app/api/v1/catalog.py:574` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/CategoryRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/products` | `backend/app/api/v1/catalog.py:597` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/CreateProductRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| PATCH | `/api/v1/admin/products/{product_id}` | `backend/app/api/v1/catalog.py:609` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/ProductRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/products/{product_id}/variants` | `backend/app/api/v1/catalog.py:641` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/VariantRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| PATCH | `/api/v1/admin/product-variants/{variant_id}` | `backend/app/api/v1/catalog.py:671` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/VariantRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/products/{product_id}/images` | `backend/app/api/v1/catalog.py:711` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/ImageRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| PATCH | `/api/v1/admin/products/{product_id}/images/{image_id}` | `backend/app/api/v1/catalog.py:761` | JWT; operations, security_admin, superadmin | {"$ref":"#/components/schemas/ImageMetadataRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| DELETE | `/api/v1/admin/products/{product_id}/images/{image_id}` | `backend/app/api/v1/catalog.py:778` | JWT; operations, security_admin, superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/qr-batches` | `backend/app/api/v1/inventory.py:119` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/BatchRequest"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/BatchResponse"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/tag-pairs` | `backend/app/api/v1/inventory_queries.py:171` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__inventory_queries__PairPage"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/tag-pairs/{pair_id}` | `backend/app/api/v1/inventory_queries.py:215` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PairDetail"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/qr-batches` | `backend/app/api/v1/inventory_queries.py:250` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__inventory_queries__BatchPage"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/qr-batches/{batch_id}` | `backend/app/api/v1/inventory_queries.py:286` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__inventory_queries__BatchMetadata"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/inventory/summary` | `backend/app/api/v1/inventory_queries.py:304` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/StockSummary"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/qr-inventory/batches` | `backend/app/api/v1/typed_inventory.py:189` | JWT; operations | {"$ref":"#/components/schemas/GenerateRequest"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/GenerationReceipt"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/qr-inventory/batches` | `backend/app/api/v1/typed_inventory.py:227` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__typed_inventory__BatchPage"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/qr-inventory/batches/{batch_id}` | `backend/app/api/v1/typed_inventory.py:241` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__typed_inventory__BatchMetadata"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/qr-inventory/summary` | `backend/app/api/v1/typed_inventory.py:250` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__typed_inventory__Summary"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/qr-inventory/codes` | `backend/app/api/v1/typed_inventory.py:259` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__typed_inventory__QRPage"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/qr-inventory/codes/{qr_id}` | `backend/app/api/v1/typed_inventory.py:270` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/QRMetadata"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/public/qr/{token}/activation-context` | `backend/app/api/v1/activation.py:121` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PublicActivationContext"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/me/tag-pairs/activation-intents` | `backend/app/api/v1/activation.py:146` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/IntentRequest"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/IntentResponse"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/me/tag-pairs/activations` | `backend/app/api/v1/activation.py:188` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ConfirmationRequest"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/ActivationResponse"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr/{qr_id}/lost-profile` | `backend/app/api/v1/profiles.py:299` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PUT | `/api/v1/me/qr/{qr_id}/lost-profile` | `backend/app/api/v1/profiles.py:305` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/LostEdit"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr/{qr_id}/ice-profile` | `backend/app/api/v1/profiles.py:337` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PUT | `/api/v1/me/qr/{qr_id}/ice-profile` | `backend/app/api/v1/profiles.py:343` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ICEEdit"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr/{qr_id}/ice-contacts` | `backend/app/api/v1/profiles.py:490` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/me/qr/{qr_id}/ice-contacts` | `backend/app/api/v1/profiles.py:600` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ContactEdit"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PATCH | `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | `backend/app/api/v1/profiles.py:618` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ContactEdit"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| DELETE | `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | `backend/app/api/v1/profiles.py:641` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"204":{}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr/{qr_id}/contact-preferences` | `backend/app/api/v1/profiles.py:699` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PUT | `/api/v1/me/qr/{qr_id}/contact-preferences` | `backend/app/api/v1/profiles.py:705` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/PreferenceEdit"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/tag-pairs` | `backend/app/api/v1/owner_qr.py:160` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__owner_qr__PairPage"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/tag-pairs/{pair_id}` | `backend/app/api/v1/owner_qr.py:209` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PairSummary"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr` | `backend/app/api/v1/owner_qr.py:232` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__owner_qr__QRPage"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/qr/{qr_id}` | `backend/app/api/v1/owner_qr.py:277` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/QRDetail"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/independent-qr` | `backend/app/api/v1/standalone_owner.py:80` | JWT; support for admin context; owner session otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/independent-qr/activation-intents` | `backend/app/api/v1/standalone_owner.py:103` | JWT; support for admin context; owner session otherwise | {"$ref":"#/components/schemas/Begin"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/independent-qr/activations` | `backend/app/api/v1/standalone_owner.py:118` | JWT; support for admin context; owner session otherwise | {"$ref":"#/components/schemas/Confirm"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/independent-qr/{qr_id}/history` | `backend/app/api/v1/standalone_owner.py:143` | JWT; support for admin context; owner session otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| PATCH | `/api/v1/me/independent-qr/{qr_id}/availability` | `backend/app/api/v1/standalone_owner.py:164` | JWT; support for admin context; owner session otherwise | {"$ref":"#/components/schemas/Availability"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/support-cases/{case_id}/independent-qr` | `backend/app/api/v1/standalone_owner.py:193` | JWT; support for admin context; owner session otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/public/qr/{token}` | `backend/app/api/v1/public_qr.py:75` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PublicQRProfile"}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/orders/{order_id}/payment-instructions` | `backend/app/api/v1/payments.py:34` | JWT; finance; typed allocation finance/operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/orders/{order_id}/payment-attempts` | `backend/app/api/v1/payments.py:209` | JWT; finance; typed allocation finance/operations | {"$ref":"#/components/schemas/PaymentRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/orders/{order_id}/payment-attempts` | `backend/app/api/v1/payments.py:291` | JWT; finance; typed allocation finance/operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/payment-attempts/{attempt_id}/evidence-uploads` | `backend/app/api/v1/payments.py:304` | JWT; finance; typed allocation finance/operations | {"$ref":"#/components/schemas/UploadRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/payment-attempts/{attempt_id}/evidence-finalize` | `backend/app/api/v1/payments.py:361` | JWT; finance; typed allocation finance/operations | {"$ref":"#/components/schemas/EvidenceRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/admin/payment-attempts/{attempt_id}/reviews` | `backend/app/api/v1/payments.py:427` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ReviewRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/orders/{order_id}/qr-allocation` | `backend/app/api/v1/payments.py:575` | JWT; finance; typed allocation finance/operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/admin/orders/{order_id}/qr-allocation/retry` | `backend/app/api/v1/payments.py:581` | JWT; finance; typed allocation finance/operations | {"$ref":"#/components/schemas/AllocationRetry"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/payment-evidence/{evidence_id}` | `backend/app/api/v1/payments.py:595` | JWT; finance; typed allocation finance/operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/orders/{order_id}/payment-attempts` | `backend/app/api/v1/payments.py:638` | JWT; finance; typed allocation finance/operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/me/tag-pairs/{pair_id}/activation-history` | `backend/app/api/v1/qr_lifecycle.py:181` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/History"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PATCH | `/api/v1/me/qr/{qr_id}/public-status` | `backend/app/api/v1/qr_lifecycle.py:270` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/Command"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__qr_lifecycle__Receipt"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/print-jobs/counts` | `backend/app/api/v1/print_queries.py:208` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__print_queries__Counts"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/print-jobs` | `backend/app/api/v1/print_queries.py:247` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__print_queries__Page"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/orders/{order_id}/print-jobs` | `backend/app/api/v1/printing.py:281` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/PrintJobRequest"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/orders/{order_id}/print-jobs` | `backend/app/api/v1/printing.py:308` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/print-jobs/{job_id}` | `backend/app/api/v1/printing.py:324` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-artifacts/{artifact_id}/download-grants` | `backend/app/api/v1/printing.py:391` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/print-downloads` | `backend/app/api/v1/printing.py:427` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/DownloadRequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/print-jobs/{job_id}/qa` | `backend/app/api/v1/printing.py:497` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/JobQARequest"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/tag-pairs/{pair_id}/print-qa` | `backend/app/api/v1/printing.py:608` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/PrintQARequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/orders/{order_id}/print-summary` | `backend/app/api/v1/printing.py:675` | JWT; operations | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/orders` | `backend/app/api/v1/fulfillment.py:78` | JWT; operations; admin order detail also finance | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/orders/{order_id}` | `backend/app/api/v1/fulfillment.py:175` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/me/orders/{order_id}/shipments` | `backend/app/api/v1/fulfillment.py:194` | JWT; operations; admin order detail also finance | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/orders/ready-to-ship` | `backend/app/api/v1/fulfillment.py:210` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/shipments/{shipment_id}/items` | `backend/app/api/v1/fulfillment.py:279` | JWT; operations; admin order detail also finance | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/shipments` | `backend/app/api/v1/fulfillment.py:413` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ShipmentRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| PATCH | `/api/v1/admin/shipments/{shipment_id}` | `backend/app/api/v1/fulfillment.py:490` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/ShipmentUpdate"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/orders/{order_id}` | `backend/app/api/v1/fulfillment.py:553` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/orders` | `backend/app/api/v1/fulfillment_queries.py:156` | JWT; orders operations/finance; shipment operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/OrderPage"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/shipments` | `backend/app/api/v1/fulfillment_queries.py:230` | JWT; orders operations/finance; shipment operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/ShipmentPage"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/shipments/{shipment_id}` | `backend/app/api/v1/fulfillment_queries.py:290` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/ShipmentDetail"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/public/qr/{token}/finder-messages` | `backend/app/api/v1/public_actions.py:122` | public; source-specific gates | {"$ref":"#/components/schemas/FinderMessageRequest"} | {"202":{"application/json":{"schema":{"$ref":"#/components/schemas/FinderReceipt"}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/public/qr/{token}/messages` | `backend/app/api/v1/public_actions.py:122` | public; source-specific gates | {"$ref":"#/components/schemas/FinderMessageRequest"} | {"202":{"application/json":{"schema":{"$ref":"#/components/schemas/FinderReceipt"}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/public/qr/{token}/contact-reveals` | `backend/app/api/v1/public_contacts.py:222` | public; source-specific gates | {"$ref":"#/components/schemas/ContactRevealRequest"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/ContactResponse"}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/public/qr/{token}/whatsapp-link` | `backend/app/api/v1/public_contacts.py:237` | public; source-specific gates | {"$ref":"#/components/schemas/WhatsAppRequest"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/WhatsAppResponse"}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/public/config` | `backend/app/api/v1/public_config.py:31` | public; source-specific gates | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PublicConfiguration"}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/public/abuse-reports` | `backend/app/api/v1/abuse_reports.py:130` | public; source-specific gates | {"$ref":"#/components/schemas/Report"} | {"202":{"application/json":{"schema":{"$ref":"#/components/schemas/app__core__abuse_intake__Receipt"}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/notification-outbox` | `backend/app/api/v1/notification_operations.py:41` | JWT; operations, security_admin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/notification-outbox/{id}/retry` | `backend/app/api/v1/notification_operations.py:85` | JWT; operations, security_admin | {"$ref":"#/components/schemas/Retry"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/me/finder-messages` | `backend/app/api/v1/messages.py:123` | JWT; owner/staff guards in source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/finder-messages/{message_id}` | `backend/app/api/v1/messages.py:185` | JWT; owner/staff guards in source | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| PATCH | `/api/v1/me/finder-messages/{message_id}` | `backend/app/api/v1/messages.py:270` | JWT; owner/staff guards in source | {"$ref":"#/components/schemas/MessageUpdate"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| DELETE | `/api/v1/me/finder-messages/{message_id}` | `backend/app/api/v1/messages.py:295` | JWT; owner/staff guards in source | none / manual source | {"204":{}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/finance/sheet-sync` | `backend/app/api/v1/retention.py:85` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/finance/sheet-sync/{sync_id}/retry` | `backend/app/api/v1/retention.py:147` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | none / manual source | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/storage/artifacts` | `backend/app/api/v1/retention.py:220` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry` | `backend/app/api/v1/retention.py:271` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | {"$ref":"#/components/schemas/RetentionHoldRequest"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | `backend/app/api/v1/retention.py:289` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | {"$ref":"#/components/schemas/RetentionHoldRequest"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| DELETE | `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | `backend/app/api/v1/retention.py:391` | JWT; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin | none / manual source | {"204":{}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/support-cases` | `backend/app/api/v1/support_cases.py:141` | JWT; support; assigned-case restrictions | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/admin/support-cases` | `backend/app/api/v1/support_cases.py:306` | JWT; support; assigned-case restrictions | {"$ref":"#/components/schemas/Intake"} | {"201":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| PATCH | `/api/v1/admin/support-cases/{case_id}` | `backend/app/api/v1/support_cases.py:336` | JWT; support; assigned-case restrictions | {"$ref":"#/components/schemas/Change"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/me/privacy/exports` | `backend/app/api/v1/privacy_exports.py:94` | JWT; security_admin for admin; owner otherwise | {"$ref":"#/components/schemas/app__api__v1__privacy_exports__ExportRequest"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/me/privacy/exports/{request_id}` | `backend/app/api/v1/privacy_exports.py:110` | JWT; security_admin for admin; owner otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/privacy/exports` | `backend/app/api/v1/privacy_exports.py:121` | JWT; security_admin for admin; owner otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/privacy/exports/{request_id}/decisions` | `backend/app/api/v1/privacy_exports.py:155` | JWT; security_admin for admin; owner otherwise | {"$ref":"#/components/schemas/app__api__v1__privacy_exports__Decision"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/me/privacy/exports/{request_id}/download-grants` | `backend/app/api/v1/privacy_exports.py:186` | JWT; security_admin for admin; owner otherwise | {"$ref":"#/components/schemas/Revision"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| POST | `/api/v1/me/privacy/exports/{request_id}/download` | `backend/app/api/v1/privacy_exports.py:248` | JWT; security_admin for admin; owner otherwise | none / manual source | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | NOT ADMIN |
| GET | `/api/v1/admin/catalog/approved-templates` | `backend/app/api/v1/catalog_templates.py:65` | JWT; operations, security_admin, superadmin | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/TemplateChoices"}}}} | Registered; runtime unverified | SUPPORTING |
| GET | `/api/v1/admin/print-templates` | `backend/app/api/v1/print_templates.py:476` | JWT; read operations/security_admin/superadmin; write and preview operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/TemplateList"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-templates` | `backend/app/api/v1/print_templates.py:502` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Create"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/CreateReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/print-templates/{template_id}` | `backend/app/api/v1/print_templates.py:512` | JWT; read operations/security_admin/superadmin; write and preview operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/TemplateDetail"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions` | `backend/app/api/v1/print_templates.py:540` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/NewRevision"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/RevisionReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| PATCH | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}` | `backend/app/api/v1/print_templates.py:552` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/DraftEditRequest"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/EditReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/preview` | `backend/app/api/v1/print_templates.py:574` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Preview"} | {"200":{"application/pdf":{"schema":{"type":"string","format":"binary"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa` | `backend/app/api/v1/print_templates.py:666` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Reason"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/SubmitReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/publish` | `backend/app/api/v1/print_templates.py:700` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Publish"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/PublishedTemplateReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/print-template-bindings` | `backend/app/api/v1/print_templates.py:729` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Bind"} | {"201":{"application/json":{"schema":{"$ref":"#/components/schemas/TemplateBindingReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/print-template-bindings` | `backend/app/api/v1/print_templates.py:739` | JWT; read operations/security_admin/superadmin; write and preview operations | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/TemplateBindingsPage"}}}} | Registered; runtime unverified | SUPPORTING |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/retire` | `backend/app/api/v1/print_templates.py:774` | JWT; read operations/security_admin/superadmin; write and preview operations | {"$ref":"#/components/schemas/Retire"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/RetiredTemplateReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/me/orders/{order_id}/cancel` | `backend/app/api/v1/cancellations.py:161` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/CancellationRequest"} | {"202":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/orders/{order_id}/cancellation-reconciliations` | `backend/app/api/v1/cancellations.py:169` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/Reconciliation"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/orders/{order_id}/cancellation-decisions` | `backend/app/api/v1/cancellations.py:179` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/app__api__v1__cancellations__Decision"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/tag-pairs/{pair_id}/release-allocation` | `backend/app/api/v1/cancellations.py:185` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/Release"} | {"200":{"application/json":{"schema":{}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/support-cases/{case_id}/financial-review` | `backend/app/api/v1/financial_disputes.py:254` | JWT; finance | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/ReviewProjection"}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/admin/support-cases/{case_id}/financial-decisions` | `backend/app/api/v1/financial_disputes.py:311` | JWT; finance | {"$ref":"#/components/schemas/FinancialDecision"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/DecisionReceipt"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/finance/reconciliation` | `backend/app/api/v1/finance_reconciliation.py:151` | JWT; finance | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__finance_reconciliation__Page"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/finance/reconciliation/counts` | `backend/app/api/v1/finance_reconciliation.py:214` | JWT; finance | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__finance_reconciliation__Counts"}}}} | Registered; runtime unverified | QUARANTINED |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports` | `backend/app/api/v1/manufacturing_exports.py:184` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/app__api__v1__manufacturing_exports__ExportRequest"} | {"202":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__manufacturing_exports__Receipt"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}` | `backend/app/api/v1/manufacturing_exports.py:232` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Metadata"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants` | `backend/app/api/v1/manufacturing_exports.py:243` | Excluded; JWT owner/staff or public activation context per source | {"$ref":"#/components/schemas/GrantRequest"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/GrantReceipt"}}}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download` | `backend/app/api/v1/manufacturing_exports.py:294` | Excluded; JWT owner/staff or public activation context per source | none / manual source | {"200":{}} | Registered; runtime unverified | QR-PAIR EXCLUDED |
| GET | `/api/v1/admin/dashboard/summary` | `backend/app/api/v1/dashboard.py:232` | JWT; all five staff roles; role-filtered projection | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__dashboard__Summary"}}}} | Registered; runtime unverified | QUARANTINED |
| GET | `/api/v1/admin/dashboard/trends` | `backend/app/api/v1/dashboard.py:292` | JWT; all five staff roles; role-filtered projection | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Trends"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/users` | `backend/app/api/v1/staff_directory.py:267` | JWT; security_admin only | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/app__api__v1__staff_directory__Page"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/users/count` | `backend/app/api/v1/staff_directory.py:305` | JWT; security_admin only | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Total"}}}} | Registered; runtime unverified | ELIGIBLE |
| GET | `/api/v1/admin/users/{user_id}` | `backend/app/api/v1/staff_directory.py:319` | JWT; security_admin only | none / manual source | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/Detail"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/users/{user_id}/suspensions` | `backend/app/api/v1/account_lifecycle.py:230` | JWT; security_admin only + case approval + recent authentication | {"$ref":"#/components/schemas/Suspend"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/StateReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/users/{user_id}/restorations` | `backend/app/api/v1/account_lifecycle.py:239` | JWT; security_admin only + case approval + recent authentication | {"$ref":"#/components/schemas/Restore"} | {"200":{"application/json":{"schema":{"$ref":"#/components/schemas/StateReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |
| POST | `/api/v1/admin/users/{user_id}/recovery-escalations` | `backend/app/api/v1/account_lifecycle.py:248` | JWT; security_admin only + case approval + recent authentication | {"$ref":"#/components/schemas/Recovery"} | {"202":{"application/json":{"schema":{"$ref":"#/components/schemas/ReferralReceipt"}}}} | Registered; runtime unverified | ELIGIBLE |

## Per-operation contracts and dependencies

OpenAPI excerpts preserve parameter bounds/defaults, body models and declared errors. Source supplements preserve actual signatures, manual query parsing, response projection and service calls. Calls alone do not establish installed database/provider readiness.

### API-001 — GET `/api/v1/health/live`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/health.py:34`, `live`. Registered and OpenAPI matched; runtime unverified.
- Screen: System Monitoring.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `Liveness, router.get`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Liveness"
          }
        }
      }
    }
  }
}
```

Source contract supplement:

```python
    @router.get("/live", response_model=Liveness, operation_id="API-001")
    def live() -> Liveness:
        return Liveness()
```

### API-002 — GET `/api/v1/health/ready`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/health.py:38`, `ready`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: internal readiness bearer.
- Dependencies/helper calls: `Depends, HTTPException, JSONResponse, Readiness, ReadinessUnavailable, ReadinessUnavailable().model_dump, compare_digest, credentials.credentials.encode, database.is_available, router.get, token.get_secret_value, token.get_secret_value().encode`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Readiness"
          }
        }
      }
    },
    "401": {
      "description": "Probe authorization required"
    },
    "404": {
      "description": "Probe disabled"
    },
    "503": {
      "description": "Database unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ReadinessUnavailable"
          }
        }
      }
    }
  },
  "security": [
    {
      "InternalReadinessProbe": []
    }
  ]
}
```

### staffSecurity — GET `/api/v1/me/staff-security`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account.py:52`, `staff_security`. Registered and OpenAPI matched; runtime unverified.
- Screen: Staff Permissions / bootstrap.
- Auth/permissions: JWT + live session; own current staff roles; AAL1 bootstrap exception.
- Dependencies/helper calls: `AccessError, STAFF_CAPABILITIES.items, StaffSecurity, allowed_roles.intersection, context.session.execute, context.session.execute(text('SELECT role FROM public.staff_roles WHERE user_id=:uid AND revoked_at IS NULL ORDER BY role'), {'uid': context.principal.user_id}).scalars, list, require_verified_account, router.get, sorted, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/StaffSecurity"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/me/staff-security", operation_id="staffSecurity", response_model=StaffSecurity
)
def staff_security(context: Authenticated):
    # AAL1 bootstrap only. Privileged operations retain their require_staff guards.
    require_verified_account(context)
    roles = list(
        context.session.execute(
            text(
                "SELECT role FROM public.staff_roles WHERE user_id=:uid AND revoked_at IS NULL ORDER BY role"
            ),
            {"uid": context.principal.user_id},
        ).scalars()
    )
    roles = [role for role in roles if role in STAFF_ROLES]
    if not roles:
        raise AccessError(403)
    capabilities = sorted(
        capability
        for capability, allowed_roles in STAFF_CAPABILITIES.items()
        if context.mfa_verified and allowed_roles.intersection(roles)
    )
    return StaffSecurity(
        roles=roles, mfa_verified=context.mfa_verified, capabilities=capabilities
    )
```

### API-020 — GET `/api/v1/me`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account.py:147`, `get_me`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: JWT + live session; own current staff roles; AAL1 bootstrap exception.
- Dependencies/helper calls: `router.get, summary`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AccountSummary"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-021 — PATCH `/api/v1/me`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account.py:154`, `edit_me`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: JWT + live session; own current staff roles; AAL1 bootstrap exception.
- Dependencies/helper calls: `Header, ProfileEdit.model_json_schema, ProfileEdit.model_validate_json, ValueError, bytearray, context.session.execute, context.session.execute(text("\n            UPDATE public.user_profiles SET\n              display_name=CASE WHEN :name_set THEN :name ELSE display_name END,\n              preferred_locale=CASE WHEN :locale_set THEN :locale ELSE preferred_locale END,\n              updated_at=greatest(clock_timestamp(),updated_at+interval '1 microsecond')\n            WHERE user_id=:uid AND extract(epoch FROM updated_at)::text=:version\n            RETURNING user_id\n        "), {'uid': uid, 'version': version, 'name_set': 'display_name' in fields, 'name': edit.display_name, 'locale_set': 'preferred_locale' in fields, 'locale': edit.preferred_locale}).scalar_one_or_none, context.session.execute(text('\n            INSERT INTO public.user_profiles(user_id,display_name,preferred_locale)\n            VALUES(:uid,:name,:locale) ON CONFLICT(user_id) DO NOTHING RETURNING user_id\n        '), {'uid': uid, 'name': edit.display_name, 'locale': edit.preferred_locale or 'en'}).scalar_one_or_none, failure, len, raw.extend, re.fullmatch, request.headers.get, request.headers.get('content-type', '').split, request.stream, router.patch, summary, text`.

```json
{
  "parameters": [
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "additionalProperties": false,
          "properties": {
            "display_name": {
              "anyOf": [
                {
                  "maxLength": 120,
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Display Name"
            },
            "preferred_locale": {
              "anyOf": [
                {
                  "enum": [
                    "en",
                    "ur"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Preferred Locale"
            }
          },
          "title": "ProfileEdit",
          "type": "object"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AccountSummary"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-022 — GET `/api/v1/me/privacy-consents`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account.py:257`, `privacy_consents`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text("\n        SELECT id,target_id,action,occurred_at,safe_details->>'reason_code' AS consent_version,\n               safe_details->>'to_status' AS active_state\n        FROM public.audit_events WHERE actor_user_id=:uid AND target_type='qr'\n          AND action IN ('profile.ice.updated','profile.ice_contact.updated','profile.ice_contact.removed','profile.whatsapp.updated')\n        ORDER BY occurred_at DESC,id DESC LIMIT 101\n    "), {'uid': context.principal.user_id}).mappings, context.session.execute(text("\n        SELECT id,target_id,action,occurred_at,safe_details->>'reason_code' AS consent_version,\n               safe_details->>'to_status' AS active_state\n        FROM public.audit_events WHERE actor_user_id=:uid AND target_type='qr'\n          AND action IN ('profile.ice.updated','profile.ice_contact.updated','profile.ice_contact.removed','profile.whatsapp.updated')\n        ORDER BY occurred_at DESC,id DESC LIMIT 101\n    "), {'uid': context.principal.user_id}).mappings().all, len, router.get, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-023 — POST `/api/v1/me/account-deletion-requests`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account.py:293`, `request_account_deletion`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `DeletionRequest.model_json_schema, DeletionRequest.model_validate_json, bytearray, context.session.execute, context.session.execute(text("\n        INSERT INTO public.support_cases(opened_by_user_id,case_type,description_ciphertext,description_key_version)\n        VALUES(:uid,'privacy',:cipher,:version) RETURNING id\n    "), {'uid': uid, 'cipher': cipher, 'version': version}).scalar_one, context.session.execute(text("\n        SELECT c.id,c.status FROM public.support_cases c JOIN public.audit_events a\n          ON a.target_id=c.id AND a.target_type='support_case'\n        WHERE a.actor_user_id=:uid AND a.action='account.deletion.requested'\n          AND c.opened_by_user_id=:uid AND c.status IN ('open','investigating')\n        ORDER BY c.created_at DESC LIMIT 1\n    "), {'uid': uid}).mappings, context.session.execute(text("\n        SELECT c.id,c.status FROM public.support_cases c JOIN public.audit_events a\n          ON a.target_id=c.id AND a.target_type='support_case'\n        WHERE a.actor_user_id=:uid AND a.action='account.deletion.requested'\n          AND c.opened_by_user_id=:uid AND c.status IN ('open','investigating')\n        ORDER BY c.created_at DESC LIMIT 1\n    "), {'uid': uid}).mappings().one_or_none, datetime.now, datetime.now(UTC).timestamp, encrypt, failure, len, raw.extend, request.headers.get, request.headers.get('content-type', '').split, request.stream, router.post, text`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "properties": {
            "confirm": {
              "type": "boolean",
              "const": true,
              "title": "Confirm"
            },
            "reason": {
              "anyOf": [
                {
                  "type": "string",
                  "maxLength": 1000
                },
                {
                  "type": "null"
                }
              ],
              "title": "Reason"
            }
          },
          "additionalProperties": false,
          "type": "object",
          "required": [
            "confirm"
          ],
          "title": "DeletionRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-100 — GET `/api/v1/admin/audit-events`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/audit_events.py:80`, `search`. Registered and OpenAPI matched; runtime unverified.
- Screen: Audit.
- Auth/permissions: JWT + live session; security_admin only.
- Dependencies/helper calls: `any, bounds, context.session.execute, context.session.execute(text('SELECT id,occurred_at,actor_kind,actor_user_id,action,target_type,target_id\n      FROM public.audit_events WHERE occurred_at>=:start AND occurred_at<:end\n      AND (CAST(:actor AS uuid) IS NULL OR actor_user_id=:actor)\n      AND (CAST(:target AS uuid) IS NULL OR target_id=:target)\n      AND (CAST(:kind AS text) IS NULL OR target_type=:kind)\n      AND (CAST(:action AS text) IS NULL OR action=:action)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (occurred_at,id)<(:stamp,:ident))\n      ORDER BY occurred_at DESC,id DESC LIMIT :lim'), {'start': start, 'end': end, 'actor': actor_id, 'target': target_id, 'kind': target_type, 'action': action, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text('SELECT id,occurred_at,actor_kind,actor_user_id,action,target_type,target_id\n      FROM public.audit_events WHERE occurred_at>=:start AND occurred_at<:end\n      AND (CAST(:actor AS uuid) IS NULL OR actor_user_id=:actor)\n      AND (CAST(:target AS uuid) IS NULL OR target_id=:target)\n      AND (CAST(:kind AS text) IS NULL OR target_type=:kind)\n      AND (CAST(:action AS text) IS NULL OR action=:action)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (occurred_at,id)<(:stamp,:ident))\n      ORDER BY occurred_at DESC,id DESC LIMIT :lim'), {'start': start, 'end': end, 'actor': actor_id, 'target': target_id, 'kind': target_type, 'action': action, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, datetime.now, dict, fail, len, page_cursor, paged, recent, request.query_params.getlist, require_staff, router.get, row.pop, text, timedelta`.

```json
{
  "parameters": [
    {
      "name": "actor_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Actor Id"
      }
    },
    {
      "name": "target_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Target Id"
      }
    },
    {
      "name": "target_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "user_profile",
              "qr",
              "tag_pair",
              "order",
              "shipment",
              "payment_attempt",
              "payment_evidence",
              "print_artifact",
              "print_job",
              "support_case",
              "privacy_export",
              "finance_sheet_sync",
              "audit_search"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Target Type"
      }
    },
    {
      "name": "action",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Action"
      }
    },
    {
      "name": "start",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "Start"
      }
    },
    {
      "name": "end",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "End"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__audit_events__Page"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/audit-events", operation_id="API-100", response_model=Page)
def search(
    context: Authenticated,
    request: Request,
    response: Response,
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
    target_type: Target | None = None,
    action: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    cursor: str | None = None,
    limit: int = 20,
):
    require_staff(context, "security_admin")
    recent(context)
    allowed = {
        "actor_id",
        "target_id",
        "target_type",
        "action",
        "start",
        "end",
        "cursor",
        "limit",
    }
    if any(
        k not in allowed or len(request.query_params.getlist(k)) != 1
        for k in request.query_params
    ):
        fail(422, "INVALID_QUERY")
    bounds(limit)
    if action is not None and action not in ACTIONS:
        fail(422, "INVALID_ACTION")
    now = datetime.now(UTC)
    end = end or now
    start = start or end - timedelta(days=7)
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or not timedelta(0) < end - start <= timedelta(days=31)
    ):
        fail(422, "INVALID_TIME_RANGE")
    stamp, ident = page_cursor(cursor)
    # Existing indexes cover actor/target lookup; broad time searches must also
    # fail within a small budget rather than sorting an unlimited history.
    context.session.execute(text("SET LOCAL statement_timeout='3000ms'"))
    # Cursor is navigation, never authority: all filters and role checks reapply.
    rows = (
        context.session.execute(
            text("""SELECT id,occurred_at,actor_kind,actor_user_id,action,target_type,target_id
      FROM public.audit_events WHERE occurred_at>=:start AND occurred_at<:end
      AND (CAST(:actor AS uuid) IS NULL OR actor_user_id=:actor)
      AND (CAST(:target AS uuid) IS NULL OR target_id=:target)
      AND (CAST(:kind AS text) IS NULL OR target_type=:kind)
      AND (CAST(:action AS text) IS NULL OR action=:action)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (occurred_at,id)<(:stamp,:ident))
      ORDER BY occurred_at DESC,id DESC LIMIT :lim"""),
            {
                "start": start,
                "end": end,
                "actor": actor_id,
                "target": target_id,
                "kind": target_type,
                "action": action,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    items = [dict(r, created_at=r["occurred_at"]) for r in rows]
    page = paged(items, limit)
    for row in page["items"]:
        row.pop("created_at")
        row["action"] = (
            row["action"] if row["action"] in ACTIONS else "restricted_event"
        )
        row["target_type"] = (
            row["target_type"] if row["target_type"] in TARGETS else "restricted"
        )
    # No filters/private strings enter the read audit. Append-only source intact.
    context.session.execute(
        text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type)
      VALUES(:uid,'staff','audit.search','audit_search')"""),
        {"uid": context.principal.user_id},
    )
    response.headers["Cache-Control"] = "private, no-store"
    return page
```

### API-003 — GET `/api/v1/public/products`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:160`, `list_products`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `Query, enumerate, fail, next, public_catalog, public_router.get, str`.

```json
{
  "parameters": [
    {
      "name": "category",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Category"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 100,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": true
            },
            "title": "Response Api-003"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

Source contract supplement:

```python
@public_router.get(
    "/public/products", operation_id="API-003", response_model=list[dict]
)
def list_products(
    request: Request,
    response: Response,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    cursor: UUID | None = None,
):
    items = public_catalog(request, response)
    if category:
        items = [p for p in items if p["category"]["slug"] == category]
    if cursor:
        index = next(
            (i for i, p in enumerate(items) if p["product_id"] == str(cursor)), None
        )
        if index is None:
            fail(400, "INVALID_CURSOR")
        items = items[index + 1 :]
    return items[:limit]
```

### API-004 — GET `/api/v1/public/products/{sku}`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:183`, `get_product`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, len, public_catalog, public_router.get, re.fullmatch`.

```json
{
  "parameters": [
    {
      "name": "sku",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Sku"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "type": "object",
            "additionalProperties": true,
            "title": "Response Api-004"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

Source contract supplement:

```python
@public_router.get(
    "/public/products/{sku}", operation_id="API-004", response_model=dict
)
def get_product(sku: str, request: Request, response: Response):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,59}", sku):
        raise AccessError(404)
    items = public_catalog(request, response, sku)
    if len(items) != 1:
        raise AccessError(404)
    return items[0]
```

### API-201 — GET `/api/v1/public/catalog/featured`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:195`, `featured`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `public_catalog, public_router.get`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  }
}
```

Source contract supplement:

```python
@public_router.get("/public/catalog/featured", operation_id="API-201")
def featured(request: Request, response: Response):
    return {
        "items": [p for p in public_catalog(request, response) if p["featured"]][:100],
        "next_cursor": None,
    }
```

### API-200 — GET `/api/v1/public/catalog/categories`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:203`, `categories`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `list, public_catalog, public_router.get, {p['category']['id']: p['category'] for p in items}.values`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  }
}
```

Source contract supplement:

```python
@public_router.get("/public/catalog/categories", operation_id="API-200")
def categories(request: Request, response: Response):
    items = public_catalog(request, response)
    return {"items": list({p["category"]["id"]: p["category"] for p in items}.values())}
```

### API-202 — GET `/api/v1/public/catalog/products/{product_id}/variants`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:209`, `variants`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, public_catalog, public_router.get, str`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

Source contract supplement:

```python
@public_router.get(
    "/public/catalog/products/{product_id}/variants", operation_id="API-202"
)
def variants(product_id: UUID, request: Request, response: Response):
    for p in public_catalog(request, response):
        if p["product_id"] == str(product_id):
            return {"items": p["variants"], "catalog_version": p["catalog_version"]}
    raise AccessError(404)
```

### API-203 — POST `/api/v1/me/checkout/quotes`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy quote/confirm inspects pair capacity and can reserve order_pair_units; never used as catalog validation/setup.
- Source: `backend/app/api/v1/checkout.py:280`, `create_quote`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `address.model_dump_json, body.model_dump, catalog_lines, context.session.execute, context.session.execute(text("INSERT INTO public.checkout_quotes(id,customer_user_id,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,expires_at)\n   VALUES(:id,:actor,CAST(:payload AS jsonb),:cipher,:version,:subtotal,:shipping,:tax,:total,clock_timestamp()+interval '15 minutes') RETURNING expires_at"), {'id': qid, 'actor': context.principal.user_id, 'payload': json.dumps(payload), 'cipher': cipher, 'version': version, 'subtotal': subtotal, 'shipping': settings.checkout_shipping_pkr, 'tax': settings.checkout_tax_pkr, 'total': total}).scalar_one, context.session.execute(text('SELECT public.sr_checkout_capacity()')).scalar_one, encrypt, fail, guard, json.dumps, line.items, record, resolve, router.post, text, uuid4`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/QuoteRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-204 — POST `/api/v1/me/checkout/quotes/{quote_id}/confirm`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy quote/confirm inspects pair capacity and can reserve order_pair_units; never used as catalog validation/setup.
- Source: `backend/app/api/v1/checkout.py:367`, `confirm_quote`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, Address.model_validate_json, CartLine, Decimal, any, body.model_dump, catalog_lines, decrypt, encrypt, fail, freeze_use, getattr, line.get, next, order.hex[:12].upper, payload.get, recheck_quote, record, router.post, session.execute, session.execute(text('INSERT INTO public.order_item_qr_uses(order_item_id,qr_code_id,pair_unit_id,use_kind,tag_type_snapshot,copies)\n     VALUES(:item,:qr,:unit,:kind,:tag,:copies) RETURNING id'), {'item': item, 'qr': qr, 'unit': reserved['unit_id'] if use['mode'] == 'new_pair' else None, 'kind': use['mode'], 'tag': use['tag_type'], 'copies': use['copies']}).scalar_one, session.execute(text('SELECT * FROM public.checkout_quotes WHERE id=:id AND customer_user_id=:actor FOR UPDATE'), {'id': quote_id, 'actor': actor}).mappings, session.execute(text('SELECT * FROM public.checkout_quotes WHERE id=:id AND customer_user_id=:actor FOR UPDATE'), {'id': quote_id, 'actor': actor}).mappings().one_or_none, session.execute(text('SELECT clock_timestamp()')).scalar_one, session.execute(text('SELECT public.sr_checkout_reserve(:quote,:order,:unit,:minutes)'), {'quote': quote_id, 'order': order, 'unit': uuid4(), 'minutes': payload['reservation_minutes']}).scalar_one, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "quote_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Quote Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ConfirmRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-060 — POST `/api/v1/me/orders`

- Eligibility: **BLOCKED**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/checkout.py:566`, `legacy_order`. Registered and OpenAPI matched; runtime unverified.
- Screen: No direct admin screen.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `fail, require_verified_account, router.post`.

```json
{
  "responses": {
    "409": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post("/me/orders", operation_id="API-060", status_code=409)
def legacy_order(context: Authenticated):
    """Legacy callers must upgrade; never run a competing order writer."""
    require_verified_account(context)
    fail(409, "QUOTE_REQUIRED")
```

### item-checkout-quote — POST `/api/v1/me/checkout/item-quotes`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/item_checkout.py:168`, `create_quote`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `address.model_dump_json, admission, body.model_dump, context.session.execute, context.session.execute(text("INSERT INTO public.checkout_quotes\n            (id,customer_user_id,commerce_model,payload,address_ciphertext,address_key_version,subtotal_pkr,shipping_pkr,tax_pkr,total_pkr,expires_at)\n            VALUES(:id,:actor,'single_qr',CAST(:payload AS jsonb),:cipher,:version,:subtotal,:shipping,:tax,:total,clock_timestamp()+interval '15 minutes') RETURNING expires_at"), {'id': qid, 'actor': context.principal.user_id, 'payload': json.dumps(payload), 'cipher': cipher, 'version': version, 'subtotal': subtotal, 'shipping': settings.checkout_shipping_pkr, 'tax': settings.checkout_tax_pkr, 'total': total}).scalar_one, context.session.execute(text('SELECT public.sr_checkout_payment_instructions()')).scalar_one, encrypt, fail, guard, json.dumps, len, public_items, record, router.post, saved_address, snapshots, text, uuid4`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ItemQuoteRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### item-checkout-confirm — POST `/api/v1/me/checkout/item-quotes/{quote_id}/confirm`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/item_checkout.py:279`, `confirm_quote`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `AccessError, Address.model_validate_json, Decimal, admission, body.model_dump, decrypt, encrypt, fail, getattr, json.dumps, len, oid.hex[:12].upper, record, revalidate, router.post, session.execute, session.execute(text('SELECT * FROM public.checkout_quotes WHERE id=:id AND customer_user_id=:actor FOR UPDATE'), {'id': quote_id, 'actor': actor}).mappings, session.execute(text('SELECT * FROM public.checkout_quotes WHERE id=:id AND customer_user_id=:actor FOR UPDATE'), {'id': quote_id, 'actor': actor}).mappings().one_or_none, session.execute(text('SELECT clock_timestamp()')).scalar_one, session.execute(text('SELECT public.sr_checkout_payment_instructions()')).scalar_one, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "quote_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Quote Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ConfirmRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-068 — GET `/api/v1/me/shipping-addresses`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/shipping_addresses.py:216`, `listing`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `book, context.session.execute, context.session.execute(text('SELECT * FROM public.shipping_addresses WHERE customer_user_id=:actor AND is_saved ORDER BY created_at,id LIMIT 100'), {'actor': context.principal.user_id}).mappings, guard, projection, router.get, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-067 — POST `/api/v1/me/shipping-addresses`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/shipping_addresses.py:232`, `create`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `advance, audit, book, cipher_params, context.session.execute, context.session.execute(text('SELECT count(*) FROM public.shipping_addresses WHERE customer_user_id=:actor AND is_saved'), {'actor': context.principal.user_id}).scalar_one, fail, guard, owned, projection, router.post, text, uuid4`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/CreateAddress"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-069 — PATCH `/api/v1/me/shipping-addresses/{address_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/shipping_addresses.py:270`, `update`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `advance, audit, book, cipher_params, context.session.execute, dict, fail, guard, mutable, owned, projection, router.patch, text`.

```json
{
  "parameters": [
    {
      "name": "address_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Address Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/UpdateAddress"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-070 — DELETE `/api/v1/me/shipping-addresses/{address_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/shipping_addresses.py:315`, `remove`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `Query, Response, advance, audit, book, context.session.execute, fail, guard, mutable, owned, router.delete, text`.

```json
{
  "parameters": [
    {
      "name": "address_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Address Id"
      }
    },
    {
      "name": "expected_version",
      "in": "query",
      "required": true,
      "schema": {
        "type": "integer",
        "maximum": 2147483646,
        "minimum": 1,
        "title": "Expected Version"
      }
    },
    {
      "name": "expected_book_version",
      "in": "query",
      "required": true,
      "schema": {
        "type": "integer",
        "maximum": 2147483646,
        "minimum": 0,
        "title": "Expected Book Version"
      }
    }
  ],
  "responses": {
    "204": {
      "description": "Successful Response"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-220 — GET `/api/v1/admin/products`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:491`, `admin_products`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `Query, admin_router.get, context.session.execute, context.session.execute(text('SELECT * FROM public.products WHERE (CAST(:cursor AS uuid) IS NULL OR id>:cursor) ORDER BY id LIMIT :limit'), {'cursor': cursor, 'limit': limit + 1}).mappings, context.session.execute(text('SELECT * FROM public.products WHERE (CAST(:cursor AS uuid) IS NULL OR id>:cursor) ORDER BY id LIMIT :limit'), {'cursor': cursor, 'limit': limit + 1}).mappings().all, context.session.execute(text(f'SELECT * FROM public.{table} WHERE product_id=:id ORDER BY id'), {'id': row['id']}).mappings, dict, guard, items.append, jsonable_encoder, len, str, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 100,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.get("/admin/products", operation_id="API-220")
def admin_products(
    context: Authenticated,
    limit: int = Query(100, ge=1, le=100),
    cursor: UUID | None = None,
):
    guard(context)
    rows = (
        context.session.execute(
            text(
                "SELECT * FROM public.products WHERE (CAST(:cursor AS uuid) IS NULL OR id>:cursor) ORDER BY id LIMIT :limit"
            ),
            {"cursor": cursor, "limit": limit + 1},
        )
        .mappings()
        .all()
    )
    items = []
    for row in rows[:limit]:
        item = dict(row)
        for key, table in (
            ("variants", "product_variants"),
            ("images", "product_images"),
        ):
            item[key] = [
                dict(r)
                for r in context.session.execute(
                    text(
                        f"SELECT * FROM public.{table} WHERE product_id=:id ORDER BY id"
                    ),
                    {"id": row["id"]},
                ).mappings()
            ]
        # Variant prices are legacy metadata; expose the product price for every size.
        for variant in item["variants"]:
            variant["unit_price"] = item["price_per_copy"]
        items.append(jsonable_encoder(item, custom_encoder={Decimal: str}))
    return {
        "items": items,
        "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None,
    }
```

### catalog-admin-product-detail — GET `/api/v1/admin/products/{product_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:534`, `admin_product_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `AccessError, admin_router.get, context.session.execute, context.session.execute(text('SELECT * FROM public.products WHERE id=:id'), {'id': product_id}).mappings, context.session.execute(text('SELECT * FROM public.products WHERE id=:id'), {'id': product_id}).mappings().one_or_none, context.session.execute(text(f'SELECT * FROM public.{table} WHERE product_id=:id ORDER BY id'), {'id': product_id}).mappings, dict, guard, jsonable_encoder, text`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.get("/admin/products/{product_id}", operation_id="catalog-admin-product-detail")
def admin_product_detail(product_id: UUID, context: Authenticated):
    guard(context)
    row = context.session.execute(text("SELECT * FROM public.products WHERE id=:id"), {"id": product_id}).mappings().one_or_none()
    if row is None:
        raise AccessError(404)
    item = dict(row)
    for key, table in (("variants", "product_variants"), ("images", "product_images")):
        item[key] = [dict(r) for r in context.session.execute(text(f"SELECT * FROM public.{table} WHERE product_id=:id ORDER BY id"), {"id": product_id}).mappings()]
    for variant in item["variants"]:
        variant["unit_price"] = item["price_per_copy"]
    return jsonable_encoder(item, custom_encoder={Decimal: str})
```

### API-227 — GET `/api/v1/admin/catalog/categories`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:548`, `admin_categories`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `admin_router.get, context.session.execute, context.session.execute(text('SELECT * FROM public.product_categories ORDER BY sort_order,id LIMIT 100')).mappings, dict, guard, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.get("/admin/catalog/categories", operation_id="API-227")
def admin_categories(context: Authenticated):
    guard(context)
    return {
        "items": [
            dict(r)
            for r in context.session.execute(
                text(
                    "SELECT * FROM public.product_categories ORDER BY sort_order,id LIMIT 100"
                )
            ).mappings()
        ]
    }
```

### API-228 — POST `/api/v1/admin/catalog/categories`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:563`, `create_category`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `admin_router.post, body.model_dump, insert, mutation`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/CategoryRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.post("/admin/catalog/categories", operation_id="API-228", status_code=201)
def create_category(body: CategoryRequest, request: Request, context: Authenticated):
    return mutation(
        context,
        request,
        "catalog.category.create",
        body.model_dump(),
        lambda: (insert(context, "product_categories", body.model_dump()), None),
    )
```

### API-229 — PATCH `/api/v1/admin/catalog/categories/{category_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:574`, `edit_category`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `Header, admin_router.patch, body.model_dump, jsonable_encoder, lock, mutation, update`.

```json
{
  "parameters": [
    {
      "name": "category_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Category Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/CategoryRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.patch("/admin/catalog/categories/{category_id}", operation_id="API-229")
def edit_category(
    category_id: UUID,
    body: CategoryRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        old = lock(context, "product_categories", category_id, if_match)
        return update(
            context, "product_categories", category_id, body.model_dump()
        ), jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.category.edit",
        {**body.model_dump(), "id": category_id, "version": if_match},
        work,
    )
```

### API-221 — POST `/api/v1/admin/products`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:597`, `create_product`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `admin_router.post, body.model_dump, fail, insert, mutation`.

```json
{
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/CreateProductRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.post("/admin/products", operation_id="API-221", status_code=201)
def create_product(body: CreateProductRequest, request: Request, context: Authenticated):
    def work():
        if body.lifecycle_status != "draft":
            fail(422, "CREATE_AS_DRAFT")
        if body.qr_type is None:
            fail(422, "QR_TYPE_REQUIRED")
        return insert(context, "products", {**body.model_dump(), "commerce_model": "single_qr", "allows_new_pair": False}), None

    return mutation(context, request, "catalog.product.create", body.model_dump(), work)
```

### API-222 — PATCH `/api/v1/admin/products/{product_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:609`, `edit_product`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `Header, admin_router.patch, body.model_dump, fail, jsonable_encoder, lock, mutation, old.get, publishable, update`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ProductRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.patch("/admin/products/{product_id}", operation_id="API-222")
def edit_product(
    product_id: UUID,
    body: ProductRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        old = lock(context, "products", product_id, if_match)
        if (
            old["lifecycle_status"] == "archived"
            and body.lifecycle_status != "archived"
        ):
            fail(422, "ARCHIVED_PRODUCT")
        if old.get("commerce_model", "legacy_pair") == "legacy_pair" and body.qr_type != old.get("qr_type"):
            fail(409, "LEGACY_PRODUCT_TYPE")
        if old.get("commerce_model") == "single_qr" and body.qr_type is None:
            fail(422, "QR_TYPE_REQUIRED")
        row = update(context, "products", product_id, body.model_dump())
        publishable(context, request, row)
        return row, jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.product.edit",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )
```

### API-223 — POST `/api/v1/admin/products/{product_id}/variants`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:641`, `create_variant`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `Header, admin_router.post, body.model_dump, fail, insert, lock, mutation, publishable, update`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/VariantRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.post(
    "/admin/products/{product_id}/variants", operation_id="API-223", status_code=201
)
def create_variant(
    product_id: UUID,
    body: VariantRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        parent = lock(context, "products", product_id, if_match)
        if parent["price_per_copy"] is None:
            fail(422, "PRODUCT_PRICE_REQUIRED")
        row = insert(
            context, "product_variants", {**body.model_dump(), "unit_price": parent["price_per_copy"], "product_id": product_id}
        )
        update(context, "products", product_id, {"name": parent["name"]})
        publishable(context, request, parent)
        return row, None

    return mutation(
        context,
        request,
        "catalog.variant.create",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )
```

### API-224 — PATCH `/api/v1/admin/product-variants/{variant_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:671`, `edit_variant`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `AccessError, Header, admin_router.patch, body.model_dump, context.session.execute, context.session.execute(text('SELECT * FROM public.products WHERE id=:id FOR UPDATE'), {'id': pid}).mappings, context.session.execute(text('SELECT * FROM public.products WHERE id=:id FOR UPDATE'), {'id': pid}).mappings().one, context.session.execute(text('SELECT product_id FROM public.product_variants WHERE id=:id'), {'id': variant_id}).scalar_one_or_none, dict, fail, jsonable_encoder, lock, mutation, publishable, text, update`.

```json
{
  "parameters": [
    {
      "name": "variant_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Variant Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/VariantRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.patch("/admin/product-variants/{variant_id}", operation_id="API-224")
def edit_variant(
    variant_id: UUID,
    body: VariantRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        pid = context.session.execute(
            text("SELECT product_id FROM public.product_variants WHERE id=:id"),
            {"id": variant_id},
        ).scalar_one_or_none()
        if pid is None:
            raise AccessError(404)
        parent = dict(
            context.session.execute(
                text("SELECT * FROM public.products WHERE id=:id FOR UPDATE"),
                {"id": pid},
            )
            .mappings()
            .one()
        )
        old = lock(context, "product_variants", variant_id, if_match)
        if parent["price_per_copy"] is None:
            fail(422, "PRODUCT_PRICE_REQUIRED")
        row = update(context, "product_variants", variant_id, {**body.model_dump(), "unit_price": parent["price_per_copy"]})
        update(context, "products", pid, {"name": parent["name"]})
        publishable(context, request, parent)
        return row, jsonable_encoder(old)

    return mutation(
        context,
        request,
        "catalog.variant.edit",
        {**body.model_dump(), "id": variant_id, "version": if_match},
        work,
    )
```

### API-225 — POST `/api/v1/admin/products/{product_id}/images`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:711`, `create_image`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `Header, admin_router.post, body.model_dump, context.session.execute, insert, lock, mutation, text, update, upload_authorization, verified_asset`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    },
    {
      "name": "authorize_upload",
      "in": "query",
      "required": false,
      "schema": {
        "type": "boolean",
        "default": false,
        "title": "Authorize Upload"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ImageRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.post(
    "/admin/products/{product_id}/images", operation_id="API-225", status_code=201
)
def create_image(
    product_id: UUID,
    body: ImageRequest,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
    authorize_upload: bool = False,
):
    def work():
        if authorize_upload:
            parent = lock(context, "products", product_id, if_match)
            return upload_authorization(
                request.app.state.settings, product_id, parent["catalog_version"]
            ), None
        # Replay is resolved first; provider HTTP holds no catalog row locks.
        url = verified_asset(request.app.state.settings, body.cloudinary_public_id)
        parent = lock(context, "products", product_id, if_match)
        if body.is_primary:
            context.session.execute(
                text(
                    "UPDATE public.product_images SET is_primary=false WHERE product_id=:id"
                ),
                {"id": product_id},
            )
        row = insert(
            context,
            "product_images",
            {**body.model_dump(), "product_id": product_id, "verified_public_url": url},
        )
        update(context, "products", product_id, {"name": parent["name"]})
        return row, None

    return mutation(
        context,
        request,
        "catalog.image.authorize" if authorize_upload else "catalog.image.create",
        {**body.model_dump(), "id": product_id, "version": if_match},
        work,
    )
```

### catalog-image-metadata — PATCH `/api/v1/admin/products/{product_id}/images/{image_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:761`, `edit_image`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `AccessError, Header, admin_router.patch, body.model_dump, context.session.execute, context.session.execute(text('SELECT * FROM public.product_images WHERE id=:id AND product_id=:pid FOR UPDATE'), {'id': image_id, 'pid': product_id}).mappings, context.session.execute(text('SELECT * FROM public.product_images WHERE id=:id AND product_id=:pid FOR UPDATE'), {'id': image_id, 'pid': product_id}).mappings().one_or_none, context.session.execute(text('UPDATE public.product_images SET alt_text=:alt_text,sort_order=:sort_order,is_primary=:is_primary WHERE id=:id AND product_id=:pid RETURNING *'), {**body.model_dump(), 'id': image_id, 'pid': product_id}).mappings, context.session.execute(text('UPDATE public.product_images SET alt_text=:alt_text,sort_order=:sort_order,is_primary=:is_primary WHERE id=:id AND product_id=:pid RETURNING *'), {**body.model_dump(), 'id': image_id, 'pid': product_id}).mappings().one, dict, lock, mutation, publishable, text, update`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    },
    {
      "name": "image_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Image Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ImageMetadataRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.patch("/admin/products/{product_id}/images/{image_id}", operation_id="catalog-image-metadata")
def edit_image(product_id: UUID, image_id: UUID, body: ImageMetadataRequest, request: Request,
               context: Authenticated, if_match: Annotated[str | None, Header()] = None):
    def work():
        parent = lock(context, "products", product_id, if_match)
        old = context.session.execute(text("SELECT * FROM public.product_images WHERE id=:id AND product_id=:pid FOR UPDATE"), {"id": image_id, "pid": product_id}).mappings().one_or_none()
        if old is None:
            raise AccessError(404)
        if body.is_primary:
            context.session.execute(text("UPDATE public.product_images SET is_primary=false WHERE product_id=:pid"), {"pid": product_id})
        row = context.session.execute(text("UPDATE public.product_images SET alt_text=:alt_text,sort_order=:sort_order,is_primary=:is_primary WHERE id=:id AND product_id=:pid RETURNING *"), {**body.model_dump(), "id": image_id, "pid": product_id}).mappings().one()
        update(context, "products", product_id, {"name": parent["name"]})
        publishable(context, request, parent)
        return dict(row), dict(old)
    return mutation(context, request, "catalog.image.edit", {**body.model_dump(), "product": product_id, "id": image_id, "version": if_match}, work)
```

### API-226 — DELETE `/api/v1/admin/products/{product_id}/images/{image_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog.py:778`, `unlink_image`. Registered and OpenAPI matched; runtime unverified.
- Screen: Products List / Add / Edit.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `AccessError, Header, admin_router.delete, context.session.execute, context.session.execute(text('DELETE FROM public.product_images WHERE id=:id AND product_id=:pid RETURNING *'), {'id': image_id, 'pid': product_id}).mappings, context.session.execute(text('DELETE FROM public.product_images WHERE id=:id AND product_id=:pid RETURNING *'), {'id': image_id, 'pid': product_id}).mappings().one_or_none, dict, lock, mutation, publishable, text, update`.

```json
{
  "parameters": [
    {
      "name": "product_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Product Id"
      }
    },
    {
      "name": "image_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Image Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@admin_router.delete(
    "/admin/products/{product_id}/images/{image_id}", operation_id="API-226"
)
def unlink_image(
    product_id: UUID,
    image_id: UUID,
    request: Request,
    context: Authenticated,
    if_match: Annotated[str | None, Header()] = None,
):
    def work():
        parent = lock(context, "products", product_id, if_match)
        row = (
            context.session.execute(
                text(
                    "DELETE FROM public.product_images WHERE id=:id AND product_id=:pid RETURNING *"
                ),
                {"id": image_id, "pid": product_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AccessError(404)
        update(context, "products", product_id, {"name": parent["name"]})
        publishable(context, request, parent)
        return dict(row), dict(row)

    return mutation(
        context,
        request,
        "catalog.image.unlink",
        {"id": image_id, "product": product_id, "version": if_match},
        work,
    )
```

### API-090 — POST `/api/v1/admin/qr-batches`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy batch-generation handler creates paired inventory/credential material. New generation integration prohibited.
- Source: `backend/app/api/v1/inventory.py:119`, `create_qr_batch`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, Header, _failure, _response, activation_verifier, body.model_dump, bytes, context.session.execute, context.session.execute(text("\n                SELECT target_id FROM public.audit_events\n                WHERE actor_user_id=:actor AND actor_kind='staff'\n                  AND action='inventory.qr_batch.generated' AND request_id=:request_id\n                ORDER BY occurred_at DESC LIMIT 1\n            "), {'actor': actor_id, 'request_id': key_hash}).scalar_one_or_none, context.session.execute(text('SELECT 1 FROM public.qr_batches WHERE batch_code=:code'), {'code': body.batch_label}).scalar_one_or_none, context.session.execute(text('\n            SELECT request_hash,state,response_status,response_body_ciphertext,response_key_version\n            FROM public.idempotency_records\n            WHERE actor_scope=:scope AND operation=:operation AND idempotency_key=:key\n            FOR UPDATE\n        '), {'scope': actor_scope, 'operation': OPERATION, 'key': idempotency_key}).mappings, context.session.execute(text('\n            SELECT request_hash,state,response_status,response_body_ciphertext,response_key_version\n            FROM public.idempotency_records\n            WHERE actor_scope=:scope AND operation=:operation AND idempotency_key=:key\n            FOR UPDATE\n        '), {'scope': actor_scope, 'operation': OPERATION, 'key': idempotency_key}).mappings().one_or_none, create_sealed_insert, credential_rows.append, hashlib.sha256, hashlib.sha256(idempotency_key.encode('ascii')).hexdigest, hashlib.sha256(json.dumps(request_model, sort_keys=True, separators=(',', ':')).encode()).hexdigest, hashlib.sha256(settings.print_recipient_public_key.get_secret_value().encode('ascii')).hexdigest, idempotency_key.encode, json.dumps, json.dumps(request_model, sort_keys=True, separators=(',', ':')).encode, json.dumps(sealed_insert, sort_keys=True, separators=(',', ':')).encode, json.loads, len, load_recipient_public_key, manifest_checksum, manifest_pairs.append, new_activation_secret, new_public_token, pair_rows.append, qr_rows.append, range, re.fullmatch, register_source, require_staff, router.post, settings.print_recipient_public_key.get_secret_value, settings.print_recipient_public_key.get_secret_value().encode, str, tags.append, text, uuid.uuid4, verifier_key`.

```json
{
  "parameters": [
    {
      "name": "Idempotency-Key",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Idempotency-Key"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/BatchRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/BatchResponse"
          }
        }
      }
    },
    "400": {
      "description": "Invalid request"
    },
    "403": {
      "description": "Staff/MFA required"
    },
    "409": {
      "description": "Conflict"
    },
    "503": {
      "description": "Secure generation unavailable"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-084 — GET `/api/v1/admin/tag-pairs`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited.
- Source: `backend/app/api/v1/inventory_queries.py:171`, `list_pairs`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Query, any, bounds, context.session.execute, context.session.execute(text(f'WITH selected AS (\n      SELECT p.* FROM public.tag_pairs p WHERE\n      (CAST(:ref AS text) IS NULL OR p.pair_reference=:ref)\n      AND (CAST(:batch AS uuid) IS NULL OR p.batch_id=:batch)\n      AND (CAST(:inventory AS text) IS NULL OR p.inventory_status=:inventory)\n      AND (CAST(:ownership AS text) IS NULL OR p.ownership_status=:ownership)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (p.created_at,p.id)<(:stamp,:ident))\n      ORDER BY p.created_at DESC,p.id DESC LIMIT :lim)\n      SELECT {PAIR_FIELDS} FROM selected p ORDER BY p.created_at DESC,p.id DESC'), {'ref': pair_reference, 'batch': batch_id, 'inventory': inventory_status, 'ownership': ownership_status, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text(f'WITH selected AS (\n      SELECT p.* FROM public.tag_pairs p WHERE\n      (CAST(:ref AS text) IS NULL OR p.pair_reference=:ref)\n      AND (CAST(:batch AS uuid) IS NULL OR p.batch_id=:batch)\n      AND (CAST(:inventory AS text) IS NULL OR p.inventory_status=:inventory)\n      AND (CAST(:ownership AS text) IS NULL OR p.ownership_status=:ownership)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (p.created_at,p.id)<(:stamp,:ident))\n      ORDER BY p.created_at DESC,p.id DESC LIMIT :lim)\n      SELECT {PAIR_FIELDS} FROM selected p ORDER BY p.created_at DESC,p.id DESC'), {'ref': pair_reference, 'batch': batch_id, 'inventory': inventory_status, 'ownership': ownership_status, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, cursor, fail, len, ord, page, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "pair_reference",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Pair Reference"
      }
    },
    {
      "name": "batch_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Batch Id"
      }
    },
    {
      "name": "inventory_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "generated",
              "printed",
              "qa_passed",
              "reserved",
              "packed",
              "shipped",
              "delivered",
              "rejected"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Inventory Status"
      }
    },
    {
      "name": "ownership_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "unclaimed",
              "active",
              "transfer_pending",
              "disputed",
              "revoked"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Ownership Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__inventory_queries__PairPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-085 — GET `/api/v1/admin/tag-pairs/{pair_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited.
- Source: `backend/app/api/v1/inventory_queries.py:215`, `pair_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, bounds, context.session.execute, context.session.execute(text(f"SELECT {PAIR_FIELDS},\n      (SELECT jsonb_build_object('unit_id',u.id,'order_id',u.order_id,'status',u.status,'reserved_until',u.reserved_until,'allocated_at',u.allocated_at)\n       FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated') LIMIT 1) AS live_allocation,\n      COALESCE((SELECT jsonb_agg(jsonb_build_object({TAG_FIELDS}) ORDER BY q.created_at DESC,q.id DESC)\n       FROM (SELECT * FROM public.qr_codes WHERE pair_id=p.id AND NOT is_current\n         AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident)) ORDER BY created_at DESC,id DESC LIMIT :lim) q),'[]'::jsonb) AS history\n      FROM public.tag_pairs p WHERE p.id=:id"), {'id': pair_id, 'stamp': stamp, 'ident': ident, 'lim': history_limit + 1}).mappings, context.session.execute(text(f"SELECT {PAIR_FIELDS},\n      (SELECT jsonb_build_object('unit_id',u.id,'order_id',u.order_id,'status',u.status,'reserved_until',u.reserved_until,'allocated_at',u.allocated_at)\n       FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status IN ('reserved','allocated') LIMIT 1) AS live_allocation,\n      COALESCE((SELECT jsonb_agg(jsonb_build_object({TAG_FIELDS}) ORDER BY q.created_at DESC,q.id DESC)\n       FROM (SELECT * FROM public.qr_codes WHERE pair_id=p.id AND NOT is_current\n         AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident)) ORDER BY created_at DESC,id DESC LIMIT :lim) q),'[]'::jsonb) AS history\n      FROM public.tag_pairs p WHERE p.id=:id"), {'id': pair_id, 'stamp': stamp, 'ident': ident, 'lim': history_limit + 1}).mappings().one_or_none, cursor, dict, page, require_staff, result.pop, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "pair_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Pair Id"
      }
    },
    {
      "name": "history_limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "History Limit"
      }
    },
    {
      "name": "history_cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "History Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PairDetail"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-091 — GET `/api/v1/admin/qr-batches`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited.
- Source: `backend/app/api/v1/inventory_queries.py:250`, `list_batches`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Query, bounds, context.session.execute, context.session.execute(text(f"WITH selected AS (\n      SELECT b.* FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'\n      AND (CAST(:label AS text) IS NULL OR b.batch_code=:label)\n      AND (CAST(:status AS text) IS NULL OR b.status=:status)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (b.created_at,b.id)<(:stamp,:ident))\n      ORDER BY b.created_at DESC,b.id DESC LIMIT :lim)\n      SELECT {BATCH_FIELDS} FROM selected b ORDER BY b.created_at DESC,b.id DESC"), {'label': batch_label, 'status': status, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text(f"WITH selected AS (\n      SELECT b.* FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'\n      AND (CAST(:label AS text) IS NULL OR b.batch_code=:label)\n      AND (CAST(:status AS text) IS NULL OR b.status=:status)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (b.created_at,b.id)<(:stamp,:ident))\n      ORDER BY b.created_at DESC,b.id DESC LIMIT :lim)\n      SELECT {BATCH_FIELDS} FROM selected b ORDER BY b.created_at DESC,b.id DESC"), {'label': batch_label, 'status': status, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, cursor, fail, len, page, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "batch_label",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Batch Label"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "draft",
              "generated",
              "printed",
              "qa_passed",
              "rejected",
              "closed"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__inventory_queries__BatchPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-092 — GET `/api/v1/admin/qr-batches/{batch_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited.
- Source: `backend/app/api/v1/inventory_queries.py:286`, `batch_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, context.session.execute, context.session.execute(text(f"SELECT {BATCH_FIELDS} FROM public.qr_batches b WHERE b.id=:id AND to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'"), {'id': batch_id}).mappings, context.session.execute(text(f"SELECT {BATCH_FIELDS} FROM public.qr_batches b WHERE b.id=:id AND to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone'"), {'id': batch_id}).mappings().one_or_none, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__inventory_queries__BatchMetadata"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-230 — GET `/api/v1/admin/inventory/summary`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy inventory list/detail/summary inspects tag_pairs/qr-batches and their QA/allocation metadata. Read-only inspection prohibited.
- Source: `backend/app/api/v1/inventory_queries.py:304`, `stock_summary`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text(f"SELECT statement_timestamp() AS as_of,count(*) AS pair_count,\n      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current)),0)::bigint AS current_tag_count,\n      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND NOT q.is_current)),0)::bigint AS historical_tag_count,\n      count(*) FILTER(WHERE {AVAILABLE}) AS available_pairs,\n      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='reserved')) AS reserved_pairs,\n      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='allocated')) AS allocated_pairs,\n      count(*) FILTER(WHERE p.inventory_status IN ('generated','printed','rejected')) AS qa_held_pairs,\n      count(*) FILTER(WHERE p.ownership_status='active') AS active_pairs,\n      (SELECT jsonb_build_object('batch_id',b.id,'batch_label',b.batch_code,'status',b.status,'generated_at',b.generated_at)\n        FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone' ORDER BY b.created_at DESC,b.id DESC LIMIT 1) AS last_batch\n      FROM public.tag_pairs p")).mappings, context.session.execute(text(f"SELECT statement_timestamp() AS as_of,count(*) AS pair_count,\n      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND q.is_current)),0)::bigint AS current_tag_count,\n      COALESCE(sum((SELECT count(*) FROM public.qr_codes q WHERE q.pair_id=p.id AND NOT q.is_current)),0)::bigint AS historical_tag_count,\n      count(*) FILTER(WHERE {AVAILABLE}) AS available_pairs,\n      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='reserved')) AS reserved_pairs,\n      count(*) FILTER(WHERE EXISTS(SELECT 1 FROM public.order_pair_units u WHERE u.pair_id=p.id AND u.status='allocated')) AS allocated_pairs,\n      count(*) FILTER(WHERE p.inventory_status IN ('generated','printed','rejected')) AS qa_held_pairs,\n      count(*) FILTER(WHERE p.ownership_status='active') AS active_pairs,\n      (SELECT jsonb_build_object('batch_id',b.id,'batch_label',b.batch_code,'status',b.status,'generated_at',b.generated_at)\n        FROM public.qr_batches b WHERE to_jsonb(b)->>'generation_mode' IS DISTINCT FROM 'standalone' ORDER BY b.created_at DESC,b.id DESC LIMIT 1) AS last_batch\n      FROM public.tag_pairs p")).mappings().one, require_staff, router.get, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/StockSummary"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### typed-inventory-generate — POST `/api/v1/admin/qr-inventory/batches`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:189`, `generate`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `checked, context.session.begin_nested, context.session.execute, context.session.execute(text('SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,:ecc,:key,CAST(:tokens AS jsonb))'), {'sid': context.principal.session_id, 'label': body.batch_label, 'kind': body.qr_type, 'quantity': body.quantity, 'ecc': body.ecc_level, 'key': keys[0], 'tokens': json.dumps([new_public_token() for _ in range(body.quantity)])}).scalar_one, fail, json.dumps, len, new_public_token, range, re.fullmatch, request.headers.getlist, require_staff, router.post, text`.

```json
{
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/GenerateRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/GenerationReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/qr-inventory/batches",
    status_code=201,
    response_model=GenerationReceipt,
    operation_id="typed-inventory-generate",
)
def generate(body: GenerateRequest, context: Authenticated, request: Request):
    require_staff(context, "operations")
    # Bearer-authenticated backend API. Browser callers use the same-origin relay
    # in Phase 3; no cookie authentication or new browser token transport here.
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", keys[0]):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    if request.query_params:
        fail(422, "INVALID_QUERY")
    try:
        with context.session.begin_nested():
            result = context.session.execute(
                text(
                    "SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,:ecc,:key,CAST(:tokens AS jsonb))"
                ),
                {
                    "sid": context.principal.session_id,
                    "label": body.batch_label,
                    "kind": body.qr_type,
                    "quantity": body.quantity,
                    "ecc": body.ecc_level,
                    "key": keys[0],
                    "tokens": json.dumps(
                        [new_public_token() for _ in range(body.quantity)]
                    ),
                },
            ).scalar_one()
            return checked(result)
    except IntegrityError:
        fail(409, "GENERATION_CONFLICT")
```

### typed-inventory-batches — GET `/api/v1/admin/qr-inventory/batches`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:227`, `batches`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `Query, page, paging, read, router.get`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "maxLength": 220
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "qr_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "lost",
              "ice"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Qr Type"
      }
    },
    {
      "name": "batch_label",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "minLength": 1,
            "maxLength": 40
          },
          {
            "type": "null"
          }
        ],
        "title": "Batch Label"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "draft",
              "generated",
              "printed",
              "qa_passed",
              "rejected",
              "closed"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__typed_inventory__BatchPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/qr-inventory/batches",
    response_model=BatchPage,
    operation_id="typed-inventory-batches",
)
def batches(context: Authenticated, filters: Annotated[BatchFilters, Query()]):
    return page(
        read(context, "batches", paging(filters)),
        filters.limit,
        BatchMetadata,
        "batch_id",
    )
```

### typed-inventory-batch-detail — GET `/api/v1/admin/qr-inventory/batches/{batch_id}`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:241`, `batch_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `read, router.get, str`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__typed_inventory__BatchMetadata"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/qr-inventory/batches/{batch_id}",
    response_model=BatchMetadata,
    operation_id="typed-inventory-batch-detail",
)
def batch_detail(batch_id: UUID, context: Authenticated):
    return read(context, "batch", {"batch_id": str(batch_id)})
```

### typed-inventory-summary — GET `/api/v1/admin/qr-inventory/summary`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:250`, `summary`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `Query, filters.model_dump, read, router.get`.

```json
{
  "parameters": [
    {
      "name": "qr_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "lost",
              "ice"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Qr Type"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__typed_inventory__Summary"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/qr-inventory/summary",
    response_model=Summary,
    operation_id="typed-inventory-summary",
)
def summary(context: Authenticated, filters: Annotated[SummaryFilters, Query()]):
    return read(context, "summary", filters.model_dump(mode="json"))
```

### typed-inventory-codes — GET `/api/v1/admin/qr-inventory/codes`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:259`, `codes`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `Query, page, paging, read, router.get`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "maxLength": 220
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "qr_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "lost",
              "ice"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Qr Type"
      }
    },
    {
      "name": "batch_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Batch Id"
      }
    },
    {
      "name": "inventory_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "available",
              "allocated",
              "retired"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Inventory Status"
      }
    },
    {
      "name": "ownership_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "unclaimed",
              "active",
              "revoked"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Ownership Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__typed_inventory__QRPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/qr-inventory/codes",
    response_model=QRPage,
    operation_id="typed-inventory-codes",
)
def codes(context: Authenticated, filters: Annotated[QRFilters, Query()]):
    return page(
        read(context, "codes", paging(filters)), filters.limit, QRMetadata, "qr_id"
    )
```

### typed-inventory-code-detail — GET `/api/v1/admin/qr-inventory/codes/{qr_id}`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/typed_inventory.py:270`, `code_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `read, router.get, str`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/QRMetadata"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/qr-inventory/codes/{qr_id}",
    response_model=QRMetadata,
    operation_id="typed-inventory-code-detail",
)
def code_detail(qr_id: UUID, context: Authenticated):
    return read(context, "code", {"qr_id": str(qr_id)})
```

### API-207 — GET `/api/v1/public/qr/{token}/activation-context`

- Eligibility: **QR-PAIR EXCLUDED**. Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials.
- Source: `backend/app/api/v1/activation.py:121`, `activation_context`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, JSONResponse, api_transaction, decision, rate_limit, re.fullmatch, router.get, session.execute, session.execute(text('SELECT public.sr_activation_context(:token)'), {'token': token}).scalar_one, text`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PublicActivationContext"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### API-208 — POST `/api/v1/me/tag-pairs/activation-intents`

- Eligibility: **QR-PAIR EXCLUDED**. Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials.
- Source: `backend/app/api/v1/activation.py:146`, `begin_activation`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, UUID, activation_verifier, body.activation_secret.get_secret_value, bytes, context.session.execute, context.session.execute(text('SELECT * FROM public.sr_activation_key_context(:token)'), {'token': body.scanned_token}).one_or_none, context.session.execute(text('SELECT public.sr_begin_activation(:token,:proof,:version)'), {'token': body.scanned_token, 'proof': proof, 'version': version}).scalar_one, decision, rate_limit, require_verified_account, router.post, text, verifier_key`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/IntentRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/IntentResponse"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-032 — POST `/api/v1/me/tag-pairs/activations`

- Eligibility: **QR-PAIR EXCLUDED**. Activation context/intents/confirmation inspects and may activate or assign legacy pair ownership/credentials.
- Source: `backend/app/api/v1/activation.py:188`, `confirm_activation`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, body.model_dump, context.session.execute, context.session.execute(text('SELECT public.sr_confirm_activation(:iid,:key,:digest)'), {'iid': body.intent_id, 'key': idempotency_key, 'digest': digest}).scalar_one, decision, hashlib.sha256, hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode()).hexdigest, json.dumps, json.dumps(body.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode, re.fullmatch, require_verified_account, router.post, text`.

```json
{
  "parameters": [
    {
      "name": "Idempotency-Key",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Idempotency-Key"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ConfirmationRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ActivationResponse"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-040 — GET `/api/v1/me/qr/{qr_id}/lost-profile`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:299`, `get_lost`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `owned, profile_data, router.get`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-041 — PUT `/api/v1/me/qr/{qr_id}/lost-profile`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:305`, `put_lost`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, ProfileError, audit, body.model_dump, changes.get, database_now, owned, profile_data, read, router.put, save, version_check`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/LostEdit"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-042 — GET `/api/v1/me/qr/{qr_id}/ice-profile`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:337`, `get_ice`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `owned, profile_data, router.get`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-043 — PUT `/api/v1/me/qr/{qr_id}/ice-profile`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:343`, `put_ice`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, ProfileError, audit, body.medical_notes.get_secret_value, bool, changes.get, changes.update, database_now, datetime.now, datetime.now(UTC).timestamp, decrypt, encrypt, getattr, owned, profile_data, read, router.put, save, version_check`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ICEEdit"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-044 — GET `/api/v1/me/qr/{qr_id}/ice-contacts`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:490`, `get_contacts`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `contacts_data, owned, router.get`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-045 — POST `/api/v1/me/qr/{qr_id}/ice-contacts`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:600`, `add_contact`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, change_contact, contacts_data, json.loads, next, response, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ContactEdit"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-046 — PATCH `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:618`, `edit_contact`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, change_contact, contacts_data, json.loads, next, response, router.patch, str`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "contact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Contact Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ContactEdit"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-047 — DELETE `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:641`, `remove_contact`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, Header, Response, audit, context.session.execute, context.session.execute(text('UPDATE public.ice_contacts SET published=false,removed_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=:cid AND ice_qr_id=:qr AND removed_at IS NULL RETURNING id'), {'cid': contact_id, 'qr': qr_id}).scalar_one_or_none, owned, read, router.delete, save, text, version_check`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "contact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Contact Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "responses": {
    "204": {
      "description": "Successful Response"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-048 — GET `/api/v1/me/qr/{qr_id}/contact-preferences`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:699`, `get_preferences`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `owned, preference_data, router.get`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-049 — PUT `/api/v1/me/qr/{qr_id}/contact-preferences`

- Eligibility: **QR-PAIR EXCLUDED**. QR profile/contact/preferences handlers authorize through QR ownership that can join tag_pairs and change pair-linked public profile state.
- Source: `backend/app/api/v1/profiles.py:705`, `put_preferences`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Header, ProfileError, audit, body.whatsapp_phone.get_secret_value, changes.update, database_now, decrypt, encrypt, owned, phone, preference_data, read, router.put, save, version_check`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "if-match",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "If-Match"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/PreferenceEdit"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-030 — GET `/api/v1/me/tag-pairs`

- Eligibility: **QR-PAIR EXCLUDED**. Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup.
- Source: `backend/app/api/v1/owner_qr.py:160`, `list_pairs`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Query, context.session.execute, context.session.execute(text('SELECT id,pair_reference,ownership_status,inventory_status,activated_at,coalesce(activated_at,created_at) AS sort_at FROM public.tag_pairs WHERE owner_user_id=:uid AND (CAST(:after AS uuid) IS NULL OR (coalesce(activated_at,created_at),id)<(CAST(:at AS timestamptz),CAST(:after AS uuid))) AND (CAST(:status AS text) IS NULL OR ownership_status=:status) ORDER BY sort_at DESC,id DESC LIMIT :limit'), {'uid': context.principal.user_id, 'after': after[0] if after else None, 'at': after[1] if after else None, 'status': status, 'limit': limit + 1}).mappings, context.session.execute(text('SELECT id,pair_reference,ownership_status,inventory_status,activated_at,coalesce(activated_at,created_at) AS sort_at FROM public.tag_pairs WHERE owner_user_id=:uid AND (CAST(:after AS uuid) IS NULL OR (coalesce(activated_at,created_at),id)<(CAST(:at AS timestamptz),CAST(:after AS uuid))) AND (CAST(:status AS text) IS NULL OR ownership_status=:status) ORDER BY sort_at DESC,id DESC LIMIT :limit'), {'uid': context.principal.user_id, 'after': after[0] if after else None, 'at': after[1] if after else None, 'status': status, 'limit': limit + 1}).mappings().all, decode_cursor, encode_cursor, failure, grouped[child['pair_id']].append, len, pair_summary, router.get, tags, text`.

```json
{
  "parameters": [
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "unclaimed",
              "active",
              "transfer_pending",
              "disputed",
              "revoked"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__owner_qr__PairPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-031 — GET `/api/v1/me/tag-pairs/{pair_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup.
- Source: `backend/app/api/v1/owner_qr.py:209`, `get_pair`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, context.session.execute, context.session.execute(text('SELECT id,pair_reference,ownership_status,inventory_status,activated_at FROM public.tag_pairs WHERE id=:pid AND owner_user_id=:uid'), {'pid': pair_id, 'uid': context.principal.user_id}).mappings, context.session.execute(text('SELECT id,pair_reference,ownership_status,inventory_status,activated_at FROM public.tag_pairs WHERE id=:pid AND owner_user_id=:uid'), {'pid': pair_id, 'uid': context.principal.user_id}).mappings().one_or_none, pair_summary, require_pair_owner, router.get, tags, text`.

```json
{
  "parameters": [
    {
      "name": "pair_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Pair Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PairSummary"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-205 — GET `/api/v1/me/qr`

- Eligibility: **QR-PAIR EXCLUDED**. Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup.
- Source: `backend/app/api/v1/owner_qr.py:232`, `list_qr`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Query, decode_cursor, encode_cursor, failure, len, router.get, search.strip, tag, tags`.

```json
{
  "parameters": [
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "tag_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "lost",
              "ice"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Tag Type"
      }
    },
    {
      "name": "pair_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Pair Id"
      }
    },
    {
      "name": "search",
      "in": "query",
      "required": false,
      "schema": {
        "type": "string",
        "maxLength": 120,
        "default": "",
        "title": "Search"
      }
    },
    {
      "name": "publication",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "draft",
              "published"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Publication"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "unactivated",
              "active",
              "owner_disabled",
              "admin_suspended",
              "revoked"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__owner_qr__QRPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-206 — GET `/api/v1/me/qr/{qr_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Owner QR/pair collection/detail uses legacy pair ownership and pair-linked inspection; not a permitted admin lookup.
- Source: `backend/app/api/v1/owner_qr.py:277`, `get_qr`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, context.session.execute, context.session.execute(text('SELECT oi.product_name_snapshot,oi.variant_name_snapshot,u.copies FROM public.order_item_qr_uses u JOIN public.order_items oi ON oi.id=u.order_item_id JOIN public.orders o ON o.id=oi.order_id WHERE u.qr_code_id=:qid AND o.customer_user_id=:uid ORDER BY u.id'), {'qid': qr_id, 'uid': context.principal.user_id}).mappings, context.session.execute(text('SELECT public.sr_standalone_products(:qid)'), {'qid': qr_id}).scalar_one, dict, require_qr_owner, router.get, tag, tags, text`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/QRDetail"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-list — GET `/api/v1/me/independent-qr`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/standalone_owner.py:80`, `collection`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `Query, checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_owner_list(:sid,:take,:after)'), {'sid': context.principal.session_id, 'take': limit + 1, 'after': after}).scalar_one, len, require_verified_account, router.get, str, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "after",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "After"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-intent — POST `/api/v1/me/independent-qr/activation-intents`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/standalone_owner.py:103`, `begin`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_begin(:sid,:iid)'), {'sid': context.principal.session_id, 'iid': body.logical_item_id}).scalar_one, require_verified_account, router.post, text`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Begin"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-activate — POST `/api/v1/me/independent-qr/activations`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/standalone_owner.py:118`, `confirm`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `Header, checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_confirm(:sid,:intent,:kh,:rh)'), {'sid': context.principal.session_id, 'intent': body.intent_id, 'kh': kh, 'rh': rh}).scalar_one, hashes, require_verified_account, router.post, text`.

```json
{
  "parameters": [
    {
      "name": "Idempotency-Key",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Idempotency-Key"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Confirm"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-history — GET `/api/v1/me/independent-qr/{qr_id}/history`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/standalone_owner.py:143`, `history`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `Query, checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_history(:sid,:qid,:take,:after)'), {'sid': context.principal.session_id, 'qid': qr_id, 'take': limit, 'after': after_revision}).scalar_one, require_verified_account, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "after_revision",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "integer",
            "minimum": 1
          },
          {
            "type": "null"
          }
        ],
        "title": "After Revision"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-availability — PATCH `/api/v1/me/independent-qr/{qr_id}/availability`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/standalone_owner.py:164`, `availability`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `Header, checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_availability(:sid,:qid,:expected,:wanted,:kh,:rh)'), {'sid': context.principal.session_id, 'qid': qr_id, 'expected': body.expected_revision, 'wanted': body.public_status, 'kh': kh, 'rh': rh}).scalar_one, hashes, require_verified_account, router.patch, text`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    },
    {
      "name": "Idempotency-Key",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Idempotency-Key"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Availability"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### independent-qr-support — GET `/api/v1/admin/support-cases/{case_id}/independent-qr`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/standalone_owner.py:193`, `support`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; support for admin context; owner session otherwise.
- Dependencies/helper calls: `checked, context.session.execute, context.session.execute(text('SELECT public.sr_standalone_support(:sid,:cid)'), {'sid': context.principal.session_id, 'cid': case_id}).scalar_one, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "case_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Case Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/support-cases/{case_id}/independent-qr",
    operation_id="independent-qr-support",
)
def support(case_id: UUID, context: Authenticated):
    require_staff(context, "support")
    return checked(
        context.session.execute(
            text("SELECT public.sr_standalone_support(:sid,:cid)"),
            {"sid": context.principal.session_id, "cid": case_id},
        ).scalar_one()
    )
```

### API-010 — GET `/api/v1/public/qr/{token}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_qr.py:75`, `get_public_qr`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, api_transaction, hashlib.sha256, hashlib.sha256(peer.encode()).hexdigest, peer.encode, re.fullmatch, router.get, session.execute, session.execute(text('SELECT public.sr_public_qr_projection(:token)'), {'token': token}).scalar_one, session.execute(text('SELECT public.sr_public_scan_rate(:binding)'), {'binding': digest}).scalar_one, text`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PublicQRProfile"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### order-payment-instructions — GET `/api/v1/me/orders/{order_id}/payment-instructions`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:34`, `payment_instructions`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text("SELECT to_jsonb(o)->'payment_instructions_snapshot' FROM public.orders o WHERE id=:id"), {'id': order_id}).scalar_one_or_none, fail, require_order_owner, require_verified_account, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-210 — POST `/api/v1/me/orders/{order_id}/payment-attempts`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:209`, `create_payment_attempt`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `body.model_dump, context.session.execute, context.session.execute(text("SELECT 1 FROM public.payment_attempts WHERE order_id=:id AND state IN ('initiated','submitted','under_review','disputed')"), {'id': order_id}).first, dict, encrypt, f"{context.principal.user_id}:{request.headers['idempotency-key']}".encode, fail, hashlib.sha256, hashlib.sha256(f"{context.principal.user_id}:{request.headers['idempotency-key']}".encode()).hexdigest, json.dumps, lock_order, record, require_order_owner, require_verified_account, router.post, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/PaymentRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-209 — GET `/api/v1/me/orders/{order_id}/payment-attempts`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:291`, `list_payment_attempts`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text('SELECT id,provider_key,state,amount,currency_code,sender_reference_masked,created_at FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC'), {'id': order_id}).mappings, dict, require_order_owner, require_verified_account, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-211 — POST `/api/v1/me/payment-attempts/{attempt_id}/evidence-uploads`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:304`, `authorize_evidence_upload`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `base64.urlsafe_b64encode, base64.urlsafe_b64encode(token).decode, body.model_dump, context.session.execute, context.session.execute(text('SELECT count(*) FROM public.idempotency_records WHERE actor_user_id=:uid AND operation=:op'), {'uid': context.principal.user_id, 'op': 'evidence.upload:' + str(attempt_id)}).scalar_one, context.session.execute(text('SELECT state FROM public.payment_attempts WHERE id=:id'), {'id': attempt_id}).mappings, context.session.execute(text('SELECT state FROM public.payment_attempts WHERE id=:id'), {'id': attempt_id}).mappings().one, dict, encrypt, fail, int, json.dumps, record, require_payment_owner, require_verified_account, router.post, storage, storage(request).authorize, str, text, time.time, uuid4`.

```json
{
  "parameters": [
    {
      "name": "attempt_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Attempt Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/UploadRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-212 — POST `/api/v1/me/payment-attempts/{attempt_id}/evidence-finalize`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:361`, `finalize_evidence`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `base64.urlsafe_b64decode, body.model_dump, body.upload_token.split, context.session.execute, context.session.execute(text('SELECT id FROM public.payment_evidence WHERE object_key=:key'), {'key': payload['object_key']}).scalar_one_or_none, decrypt, dict, fail, int, json.loads, lock_attempt, record, require_payment_owner, require_verified_account, router.post, storage, storage(request).verify, str, text, time.time, uuid4`.

```json
{
  "parameters": [
    {
      "name": "attempt_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Attempt Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/EvidenceRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-241 — POST `/api/v1/admin/payment-attempts/{attempt_id}/reviews`

- Eligibility: **QR-PAIR EXCLUDED**. Generic review verify branch allocates order_pair_units and can enqueue allocation.finalize; finance label does not isolate it.
- Source: `backend/app/api/v1/payments.py:427`, `review_payment`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance; typed allocation finance/operations.
- Dependencies/helper calls: `AccessError, Decimal, UUID, any, body.bank_match_reference.casefold, body.bank_match_reference.casefold().strip, body.bank_match_reference.casefold().strip().encode, body.model_dump, context.session.execute, context.session.execute(text('SELECT id,status FROM public.order_pair_units WHERE order_id=:id ORDER BY id FOR UPDATE'), {'id': order['id']}).all, context.session.execute(text('SELECT public.sr_typed_settle(\n                    :sid,:aid,:bank_verified,:amount,:currency,:fingerprint,:reason)'), {'sid': context.principal.session_id, 'aid': attempt_id, 'bank_verified': body.bank_verified, 'amount': Decimal(body.settled_amount), 'currency': body.settled_currency, 'fingerprint': fingerprint, 'reason': body.reason}).scalar_one, dict, fail, hmac.new, hmac.new(s.payment_reference_key.get_secret_value().encode(), body.bank_match_reference.casefold().strip().encode(), hashlib.sha256).digest, lock_attempt, order.get, record, require_order_clear, require_staff, router.post, s.payment_reference_key.get_secret_value, s.payment_reference_key.get_secret_value().encode, str, text, typed_result, uuid4`.

```json
{
  "parameters": [
    {
      "name": "attempt_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Attempt Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ReviewRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### typed-allocation-status — GET `/api/v1/admin/orders/{order_id}/qr-allocation`

- Eligibility: **QUARANTINED**. Owner explicitly quarantined this exact endpoint; independent/typed naming is not authorization. Do not integrate, call, test, prefetch or initialize.
- Source: `backend/app/api/v1/payments.py:575`, `allocation_status`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance; typed allocation finance/operations.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text('SELECT public.sr_typed_allocation_status(:id)'), {'id': order_id}).scalar_one, require_staff, router.get, text, typed_result`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/orders/{order_id}/qr-allocation", operation_id="typed-allocation-status")
def allocation_status(order_id: UUID, context: Authenticated):
    require_staff(context, "finance", "operations")
    return typed_result(context.session.execute(text("SELECT public.sr_typed_allocation_status(:id)"), {"id": order_id}).scalar_one())
```

### typed-allocation-retry — POST `/api/v1/admin/orders/{order_id}/qr-allocation/retry`

- Eligibility: **QUARANTINED**. Allocation retry is quarantined by default-deny, not merely waiting for release gates. Independent-QR terminology does not authorize it.
- Source: `backend/app/api/v1/payments.py:581`, `retry_allocation`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance; typed allocation finance/operations.
- Dependencies/helper calls: `body.model_dump, context.session.execute, context.session.execute(text('SELECT public.sr_typed_allocation_retry(:sid,:id)'), {'sid': context.principal.session_id, 'id': order_id}).scalar_one, record, require_staff, router.post, str, text, typed_result`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AllocationRetry"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post("/admin/orders/{order_id}/qr-allocation/retry", operation_id="typed-allocation-retry")
def retry_allocation(order_id: UUID, body: AllocationRetry, context: Authenticated, request: Request):
    require_staff(context, "finance", "operations")

    def work(settings):
        value = typed_result(context.session.execute(text("SELECT public.sr_typed_allocation_retry(:sid,:id)"),
                            {"sid": context.principal.session_id, "id": order_id}).scalar_one())
        context.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        context.session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        return value, order_id

    return record(context, request, "allocation.retry", {"order_id": str(order_id), **body.model_dump()}, work)
```

### payment-evidence-read — GET `/api/v1/admin/payment-evidence/{evidence_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:595`, `read_evidence`. Registered and OpenAPI matched; runtime unverified.
- Screen: Payments.
- Auth/permissions: JWT + live session; finance; typed allocation finance/operations.
- Dependencies/helper calls: `AccessError, Response, context.session.execute, context.session.execute(text('SELECT * FROM public.payment_evidence WHERE id=:id AND deleted_at IS NULL'), {'id': evidence_id}).mappings, context.session.execute(text('SELECT * FROM public.payment_evidence WHERE id=:id AND deleted_at IS NULL'), {'id': evidence_id}).mappings().one_or_none, require_staff, router.get, storage, storage(request).verify, text`.

```json
{
  "parameters": [
    {
      "name": "evidence_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Evidence Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/payment-evidence/{evidence_id}", operation_id="payment-evidence-read"
)
def read_evidence(evidence_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "finance")
    row = (
        context.session.execute(
            text(
                "SELECT * FROM public.payment_evidence WHERE id=:id AND deleted_at IS NULL"
            ),
            {"id": evidence_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccessError(404)
    data = storage(request).verify(
        {
            "object_key": row["object_key"],
            "bytes_size": row["bytes_size"],
            "content_type": row["content_type"],
            "sha256": row["sha256_hex"],
        }
    )
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(:actor,'staff','payment.evidence.read','payment_evidence',:id,'finance evidence retrieval','{}'::jsonb)"
        ),
        {"actor": context.principal.user_id, "id": evidence_id},
    )
    return Response(
        data,
        media_type=row["content_type"],
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="payment-evidence"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )
```

### API-240 — GET `/api/v1/admin/orders/{order_id}/payment-attempts`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/payments.py:638`, `finance_attempts`. Registered and OpenAPI matched; runtime unverified.
- Screen: Payments.
- Auth/permissions: JWT + live session; finance; typed allocation finance/operations.
- Dependencies/helper calls: `AccessError, context.session.execute, context.session.execute(text('SELECT * FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC LIMIT 100'), {'id': order_id}).mappings, context.session.execute(text('SELECT * FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC LIMIT 100'), {'id': order_id}).mappings().all, context.session.execute(text('SELECT id,content_type,bytes_size FROM public.payment_evidence WHERE attempt_id=:id AND deleted_at IS NULL ORDER BY created_at DESC'), {'id': a['id']}).mappings, context.session.execute(text('SELECT id,content_type,bytes_size FROM public.payment_evidence WHERE attempt_id=:id AND deleted_at IS NULL ORDER BY created_at DESC'), {'id': a['id']}).mappings().all, decrypt, dict, items.append, json.loads, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/orders/{order_id}/payment-attempts", operation_id="API-240")
def finance_attempts(order_id: UUID, context: Authenticated, request: Request):
    require_staff(context, "finance")
    rows = (
        context.session.execute(
            text(
                "SELECT * FROM public.payment_attempts WHERE order_id=:id ORDER BY created_at DESC,id DESC LIMIT 100"
            ),
            {"id": order_id},
        )
        .mappings()
        .all()
    )
    items = []
    try:
        for a in rows:
            holder = (
                json.loads(
                    decrypt(
                        request.app.state.settings,
                        a["id"],
                        "sender_holder",
                        a["sender_holder_ciphertext"],
                        a["sender_key_version"],
                    )
                )
                if a["sender_holder_ciphertext"]
                else {}
            )
            account = (
                decrypt(
                    request.app.state.settings,
                    a["id"],
                    "sender_account",
                    a["sender_account_ciphertext"],
                    a["sender_key_version"],
                )
                if a["sender_account_ciphertext"]
                else None
            )
            evidence = (
                context.session.execute(
                    text(
                        "SELECT id,content_type,bytes_size FROM public.payment_evidence WHERE attempt_id=:id AND deleted_at IS NULL ORDER BY created_at DESC"
                    ),
                    {"id": a["id"]},
                )
                .mappings()
                .all()
            )
            items.append(
                {
                    "attempt_id": a["id"],
                    "state": a["state"],
                    "amount": f"{a['amount']:.2f}",
                    "currency_code": a["currency_code"],
                    "sender_account": account,
                    "sender_holder": holder,
                    "evidence": [dict(e) for e in evidence],
                }
            )
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    context.session.execute(
        text(
            "INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,reason,safe_details) VALUES(:actor,'staff','payment.finance.read','order',:id,'finance settlement review','{}'::jsonb)"
        ),
        {"actor": context.principal.user_id, "id": order_id},
    )
    return {"items": items}
```

### API-034 — GET `/api/v1/me/tag-pairs/{pair_id}/activation-history`

- Eligibility: **QR-PAIR EXCLUDED**. Activation-history/public-status workflow inspects pair history or changes pair-linked public availability/lifecycle.
- Source: `backend/app/api/v1/qr_lifecycle.py:181`, `history`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, History, LifecycleError, Position, Snapshot.model_validate, any, authorize, checked, cursor, db.execute, db.execute(text('SELECT public.sr_qr_lifecycle_history(:sid,:pid,1,NULL,NULL)'), {'sid': args['sid'], 'pid': pair_id}).scalar_one, db.execute(text('SELECT public.sr_qr_lifecycle_history(:sid,:pid,:take,:stamp,:eid)'), args).scalar_one, guard, int, key, len, params.get, params.getlist, position, re.fullmatch, router.get, snap.model_dump, text`.

```json
{
  "parameters": [
    {
      "name": "pair_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Pair Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/History"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-035 — PATCH `/api/v1/me/qr/{qr_id}/public-status`

- Eligibility: **QR-PAIR EXCLUDED**. Activation-history/public-status workflow inspects pair history or changes pair-linked public availability/lifecycle.
- Source: `backend/app/api/v1/qr_lifecycle.py:270`, `change_status`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, ClosedReceipt.model_validate, LifecycleError, Receipt.model_validate, Receipt.model_validate_json, authorize, body.model_dump_json, body.model_dump_json().encode, bytes.fromhex, checked, db.execute, db.execute(sql, params).scalar_one, db.execute(text('SELECT public.sr_qr_lifecycle_save(:sid,:amr,:qid,:scope,:digest,:cipher,CAST(:version AS smallint))'), {'sid': params['sid'], 'amr': params['amr'], 'qid': qr_id, 'scope': scope, 'digest': digest, 'cipher': cipher, 'version': version}).scalar_one, decrypt, encrypt, f'{actor}:qr.public_status:{qr_id}:{keys[0]}'.encode, guard, hashlib.sha256, hashlib.sha256(body.model_dump_json().encode()).hexdigest, hashlib.sha256(f'{actor}:qr.public_status:{qr_id}:{keys[0]}'.encode()).hexdigest, len, re.fullmatch, request.headers.getlist, result.model_dump_json, router.patch, set, text`.

```json
{
  "parameters": [
    {
      "name": "qr_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Qr Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Command"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__qr_lifecycle__Receipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-350 — GET `/api/v1/admin/print-jobs/counts`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_queries.py:208`, `counts`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Jobs.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `','.join, AccessError, Count, Counts, ValueError, cap, datetime.now, filters.model_dump, finish, router.get, selected, timed, timed(context, 'WITH selected AS (SELECT j.order_id,j.status AS job_status ' + WHERE + ') SELECT ' + ','.join(measures), {**filters.model_dump(), 'as_of': as_of, **{s: s for s in STATES}}).one, type`.
- Manual Filters model; count includes value/is_exact, not guaranteed exact totals.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__print_queries__Counts"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/print-jobs/counts", operation_id="API-350", response_model=Counts)
def counts(context: Authenticated, request: Request):
    filters = selected(context, request, False)
    as_of = datetime.now(UTC)
    measures = [
        "(SELECT count(*) FROM (SELECT 1 FROM selected LIMIT 1000) bounded) AS matching_jobs",
        "(SELECT count(*) FROM (SELECT DISTINCT order_id FROM selected LIMIT 1000) bounded) AS affected_orders",
    ]
    measures += [
        f"(SELECT count(*) FROM (SELECT 1 FROM selected WHERE job_status=:{state} LIMIT 1000) bounded) AS {state}"
        for state in STATES
    ]
    try:
        row = timed(
            context,
            "WITH selected AS (SELECT j.order_id,j.status AS job_status "
            + WHERE
            + ") SELECT "
            + ",".join(measures),
            {**filters.model_dump(), "as_of": as_of, **{s: s for s in STATES}},
        ).one()

        def cap(value):
            if type(value) is not int or not 0 <= value <= 1000:
                raise ValueError("Invalid bounded count")
            return Count(value=value, is_exact=value < 1000)

        result = Counts(
            as_of=as_of,
            matching_jobs=cap(row["matching_jobs"]),
            affected_orders=cap(row["affected_orders"]),
            by_job_status={s: cap(row[s]) for s in STATES},
        )
        finish(context, "print.metadata.counts")
        return result
    except (SQLAlchemyError, ValueError, ProfileCryptoUnavailable):
        raise AccessError(503) from None
```

### API-349 — GET `/api/v1/admin/print-jobs`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_queries.py:247`, `jobs`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Jobs.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `AccessError, Item.model_validate, Page, Position, UUID, datetime.now, decode, encode, fail, filters.model_dump, filters.model_dump_json, finish, int, key, len, pos.as_of.astimezone, re.fullmatch, router.get, selected, timed, timed(context, 'SELECT ' + FIELDS + ' ' + WHERE + f' AND (CAST(:at AS timestamptz) IS NULL OR (j.created_at,j.id){comparison}(:at,:after_id)) ORDER BY j.created_at {direction},j.id {direction} LIMIT :take', {**filters.model_dump(), 'as_of': as_of, 'at': pos.at if pos else None, 'after_id': pos.job_id if pos else UUID(int=0), 'take': limit + 1}).all, values.get`.
- Manual Filters model plus limit, cursor, sort; cursor binds actor/filter/sort/as_of.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__print_queries__Page"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/print-jobs", operation_id="API-349", response_model=Page)
def jobs(context: Authenticated, request: Request):
    filters = selected(context, request, True)
    values = request.query_params
    raw_limit, sort = values.get("limit", "20"), values.get("sort", "oldest")
    if (
        not re.fullmatch(r"[1-9][0-9]{0,2}", raw_limit)
        or not 1 <= int(raw_limit) <= 100
        or sort not in ("oldest", "newest")
    ):
        fail(422, "INVALID_QUERY")
    limit = int(raw_limit)
    settings, actor = request.app.state.settings, context.principal.user_id
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    pos = (
        decode(settings, actor, values["cursor"], filters, sort)
        if "cursor" in values
        else None
    )
    as_of = pos.as_of.astimezone(UTC) if pos else datetime.now(UTC)
    direction, comparison = ("ASC", ">") if sort == "oldest" else ("DESC", "<")
    try:
        rows = timed(
            context,
            "SELECT "
            + FIELDS
            + " "
            + WHERE
            + f" AND (CAST(:at AS timestamptz) IS NULL OR (j.created_at,j.id){comparison}(:at,:after_id)) ORDER BY j.created_at {direction},j.id {direction} LIMIT :take",
            {
                **filters.model_dump(),
                "as_of": as_of,
                "at": pos.at if pos else None,
                "after_id": pos.job_id if pos else UUID(int=0),
                "take": limit + 1,
            },
        ).all()
        items = [Item.model_validate(r) for r in rows[:limit]]
        cursor = (
            encode(
                settings,
                actor,
                Position(
                    filters=filters.model_dump_json(),
                    sort=sort,
                    as_of=as_of,
                    at=items[-1].created_at,
                    job_id=items[-1].job_id,
                ),
            )
            if len(rows) > limit
            else None
        )
        result = Page(as_of=as_of, items=items, next_cursor=cursor)
        finish(context, "print.metadata.list")
        return result
    except (SQLAlchemyError, ValueError, ProfileCryptoUnavailable):
        raise AccessError(503) from None
```

### API-234 — POST `/api/v1/admin/orders/{order_id}/print-jobs`

- Eligibility: **QR-PAIR EXCLUDED**. Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied.
- Source: `backend/app/api/v1/printing.py:281`, `create_print_job`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `AccessError, body.model_dump, enqueue, record, require_staff, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/PrintJobRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-233 — GET `/api/v1/admin/orders/{order_id}/print-jobs`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/printing.py:308`, `list_print_jobs`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Jobs.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text('SELECT id,job_revision,status,template_fingerprint,failure_code FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC'), {'id': order_id}).mappings, context.session.execute(text('SELECT id,job_revision,status,template_fingerprint,failure_code FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC'), {'id': order_id}).mappings().all, dict, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/orders/{order_id}/print-jobs", operation_id="API-233")
def list_print_jobs(order_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    rows = (
        context.session.execute(
            text(
                "SELECT id,job_revision,status,template_fingerprint,failure_code FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC"
            ),
            {"id": order_id},
        )
        .mappings()
        .all()
    )
    return {"items": [dict(r) for r in rows]}
```

### API-235 — GET `/api/v1/admin/print-jobs/{job_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/printing.py:324`, `get_print_job`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Jobs.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `AccessError, context.session.execute, context.session.execute(text('SELECT id,format,size_bytes,sha256_hex,deleted_at FROM public.print_artifacts WHERE print_job_id=:id'), {'id': job_id}).mappings, context.session.execute(text('SELECT id,format,size_bytes,sha256_hex,deleted_at FROM public.print_artifacts WHERE print_job_id=:id'), {'id': job_id}).mappings().all, context.session.execute(text('SELECT id,order_id,job_revision,status,template_fingerprint,attempt_count,failure_code FROM public.print_jobs WHERE id=:id'), {'id': job_id}).mappings, context.session.execute(text('SELECT id,order_id,job_revision,status,template_fingerprint,attempt_count,failure_code FROM public.print_jobs WHERE id=:id'), {'id': job_id}).mappings().one_or_none, context.session.execute(text('SELECT id,product_name_snapshot,qr_type_snapshot FROM public.order_logical_items WHERE order_id=:id ORDER BY id'), {'id': r['order_id']}).mappings, context.session.execute(text('SELECT id,product_name_snapshot,qr_type_snapshot FROM public.order_logical_items WHERE order_id=:id ORDER BY id'), {'id': r['order_id']}).mappings().all, dict, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "job_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Job Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/print-jobs/{job_id}", operation_id="API-235")
def get_print_job(job_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    r = (
        context.session.execute(
            text(
                "SELECT id,order_id,job_revision,status,template_fingerprint,attempt_count,failure_code FROM public.print_jobs WHERE id=:id"
            ),
            {"id": job_id},
        )
        .mappings()
        .one_or_none()
    )
    if r is None:
        raise AccessError(404)
    artifacts = (
        context.session.execute(
            text(
                "SELECT id,format,size_bytes,sha256_hex,deleted_at FROM public.print_artifacts WHERE print_job_id=:id"
            ),
            {"id": job_id},
        )
        .mappings()
        .all()
    )
    items = context.session.execute(text("SELECT id,product_name_snapshot,qr_type_snapshot FROM public.order_logical_items WHERE order_id=:id ORDER BY id"), {"id": r["order_id"]}).mappings().all()
    return dict(r, artifacts=[dict(a) for a in artifacts], inspection_items=[dict(i) for i in items])
```

### API-236 — POST `/api/v1/admin/print-artifacts/{artifact_id}/download-grants`

- Eligibility: **QR-PAIR EXCLUDED**. Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied.
- Source: `backend/app/api/v1/printing.py:391`, `create_download_grant`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `artifact, context.session.execute, context.session.execute(text("INSERT INTO public.print_download_grants(id,artifact_id,granted_to,token_hash,expires_at) VALUES(:id,:aid,:uid,:hash,clock_timestamp()+interval '5 minutes') RETURNING expires_at"), {'id': gid, 'aid': artifact_id, 'uid': context.principal.user_id, 'hash': hashlib.sha256(token.encode()).digest()}).scalar_one, expiry.isoformat, hashlib.sha256, hashlib.sha256(token.encode()).digest, record, require_staff, router.post, secrets.token_urlsafe, str, text, token.encode, uuid4`.

```json
{
  "parameters": [
    {
      "name": "artifact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Artifact Id"
      }
    }
  ],
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### print-download-redeem — POST `/api/v1/admin/print-downloads`

- Eligibility: **QR-PAIR EXCLUDED**. Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied.
- Source: `backend/app/api/v1/printing.py:427`, `redeem_download`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `AccessError, Response, artifact, audit, body.download_token.encode, bytes, context.session.execute, context.session.execute(text('SELECT * FROM public.print_download_grants WHERE id=:id AND granted_to=:uid AND expires_at>clock_timestamp() AND used_at IS NULL'), params).mappings, context.session.execute(text('SELECT * FROM public.print_download_grants WHERE id=:id AND granted_to=:uid AND expires_at>clock_timestamp() AND used_at IS NULL'), params).mappings().one_or_none, context.session.execute(text('UPDATE public.print_download_grants SET used_at=clock_timestamp() WHERE id=:id AND granted_to=:uid AND used_at IS NULL AND expires_at>clock_timestamp() RETURNING id'), params).scalar_one_or_none, fail, gate, hashlib.sha256, hashlib.sha256(body.download_token.encode()).digest, hmac.compare_digest, require_staff, router.post, store, store(request).download, text`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/DownloadRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-237 — POST `/api/v1/admin/print-jobs/{job_id}/qa`

- Eligibility: **QR-PAIR EXCLUDED**. Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied.
- Source: `backend/app/api/v1/printing.py:497`, `record_job_qa`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `AccessError, Decimal, actual.get, all, artifact, body.model_dump, canonical, context.session.execute, context.session.execute(text("SELECT * FROM public.print_artifacts WHERE print_job_id=:id AND deleted_at IS NULL AND format='pdf'"), {'id': job_id}).mappings, context.session.execute(text("SELECT * FROM public.print_artifacts WHERE print_job_id=:id AND deleted_at IS NULL AND format='pdf'"), {'id': job_id}).mappings().one, context.session.execute(text("SELECT commerce_model='single_qr' FROM public.orders WHERE id=:id"), {'id': job['order_id']}).scalar_one, context.session.execute(text('SELECT * FROM public.print_jobs WHERE id=:id FOR UPDATE'), {'id': job_id}).mappings, context.session.execute(text('SELECT * FROM public.print_jobs WHERE id=:id FOR UPDATE'), {'id': job_id}).mappings().one_or_none, context.session.execute(text('SELECT id FROM public.order_logical_items WHERE order_id=:id'), {'id': job['order_id']}).scalars, context.session.execute(text('SELECT id FROM public.order_logical_items WHERE order_id=:id'), {'id': job['order_id']}).scalars().all, expected.get, fail, frozen, len, record, require_staff, router.post, set, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "job_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Job Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/JobQARequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-094 — POST `/api/v1/admin/tag-pairs/{pair_id}/print-qa`

- Eligibility: **QR-PAIR EXCLUDED**. Print job request/grant/redeem/QA paths can inspect pair-bound occurrence/manifest data, export real QR material or approve pair print QA; generic operation denied.
- Source: `backend/app/api/v1/printing.py:608`, `record_print_qa`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations.
- Dependencies/helper calls: `all, body.model_dump, context.session.execute, context.session.execute(text("SELECT id FROM public.tag_pairs WHERE id=:id AND inventory_status IN('generated','qa_pending','qa_passed') AND owner_user_id IS NULL FOR UPDATE"), {'id': pair_id}).first, fail, getattr, record, require_staff, router.post, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "pair_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Pair Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/PrintQARequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-213 — GET `/api/v1/me/orders/{order_id}/print-summary`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/printing.py:675`, `owner_print_summary`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text('SELECT fulfillment_status FROM public.orders WHERE id=:id'), {'id': order_id}).scalar_one, context.session.execute(text('SELECT kind,sum(copies) FROM (SELECT u.tag_type_snapshot AS kind,u.copies FROM public.order_item_qr_uses u JOIN public.order_items i ON i.id=u.order_item_id WHERE i.order_id=:id UNION ALL SELECT i.qr_type_snapshot,s.copies FROM public.order_item_sizes s JOIN public.order_logical_items i ON i.id=s.logical_item_id WHERE i.order_id=:id) counts GROUP BY kind'), {'id': order_id}).all, context.session.execute(text('SELECT status FROM public.print_jobs WHERE order_id=:id ORDER BY job_revision DESC LIMIT 1'), {'id': order_id}).scalar_one_or_none, dict, require_order_owner, require_verified_account, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-061 — GET `/api/v1/me/orders`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/fulfillment.py:78`, `list_orders`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `bounds, page_cursor, paged, router.get, rows`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-062 — GET `/api/v1/me/orders/{order_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch.
- Source: `backend/app/api/v1/fulfillment.py:175`, `get_order`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `cancellation_projection, detail, require_order_owner, router.get, rows, shipping`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-066 — GET `/api/v1/me/orders/{order_id}/shipments`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/fulfillment.py:194`, `list_shipments`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `require_order_owner, router.get, rows`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-232 — GET `/api/v1/admin/orders/ready-to-ship`

- Eligibility: **QR-PAIR EXCLUDED**. Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch.
- Source: `backend/app/api/v1/fulfillment.py:210`, `ready_to_ship`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `bounds, detail, item.update, page_cursor, paged, require_staff, router.get, rows`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "allocated",
              "packed",
              "dispatched",
              "delivered",
              "exception",
              "returned"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### typed-shipment-items — GET `/api/v1/admin/shipments/{shipment_id}/items`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/fulfillment.py:279`, `shipment_items`. Registered and OpenAPI matched; runtime unverified.
- Screen: Orders / Shipments.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `AccessError, require_staff, router.get, rows`.

```json
{
  "parameters": [
    {
      "name": "shipment_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Shipment Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/shipments/{shipment_id}/items", operation_id="typed-shipment-items")
def shipment_items(shipment_id: UUID, context: Authenticated):
    require_staff(context, "operations")
    shipment = rows(context.session, "SELECT o.commerce_model FROM public.shipments s JOIN public.orders o ON o.id=s.order_id WHERE s.id=:id", id=shipment_id)
    if not shipment:
        raise AccessError(404)
    return {"commerce_model": shipment[0]["commerce_model"], "items": rows(context.session,
        "SELECT logical_item_id,print_job_id,packed_qa_confirmed,packed_at FROM public.shipment_items WHERE shipment_id=:id ORDER BY logical_item_id", id=shipment_id)}
```

### API-095 — POST `/api/v1/admin/shipments`

- Eligibility: **QR-PAIR EXCLUDED**. Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch.
- Source: `backend/app/api/v1/fulfillment.py:413`, `create_shipment`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `body.model_dump, command, eligible, fail, len, lock_order, router.post, rows, s.execute, s.execute(text("SELECT commerce_model='single_qr' FROM public.orders WHERE id=:id"), {'id': body.order_id}).scalar_one, set, shipping, str, text, uuid4`.

```json
{
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ShipmentRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-096 — PATCH `/api/v1/admin/shipments/{shipment_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch.
- Source: `backend/app/api/v1/fulfillment.py:490`, `update_shipment`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `AccessError, body.model_dump, command, eligible, fail, lock_order, router.patch, rows, s.execute, s.execute(text("SELECT commerce_model='single_qr' FROM public.orders WHERE id=:id"), {'id': oid}).scalar_one, str, text`.

```json
{
  "parameters": [
    {
      "name": "shipment_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Shipment Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ShipmentUpdate"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-081 — GET `/api/v1/admin/orders/{order_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Mixed order detail/ready-to-ship/shipments call pair/QR-use projections, validate pair membership or mutate packed pair state; no separate permitted generic branch.
- Source: `backend/app/api/v1/fulfillment.py:553`, `operations_order_detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; operations; admin order detail also finance.
- Dependencies/helper calls: `AccessError, cancellation_projection, context.session.execute, detail, require_staff, router.get, rows, shipping, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-080 — GET `/api/v1/admin/orders`

- Eligibility: **QUARANTINED**. Operations role automatically adds sr_fulfillment_eligible to order list. Finance-only branch is not a separate endpoint; mixed-role users select operations. Whole operation quarantined.
- Source: `backend/app/api/v1/fulfillment_queries.py:156`, `orders`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; orders operations/finance; shipment operations.
- Dependencies/helper calls: `bounds, context.session.execute, context.session.execute(text("SELECT 1 FROM public.staff_roles WHERE user_id=:uid AND role='operations' AND revoked_at IS NULL"), {'uid': context.principal.user_id}).scalar_one_or_none, context.session.execute(text(f'WITH selected AS (\n      SELECT o.* FROM public.orders o WHERE public.sr_is_staff(ARRAY[:role])\n      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)\n      AND (CAST(:status AS text) IS NULL OR o.order_status=:status)\n      AND (CAST(:payment AS text) IS NULL OR o.payment_status=:payment)\n      AND (CAST(:fulfillment AS text) IS NULL OR o.fulfillment_status=:fulfillment)\n      AND (CAST(:start AS timestamptz) IS NULL OR o.created_at>=:start)\n      AND (CAST(:end AS timestamptz) IS NULL OR o.created_at<:end)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (o.created_at,o.id){comparison}(:stamp,:ident))\n      ORDER BY o.created_at {direction},o.id {direction} LIMIT :lim)\n      SELECT {ORDER_FIELDS}{extra} FROM selected o ORDER BY o.created_at {direction},o.id {direction}'), {'role': role, 'number': order_number, 'status': order_status, 'payment': payment_status, 'fulfillment': fulfillment_status, 'start': start, 'end': end, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text(f'WITH selected AS (\n      SELECT o.* FROM public.orders o WHERE public.sr_is_staff(ARRAY[:role])\n      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)\n      AND (CAST(:status AS text) IS NULL OR o.order_status=:status)\n      AND (CAST(:payment AS text) IS NULL OR o.payment_status=:payment)\n      AND (CAST(:fulfillment AS text) IS NULL OR o.fulfillment_status=:fulfillment)\n      AND (CAST(:start AS timestamptz) IS NULL OR o.created_at>=:start)\n      AND (CAST(:end AS timestamptz) IS NULL OR o.created_at<:end)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (o.created_at,o.id){comparison}(:stamp,:ident))\n      ORDER BY o.created_at {direction},o.id {direction} LIMIT :lim)\n      SELECT {ORDER_FIELDS}{extra} FROM selected o ORDER BY o.created_at {direction},o.id {direction}'), {'role': role, 'number': order_number, 'status': order_status, 'payment': payment_status, 'fulfillment': fulfillment_status, 'start': start, 'end': end, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, date_range, exact, location, page, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "sort",
      "in": "query",
      "required": false,
      "schema": {
        "enum": [
          "newest",
          "oldest"
        ],
        "type": "string",
        "default": "newest",
        "title": "Sort"
      }
    },
    {
      "name": "order_number",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Order Number"
      }
    },
    {
      "name": "order_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "draft",
              "placed",
              "processing",
              "fulfilled",
              "cancelled"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Order Status"
      }
    },
    {
      "name": "payment_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "awaiting_transfer",
              "proof_submitted",
              "under_review",
              "verified",
              "rejected",
              "refunded"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Payment Status"
      }
    },
    {
      "name": "fulfillment_status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "unallocated",
              "allocated",
              "packed",
              "dispatched",
              "delivered",
              "exception"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Fulfillment Status"
      }
    },
    {
      "name": "created_from",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "Created From"
      }
    },
    {
      "name": "created_before",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "Created Before"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/OrderPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/orders", operation_id="API-080", response_model=OrderPage)
def orders(
    context: Authenticated,
    limit: int = 20,
    cursor: str | None = None,
    sort: Sort = "newest",
    order_number: str | None = None,
    order_status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    fulfillment_status: FulfillmentStatus | None = None,
    created_from: datetime | None = None,
    created_before: datetime | None = None,
):
    operations = (
        context.session.execute(
            text(
                "SELECT 1 FROM public.staff_roles WHERE user_id=:uid AND role='operations' AND revoked_at IS NULL"
            ),
            {"uid": context.principal.user_id},
        ).scalar_one_or_none()
        is not None
    )
    role = "operations" if operations else "finance"
    require_staff(context, role)
    bounds(limit)
    exact(order_number, 40)
    start, end = date_range(created_from, created_before)
    stamp, ident = location(cursor)
    direction, comparison = ("DESC", "<") if sort == "newest" else ("ASC", ">")
    extra = (
        """,(SELECT count(*) FROM public.shipments s WHERE s.order_id=o.id) AS shipment_count,
      (SELECT jsonb_build_object("""
        + SHIP_JSON
        + """) FROM public.shipments s WHERE s.order_id=o.id ORDER BY s.created_at DESC,s.id DESC LIMIT 1) AS latest_shipment,
      public.sr_fulfillment_eligible(o.id) AS fulfillment_eligible"""
        if operations
        else ""
    )
    # Role is a fixed server-chosen value. Recheck inside the representation SQL
    # so revocation cannot leave a cached operations projection available.
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT o.* FROM public.orders o WHERE public.sr_is_staff(ARRAY[:role])
      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)
      AND (CAST(:status AS text) IS NULL OR o.order_status=:status)
      AND (CAST(:payment AS text) IS NULL OR o.payment_status=:payment)
      AND (CAST(:fulfillment AS text) IS NULL OR o.fulfillment_status=:fulfillment)
      AND (CAST(:start AS timestamptz) IS NULL OR o.created_at>=:start)
      AND (CAST(:end AS timestamptz) IS NULL OR o.created_at<:end)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (o.created_at,o.id){comparison}(:stamp,:ident))
      ORDER BY o.created_at {direction},o.id {direction} LIMIT :lim)
      SELECT {ORDER_FIELDS}{extra} FROM selected o ORDER BY o.created_at {direction},o.id {direction}"""),
            {
                "role": role,
                "number": order_number,
                "status": order_status,
                "payment": payment_status,
                "fulfillment": fulfillment_status,
                "start": start,
                "end": end,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(
        data, limit, OperationsOrder if operations else FinanceOrder, "order_id"
    )
```

### API-246 — GET `/api/v1/admin/shipments`

- Eligibility: **QUARANTINED**. Shipment list SHIP_COUNTS reads shipment_pairs and sr_fulfillment_eligible, even without a detail request. Read-only is not pair-free.
- Source: `backend/app/api/v1/fulfillment_queries.py:230`, `shipments`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; orders operations/finance; shipment operations.
- Dependencies/helper calls: `bounds, context.session.execute, context.session.execute(text(f"WITH selected AS (\n      SELECT s.* FROM public.shipments s JOIN public.orders o ON o.id=s.order_id\n      WHERE public.sr_is_staff(ARRAY['operations'])\n      AND (CAST(:oid AS uuid) IS NULL OR s.order_id=:oid)\n      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)\n      AND (CAST(:status AS text) IS NULL OR s.status=:status)\n      AND (CAST(:carrier AS text) IS NULL OR s.carrier=:carrier)\n      AND (CAST(:tracking AS text) IS NULL OR s.tracking_reference=:tracking)\n      AND (CAST(:review AS boolean) IS NULL OR (s.status IN ('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id))=:review)\n      AND (CAST(:start AS timestamptz) IS NULL OR s.created_at>=:start)\n      AND (CAST(:end AS timestamptz) IS NULL OR s.created_at<:end)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (s.created_at,s.id){comparison}(:stamp,:ident))\n      ORDER BY s.created_at {direction},s.id {direction} LIMIT :lim)\n      SELECT {SHIP_FIELDS},{SHIP_COUNTS} FROM selected s JOIN public.orders o ON o.id=s.order_id\n      ORDER BY s.created_at {direction},s.id {direction}"), {'oid': order_id, 'number': order_number, 'status': status, 'carrier': carrier, 'tracking': tracking_reference, 'review': requires_review, 'start': start, 'end': end, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text(f"WITH selected AS (\n      SELECT s.* FROM public.shipments s JOIN public.orders o ON o.id=s.order_id\n      WHERE public.sr_is_staff(ARRAY['operations'])\n      AND (CAST(:oid AS uuid) IS NULL OR s.order_id=:oid)\n      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)\n      AND (CAST(:status AS text) IS NULL OR s.status=:status)\n      AND (CAST(:carrier AS text) IS NULL OR s.carrier=:carrier)\n      AND (CAST(:tracking AS text) IS NULL OR s.tracking_reference=:tracking)\n      AND (CAST(:review AS boolean) IS NULL OR (s.status IN ('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id))=:review)\n      AND (CAST(:start AS timestamptz) IS NULL OR s.created_at>=:start)\n      AND (CAST(:end AS timestamptz) IS NULL OR s.created_at<:end)\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (s.created_at,s.id){comparison}(:stamp,:ident))\n      ORDER BY s.created_at {direction},s.id {direction} LIMIT :lim)\n      SELECT {SHIP_FIELDS},{SHIP_COUNTS} FROM selected s JOIN public.orders o ON o.id=s.order_id\n      ORDER BY s.created_at {direction},s.id {direction}"), {'oid': order_id, 'number': order_number, 'status': status, 'carrier': carrier, 'tracking': tracking_reference, 'review': requires_review, 'start': start, 'end': end, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, date_range, exact, location, page, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "sort",
      "in": "query",
      "required": false,
      "schema": {
        "enum": [
          "newest",
          "oldest"
        ],
        "type": "string",
        "default": "newest",
        "title": "Sort"
      }
    },
    {
      "name": "order_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Order Id"
      }
    },
    {
      "name": "order_number",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Order Number"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "preparing",
              "packed",
              "dispatched",
              "delivered",
              "exception",
              "returned"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    },
    {
      "name": "carrier",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Carrier"
      }
    },
    {
      "name": "tracking_reference",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Tracking Reference"
      }
    },
    {
      "name": "requires_review",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "boolean"
          },
          {
            "type": "null"
          }
        ],
        "title": "Requires Review"
      }
    },
    {
      "name": "created_from",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "Created From"
      }
    },
    {
      "name": "created_before",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "date-time"
          },
          {
            "type": "null"
          }
        ],
        "title": "Created Before"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ShipmentPage"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/shipments", operation_id="API-246", response_model=ShipmentPage)
def shipments(
    context: Authenticated,
    limit: int = 20,
    cursor: str | None = None,
    sort: Sort = "newest",
    order_id: UUID | None = None,
    order_number: str | None = None,
    status: ShipmentStatus | None = None,
    carrier: str | None = None,
    tracking_reference: str | None = None,
    requires_review: bool | None = None,
    created_from: datetime | None = None,
    created_before: datetime | None = None,
):
    require_staff(context, "operations")
    bounds(limit)
    exact(order_number, 40)
    exact(carrier, 80)
    exact(tracking_reference, 150)
    start, end = date_range(created_from, created_before)
    stamp, ident = location(cursor)
    direction, comparison = ("DESC", "<") if sort == "newest" else ("ASC", ">")
    data = (
        context.session.execute(
            text(f"""WITH selected AS (
      SELECT s.* FROM public.shipments s JOIN public.orders o ON o.id=s.order_id
      WHERE public.sr_is_staff(ARRAY['operations'])
      AND (CAST(:oid AS uuid) IS NULL OR s.order_id=:oid)
      AND (CAST(:number AS text) IS NULL OR o.order_number=:number)
      AND (CAST(:status AS text) IS NULL OR s.status=:status)
      AND (CAST(:carrier AS text) IS NULL OR s.carrier=:carrier)
      AND (CAST(:tracking AS text) IS NULL OR s.tracking_reference=:tracking)
      AND (CAST(:review AS boolean) IS NULL OR (s.status IN ('preparing','packed','dispatched') AND NOT public.sr_fulfillment_eligible(o.id))=:review)
      AND (CAST(:start AS timestamptz) IS NULL OR s.created_at>=:start)
      AND (CAST(:end AS timestamptz) IS NULL OR s.created_at<:end)
      AND (CAST(:stamp AS timestamptz) IS NULL OR (s.created_at,s.id){comparison}(:stamp,:ident))
      ORDER BY s.created_at {direction},s.id {direction} LIMIT :lim)
      SELECT {SHIP_FIELDS},{SHIP_COUNTS} FROM selected s JOIN public.orders o ON o.id=s.order_id
      ORDER BY s.created_at {direction},s.id {direction}"""),
            {
                "oid": order_id,
                "number": order_number,
                "status": status,
                "carrier": carrier,
                "tracking": tracking_reference,
                "review": requires_review,
                "start": start,
                "end": end,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    return page(data, limit, ShipmentSummary, "shipment_id")
```

### API-247 — GET `/api/v1/admin/shipments/{shipment_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Legacy shipment detail returns shipment_pairs and pair packing QA/metadata; inspection is prohibited.
- Source: `backend/app/api/v1/fulfillment_queries.py:290`, `shipment`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; orders operations/finance; shipment operations.
- Dependencies/helper calls: `AccessError, PackedPair.model_validate, bounds, context.session.execute, context.session.execute(text(f"SELECT {SHIP_FIELDS},{SHIP_COUNTS},\n      COALESCE((SELECT jsonb_agg(jsonb_build_object('pair_id',sp.pair_id,'packed_qa_confirmed',sp.packed_qa_confirmed,'packed_at',sp.packed_at) ORDER BY sp.pair_id)\n        FROM (SELECT pair_id,packed_qa_confirmed,packed_at FROM public.shipment_pairs WHERE shipment_id=s.id\n          AND (CAST(:after AS uuid) IS NULL OR pair_id>:after) ORDER BY pair_id LIMIT :lim) sp),'[]'::jsonb) AS packed_pairs\n      FROM public.shipments s JOIN public.orders o ON o.id=s.order_id\n      WHERE s.id=:id AND public.sr_is_staff(ARRAY['operations'])"), {'id': shipment_id, 'after': pair_cursor, 'lim': pair_limit + 1}).mappings, context.session.execute(text(f"SELECT {SHIP_FIELDS},{SHIP_COUNTS},\n      COALESCE((SELECT jsonb_agg(jsonb_build_object('pair_id',sp.pair_id,'packed_qa_confirmed',sp.packed_qa_confirmed,'packed_at',sp.packed_at) ORDER BY sp.pair_id)\n        FROM (SELECT pair_id,packed_qa_confirmed,packed_at FROM public.shipment_pairs WHERE shipment_id=s.id\n          AND (CAST(:after AS uuid) IS NULL OR pair_id>:after) ORDER BY pair_id LIMIT :lim) sp),'[]'::jsonb) AS packed_pairs\n      FROM public.shipments s JOIN public.orders o ON o.id=s.order_id\n      WHERE s.id=:id AND public.sr_is_staff(ARRAY['operations'])"), {'id': shipment_id, 'after': pair_cursor, 'lim': pair_limit + 1}).mappings().one_or_none, dict, len, require_staff, result.pop, router.get, str, text`.

```json
{
  "parameters": [
    {
      "name": "shipment_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Shipment Id"
      }
    },
    {
      "name": "pair_limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Pair Limit"
      }
    },
    {
      "name": "pair_cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Pair Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ShipmentDetail"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-015 — POST `/api/v1/public/qr/{token}/finder-messages`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_actions.py:122`, `submit_finder_message`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, ChallengeRequired, api_transaction, body.model_dump, body.turnstile_token.get_secret_value, challenge_binding, datetime.now, encrypt, failure, getattr, hashlib.sha256, hashlib.sha256(json.dumps(body.model_dump(mode='json', exclude={'turnstile_token'}), sort_keys=True, separators=(',', ':')).encode()).hexdigest, hashlib.sha256(proof.encode()).hexdigest, json.dumps, json.dumps(body.model_dump(mode='json', exclude={'turnstile_token'}), sort_keys=True, separators=(',', ':')).encode, no_cache, proof.encode, rate_limit, re.fullmatch, request.headers.get, router.post, session.execute, session.execute(text('SELECT public.sr_public_contact_proof(:proof)'), {'proof': hashlib.sha256(proof.encode()).hexdigest()}).scalar_one, session.execute(text('SELECT public.sr_public_lost_qr_id(:token)'), {'token': token}).scalar_one_or_none, session.execute(text('\n                    SELECT public.sr_public_submit_finder_message(\n                        :token,:name,:email,:phone,:contact_version,:preferred,\n                        :message,:message_version,:consent,:consent_at,\n                        :latitude,:longitude,:accuracy,:source,\n                        :location_consent_at,:location_consent_version,:location_key_version,\n                        :idempotency_key,:request_hash\n                    )\n                    '), {'token': token, 'name': body.finder_name, 'email': email_ciphertext, 'phone': phone_ciphertext, 'contact_version': settings.profile_data_key_version, 'preferred': body.preferred_contact, 'message': message_ciphertext, 'message_version': message_version, 'consent': body.consent_version, 'consent_at': now, 'latitude': location_values[0], 'longitude': location_values[1], 'accuracy': location_values[2], 'source': location_values[3], 'location_consent_at': location_values[4], 'location_consent_version': location_values[5], 'location_key_version': location_values[6], 'idempotency_key': idempotency_key, 'request_hash': request_hash}).scalar_one_or_none, str, text, valid_token, verify`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/FinderMessageRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/FinderReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### API-011 — POST `/api/v1/public/qr/{token}/messages`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_actions.py:122`, `submit_finder_message`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `AccessError, ChallengeRequired, api_transaction, body.model_dump, body.turnstile_token.get_secret_value, challenge_binding, datetime.now, encrypt, failure, getattr, hashlib.sha256, hashlib.sha256(json.dumps(body.model_dump(mode='json', exclude={'turnstile_token'}), sort_keys=True, separators=(',', ':')).encode()).hexdigest, hashlib.sha256(proof.encode()).hexdigest, json.dumps, json.dumps(body.model_dump(mode='json', exclude={'turnstile_token'}), sort_keys=True, separators=(',', ':')).encode, no_cache, proof.encode, rate_limit, re.fullmatch, request.headers.get, router.post, session.execute, session.execute(text('SELECT public.sr_public_contact_proof(:proof)'), {'proof': hashlib.sha256(proof.encode()).hexdigest()}).scalar_one, session.execute(text('SELECT public.sr_public_lost_qr_id(:token)'), {'token': token}).scalar_one_or_none, session.execute(text('\n                    SELECT public.sr_public_submit_finder_message(\n                        :token,:name,:email,:phone,:contact_version,:preferred,\n                        :message,:message_version,:consent,:consent_at,\n                        :latitude,:longitude,:accuracy,:source,\n                        :location_consent_at,:location_consent_version,:location_key_version,\n                        :idempotency_key,:request_hash\n                    )\n                    '), {'token': token, 'name': body.finder_name, 'email': email_ciphertext, 'phone': phone_ciphertext, 'contact_version': settings.profile_data_key_version, 'preferred': body.preferred_contact, 'message': message_ciphertext, 'message_version': message_version, 'consent': body.consent_version, 'consent_at': now, 'latitude': location_values[0], 'longitude': location_values[1], 'accuracy': location_values[2], 'source': location_values[3], 'location_consent_at': location_values[4], 'location_consent_version': location_values[5], 'location_key_version': location_values[6], 'idempotency_key': idempotency_key, 'request_hash': request_hash}).scalar_one_or_none, str, text, valid_token, verify`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/FinderMessageRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/FinderReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### API-012 — POST `/api/v1/public/qr/{token}/contact-reveals`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_contacts.py:222`, `reveal_contact`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `contact_phone, no_cache, router.post`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ContactRevealRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ContactResponse"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### API-013 — POST `/api/v1/public/qr/{token}/whatsapp-link`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_contacts.py:237`, `whatsapp_link`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `contact_phone, no_cache, quote, router.post`.

```json
{
  "parameters": [
    {
      "name": "token",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "title": "Token"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/WhatsAppRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/WhatsAppResponse"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  }
}
```

### API-005 — GET `/api/v1/public/config`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/public_config.py:31`, `get_public_config`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `any, failure, len, list, public.configuration, request.query_params.multi_items, request.stream, response.headers.update, router.get`.

```json
{
  "parameters": [
    {
      "name": "lang",
      "in": "query",
      "required": false,
      "schema": {
        "type": "string",
        "enum": [
          "en",
          "ur"
        ],
        "default": "en"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PublicConfiguration"
          }
        }
      }
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorResponse"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorResponse"
          }
        }
      },
      "description": "Service Unavailable"
    }
  }
}
```

### API-014 — POST `/api/v1/public/abuse-reports`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/abuse_reports.py:130`, `report`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: public; route-specific abuse/configuration/scan checks.
- Dependencies/helper calls: `failure, router.post, submit`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Report"
        }
      }
    },
    "required": true
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__core__abuse_intake__Receipt"
          }
        }
      }
    },
    "4XX": {
      "description": "Client Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "400": {
      "description": "Bad Request",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "409": {
      "description": "Conflict",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "413": {
      "description": "Content Too Large",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "415": {
      "description": "Unsupported Media Type",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "429": {
      "description": "Too Many Requests",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/AbuseErrorEnvelope"
          }
        }
      }
    }
  }
}
```

### API-101 — GET `/api/v1/admin/notification-outbox`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/notification_operations.py:41`, `notifications`. Registered and OpenAPI matched; runtime unverified.
- Screen: Notifications.
- Auth/permissions: JWT + live session; operations, security_admin.
- Dependencies/helper calls: `(SUBJECT + '\n' + HTML).encode, bounds, budget, context.session.execute, context.session.execute(text('SELECT public.sr_notification_metadata(\n      :lim,:stamp,:ident,:status,:id,:attempt_lim,:before,:budget)'), {'lim': limit + 1, 'stamp': stamp, 'ident': ident, 'status': status, 'id': id, 'attempt_lim': attempt_limit, 'before': attempt_before, 'budget': budget(request)}).scalar_one, datetime.fromisoformat, fail, hashlib.sha256, hashlib.sha256((SUBJECT + '\n' + HTML).encode()).hexdigest, page_cursor, paged, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "pending",
              "leased",
              "retry",
              "sent",
              "dead"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    },
    {
      "name": "id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Id"
      }
    },
    {
      "name": "attempt_limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Attempt Limit"
      }
    },
    {
      "name": "attempt_before",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "integer"
          },
          {
            "type": "null"
          }
        ],
        "title": "Attempt Before"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/notification-outbox", operation_id="API-101")
def notifications(
    context: Authenticated,
    request: Request,
    limit: int = 20,
    cursor: str | None = None,
    status: Status | None = None,
    id: UUID | None = None,
    attempt_limit: int = 20,
    attempt_before: int | None = None,
):
    require_staff(context, "operations", "security_admin")
    bounds(limit)
    bounds(attempt_limit)
    if attempt_before is not None and not 1 <= attempt_before <= 2147483647:
        fail(422, "INVALID_ATTEMPT_CURSOR")
    stamp, ident = page_cursor(cursor)
    items = context.session.execute(
        text("""SELECT public.sr_notification_metadata(
      :lim,:stamp,:ident,:status,:id,:attempt_lim,:before,:budget)"""),
        {
            "lim": limit + 1,
            "stamp": stamp,
            "ident": ident,
            "status": status,
            "id": id,
            "attempt_lim": attempt_limit,
            "before": attempt_before,
            "budget": budget(request),
        },
    ).scalar_one()
    # SQL JSON has ISO strings; paging helper expects typed timestamps.
    for item in items:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
    result = paged(items, limit)
    result["current_template"] = {
        "identifier": "finder-message/v1",
        "fingerprint": hashlib.sha256((SUBJECT + "\n" + HTML).encode()).hexdigest(),
        "historical_version": "not_recorded",
        "review": "4.4C_pending",
    }
    return result
```

### API-102 — POST `/api/v1/admin/notification-outbox/{id}/retry`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/notification_operations.py:85`, `retry`. Registered and OpenAPI matched; runtime unverified.
- Screen: Notifications.
- Auth/permissions: JWT + live session; operations, security_admin.
- Dependencies/helper calls: `AccessError, body.model_dump_json, body.model_dump_json().encode, budget, decrypt, encrypt, f'{actor}:{operation}:{key}'.encode, fail, getattr, hashlib.sha256, hashlib.sha256(body.model_dump_json().encode()).hexdigest, hashlib.sha256(f'{actor}:{operation}:{key}'.encode()).hexdigest, json.dumps, json.loads, re.fullmatch, request.headers.get, require_staff, router.post, session.execute, session.execute(text('SELECT public.sr_notification_retry(:id,:expected,:budget,:reason,:request_id)'), {'id': id, 'expected': body.expected_attempt_count, 'budget': budget(request), 'reason': body.reason, 'request_id': getattr(request.state, 'request_id', None)}).scalar_one, session.execute(text('SELECT request_hash,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE'), params).mappings, session.execute(text('SELECT request_hash,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE'), params).mappings().one_or_none, str, text, {'NOT_FOUND': 404, 'STALE_ATTEMPT': 412, 'INVALID_REQUEST': 422}.get`.

```json
{
  "parameters": [
    {
      "name": "id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Retry"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/notification-outbox/{id}/retry", operation_id="API-102", status_code=202
)
def retry(id: UUID, body: Retry, context: Authenticated, request: Request):
    require_staff(context, "operations", "security_admin")
    key = request.headers.get("idempotency-key", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        fail(400, "IDEMPOTENCY_KEY_REQUIRED")
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    actor = context.principal.user_id
    operation = f"notification.retry:{id}"
    reference = hashlib.sha256(f"{actor}:{operation}:{key}".encode()).hexdigest()
    session = context.session
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:reference,0))"),
        {"reference": reference},
    )
    params = {"scope": str(actor), "actor": actor, "op": operation, "key": key}
    old = (
        session.execute(
            text(
                "SELECT request_hash,response_body_ciphertext,response_key_version FROM public.idempotency_records WHERE actor_scope=:scope AND operation=:op AND idempotency_key=:key FOR UPDATE"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    settings = request.app.state.settings
    try:
        if old:
            if old["request_hash"] != digest:
                fail(409, "IDEMPOTENCY_KEY_REUSED")
            return json.loads(
                decrypt(
                    settings,
                    actor,
                    "notification:" + reference,
                    old["response_body_ciphertext"],
                    old["response_key_version"],
                )
            )
        result = session.execute(
            text(
                "SELECT public.sr_notification_retry(:id,:expected,:budget,:reason,:request_id)"
            ),
            {
                "id": id,
                "expected": body.expected_attempt_count,
                "budget": budget(request),
                "reason": body.reason,
                "request_id": getattr(request.state, "request_id", None),
            },
        ).scalar_one()
        if "error" in result:
            fail(
                {"NOT_FOUND": 404, "STALE_ATTEMPT": 412, "INVALID_REQUEST": 422}.get(
                    result["error"], 409
                ),
                result["error"],
            )
        ciphertext, version = encrypt(
            settings, actor, "notification:" + reference, json.dumps(result)
        )
        session.execute(
            text("""INSERT INTO public.idempotency_records(actor_scope,actor_user_id,operation,idempotency_key,request_hash,state,response_status,response_body_ciphertext,response_key_version,expires_at)
        VALUES(:scope,:actor,:op,:key,:hash,'completed',202,:cipher,:version,now()+interval '1 day')"""),
            {**params, "hash": digest, "cipher": ciphertext, "version": version},
        )
        return result
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
```

### API-050 — GET `/api/v1/me/finder-messages`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/messages.py:123`, `list_finder_messages`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `HTTPException, Query, _cursor, _parse_cursor, context.session.execute, context.session.execute(text("\n                SELECT m.id,m.qr_id,m.finder_name,m.status,m.submitted_at,q.tag_type,\n                       lp.item_label AS qr_label,\n                       (SELECT o.status FROM public.notification_outbox o\n                        WHERE o.aggregate_type='finder_message' AND o.aggregate_id=m.id\n                          AND o.event_type='finder_message.created' AND o.recipient_user_id=:uid\n                        ORDER BY o.created_at DESC,o.id DESC LIMIT 1) AS notification_status\n                FROM public.finder_messages m\n                JOIN public.qr_codes q ON q.id=m.qr_id\n                LEFT JOIN public.lost_item_profiles lp ON lp.qr_id=m.qr_id\n                WHERE m.recipient_owner_user_id=:uid\n                  AND m.deleted_at IS NULL AND m.status<>'deleted'\n                  AND (CAST(:cursor AS timestamptz) IS NULL OR (m.submitted_at,m.id) < (CAST(:cursor AS timestamptz),CAST(:cursor_id AS uuid)))\n                  AND (CAST(:status AS text) IS NULL OR m.status=CAST(:status AS text))\n                  AND (CAST(:qr_id AS uuid) IS NULL OR m.qr_id=CAST(:qr_id AS uuid))\n                ORDER BY m.submitted_at DESC,m.id DESC\n                LIMIT :limit\n                "), {'uid': context.principal.user_id, 'cursor': cursor_ts, 'cursor_id': cursor_id, 'status': status, 'qr_id': qr_id, 'limit': limit + 1}).mappings, len, list, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "maxLength": 256
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 25,
        "title": "Limit"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "pattern": "^(new|viewed|archived|flagged)$"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    },
    {
      "name": "qr_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Qr Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-051 — GET `/api/v1/me/finder-messages/{message_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/messages.py:185`, `get_finder_message`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `HTTPException, Settings, _decrypt_message, _message_or_404, context.session.execute, context.session.execute(text('\n            SELECT latitude_ciphertext,longitude_ciphertext,accuracy_m,\n                   consent_at,key_version\n            FROM public.finder_message_locations\n            WHERE finder_message_id=:id\n            '), {'id': message_id}).mappings, context.session.execute(text('\n            SELECT latitude_ciphertext,longitude_ciphertext,accuracy_m,\n                   consent_at,key_version\n            FROM public.finder_message_locations\n            WHERE finder_message_id=:id\n            '), {'id': message_id}).mappings().one_or_none, context.session.info.get, decrypt, float, hasattr, math.isfinite, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "message_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Message Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-052 — PATCH `/api/v1/me/finder-messages/{message_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/messages.py:270`, `update_finder_message`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `HTTPException, context.session.execute, context.session.execute(text("\n            UPDATE public.finder_messages\n            SET status=:status\n            WHERE id=:id AND recipient_owner_user_id=:uid AND deleted_at IS NULL AND status<>'deleted'\n            RETURNING id,status\n            "), {'id': message_id, 'uid': context.principal.user_id, 'status': body.status}).mappings, context.session.execute(text("\n            UPDATE public.finder_messages\n            SET status=:status\n            WHERE id=:id AND recipient_owner_user_id=:uid AND deleted_at IS NULL AND status<>'deleted'\n            RETURNING id,status\n            "), {'id': message_id, 'uid': context.principal.user_id, 'status': body.status}).mappings().one_or_none, dict, require_message_recipient, router.patch, text`.

```json
{
  "parameters": [
    {
      "name": "message_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Message Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/MessageUpdate"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-053 — DELETE `/api/v1/me/finder-messages/{message_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/messages.py:295`, `delete_finder_message`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, require_message_recipient, router.delete, text`.

```json
{
  "parameters": [
    {
      "name": "message_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Message Id"
      }
    }
  ],
  "responses": {
    "204": {
      "description": "Successful Response"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-238 — GET `/api/v1/admin/finance/sheet-sync`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/retention.py:85`, `list_sheet_sync`. Registered and OpenAPI matched; runtime unverified.
- Screen: Finance Sheet Sync / Storage.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `Query, _encode_cursor, _parse_cursor, context.session.execute, context.session.execute(text("\n                SELECT s.id, s.order_id, s.sheet_row_key, s.last_export_version,\n                       CASE WHEN EXISTS(SELECT 1 FROM public.durable_jobs d\n                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status='dead')\n                         AND NOT EXISTS(SELECT 1 FROM public.durable_jobs d\n                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status IN ('pending','retry','leased'))\n                         AND s.status<>'synced' THEN 'failed' ELSE s.status END AS status,\n                       s.attempt_count, s.last_error_code, s.last_synced_at, s.updated_at,\n                       o.payment_status, o.fulfillment_status, o.currency_code, o.total_pkr\n                FROM public.finance_sheet_sync s\n                JOIN public.orders o ON o.id=s.order_id\n                WHERE (CAST(:cursor_ts AS timestamptz) IS NULL OR (s.updated_at < CAST(:cursor_ts AS timestamptz) OR (s.updated_at = CAST(:cursor_ts AS timestamptz) AND s.id < CAST(:cursor_id AS uuid))))\n                ORDER BY s.updated_at DESC, s.id DESC\n                LIMIT :fetch_limit\n                "), {'cursor_ts': cursor_ts, 'cursor_id': cursor_id, 'fetch_limit': fetch_limit}).mappings, len, list, require_staff, router.get, str, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 50,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/finance/sheet-sync", operation_id="API-238")
def list_sheet_sync(
    context: Authenticated,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
):
    require_staff(context, "finance", "security_admin", "superadmin")
    cursor_ts, cursor_id = _parse_cursor(cursor)
    fetch_limit = limit + 1
    rows = list(
        context.session.execute(
            text(
                """
                SELECT s.id, s.order_id, s.sheet_row_key, s.last_export_version,
                       CASE WHEN EXISTS(SELECT 1 FROM public.durable_jobs d
                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status='dead')
                         AND NOT EXISTS(SELECT 1 FROM public.durable_jobs d
                         WHERE d.order_id=s.order_id AND d.job_kind='finance.sync' AND d.status IN ('pending','retry','leased'))
                         AND s.status<>'synced' THEN 'failed' ELSE s.status END AS status,
                       s.attempt_count, s.last_error_code, s.last_synced_at, s.updated_at,
                       o.payment_status, o.fulfillment_status, o.currency_code, o.total_pkr
                FROM public.finance_sheet_sync s
                JOIN public.orders o ON o.id=s.order_id
                WHERE (CAST(:cursor_ts AS timestamptz) IS NULL OR (s.updated_at < CAST(:cursor_ts AS timestamptz) OR (s.updated_at = CAST(:cursor_ts AS timestamptz) AND s.id < CAST(:cursor_id AS uuid))))
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT :fetch_limit
                """
            ),
            {
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "fetch_limit": fetch_limit,
            },
        ).mappings()
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [
        {
            "id": row["id"],
            "order_id": row["order_id"],
            "sheet_row_key": row["sheet_row_key"],
            "last_export_version": row["last_export_version"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "last_error_code": row["last_error_code"],
            "last_synced_at": row["last_synced_at"],
            "updated_at": row["updated_at"],
            "payment_status": row["payment_status"],
            "fulfillment_status": row["fulfillment_status"],
            "currency_code": row["currency_code"],
            "total_pkr": str(row["total_pkr"]),
        }
        for row in page_rows
    ]
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last["updated_at"], last["id"])
    return {"items": items, "next_cursor": next_cursor}
```

### API-239 — POST `/api/v1/admin/finance/sheet-sync/{sync_id}/retry`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/retention.py:147`, `retry_sheet_sync`. Registered and OpenAPI matched; runtime unverified.
- Screen: Finance Sheet Sync / Storage.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `HTTPException, _audit, context.session.execute, context.session.execute(text("\n            UPDATE public.finance_sheet_sync\n            SET status='retry', last_error_code=NULL, updated_at=clock_timestamp()\n            WHERE id=:id AND (status IN ('failed','retry') OR (status<>'synced' AND\n              EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=finance_sheet_sync.order_id\n                AND d.job_kind='finance.sync' AND d.status='dead')))\n            RETURNING id, order_id, status\n            "), {'id': sync_id}).mappings, context.session.execute(text("\n            UPDATE public.finance_sheet_sync\n            SET status='retry', last_error_code=NULL, updated_at=clock_timestamp()\n            WHERE id=:id AND (status IN ('failed','retry') OR (status<>'synced' AND\n              EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=finance_sheet_sync.order_id\n                AND d.job_kind='finance.sync' AND d.status='dead')))\n            RETURNING id, order_id, status\n            "), {'id': sync_id}).mappings().one_or_none, context.session.execute(text('SELECT id, status FROM public.finance_sheet_sync WHERE id=:id'), {'id': sync_id}).mappings, context.session.execute(text('SELECT id, status FROM public.finance_sheet_sync WHERE id=:id'), {'id': sync_id}).mappings().one_or_none, context.session.execute(text('SELECT status FROM public.finance_sheet_sync WHERE id=:id FOR UPDATE'), {'id': sync_id}).scalar_one_or_none, dict, require_staff, router.post, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "sync_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Sync Id"
      }
    }
  ],
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/finance/sheet-sync/{sync_id}/retry",
    operation_id="API-239",
    status_code=202,
)
def retry_sheet_sync(sync_id: UUID, context: Authenticated):
    require_staff(context, "finance", "security_admin", "superadmin")
    previous_status = context.session.execute(
        text("SELECT status FROM public.finance_sheet_sync WHERE id=:id FOR UPDATE"),
        {"id": sync_id},
    ).scalar_one_or_none()
    updated = (
        context.session.execute(
            text(
                """
            UPDATE public.finance_sheet_sync
            SET status='retry', last_error_code=NULL, updated_at=clock_timestamp()
            WHERE id=:id AND (status IN ('failed','retry') OR (status<>'synced' AND
              EXISTS(SELECT 1 FROM public.durable_jobs d WHERE d.order_id=finance_sheet_sync.order_id
                AND d.job_kind='finance.sync' AND d.status='dead')))
            RETURNING id, order_id, status
            """
            ),
            {"id": sync_id},
        )
        .mappings()
        .one_or_none()
    )
    if updated is None:
        existing = (
            context.session.execute(
                text("SELECT id, status FROM public.finance_sheet_sync WHERE id=:id"),
                {"id": sync_id},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Sheet sync in status '{existing['status']}' cannot be retried",
            )
        raise HTTPException(status_code=404, detail="Eligible Sheet sync not found")

    order_id = updated["order_id"]
    context.session.execute(
        text(
            """
            INSERT INTO public.durable_jobs
              (job_kind, aggregate_type, aggregate_id, order_id, status, idempotency_key)
            SELECT 'finance.sync', 'order', :order, :order, 'pending', :key
            WHERE NOT EXISTS (
              SELECT 1 FROM public.durable_jobs WHERE order_id=:order
              AND job_kind='finance.sync' AND status IN ('pending','retry','leased')
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "order": order_id,
            "key": f"payment.finance:{order_id}:{uuid4().hex}",
        },
    )
    _audit(
        context,
        "finance.sheet_sync_retry",
        "finance_sheet_sync",
        sync_id,
        {"from_status": previous_status, "to_status": "retry"},
    )
    return dict(updated)
```

### API-242 — GET `/api/v1/admin/storage/artifacts`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/retention.py:220`, `list_private_artifacts`. Registered and OpenAPI matched; runtime unverified.
- Screen: Finance Sheet Sync / Storage.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `Query, context.session.execute, context.session.execute(text("\n            SELECT a.id, 'print_artifact' AS resource_type, a.print_job_id AS owner_id,\n                   a.bucket, a.object_key, a.format, a.sha256_hex, a.size_bytes,\n                   a.retention_until, a.deletion_hold_reason, a.deleted_at,\n                   (a.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('print_artifact',a.id)) AS on_hold,\n                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)\n                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='print_artifact' AND d.aggregate_id=a.id\n                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1) AS cleanup_job\n            FROM public.print_artifacts a\n            JOIN public.print_jobs j ON j.id=a.print_job_id\n            WHERE (CAST(:order_id AS uuid) IS NULL OR j.order_id=CAST(:order_id AS uuid))\n              AND (CAST(:job_id AS uuid) IS NULL OR j.id=CAST(:job_id AS uuid))\n              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='print_artifact')\n            UNION ALL\n            SELECT e.id, 'payment_evidence', e.attempt_id,\n                   e.bucket, e.object_key, e.content_type,\n                   e.sha256_hex, e.bytes_size, e.retention_until, e.deletion_hold_reason, e.deleted_at,\n                   (e.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('payment_evidence',e.id)),\n                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)\n                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='payment_evidence' AND d.aggregate_id=e.id\n                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1)\n            FROM public.payment_evidence e\n            JOIN public.payment_attempts p ON p.id=e.attempt_id\n            WHERE (CAST(:order_id AS uuid) IS NULL OR p.order_id=CAST(:order_id AS uuid))\n              AND (CAST(:job_id AS uuid) IS NULL)\n              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='payment_evidence')\n            ORDER BY deleted_at NULLS FIRST, retention_until NULLS LAST, id DESC\n            LIMIT :limit\n            "), {'order_id': order_id, 'job_id': job_id, 'resource_type': resource_type, 'limit': limit}).mappings, dict, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Order Id"
      }
    },
    {
      "name": "job_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Job Id"
      }
    },
    {
      "name": "resource_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Resource Type"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 50,
        "title": "Limit"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/storage/artifacts", operation_id="API-242")
def list_private_artifacts(
    context: Authenticated,
    order_id: UUID | None = None,
    job_id: UUID | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    require_staff(context, "operations", "finance", "security_admin", "superadmin")
    rows = context.session.execute(
        text(
            """
            SELECT a.id, 'print_artifact' AS resource_type, a.print_job_id AS owner_id,
                   a.bucket, a.object_key, a.format, a.sha256_hex, a.size_bytes,
                   a.retention_until, a.deletion_hold_reason, a.deleted_at,
                   (a.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('print_artifact',a.id)) AS on_hold,
                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)
                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='print_artifact' AND d.aggregate_id=a.id
                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1) AS cleanup_job
            FROM public.print_artifacts a
            JOIN public.print_jobs j ON j.id=a.print_job_id
            WHERE (CAST(:order_id AS uuid) IS NULL OR j.order_id=CAST(:order_id AS uuid))
              AND (CAST(:job_id AS uuid) IS NULL OR j.id=CAST(:job_id AS uuid))
              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='print_artifact')
            UNION ALL
            SELECT e.id, 'payment_evidence', e.attempt_id,
                   e.bucket, e.object_key, e.content_type,
                   e.sha256_hex, e.bytes_size, e.retention_until, e.deletion_hold_reason, e.deleted_at,
                   (e.deletion_hold_reason IS NOT NULL OR public.sr_retention_held('payment_evidence',e.id)),
                   (SELECT jsonb_build_object('id',d.id,'status',d.status,'attempt_count',d.attempt_count,'last_error_code',d.last_error_code)
                    FROM public.durable_jobs d WHERE d.job_kind='retention.cleanup' AND d.aggregate_type='payment_evidence' AND d.aggregate_id=e.id
                    ORDER BY d.created_at DESC,d.id DESC LIMIT 1)
            FROM public.payment_evidence e
            JOIN public.payment_attempts p ON p.id=e.attempt_id
            WHERE (CAST(:order_id AS uuid) IS NULL OR p.order_id=CAST(:order_id AS uuid))
              AND (CAST(:job_id AS uuid) IS NULL)
              AND (CAST(:resource_type AS text) IS NULL OR CAST(:resource_type AS text)='payment_evidence')
            ORDER BY deleted_at NULLS FIRST, retention_until NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {
            "order_id": order_id,
            "job_id": job_id,
            "resource_type": resource_type,
            "limit": limit,
        },
    ).mappings()
    return {"items": [dict(row) for row in rows]}
```

### API-245 — POST `/api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry`

- Eligibility: **QUARANTINED**. sr_retention_retry revives cleanup -> finance_retention worker -> sr_retention_prepare checks order_pair_units/support-case pair references before private object deletion.
- Source: `backend/app/api/v1/retention.py:271`, `retry_artifact_cleanup`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `HTTPException, context.session.execute, context.session.execute(text('SELECT public.sr_retention_retry(:id,:reason)'), {'id': artifact_id, 'reason': body.reason_code}).scalar_one_or_none, require_staff, router.post, text`.

```json
{
  "parameters": [
    {
      "name": "artifact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Artifact Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/RetentionHoldRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/storage/artifacts/{artifact_id}/cleanup-retry",
    operation_id="API-245",
    status_code=202,
)
def retry_artifact_cleanup(
    artifact_id: UUID, body: RetentionHoldRequest, context: Authenticated
):
    require_staff(context, "security_admin", "superadmin")
    job_id = context.session.execute(
        text("SELECT public.sr_retention_retry(:id,:reason)"),
        {"id": artifact_id, "reason": body.reason_code},
    ).scalar_one_or_none()
    if job_id is None:
        raise HTTPException(status_code=404, detail="Cleanup job not found")
    return {"job_id": job_id}
```

### API-243 — POST `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds`

- Eligibility: **QUARANTINED**. Generic hold can target finder_message -> retention_holds INSERT trigger sr_support_finder_hold_lock reads qr_codes.pair_id/order_pair_units and locks tag_pairs.
- Source: `backend/app/api/v1/retention.py:289`, `place_retention_hold`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `HTTPException, _audit, _insert_hold, context.session.execute, context.session.execute(text("\n            SELECT 'print_artifact' AS res_type, deleted_at FROM public.print_artifacts WHERE id=:id\n            UNION ALL\n            SELECT 'payment_evidence' AS res_type, deleted_at FROM public.payment_evidence WHERE id=:id\n            UNION ALL\n            SELECT 'order' AS res_type, NULL::timestamptz AS deleted_at FROM public.orders WHERE id=:id\n            UNION ALL\n            SELECT 'finder_message' AS res_type, deleted_at FROM public.finder_messages WHERE id=:id\n            "), {'id': artifact_id}).mappings, context.session.execute(text("\n            SELECT 'print_artifact' AS res_type, deleted_at FROM public.print_artifacts WHERE id=:id\n            UNION ALL\n            SELECT 'payment_evidence' AS res_type, deleted_at FROM public.payment_evidence WHERE id=:id\n            UNION ALL\n            SELECT 'order' AS res_type, NULL::timestamptz AS deleted_at FROM public.orders WHERE id=:id\n            UNION ALL\n            SELECT 'finder_message' AS res_type, deleted_at FROM public.finder_messages WHERE id=:id\n            "), {'id': artifact_id}).mappings().one_or_none, context.session.execute(text('\n            SELECT id FROM public.retention_holds\n            WHERE resource_id=:resource AND reason_code=:reason AND released_at IS NULL\n            '), {'resource': artifact_id, 'reason': body.reason_code}).scalar_one_or_none, require_staff, router.post, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "artifact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Artifact Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/RetentionHoldRequest"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/storage/artifacts/{artifact_id}/retention-holds",
    operation_id="API-243",
    status_code=201,
)
def place_retention_hold(
    artifact_id: UUID, body: RetentionHoldRequest, context: Authenticated
):
    require_staff(context, "security_admin", "superadmin")
    context.session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text),560056))"
        ),
        {"id": artifact_id},
    )
    # Check if resource exists and is active (not deleted)
    resource_info = (
        context.session.execute(
            text(
                """
            SELECT 'print_artifact' AS res_type, deleted_at FROM public.print_artifacts WHERE id=:id
            UNION ALL
            SELECT 'payment_evidence' AS res_type, deleted_at FROM public.payment_evidence WHERE id=:id
            UNION ALL
            SELECT 'order' AS res_type, NULL::timestamptz AS deleted_at FROM public.orders WHERE id=:id
            UNION ALL
            SELECT 'finder_message' AS res_type, deleted_at FROM public.finder_messages WHERE id=:id
            """
            ),
            {"id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )

    if resource_info is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if resource_info["deleted_at"] is not None:
        raise HTTPException(
            status_code=409, detail="Artifact already deleted; cannot place hold"
        )

    resource_type = resource_info["res_type"]

    # Check for existing active hold with the same reason (idempotent)
    existing_hold = context.session.execute(
        text(
            """
            SELECT id FROM public.retention_holds
            WHERE resource_id=:resource AND reason_code=:reason AND released_at IS NULL
            """
        ),
        {"resource": artifact_id, "reason": body.reason_code},
    ).scalar_one_or_none()
    if existing_hold is not None:
        return {
            "hold_id": existing_hold,
            "resource_type": resource_type,
            "resource_id": artifact_id,
            "reason_code": body.reason_code,
        }

    hold_id = uuid4()
    _insert_hold(
        context,
        {
            "id": hold_id,
            "type": resource_type,
            "resource": artifact_id,
            "reason": body.reason_code,
            "actor": context.principal.user_id,
        },
    )
    if resource_type == "print_artifact":
        context.session.execute(
            text(
                "UPDATE public.print_artifacts SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": body.reason_code},
        )
    elif resource_type == "payment_evidence":
        context.session.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": body.reason_code},
        )
    _audit(
        context,
        "storage.retention_hold_placed",
        resource_type,
        artifact_id,
        {"reason_code": body.reason_code},
    )
    return {
        "hold_id": hold_id,
        "resource_type": resource_type,
        "resource_id": artifact_id,
        "reason_code": body.reason_code,
    }
```

### API-244 — DELETE `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds`

- Eligibility: **QUARANTINED**. Release can clear a finder-message/artifact/order hold, enabling existing cleanup admission whose sr_retention_prepare checks pair-linked disputes. No separately scoped release endpoint proves a pair-free background chain.
- Source: `backend/app/api/v1/retention.py:391`, `release_retention_hold`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; sheet finance/security_admin/superadmin; metadata also operations; hold/cleanup security_admin/superadmin.
- Dependencies/helper calls: `HTTPException, _audit, context.session.execute, context.session.execute(text('\n                UPDATE public.retention_holds\n                SET released_by=:actor, released_at=clock_timestamp()\n                WHERE resource_id=:resource AND released_at IS NULL\n                RETURNING id, resource_type, reason_code\n                '), {'resource': artifact_id, 'actor': context.principal.user_id}).mappings, context.session.execute(text('\n            SELECT reason_code FROM public.retention_holds\n            WHERE resource_id=:resource AND released_at IS NULL\n            ORDER BY created_at DESC\n            LIMIT 1\n            '), {'resource': artifact_id}).scalar_one_or_none, list, require_staff, router.delete, text`.

```json
{
  "parameters": [
    {
      "name": "artifact_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Artifact Id"
      }
    }
  ],
  "responses": {
    "204": {
      "description": "Successful Response"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.delete(
    "/admin/storage/artifacts/{artifact_id}/retention-holds",
    operation_id="API-244",
    status_code=204,
)
def release_retention_hold(artifact_id: UUID, context: Authenticated):
    require_staff(context, "security_admin", "superadmin")
    context.session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text),560056))"
        ),
        {"id": artifact_id},
    )
    released_rows = list(
        context.session.execute(
            text(
                """
                UPDATE public.retention_holds
                SET released_by=:actor, released_at=clock_timestamp()
                WHERE resource_id=:resource AND released_at IS NULL
                RETURNING id, resource_type, reason_code
                """
            ),
            {"resource": artifact_id, "actor": context.principal.user_id},
        ).mappings()
    )
    if not released_rows:
        raise HTTPException(status_code=404, detail="Active retention hold not found")
    resource_type = released_rows[0]["resource_type"]

    remaining_hold = context.session.execute(
        text(
            """
            SELECT reason_code FROM public.retention_holds
            WHERE resource_id=:resource AND released_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"resource": artifact_id},
    ).scalar_one_or_none()

    if resource_type == "print_artifact":
        context.session.execute(
            text(
                "UPDATE public.print_artifacts SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": remaining_hold},
        )
    elif resource_type == "payment_evidence":
        context.session.execute(
            text(
                "UPDATE public.payment_evidence SET deletion_hold_reason=:reason WHERE id=:id"
            ),
            {"id": artifact_id, "reason": remaining_hold},
        )
    _audit(
        context,
        "storage.retention_hold_released",
        resource_type,
        artifact_id,
        {"reason_code": released_rows[0]["reason_code"]},
    )
```

### API-097 — GET `/api/v1/admin/support-cases`

- Eligibility: **QUARANTINED**. case_id detail branch invokes sr_support_context -> order_pair_units/qr_codes/holds. No separate metadata-only backend endpoint for this mixed operation.
- Source: `backend/app/api/v1/support_cases.py:141`, `cases`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; support; assigned-case restrictions.
- Dependencies/helper calls: `AccessError, bounds, case_clause, case_policy, context.session.execute, context.session.execute(text('SELECT id,case_revision,actor_staff_id,event_type,from_status,to_status,priority,created_at,note_ciphertext,note_key_version\n                FROM public.support_case_events WHERE case_id=:id AND (CAST(:before AS integer) IS NULL OR case_revision<:before)\n                ORDER BY case_revision DESC LIMIT :lim'), {'id': case_id, 'before': before_revision, 'lim': event_limit + 1}).mappings, context.session.execute(text('SELECT id,case_revision,actor_staff_id,event_type,from_status,to_status,priority,created_at,note_ciphertext,note_key_version\n                FROM public.support_case_events WHERE case_id=:id AND (CAST(:before AS integer) IS NULL OR case_revision<:before)\n                ORDER BY case_revision DESC LIMIT :lim'), {'id': case_id, 'before': before_revision, 'lim': event_limit + 1}).mappings().all, context.session.execute(text('SELECT pair_id,order_id,opened_by_user_id,description_ciphertext,description_key_version FROM public.support_cases WHERE id=:id AND assigned_staff_id=:uid'), {'id': case_id, 'uid': uid}).mappings, context.session.execute(text('SELECT pair_id,order_id,opened_by_user_id,description_ciphertext,description_key_version FROM public.support_cases WHERE id=:id AND assigned_staff_id=:uid'), {'id': case_id, 'uid': uid}).mappings().one_or_none, context.session.execute(text('SELECT public.sr_support_context(:id)'), {'id': case_id}).scalar_one, context.session.execute(text(f"SELECT {FIELDS} FROM public.support_cases\n      WHERE (assigned_staff_id IS NULL OR assigned_staff_id=:uid) {policy_clause}\n      AND (CAST(:id AS uuid) IS NULL OR id=:id) AND (CAST(:kind AS text) IS NULL OR case_type=:kind)\n      AND (CAST(:status AS text) IS NULL OR status=:status) AND (CAST(:priority AS text) IS NULL OR priority=:priority)\n      AND (:queue='all' OR (:queue='mine' AND assigned_staff_id=:uid) OR (:queue='unassigned' AND assigned_staff_id IS NULL))\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident))\n      ORDER BY created_at DESC,id DESC LIMIT :lim"), {'uid': uid, 'id': case_id, 'kind': case_type, 'status': status, 'priority': priority, 'queue': queue, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings, context.session.execute(text(f"SELECT {FIELDS} FROM public.support_cases\n      WHERE (assigned_staff_id IS NULL OR assigned_staff_id=:uid) {policy_clause}\n      AND (CAST(:id AS uuid) IS NULL OR id=:id) AND (CAST(:kind AS text) IS NULL OR case_type=:kind)\n      AND (CAST(:status AS text) IS NULL OR status=:status) AND (CAST(:priority AS text) IS NULL OR priority=:priority)\n      AND (:queue='all' OR (:queue='mine' AND assigned_staff_id=:uid) OR (:queue='unassigned' AND assigned_staff_id IS NULL))\n      AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident))\n      ORDER BY created_at DESC,id DESC LIMIT :lim"), {'uid': uid, 'id': case_id, 'kind': case_type, 'status': status, 'priority': priority, 'queue': queue, 'stamp': stamp, 'ident': ident, 'lim': limit + 1}).mappings().all, decrypt, event.items, fail, getattr, history.append, item.update, items.append, len, page_cursor, paged, require_staff, router.get, row.items, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    },
    {
      "name": "case_id",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "format": "uuid"
          },
          {
            "type": "null"
          }
        ],
        "title": "Case Id"
      }
    },
    {
      "name": "case_type",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "activation",
              "lost_tag",
              "payment",
              "privacy",
              "ownership_dispute",
              "other"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Case Type"
      }
    },
    {
      "name": "status",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "open",
              "investigating",
              "resolved",
              "closed"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Status"
      }
    },
    {
      "name": "priority",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "low",
              "normal",
              "high",
              "urgent"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Priority"
      }
    },
    {
      "name": "queue",
      "in": "query",
      "required": false,
      "schema": {
        "enum": [
          "all",
          "mine",
          "unassigned"
        ],
        "type": "string",
        "default": "all",
        "title": "Queue"
      }
    },
    {
      "name": "event_limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Event Limit"
      }
    },
    {
      "name": "before_revision",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "integer"
          },
          {
            "type": "null"
          }
        ],
        "title": "Before Revision"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/support-cases", operation_id="API-097")
def cases(
    context: Authenticated,
    request: Request,
    limit: int = 20,
    cursor: str | None = None,
    case_id: UUID | None = None,
    case_type: CaseType | None = None,
    status: CaseStatus | None = None,
    priority: Priority | None = None,
    queue: Literal["all", "mine", "unassigned"] = "all",
    event_limit: int = 20,
    before_revision: int | None = None,
):
    require_staff(context, "support")
    bounds(limit)
    bounds(event_limit)
    if before_revision is not None and not 1 <= before_revision <= 2147483647:
        fail(422, "INVALID_EVENT_CURSOR")
    stamp, ident = page_cursor(cursor)
    uid = context.principal.user_id
    from app.db.abuse_intake import case_clause, case_policy

    policy_clause = case_clause(context.session)
    rows = (
        context.session.execute(
            text(f"""SELECT {FIELDS} FROM public.support_cases
      WHERE (assigned_staff_id IS NULL OR assigned_staff_id=:uid) {policy_clause}
      AND (CAST(:id AS uuid) IS NULL OR id=:id) AND (CAST(:kind AS text) IS NULL OR case_type=:kind)
      AND (CAST(:status AS text) IS NULL OR status=:status) AND (CAST(:priority AS text) IS NULL OR priority=:priority)
      AND (:queue='all' OR (:queue='mine' AND assigned_staff_id=:uid) OR (:queue='unassigned' AND assigned_staff_id IS NULL))
      AND (CAST(:stamp AS timestamptz) IS NULL OR (created_at,id)<(:stamp,:ident))
      ORDER BY created_at DESC,id DESC LIMIT :lim"""),
            {
                "uid": uid,
                "id": case_id,
                "kind": case_type,
                "status": status,
                "priority": priority,
                "queue": queue,
                "stamp": stamp,
                "ident": ident,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    if case_id and not rows:
        case_policy(context.session, case_id)  # policy-blocked owned scope is503
        raise AccessError(404)
    items = []
    for row in rows:
        abuse_policy = case_policy(context.session, row["id"])
        item = {
            k: v
            for k, v in row.items()
            if k not in ["assigned_staff_id", "description_format"]
        }
        own = row["assigned_staff_id"] == uid
        item.update(
            assigned_to_me=own,
            can_claim=row["assigned_staff_id"] is None
            and row["status"] in ["open", "investigating"],
            requires_escalation=row["case_type"]
            in ["payment", "privacy", "ownership_dispute"]
            or abuse_policy is not None,
        )
        if case_id and own:
            private = (
                context.session.execute(
                    text(
                        "SELECT pair_id,order_id,opened_by_user_id,description_ciphertext,description_key_version FROM public.support_cases WHERE id=:id AND assigned_staff_id=:uid"
                    ),
                    {"id": case_id, "uid": uid},
                )
                .mappings()
                .one_or_none()
            )
            if private is None:
                raise AccessError(404)
            scope = context.session.execute(
                text("SELECT public.sr_support_context(:id)"), {"id": case_id}
            ).scalar_one()
            if scope is None:
                raise AccessError(404)
            item.update(
                {k: private[k] for k in ["pair_id", "order_id", "opened_by_user_id"]}
            )
            item.update(scope)
            item["legacy_description_restricted"] = (
                row["description_format"] == 0
                and private["description_ciphertext"] is not None
            )
            item["description"] = None
            try:
                if (
                    row["description_format"] == 1
                    and private["description_ciphertext"] is not None
                ):
                    item["description"] = decrypt(
                        request.app.state.settings,
                        case_id,
                        "support_description",
                        private["description_ciphertext"],
                        private["description_key_version"],
                    )
                events = (
                    context.session.execute(
                        text("""SELECT id,case_revision,actor_staff_id,event_type,from_status,to_status,priority,created_at,note_ciphertext,note_key_version
                FROM public.support_case_events WHERE case_id=:id AND (CAST(:before AS integer) IS NULL OR case_revision<:before)
                ORDER BY case_revision DESC LIMIT :lim"""),
                        {
                            "id": case_id,
                            "before": before_revision,
                            "lim": event_limit + 1,
                        },
                    )
                    .mappings()
                    .all()
                )
                history = []
                for event in events[:event_limit]:
                    entry = {
                        k: v
                        for k, v in event.items()
                        if k not in ["note_ciphertext", "note_key_version"]
                    }
                    entry["note"] = (
                        decrypt(
                            request.app.state.settings,
                            event["id"],
                            "support_note",
                            event["note_ciphertext"],
                            event["note_key_version"],
                        )
                        if event["note_ciphertext"] is not None
                        else None
                    )
                    history.append(entry)
            except ProfileCryptoUnavailable:
                raise AccessError(503) from None
            item["history"] = {
                "items": history,
                "next_before_revision": history[-1]["case_revision"]
                if len(events) > event_limit
                else None,
            }
            item["historical_creation_recorded"] = (
                row["description_format"] == 1 and abuse_policy is None
            )
            context.session.execute(
                text("""INSERT INTO public.audit_events(actor_user_id,actor_kind,action,target_type,target_id,request_id,reason,safe_details)
            VALUES(:uid,'staff','support_case.read','support_case',:id,:rid,'assigned_case_review',jsonb_build_object('version',CAST(:rev AS integer)))"""),
                {
                    "uid": uid,
                    "id": case_id,
                    "rid": getattr(request.state, "request_id", None),
                    "rev": row["case_revision"],
                },
            )
        items.append(item)
    return paged(items, limit)
```

### API-098 — POST `/api/v1/admin/support-cases`

- Eligibility: **QUARANTINED**. create_case -> sr_support_create validates tag_pairs/order_pair_units when pair_ref supplied; support_cases INSERT also invokes sr_retention_admission pair-link lookup. Null form fields do not establish an independent permitted endpoint.
- Source: `backend/app/api/v1/support_cases.py:306`, `create_case`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; support; assigned-case restrictions.
- Dependencies/helper calls: `command, context.session.execute, context.session.execute(text('SELECT public.sr_support_create(:id,:kind,:priority,:pair,:order,:cipher,CAST(:version AS smallint),:event,:rid)'), {'id': cid, 'kind': body.case_type, 'priority': body.priority, 'pair': body.pair_id, 'order': body.order_id, 'cipher': cipher, 'version': version, 'event': event_id, 'rid': getattr(request.state, 'request_id', None)}).scalar_one, encrypt, getattr, require_staff, router.post, text, uuid4`.

```json
{
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Intake"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post("/admin/support-cases", operation_id="API-098", status_code=201)
def create_case(body: Intake, context: Authenticated, request: Request):
    require_staff(context, "support")

    def work(settings):
        cid = uuid4()
        event_id = uuid4()
        cipher, version = encrypt(
            settings, cid, "support_description", body.description
        )
        return context.session.execute(
            text(
                "SELECT public.sr_support_create(:id,:kind,:priority,:pair,:order,:cipher,CAST(:version AS smallint),:event,:rid)"
            ),
            {
                "id": cid,
                "kind": body.case_type,
                "priority": body.priority,
                "pair": body.pair_id,
                "order": body.order_id,
                "cipher": cipher,
                "version": version,
                "event": event_id,
                "rid": getattr(request.state, "request_id", None),
            },
        ).scalar_one()

    return command(context, request, "support.case.create", body, work, 201)
```

### API-099 — PATCH `/api/v1/admin/support-cases/{case_id}`

- Eligibility: **QUARANTINED**. update_case -> sr_support_change (0035 wrapper -> v34) locks order_pair_units/tag_pairs and calls sr_support_context; claim, note and status edits are all mixed.
- Source: `backend/app/api/v1/support_cases.py:336`, `update_case`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; support; assigned-case restrictions.
- Dependencies/helper calls: `AccessError, case_policy, command, context.session.execute, context.session.execute(text('SELECT 1 FROM public.support_cases WHERE id=:id AND (assigned_staff_id IS NULL OR assigned_staff_id=:uid)'), {'id': case_id, 'uid': context.principal.user_id}).scalar_one_or_none, context.session.execute(text('SELECT public.sr_support_change(:id,:expected,:action,:status,:priority,:event,:note,CAST(:version AS smallint),:rid)'), {'id': case_id, 'expected': body.expected_revision, 'action': body.action, 'status': body.status, 'priority': body.priority, 'event': event_id, 'note': cipher, 'version': version, 'rid': getattr(request.state, 'request_id', None)}).scalar_one, encrypt, getattr, require_staff, router.patch, str, text, uuid4`.

```json
{
  "parameters": [
    {
      "name": "case_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Case Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Change"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.patch("/admin/support-cases/{case_id}", operation_id="API-099")
def update_case(case_id: UUID, body: Change, context: Authenticated, request: Request):
    require_staff(context, "support")
    from app.db.abuse_intake import case_policy

    # Independent of the public feature flag: retained linkage stays restricted.
    intake_policy = case_policy(context.session, case_id)
    if (
        context.session.execute(
            text(
                "SELECT 1 FROM public.support_cases WHERE id=:id AND (assigned_staff_id IS NULL OR assigned_staff_id=:uid)"
            ),
            {"id": case_id, "uid": context.principal.user_id},
        ).scalar_one_or_none()
        is None
    ):
        raise AccessError(404)

    def work(settings):
        event_id = uuid4()
        cipher = version = None
        if body.note is not None:
            cipher, version = encrypt(settings, event_id, "support_note", body.note)
        return context.session.execute(
            text(
                "SELECT public.sr_support_change(:id,:expected,:action,:status,:priority,:event,:note,CAST(:version AS smallint),:rid)"
            ),
            {
                "id": case_id,
                "expected": body.expected_revision,
                "action": body.action,
                "status": body.status,
                "priority": body.priority,
                "event": event_id,
                "note": cipher,
                "version": version,
                "rid": getattr(request.state, "request_id", None),
            },
        ).scalar_one()

    return command(
        context, request, "support.case.update:" + str(case_id), body, work, 200,
        intake_policy=intake_policy,
    )
```

### API-325 — POST `/api/v1/me/privacy/exports`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/privacy_exports.py:94`, `create`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `command, context.session.execute, context.session.execute(text('SELECT public.sr_export_request(:rid,:cid,:mid)'), {'rid': uuid4(), 'cid': body.case_id, 'mid': uuid4()}).scalar_one, recent, router.post, text, uuid4`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/app__api__v1__privacy_exports__ExportRequest"
        }
      }
    },
    "required": true
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-326 — GET `/api/v1/me/privacy/exports/{request_id}`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/privacy_exports.py:110`, `status`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `context.session.execute, context.session.execute(text('SELECT public.sr_export_read(:id)'), {'id': request_id}).scalar_one, require_verified_account, result, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "request_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Request Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-330 — GET `/api/v1/admin/privacy/exports`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/privacy_exports.py:121`, `listing`. Registered and OpenAPI matched; runtime unverified.
- Screen: Privacy Requests.
- Auth/permissions: JWT + live session; security_admin for admin; owner otherwise.
- Dependencies/helper calls: `base64.urlsafe_b64encode, base64.urlsafe_b64encode(json.dumps([last['created_at'], last['request_id']]).encode()).decode, base64.urlsafe_b64encode(json.dumps([last['created_at'], last['request_id']]).encode()).decode().rstrip, bounds, context.session.execute, context.session.execute(text('SELECT public.sr_export_list(:lim,:stamp,:id)'), {'lim': limit + 1, 'stamp': stamp, 'id': ident}).scalars, json.dumps, json.dumps([last['created_at'], last['request_id']]).encode, len, list, page_cursor, require_staff, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/privacy/exports", operation_id="API-330")
def listing(
    context: Authenticated,
    response: Response,
    limit: int = 20,
    cursor: str | None = None,
):
    require_staff(context, "security_admin")
    response.headers["Cache-Control"] = "private, no-store"
    bounds(limit)
    stamp, ident = page_cursor(cursor)
    rows = list(
        context.session.execute(
            text("SELECT public.sr_export_list(:lim,:stamp,:id)"),
            {"lim": limit + 1, "stamp": stamp, "id": ident},
        ).scalars()
    )
    import base64
    import json

    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps([last["created_at"], last["request_id"]]).encode()
            )
            .decode()
            .rstrip("=")
        )
    return {"items": items, "next_cursor": next_cursor}
```

### API-327 — POST `/api/v1/admin/privacy/exports/{request_id}/decisions`

- Eligibility: **QUARANTINED**. approve -> sr_export_decide marks request approved -> privacy_exports worker claim/snapshot -> sr_export_page includes pairs/occurrences. Reject/escalate branches do not make the mixed decision endpoint eligible.
- Source: `backend/app/api/v1/privacy_exports.py:155`, `decide`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; security_admin for admin; owner otherwise.
- Dependencies/helper calls: `AccessError, command, context.session.execute, context.session.execute(text("SELECT public.sr_export_preflight(:id,'decision')"), {'id': request_id}).scalar_one, context.session.execute(text('SELECT public.sr_export_decide(:rid,:cid,:rev,:choice,:reason)'), {'rid': request_id, 'cid': body.case_id, 'rev': body.expected_revision, 'choice': body.decision, 'reason': body.reason_code}).scalar_one, recent, require_staff, result, router.post, str, text`.

```json
{
  "parameters": [
    {
      "name": "request_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Request Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/app__api__v1__privacy_exports__Decision"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post("/admin/privacy/exports/{request_id}/decisions", operation_id="API-327")
def decide(request_id: UUID, body: Decision, request: Request, context: Authenticated):
    require_staff(context, "security_admin")
    recent(context)
    current = result(
        context.session.execute(
            text("SELECT public.sr_export_preflight(:id,'decision')"),
            {"id": request_id},
        ).scalar_one()
    )
    if current["case_id"] != str(body.case_id):
        raise AccessError(404)
    return command(
        context,
        request,
        "privacy.export.decide:" + str(request_id),
        body,
        lambda _: context.session.execute(
            text("SELECT public.sr_export_decide(:rid,:cid,:rev,:choice,:reason)"),
            {
                "rid": request_id,
                "cid": body.case_id,
                "rev": body.expected_revision,
                "choice": body.decision,
                "reason": body.reason_code,
            },
        ).scalar_one(),
        200,
    )
```

### API-328 — POST `/api/v1/me/privacy/exports/{request_id}/download-grants`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/privacy_exports.py:186`, `grant`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `AccessError, base64.urlsafe_b64encode, base64.urlsafe_b64encode(hmac.digest(key(settings, receipt['key_version']), binding.encode(), 'sha256')).decode, base64.urlsafe_b64encode(hmac.digest(key(settings, receipt['key_version']), binding.encode(), 'sha256')).decode().rstrip, binding.encode, command, context.session.execute, context.session.execute(text("SELECT public.sr_export_preflight(:id,'grant')"), {'id': request_id}).scalar_one, context.session.execute(text('SELECT public.sr_export_grant(:rid,:sid,:rev,:hash,:origin)'), {'rid': request_id, 'sid': context.principal.session_id, 'rev': body.expected_revision, 'hash': hashlib.sha256(token.encode()).hexdigest(), 'origin': web_origin}).scalar_one, f'{request_id}:{context.principal.session_id}:{web_origin}'.encode, hashlib.sha256, hashlib.sha256(f'{request_id}:{context.principal.session_id}:{web_origin}'.encode()).hexdigest, hashlib.sha256(token.encode()).hexdigest, hmac.digest, key, origin, recent, result, router.post, secrets.token_hex, text, token.encode, verifier`.

```json
{
  "parameters": [
    {
      "name": "request_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Request Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Revision"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-329 — POST `/api/v1/me/privacy/exports/{request_id}/download`

- Eligibility: **NOT ADMIN**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/privacy_exports.py:248`, `download`. Registered and OpenAPI matched; runtime unverified.
- Screen: Excluded or customer/internal; no new admin control.
- Auth/permissions: Supabase bearer + live session; own authenticated account and object ownership where required, verified-account/recent-authentication checks according to handler. No admin privilege is granted by this customer endpoint.
- Dependencies/helper calls: `ProfileCryptoUnavailable, Response, StreamingResponse, context.session.execute, context.session.execute(text('SELECT public.sr_export_consume(:rid,:sid,:hash,:origin)'), {'rid': request_id, 'sid': context.principal.session_id, 'hash': hashlib.sha256(tokens[0].encode()).hexdigest(), 'origin': web_origin}).scalar_one, decrypt, decrypt(request.app.state.settings, request_id, 'privacy-export:' + value['manifest_id'], cipher, value['key_version']).encode, fail, getattr, hashlib.sha256, hashlib.sha256(data).hexdigest, hashlib.sha256(tokens[0].encode()).hexdigest, len, origin, range, recent, request.headers.getlist, result, router.post, store.read, text, tokens[0].encode`.

```json
{
  "parameters": [
    {
      "name": "request_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Request Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-339 — GET `/api/v1/admin/catalog/approved-templates`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/catalog_templates.py:65`, `choices`. Registered and OpenAPI matched; runtime unverified.
- Screen: Product template choices.
- Auth/permissions: JWT + live session; operations, security_admin, superadmin.
- Dependencies/helper calls: `AccessError, TemplateChoice, TemplateChoices, datetime.now, datetime.now(UTC).isoformat, datetime.now(UTC).isoformat().replace, getattr, guard, int, isinstance, len, pairs.add, re.fullmatch, request.stream, router.get, safe_error, set, sorted, type`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateChoices"
          }
        }
      }
    },
    "401": {
      "description": "Unauthorized",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorEnvelope"
          }
        }
      }
    },
    "403": {
      "description": "Forbidden",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorEnvelope"
          }
        }
      }
    },
    "422": {
      "description": "Unprocessable Content",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ErrorEnvelope"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/catalog/approved-templates",
    operation_id="API-339",
    response_model=TemplateChoices,
    responses={
        status: {"model": ErrorEnvelope} for status in (401, 403, 405, 422, 503)
    },
)
async def choices(request: Request, context: Authenticated):
    guard(context)
    if request.url.query:
        return safe_error(request, 422, "VALIDATION_ERROR")
    async for chunk in request.stream():
        if chunk:
            return safe_error(request, 422, "VALIDATION_ERROR")
    raw = getattr(request.app.state.settings, "catalog_approved_templates", None)
    if type(raw) is not list or len(raw) > 100:
        raise AccessError(503)
    pairs = set()
    for entry in raw:
        if not isinstance(entry, str) or not 5 <= len(entry) <= 87:
            raise AccessError(503)
        match = re.fullmatch(
            r"([A-Za-z0-9._-]{3,80})@([1-9][0-9]{0,5})", entry, re.ASCII
        )
        if match is None or int(match[2]) > 100000:
            raise AccessError(503)
        key, version = match[1], int(match[2])
        if f"{key}@{version}" != entry:
            raise AccessError(503)
        pairs.add((key, version))
    return TemplateChoices(
        as_of=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        items=[
            TemplateChoice(template_key=k, template_version=v) for k, v in sorted(pairs)
        ],
    )
```

### API-300 — GET `/api/v1/admin/print-templates`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:476`, `listing`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `TemplateRepository, TemplateRepository(context).call, cursor, dict, fail, guard, int, json.dumps, p.get, p.items, query, re.fullmatch, router.get`.
- Manual query allowlist: purpose (lost/ice), status (draft/active/retired), limit (default 20, max 50), cursor. Unknown/duplicate fields rejected.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateList"
          }
        }
      }
    },
    "400": {
      "description": "Bad Request",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "401": {
      "description": "Unauthorized",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "403": {
      "description": "Forbidden",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "404": {
      "description": "Not Found",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "409": {
      "description": "Conflict",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "412": {
      "description": "Precondition Failed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "413": {
      "description": "Content Too Large",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "422": {
      "description": "Unprocessable Content",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "429": {
      "description": "Too Many Requests",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/print-templates", operation_id="API-300", response_model=TemplateList
)
def listing(request: Request, context: Authenticated):
    guard(context, request)
    query(request, {"purpose", "status", "limit", "cursor"})
    p = dict(request.query_params)
    if p.get("purpose", "lost") not in {"lost", "ice"} or p.get(
        "status", "draft"
    ) not in {"draft", "active", "retired"}:
        fail(422, "VALIDATION_ERROR")
    if (
        not re.fullmatch(r"[1-9][0-9]?", p.get("limit", "20"))
        or int(p.get("limit", 20)) > 50
    ):
        fail(422, "VALIDATION_ERROR")
    scope = "list:" + json.dumps(
        {k: v for k, v in p.items() if k != "cursor"}, sort_keys=True
    )
    p["after"] = cursor(request, context, scope)
    value = TemplateRepository(context).call("list", p)
    if value["next_cursor"]:
        value["next_cursor"] = cursor(request, context, scope, value["next_cursor"])
    return value
```

### API-301 — POST `/api/v1/admin/print-templates`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:502`, `create`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, router.post`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Create"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/CreateReceipt"
          }
        }
      }
    },
    "400": {
      "description": "Bad Request",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "401": {
      "description": "Unauthorized",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "403": {
      "description": "Forbidden",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "404": {
      "description": "Not Found",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "409": {
      "description": "Conflict",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "412": {
      "description": "Precondition Failed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "413": {
      "description": "Content Too Large",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "422": {
      "description": "Unprocessable Content",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "429": {
      "description": "Too Many Requests",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates",
    operation_id="API-301",
    status_code=201,
    response_model=CreateReceipt,
)
def create(body: Create, request: Request, context: Authenticated):
    return command(context, request, "create", body)
```

### API-302 — GET `/api/v1/admin/print-templates/{template_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:512`, `detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `TemplateRepository, TemplateRepository(context).call, cursor, fail, guard, int, query, re.fullmatch, request.query_params.get, router.get, str`.
- Manual query: revisions_limit (default 20, max 50), revisions_cursor; response ETag is template row_version.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateDetail"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/print-templates/{template_id}",
    operation_id="API-302",
    response_model=TemplateDetail,
)
def detail(
    template_id: UUID, request: Request, response: Response, context: Authenticated
):
    guard(context, request)
    query(request, {"revisions_limit", "revisions_cursor"})
    limit = request.query_params.get("revisions_limit", "20")
    if not re.fullmatch(r"[1-9][0-9]?", limit) or int(limit) > 50:
        fail(422, "VALIDATION_ERROR")
    scope = "revisions:" + str(template_id) + ":" + limit
    value = TemplateRepository(context).call(
        "detail",
        {
            "template_id": str(template_id),
            "limit": int(limit),
            "after": cursor(request, context, scope),
        },
    )
    if value["next_cursor"]:
        value["next_cursor"] = cursor(request, context, scope, value["next_cursor"])
    response.headers["ETag"] = f'"{value["template"]["row_version"]}"'
    return value
```

### API-303 — POST `/api/v1/admin/print-templates/{template_id}/revisions`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:540`, `revision`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/NewRevision"
        }
      }
    }
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/RevisionReceipt"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates/{template_id}/revisions",
    operation_id="API-303",
    status_code=201,
    response_model=RevisionReceipt,
)
def revision(
    template_id: UUID, body: NewRevision, request: Request, context: Authenticated
):
    return command(context, request, "revision", body, template_id=str(template_id))
```

### API-304 — PATCH `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:552`, `edit`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, router.patch, str`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    },
    {
      "name": "revision_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Revision Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/DraftEditRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/EditReceipt"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.patch(
    "/admin/print-templates/{template_id}/revisions/{revision_id}",
    operation_id="API-304",
    response_model=EditReceipt,
)
def edit(
    template_id: UUID,
    revision_id: UUID,
    body: DraftEditRequest,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "edit",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )
```

### API-305 — POST `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/preview`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:574`, `preview`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `Response, proof, router.post`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    },
    {
      "name": "revision_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Revision Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Preview"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Private synthetic PDF; not physical QA approval",
      "content": {
        "application/pdf": {
          "schema": {
            "type": "string",
            "format": "binary"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/preview",
    operation_id="API-305",
    response_class=Response,
    responses={
        200: {
            "description": "Private synthetic PDF; not physical QA approval",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
def preview(
    template_id: UUID,
    revision_id: UUID,
    body: Preview,
    request: Request,
    context: Authenticated,
):
    data, fingerprint, _ = proof(
        context, request, template_id, revision_id, body.expected_revision
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": 'inline; filename="synthetic-template-preview.pdf"',
            "X-Template-Fingerprint": fingerprint,
        },
    )
```

### API-306 — POST `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:666`, `submit`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, match, proof, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    },
    {
      "name": "revision_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Revision Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Reason"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/SubmitReceipt"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa",
    operation_id="API-306",
    response_model=SubmitReceipt,
)
def submit(
    template_id: UUID,
    revision_id: UUID,
    body: Reason,
    request: Request,
    context: Authenticated,
):
    def prepare():
        _, fingerprint, spec = proof(
            context, request, template_id, revision_id, match(request)
        )
        return {
            "proof_content": spec["content"],
            "proof_font": spec["assets"]["font"]["sha256"],
            "proof_logo": spec["assets"]["logo"]["sha256"],
            "proof_fingerprint": fingerprint,
        }

    return command(
        context,
        request,
        "submit",
        body,
        prepare=prepare,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )
```

### API-307 — POST `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/publish`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:700`, `publish`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, publication_proof, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    },
    {
      "name": "revision_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Revision Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Publish"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/PublishedTemplateReceipt"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/publish",
    operation_id="API-307",
    response_model=PublishedTemplateReceipt,
)
def publish(
    template_id: UUID,
    revision_id: UUID,
    body: Publish,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "publish",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
        prepare=lambda: publication_proof(
            context,
            request.app.state.settings,
            template_id,
            revision_id,
            body.approval_id,
        ),
    )
```

### API-308 — POST `/api/v1/admin/print-template-bindings`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:729`, `bind`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, router.post`.

```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Bind"
        }
      }
    },
    "required": true
  },
  "responses": {
    "201": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateBindingReceipt"
          }
        }
      }
    },
    "400": {
      "description": "Bad Request",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "401": {
      "description": "Unauthorized",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "403": {
      "description": "Forbidden",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "404": {
      "description": "Not Found",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "409": {
      "description": "Conflict",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "412": {
      "description": "Precondition Failed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "413": {
      "description": "Content Too Large",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "422": {
      "description": "Unprocessable Content",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "429": {
      "description": "Too Many Requests",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-template-bindings",
    operation_id="API-308",
    status_code=201,
    response_model=TemplateBindingReceipt,
)
def bind(body: Bind, request: Request, context: Authenticated):
    return command(context, request, "bind", body)
```

### API-309 — GET `/api/v1/admin/print-template-bindings`

- Eligibility: **SUPPORTING**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:739`, `bindings`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `TemplateRepository, TemplateRepository(context).call, UUID, cursor, dict, fail, guard, int, json.dumps, len, p.get, p.items, query, re.fullmatch, router.get, str`.
- Manual binding filters/pagination are parsed by request.query_params in source below.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateBindingsPage"
          }
        }
      }
    },
    "400": {
      "description": "Bad Request",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "401": {
      "description": "Unauthorized",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "403": {
      "description": "Forbidden",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "404": {
      "description": "Not Found",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "405": {
      "description": "Method Not Allowed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "409": {
      "description": "Conflict",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "412": {
      "description": "Precondition Failed",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "413": {
      "description": "Content Too Large",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "422": {
      "description": "Unprocessable Content",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "429": {
      "description": "Too Many Requests",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    },
    "503": {
      "description": "Service Unavailable",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/print-template-bindings",
    operation_id="API-309",
    response_model=TemplateBindingsPage,
)
def bindings(request: Request, context: Authenticated):
    guard(context, request)
    query(request, {"variant_id", "tag_type", "active", "limit", "cursor"})
    p = dict(request.query_params)
    limit = p.get("limit", "20")
    if (
        not re.fullmatch(r"[1-9][0-9]?", limit)
        or int(limit) > 50
        or p.get("tag_type", "lost") not in {"lost", "ice"}
        or p.get("active", "true") not in {"true", "false"}
    ):
        fail(422, "VALIDATION_ERROR")
    try:
        if "variant_id" in p:
            p["variant_id"] = str(UUID(p["variant_id"]))
    except ValueError:
        fail(422, "VALIDATION_ERROR")
    scope = "bindings:" + json.dumps(
        {k: v for k, v in p.items() if k != "cursor"}, sort_keys=True
    )
    p["after"] = cursor(request, context, scope)
    result = TemplateRepository(context).call("bindings", p)
    if len(result["items"]) > int(limit):
        result["items"] = result["items"][: int(limit)]
        result["next_cursor"] = cursor(
            request, context, scope, result["items"][-1]["binding_id"]
        )
    return result
```

### API-310 — POST `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/retire`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/print_templates.py:774`, `retire`. Registered and OpenAPI matched; runtime unverified.
- Screen: Print Templates / Create Key / Revisions.
- Auth/permissions: JWT + live session; read operations/security_admin/superadmin; write and preview operations.
- Dependencies/helper calls: `command, router.post, str`.

```json
{
  "parameters": [
    {
      "name": "template_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Template Id"
      }
    },
    {
      "name": "revision_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Revision Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Retire"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/RetiredTemplateReceipt"
          }
        }
      }
    },
    "400": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Bad Request"
    },
    "401": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unauthorized"
    },
    "403": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Forbidden"
    },
    "404": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Not Found"
    },
    "405": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Method Not Allowed"
    },
    "409": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Conflict"
    },
    "412": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Precondition Failed"
    },
    "413": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Content Too Large"
    },
    "422": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Unprocessable Content"
    },
    "429": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Too Many Requests"
    },
    "503": {
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/TemplateErrorEnvelope"
          }
        }
      },
      "description": "Service Unavailable"
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/print-templates/{template_id}/revisions/{revision_id}/retire",
    operation_id="API-310",
    response_model=RetiredTemplateReceipt,
)
def retire(
    template_id: UUID,
    revision_id: UUID,
    body: Retire,
    request: Request,
    context: Authenticated,
):
    return command(
        context,
        request,
        "retire",
        body,
        template_id=str(template_id),
        revision_id=str(revision_id),
    )
```

### API-065 — POST `/api/v1/me/orders/{order_id}/cancel`

- Eligibility: **QR-PAIR EXCLUDED**. Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation.
- Source: `backend/app/api/v1/cancellations.py:161`, `request_cancel`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `guard, router.post, run`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/CancellationRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-340 — POST `/api/v1/admin/orders/{order_id}/cancellation-reconciliations`

- Eligibility: **QR-PAIR EXCLUDED**. Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation.
- Source: `backend/app/api/v1/cancellations.py:169`, `reconcile`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `guard, router.post, run`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Reconciliation"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-341 — POST `/api/v1/admin/orders/{order_id}/cancellation-decisions`

- Eligibility: **QR-PAIR EXCLUDED**. Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation.
- Source: `backend/app/api/v1/cancellations.py:179`, `decide`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `guard, router.post, run`.

```json
{
  "parameters": [
    {
      "name": "order_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Order Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/app__api__v1__cancellations__Decision"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-087 — POST `/api/v1/admin/tag-pairs/{pair_id}/release-allocation`

- Eligibility: **QR-PAIR EXCLUDED**. Cancellation commands/projection inspect reserved pair state and release-allocation changes pair reservations. No isolated permitted operation.
- Source: `backend/app/api/v1/cancellations.py:185`, `release`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `guard, router.post, run`.

```json
{
  "parameters": [
    {
      "name": "pair_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Pair Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Release"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {}
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-324 — GET `/api/v1/admin/support-cases/{case_id}/financial-review`

- Eligibility: **QUARANTINED**. load_context -> sr_financial_case_context (latest 0030 definition) locks order_pair_units and tag_pairs before financial case review.
- Source: `backend/app/api/v1/financial_disputes.py:254`, `review`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance.
- Dependencies/helper calls: `AccessError, Query, ReviewProjection, context.session.execute, context.session.execute(text('SELECT public.sr_financial_case_history(:cid,:before,:lim)'), {'cid': case_id, 'before': before, 'lim': limit + 1}).scalar_one, exact_money, exceptions.append, guard, len, load_context, page_token, parse_token, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "case_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Case Id"
      }
    },
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "maxLength": 2000
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ReviewProjection"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/support-cases/{case_id}/financial-review",
    operation_id="API-324",
    response_model=ReviewProjection,
)
def review(
    case_id: UUID,
    context: Authenticated,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2000),
):
    guard(context, request)
    snap = load_context(context, case_id)
    settings = request.app.state.settings
    before = parse_token(settings, case_id, snap["case"]["revision"], cursor)
    history = context.session.execute(
        text("SELECT public.sr_financial_case_history(:cid,:before,:lim)"),
        {"cid": case_id, "before": before, "lim": limit + 1},
    ).scalar_one()
    if history is None:
        raise AccessError(404)
    more = len(history) > limit
    history = history[:limit]
    exceptions = []
    if snap["fence_active"]:
        exceptions.append("FINANCIAL_FENCE")
    if snap["shipments"]:
        exceptions.append("PACKAGE_REQUIRES_REVIEW")
    if snap["has_active_hold"]:
        exceptions.append("ACTIVE_RETENTION_HOLD")
    try:
        return ReviewProjection(
            case_id=case_id,
            case_type=snap["case"]["type"],
            case_status=snap["case"]["status"],
            case_revision=snap["case"]["revision"],
            order_id=snap["order"]["id"],
            order_revision=snap["order"]["revision"],
            attempt_id=snap["attempt"]["id"],
            amount=exact_money(snap["attempt"]["amount"]),
            currency=snap["attempt"]["currency"],
            settlement_state=snap["attempt"]["state"],
            order_payment_status=snap["order"]["payment_status"],
            dispute_fence="active" if snap["fence_active"] else "none",
            exceptions=exceptions,
            prior_decisions=history,
            next_cursor=page_token(
                settings, case_id, snap["case"]["revision"], history[-1]["revision"]
            )
            if more
            else None,
        )
    except ValidationError:
        raise AccessError(503) from None
```

### API-323 — POST `/api/v1/admin/support-cases/{case_id}/financial-decisions`

- Eligibility: **QUARANTINED**. financial decision calls load_context and sr_financial_case_apply -> sr_financial_case_context; pair locks occur even though final output is finance metadata.
- Source: `backend/app/api/v1/financial_disputes.py:311`, `decide`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance.
- Dependencies/helper calls: `AccessError, DecisionReceipt.model_validate, DecisionReceipt.model_validate(value).model_dump, body.model_dump_json, command, context.session.execute, context.session.execute(text('SELECT public.sr_financial_case_apply(:cid,CAST(:body AS jsonb),CAST(:plan AS jsonb))'), {'cid': case_id, 'body': body.model_dump_json(), 'plan': json.dumps(plan)}).scalar_one, evaluate, guard, json.dumps, load_context, router.post, str, text`.

```json
{
  "parameters": [
    {
      "name": "case_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Case Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/FinancialDecision"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/DecisionReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/support-cases/{case_id}/financial-decisions",
    operation_id="API-323",
    response_model=DecisionReceipt,
)
def decide(
    case_id: UUID, body: FinancialDecision, context: Authenticated, request: Request
):
    guard(context, request, True)
    # The context takes parent/case/grant locks before replay and keeps them to commit.
    snapshot = load_context(context, case_id, True, body.settlement_review_reference)

    def work(_settings):
        plan = evaluate(snapshot, body)
        value = context.session.execute(
            text(
                "SELECT public.sr_financial_case_apply(:cid,CAST(:body AS jsonb),CAST(:plan AS jsonb))"
            ),
            {"cid": case_id, "body": body.model_dump_json(), "plan": json.dumps(plan)},
        ).scalar_one()
        if value is None:
            raise AccessError(404)
        if "error" in value:
            return value
        try:
            return DecisionReceipt.model_validate(value).model_dump(mode="json")
        except ValidationError:
            raise AccessError(503) from None

    return command(context, request, "finance.case:" + str(case_id), body, work, 200)
```

### API-342 — GET `/api/v1/admin/finance/reconciliation`

- Eligibility: **QUARANTINED**. sr_finance_reconciliation -> sr_finance_reconciliation_rows checks order_pair_units for VERIFIED_ALLOCATION_MISMATCH. A reason filter does not expose a distinct independent endpoint.
- Source: `backend/app/api/v1/finance_reconciliation.py:151`, `reconciliation`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance.
- Dependencies/helper calls: `AccessError, Page, Position, Query, audit, context.session.execute, context.session.execute(text('SELECT * FROM public.sr_finance_reconciliation(\n        :as_of,:reason,:stamp,:oid,:aid,:code,:take)'), {'as_of': as_of, 'reason': reason, 'stamp': pos.observed_since if pos else None, 'oid': pos.order_id if pos else ZERO, 'aid': pos.attempt_id if pos else ZERO, 'code': pos.reason_code if pos else '', 'take': limit + 1}).mappings, context.session.execute(text('SELECT * FROM public.sr_finance_reconciliation(\n        :as_of,:reason,:stamp,:oid,:aid,:code,:take)'), {'as_of': as_of, 'reason': reason, 'stamp': pos.observed_since if pos else None, 'oid': pos.order_id if pos else ZERO, 'aid': pos.attempt_id if pos else ZERO, 'code': pos.reason_code if pos else '', 'take': limit + 1}).mappings().all, datetime.now, decode, encode, guard, key, len, projection, router.get, text`.

```json
{
  "parameters": [
    {
      "name": "limit",
      "in": "query",
      "required": false,
      "schema": {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit"
      }
    },
    {
      "name": "reason",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "enum": [
              "REVIEW_PENDING",
              "ATTEMPT_ORDER_AMOUNT_MISMATCH",
              "ATTEMPT_ORDER_CURRENCY_MISMATCH",
              "VERIFIED_HISTORY_MISMATCH",
              "ORDER_SETTLEMENT_MISMATCH",
              "VERIFIED_ALLOCATION_MISMATCH",
              "DUPLICATE_VERIFIED_REFERENCE"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Reason"
      }
    },
    {
      "name": "cursor",
      "in": "query",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string",
            "maxLength": 4096
          },
          {
            "type": "null"
          }
        ],
        "title": "Cursor"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__finance_reconciliation__Page"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/finance/reconciliation", operation_id="API-342", response_model=Page
)
def reconciliation(
    context: Authenticated,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    reason: Reason | None = None,
    cursor: str | None = Query(default=None, max_length=4096),
):
    guard(context, request, {"limit", "reason", "cursor"})
    settings, actor = request.app.state.settings, context.principal.user_id
    try:
        key(settings, settings.profile_data_key_version)
    except ProfileCryptoUnavailable:
        raise AccessError(503) from None
    pos = decode(settings, actor, cursor, reason) if cursor else None
    as_of = pos.as_of if pos else datetime.now(UTC)
    rows = (
        context.session.execute(
            text("""SELECT * FROM public.sr_finance_reconciliation(
        :as_of,:reason,:stamp,:oid,:aid,:code,:take)"""),
            {
                "as_of": as_of,
                "reason": reason,
                "stamp": pos.observed_since if pos else None,
                "oid": pos.order_id if pos else ZERO,
                "aid": pos.attempt_id if pos else ZERO,
                "code": pos.reason_code if pos else "",
                "take": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    items = [projection(row) for row in rows[:limit]]
    token = None
    if len(rows) > limit and items:
        last = items[-1]
        token = encode(
            settings,
            actor,
            Position(
                as_of=as_of,
                reason=reason,
                observed_since=last.observed_since,
                order_id=last.order_id,
                attempt_id=last.attempt_id or ZERO,
                reason_code=last.reason_code,
            ),
        )
    audit(context, "finance.reconciliation.read")
    return Page(
        as_of=as_of, items=items, next_cursor=token, unavailable_checks=UNAVAILABLE
    )
```

### API-343 — GET `/api/v1/admin/finance/reconciliation/counts`

- Eligibility: **QUARANTINED**. sr_finance_reconciliation_counts -> rows helper checks legacy pair allocation; count-only response is still indirect inspection.
- Source: `backend/app/api/v1/finance_reconciliation.py:214`, `counts`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; finance.
- Dependencies/helper calls: `AccessError, Counts, audit, capped, context.session.execute, context.session.execute(text('SELECT reason_code,n\n        FROM public.sr_finance_reconciliation_counts(:as_of)'), {'as_of': as_of}).mappings, context.session.execute(text('SELECT reason_code,n\n        FROM public.sr_finance_reconciliation_counts(:as_of)'), {'as_of': as_of}).mappings().all, datetime.now, guard, len, router.get, set, text`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__finance_reconciliation__Counts"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get(
    "/admin/finance/reconciliation/counts",
    operation_id="API-343",
    response_model=Counts,
)
def counts(context: Authenticated, request: Request):
    guard(context, request, set())
    as_of = datetime.now(UTC)
    # One statement/snapshot; distinct affected orders has a separate cap because
    # many attempts from one order must not hide other affected orders.
    rows = (
        context.session.execute(
            text("""SELECT reason_code,n
        FROM public.sr_finance_reconciliation_counts(:as_of)"""),
            {"as_of": as_of},
        )
        .mappings()
        .all()
    )
    values = {row["reason_code"]: row["n"] for row in rows}
    if len(rows) != len(REASONS) + 1 or set(values) != set(REASONS) | {
        "AFFECTED_ORDERS"
    }:
        raise AccessError(503)
    result = Counts(
        as_of=as_of,
        by_reason={r: capped(values[r]) for r in REASONS},
        affected_orders=capped(values["AFFECTED_ORDERS"]),
        unavailable_checks=UNAVAILABLE,
    )
    audit(context, "finance.reconciliation.counts")
    return result
```

### API-093 — POST `/api/v1/admin/qr-batches/{batch_id}/print-exports`

- Eligibility: **QR-PAIR EXCLUDED**. Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection.
- Source: `backend/app/api/v1/manufacturing_exports.py:184`, `enqueue`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `Receipt.model_validate, Receipt.model_validate(result).model_dump, authority, call, checked, command, fail, projection, projection(snapshot).model_dump, router.post, sealed_bytes, sha, snapshot.get, str, unpack, uuid4`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/app__api__v1__manufacturing_exports__ExportRequest"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__manufacturing_exports__Receipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-336 — GET `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}`

- Eligibility: **QR-PAIR EXCLUDED**. Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection.
- Source: `backend/app/api/v1/manufacturing_exports.py:232`, `status`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, checked, current, guard, projection, router.get`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    },
    {
      "name": "job_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Job Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Metadata"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-338 — POST `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants`

- Eligibility: **QR-PAIR EXCLUDED**. Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection.
- Source: `backend/app/api/v1/manufacturing_exports.py:243`, `issue`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `GrantReceipt.model_validate, GrantReceipt.model_validate({**result, 'grant_token': secret}).model_dump, call, checked, command, fail, router.post, secret.encode, secrets.token_urlsafe, sha, str, uuid4`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    },
    {
      "name": "job_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Job Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/GrantRequest"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/GrantReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-337 — POST `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download`

- Eligibility: **QR-PAIR EXCLUDED**. Batch export service reads pair inventory and builds/downloads credential-bearing manufacturing material or authorizes its worker/grant. No export/grant/redeem connection.
- Source: `backend/app/api/v1/manufacturing_exports.py:294`, `download`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; owner and route-specific checks.
- Dependencies/helper calls: `AccessError, Header, Response, UUID, call, checked, current, fail, grant.split, guard, hmac.compare_digest, len, re.fullmatch, request.headers.getlist, router.post, sealed_bytes, sha, str, token.encode, unpack`.

```json
{
  "parameters": [
    {
      "name": "batch_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Batch Id"
      }
    },
    {
      "name": "job_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "Job Id"
      }
    },
    {
      "name": "X-Print-Grant",
      "in": "header",
      "required": false,
      "schema": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "X-Print-Grant"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response"
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

### API-344 — GET `/api/v1/admin/dashboard/summary`

- Eligibility: **QUARANTINED**. summary -> sr_dashboard_summary(fulfillment) -> sr_fulfillment_eligible; operations projection reads legacy pair allocation/QA. No backend group selector isolates safe groups for all roles.
- Source: `backend/app/api/v1/dashboard.py:232`, `summary`. Registered and OpenAPI matched; runtime unverified.
- Screen: no proposed integration; existing frontend references are avoidance evidence in the exclusion table.
- Auth/permissions: JWT + live session; all five staff roles; role-filtered projection.
- Dependencies/helper calls: `AccessError, Group, METRICS[group].items, Metric, ROLES.items, Summary, ValueError, count, datetime.now, final.intersection, final_roles, groups.append, guard, isinstance, monotonic, permitted.intersection, query, router.get, set`.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__dashboard__Summary"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/dashboard/summary", operation_id="API-344", response_model=Summary)
def summary(request: Request, context: Authenticated):
    permitted = guard(context, request, set())
    settings = request.app.state.settings
    deadline, observed = monotonic() + 8, datetime.now(UTC)
    groups = []
    for group, allowed in ROLES.items():
        if not permitted.intersection(allowed):
            continue
        reason = None
        metrics = []
        stamp = None
        if group not in METRICS:
            reason = "DRILLDOWN_UNAVAILABLE"
            if group == "finance" and not settings.finance_reconciliation_enabled:
                reason = "FEATURE_DISABLED"
            if group == "inventory" and settings.inventory_low_stock_threshold is None:
                reason = "LOW_STOCK_UNCONFIGURED"
        else:
            try:
                stamp = datetime.now(UTC)
                values = query(
                    context,
                    deadline,
                    "SELECT public.sr_dashboard_summary(:group)",
                    {"group": group},
                )
                if not isinstance(values, dict) or set(values) != set(METRICS[group]):
                    raise ValueError("Unexpected projection")
                metrics = [
                    Metric(
                        metric_id=key,
                        unit=unit,
                        count=count(values[key]),
                        drilldown=path,
                    )
                    for key, (unit, path) in METRICS[group].items()
                ]
            except BudgetExpired:
                reason = "REQUEST_BUDGET_EXHAUSTED"
            except (SQLAlchemyError, ValidationError, ValueError, TypeError):
                reason = "QUERY_UNAVAILABLE"
        groups.append(
            Group(
                group=group,
                status="unavailable" if reason else "ready",
                as_of=None if reason else stamp,
                metrics=[] if reason else metrics,
                reason_code=reason,
            )
        )
    # Revocations during independent queries cannot leave now-forbidden groups.
    final = final_roles(context)
    if not final:
        raise AccessError(403)
    return Summary(
        as_of=observed, groups=[g for g in groups if final.intersection(ROLES[g.group])]
    )
```

### API-345 — GET `/api/v1/admin/dashboard/trends`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/dashboard.py:292`, `trends`. Registered and OpenAPI matched; runtime unverified.
- Screen: Overview.
- Auth/permissions: JWT + live session; all five staff roles; role-filtered projection.
- Dependencies/helper calls: `AccessError, Bucket, SERIES.items, Series, Trends, ValueError, buckets.append, count, datetime.now, enumerate, final.intersection, final_roles, guard, isinstance, len, monotonic, observed.replace, permitted.intersection, query, router.get, series.append, set, timedelta`.

```json
{
  "parameters": [
    {
      "name": "display_timezone",
      "in": "query",
      "required": false,
      "schema": {
        "enum": [
          "UTC",
          "Asia/Karachi"
        ],
        "type": "string",
        "default": "UTC",
        "title": "Display Timezone"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Trends"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/dashboard/trends", operation_id="API-345", response_model=Trends)
def trends(
    request: Request,
    context: Authenticated,
    display_timezone: Literal["UTC", "Asia/Karachi"] = "UTC",
):
    permitted = guard(context, request, {"display_timezone"})
    observed = datetime.now(UTC)
    end = observed.replace(hour=0, minute=0, second=0, microsecond=0)
    start, deadline = end - timedelta(days=30), monotonic() + 8
    series = []
    for ident, (allowed, unit) in SERIES.items():
        if not permitted.intersection(allowed):
            continue
        reason, buckets = None, []
        if ident == "orders_placed":
            reason = "DRILLDOWN_UNAVAILABLE"
        else:
            try:
                rows = query(
                    context,
                    deadline,
                    "SELECT public.sr_dashboard_trend(:series,:end)",
                    {"series": ident, "end": end},
                )
                if not isinstance(rows, list) or len(rows) != 30:
                    raise ValueError("Invalid buckets")
                for i, row in enumerate(rows):
                    if set(row) != {"start", "end", "n"}:
                        raise ValueError("Invalid bucket")
                    bucket = Bucket(
                        start=row["start"], end=row["end"], count=count(row["n"])
                    )
                    if bucket.start != start + timedelta(
                        days=i
                    ) or bucket.end != bucket.start + timedelta(days=1):
                        raise ValueError("Invalid range")
                    buckets.append(bucket)
            except BudgetExpired:
                reason = "REQUEST_BUDGET_EXHAUSTED"
            except (SQLAlchemyError, ValidationError, ValueError, TypeError):
                reason = "QUERY_UNAVAILABLE"
        series.append(
            Series(
                series_id=ident,
                unit=unit,
                status="unavailable" if reason else "ready",
                reason_code=reason,
                buckets=[] if reason else buckets,
            )
        )
    final = final_roles(context)
    if not final:
        raise AccessError(403)
    return Trends(
        as_of=observed,
        range_start=start,
        range_end=end,
        display_timezone=display_timezone,
        series=[s for s in series if final.intersection(SERIES[s.series_id][0])],
    )
```

### API-346 — GET `/api/v1/admin/users`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/staff_directory.py:267`, `users`. Registered and OpenAPI matched; runtime unverified.
- Screen: Users.
- Auth/permissions: JWT + live session; security_admin only.
- Dependencies/helper calls: `AccessError, Page, User.model_validate, ValueError, decode_cursor, encode_cursor, fail, filters, finish, guard, int, isinstance, len, re.fullmatch, read, request.query_params.get, router.get, set`.
- Manual query: user_id, email_verified, provider_access, limit (1-100), cursor; duplicates/unknown fields rejected.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/app__api__v1__staff_directory__Page"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/users", operation_id="API-346", response_model=Page)
def users(request: Request, context: Authenticated) -> Page:
    guard(
        context,
        request,
        {"user_id", "email_verified", "provider_access", "limit", "cursor"},
    )
    selected = filters(request)
    limit_text = request.query_params.get("limit", "20")
    if (
        not re.fullmatch(r"[1-9][0-9]{0,2}", limit_text)
        or not 1 <= int(limit_text) <= 100
    ):
        fail(422, "INVALID_LIMIT")
    limit = int(limit_text)
    stamp, ident = decode_cursor(request.query_params.get("cursor"), selected)
    raw = read(context, "list", selected, limit, stamp, ident)
    try:
        if (
            set(raw) != {"as_of", "items"}
            or not isinstance(raw["items"], list)
            or len(raw["items"]) > limit + 1
        ):
            raise ValueError()
        rows = [User.model_validate(row) for row in raw["items"]]
        result = Page(
            as_of=raw["as_of"],
            items=rows[:limit],
            next_cursor=encode_cursor(rows[limit - 1], selected)
            if len(rows) > limit
            else None,
        )
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    finish(context)
    return result
```

### API-348 — GET `/api/v1/admin/users/count`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/staff_directory.py:305`, `total`. Registered and OpenAPI matched; runtime unverified.
- Screen: Users.
- Auth/permissions: JWT + live session; security_admin only.
- Dependencies/helper calls: `AccessError, Total.model_validate, ValueError, filters, finish, guard, read, router.get`.
- Manual query: user_id, email_verified, provider_access.

```json
{
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Total"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/users/count", operation_id="API-348", response_model=Total)
def total(request: Request, context: Authenticated) -> Total:
    guard(context, request, {"user_id", "email_verified", "provider_access"})
    selected = filters(request)
    try:
        result = Total.model_validate(read(context, "count", selected))
        if result.filters != selected:
            raise ValueError()
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    finish(context)
    return result
```

### API-347 — GET `/api/v1/admin/users/{user_id}`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/staff_directory.py:319`, `detail`. Registered and OpenAPI matched; runtime unverified.
- Screen: Users.
- Auth/permissions: JWT + live session; security_admin only.
- Dependencies/helper calls: `AccessError, Detail, Filters, User.model_validate, ValueError, application_state, fail, finish, guard, isinstance, len, read, request.query_params.get, router.get, set`.
- Manual query: include; application_suspension may be unavailable.

```json
{
  "parameters": [
    {
      "name": "user_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "User Id"
      }
    }
  ],
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/Detail"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.get("/admin/users/{user_id}", operation_id="API-347", response_model=Detail)
def detail(user_id: UUID, request: Request, context: Authenticated) -> Detail:
    guard(context, request, {"include"})
    include = request.query_params.get("include")
    if include not in (None, "account_security"):
        fail(422, "INVALID_QUERY")
    raw = read(context, "detail", Filters(user_id=user_id))
    try:
        if (
            set(raw) != {"as_of", "items"}
            or not isinstance(raw["items"], list)
            or len(raw["items"]) > 1
        ):
            raise ValueError()
        if not raw["items"]:
            finish(context)
            raise AccessError(404)
        result = Detail(as_of=raw["as_of"], user=User.model_validate(raw["items"][0]))
        if result.user.user_id != user_id:
            raise ValueError()
    except (ValueError, TypeError, ValidationError):
        raise AccessError(503) from None
    if include == "account_security":
        result.application_suspension = application_state(context, user_id, request)
    finish(context)
    return result
```

### API-320 — POST `/api/v1/admin/users/{user_id}/suspensions`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account_lifecycle.py:230`, `suspend`. Registered and OpenAPI matched; runtime unverified.
- Screen: User Governance.
- Auth/permissions: JWT + live session; security_admin only + case approval + recent authentication.
- Dependencies/helper calls: `execute, router.post`.

```json
{
  "parameters": [
    {
      "name": "user_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "User Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Suspend"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/StateReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/users/{user_id}/suspensions",
    operation_id="API-320",
    response_model=StateReceipt,
)
def suspend(user_id: UUID, body: Suspend, request: Request, context: Authenticated):
    return execute(user_id, body, "suspend", request, context)
```

### API-321 — POST `/api/v1/admin/users/{user_id}/restorations`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account_lifecycle.py:239`, `restore`. Registered and OpenAPI matched; runtime unverified.
- Screen: User Governance.
- Auth/permissions: JWT + live session; security_admin only + case approval + recent authentication.
- Dependencies/helper calls: `execute, router.post`.

```json
{
  "parameters": [
    {
      "name": "user_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "User Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Restore"
        }
      }
    }
  },
  "responses": {
    "200": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/StateReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/users/{user_id}/restorations",
    operation_id="API-321",
    response_model=StateReceipt,
)
def restore(user_id: UUID, body: Restore, request: Request, context: Authenticated):
    return execute(user_id, body, "restore", request, context)
```

### API-322 — POST `/api/v1/admin/users/{user_id}/recovery-escalations`

- Eligibility: **ELIGIBLE**. Source-reviewed administrative/supporting behavior; outside Phase 1 unless explicitly allowlisted.
- Source: `backend/app/api/v1/account_lifecycle.py:248`, `recovery`. Registered and OpenAPI matched; runtime unverified.
- Screen: User Governance.
- Auth/permissions: JWT + live session; security_admin only + case approval + recent authentication.
- Dependencies/helper calls: `execute, router.post`.

```json
{
  "parameters": [
    {
      "name": "user_id",
      "in": "path",
      "required": true,
      "schema": {
        "type": "string",
        "format": "uuid",
        "title": "User Id"
      }
    }
  ],
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/Recovery"
        }
      }
    }
  },
  "responses": {
    "202": {
      "description": "Successful Response",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/ReferralReceipt"
          }
        }
      }
    },
    "422": {
      "description": "Validation Error",
      "content": {
        "application/json": {
          "schema": {
            "$ref": "#/components/schemas/HTTPValidationError"
          }
        }
      }
    }
  },
  "security": [
    {
      "SupabaseAccessToken": []
    }
  ]
}
```

Source contract supplement:

```python
@router.post(
    "/admin/users/{user_id}/recovery-escalations",
    operation_id="API-322",
    response_model=ReferralReceipt,
    status_code=202,
)
def recovery(user_id: UUID, body: Recovery, request: Request, context: Authenticated):
    return execute(user_id, body, "recovery_escalated", request, context)
```


## Registration limits

The prior registered set is retained; no app reimport/request in this correction. Source review, SQL/trigger inspection and report consistency checks do not prove deployed behavior. NOT ADMIN/BLOCKED and future-only candidates are denied to the first phase.

## OpenAPI schema appendix

Source metadata, not real credentials or payloads.

```json
{
  "schemas": {
    "AbuseError": {
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "VALIDATION_ERROR",
            "UNSUPPORTED_MEDIA_TYPE",
            "FILE_TOO_LARGE",
            "RATE_LIMITED",
            "CHALLENGE_REQUIRED",
            "IDEMPOTENCY_KEY_REUSED",
            "PROVIDER_UNAVAILABLE",
            "METHOD_NOT_ALLOWED"
          ],
          "title": "Code"
        },
        "message": {
          "type": "string",
          "title": "Message"
        },
        "message_ur": {
          "type": "string",
          "title": "Message Ur"
        },
        "request_id": {
          "type": "string",
          "pattern": "^[0-9a-f]{32}$",
          "title": "Request Id"
        },
        "details": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/EmptyDetails"
            },
            {
              "$ref": "#/components/schemas/ChallengeDetails"
            }
          ],
          "title": "Details"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "code",
        "message",
        "message_ur",
        "request_id",
        "details"
      ],
      "title": "AbuseError"
    },
    "AbuseErrorEnvelope": {
      "properties": {
        "error": {
          "$ref": "#/components/schemas/AbuseError"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "error"
      ],
      "title": "AbuseErrorEnvelope"
    },
    "AccountSummary": {
      "properties": {
        "user_id": {
          "type": "string",
          "title": "User Id"
        },
        "display_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Name"
        },
        "preferred_locale": {
          "type": "string",
          "enum": [
            "en",
            "ur"
          ],
          "title": "Preferred Locale"
        },
        "email_verified": {
          "type": "boolean",
          "title": "Email Verified"
        },
        "masked_contact": {
          "$ref": "#/components/schemas/MaskedContact"
        },
        "version": {
          "type": "string",
          "title": "Version"
        }
      },
      "type": "object",
      "required": [
        "user_id",
        "display_name",
        "preferred_locale",
        "email_verified",
        "masked_contact",
        "version"
      ],
      "title": "AccountSummary"
    },
    "ActivatedQR": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        }
      },
      "type": "object",
      "required": [
        "qr_id",
        "tag_type"
      ],
      "title": "ActivatedQR"
    },
    "ActivationResponse": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "status": {
          "type": "string",
          "const": "active",
          "title": "Status"
        },
        "activated_at": {
          "type": "string",
          "format": "date-time",
          "title": "Activated At"
        },
        "qr_codes": {
          "items": {
            "$ref": "#/components/schemas/ActivatedQR"
          },
          "type": "array",
          "title": "Qr Codes"
        }
      },
      "type": "object",
      "required": [
        "pair_id",
        "status",
        "activated_at",
        "qr_codes"
      ],
      "title": "ActivationResponse"
    },
    "Address": {
      "properties": {
        "recipient_name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Recipient Name"
        },
        "phone": {
          "type": "string",
          "pattern": "^\\+[1-9][0-9]{7,14}$",
          "title": "Phone"
        },
        "address": {
          "type": "string",
          "maxLength": 500,
          "minLength": 1,
          "title": "Address"
        },
        "city": {
          "type": "string",
          "maxLength": 100,
          "minLength": 1,
          "title": "City"
        },
        "province": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 100
            },
            {
              "type": "null"
            }
          ],
          "title": "Province"
        },
        "postal_code": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 20
            },
            {
              "type": "null"
            }
          ],
          "title": "Postal Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "recipient_name",
        "phone",
        "address",
        "city"
      ],
      "title": "Address"
    },
    "AllocationRetry": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed"
      ],
      "title": "AllocationRetry"
    },
    "ApplicationState": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "status": {
          "type": "string",
          "const": "ready",
          "title": "Status",
          "default": "ready"
        },
        "state": {
          "type": "string",
          "enum": [
            "active",
            "suspended"
          ],
          "title": "State"
        },
        "revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Revision"
        },
        "commands_available": {
          "type": "boolean",
          "title": "Commands Available"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "state",
        "revision",
        "commands_available"
      ],
      "title": "ApplicationState"
    },
    "Availability": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "public_status": {
          "type": "string",
          "enum": [
            "active",
            "owner_disabled"
          ],
          "title": "Public Status"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "public_status",
        "expected_revision"
      ],
      "title": "Availability"
    },
    "BatchRequest": {
      "properties": {
        "pair_count": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 1.0,
          "title": "Pair Count"
        },
        "batch_label": {
          "type": "string",
          "maxLength": 40,
          "minLength": 3,
          "title": "Batch Label"
        },
        "logo_template_key": {
          "type": "string",
          "const": "safe-return-primary",
          "title": "Logo Template Key"
        },
        "qr_ecc": {
          "type": "string",
          "enum": [
            "M",
            "Q"
          ],
          "title": "Qr Ecc"
        },
        "print_material": {
          "type": "string",
          "maxLength": 60,
          "minLength": 2,
          "title": "Print Material"
        },
        "intended_environment": {
          "type": "string",
          "enum": [
            "indoor",
            "outdoor"
          ],
          "title": "Intended Environment"
        },
        "lost_symbol_size_mm": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 100.0,
              "minimum": 30.0
            },
            {
              "type": "string"
            }
          ],
          "title": "Lost Symbol Size Mm"
        },
        "ice_symbol_size_mm": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 100.0,
              "minimum": 30.0
            },
            {
              "type": "string"
            }
          ],
          "title": "Ice Symbol Size Mm"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "pair_count",
        "batch_label",
        "logo_template_key",
        "qr_ecc",
        "print_material",
        "intended_environment",
        "lost_symbol_size_mm",
        "ice_symbol_size_mm"
      ],
      "title": "BatchRequest"
    },
    "BatchResponse": {
      "properties": {
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "generated_pair_count": {
          "type": "integer",
          "title": "Generated Pair Count"
        },
        "generated_qr_count": {
          "type": "integer",
          "title": "Generated Qr Count"
        },
        "status": {
          "type": "string",
          "const": "generated",
          "title": "Status"
        },
        "sealed_insert": {
          "$ref": "#/components/schemas/SealedInsert"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "batch_id",
        "batch_label",
        "generated_pair_count",
        "generated_qr_count",
        "status",
        "sealed_insert"
      ],
      "title": "BatchResponse"
    },
    "Begin": {
      "properties": {
        "logical_item_id": {
          "type": "string",
          "format": "uuid",
          "title": "Logical Item Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "logical_item_id"
      ],
      "title": "Begin"
    },
    "Bind": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "variant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Variant Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "revision_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Revision Id"
        },
        "expected_variant_version": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Expected Variant Version"
        },
        "expected_binding_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Expected Binding Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "variant_id",
        "tag_type",
        "revision_id",
        "expected_variant_version",
        "expected_binding_id"
      ],
      "title": "Bind"
    },
    "Bucket": {
      "properties": {
        "start": {
          "type": "string",
          "format": "date-time",
          "title": "Start"
        },
        "end": {
          "type": "string",
          "format": "date-time",
          "title": "End"
        },
        "count": {
          "$ref": "#/components/schemas/Count"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "start",
        "end",
        "count"
      ],
      "title": "Bucket"
    },
    "CancellationRequest": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "ordered_by_mistake",
            "no_longer_needed",
            "other"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision",
        "reason_code"
      ],
      "title": "CancellationRequest"
    },
    "CartLine": {
      "properties": {
        "variant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Variant Id"
        },
        "quantity": {
          "type": "integer",
          "maximum": 100.0,
          "minimum": 1.0,
          "title": "Quantity"
        },
        "qr_uses": {
          "items": {
            "$ref": "#/components/schemas/QRUse"
          },
          "type": "array",
          "maxItems": 20,
          "minItems": 1,
          "title": "Qr Uses"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "variant_id",
        "quantity",
        "qr_uses"
      ],
      "title": "CartLine"
    },
    "CategoryRequest": {
      "properties": {
        "slug": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9-]{1,59}$",
          "title": "Slug"
        },
        "name": {
          "type": "string",
          "maxLength": 120,
          "minLength": 1,
          "title": "Name"
        },
        "sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Sort Order",
          "default": 0
        },
        "is_active": {
          "type": "boolean",
          "title": "Is Active",
          "default": true
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "slug",
        "name"
      ],
      "title": "CategoryRequest"
    },
    "ChallengeDetails": {
      "properties": {
        "challenge": {
          "type": "string",
          "const": "turnstile",
          "title": "Challenge"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "challenge"
      ],
      "title": "ChallengeDetails"
    },
    "Change": {
      "properties": {
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "action": {
          "type": "string",
          "enum": [
            "claim",
            "update"
          ],
          "title": "Action"
        },
        "status": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "open",
                "investigating",
                "resolved",
                "closed"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Status"
        },
        "priority": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "low",
                "normal",
                "high",
                "urgent"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Priority"
        },
        "note": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2000,
              "minLength": 4
            },
            {
              "type": "null"
            }
          ],
          "title": "Note"
        },
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "expected_revision",
        "action",
        "confirmed"
      ],
      "title": "Change"
    },
    "Command": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "public_status": {
          "type": "string",
          "enum": [
            "active",
            "owner_disabled"
          ],
          "title": "Public Status"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "reason": {
          "type": "string",
          "enum": [
            "temporary",
            "resume"
          ],
          "title": "Reason"
        },
        "public_access_acknowledged": {
          "type": "boolean",
          "title": "Public Access Acknowledged"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "public_status",
        "expected_revision",
        "reason",
        "public_access_acknowledged"
      ],
      "title": "Command"
    },
    "ConfigurationFeatures": {
      "properties": {
        "abuse_reporting_available": {
          "type": "boolean",
          "const": false,
          "title": "Abuse Reporting Available"
        },
        "template_publication_available": {
          "type": "boolean",
          "const": false,
          "title": "Template Publication Available"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "abuse_reporting_available",
        "template_publication_available"
      ],
      "title": "ConfigurationFeatures"
    },
    "Confirm": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "intent_id": {
          "type": "string",
          "format": "uuid",
          "title": "Intent Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "intent_id"
      ],
      "title": "Confirm"
    },
    "ConfirmRequest": {
      "properties": {
        "accept_total": {
          "type": "string",
          "pattern": "^[0-9]{1,10}\\.[0-9]{2}$",
          "title": "Accept Total"
        },
        "accept_currency": {
          "type": "string",
          "const": "PKR",
          "title": "Accept Currency"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "accept_total",
        "accept_currency"
      ],
      "title": "ConfirmRequest"
    },
    "ConfirmationRequest": {
      "properties": {
        "intent_id": {
          "type": "string",
          "format": "uuid",
          "title": "Intent Id"
        },
        "confirm": {
          "type": "boolean",
          "title": "Confirm"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "intent_id",
        "confirm"
      ],
      "title": "ConfirmationRequest"
    },
    "ConsentVersions": {
      "properties": {
        "finder_contact": {
          "prefixItems": [
            {
              "type": "string",
              "const": "finder-v1"
            },
            {
              "type": "string",
              "const": "finder-public-v1"
            }
          ],
          "type": "array",
          "maxItems": 2,
          "minItems": 2,
          "title": "Finder Contact"
        },
        "finder_location": {
          "prefixItems": [
            {
              "type": "string",
              "const": "location-v1"
            },
            {
              "type": "string",
              "const": "finder-location-v1"
            }
          ],
          "type": "array",
          "maxItems": 2,
          "minItems": 2,
          "title": "Finder Location"
        },
        "ice_publication": {
          "prefixItems": [
            {
              "type": "string",
              "const": "ice-public-v1"
            }
          ],
          "type": "array",
          "maxItems": 1,
          "minItems": 1,
          "title": "Ice Publication"
        },
        "ice_contact": {
          "prefixItems": [
            {
              "type": "string",
              "const": "ice-contact-v1"
            }
          ],
          "type": "array",
          "maxItems": 1,
          "minItems": 1,
          "title": "Ice Contact"
        },
        "whatsapp_publication": {
          "prefixItems": [
            {
              "type": "string",
              "const": "wa-public-v1"
            }
          ],
          "type": "array",
          "maxItems": 1,
          "minItems": 1,
          "title": "Whatsapp Publication"
        },
        "abuse_report": {
          "prefixItems": [
            {
              "type": "string",
              "const": "abuse-report-v1"
            }
          ],
          "type": "array",
          "maxItems": 1,
          "minItems": 1,
          "title": "Abuse Report"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "finder_contact",
        "finder_location",
        "ice_publication",
        "ice_contact",
        "whatsapp_publication",
        "abuse_report"
      ],
      "title": "ConsentVersions"
    },
    "ContactEdit": {
      "properties": {
        "relationship_label": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 60,
              "minLength": 1
            },
            {
              "type": "null"
            }
          ],
          "title": "Relationship Label"
        },
        "display_name": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Name"
        },
        "phone": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 16,
              "minLength": 8,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Phone"
        },
        "display_order": {
          "anyOf": [
            {
              "type": "integer",
              "maximum": 100.0,
              "minimum": 0.0
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Order"
        },
        "published": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Published"
        },
        "publication_consent_accepted": {
          "type": "boolean",
          "title": "Publication Consent Accepted",
          "default": false
        },
        "publication_consent_version": {
          "anyOf": [
            {
              "type": "string",
              "const": "ice-contact-v1"
            },
            {
              "type": "null"
            }
          ],
          "title": "Publication Consent Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "ContactEdit"
    },
    "ContactResponse": {
      "properties": {
        "phone": {
          "type": "string",
          "title": "Phone"
        },
        "tel_uri": {
          "type": "string",
          "title": "Tel Uri"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "phone",
        "tel_uri"
      ],
      "title": "ContactResponse"
    },
    "ContactRevealRequest": {
      "properties": {
        "contact_id": {
          "type": "string",
          "format": "uuid",
          "title": "Contact Id"
        },
        "turnstile_token": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2048,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Turnstile Token"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "contact_id"
      ],
      "title": "ContactRevealRequest"
    },
    "Content": {
      "properties": {
        "schema_version": {
          "type": "integer",
          "const": 1,
          "title": "Schema Version"
        },
        "renderer": {
          "type": "string",
          "const": "safereturn-vector-v1",
          "title": "Renderer"
        },
        "preset": {
          "type": "string",
          "const": "fixed-footer-v1",
          "title": "Preset"
        },
        "symbol_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Symbol Mm"
        },
        "width_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Width Mm"
        },
        "height_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Height Mm"
        },
        "qr_x_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Qr X Mm"
        },
        "qr_y_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Qr Y Mm"
        },
        "logo_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Logo Mm"
        },
        "min_pitch_mm": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Min Pitch Mm"
        },
        "font_pt": {
          "type": "string",
          "pattern": "^[0-9]{1,3}\\.[0-9]{2}$",
          "title": "Font Pt"
        },
        "header": {
          "type": "string",
          "maxLength": 50,
          "minLength": 1,
          "title": "Header"
        },
        "english_lines": {
          "items": {
            "type": "string",
            "maxLength": 120,
            "minLength": 1
          },
          "type": "array",
          "maxItems": 4,
          "minItems": 1,
          "title": "English Lines"
        },
        "urdu_lines": {
          "items": {
            "type": "string",
            "maxLength": 120,
            "minLength": 1
          },
          "type": "array",
          "maxItems": 4,
          "minItems": 1,
          "title": "Urdu Lines"
        },
        "asset_set_id": {
          "type": "string",
          "format": "uuid",
          "title": "Asset Set Id"
        },
        "material_codes": {
          "items": {
            "type": "string",
            "pattern": "^[a-z0-9_-]{1,40}$"
          },
          "type": "array",
          "maxItems": 10,
          "minItems": 1,
          "title": "Material Codes"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "schema_version",
        "renderer",
        "preset",
        "symbol_mm",
        "width_mm",
        "height_mm",
        "qr_x_mm",
        "qr_y_mm",
        "logo_mm",
        "min_pitch_mm",
        "font_pt",
        "header",
        "english_lines",
        "urdu_lines",
        "asset_set_id",
        "material_codes"
      ],
      "title": "Content"
    },
    "Count": {
      "properties": {
        "value": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 0.0,
          "title": "Value"
        },
        "is_exact": {
          "type": "boolean",
          "title": "Is Exact"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "value",
        "is_exact"
      ],
      "title": "Count"
    },
    "Create": {
      "properties": {
        "key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9._-]{3,80}$",
          "title": "Key"
        },
        "name": {
          "type": "string",
          "maxLength": 100,
          "minLength": 1,
          "title": "Name"
        },
        "purpose": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Purpose"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "key",
        "name",
        "purpose"
      ],
      "title": "Create"
    },
    "CreateAddress": {
      "properties": {
        "recipient_name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Recipient Name"
        },
        "phone": {
          "type": "string",
          "pattern": "^\\+[1-9][0-9]{7,14}$",
          "title": "Phone"
        },
        "address": {
          "type": "string",
          "maxLength": 500,
          "minLength": 1,
          "title": "Address"
        },
        "city": {
          "type": "string",
          "maxLength": 100,
          "minLength": 1,
          "title": "City"
        },
        "province": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 100
            },
            {
              "type": "null"
            }
          ],
          "title": "Province"
        },
        "postal_code": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 20
            },
            {
              "type": "null"
            }
          ],
          "title": "Postal Code"
        },
        "is_default": {
          "type": "boolean",
          "title": "Is Default",
          "default": false
        },
        "expected_book_version": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 0.0,
          "title": "Expected Book Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "recipient_name",
        "phone",
        "address",
        "city",
        "expected_book_version"
      ],
      "title": "CreateAddress"
    },
    "CreateProductRequest": {
      "properties": {
        "category_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Category Id"
        },
        "slug": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9-]{1,99}$",
          "title": "Slug"
        },
        "name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Name"
        },
        "description": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 4000
            },
            {
              "type": "null"
            }
          ],
          "title": "Description"
        },
        "lifecycle_status": {
          "type": "string",
          "enum": [
            "draft",
            "published",
            "archived"
          ],
          "title": "Lifecycle Status",
          "default": "draft"
        },
        "price_per_copy": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 9999999999.99,
              "minimum": 0.0
            },
            {
              "type": "string"
            }
          ],
          "title": "Price Per Copy"
        },
        "max_order_copies": {
          "type": "integer",
          "maximum": 100.0,
          "minimum": 1.0,
          "title": "Max Order Copies",
          "default": 100
        },
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "is_featured": {
          "type": "boolean",
          "title": "Is Featured",
          "default": false
        },
        "featured_sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Featured Sort Order",
          "default": 0
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "slug",
        "name",
        "price_per_copy",
        "qr_type"
      ],
      "title": "CreateProductRequest"
    },
    "CreateReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/TemplateView"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "CreateReceipt"
    },
    "DecisionReceipt": {
      "properties": {
        "decision_id": {
          "type": "string",
          "format": "uuid",
          "title": "Decision Id"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "case_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Case Revision"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Order Revision"
        },
        "decision": {
          "type": "string",
          "enum": [
            "investigate",
            "confirm_dispute",
            "resolve_no_change",
            "escalate"
          ],
          "title": "Decision"
        },
        "effective_decision": {
          "type": "string",
          "enum": [
            "investigate",
            "confirm_dispute",
            "resolve_no_change",
            "escalate"
          ],
          "title": "Effective Decision"
        },
        "dispute_fence": {
          "type": "string",
          "enum": [
            "active",
            "none"
          ],
          "title": "Dispute Fence"
        },
        "next_action": {
          "type": "string",
          "enum": [
            "await_reconciliation",
            "review_recorded",
            "escalated"
          ],
          "title": "Next Action"
        },
        "refund_execution_enabled": {
          "type": "boolean",
          "const": false,
          "title": "Refund Execution Enabled",
          "default": false
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "decision_id",
        "case_id",
        "case_revision",
        "order_id",
        "order_revision",
        "decision",
        "effective_decision",
        "dispute_fence",
        "next_action"
      ],
      "title": "DecisionReceipt"
    },
    "Detail": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "user": {
          "$ref": "#/components/schemas/User"
        },
        "application_suspension": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/Suspension"
            },
            {
              "$ref": "#/components/schemas/StateUnavailable"
            },
            {
              "$ref": "#/components/schemas/ApplicationState"
            }
          ],
          "title": "Application Suspension"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "user"
      ],
      "title": "Detail"
    },
    "DownloadRequest": {
      "properties": {
        "grant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Grant Id"
        },
        "download_token": {
          "type": "string",
          "pattern": "^[A-Za-z0-9_-]{43}$",
          "title": "Download Token"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "grant_id",
        "download_token"
      ],
      "title": "DownloadRequest"
    },
    "DraftEditRequest": {
      "properties": {
        "content": {
          "$ref": "#/components/schemas/Content"
        },
        "version_note": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Version Note"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "content",
        "version_note"
      ],
      "title": "DraftEditRequest"
    },
    "EditReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/RevisionView"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "EditReceipt"
    },
    "EmptyDetails": {
      "properties": {},
      "additionalProperties": false,
      "type": "object",
      "title": "EmptyDetails"
    },
    "Error": {
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "PROVIDER_UNAVAILABLE",
            "VALIDATION_ERROR"
          ],
          "title": "Code"
        },
        "message": {
          "type": "string",
          "enum": [
            "Service temporarily unavailable.",
            "Invalid request."
          ],
          "title": "Message"
        },
        "details": {
          "$ref": "#/components/schemas/ErrorDetails"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "code",
        "message",
        "details"
      ],
      "title": "Error"
    },
    "ErrorBody": {
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "AUTH_REQUIRED",
            "FORBIDDEN",
            "REAUTH_REQUIRED",
            "NOT_FOUND",
            "CONFLICT",
            "IDEMPOTENCY_KEY_REUSED",
            "VERSION_MISMATCH",
            "FILE_TOO_LARGE",
            "VALIDATION_ERROR",
            "RATE_LIMITED",
            "PROVIDER_UNAVAILABLE",
            "METHOD_NOT_ALLOWED"
          ],
          "title": "Code"
        },
        "message": {
          "type": "string",
          "title": "Message"
        },
        "message_ur": {
          "type": "string",
          "title": "Message Ur"
        },
        "request_id": {
          "type": "string",
          "title": "Request Id"
        },
        "details": {
          "additionalProperties": true,
          "type": "object",
          "maxProperties": 0,
          "title": "Details"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "code",
        "message",
        "message_ur",
        "request_id",
        "details"
      ],
      "title": "ErrorBody"
    },
    "ErrorContent": {
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "AUTH_REQUIRED",
            "FORBIDDEN",
            "VALIDATION_ERROR",
            "PROVIDER_UNAVAILABLE",
            "METHOD_NOT_ALLOWED"
          ],
          "title": "Code"
        },
        "message": {
          "type": "string",
          "title": "Message"
        },
        "message_ur": {
          "type": "string",
          "title": "Message Ur"
        },
        "request_id": {
          "type": "string",
          "pattern": "^[a-f0-9]{32}$",
          "title": "Request Id"
        },
        "details": {
          "additionalProperties": true,
          "type": "object",
          "maxProperties": 0,
          "title": "Details"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "code",
        "message",
        "message_ur",
        "request_id",
        "details"
      ],
      "title": "ErrorContent"
    },
    "ErrorDetails": {
      "properties": {},
      "additionalProperties": false,
      "type": "object",
      "title": "ErrorDetails"
    },
    "ErrorEnvelope": {
      "properties": {
        "error": {
          "$ref": "#/components/schemas/ErrorContent"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "error"
      ],
      "title": "ErrorEnvelope"
    },
    "ErrorResponse": {
      "properties": {
        "error": {
          "$ref": "#/components/schemas/Error"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "error"
      ],
      "title": "ErrorResponse"
    },
    "EvidenceRequest": {
      "properties": {
        "upload_token": {
          "type": "string",
          "maxLength": 4000,
          "minLength": 40,
          "title": "Upload Token"
        },
        "sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Sha256"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "upload_token",
        "sha256"
      ],
      "title": "EvidenceRequest"
    },
    "Filters": {
      "properties": {
        "user_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "User Id"
        },
        "email_verified": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Email Verified"
        },
        "provider_access": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "banned",
                "not_banned"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Provider Access"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "Filters"
    },
    "FinanceOrder": {
      "properties": {
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "title": "Order Number"
        },
        "order_status": {
          "type": "string",
          "enum": [
            "draft",
            "placed",
            "processing",
            "fulfilled",
            "cancelled"
          ],
          "title": "Order Status"
        },
        "payment_status": {
          "type": "string",
          "enum": [
            "awaiting_transfer",
            "proof_submitted",
            "under_review",
            "verified",
            "rejected",
            "refunded"
          ],
          "title": "Payment Status"
        },
        "fulfillment_status": {
          "type": "string",
          "enum": [
            "unallocated",
            "allocated",
            "packed",
            "dispatched",
            "delivered",
            "exception"
          ],
          "title": "Fulfillment Status"
        },
        "currency_code": {
          "type": "string",
          "title": "Currency Code"
        },
        "total_pkr": {
          "type": "string",
          "title": "Total Pkr"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "placed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Placed At"
        },
        "projection": {
          "type": "string",
          "const": "finance",
          "title": "Projection",
          "default": "finance"
        }
      },
      "type": "object",
      "required": [
        "order_id",
        "order_number",
        "order_status",
        "payment_status",
        "fulfillment_status",
        "currency_code",
        "total_pkr",
        "created_at",
        "placed_at"
      ],
      "title": "FinanceOrder"
    },
    "FinancialDecision": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "expected_order_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Order Revision"
        },
        "decision": {
          "type": "string",
          "enum": [
            "investigate",
            "confirm_dispute",
            "resolve_no_change",
            "escalate"
          ],
          "title": "Decision"
        },
        "settlement_review_reference": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settlement Review Reference"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "review_started",
            "settlement_disputed",
            "no_financial_change",
            "requires_review"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision",
        "expected_order_revision",
        "decision",
        "reason_code"
      ],
      "title": "FinancialDecision"
    },
    "FinderLocation": {
      "properties": {
        "latitude": {
          "type": "number",
          "maximum": 90.0,
          "minimum": -90.0,
          "title": "Latitude"
        },
        "longitude": {
          "type": "number",
          "maximum": 180.0,
          "minimum": -180.0,
          "title": "Longitude"
        },
        "accuracy_m": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 100000.0,
              "minimum": 0.0
            },
            {
              "type": "null"
            }
          ],
          "title": "Accuracy M"
        },
        "consent_accepted": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Consent Accepted"
        },
        "consent_version": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "location-v1",
                "finder-location-v1"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Consent Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "latitude",
        "longitude"
      ],
      "title": "FinderLocation"
    },
    "FinderMessageRequest": {
      "properties": {
        "finder_name": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 80
            },
            {
              "type": "null"
            }
          ],
          "title": "Finder Name"
        },
        "finder_email": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 254
            },
            {
              "type": "null"
            }
          ],
          "title": "Finder Email"
        },
        "finder_phone": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 16
            },
            {
              "type": "null"
            }
          ],
          "title": "Finder Phone"
        },
        "preferred_contact": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^(email|phone)$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Preferred Contact"
        },
        "message": {
          "type": "string",
          "maxLength": 1000,
          "minLength": 10,
          "title": "Message"
        },
        "contact_consent_accepted": {
          "type": "boolean",
          "title": "Contact Consent Accepted",
          "default": false
        },
        "contact_consent_version": {
          "type": "string",
          "pattern": "^(finder-public-v1|finder-v1)$",
          "title": "Contact Consent Version"
        },
        "location": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/FinderLocation"
            },
            {
              "type": "null"
            }
          ]
        },
        "location_consent": {
          "type": "boolean",
          "title": "Location Consent",
          "default": false
        },
        "turnstile_token": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2048,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Turnstile Token"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "message",
        "contact_consent_version"
      ],
      "title": "FinderMessageRequest"
    },
    "FinderReceipt": {
      "properties": {
        "status": {
          "type": "string",
          "const": "accepted",
          "title": "Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status"
      ],
      "title": "FinderReceipt"
    },
    "GenerateRequest": {
      "properties": {
        "batch_label": {
          "type": "string",
          "maxLength": 40,
          "minLength": 3,
          "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]+$",
          "title": "Batch Label"
        },
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "quantity": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 1.0,
          "title": "Quantity"
        },
        "ecc_level": {
          "type": "string",
          "enum": [
            "M",
            "Q"
          ],
          "title": "Ecc Level",
          "default": "Q"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "batch_label",
        "qr_type",
        "quantity"
      ],
      "title": "GenerateRequest"
    },
    "GenerationReceipt": {
      "properties": {
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "generated_quantity": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 1.0,
          "title": "Generated Quantity"
        },
        "status": {
          "type": "string",
          "const": "generated",
          "title": "Status"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "batch_id",
        "batch_label",
        "qr_type",
        "generated_quantity",
        "status",
        "created_at"
      ],
      "title": "GenerationReceipt"
    },
    "GrantReceipt": {
      "properties": {
        "grant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Grant Id"
        },
        "grant_token": {
          "type": "string",
          "pattern": "^[A-Za-z0-9_-]{43}$",
          "title": "Grant Token"
        },
        "job_id": {
          "type": "string",
          "format": "uuid",
          "title": "Job Id"
        },
        "revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Revision"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "title": "Expires At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "grant_id",
        "grant_token",
        "job_id",
        "revision",
        "expires_at"
      ],
      "title": "GrantReceipt"
    },
    "GrantRequest": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision"
      ],
      "title": "GrantRequest"
    },
    "Group": {
      "properties": {
        "group": {
          "type": "string",
          "enum": [
            "catalog",
            "inventory",
            "fulfillment",
            "printing",
            "finance",
            "notifications",
            "support",
            "finance_mirror"
          ],
          "title": "Group"
        },
        "status": {
          "type": "string",
          "enum": [
            "ready",
            "unavailable"
          ],
          "title": "Status"
        },
        "as_of": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "As Of"
        },
        "metrics": {
          "items": {
            "$ref": "#/components/schemas/Metric"
          },
          "type": "array",
          "maxItems": 8,
          "title": "Metrics"
        },
        "reason_code": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "QUERY_UNAVAILABLE",
                "DRILLDOWN_UNAVAILABLE",
                "FEATURE_DISABLED",
                "LOW_STOCK_UNCONFIGURED",
                "REQUEST_BUDGET_EXHAUSTED"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "group",
        "status",
        "as_of",
        "metrics",
        "reason_code"
      ],
      "title": "Group"
    },
    "HTTPValidationError": {
      "properties": {
        "detail": {
          "items": {
            "$ref": "#/components/schemas/ValidationError"
          },
          "type": "array",
          "title": "Detail"
        }
      },
      "type": "object",
      "title": "HTTPValidationError"
    },
    "History": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "pair_revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Pair Revision"
        },
        "current_tags": {
          "items": {
            "$ref": "#/components/schemas/Tag"
          },
          "type": "array",
          "maxItems": 2,
          "minItems": 2,
          "title": "Current Tags"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__qr_lifecycle__Event"
          },
          "type": "array",
          "maxItems": 101,
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "pair_id",
        "pair_revision",
        "current_tags",
        "items",
        "next_cursor"
      ],
      "title": "History"
    },
    "HistoryEntry": {
      "properties": {
        "decision_id": {
          "type": "string",
          "format": "uuid",
          "title": "Decision Id"
        },
        "revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Revision"
        },
        "decision": {
          "type": "string",
          "enum": [
            "investigate",
            "confirm_dispute",
            "resolve_no_change",
            "escalate"
          ],
          "title": "Decision"
        },
        "effective_decision": {
          "type": "string",
          "enum": [
            "investigate",
            "confirm_dispute",
            "resolve_no_change",
            "escalate"
          ],
          "title": "Effective Decision"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "review_started",
            "settlement_disputed",
            "no_financial_change",
            "requires_review"
          ],
          "title": "Reason Code"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "decision_id",
        "revision",
        "decision",
        "effective_decision",
        "reason_code",
        "created_at"
      ],
      "title": "HistoryEntry"
    },
    "ICEEdit": {
      "properties": {
        "display_name": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Name"
        },
        "blood_group": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "A+",
                "A-",
                "B+",
                "B-",
                "AB+",
                "AB-",
                "O+",
                "O-"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Blood Group"
        },
        "emergency_instructions": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 1000
            },
            {
              "type": "null"
            }
          ],
          "title": "Emergency Instructions"
        },
        "medical_notes": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 1000,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Medical Notes"
        },
        "show_medical_notes": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Show Medical Notes"
        },
        "published": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Published"
        },
        "publication_consent_accepted": {
          "type": "boolean",
          "title": "Publication Consent Accepted",
          "default": false
        },
        "publication_consent_version": {
          "anyOf": [
            {
              "type": "string",
              "const": "ice-public-v1"
            },
            {
              "type": "null"
            }
          ],
          "title": "Publication Consent Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "ICEEdit"
    },
    "ICEProfile": {
      "properties": {
        "display_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Name"
        },
        "blood_group": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Blood Group"
        },
        "medical_notes": {
          "type": "null",
          "title": "Medical Notes"
        },
        "contacts": {
          "items": {
            "$ref": "#/components/schemas/PublicContact"
          },
          "type": "array",
          "title": "Contacts"
        },
        "owner_information_disclaimer": {
          "type": "string",
          "title": "Owner Information Disclaimer"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "display_name",
        "blood_group",
        "contacts",
        "owner_information_disclaimer"
      ],
      "title": "ICEProfile"
    },
    "ImageMetadataRequest": {
      "properties": {
        "alt_text": {
          "type": "string",
          "maxLength": 240,
          "minLength": 1,
          "title": "Alt Text"
        },
        "sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Sort Order",
          "default": 0
        },
        "is_primary": {
          "type": "boolean",
          "title": "Is Primary"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "alt_text",
        "is_primary"
      ],
      "title": "ImageMetadataRequest"
    },
    "ImageRequest": {
      "properties": {
        "cloudinary_public_id": {
          "type": "string",
          "pattern": "^[A-Za-z0-9/_-]{1,240}$",
          "title": "Cloudinary Public Id"
        },
        "alt_text": {
          "type": "string",
          "maxLength": 240,
          "minLength": 1,
          "title": "Alt Text"
        },
        "sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Sort Order",
          "default": 0
        },
        "is_primary": {
          "type": "boolean",
          "title": "Is Primary",
          "default": false
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "cloudinary_public_id",
        "alt_text"
      ],
      "title": "ImageRequest"
    },
    "Intake": {
      "properties": {
        "case_type": {
          "type": "string",
          "enum": [
            "activation",
            "lost_tag",
            "payment",
            "privacy",
            "ownership_dispute",
            "other"
          ],
          "title": "Case Type"
        },
        "priority": {
          "type": "string",
          "enum": [
            "low",
            "normal",
            "high",
            "urgent"
          ],
          "title": "Priority",
          "default": "normal"
        },
        "pair_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Pair Id"
        },
        "order_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Order Id"
        },
        "description": {
          "type": "string",
          "maxLength": 2000,
          "minLength": 4,
          "title": "Description"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "case_type",
        "description"
      ],
      "title": "Intake"
    },
    "IntentRequest": {
      "properties": {
        "scanned_token": {
          "type": "string",
          "maxLength": 80,
          "minLength": 1,
          "pattern": "^[A-Za-z0-9_-]+$",
          "title": "Scanned Token"
        },
        "activation_secret": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 256,
              "minLength": 12,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Activation Secret"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "scanned_token"
      ],
      "title": "IntentRequest"
    },
    "IntentResponse": {
      "properties": {
        "intent_id": {
          "type": "string",
          "format": "uuid",
          "title": "Intent Id"
        },
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "lost_qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Lost Qr Id"
        },
        "ice_qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Ice Qr Id"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "title": "Expires At"
        },
        "method": {
          "type": "string",
          "enum": [
            "order_entitlement",
            "concealed_credential"
          ],
          "title": "Method"
        }
      },
      "type": "object",
      "required": [
        "intent_id",
        "pair_id",
        "lost_qr_id",
        "ice_qr_id",
        "expires_at",
        "method"
      ],
      "title": "IntentResponse"
    },
    "Item-Input": {
      "properties": {
        "product_id": {
          "type": "string",
          "format": "uuid",
          "title": "Product Id"
        },
        "identity_group": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9_-]{1,80}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Identity Group"
        },
        "sizes": {
          "items": {
            "$ref": "#/components/schemas/SizeSelection"
          },
          "type": "array",
          "maxItems": 50,
          "minItems": 1,
          "title": "Sizes"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "product_id",
        "sizes"
      ],
      "title": "Item"
    },
    "ItemQuoteRequest": {
      "properties": {
        "address": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/Address"
            },
            {
              "type": "null"
            }
          ]
        },
        "shipping_address_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Shipping Address Id"
        },
        "shipping_address_version": {
          "anyOf": [
            {
              "type": "integer",
              "maximum": 2147483646.0,
              "minimum": 1.0
            },
            {
              "type": "null"
            }
          ],
          "title": "Shipping Address Version"
        },
        "contact_phone_confirmation": {
          "type": "boolean",
          "title": "Contact Phone Confirmation"
        },
        "commerce_model": {
          "type": "string",
          "const": "single_qr",
          "title": "Commerce Model"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/Item-Input"
          },
          "type": "array",
          "maxItems": 50,
          "minItems": 1,
          "title": "Items"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "contact_phone_confirmation",
        "commerce_model",
        "items"
      ],
      "title": "ItemQuoteRequest"
    },
    "JobQARequest": {
      "properties": {
        "approved": {
          "type": "boolean",
          "title": "Approved"
        },
        "artifact_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Artifact Sha256"
        },
        "observed": {
          "items": {
            "$ref": "#/components/schemas/Observation"
          },
          "type": "array",
          "maxItems": 50,
          "minItems": 1,
          "title": "Observed"
        },
        "scan_passed": {
          "type": "boolean",
          "title": "Scan Passed"
        },
        "logo_quiet_zone_passed": {
          "type": "boolean",
          "title": "Logo Quiet Zone Passed"
        },
        "bilingual_passed": {
          "type": "boolean",
          "title": "Bilingual Passed"
        },
        "cutting_packaging_passed": {
          "type": "boolean",
          "title": "Cutting Packaging Passed"
        },
        "actual_scale_passed": {
          "type": "boolean",
          "title": "Actual Scale Passed"
        },
        "reason": {
          "type": "string",
          "maxLength": 1000,
          "minLength": 4,
          "title": "Reason"
        },
        "inspected_item_ids": {
          "items": {
            "type": "string",
            "format": "uuid"
          },
          "type": "array",
          "maxItems": 50,
          "title": "Inspected Item Ids"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "approved",
        "artifact_sha256",
        "observed",
        "scan_passed",
        "logo_quiet_zone_passed",
        "bilingual_passed",
        "cutting_packaging_passed",
        "actual_scale_passed",
        "reason"
      ],
      "title": "JobQARequest"
    },
    "LastBatch": {
      "properties": {
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "status": {
          "type": "string",
          "title": "Status"
        },
        "generated_at": {
          "type": "string",
          "format": "date-time",
          "title": "Generated At"
        }
      },
      "type": "object",
      "required": [
        "batch_id",
        "batch_label",
        "status",
        "generated_at"
      ],
      "title": "LastBatch"
    },
    "LatestQA": {
      "properties": {
        "qa_round": {
          "type": "integer",
          "title": "Qa Round"
        },
        "approved": {
          "type": "boolean",
          "title": "Approved"
        },
        "inspected_at": {
          "type": "string",
          "format": "date-time",
          "title": "Inspected At"
        }
      },
      "type": "object",
      "required": [
        "qa_round",
        "approved",
        "inspected_at"
      ],
      "title": "LatestQA"
    },
    "LiveAllocation": {
      "properties": {
        "unit_id": {
          "type": "string",
          "format": "uuid",
          "title": "Unit Id"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "status": {
          "type": "string",
          "title": "Status"
        },
        "reserved_until": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Reserved Until"
        },
        "allocated_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Allocated At"
        }
      },
      "type": "object",
      "required": [
        "unit_id",
        "order_id",
        "status",
        "reserved_until",
        "allocated_at"
      ],
      "title": "LiveAllocation"
    },
    "Liveness": {
      "properties": {
        "status": {
          "type": "string",
          "const": "ok",
          "title": "Status",
          "default": "ok"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "Liveness"
    },
    "LostEdit": {
      "properties": {
        "item_label": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Item Label"
        },
        "description": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 1000
            },
            {
              "type": "null"
            }
          ],
          "title": "Description"
        },
        "reward_text": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 200
            },
            {
              "type": "null"
            }
          ],
          "title": "Reward Text"
        },
        "return_instructions": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 1000
            },
            {
              "type": "null"
            }
          ],
          "title": "Return Instructions"
        },
        "published": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Published"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "LostEdit"
    },
    "LostItem": {
      "properties": {
        "label": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Label"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Description"
        },
        "reward_text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Reward Text"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "label",
        "description",
        "reward_text"
      ],
      "title": "LostItem"
    },
    "MaskedContact": {
      "properties": {
        "phone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Phone"
        }
      },
      "type": "object",
      "required": [
        "phone"
      ],
      "title": "MaskedContact"
    },
    "MessageUpdate": {
      "properties": {
        "status": {
          "type": "string",
          "pattern": "^(viewed|archived|flagged)$",
          "title": "Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status"
      ],
      "title": "MessageUpdate"
    },
    "Metadata": {
      "properties": {
        "job_id": {
          "type": "string",
          "format": "uuid",
          "title": "Job Id"
        },
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Revision"
        },
        "status": {
          "type": "string",
          "enum": [
            "queued",
            "ready",
            "awaiting_ack",
            "accepted",
            "failed"
          ],
          "title": "Status"
        },
        "manifest_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Manifest Sha256"
        },
        "pair_count": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 1.0,
          "title": "Pair Count"
        },
        "tag_count": {
          "type": "integer",
          "maximum": 2000.0,
          "minimum": 2.0,
          "title": "Tag Count"
        },
        "attempt_count": {
          "type": "integer",
          "maximum": 5.0,
          "minimum": 0.0,
          "title": "Attempt Count"
        },
        "physical_release_enabled": {
          "type": "boolean",
          "const": false,
          "title": "Physical Release Enabled",
          "default": false
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "job_id",
        "batch_id",
        "revision",
        "status",
        "manifest_sha256",
        "pair_count",
        "tag_count",
        "attempt_count"
      ],
      "title": "Metadata"
    },
    "Metric": {
      "properties": {
        "metric_id": {
          "type": "string",
          "title": "Metric Id"
        },
        "unit": {
          "type": "string",
          "enum": [
            "product",
            "variant",
            "pair",
            "qr_identity",
            "order",
            "attempt",
            "job",
            "shipment",
            "outbox_event",
            "case",
            "sync_record"
          ],
          "title": "Unit"
        },
        "count": {
          "$ref": "#/components/schemas/Count"
        },
        "drilldown": {
          "type": "string",
          "title": "Drilldown"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "metric_id",
        "unit",
        "count",
        "drilldown"
      ],
      "title": "Metric"
    },
    "NewRevision": {
      "properties": {
        "content": {
          "$ref": "#/components/schemas/Content"
        },
        "version_note": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Version Note"
        },
        "base_revision_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Base Revision Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "content",
        "version_note",
        "base_revision_id"
      ],
      "title": "NewRevision"
    },
    "Observation": {
      "properties": {
        "tag_type": {
          "type": "string",
          "pattern": "^(lost|ice)$",
          "title": "Tag Type"
        },
        "symbol_mm": {
          "type": "string",
          "pattern": "^[0-9]{2,3}(?:\\.[0-9]{1,2})?$",
          "title": "Symbol Mm"
        },
        "copies": {
          "type": "integer",
          "maximum": 5000.0,
          "minimum": 1.0,
          "title": "Copies"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "tag_type",
        "symbol_mm",
        "copies"
      ],
      "title": "Observation"
    },
    "OperationsOrder": {
      "properties": {
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "title": "Order Number"
        },
        "order_status": {
          "type": "string",
          "enum": [
            "draft",
            "placed",
            "processing",
            "fulfilled",
            "cancelled"
          ],
          "title": "Order Status"
        },
        "payment_status": {
          "type": "string",
          "enum": [
            "awaiting_transfer",
            "proof_submitted",
            "under_review",
            "verified",
            "rejected",
            "refunded"
          ],
          "title": "Payment Status"
        },
        "fulfillment_status": {
          "type": "string",
          "enum": [
            "unallocated",
            "allocated",
            "packed",
            "dispatched",
            "delivered",
            "exception"
          ],
          "title": "Fulfillment Status"
        },
        "currency_code": {
          "type": "string",
          "title": "Currency Code"
        },
        "total_pkr": {
          "type": "string",
          "title": "Total Pkr"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "placed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Placed At"
        },
        "projection": {
          "type": "string",
          "const": "operations",
          "title": "Projection",
          "default": "operations"
        },
        "shipment_count": {
          "type": "integer",
          "title": "Shipment Count"
        },
        "latest_shipment": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/ShipmentMetadata"
            },
            {
              "type": "null"
            }
          ]
        },
        "fulfillment_eligible": {
          "type": "boolean",
          "title": "Fulfillment Eligible"
        }
      },
      "type": "object",
      "required": [
        "order_id",
        "order_number",
        "order_status",
        "payment_status",
        "fulfillment_status",
        "currency_code",
        "total_pkr",
        "created_at",
        "placed_at",
        "shipment_count",
        "latest_shipment",
        "fulfillment_eligible"
      ],
      "title": "OperationsOrder"
    },
    "OrderPage": {
      "properties": {
        "items": {
          "items": {
            "oneOf": [
              {
                "$ref": "#/components/schemas/FinanceOrder"
              },
              {
                "$ref": "#/components/schemas/OperationsOrder"
              }
            ],
            "discriminator": {
              "propertyName": "projection",
              "mapping": {
                "finance": "#/components/schemas/FinanceOrder",
                "operations": "#/components/schemas/OperationsOrder"
              }
            }
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "OrderPage"
    },
    "PackedPair": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "packed_qa_confirmed": {
          "type": "boolean",
          "title": "Packed Qa Confirmed"
        },
        "packed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Packed At"
        }
      },
      "type": "object",
      "required": [
        "pair_id",
        "packed_qa_confirmed",
        "packed_at"
      ],
      "title": "PackedPair"
    },
    "PackedPairPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/PackedPair"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "PackedPairPage"
    },
    "PairDetail": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "pair_reference": {
          "type": "string",
          "title": "Pair Reference"
        },
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "inventory_status": {
          "type": "string",
          "title": "Inventory Status"
        },
        "ownership_status": {
          "type": "string",
          "title": "Ownership Status"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "current_tags": {
          "items": {
            "$ref": "#/components/schemas/TagMetadata"
          },
          "type": "array",
          "title": "Current Tags"
        },
        "latest_qa": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/LatestQA"
            },
            {
              "type": "null"
            }
          ]
        },
        "live_allocation": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/LiveAllocation"
            },
            {
              "type": "null"
            }
          ]
        },
        "historical_tags": {
          "$ref": "#/components/schemas/TagHistory"
        }
      },
      "type": "object",
      "required": [
        "pair_id",
        "pair_reference",
        "batch_id",
        "inventory_status",
        "ownership_status",
        "created_at",
        "current_tags",
        "latest_qa",
        "live_allocation",
        "historical_tags"
      ],
      "title": "PairDetail"
    },
    "PairMetadata": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "pair_reference": {
          "type": "string",
          "title": "Pair Reference"
        },
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "inventory_status": {
          "type": "string",
          "title": "Inventory Status"
        },
        "ownership_status": {
          "type": "string",
          "title": "Ownership Status"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "current_tags": {
          "items": {
            "$ref": "#/components/schemas/TagMetadata"
          },
          "type": "array",
          "title": "Current Tags"
        },
        "latest_qa": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/LatestQA"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "type": "object",
      "required": [
        "pair_id",
        "pair_reference",
        "batch_id",
        "inventory_status",
        "ownership_status",
        "created_at",
        "current_tags",
        "latest_qa"
      ],
      "title": "PairMetadata"
    },
    "PairSummary": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "pair_reference": {
          "type": "string",
          "title": "Pair Reference"
        },
        "ownership_status": {
          "type": "string",
          "title": "Ownership Status"
        },
        "inventory_status": {
          "type": "string",
          "title": "Inventory Status"
        },
        "activated_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Activated At"
        },
        "tags": {
          "items": {
            "$ref": "#/components/schemas/TagSummary"
          },
          "type": "array",
          "title": "Tags"
        }
      },
      "type": "object",
      "required": [
        "pair_id",
        "pair_reference",
        "ownership_status",
        "inventory_status",
        "activated_at",
        "tags"
      ],
      "title": "PairSummary"
    },
    "PaymentRequest": {
      "properties": {
        "provider_key": {
          "type": "string",
          "const": "manual_bank",
          "title": "Provider Key",
          "default": "manual_bank"
        },
        "sender_account": {
          "type": "string",
          "maxLength": 80,
          "minLength": 4,
          "title": "Sender Account"
        },
        "sender_holder_name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Sender Holder Name"
        },
        "transfer_reference": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Transfer Reference"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "sender_account",
        "sender_holder_name"
      ],
      "title": "PaymentRequest"
    },
    "PhysicalProduct": {
      "properties": {
        "product_name_snapshot": {
          "type": "string",
          "title": "Product Name Snapshot"
        },
        "variant_name_snapshot": {
          "type": "string",
          "title": "Variant Name Snapshot"
        },
        "copies": {
          "type": "integer",
          "title": "Copies"
        }
      },
      "type": "object",
      "required": [
        "product_name_snapshot",
        "variant_name_snapshot",
        "copies"
      ],
      "title": "PhysicalProduct"
    },
    "Policies": {
      "properties": {
        "privacy": {
          "$ref": "#/components/schemas/PolicyMetadata"
        },
        "terms": {
          "$ref": "#/components/schemas/PolicyMetadata"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "privacy",
        "terms"
      ],
      "title": "Policies"
    },
    "PolicyMetadata": {
      "properties": {
        "status": {
          "type": "string",
          "enum": [
            "available",
            "unavailable"
          ],
          "title": "Status"
        },
        "version": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9._:-]{1,80}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Version"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Url"
        },
        "locale": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "en",
                "ur"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Locale"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status",
        "version",
        "url",
        "locale"
      ],
      "title": "PolicyMetadata"
    },
    "PreferenceEdit": {
      "properties": {
        "whatsapp_enabled": {
          "type": "boolean",
          "title": "Whatsapp Enabled"
        },
        "whatsapp_phone": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 16,
              "minLength": 8,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Whatsapp Phone"
        },
        "public_disclosure_consent": {
          "type": "boolean",
          "title": "Public Disclosure Consent",
          "default": false
        },
        "consent_version": {
          "anyOf": [
            {
              "type": "string",
              "const": "wa-public-v1"
            },
            {
              "type": "null"
            }
          ],
          "title": "Consent Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "whatsapp_enabled"
      ],
      "title": "PreferenceEdit"
    },
    "Preview": {
      "properties": {
        "expected_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Expected Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "expected_revision"
      ],
      "title": "Preview"
    },
    "PrintJobRequest": {
      "properties": {
        "reason": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Reason"
        },
        "expected_revision": {
          "type": "integer",
          "minimum": 0.0,
          "title": "Expected Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "reason",
        "expected_revision"
      ],
      "title": "PrintJobRequest"
    },
    "PrintQARequest": {
      "properties": {
        "qa_round": {
          "type": "integer",
          "maximum": 1000.0,
          "minimum": 1.0,
          "title": "Qa Round"
        },
        "lost_scan_passed": {
          "type": "boolean",
          "title": "Lost Scan Passed"
        },
        "ice_scan_passed": {
          "type": "boolean",
          "title": "Ice Scan Passed"
        },
        "pair_match_passed": {
          "type": "boolean",
          "title": "Pair Match Passed"
        },
        "credential_concealed": {
          "type": "boolean",
          "title": "Credential Concealed"
        },
        "bilingual_label_passed": {
          "type": "boolean",
          "title": "Bilingual Label Passed"
        },
        "quiet_zone_passed": {
          "type": "boolean",
          "title": "Quiet Zone Passed"
        },
        "indoor_size_passed": {
          "type": "boolean",
          "title": "Indoor Size Passed"
        },
        "outdoor_size_passed": {
          "type": "boolean",
          "title": "Outdoor Size Passed"
        },
        "packaging_method": {
          "type": "string",
          "pattern": "^(scratch_off|sealed_sleeve|peel_seal)$",
          "title": "Packaging Method"
        },
        "tamper_evidence_passed": {
          "type": "boolean",
          "title": "Tamper Evidence Passed"
        },
        "approved": {
          "type": "boolean",
          "title": "Approved"
        },
        "notes": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2000
            },
            {
              "type": "null"
            }
          ],
          "title": "Notes"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "qa_round",
        "lost_scan_passed",
        "ice_scan_passed",
        "pair_match_passed",
        "credential_concealed",
        "bilingual_label_passed",
        "quiet_zone_passed",
        "indoor_size_passed",
        "outdoor_size_passed",
        "packaging_method",
        "tamper_evidence_passed",
        "approved"
      ],
      "title": "PrintQARequest"
    },
    "ProductRequest": {
      "properties": {
        "category_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Category Id"
        },
        "slug": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9-]{1,99}$",
          "title": "Slug"
        },
        "name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Name"
        },
        "description": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 4000
            },
            {
              "type": "null"
            }
          ],
          "title": "Description"
        },
        "lifecycle_status": {
          "type": "string",
          "enum": [
            "draft",
            "published",
            "archived"
          ],
          "title": "Lifecycle Status",
          "default": "draft"
        },
        "price_per_copy": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 9999999999.99,
              "minimum": 0.0
            },
            {
              "type": "string"
            }
          ],
          "title": "Price Per Copy"
        },
        "max_order_copies": {
          "type": "integer",
          "maximum": 100.0,
          "minimum": 1.0,
          "title": "Max Order Copies",
          "default": 100
        },
        "qr_type": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "lost",
                "ice"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Qr Type"
        },
        "is_featured": {
          "type": "boolean",
          "title": "Is Featured",
          "default": false
        },
        "featured_sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Featured Sort Order",
          "default": 0
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "slug",
        "name",
        "price_per_copy"
      ],
      "title": "ProductRequest"
    },
    "PublicActivationContext": {
      "properties": {
        "status": {
          "type": "string",
          "const": "not_activated",
          "title": "Status"
        },
        "can_begin": {
          "type": "boolean",
          "const": true,
          "title": "Can Begin"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "context_ttl_seconds": {
          "type": "integer",
          "title": "Context Ttl Seconds"
        }
      },
      "type": "object",
      "required": [
        "status",
        "can_begin",
        "tag_type",
        "context_ttl_seconds"
      ],
      "title": "PublicActivationContext"
    },
    "PublicConfiguration": {
      "properties": {
        "supported_locales": {
          "prefixItems": [
            {
              "type": "string",
              "const": "en"
            },
            {
              "type": "string",
              "const": "ur"
            }
          ],
          "type": "array",
          "maxItems": 2,
          "minItems": 2,
          "title": "Supported Locales"
        },
        "default_locale": {
          "type": "string",
          "const": "en",
          "title": "Default Locale"
        },
        "locale": {
          "type": "string",
          "enum": [
            "en",
            "ur"
          ],
          "title": "Locale"
        },
        "public_features": {
          "$ref": "#/components/schemas/ConfigurationFeatures"
        },
        "max_finder_message_length": {
          "type": "integer",
          "const": 1000,
          "title": "Max Finder Message Length"
        },
        "privacy_policy_version": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9._:-]{1,80}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Privacy Policy Version"
        },
        "policies": {
          "$ref": "#/components/schemas/Policies"
        },
        "consent_versions": {
          "$ref": "#/components/schemas/ConsentVersions"
        },
        "support": {
          "$ref": "#/components/schemas/SupportMetadata"
        },
        "policy_publication_ready": {
          "type": "boolean",
          "title": "Policy Publication Ready"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "supported_locales",
        "default_locale",
        "locale",
        "public_features",
        "max_finder_message_length",
        "privacy_policy_version",
        "policies",
        "consent_versions",
        "support",
        "policy_publication_ready"
      ],
      "title": "PublicConfiguration"
    },
    "PublicContact": {
      "properties": {
        "contact_id": {
          "type": "string",
          "format": "uuid",
          "title": "Contact Id"
        },
        "relationship_label": {
          "type": "string",
          "title": "Relationship Label"
        },
        "display_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Display Name"
        },
        "reveal_available": {
          "type": "boolean",
          "title": "Reveal Available"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "contact_id",
        "relationship_label",
        "display_name",
        "reveal_available"
      ],
      "title": "PublicContact"
    },
    "PublicFeatures": {
      "properties": {
        "finder_form_enabled": {
          "type": "boolean",
          "title": "Finder Form Enabled"
        },
        "whatsapp_contact_enabled": {
          "type": "boolean",
          "title": "Whatsapp Contact Enabled"
        },
        "location_sharing_available": {
          "type": "boolean",
          "title": "Location Sharing Available"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "finder_form_enabled",
        "whatsapp_contact_enabled",
        "location_sharing_available"
      ],
      "title": "PublicFeatures"
    },
    "PublicQRProfile": {
      "properties": {
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "status": {
          "type": "string",
          "enum": [
            "unactivated",
            "active",
            "owner_disabled",
            "admin_suspended",
            "revoked"
          ],
          "title": "Status"
        },
        "locale_options": {
          "items": {
            "type": "string",
            "enum": [
              "en",
              "ur"
            ]
          },
          "type": "array",
          "title": "Locale Options"
        },
        "lost_item": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/LostItem"
            },
            {
              "type": "null"
            }
          ]
        },
        "features": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/PublicFeatures"
            },
            {
              "type": "null"
            }
          ]
        },
        "whatsapp_contact": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/WhatsAppContact"
            },
            {
              "type": "null"
            }
          ]
        },
        "ice": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/ICEProfile"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "tag_type",
        "status",
        "locale_options"
      ],
      "title": "PublicQRProfile"
    },
    "Publish": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "approval_id": {
          "type": "string",
          "format": "uuid",
          "title": "Approval Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "approval_id"
      ],
      "title": "Publish"
    },
    "PublishedTemplateReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/PublishedTemplateResult"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "PublishedTemplateReceipt"
    },
    "PublishedTemplateResult": {
      "properties": {
        "revision": {
          "$ref": "#/components/schemas/RevisionView"
        },
        "approval_id": {
          "type": "string",
          "format": "uuid",
          "title": "Approval Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "revision",
        "approval_id"
      ],
      "title": "PublishedTemplateResult"
    },
    "QRDetail": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "pair_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Pair Id"
        },
        "pair_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Pair Reference"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "public_status": {
          "type": "string",
          "title": "Public Status"
        },
        "profile_label": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Profile Label"
        },
        "published": {
          "type": "boolean",
          "title": "Published"
        },
        "profile_version": {
          "type": "integer",
          "title": "Profile Version"
        },
        "preference_version": {
          "type": "integer",
          "title": "Preference Version"
        },
        "profile_complete": {
          "type": "boolean",
          "title": "Profile Complete"
        },
        "editable": {
          "type": "boolean",
          "title": "Editable"
        },
        "editor_url": {
          "type": "string",
          "title": "Editor Url"
        },
        "physical_products": {
          "items": {
            "$ref": "#/components/schemas/PhysicalProduct"
          },
          "type": "array",
          "title": "Physical Products"
        }
      },
      "type": "object",
      "required": [
        "qr_id",
        "pair_id",
        "pair_reference",
        "tag_type",
        "public_status",
        "profile_label",
        "published",
        "profile_version",
        "preference_version",
        "profile_complete",
        "editable",
        "editor_url",
        "physical_products"
      ],
      "title": "QRDetail"
    },
    "QRMetadata": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "serial_number": {
          "type": "string",
          "title": "Serial Number"
        },
        "public_status": {
          "type": "string",
          "title": "Public Status"
        },
        "inventory_status": {
          "type": "string",
          "enum": [
            "available",
            "allocated",
            "retired"
          ],
          "title": "Inventory Status"
        },
        "ownership_status": {
          "type": "string",
          "enum": [
            "unclaimed",
            "active",
            "revoked"
          ],
          "title": "Ownership Status"
        },
        "row_version": {
          "type": "integer",
          "title": "Row Version"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "allocatable": {
          "type": "boolean",
          "title": "Allocatable"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "qr_id",
        "batch_id",
        "batch_label",
        "qr_type",
        "serial_number",
        "public_status",
        "inventory_status",
        "ownership_status",
        "row_version",
        "created_at",
        "allocatable"
      ],
      "title": "QRMetadata"
    },
    "QRUse": {
      "properties": {
        "mode": {
          "type": "string",
          "enum": [
            "new_pair",
            "existing_owned"
          ],
          "title": "Mode"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "copies": {
          "type": "integer",
          "maximum": 100.0,
          "minimum": 1.0,
          "title": "Copies"
        },
        "existing_qr_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Existing Qr Id"
        },
        "client_pair_group": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 80,
              "minLength": 1
            },
            {
              "type": "null"
            }
          ],
          "title": "Client Pair Group"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "mode",
        "tag_type",
        "copies"
      ],
      "title": "QRUse"
    },
    "QuoteRequest": {
      "properties": {
        "address": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/Address"
            },
            {
              "type": "null"
            }
          ]
        },
        "shipping_address_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Shipping Address Id"
        },
        "shipping_address_version": {
          "anyOf": [
            {
              "type": "integer",
              "maximum": 2147483646.0,
              "minimum": 1.0
            },
            {
              "type": "null"
            }
          ],
          "title": "Shipping Address Version"
        },
        "contact_phone_confirmation": {
          "type": "boolean",
          "title": "Contact Phone Confirmation"
        },
        "lines": {
          "items": {
            "$ref": "#/components/schemas/CartLine"
          },
          "type": "array",
          "maxItems": 50,
          "minItems": 1,
          "title": "Lines"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "contact_phone_confirmation",
        "lines"
      ],
      "title": "QuoteRequest"
    },
    "Readiness": {
      "properties": {
        "status": {
          "type": "string",
          "const": "ready",
          "title": "Status",
          "default": "ready"
        },
        "database": {
          "type": "string",
          "const": "ok",
          "title": "Database",
          "default": "ok"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "Readiness"
    },
    "ReadinessUnavailable": {
      "properties": {
        "status": {
          "type": "string",
          "const": "not_ready",
          "title": "Status",
          "default": "not_ready"
        },
        "database": {
          "type": "string",
          "const": "unavailable",
          "title": "Database",
          "default": "unavailable"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "ReadinessUnavailable"
    },
    "Reason": {
      "properties": {
        "reason": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Reason"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "reason"
      ],
      "title": "Reason"
    },
    "Reconciliation": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "request_id": {
          "type": "string",
          "format": "uuid",
          "title": "Request Id"
        },
        "expected_order_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Order Revision"
        },
        "expected_request_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Request Revision"
        },
        "outcome": {
          "type": "string",
          "enum": [
            "clear",
            "escalate"
          ],
          "title": "Outcome"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "no_settlement_pending",
            "settlement_requires_review"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "request_id",
        "expected_order_revision",
        "expected_request_revision",
        "outcome",
        "reason_code"
      ],
      "title": "Reconciliation"
    },
    "Recovery": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "factor_loss",
            "account_access_review"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "case_id",
        "expected_revision",
        "reason_code"
      ],
      "title": "Recovery"
    },
    "ReferralReceipt": {
      "properties": {
        "user_id": {
          "type": "string",
          "format": "uuid",
          "title": "User Id"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "action": {
          "type": "string",
          "const": "recovery_escalated",
          "title": "Action"
        },
        "revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 2.0,
          "title": "Revision"
        },
        "event_id": {
          "type": "string",
          "format": "uuid",
          "title": "Event Id"
        },
        "occurred_at": {
          "type": "string",
          "format": "date-time",
          "title": "Occurred At"
        },
        "status": {
          "type": "string",
          "const": "referred",
          "title": "Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "user_id",
        "case_id",
        "action",
        "revision",
        "event_id",
        "occurred_at",
        "status"
      ],
      "title": "ReferralReceipt"
    },
    "Release": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "request_id": {
          "type": "string",
          "format": "uuid",
          "title": "Request Id"
        },
        "expected_order_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Order Revision"
        },
        "expected_request_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Request Revision"
        },
        "reconciliation_id": {
          "type": "string",
          "format": "uuid",
          "title": "Reconciliation Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "request_id",
        "expected_order_revision",
        "expected_request_revision",
        "reconciliation_id"
      ],
      "title": "Release"
    },
    "Report": {
      "properties": {
        "qr_token": {
          "type": "string",
          "maxLength": 80,
          "minLength": 20,
          "format": "password",
          "title": "Qr Token",
          "writeOnly": true
        },
        "message_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Message Id"
        },
        "category": {
          "type": "string",
          "enum": [
            "spam",
            "fraud",
            "unsafe_content",
            "other"
          ],
          "title": "Category"
        },
        "message": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 500,
              "minLength": 1
            },
            {
              "type": "null"
            }
          ],
          "title": "Message"
        },
        "consent_accepted": {
          "type": "boolean",
          "const": true,
          "title": "Consent Accepted"
        },
        "consent_version": {
          "type": "string",
          "const": "abuse-report-v1",
          "title": "Consent Version"
        },
        "turnstile_token": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2048,
              "minLength": 1,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Turnstile Token"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "qr_token",
        "category",
        "consent_accepted",
        "consent_version"
      ],
      "title": "Report"
    },
    "Restore": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "reason_code": {
          "type": "string",
          "const": "review_cleared",
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "case_id",
        "expected_revision",
        "reason_code"
      ],
      "title": "Restore"
    },
    "RetentionHoldRequest": {
      "properties": {
        "reason_code": {
          "type": "string",
          "pattern": "^[A-Za-z0-9_.-]{1,80}$",
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "reason_code"
      ],
      "title": "RetentionHoldRequest"
    },
    "Retire": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "reason": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Reason"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "reason"
      ],
      "title": "Retire"
    },
    "RetiredTemplateReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/RetiredTemplateResult"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "RetiredTemplateReceipt"
    },
    "RetiredTemplateResult": {
      "properties": {
        "revision": {
          "$ref": "#/components/schemas/RevisionView"
        },
        "template": {
          "$ref": "#/components/schemas/TemplateView"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "revision",
        "template"
      ],
      "title": "RetiredTemplateResult"
    },
    "Retry": {
      "properties": {
        "expected_attempt_count": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Expected Attempt Count"
        },
        "reason": {
          "type": "string",
          "enum": [
            "provider_recovered",
            "recipient_reverified"
          ],
          "title": "Reason"
        },
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "expected_attempt_count",
        "reason",
        "confirmed"
      ],
      "title": "Retry"
    },
    "ReviewProjection": {
      "properties": {
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "case_type": {
          "type": "string",
          "const": "payment",
          "title": "Case Type"
        },
        "case_status": {
          "type": "string",
          "enum": [
            "open",
            "investigating",
            "resolved",
            "closed"
          ],
          "title": "Case Status"
        },
        "case_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Case Revision"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Order Revision"
        },
        "attempt_id": {
          "type": "string",
          "format": "uuid",
          "title": "Attempt Id"
        },
        "amount": {
          "type": "string",
          "pattern": "^[0-9]{1,10}\\.[0-9]{2}$",
          "title": "Amount"
        },
        "currency": {
          "type": "string",
          "pattern": "^[A-Z]{3}$",
          "title": "Currency"
        },
        "settlement_state": {
          "type": "string",
          "enum": [
            "initiated",
            "submitted",
            "under_review",
            "verified",
            "rejected",
            "expired",
            "refunded",
            "disputed"
          ],
          "title": "Settlement State"
        },
        "order_payment_status": {
          "type": "string",
          "enum": [
            "awaiting_transfer",
            "proof_submitted",
            "under_review",
            "verified",
            "rejected",
            "refunded"
          ],
          "title": "Order Payment Status"
        },
        "dispute_fence": {
          "type": "string",
          "enum": [
            "active",
            "none"
          ],
          "title": "Dispute Fence"
        },
        "exceptions": {
          "items": {
            "type": "string",
            "enum": [
              "FINANCIAL_FENCE",
              "PACKAGE_REQUIRES_REVIEW",
              "ACTIVE_RETENTION_HOLD"
            ]
          },
          "type": "array",
          "title": "Exceptions"
        },
        "prior_decisions": {
          "items": {
            "$ref": "#/components/schemas/HistoryEntry"
          },
          "type": "array",
          "title": "Prior Decisions"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        },
        "refund_execution_enabled": {
          "type": "boolean",
          "const": false,
          "title": "Refund Execution Enabled",
          "default": false
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "case_id",
        "case_type",
        "case_status",
        "case_revision",
        "order_id",
        "order_revision",
        "attempt_id",
        "amount",
        "currency",
        "settlement_state",
        "order_payment_status",
        "dispute_fence",
        "exceptions",
        "prior_decisions",
        "next_cursor"
      ],
      "title": "ReviewProjection"
    },
    "ReviewRequest": {
      "properties": {
        "decision": {
          "type": "string",
          "enum": [
            "verify",
            "reject",
            "request_more_info"
          ],
          "title": "Decision"
        },
        "bank_verified": {
          "type": "boolean",
          "title": "Bank Verified",
          "default": false
        },
        "bank_match_reference": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120,
              "minLength": 4
            },
            {
              "type": "null"
            }
          ],
          "title": "Bank Match Reference"
        },
        "settled_amount": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[0-9]{1,10}\\.[0-9]{2}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settled Amount"
        },
        "settled_currency": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Z]{3}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Settled Currency"
        },
        "reason": {
          "type": "string",
          "maxLength": 1000,
          "minLength": 4,
          "title": "Reason"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "decision",
        "reason"
      ],
      "title": "ReviewRequest"
    },
    "Revision": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision"
      ],
      "title": "Revision"
    },
    "RevisionReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/RevisionResult"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "RevisionReceipt"
    },
    "RevisionResult": {
      "properties": {
        "template": {
          "$ref": "#/components/schemas/TemplateView"
        },
        "revision": {
          "$ref": "#/components/schemas/RevisionView"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "template",
        "revision"
      ],
      "title": "RevisionResult"
    },
    "RevisionView": {
      "properties": {
        "revision_id": {
          "type": "string",
          "format": "uuid",
          "title": "Revision Id"
        },
        "template_id": {
          "type": "string",
          "format": "uuid",
          "title": "Template Id"
        },
        "version": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": 1.0,
          "title": "Version"
        },
        "status": {
          "type": "string",
          "enum": [
            "draft",
            "pending_qa",
            "published",
            "retired"
          ],
          "title": "Status"
        },
        "row_version": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Row Version"
        },
        "content": {
          "$ref": "#/components/schemas/Content"
        },
        "fingerprint_sha256": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Fingerprint Sha256"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "published_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Published At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "revision_id",
        "template_id",
        "version",
        "status",
        "row_version",
        "content",
        "created_at",
        "published_at"
      ],
      "title": "RevisionView"
    },
    "SealedInsert": {
      "properties": {
        "format": {
          "type": "string",
          "const": "safereturn-sealed-insert-v1",
          "title": "Format"
        },
        "wrapped_key": {
          "type": "string",
          "title": "Wrapped Key"
        },
        "nonce": {
          "type": "string",
          "title": "Nonce"
        },
        "ciphertext": {
          "type": "string",
          "title": "Ciphertext"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "format",
        "wrapped_key",
        "nonce",
        "ciphertext"
      ],
      "title": "SealedInsert"
    },
    "Series": {
      "properties": {
        "series_id": {
          "type": "string",
          "enum": [
            "orders_placed",
            "shipments_dispatched",
            "notifications_created"
          ],
          "title": "Series Id"
        },
        "unit": {
          "type": "string",
          "enum": [
            "product",
            "variant",
            "pair",
            "qr_identity",
            "order",
            "attempt",
            "job",
            "shipment",
            "outbox_event",
            "case",
            "sync_record"
          ],
          "title": "Unit"
        },
        "status": {
          "type": "string",
          "enum": [
            "ready",
            "unavailable"
          ],
          "title": "Status"
        },
        "reason_code": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "QUERY_UNAVAILABLE",
                "DRILLDOWN_UNAVAILABLE",
                "FEATURE_DISABLED",
                "LOW_STOCK_UNCONFIGURED",
                "REQUEST_BUDGET_EXHAUSTED"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Reason Code"
        },
        "buckets": {
          "items": {
            "$ref": "#/components/schemas/Bucket"
          },
          "type": "array",
          "maxItems": 30,
          "title": "Buckets"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "series_id",
        "unit",
        "status",
        "reason_code",
        "buckets"
      ],
      "title": "Series"
    },
    "ShipmentDetail": {
      "properties": {
        "shipment_id": {
          "type": "string",
          "format": "uuid",
          "title": "Shipment Id"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "title": "Order Number"
        },
        "status": {
          "type": "string",
          "enum": [
            "preparing",
            "packed",
            "dispatched",
            "delivered",
            "exception",
            "returned"
          ],
          "title": "Status"
        },
        "carrier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Carrier"
        },
        "tracking_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Tracking Reference"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "packed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Packed At"
        },
        "dispatched_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Dispatched At"
        },
        "delivered_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Delivered At"
        },
        "pair_count": {
          "type": "integer",
          "title": "Pair Count"
        },
        "fulfillment_eligible": {
          "type": "boolean",
          "title": "Fulfillment Eligible"
        },
        "requires_review": {
          "type": "boolean",
          "title": "Requires Review"
        },
        "pairs": {
          "$ref": "#/components/schemas/PackedPairPage"
        }
      },
      "type": "object",
      "required": [
        "shipment_id",
        "order_id",
        "order_number",
        "status",
        "carrier",
        "tracking_reference",
        "created_at",
        "packed_at",
        "dispatched_at",
        "delivered_at",
        "pair_count",
        "fulfillment_eligible",
        "requires_review",
        "pairs"
      ],
      "title": "ShipmentDetail"
    },
    "ShipmentMetadata": {
      "properties": {
        "shipment_id": {
          "type": "string",
          "format": "uuid",
          "title": "Shipment Id"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "title": "Order Number"
        },
        "status": {
          "type": "string",
          "enum": [
            "preparing",
            "packed",
            "dispatched",
            "delivered",
            "exception",
            "returned"
          ],
          "title": "Status"
        },
        "carrier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Carrier"
        },
        "tracking_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Tracking Reference"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "packed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Packed At"
        },
        "dispatched_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Dispatched At"
        },
        "delivered_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Delivered At"
        }
      },
      "type": "object",
      "required": [
        "shipment_id",
        "order_id",
        "order_number",
        "status",
        "carrier",
        "tracking_reference",
        "created_at",
        "packed_at",
        "dispatched_at",
        "delivered_at"
      ],
      "title": "ShipmentMetadata"
    },
    "ShipmentPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/ShipmentSummary"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "ShipmentPage"
    },
    "ShipmentRequest": {
      "properties": {
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "shipping_address_id": {
          "type": "string",
          "format": "uuid",
          "title": "Shipping Address Id"
        },
        "pair_ids": {
          "items": {
            "type": "string",
            "format": "uuid"
          },
          "type": "array",
          "maxItems": 100,
          "title": "Pair Ids"
        },
        "logical_item_ids": {
          "items": {
            "type": "string",
            "format": "uuid"
          },
          "type": "array",
          "maxItems": 50,
          "title": "Logical Item Ids"
        },
        "carrier": {
          "type": "string",
          "maxLength": 80,
          "minLength": 1,
          "title": "Carrier"
        },
        "reason": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Reason"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "order_id",
        "shipping_address_id",
        "carrier",
        "reason"
      ],
      "title": "ShipmentRequest"
    },
    "ShipmentSummary": {
      "properties": {
        "shipment_id": {
          "type": "string",
          "format": "uuid",
          "title": "Shipment Id"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "title": "Order Number"
        },
        "status": {
          "type": "string",
          "enum": [
            "preparing",
            "packed",
            "dispatched",
            "delivered",
            "exception",
            "returned"
          ],
          "title": "Status"
        },
        "carrier": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Carrier"
        },
        "tracking_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Tracking Reference"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "packed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Packed At"
        },
        "dispatched_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Dispatched At"
        },
        "delivered_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Delivered At"
        },
        "pair_count": {
          "type": "integer",
          "title": "Pair Count"
        },
        "fulfillment_eligible": {
          "type": "boolean",
          "title": "Fulfillment Eligible"
        },
        "requires_review": {
          "type": "boolean",
          "title": "Requires Review"
        }
      },
      "type": "object",
      "required": [
        "shipment_id",
        "order_id",
        "order_number",
        "status",
        "carrier",
        "tracking_reference",
        "created_at",
        "packed_at",
        "dispatched_at",
        "delivered_at",
        "pair_count",
        "fulfillment_eligible",
        "requires_review"
      ],
      "title": "ShipmentSummary"
    },
    "ShipmentUpdate": {
      "properties": {
        "status": {
          "type": "string",
          "enum": [
            "packed",
            "dispatched",
            "delivered",
            "exception",
            "returned"
          ],
          "title": "Status"
        },
        "expected_status": {
          "type": "string",
          "enum": [
            "preparing",
            "packed",
            "dispatched",
            "exception",
            "delivered"
          ],
          "title": "Expected Status"
        },
        "tracking_reference": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 150,
              "minLength": 1
            },
            {
              "type": "null"
            }
          ],
          "title": "Tracking Reference"
        },
        "packing_confirmed": {
          "type": "boolean",
          "title": "Packing Confirmed",
          "default": false
        },
        "reason": {
          "type": "string",
          "maxLength": 500,
          "minLength": 4,
          "title": "Reason"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status",
        "expected_status",
        "reason"
      ],
      "title": "ShipmentUpdate"
    },
    "SizeSelection": {
      "properties": {
        "variant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Variant Id"
        },
        "copies": {
          "type": "integer",
          "maximum": 100.0,
          "minimum": 1.0,
          "title": "Copies"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "variant_id",
        "copies"
      ],
      "title": "SizeSelection"
    },
    "StaffSecurity": {
      "properties": {
        "roles": {
          "items": {
            "type": "string"
          },
          "type": "array",
          "title": "Roles"
        },
        "mfa_verified": {
          "type": "boolean",
          "title": "Mfa Verified"
        },
        "capabilities": {
          "items": {
            "type": "string"
          },
          "type": "array",
          "title": "Capabilities"
        }
      },
      "type": "object",
      "required": [
        "roles",
        "mfa_verified",
        "capabilities"
      ],
      "title": "StaffSecurity"
    },
    "StateReceipt": {
      "properties": {
        "user_id": {
          "type": "string",
          "format": "uuid",
          "title": "User Id"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "action": {
          "type": "string",
          "enum": [
            "suspend",
            "restore"
          ],
          "title": "Action"
        },
        "revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 2.0,
          "title": "Revision"
        },
        "event_id": {
          "type": "string",
          "format": "uuid",
          "title": "Event Id"
        },
        "occurred_at": {
          "type": "string",
          "format": "date-time",
          "title": "Occurred At"
        },
        "state": {
          "type": "string",
          "enum": [
            "active",
            "suspended"
          ],
          "title": "State"
        },
        "fresh_sign_in_required": {
          "type": "boolean",
          "const": true,
          "title": "Fresh Sign In Required"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "user_id",
        "case_id",
        "action",
        "revision",
        "event_id",
        "occurred_at",
        "state",
        "fresh_sign_in_required"
      ],
      "title": "StateReceipt"
    },
    "StateUnavailable": {
      "properties": {
        "status": {
          "type": "string",
          "const": "unavailable",
          "title": "Status",
          "default": "unavailable"
        },
        "reason_code": {
          "type": "string",
          "const": "STATE_UNAVAILABLE",
          "title": "Reason Code",
          "default": "STATE_UNAVAILABLE"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "StateUnavailable"
    },
    "StockSummary": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "pair_count": {
          "type": "integer",
          "title": "Pair Count"
        },
        "current_tag_count": {
          "type": "integer",
          "title": "Current Tag Count"
        },
        "historical_tag_count": {
          "type": "integer",
          "title": "Historical Tag Count"
        },
        "available_pairs": {
          "type": "integer",
          "title": "Available Pairs"
        },
        "reserved_pairs": {
          "type": "integer",
          "title": "Reserved Pairs"
        },
        "allocated_pairs": {
          "type": "integer",
          "title": "Allocated Pairs"
        },
        "qa_held_pairs": {
          "type": "integer",
          "title": "Qa Held Pairs"
        },
        "active_pairs": {
          "type": "integer",
          "title": "Active Pairs"
        },
        "low_stock_threshold": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "title": "Low Stock Threshold"
        },
        "low_stock": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Low Stock"
        },
        "last_batch": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/LastBatch"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "type": "object",
      "required": [
        "as_of",
        "pair_count",
        "current_tag_count",
        "historical_tag_count",
        "available_pairs",
        "reserved_pairs",
        "allocated_pairs",
        "qa_held_pairs",
        "active_pairs",
        "low_stock_threshold",
        "low_stock",
        "last_batch"
      ],
      "title": "StockSummary"
    },
    "SubmitReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/SubmitResult"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "SubmitReceipt"
    },
    "SubmitResult": {
      "properties": {
        "revision": {
          "$ref": "#/components/schemas/RevisionView"
        },
        "validation_status": {
          "type": "string",
          "const": "needs_independent_physical_qa",
          "title": "Validation Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "revision",
        "validation_status"
      ],
      "title": "SubmitResult"
    },
    "SupportMetadata": {
      "properties": {
        "status": {
          "type": "string",
          "enum": [
            "available",
            "unavailable"
          ],
          "title": "Status"
        },
        "url": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Url"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status",
        "url"
      ],
      "title": "SupportMetadata"
    },
    "Suspend": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "suspected_compromise",
            "abuse_review",
            "security_review"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "case_id",
        "expected_revision",
        "reason_code"
      ],
      "title": "Suspend"
    },
    "Suspension": {
      "properties": {
        "status": {
          "type": "string",
          "const": "unavailable",
          "title": "Status",
          "default": "unavailable"
        },
        "reason_code": {
          "type": "string",
          "const": "NOT_IMPLEMENTED",
          "title": "Reason Code",
          "default": "NOT_IMPLEMENTED"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "title": "Suspension"
    },
    "Tag": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "public_status": {
          "type": "string",
          "enum": [
            "unactivated",
            "active",
            "owner_disabled",
            "admin_suspended",
            "revoked"
          ],
          "title": "Public Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "qr_id",
        "tag_type",
        "public_status"
      ],
      "title": "Tag"
    },
    "TagHistory": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/TagMetadata"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "TagHistory"
    },
    "TagMetadata": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "serial_number": {
          "type": "string",
          "title": "Serial Number"
        },
        "public_status": {
          "type": "string",
          "title": "Public Status"
        },
        "replaces_qr_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Replaces Qr Id"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "type": "object",
      "required": [
        "qr_id",
        "tag_type",
        "serial_number",
        "public_status",
        "replaces_qr_id",
        "created_at"
      ],
      "title": "TagMetadata"
    },
    "TagSummary": {
      "properties": {
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "pair_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Pair Id"
        },
        "pair_reference": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Pair Reference"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "public_status": {
          "type": "string",
          "title": "Public Status"
        },
        "profile_label": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Profile Label"
        },
        "published": {
          "type": "boolean",
          "title": "Published"
        },
        "profile_version": {
          "type": "integer",
          "title": "Profile Version"
        },
        "preference_version": {
          "type": "integer",
          "title": "Preference Version"
        },
        "profile_complete": {
          "type": "boolean",
          "title": "Profile Complete"
        },
        "editable": {
          "type": "boolean",
          "title": "Editable"
        },
        "editor_url": {
          "type": "string",
          "title": "Editor Url"
        }
      },
      "type": "object",
      "required": [
        "qr_id",
        "pair_id",
        "pair_reference",
        "tag_type",
        "public_status",
        "profile_label",
        "published",
        "profile_version",
        "preference_version",
        "profile_complete",
        "editable",
        "editor_url"
      ],
      "title": "TagSummary"
    },
    "TemplateBindingReceipt": {
      "properties": {
        "command_id": {
          "type": "string",
          "format": "uuid",
          "title": "Command Id"
        },
        "result": {
          "$ref": "#/components/schemas/TemplateBindingResult"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "command_id",
        "result"
      ],
      "title": "TemplateBindingReceipt"
    },
    "TemplateBindingResult": {
      "properties": {
        "binding": {
          "$ref": "#/components/schemas/TemplateBindingView"
        },
        "variant_row_version": {
          "type": "integer",
          "title": "Variant Row Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "binding",
        "variant_row_version"
      ],
      "title": "TemplateBindingResult"
    },
    "TemplateBindingView": {
      "properties": {
        "binding_id": {
          "type": "string",
          "format": "uuid",
          "title": "Binding Id"
        },
        "variant_id": {
          "type": "string",
          "format": "uuid",
          "title": "Variant Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "revision_id": {
          "type": "string",
          "format": "uuid",
          "title": "Revision Id"
        },
        "is_active": {
          "type": "boolean",
          "title": "Is Active"
        },
        "row_version": {
          "type": "integer",
          "title": "Row Version"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "binding_id",
        "variant_id",
        "tag_type",
        "revision_id",
        "is_active",
        "row_version",
        "created_at"
      ],
      "title": "TemplateBindingView"
    },
    "TemplateBindingsPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/TemplateBindingView"
          },
          "type": "array",
          "maxItems": 50,
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        },
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "items",
        "next_cursor",
        "as_of"
      ],
      "title": "TemplateBindingsPage"
    },
    "TemplateChoice": {
      "properties": {
        "template_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9._-]{3,80}$",
          "title": "Template Key"
        },
        "template_version": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": 1.0,
          "title": "Template Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "template_key",
        "template_version"
      ],
      "title": "TemplateChoice"
    },
    "TemplateChoices": {
      "properties": {
        "as_of": {
          "type": "string",
          "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?Z$",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/TemplateChoice"
          },
          "type": "array",
          "maxItems": 100,
          "title": "Items"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items"
      ],
      "title": "TemplateChoices"
    },
    "TemplateDetail": {
      "properties": {
        "template": {
          "$ref": "#/components/schemas/TemplateView"
        },
        "revisions": {
          "items": {
            "$ref": "#/components/schemas/RevisionView"
          },
          "type": "array",
          "maxItems": 50,
          "title": "Revisions"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "template",
        "revisions",
        "next_cursor"
      ],
      "title": "TemplateDetail"
    },
    "TemplateErrorEnvelope": {
      "properties": {
        "error": {
          "$ref": "#/components/schemas/ErrorBody"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "error"
      ],
      "title": "TemplateErrorEnvelope"
    },
    "TemplateList": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/TemplateView"
          },
          "type": "array",
          "maxItems": 50,
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        },
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "items",
        "next_cursor",
        "as_of"
      ],
      "title": "TemplateList"
    },
    "TemplateView": {
      "properties": {
        "template_id": {
          "type": "string",
          "format": "uuid",
          "title": "Template Id"
        },
        "key": {
          "type": "string",
          "title": "Key"
        },
        "name": {
          "type": "string",
          "title": "Name"
        },
        "purpose": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Purpose"
        },
        "lifecycle_status": {
          "type": "string",
          "enum": [
            "draft",
            "active",
            "retired"
          ],
          "title": "Lifecycle Status"
        },
        "row_version": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Row Version"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "template_id",
        "key",
        "name",
        "purpose",
        "lifecycle_status",
        "row_version",
        "created_at"
      ],
      "title": "TemplateView"
    },
    "Total": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "definition": {
          "type": "string",
          "const": "retained_nonanonymous_auth_registrations_v1",
          "title": "Definition"
        },
        "filters": {
          "$ref": "#/components/schemas/Filters"
        },
        "count": {
          "$ref": "#/components/schemas/Count"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "definition",
        "filters",
        "count"
      ],
      "title": "Total"
    },
    "Trends": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "range_start": {
          "type": "string",
          "format": "date-time",
          "title": "Range Start"
        },
        "range_end": {
          "type": "string",
          "format": "date-time",
          "title": "Range End"
        },
        "bucket_timezone": {
          "type": "string",
          "const": "UTC",
          "title": "Bucket Timezone",
          "default": "UTC"
        },
        "display_timezone": {
          "type": "string",
          "enum": [
            "UTC",
            "Asia/Karachi"
          ],
          "title": "Display Timezone"
        },
        "series": {
          "items": {
            "$ref": "#/components/schemas/Series"
          },
          "type": "array",
          "maxItems": 3,
          "title": "Series"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "range_start",
        "range_end",
        "display_timezone",
        "series"
      ],
      "title": "Trends"
    },
    "TypeCount": {
      "properties": {
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "total": {
          "type": "integer",
          "title": "Total"
        },
        "available": {
          "type": "integer",
          "title": "Available"
        },
        "allocated": {
          "type": "integer",
          "title": "Allocated"
        },
        "retired": {
          "type": "integer",
          "title": "Retired"
        },
        "allocatable": {
          "type": "integer",
          "title": "Allocatable"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "qr_type",
        "total",
        "available",
        "allocated",
        "retired",
        "allocatable"
      ],
      "title": "TypeCount"
    },
    "UpdateAddress": {
      "properties": {
        "address": {
          "$ref": "#/components/schemas/Address"
        },
        "is_default": {
          "type": "boolean",
          "title": "Is Default"
        },
        "expected_version": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Version"
        },
        "expected_book_version": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 0.0,
          "title": "Expected Book Version"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "address",
        "is_default",
        "expected_version",
        "expected_book_version"
      ],
      "title": "UpdateAddress"
    },
    "UploadRequest": {
      "properties": {
        "filename": {
          "type": "string",
          "pattern": "^[A-Za-z0-9_-]{1,100}\\.(?:png|jpg|jpeg|pdf)$",
          "title": "Filename"
        },
        "content_type": {
          "type": "string",
          "enum": [
            "image/png",
            "image/jpeg",
            "application/pdf"
          ],
          "title": "Content Type"
        },
        "bytes_size": {
          "type": "integer",
          "maximum": 5000000.0,
          "exclusiveMinimum": 0.0,
          "title": "Bytes Size"
        },
        "sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Sha256"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "filename",
        "content_type",
        "bytes_size",
        "sha256"
      ],
      "title": "UploadRequest"
    },
    "User": {
      "properties": {
        "user_id": {
          "type": "string",
          "format": "uuid",
          "title": "User Id"
        },
        "registered_at": {
          "type": "string",
          "format": "date-time",
          "title": "Registered At"
        },
        "email_verified": {
          "type": "boolean",
          "title": "Email Verified"
        },
        "provider_access": {
          "type": "string",
          "enum": [
            "banned",
            "not_banned"
          ],
          "title": "Provider Access"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "user_id",
        "registered_at",
        "email_verified",
        "provider_access"
      ],
      "title": "User"
    },
    "ValidationError": {
      "properties": {
        "loc": {
          "items": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "integer"
              }
            ]
          },
          "type": "array",
          "title": "Location"
        },
        "msg": {
          "type": "string",
          "title": "Message"
        },
        "type": {
          "type": "string",
          "title": "Error Type"
        },
        "input": {
          "title": "Input"
        },
        "ctx": {
          "type": "object",
          "title": "Context"
        }
      },
      "type": "object",
      "required": [
        "loc",
        "msg",
        "type"
      ],
      "title": "ValidationError"
    },
    "VariantRequest": {
      "properties": {
        "sku": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$",
          "title": "Sku"
        },
        "name": {
          "type": "string",
          "maxLength": 160,
          "minLength": 1,
          "title": "Name"
        },
        "size_mm": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 99999.0,
              "exclusiveMinimum": 0.0
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Size Mm"
        },
        "material": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Material"
        },
        "color": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 80
            },
            {
              "type": "null"
            }
          ],
          "title": "Color"
        },
        "unit_price": {
          "anyOf": [
            {
              "type": "number",
              "maximum": 9999999999.99,
              "minimum": 0.0
            },
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Unit Price"
        },
        "fulfillment_method": {
          "type": "string",
          "enum": [
            "pdf_label",
            "manufacturer_artwork",
            "manual"
          ],
          "title": "Fulfillment Method"
        },
        "template_key": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 120
            },
            {
              "type": "null"
            }
          ],
          "title": "Template Key"
        },
        "template_version": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": 1.0,
          "title": "Template Version",
          "default": 1
        },
        "is_active": {
          "type": "boolean",
          "title": "Is Active",
          "default": true
        },
        "sort_order": {
          "type": "integer",
          "maximum": 100000.0,
          "minimum": -100000.0,
          "title": "Sort Order",
          "default": 0
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "sku",
        "name",
        "fulfillment_method"
      ],
      "title": "VariantRequest"
    },
    "WhatsAppContact": {
      "properties": {
        "action_available": {
          "type": "boolean",
          "title": "Action Available"
        },
        "disclosure_notice": {
          "type": "string",
          "title": "Disclosure Notice"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "action_available",
        "disclosure_notice"
      ],
      "title": "WhatsAppContact"
    },
    "WhatsAppRequest": {
      "properties": {
        "intent": {
          "type": "string",
          "const": "open_chat",
          "title": "Intent"
        },
        "turnstile_token": {
          "anyOf": [
            {
              "type": "string",
              "maxLength": 2048,
              "format": "password",
              "writeOnly": true
            },
            {
              "type": "null"
            }
          ],
          "title": "Turnstile Token"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "intent"
      ],
      "title": "WhatsAppRequest"
    },
    "WhatsAppResponse": {
      "properties": {
        "url": {
          "type": "string",
          "title": "Url"
        },
        "disclosure": {
          "type": "string",
          "title": "Disclosure"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "url",
        "disclosure"
      ],
      "title": "WhatsAppResponse"
    },
    "app__api__v1__audit_events__Event": {
      "properties": {
        "id": {
          "type": "string",
          "format": "uuid",
          "title": "Id"
        },
        "occurred_at": {
          "type": "string",
          "format": "date-time",
          "title": "Occurred At"
        },
        "actor_kind": {
          "type": "string",
          "enum": [
            "customer",
            "staff",
            "system",
            "anonymous"
          ],
          "title": "Actor Kind"
        },
        "actor_user_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Actor User Id"
        },
        "action": {
          "type": "string",
          "title": "Action"
        },
        "target_type": {
          "type": "string",
          "title": "Target Type"
        },
        "target_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Target Id"
        }
      },
      "type": "object",
      "required": [
        "id",
        "occurred_at",
        "actor_kind",
        "actor_user_id",
        "action",
        "target_type",
        "target_id"
      ],
      "title": "Event"
    },
    "app__api__v1__audit_events__Page": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__audit_events__Event"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        },
        "scope": {
          "type": "string",
          "const": "security_metadata",
          "title": "Scope",
          "default": "security_metadata"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "Page"
    },
    "app__api__v1__cancellations__Decision": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "title": "Confirmed"
        },
        "request_id": {
          "type": "string",
          "format": "uuid",
          "title": "Request Id"
        },
        "expected_order_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Order Revision"
        },
        "expected_request_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 1.0,
          "title": "Expected Request Revision"
        },
        "decision": {
          "type": "string",
          "enum": [
            "investigate",
            "approve",
            "reject",
            "escalate"
          ],
          "title": "Decision"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "review_started",
            "eligible_unpaid",
            "request_declined",
            "requires_review"
          ],
          "title": "Reason Code"
        },
        "reconciliation_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Reconciliation Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "request_id",
        "expected_order_revision",
        "expected_request_revision",
        "decision",
        "reason_code"
      ],
      "title": "Decision"
    },
    "app__api__v1__dashboard__Summary": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "groups": {
          "items": {
            "$ref": "#/components/schemas/Group"
          },
          "type": "array",
          "maxItems": 8,
          "title": "Groups"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "groups"
      ],
      "title": "Summary"
    },
    "app__api__v1__finance_reconciliation__Counts": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "by_reason": {
          "additionalProperties": {
            "$ref": "#/components/schemas/Count"
          },
          "propertyNames": {
            "enum": [
              "REVIEW_PENDING",
              "ATTEMPT_ORDER_AMOUNT_MISMATCH",
              "ATTEMPT_ORDER_CURRENCY_MISMATCH",
              "VERIFIED_HISTORY_MISMATCH",
              "ORDER_SETTLEMENT_MISMATCH",
              "VERIFIED_ALLOCATION_MISMATCH",
              "DUPLICATE_VERIFIED_REFERENCE"
            ]
          },
          "type": "object",
          "title": "By Reason"
        },
        "affected_orders": {
          "$ref": "#/components/schemas/Count"
        },
        "unavailable_checks": {
          "items": {
            "type": "string"
          },
          "type": "array",
          "title": "Unavailable Checks"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "by_reason",
        "affected_orders",
        "unavailable_checks"
      ],
      "title": "Counts"
    },
    "app__api__v1__finance_reconciliation__Item": {
      "properties": {
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "attempt_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Attempt Id"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "REVIEW_PENDING",
            "ATTEMPT_ORDER_AMOUNT_MISMATCH",
            "ATTEMPT_ORDER_CURRENCY_MISMATCH",
            "VERIFIED_HISTORY_MISMATCH",
            "ORDER_SETTLEMENT_MISMATCH",
            "VERIFIED_ALLOCATION_MISMATCH",
            "DUPLICATE_VERIFIED_REFERENCE"
          ],
          "title": "Reason Code"
        },
        "observed_since": {
          "type": "string",
          "format": "date-time",
          "title": "Observed Since"
        },
        "attempt_amount": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[0-9]{1,10}\\.[0-9]{2}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Attempt Amount"
        },
        "order_amount": {
          "type": "string",
          "pattern": "^[0-9]{1,10}\\.[0-9]{2}$",
          "title": "Order Amount"
        },
        "currency": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Z]{3}$"
            },
            {
              "type": "null"
            }
          ],
          "title": "Currency"
        },
        "order_currency": {
          "type": "string",
          "pattern": "^[A-Z]{3}$",
          "title": "Order Currency"
        },
        "next_action": {
          "type": "string",
          "enum": [
            "review_payment",
            "investigate_order"
          ],
          "title": "Next Action"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "order_id",
        "attempt_id",
        "reason_code",
        "observed_since",
        "attempt_amount",
        "order_amount",
        "currency",
        "order_currency",
        "next_action"
      ],
      "title": "Item"
    },
    "app__api__v1__finance_reconciliation__Page": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__finance_reconciliation__Item"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        },
        "unavailable_checks": {
          "items": {
            "type": "string"
          },
          "type": "array",
          "title": "Unavailable Checks"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items",
        "next_cursor",
        "unavailable_checks"
      ],
      "title": "Page"
    },
    "app__api__v1__inventory_queries__BatchMetadata": {
      "properties": {
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "status": {
          "type": "string",
          "title": "Status"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "generated_at": {
          "type": "string",
          "format": "date-time",
          "title": "Generated At"
        },
        "printed_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Printed At"
        },
        "qa_approved_at": {
          "anyOf": [
            {
              "type": "string",
              "format": "date-time"
            },
            {
              "type": "null"
            }
          ],
          "title": "Qa Approved At"
        },
        "ecc_level": {
          "type": "string",
          "title": "Ecc Level"
        },
        "print_material": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Print Material"
        },
        "logo_template_key": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Logo Template Key"
        },
        "intended_environment": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Intended Environment"
        },
        "pair_count": {
          "type": "integer",
          "title": "Pair Count"
        },
        "current_tag_count": {
          "type": "integer",
          "title": "Current Tag Count"
        },
        "historical_tag_count": {
          "type": "integer",
          "title": "Historical Tag Count"
        },
        "qa_passed_pair_count": {
          "type": "integer",
          "title": "Qa Passed Pair Count"
        }
      },
      "type": "object",
      "required": [
        "batch_id",
        "batch_label",
        "status",
        "created_at",
        "generated_at",
        "printed_at",
        "qa_approved_at",
        "ecc_level",
        "print_material",
        "logo_template_key",
        "intended_environment",
        "pair_count",
        "current_tag_count",
        "historical_tag_count",
        "qa_passed_pair_count"
      ],
      "title": "BatchMetadata"
    },
    "app__api__v1__inventory_queries__BatchPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__inventory_queries__BatchMetadata"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "BatchPage"
    },
    "app__api__v1__inventory_queries__PairPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/PairMetadata"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "PairPage"
    },
    "app__api__v1__manufacturing_exports__ExportRequest": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483646.0,
          "minimum": 0.0,
          "title": "Expected Revision"
        },
        "printer_key_fingerprint": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Printer Key Fingerprint"
        },
        "production_approval_id": {
          "type": "string",
          "format": "uuid",
          "title": "Production Approval Id"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "initial_transport",
            "same_payload_retry"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision",
        "printer_key_fingerprint",
        "production_approval_id",
        "reason_code"
      ],
      "title": "ExportRequest"
    },
    "app__api__v1__manufacturing_exports__Receipt": {
      "properties": {
        "job_id": {
          "type": "string",
          "format": "uuid",
          "title": "Job Id"
        },
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Revision"
        },
        "status": {
          "type": "string",
          "enum": [
            "queued",
            "ready",
            "awaiting_ack",
            "accepted",
            "failed"
          ],
          "title": "Status"
        },
        "manifest_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "title": "Manifest Sha256"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "job_id",
        "batch_id",
        "revision",
        "status",
        "manifest_sha256"
      ],
      "title": "Receipt"
    },
    "app__api__v1__owner_qr__PairPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/PairSummary"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "PairPage"
    },
    "app__api__v1__owner_qr__QRPage": {
      "properties": {
        "items": {
          "items": {
            "$ref": "#/components/schemas/TagSummary"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "type": "object",
      "required": [
        "items",
        "next_cursor"
      ],
      "title": "QRPage"
    },
    "app__api__v1__print_queries__Counts": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "matching_jobs": {
          "$ref": "#/components/schemas/Count"
        },
        "by_job_status": {
          "additionalProperties": {
            "$ref": "#/components/schemas/Count"
          },
          "propertyNames": {
            "enum": [
              "queued",
              "rendering",
              "ready",
              "downloaded",
              "qa_passed",
              "failed",
              "superseded",
              "deleted"
            ]
          },
          "type": "object",
          "title": "By Job Status"
        },
        "affected_orders": {
          "$ref": "#/components/schemas/Count"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "matching_jobs",
        "by_job_status",
        "affected_orders"
      ],
      "title": "Counts"
    },
    "app__api__v1__print_queries__Item": {
      "properties": {
        "job_id": {
          "type": "string",
          "format": "uuid",
          "title": "Job Id"
        },
        "order_id": {
          "type": "string",
          "format": "uuid",
          "title": "Order Id"
        },
        "order_number": {
          "type": "string",
          "maxLength": 40,
          "minLength": 1,
          "title": "Order Number"
        },
        "job_revision": {
          "type": "integer",
          "minimum": 1.0,
          "title": "Job Revision"
        },
        "job_status": {
          "type": "string",
          "enum": [
            "queued",
            "rendering",
            "ready",
            "downloaded",
            "qa_passed",
            "failed",
            "superseded",
            "deleted"
          ],
          "title": "Job Status"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        },
        "order_status": {
          "type": "string",
          "enum": [
            "draft",
            "placed",
            "processing",
            "fulfilled",
            "cancelled"
          ],
          "title": "Order Status"
        },
        "payment_status": {
          "type": "string",
          "enum": [
            "awaiting_transfer",
            "proof_submitted",
            "under_review",
            "verified",
            "rejected",
            "refunded"
          ],
          "title": "Payment Status"
        },
        "fulfillment_status": {
          "type": "string",
          "enum": [
            "unallocated",
            "allocated",
            "packed",
            "dispatched",
            "delivered",
            "exception"
          ],
          "title": "Fulfillment Status"
        },
        "attempt_count": {
          "type": "integer",
          "minimum": 0.0,
          "title": "Attempt Count"
        },
        "failure_category": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "PHYSICAL_QA_FAILED",
                "PRINT_FAILURE_RECORDED"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Failure Category"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "job_id",
        "order_id",
        "order_number",
        "job_revision",
        "job_status",
        "created_at",
        "order_status",
        "payment_status",
        "fulfillment_status",
        "attempt_count",
        "failure_category"
      ],
      "title": "Item"
    },
    "app__api__v1__print_queries__Page": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__print_queries__Item"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items",
        "next_cursor"
      ],
      "title": "Page"
    },
    "app__api__v1__privacy_exports__Decision": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "expected_revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 1.0,
          "title": "Expected Revision"
        },
        "case_id": {
          "type": "string",
          "format": "uuid",
          "title": "Case Id"
        },
        "decision": {
          "type": "string",
          "enum": [
            "approve",
            "reject",
            "escalate"
          ],
          "title": "Decision"
        },
        "scope_version": {
          "type": "string",
          "const": "basic_v1",
          "title": "Scope Version"
        },
        "reason_code": {
          "type": "string",
          "enum": [
            "scope_reviewed",
            "scope_not_supported",
            "identity_review_failed",
            "requires_review"
          ],
          "title": "Reason Code"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "expected_revision",
        "case_id",
        "decision",
        "scope_version",
        "reason_code"
      ],
      "title": "Decision"
    },
    "app__api__v1__privacy_exports__ExportRequest": {
      "properties": {
        "confirmed": {
          "type": "boolean",
          "const": true,
          "title": "Confirmed"
        },
        "scope": {
          "type": "string",
          "const": "basic_v1",
          "title": "Scope"
        },
        "case_id": {
          "anyOf": [
            {
              "type": "string",
              "format": "uuid"
            },
            {
              "type": "null"
            }
          ],
          "title": "Case Id"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "confirmed",
        "scope"
      ],
      "title": "ExportRequest"
    },
    "app__api__v1__qr_lifecycle__Event": {
      "properties": {
        "event_id": {
          "type": "string",
          "format": "uuid",
          "title": "Event Id"
        },
        "event_type": {
          "type": "string",
          "enum": [
            "activation_completed",
            "owner_disabled",
            "owner_enabled"
          ],
          "title": "Event Type"
        },
        "occurred_at": {
          "type": "string",
          "format": "date-time",
          "title": "Occurred At"
        },
        "tag_type": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "lost",
                "ice"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "Tag Type"
        },
        "from_status": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "active",
                "owner_disabled"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "From Status"
        },
        "to_status": {
          "anyOf": [
            {
              "type": "string",
              "enum": [
                "active",
                "owner_disabled"
              ]
            },
            {
              "type": "null"
            }
          ],
          "title": "To Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "event_id",
        "event_type",
        "occurred_at",
        "tag_type",
        "from_status",
        "to_status"
      ],
      "title": "Event"
    },
    "app__api__v1__qr_lifecycle__Receipt": {
      "properties": {
        "pair_id": {
          "type": "string",
          "format": "uuid",
          "title": "Pair Id"
        },
        "qr_id": {
          "type": "string",
          "format": "uuid",
          "title": "Qr Id"
        },
        "tag_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Tag Type"
        },
        "public_status": {
          "type": "string",
          "enum": [
            "active",
            "owner_disabled"
          ],
          "title": "Public Status"
        },
        "pair_revision": {
          "type": "integer",
          "maximum": 2147483647.0,
          "minimum": 2.0,
          "title": "Pair Revision"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "pair_id",
        "qr_id",
        "tag_type",
        "public_status",
        "pair_revision"
      ],
      "title": "Receipt"
    },
    "app__api__v1__staff_directory__Page": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/User"
          },
          "type": "array",
          "maxItems": 100,
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items",
        "next_cursor"
      ],
      "title": "Page"
    },
    "app__api__v1__typed_inventory__BatchMetadata": {
      "properties": {
        "batch_id": {
          "type": "string",
          "format": "uuid",
          "title": "Batch Id"
        },
        "batch_label": {
          "type": "string",
          "title": "Batch Label"
        },
        "qr_type": {
          "type": "string",
          "enum": [
            "lost",
            "ice"
          ],
          "title": "Qr Type"
        },
        "requested_quantity": {
          "type": "integer",
          "title": "Requested Quantity"
        },
        "generated_quantity": {
          "type": "integer",
          "title": "Generated Quantity"
        },
        "status": {
          "type": "string",
          "enum": [
            "draft",
            "generated",
            "printed",
            "qa_passed",
            "rejected",
            "closed"
          ],
          "title": "Status"
        },
        "ecc_level": {
          "type": "string",
          "enum": [
            "M",
            "Q"
          ],
          "title": "Ecc Level"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "title": "Created At"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "batch_id",
        "batch_label",
        "qr_type",
        "requested_quantity",
        "generated_quantity",
        "status",
        "ecc_level",
        "created_at"
      ],
      "title": "BatchMetadata"
    },
    "app__api__v1__typed_inventory__BatchPage": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/app__api__v1__typed_inventory__BatchMetadata"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items",
        "next_cursor"
      ],
      "title": "BatchPage"
    },
    "app__api__v1__typed_inventory__QRPage": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/QRMetadata"
          },
          "type": "array",
          "title": "Items"
        },
        "next_cursor": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Next Cursor"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items",
        "next_cursor"
      ],
      "title": "QRPage"
    },
    "app__api__v1__typed_inventory__Summary": {
      "properties": {
        "as_of": {
          "type": "string",
          "format": "date-time",
          "title": "As Of"
        },
        "items": {
          "items": {
            "$ref": "#/components/schemas/TypeCount"
          },
          "type": "array",
          "title": "Items"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "as_of",
        "items"
      ],
      "title": "Summary"
    },
    "app__core__abuse_intake__Receipt": {
      "properties": {
        "status": {
          "type": "string",
          "const": "accepted",
          "title": "Status"
        }
      },
      "additionalProperties": false,
      "type": "object",
      "required": [
        "status"
      ],
      "title": "Receipt"
    }
  },
  "securitySchemes": {
    "InternalReadinessProbe": {
      "type": "http",
      "scheme": "bearer"
    },
    "SupabaseAccessToken": {
      "type": "http",
      "scheme": "bearer"
    }
  }
}
```

## Manual-contract local models

These supplement manually parsed filters and generic OpenAPI responses; validators/helper checks still apply.

### app.api.v1.account.StaffSecurity

```python
class StaffSecurity(BaseModel):
    roles: list[str]
    mfa_verified: bool
    capabilities: list[str]
```

### app.api.v1.account.MaskedContact

```python
class MaskedContact(BaseModel):
    phone: str | None
```

### app.api.v1.account.AccountSummary

```python
class AccountSummary(BaseModel):
    user_id: str
    display_name: str | None
    preferred_locale: Literal["en", "ur"]
    email_verified: bool
    masked_contact: MaskedContact
    version: str
```

### app.api.v1.account.ProfileEdit

```python
class ProfileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str | None = Field(default=None, max_length=120)
    preferred_locale: Literal["en", "ur"] | None = None

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError("Invalid name")
        return value
```

### app.api.v1.account.DeletionRequest

```python
class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm: Literal[True]
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("confirm", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError("Explicit confirmation required")
        return value
```

### app.api.v1.account_lifecycle.Command

```python
class Command(Confirmed):
    case_id: UUID
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
```

### app.api.v1.account_lifecycle.Suspend

```python
class Suspend(Command):
    reason_code: Literal["suspected_compromise", "abuse_review", "security_review"]
```

### app.api.v1.account_lifecycle.Restore

```python
class Restore(Command):
    reason_code: Literal["review_cleared"]
```

### app.api.v1.account_lifecycle.Recovery

```python
class Recovery(Command):
    reason_code: Literal["factor_loss", "account_access_review"]
```

### app.api.v1.account_lifecycle.Receipt

```python
class Receipt(Closed):
    user_id: UUID
    case_id: UUID
    action: Action
    revision: int = Field(ge=2, le=2147483647, strict=True)
    event_id: UUID
    occurred_at: AwareDatetime

    @field_validator("occurred_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
```

### app.api.v1.account_lifecycle.StateReceipt

```python
class StateReceipt(Receipt):
    action: Literal["suspend", "restore"]
    state: Literal["active", "suspended"]
    fresh_sign_in_required: Literal[True]
```

### app.api.v1.account_lifecycle.ReferralReceipt

```python
class ReferralReceipt(Receipt):
    action: Literal["recovery_escalated"]
    status: Literal["referred"]
```

### app.api.v1.audit_events.Event

```python
class Event(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_kind: Literal["customer", "staff", "system", "anonymous"]
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None
```

### app.api.v1.audit_events.Page

```python
class Page(BaseModel):
    items: list[Event]
    next_cursor: str | None
    scope: Literal["security_metadata"] = "security_metadata"
```

### app.api.v1.catalog.Closed

```python
class Closed(BaseModel):
    model_config = ConfigDict(
        extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True
    )

    @field_validator("*", mode="after")
    @classmethod
    def meaningful(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Must not be blank")
        return value
```

### app.api.v1.catalog.CategoryRequest

```python
class CategoryRequest(Closed):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,59}$")
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
    is_active: bool = Field(default=True, strict=True)
```

### app.api.v1.catalog.ProductRequest

```python
class ProductRequest(Closed):
    category_id: UUID | None = None
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,99}$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    lifecycle_status: Literal["draft", "published", "archived"] = "draft"
    price_per_copy: Decimal = Field(ge=0, le=Decimal("9999999999.99"), decimal_places=2, allow_inf_nan=False)
    max_order_copies: int = Field(default=100, ge=1, le=100, strict=True)
    qr_type: Literal["lost", "ice"] | None = None

    @field_validator("price_per_copy", mode="before")
    @classmethod
    def product_money(cls, value):
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Money must be a decimal string")  # noqa: TRY004 - Pydantic requires ValueError
        return value

    is_featured: bool = Field(default=False, strict=True)
    featured_sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
```

### app.api.v1.catalog.CreateProductRequest

```python
class CreateProductRequest(ProductRequest):
    qr_type: Literal["lost", "ice"]
```

### app.api.v1.catalog.VariantRequest

```python
class VariantRequest(Closed):
    sku: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,59}$")
    name: str = Field(min_length=1, max_length=160)
    size_mm: Decimal | None = Field(
        default=None, gt=0, le=99999, decimal_places=2, allow_inf_nan=False
    )
    material: str | None = Field(default=None, max_length=120)
    color: str | None = Field(default=None, max_length=80)
    unit_price: Decimal | None = Field(
        default=None, ge=0, le=Decimal("9999999999.99"), decimal_places=2, allow_inf_nan=False
    )
    fulfillment_method: Literal["pdf_label", "manufacturer_artwork", "manual"]
    template_key: str | None = Field(default=None, max_length=120)
    template_version: int = Field(default=1, ge=1, le=100000, strict=True)
    is_active: bool = Field(default=True, strict=True)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)

    @field_validator("unit_price", mode="before")
    @classmethod
    def decimal_money(cls, value):
        if value is not None and not isinstance(value, (str, Decimal)):
            raise ValueError("Money must be a decimal string")
        return value
```

### app.api.v1.catalog.ImageRequest

```python
class ImageRequest(Closed):
    cloudinary_public_id: str = Field(pattern=r"^[A-Za-z0-9/_-]{1,240}$")
    alt_text: str = Field(min_length=1, max_length=240)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
    is_primary: bool = Field(default=False, strict=True)
```

### app.api.v1.catalog.ImageMetadataRequest

```python
class ImageMetadataRequest(Closed):
    alt_text: str = Field(min_length=1, max_length=240)
    sort_order: int = Field(default=0, ge=-100000, le=100000, strict=True)
    is_primary: bool = Field(strict=True)
```

### app.api.v1.catalog_templates.TemplateChoice

```python
class TemplateChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    template_key: str = Field(pattern=r"^[A-Za-z0-9._-]{3,80}$")
    template_version: int = Field(ge=1, le=100000)
```

### app.api.v1.catalog_templates.TemplateChoices

```python
class TemplateChoices(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    as_of: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
    items: list[TemplateChoice] = Field(max_length=100)
```

### app.api.v1.catalog_templates.ErrorContent

```python
class ErrorContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: Literal[
        "AUTH_REQUIRED",
        "FORBIDDEN",
        "VALIDATION_ERROR",
        "PROVIDER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
    ]
    message: str
    message_ur: str
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    details: dict = Field(max_length=0)
```

### app.api.v1.catalog_templates.ErrorEnvelope

```python
class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    error: ErrorContent
```

### app.api.v1.checkout.Closed

```python
class Closed(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True
    )
```

### app.api.v1.checkout.Address

```python
class Address(Closed):
    recipient_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    province: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
```

### app.api.v1.checkout.QRUse

```python
class QRUse(Closed):
    mode: Literal["new_pair", "existing_owned"]
    tag_type: Literal["lost", "ice"]
    copies: int = Field(ge=1, le=100, strict=True)
    existing_qr_id: UUID | None = None
    client_pair_group: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def binding(self):
        if self.mode == "new_pair" and (
            self.existing_qr_id is not None or not self.client_pair_group
        ):
            raise ValueError("Invalid new-pair binding")
        if self.mode == "existing_owned" and (
            self.existing_qr_id is None or self.client_pair_group is not None
        ):
            raise ValueError("Invalid existing binding")
        return self
```

### app.api.v1.checkout.CartLine

```python
class CartLine(Closed):
    variant_id: UUID
    quantity: int = Field(ge=1, le=100, strict=True)
    qr_uses: list[QRUse] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def copies_match(self):
        if sum(u.copies for u in self.qr_uses) != self.quantity:
            raise ValueError("Copy counts must match quantity")
        return self
```

### app.api.v1.checkout.DeliveryRequest

```python
class DeliveryRequest(Closed):
    address: Address | None = None
    shipping_address_id: UUID | None = None
    shipping_address_version: int | None = Field(
        default=None, ge=1, le=2147483646, strict=True
    )
    contact_phone_confirmation: bool = Field(strict=True)

    @model_validator(mode="after")
    def address_source(self):
        if self.address is not None:
            if (
                self.shipping_address_id is not None
                or self.shipping_address_version is not None
            ):
                raise ValueError("Choose one address source")
        elif self.shipping_address_id is None or self.shipping_address_version is None:
            raise ValueError("Saved address and version required")
        return self

    @field_validator("contact_phone_confirmation")
    @classmethod
    def confirmed(cls, value):
        if not value:
            raise ValueError("Confirm shipping contact")
        return value
```

### app.api.v1.checkout.QuoteRequest

```python
class QuoteRequest(DeliveryRequest):
    lines: list[CartLine] = Field(min_length=1, max_length=50)
```

### app.api.v1.checkout.ConfirmRequest

```python
class ConfirmRequest(Closed):
    accept_total: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    accept_currency: Literal["PKR"]
```

### app.api.v1.dashboard.Count

```python
class Count(Closed):
    value: int = Field(ge=0, le=1000, strict=True)
    is_exact: bool = Field(strict=True)

    @model_validator(mode="after")
    def exact(self):
        if self.is_exact != (self.value < 1000):
            raise ValueError("Invalid count")
        return self
```

### app.api.v1.dashboard.Metric

```python
class Metric(Closed):
    metric_id: str
    unit: Unit
    count: Count
    drilldown: str
```

### app.api.v1.dashboard.Group

```python
class Group(Closed):
    group: GroupId
    status: Literal["ready", "unavailable"]
    as_of: datetime | None
    metrics: list[Metric] = Field(max_length=8)
    reason_code: Reason | None
```

### app.api.v1.dashboard.Summary

```python
class Summary(Closed):
    as_of: datetime
    groups: list[Group] = Field(max_length=8)
```

### app.api.v1.dashboard.Bucket

```python
class Bucket(Closed):
    start: datetime
    end: datetime
    count: Count

    @field_validator("start", "end")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value.astimezone(UTC)
```

### app.api.v1.dashboard.Series

```python
class Series(Closed):
    series_id: Literal["orders_placed", "shipments_dispatched", "notifications_created"]
    unit: Unit
    status: Literal["ready", "unavailable"]
    reason_code: Reason | None
    buckets: list[Bucket] = Field(max_length=30)
```

### app.api.v1.dashboard.Trends

```python
class Trends(Closed):
    as_of: datetime
    range_start: datetime
    range_end: datetime
    bucket_timezone: Literal["UTC"] = "UTC"
    display_timezone: Literal["UTC", "Asia/Karachi"]
    series: list[Series] = Field(max_length=3)
```

### app.api.v1.finance_reconciliation.Item

```python
class Item(Closed):
    order_id: UUID
    attempt_id: UUID | None
    reason_code: Reason
    observed_since: datetime
    attempt_amount: str | None = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    order_amount: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    currency: str | None = Field(pattern=r"^[A-Z]{3}$")
    order_currency: str = Field(pattern=r"^[A-Z]{3}$")
    next_action: Literal["review_payment", "investigate_order"]
```

### app.api.v1.finance_reconciliation.Page

```python
class Page(Closed):
    as_of: datetime
    items: list[Item]
    next_cursor: str | None
    unavailable_checks: list[str]
```

### app.api.v1.finance_reconciliation.Count

```python
class Count(Closed):
    value: int = Field(ge=0, le=1000)
    is_exact: bool
```

### app.api.v1.finance_reconciliation.Counts

```python
class Counts(Closed):
    as_of: datetime
    by_reason: dict[Reason, Count]
    affected_orders: Count
    unavailable_checks: list[str]
```

### app.api.v1.finance_reconciliation.Position

```python
class Position(Closed):
    as_of: datetime
    reason: Reason | None
    observed_since: datetime
    order_id: UUID
    attempt_id: UUID
    reason_code: Reason
```

### app.api.v1.financial_disputes.FinancialDecision

```python
class FinancialDecision(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
    expected_order_revision: int = Field(ge=1, le=2147483646, strict=True)
    decision: DecisionKind
    settlement_review_reference: UUID | None = None
    reason_code: Reason

    @model_validator(mode="after")
    def consistent(self):
        reasons = {
            "investigate": "review_started",
            "confirm_dispute": "settlement_disputed",
            "resolve_no_change": "no_financial_change",
            "escalate": "requires_review",
        }
        if reasons[self.decision] != self.reason_code:
            raise ValueError("Decision and reason differ")
        if (
            self.decision in {"confirm_dispute", "resolve_no_change"}
            and self.settlement_review_reference is None
        ):
            raise ValueError("Review reference required")
        return self
```

### app.api.v1.financial_disputes.HistoryEntry

```python
class HistoryEntry(Closed):
    decision_id: UUID
    revision: int = Field(ge=1)
    decision: DecisionKind
    effective_decision: DecisionKind
    reason_code: Reason
    created_at: datetime
```

### app.api.v1.financial_disputes.ReviewProjection

```python
class ReviewProjection(Closed):
    case_id: UUID
    case_type: Literal["payment"]
    case_status: Literal["open", "investigating", "resolved", "closed"]
    case_revision: int = Field(ge=1)
    order_id: UUID
    order_revision: int = Field(ge=1)
    attempt_id: UUID
    amount: str = Field(pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    settlement_state: Literal[
        "initiated",
        "submitted",
        "under_review",
        "verified",
        "rejected",
        "expired",
        "refunded",
        "disputed",
    ]
    order_payment_status: Literal[
        "awaiting_transfer",
        "proof_submitted",
        "under_review",
        "verified",
        "rejected",
        "refunded",
    ]
    dispute_fence: Literal["active", "none"]
    exceptions: list[
        Literal["FINANCIAL_FENCE", "PACKAGE_REQUIRES_REVIEW", "ACTIVE_RETENTION_HOLD"]
    ]
    prior_decisions: list[HistoryEntry]
    next_cursor: str | None
    refund_execution_enabled: Literal[False] = False
```

### app.api.v1.financial_disputes.DecisionReceipt

```python
class DecisionReceipt(Closed):
    decision_id: UUID
    case_id: UUID
    case_revision: int = Field(ge=1)
    order_id: UUID
    order_revision: int = Field(ge=1)
    decision: DecisionKind
    effective_decision: DecisionKind
    dispute_fence: Literal["active", "none"]
    next_action: Literal["await_reconciliation", "review_recorded", "escalated"]
    refund_execution_enabled: Literal[False] = False
```

### app.api.v1.fulfillment.ShipmentRequest

```python
class ShipmentRequest(Closed):
    order_id: UUID
    shipping_address_id: UUID
    pair_ids: list[UUID] = Field(default_factory=list, max_length=100)
    logical_item_ids: list[UUID] = Field(default_factory=list, max_length=50)
    carrier: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=4, max_length=500)

    @model_validator(mode="after")
    def membership_model(self):
        if bool(self.pair_ids) == bool(self.logical_item_ids):
            raise ValueError("Supply exactly one membership model")
        return self
```

### app.api.v1.fulfillment.ShipmentUpdate

```python
class ShipmentUpdate(Closed):
    status: Literal["packed", "dispatched", "delivered", "exception", "returned"]
    expected_status: Literal[
        "preparing", "packed", "dispatched", "exception", "delivered"
    ]
    tracking_reference: str | None = Field(default=None, min_length=1, max_length=150)
    packing_confirmed: bool = Field(default=False, strict=True)
    reason: str = Field(min_length=4, max_length=500)
```

### app.api.v1.fulfillment_queries.ShipmentMetadata

```python
class ShipmentMetadata(BaseModel):
    shipment_id: UUID
    order_id: UUID
    order_number: str
    status: ShipmentStatus
    carrier: str | None
    tracking_reference: str | None
    created_at: datetime
    packed_at: datetime | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
```

### app.api.v1.fulfillment_queries.ShipmentSummary

```python
class ShipmentSummary(ShipmentMetadata):
    pair_count: int
    fulfillment_eligible: bool
    requires_review: bool
```

### app.api.v1.fulfillment_queries.ShipmentPage

```python
class ShipmentPage(BaseModel):
    items: list[ShipmentSummary]
    next_cursor: str | None
```

### app.api.v1.fulfillment_queries.PackedPair

```python
class PackedPair(BaseModel):
    pair_id: UUID
    packed_qa_confirmed: bool
    packed_at: datetime | None
```

### app.api.v1.fulfillment_queries.PackedPairPage

```python
class PackedPairPage(BaseModel):
    items: list[PackedPair]
    next_cursor: str | None
```

### app.api.v1.fulfillment_queries.ShipmentDetail

```python
class ShipmentDetail(ShipmentSummary):
    pairs: PackedPairPage
```

### app.api.v1.fulfillment_queries.OrderMetadata

```python
class OrderMetadata(BaseModel):
    order_id: UUID
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus
    currency_code: str
    total_pkr: Decimal
    created_at: datetime
    placed_at: datetime | None
```

### app.api.v1.fulfillment_queries.FinanceOrder

```python
class FinanceOrder(OrderMetadata):
    projection: Literal["finance"] = "finance"
```

### app.api.v1.fulfillment_queries.OperationsOrder

```python
class OperationsOrder(OrderMetadata):
    projection: Literal["operations"] = "operations"
    shipment_count: int
    latest_shipment: ShipmentMetadata | None
    fulfillment_eligible: bool
```

### app.api.v1.fulfillment_queries.OrderPage

```python
class OrderPage(BaseModel):
    items: list[
        Annotated[FinanceOrder | OperationsOrder, Field(discriminator="projection")]
    ]
    next_cursor: str | None
```

### app.api.v1.health.Liveness

```python
class Liveness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"
```

### app.api.v1.health.ReadinessUnavailable

```python
class ReadinessUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["not_ready"] = "not_ready"
    database: Literal["unavailable"] = "unavailable"
```

### app.api.v1.health.Readiness

```python
class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready"] = "ready"
    database: Literal["ok"] = "ok"
```

### app.api.v1.notification_operations.Retry

```python
class Retry(Closed):
    expected_attempt_count: int = Field(ge=1, le=2147483647, strict=True)
    reason: Literal["provider_recovered", "recipient_reverified"]
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value
```

### app.api.v1.payments.PaymentRequest

```python
class PaymentRequest(Closed):
    provider_key: Literal["manual_bank"] = "manual_bank"
    sender_account: str = Field(min_length=4, max_length=80)
    sender_holder_name: str = Field(min_length=1, max_length=160)
    transfer_reference: str | None = Field(default=None, max_length=120)
```

### app.api.v1.payments.UploadRequest

```python
class UploadRequest(Closed):
    filename: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}\.(?:png|jpg|jpeg|pdf)$")
    content_type: Literal["image/png", "image/jpeg", "application/pdf"]
    bytes_size: int = Field(gt=0, le=5_000_000, strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
```

### app.api.v1.payments.EvidenceRequest

```python
class EvidenceRequest(Closed):
    upload_token: str = Field(min_length=40, max_length=4000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
```

### app.api.v1.payments.ReviewRequest

```python
class ReviewRequest(Closed):
    decision: Literal["verify", "reject", "request_more_info"]
    bank_verified: bool = Field(default=False, strict=True)
    bank_match_reference: str | None = Field(default=None, min_length=4, max_length=120)
    settled_amount: str | None = Field(default=None, pattern=r"^[0-9]{1,10}\.[0-9]{2}$")
    settled_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    reason: str = Field(min_length=4, max_length=1000)
```

### app.api.v1.payments.AllocationRetry

```python
class AllocationRetry(Closed):
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def confirmation(cls, value):
        if not value:
            raise ValueError("Explicit allocation confirmation required")
        return value
```

### app.api.v1.print_queries.Filters

```python
class Filters(Closed):
    job_id: UUID | None = None
    order_id: UUID | None = None
    order_number: str | None = Field(default=None, min_length=1, max_length=40)
    job_status: State | None = None
    order_status: OrderStatus | None = None
    payment_status: PaymentStatus | None = None
    fulfillment_status: FulfillmentStatus | None = None
    created_from: AwareDatetime | None = None
    created_before: AwareDatetime | None = None

    @field_validator("order_number", mode="before")
    @classmethod
    def exact_number(cls, value):
        if isinstance(value, str) and (
            value != value.strip() or re.search(r"[\x00-\x1f\x7f]", value)
        ):
            raise ValueError("Invalid exact number")
        return value

    @field_validator("created_from", "created_before", mode="before")
    @classmethod
    def aware_text(cls, value):
        if isinstance(value, str) and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
            value,
        ):
            raise ValueError("Expected aware ISO timestamp")
        return value

    @field_validator("created_from", "created_before")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC) if value else value
```

### app.api.v1.print_queries.Item

```python
class Item(Closed):
    job_id: UUID
    order_id: UUID
    order_number: str = Field(min_length=1, max_length=40)
    job_revision: int = Field(ge=1, strict=True)
    job_status: State
    created_at: AwareDatetime
    order_status: OrderStatus
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus
    attempt_count: int = Field(ge=0, strict=True)
    failure_category: Literal["PHYSICAL_QA_FAILED", "PRINT_FAILURE_RECORDED"] | None

    @field_validator("created_at")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC)
```

### app.api.v1.print_queries.Page

```python
class Page(Closed):
    as_of: AwareDatetime
    items: list[Item]
    next_cursor: str | None
```

### app.api.v1.print_queries.Count

```python
class Count(Closed):
    value: int = Field(ge=0, le=1000, strict=True)
    is_exact: bool = Field(strict=True)
```

### app.api.v1.print_queries.Counts

```python
class Counts(Closed):
    as_of: AwareDatetime
    matching_jobs: Count
    by_job_status: dict[State, Count]
    affected_orders: Count
```

### app.api.v1.print_queries.Position

```python
class Position(Closed):
    filters: str
    sort: Sort
    as_of: AwareDatetime
    at: AwareDatetime
    job_id: UUID
```

### app.api.v1.print_templates.ErrorBody

```python
class ErrorBody(Closed):
    code: Literal[
        "AUTH_REQUIRED",
        "FORBIDDEN",
        "REAUTH_REQUIRED",
        "NOT_FOUND",
        "CONFLICT",
        "IDEMPOTENCY_KEY_REUSED",
        "VERSION_MISMATCH",
        "FILE_TOO_LARGE",
        "VALIDATION_ERROR",
        "RATE_LIMITED",
        "PROVIDER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
    ]
    message: str
    message_ur: str
    request_id: str
    details: dict = Field(max_length=0)
```

### app.api.v1.print_templates.TemplateErrorEnvelope

```python
class TemplateErrorEnvelope(Closed):
    error: ErrorBody
```

### app.api.v1.print_templates.Create

```python
class Create(Closed):
    key: str = Field(pattern=r"^[A-Za-z0-9._-]{3,80}$")
    name: str = Field(min_length=1, max_length=100)
    purpose: Literal["lost", "ice"]

    @field_validator("name")
    @classmethod
    def text(cls, value):
        return plain(value)
```

### app.api.v1.print_templates.DraftEditRequest

```python
class DraftEditRequest(Closed):
    content: Content
    version_note: str = Field(min_length=4, max_length=500)

    @field_validator("version_note")
    @classmethod
    def text(cls, value):
        return plain(value)
```

### app.api.v1.print_templates.NewRevision

```python
class NewRevision(DraftEditRequest):
    base_revision_id: UUID | None
```

### app.api.v1.print_templates.Reason

```python
class Reason(Closed):
    reason: str = Field(min_length=4, max_length=500)

    @field_validator("reason")
    @classmethod
    def text(cls, value):
        return plain(value)
```

### app.api.v1.print_templates.Retire

```python
class Retire(Reason, Confirmed):
    pass
```

### app.api.v1.print_templates.Publish

```python
class Publish(Confirmed):
    approval_id: UUID
```

### app.api.v1.print_templates.Bind

```python
class Bind(Confirmed):
    variant_id: UUID
    tag_type: Literal["lost", "ice"]
    revision_id: UUID | None
    expected_variant_version: int = Field(ge=1, strict=True)
    expected_binding_id: UUID | None

    @model_validator(mode="after")
    def deactivation_target(self):
        if self.revision_id is None and self.expected_binding_id is None:
            raise ValueError("Explicit current binding required")
        return self
```

### app.api.v1.print_templates.Preview

```python
class Preview(Closed):
    expected_revision: int = Field(ge=1, strict=True)
```

### app.api.v1.print_templates.TemplateView

```python
class TemplateView(Closed):
    template_id: UUID
    key: str
    name: str
    purpose: Literal["lost", "ice"]
    lifecycle_status: Literal["draft", "active", "retired"]
    row_version: int = Field(ge=1)
    created_at: datetime
```

### app.api.v1.print_templates.RevisionView

```python
class RevisionView(Closed):
    revision_id: UUID
    template_id: UUID
    version: int = Field(ge=1, le=100000)
    status: Literal["draft", "pending_qa", "published", "retired"]
    row_version: int = Field(ge=1)
    content: Content
    fingerprint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    published_at: datetime | None
```

### app.api.v1.print_templates.RevisionResult

```python
class RevisionResult(Closed):
    template: TemplateView
    revision: RevisionView
```

### app.api.v1.print_templates.CreateReceipt

```python
class CreateReceipt(Closed):
    command_id: UUID
    result: TemplateView
```

### app.api.v1.print_templates.RevisionReceipt

```python
class RevisionReceipt(Closed):
    command_id: UUID
    result: RevisionResult
```

### app.api.v1.print_templates.EditReceipt

```python
class EditReceipt(Closed):
    command_id: UUID
    result: RevisionView
```

### app.api.v1.print_templates.SubmitResult

```python
class SubmitResult(Closed):
    revision: RevisionView
    validation_status: Literal["needs_independent_physical_qa"]
```

### app.api.v1.print_templates.SubmitReceipt

```python
class SubmitReceipt(Closed):
    command_id: UUID
    result: SubmitResult
```

### app.api.v1.print_templates.TemplateList

```python
class TemplateList(Closed):
    items: list[TemplateView] = Field(max_length=50)
    next_cursor: str | None
    as_of: datetime
```

### app.api.v1.print_templates.TemplateDetail

```python
class TemplateDetail(Closed):
    template: TemplateView
    revisions: list[RevisionView] = Field(max_length=50)
    next_cursor: str | None
```

### app.api.v1.print_templates.PublishedTemplateResult

```python
class PublishedTemplateResult(Closed):
    revision: RevisionView
    approval_id: UUID
```

### app.api.v1.print_templates.PublishedTemplateReceipt

```python
class PublishedTemplateReceipt(Closed):
    command_id: UUID
    result: PublishedTemplateResult
```

### app.api.v1.print_templates.TemplateBindingView

```python
class TemplateBindingView(Closed):
    binding_id: UUID
    variant_id: UUID
    tag_type: Literal["lost", "ice"]
    revision_id: UUID
    is_active: bool
    row_version: int
    created_at: datetime
```

### app.api.v1.print_templates.TemplateBindingResult

```python
class TemplateBindingResult(Closed):
    binding: TemplateBindingView
    variant_row_version: int
```

### app.api.v1.print_templates.TemplateBindingReceipt

```python
class TemplateBindingReceipt(Closed):
    command_id: UUID
    result: TemplateBindingResult
```

### app.api.v1.print_templates.TemplateBindingsPage

```python
class TemplateBindingsPage(Closed):
    items: list[TemplateBindingView] = Field(max_length=50)
    next_cursor: str | None
    as_of: datetime
```

### app.api.v1.print_templates.RetiredTemplateResult

```python
class RetiredTemplateResult(Closed):
    revision: RevisionView
    template: TemplateView
```

### app.api.v1.print_templates.RetiredTemplateReceipt

```python
class RetiredTemplateReceipt(Closed):
    command_id: UUID
    result: RetiredTemplateResult
```

### app.api.v1.printing.PrintJobRequest

```python
class PrintJobRequest(Closed):
    reason: str = Field(min_length=4, max_length=500)
    expected_revision: int = Field(ge=0, strict=True)
```

### app.api.v1.printing.DownloadRequest

```python
class DownloadRequest(Closed):
    grant_id: UUID
    download_token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
```

### app.api.v1.printing.Observation

```python
class Observation(Closed):
    tag_type: str = Field(pattern="^(lost|ice)$")
    symbol_mm: str = Field(pattern=r"^[0-9]{2,3}(?:\.[0-9]{1,2})?$")
    copies: int = Field(ge=1, le=5000, strict=True)
```

### app.api.v1.printing.JobQARequest

```python
class JobQARequest(Closed):
    approved: bool = Field(strict=True)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed: list[Observation] = Field(min_length=1, max_length=50)
    scan_passed: bool = Field(strict=True)
    logo_quiet_zone_passed: bool = Field(strict=True)
    bilingual_passed: bool = Field(strict=True)
    cutting_packaging_passed: bool = Field(strict=True)
    actual_scale_passed: bool = Field(strict=True)
    reason: str = Field(min_length=4, max_length=1000)
    inspected_item_ids: list[UUID] = Field(default_factory=list, max_length=50)
```

### app.api.v1.printing.PrintQARequest

```python
class PrintQARequest(Closed):
    qa_round: int = Field(ge=1, le=1000, strict=True)
    lost_scan_passed: bool = Field(strict=True)
    ice_scan_passed: bool = Field(strict=True)
    pair_match_passed: bool = Field(strict=True)
    credential_concealed: bool = Field(strict=True)
    bilingual_label_passed: bool = Field(strict=True)
    quiet_zone_passed: bool = Field(strict=True)
    indoor_size_passed: bool = Field(strict=True)
    outdoor_size_passed: bool = Field(strict=True)
    packaging_method: str = Field(pattern="^(scratch_off|sealed_sleeve|peel_seal)$")
    tamper_evidence_passed: bool = Field(strict=True)
    approved: bool = Field(strict=True)
    notes: str | None = Field(default=None, max_length=2000)
```

### app.api.v1.privacy_exports.Confirmed

```python
class Confirmed(Closed):
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value
```

### app.api.v1.privacy_exports.ExportRequest

```python
class ExportRequest(Confirmed):
    scope: Literal["basic_v1"]
    case_id: UUID | None = None
```

### app.api.v1.privacy_exports.Revision

```python
class Revision(Confirmed):
    expected_revision: int = Field(ge=1, le=2147483647, strict=True)
```

### app.api.v1.privacy_exports.Decision

```python
class Decision(Revision):
    case_id: UUID
    decision: Literal["approve", "reject", "escalate"]
    scope_version: Literal["basic_v1"]
    reason_code: Literal[
        "scope_reviewed",
        "scope_not_supported",
        "identity_review_failed",
        "requires_review",
    ]
```

### app.api.v1.retention.RetentionHoldRequest

```python
class RetentionHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reason_code: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
```

### app.api.v1.staff_directory.Filters

```python
class Filters(Closed):
    user_id: UUID | None = None
    email_verified: bool | None = Field(default=None, strict=True)
    provider_access: Access | None = None
```

### app.api.v1.staff_directory.User

```python
class User(Closed):
    user_id: UUID
    registered_at: AwareDatetime
    email_verified: bool = Field(strict=True)
    provider_access: Access

    @field_validator("registered_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
```

### app.api.v1.staff_directory.Observed

```python
class Observed(Closed):
    as_of: AwareDatetime

    @field_validator("as_of")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
```

### app.api.v1.staff_directory.Page

```python
class Page(Observed):
    items: list[User] = Field(max_length=100)
    next_cursor: str | None
```

### app.api.v1.staff_directory.Suspension

```python
class Suspension(Closed):
    status: Literal["unavailable"] = "unavailable"
    reason_code: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"
```

### app.api.v1.staff_directory.StateUnavailable

```python
class StateUnavailable(Closed):
    status: Literal["unavailable"] = "unavailable"
    reason_code: Literal["STATE_UNAVAILABLE"] = "STATE_UNAVAILABLE"
```

### app.api.v1.staff_directory.ApplicationState

```python
class ApplicationState(Observed):
    status: Literal["ready"] = "ready"
    state: Literal["active", "suspended"]
    revision: int = Field(ge=1, le=2147483647, strict=True)
    commands_available: bool = Field(strict=True)
```

### app.api.v1.staff_directory.Detail

```python
class Detail(Observed):
    user: User
    application_suspension: Suspension | StateUnavailable | ApplicationState = Field(
        default_factory=Suspension
    )
```

### app.api.v1.staff_directory.Total

```python
class Total(Observed):
    definition: Literal["retained_nonanonymous_auth_registrations_v1"]
    filters: Filters
    count: Count
```

### app.api.v1.standalone_owner.Begin

```python
class Begin(Closed):
    logical_item_id: UUID
```

### app.api.v1.standalone_owner.Confirm

```python
class Confirm(Confirmed):
    intent_id: UUID
```

### app.api.v1.standalone_owner.Availability

```python
class Availability(Confirmed):
    public_status: Literal["active", "owner_disabled"]
    expected_revision: int = Field(ge=1, le=2147483646, strict=True)
```

### app.api.v1.support_cases.Intake

```python
class Intake(Closed):
    case_type: CaseType
    priority: Priority = "normal"
    pair_id: UUID | None = None
    order_id: UUID | None = None
    description: str = Field(min_length=4, max_length=2000)
```

### app.api.v1.support_cases.Change

```python
class Change(Closed):
    expected_revision: int = Field(ge=1, le=2147483647, strict=True)
    action: Literal["claim", "update"]
    status: CaseStatus | None = None
    priority: Priority | None = None
    note: str | None = Field(default=None, min_length=4, max_length=2000)
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def meaningful_change(self):
        if not self.confirmed:
            raise ValueError("Explicit confirmation required")
        values = (self.status, self.priority, self.note)
        if self.action == "claim" and any(v is not None for v in values):
            raise ValueError("Claim assigns only the current agent")
        if self.action == "update" and all(v is None for v in values):
            raise ValueError("Update must contain a change")
        return self
```

### app.api.v1.typed_inventory.Closed

```python
class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

### app.api.v1.typed_inventory.GenerateRequest

```python
class GenerateRequest(Closed):
    batch_label: str = Field(
        min_length=3, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$"
    )
    qr_type: QRType
    quantity: int = Field(ge=1, le=1000, strict=True)
    ecc_level: Literal["M", "Q"] = "Q"
```

### app.api.v1.typed_inventory.GenerationReceipt

```python
class GenerationReceipt(Closed):
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    generated_quantity: int = Field(ge=1, le=1000)
    status: Literal["generated"]
    created_at: datetime
```

### app.api.v1.typed_inventory.Paging

```python
class Paging(Closed):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=220)
```

### app.api.v1.typed_inventory.QRFilters

```python
class QRFilters(Paging):
    qr_type: QRType | None = None
    batch_id: UUID | None = None
    inventory_status: InventoryStatus | None = None
    ownership_status: OwnershipStatus | None = None
```

### app.api.v1.typed_inventory.BatchFilters

```python
class BatchFilters(Paging):
    qr_type: QRType | None = None
    batch_label: str | None = Field(default=None, min_length=1, max_length=40)
    status: BatchStatus | None = None
```

### app.api.v1.typed_inventory.SummaryFilters

```python
class SummaryFilters(Closed):
    qr_type: QRType | None = None
```

### app.api.v1.typed_inventory.QRMetadata

```python
class QRMetadata(Closed):
    qr_id: UUID
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    serial_number: str
    public_status: str
    inventory_status: InventoryStatus
    ownership_status: OwnershipStatus
    row_version: int
    created_at: datetime
    allocatable: bool
```

### app.api.v1.typed_inventory.BatchMetadata

```python
class BatchMetadata(Closed):
    batch_id: UUID
    batch_label: str
    qr_type: QRType
    requested_quantity: int
    generated_quantity: int
    status: BatchStatus
    ecc_level: Literal["M", "Q"]
    created_at: datetime
```

### app.api.v1.typed_inventory.QRPage

```python
class QRPage(Closed):
    as_of: datetime
    items: list[QRMetadata]
    next_cursor: str | None
```

### app.api.v1.typed_inventory.BatchPage

```python
class BatchPage(Closed):
    as_of: datetime
    items: list[BatchMetadata]
    next_cursor: str | None
```

### app.api.v1.typed_inventory.TypeCount

```python
class TypeCount(Closed):
    qr_type: QRType
    total: int
    available: int
    allocated: int
    retired: int
    allocatable: int
```

### app.api.v1.typed_inventory.Summary

```python
class Summary(Closed):
    as_of: datetime
    items: list[TypeCount]
```

## Phase 9A addendum — independent support metadata (2026-10-24)

**IMPLEMENTED — PENDING ACCEPTANCE. NOT ADMITTED TO THE FRONTEND INTEGRATION ALLOWLIST.** This is a later implementation record, not a revision of the historical 162-operation audit totals or the Products request budget. Original API-097/098/099/323/324 quarantines remain unchanged. No numeric API ID is self-allocated; actual OpenAPI operation IDs are listed below.

| Method/path | Actual operationId / response model | Status |
|---|---|---|
| GET `/api/v1/admin/support-case-metadata` | `support_metadata_list_v1` / `Page` | IMPLEMENTED — PENDING ACCEPTANCE |
| GET `/api/v1/admin/support-case-metadata/{case_id}` | `support_metadata_detail_v1` / `Detail` | IMPLEMENTED — PENDING ACCEPTANCE |
| GET `/api/v1/admin/support-case-metadata/{case_id}/history` | `support_metadata_history_v1` / `History` | IMPLEMENTED — PENDING ACCEPTANCE |

Source: `backend/app/api/v1/support_metadata.py`; service/DTOs/SQL/cursors: `backend/app/services/support_metadata.py`; installed in `backend/app/main.py`. No legacy support/finance/order service imported or invoked by the new module. Content endpoint is **NOT IMPLEMENTED / BLOCKED — disclosure/redaction policy not approved**; detail always returns content_available=false. No mutation, financial metadata or frontend integration.

### Actual request and response contracts

All GET only, no body. Unknown or duplicate query keys rejected400; invalid values/UUIDs/cursors422. List query: optional case_id UUID, case_type activation|lost_tag|payment|privacy|ownership_dispute|other, status open|investigating|resolved|closed, priority low|normal|high|urgent, queue all(default)|mine|unassigned, limit1–100(default20), cursor max2000. Whole query limited4096 characters. No global text/date/staff-ID filter. Detail has no query parameters. History accepts limit/cursor only. Filters remain server-side and cursor-bound; list sorts created_at DESC,id DESC, history case_revision DESC; limit+1 pagination. List cursor binds actor/normalized filters/purpose/version; history binds actor/case/current revision and position. No cursor expiry or frozen multi-page snapshot is promised; every request reauthorizes current access. Cryptographic configuration required to issue/consume cursors; absent encryption configuration503 when issuance is needed. Stale history revision409.

Closed models:

- `CaseMetadata={case_id:UUID,case_type,status,priority,case_revision:int1..2147483647,created_at:UTC timestamp,assignment:mine|unassigned,assigned_to_me:boolean}`.
- `Page={as_of:UTC timestamp,items:CaseMetadata[0..100],next_cursor:string|null}`. as_of is application observation-start time, not database snapshot/cross-page watermark.
- `Detail=CaseMetadata+{content_available:false}`.
- `History={case_id:UUID,case_revision:int1..2147483647,items:[{event_id:UUID,case_revision:int1..2147483647,event_type:created|claimed|updated,from_status:status|null,to_status:status,priority,created_at:UTC timestamp}],next_cursor:string|null}`. No fabricated events/contiguous revision assumption; maximum signed-int event revision is included on the first page.

No description/note text/ciphertext, actor/opener/assignee UUIDs, customer references, updated_at, pair/order identifiers, profile/recovery/medical/location, financial/evidence fields or raw audit metadata returned. Missing detail/history404; empty list200. Errors use shared redacted auth/dependency envelope for401/403/404/503; query/cursor errors use `{error:{code,request_id}}`. Malformed database projections503. Unsupported methods405. Private/no-store/nosniff/no-referrer on success/errors, inherited bearer WWW-Authenticate on401.

### Authorization, database and independence evidence

`Authenticated` → verified JWT/live session/email/current provider+signed MFA → explicit current Support role. No Finance/security_admin/superadmin inheritance or frontend-role input. List/detail SQL explicitly requires unassigned or current actor; history additionally requires assigned actor. Existing support/event RLS retained, including restrictive abuse policy. Every query explicitly calls `sr_abuse_case_readable`; missing helper returns503 instead of legacy optional-policy fallback. Current Support/session is rechecked before return. Read-only observations write only bounded safe audit records, inside the existing transaction before protected response delivery; failures roll back.

Business SELECT budget: support_cases and support_case_events only. Existing transitive policy path: sr_abuse_case_readable → abuse_reports / sr_abuse_case_marker / sr_abuse_policy → abuse_intake_policies / shared abuse-policy advisory admission; staff/session/account admission reads auth/session/roles/account-state only. Audit INSERT uses existing audit RLS and sr_safe_json (pg_catalog JSON checks only); count is encoded in approved scalar `outcome=returned_N_records`, not an unapproved count key. No INSERT/UPDATE support case trigger is reached. No pair/QR relations, owner/context helpers, row locks, retention admission, fulfillment inspection, provider calls or workers. Existing auth/policy shared advisory locks are retained security admission, not pair row locks. Existing SELECT/INSERT audit grants suffice; **no SQL helper, migration, grant, RLS, trigger or historical migration changed**. Actual deployed graph/grants remain unverified.

### Verification and admission gates

From backend: `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider`: **44 passed**. Isolated new-router ASGI, real synthetic JWT signatures/JWKS mock and AEAD; scripted SQL session, no PostgreSQL. Covers authentication/MFA/roles/session recheck/rollback, queue and assigned-only policy, detail/history, filters/tie pagination/cursor actor-filter-purpose binding/tampering/stale revisions, maximum revision/history gaps, safe projections, crypto/dependency failures, bad inputs, blocked content/methods, headers and strict forbidden SQL/service/route checks. Ruff check passed on three new Python files. Prior fixture/setup/teardown inspected; no legacy fixtures or excluded requests. Protected support/financial/order and relevant retention/history/abuse migration SHA256 values compared with pre-edit baseline: unchanged.

No PostgreSQL/RLS/installed-helper/plan/lock/concurrency/provider/live-session acceptance or frontend/responsive tests executed. Scripted SQL denies pair access at application SQL boundary; it does not execute or prove deployed nested SQL. Source transitive review is separate evidence, not a live relation-access assertion. **Live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** Actual source-matching schema/grants/0035 policy helpers, isolated data, authoritative auth/session/MFA, crypto configuration and nested relation-access verification remain prerequisites. Do not automatically enable a relay, frontend, missing policy or deployment flag. Corrected integration allowlist remains unchanged pending required acceptance/admission review.
