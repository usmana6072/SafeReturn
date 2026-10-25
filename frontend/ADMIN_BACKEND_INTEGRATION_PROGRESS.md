# Admin backend integration progress

**Current scope (25 October 2026): Phase14 shared live acceptance — PARTIALLY EXECUTED, NOT COMPLETE.** Actual Cloud catalog/runtime connectivity, local FastAPI liveness/anonymous denial and public Auth JWKS checks passed; no accessible owner-supplied genuine staff/MFA session was found. Authenticated RLS/pagination/redaction remains blocked. Backend wheel built and smoke-tested; Docker image unverified. All admission gates, quarantines, unapplied0044, provisioning restrictions and Phase4/9–13 implementations remain preserved. Earlier “Phase14 not started” entries are historical; the execution result at the end and ADMIN_FINAL_INTEGRATION_REPORT.md section8 are current. No Phase15 started.

Date: 23 October 2026 (Asia/Karachi)
Module: **Products Management only**
Status: **Implemented in the current admin screens; local isolated checks pass. Real PostgreSQL/RLS, live sign-in and live Cloudinary acceptance remain unverified.**

## Pre-implementation gates and scope

Read the three corrected inventory/mapping/plan reports, their strict allowlist/exclusion sections, approved Product Copy Pricing v1.4, API/security specifications, frontend AGENTS.md and the installed Next.js route/server-client documentation. The audit correction exists and is consistent: 162 operations; 42 eligible, 10 supporting, 47 excluded, 23 quarantined, 1 blocked and 39 not admin. The 14-operation Products allowlist is present in all three reports.

Rechecked FastAPI catalog router registration in app/main.py, individual catalog handlers/schemas, mutation/lock/publishable/upload helpers, template registry catalog eligibility/gate and relevant source RLS/trigger chains (0003, 0015, 0034, 0036, 0039). Registered product metadata operations do not invoke pair generation, inspection, allocation, reservation, assignment, activation, credentials, export or ownership/lifecycle. The registry gate is an advisory lock; publication eligibility reads template evidence/bindings, not QR inventory. No backend source, schema, migration, customer behavior, environment or production auth configuration changed.

## Endpoint allowlist actually connected

All paths below have prefix `/api/v1`. The existing same-origin browser endpoint is `/admin/catalog-api`; backend methods are passed through a validated closed matrix, not arbitrary paths. Own staff-security is reused by the existing session/MFA architecture and checked server-side before catalog relay requests.

| Backend method | Backend path | Use |
|---|---|---|
| GET | /me/staff-security | Existing own role/MFA/capability bootstrap, not a privilege bypass |
| GET | /admin/products | Default Products List; UUID cursor, limit validation, no fabricated total |
| GET | /admin/products/{product_id} | Current Product Details/Edit, reload and conflict recovery |
| POST | /admin/products | Draft creation; navigate only to confirmed backend ID |
| PATCH | /admin/products/{product_id} | Product edits, publish/archive through supported lifecycle_status |
| GET | /admin/catalog/categories | Backend category choices and management list (capped 100) |
| POST | /admin/catalog/categories | Compact Create Category form |
| PATCH | /admin/catalog/categories/{category_id} | Category edits/status/sort with category version |
| POST | /admin/products/{product_id}/variants | Variant creation using parent version |
| PATCH | /admin/product-variants/{variant_id} | Full documented variant update using variant version |
| POST | /admin/products/{product_id}/images | authorize_upload=true, then independently keyed verified attachment |
| PATCH | /admin/products/{product_id}/images/{image_id} | Alt text, sort order/reorder and main-image metadata |
| DELETE | /admin/products/{product_id}/images/{image_id} | Confirmed catalog image unlink, not provider file deletion |
| GET | /admin/catalog/approved-templates | Existing approved key/version selector, enabled only during variant editing |

13 functional catalog operations plus the existing auth bootstrap = 14. No new backend endpoints invented. Signed public Cloudinary raster upload to the exact validated provider URL is a scoped infrastructure step; it is not a new SafeReturn API, private storage grant or QR export. Public catalog/checkout, template binding management and all other SafeReturn APIs are outside this module.

## Excluded operations and request isolation

The inventory's entire 70-operation exclusion/quarantine table remains authoritative. In particular, all six qr-inventory routes, order qr-allocation status/retry and independent-QR support context stay denied. No pair generation/QA/export/credentials/allocation/reservation/assignment/activation/ownership/inventory mutation is connected. Generic mixed payment, order, shipment, support, dashboard summary, finance reconciliation, privacy decision and retention workflows stay outside the module.

The relay rejects nonallowlisted path/method/query/body combinations before upstream fetch. Deny-policy unit inputs use an in-memory relay and assert zero upstream dispatch; they do not call excluded backend endpoints. No excluded API is used in fixtures, setup, teardown, rendering, polling or background effects. The browser network harness rejects unrelated destinations and the SQL/session harness fails on pair tables/functions or any unexpected SQL.

Product pages no longer import/mount ProductAdminList/ProductAdminEditor or branch to legacy consoles for view=live/real UUID paths. All product paths now use the established ProductsList/AddProductForm/AdminProductDetails interface. The shared shell remains; existing navigation prefetch=false is preserved. No allocation, inventory, orders, payments, support, printing, privacy or finance console/hook is imported into the Product tree. No production function was disabled or removed outside Products routing.

## Components and files

Modified current application paths:

- app/admin/products/page.tsx
- app/admin/products/new/page.tsx
- app/admin/products/[productId]/page.tsx
- components/admin-products-list.tsx
- components/admin-add-product.tsx
- components/admin-product-details.tsx
- app/admin/catalog-api/route.ts
- lib/catalog-admin-feedback.ts (additive fixed-message export; existing consumers unchanged)

Added supporting Product modules (not a second interface):

- components/admin-product-controls.tsx: category, variant and image sections inside the current editor
- lib/admin-products-contract.ts: allowlist, body validation and sanitized response parsers
- lib/admin-products-client.ts: catalog-only requests, fixed messages and memory-only stable intent keys

Reuse: AdminPage, AdminShell, AdminPageHeader, AdminCard, AdminStatusBadge, AdminEmptyState, AdminConfirmDialog, existing auth/server/staff modules, lib/product-admin.ts types, catalog feedback, approved-template choices/parser and the existing useTemplateChoices hook. Existing teal/slate card/table/form design and responsive shell remain. Add/Edit share ProductEditor exported by the existing Add Product component; legacy consoles are not mounted as adapters.

Test infrastructure added/updated:

- scripts/test-product-admin-relay.cjs now invokes the expanded Products-only checks
- scripts/test-products-integration.cjs
- scripts/test-products-backend.py
- tests/products-fixture.cjs
- tests/products-integration.spec.ts
- playwright.products-integration.config.ts (no webServer/global legacy setup)

## Controls and behavior now backed by APIs

- Products List: authenticated loading, visible failures, empty states, actual lifecycle/PKR price, real UUID details links, server cursor next/previous and refresh. Backend exposes no global search/filter/total-count contract; these are clearly unavailable rather than simulated with one page of records.
- Add Product: full valid ProductRequest including name/slug/description/category_id/qr_type/PKR copy price/max copies/featured state. Creation is draft-only; size/media work follows on the confirmed backend record. No mock success or mock-store persistence.
- Product Details/Edit: actual server fields, editable metadata, safe publish/archive status confirmation, preserved inputs and explicit latest-version review on 409/412. Archived products cannot reopen. Browser unload warns about unsaved product-field changes.
- Category management: compact create/edit section, name/slug/sort/is_active, status-change confirmation and category-version conflict recovery. No delete API/control invented.
- Variants: add/edit SKU/name/size/material/color/fulfillment/template reference/version/is_active/sort_order, preserve IDs and unaffected fields. Inactivation confirmation, variant-version vs parent-version distinction, conflict refresh/merge. No silent variant deletion.
- Images: authorizes scoped public raster upload, uploads that file to the validated public provider URL, then confirms verified attachment. Supports alt text, numeric sort/reorder, main image and confirmed unlink. No private evidence/storage/print file handling. Upload/attachment failures remain visible and do not claim success.
- Approved template choices: existing key/version selector. A configured reference is not approval or a real binding. No binding or evidence-provisioning endpoint is invoked to satisfy publication.

Existing PKR price_per_copy/max_order_copies fields were retained and wired, not duplicated. Subordinate new controls currently use English labels; primary Product headings and error fallbacks retain English/Urdu handling through the existing locale flag. Full translation of every new supporting label remains presentation follow-up, not an API gap.

## Authentication and security

- Existing verifiedSession -> server staffState -> current role/MFA/catalog.manage checks. Backend separately enforces verified email, active MFA, nonrevoked operations/security_admin/superadmin membership and RLS. Demo role preview has no authorization effect.
- Existing Supabase SSR server-only token transport and HttpOnly/Secure production cookies remain. Customer/admin origins, provider settings, callbacks and deployment configurations were not merged or changed.
- Relay checks configured same-origin mutation Origin, rejects cross-site requests/foreign Origin, permits only GET and POST browser envelopes and validates exact upstream methods/UUID paths/keys/versions/body/query shape. No open proxy.
- Bearer and signing/provider secrets stay server-side; no privileged localStorage. Upload API key/signature are public-provider scoped authorization parameters held only in form memory, not long-lived service/storage credentials. API secret is never forwarded.
- Request body limit: 32 KiB; upstream successful JSON: 2 MiB; error JSON: 8 KiB. JSON media type required, UTF-8 validation, bounded upstream timeout, redirects rejected, private no-store responses and fixed error messages. Sanitized responses drop unrelated raw database/provider fields.
- Stable Idempotency-Key per exact path/method/body/version/upload intent; synchronous in-flight locks prevent duplicate submit handlers. Upload authorization and attachment have separate keys. No automatic blind new-key retry.
- Current versions and quoted If-Match preserved. Product/category/variant/image conflicts retain user input and merge untouched fields from the explicitly reloaded record. Saving is blocked until conflict review. Provider success does not imply catalog attachment; server-confirmed persistence is distinguished from failed refresh.

## Pricing and historical data

One product price_per_copy in PKR applies to all sizes, with strict decimal string and 1–100 combined-copy ceiling. Variant writes omit price authority; backend overwrites legacy unit_price from parent. Nullable legacy prices display unconfigured, never a fabricated zero. Complete editable body fields are preserved, and Product PATCH does not replace variant arrays. No historical order/quote/snapshot write or recalculation occurs. No QR identity lookup/allocation is needed for this module.

## Tests actually executed and final results

1. `node scripts/test-product-admin-relay.cjs` (frontend): **55 passed checks**. All 13 catalog paths/methods, role/MFA/session/Origin, pagination, category/variant/image commands, version forwarding, same-intent replay/mismatched replay, input/response validation, bounds, safe errors and default-deny. Actual relay/contracts execute in a VM with synthetic auth/upstream; no external requests.
2. `backend/.venv/Scripts/python.exe -B frontend/scripts/test-products-backend.py` (repository root): **22 passed HTTP checks against actual FastAPI catalog handlers**, mounted alone with an isolated session/encryption/provider double. Covers registered handler requests, source validation, draft create/list/detail/edit, categories, variant preservation/parent pricing, upload authorization/attach/metadata/unlink, stale If-Match, replay and missing records. This is not PostgreSQL/RLS/JWT acceptance; no DB/real provider/worker/legacy setup.
3. `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_catalog_assets.py tests/test_product_copy_pricing.py::test_product_rejects_invalid_price tests/test_product_copy_pricing.py::test_price_required_and_exact_decimal tests/test_product_copy_pricing.py::test_strict_combined_copy_limit` (backend): **31 passed**. Reviewed selected tests use schema checks/synthetic settings/monkeypatched provider responses only. No checkout/allocation tests or fixtures executed.
4. `node node_modules/@playwright/test/cli.js test --config playwright.products-integration.config.ts` (frontend): **11 browser tests passed**. Source-bundled real Product components and AdminShell/client/relay; isolated HTTPS test origin and in-memory upstream. Tests list/cursor/refresh/UUID navigation, invalid add, duplicate submit, confirmed real-ID navigation, conflict retention/merge, category create/edit, variant attributes, signed upload/attach/metadata/unlink, 401/403/404/503 without mock fallback, mobile bounds and confirmed archive. Deny-by-default network interception; no app server, production sign-in, backend database or external provider used.
5. `node node_modules/typescript/bin/tsc --noEmit --incremental false` (frontend): **passed**.
6. Focused diff whitespace check: **passed**. Mobile screenshot reviewed; no horizontal viewport overflow in the browser assertion. Screenshot: `test-results/products-integration/mobile-products.png`.

Initial browser runs exposed ambiguous field labels and an insecure synthetic-origin harness issue; explicit accessible labels and an HTTPS isolated origin resolved them. A duplicate-submit test initially targeted the shell logout form; it now submits the actual Product form twice and verifies one backend intent. Final results above are from corrected tests. Existing dependency warnings (Starlette TestClient/httpx deprecation and Node color environment warning) did not fail checks; no dependency/config upgrade was made.

No broad legacy suite or full Next build/render sweep was run: unrelated screens can initialize excluded calls. UI tests transpile current source with the existing local stylesheet artifact; a fresh production build/deployed authenticated journey remains unverified. No production services or data were used.

## Remaining blockers / limits

- Validate real development/test PostgreSQL schema/grants, transactional rollback/RLS, actual JWT/session/MFA behavior and Cloudinary configuration separately before production release. No live keys/environment files were loaded or probed here.
- Publication still requires real approved registry bindings/evidence, valid variants/category and a verified main image. The allowed config choice lookup cannot create a binding; this module deliberately offers no backend bypass or forbidden stock/QA call. Invalid/deferred database constraints can surface as generic 503, not always 422.
- Signed upload needs configured public folder/preset/provider credentials. Provider acceptance/integrity checks are covered with doubles, not a live upload. Expired grants require explicit latest-state review/new authorization; raw authorization parameters are not persisted.
- Intent keys are form-memory only. After a page reload following an ambiguous mutation, inspect the actual record before resubmitting; no cross-session durable receipt browser storage was added.
- Categories are capped at 100; global product search/filter/count APIs do not exist in the current contract. Product creation precedes size/image persistence; no fabricated multi-resource atomic save is claimed.
- Existing unrelated legacy consoles and mixed QR routes remain in the repository unchanged; their presence is not permission for integration. Customer frontend behavior remains unchanged.

## Demo separation and next step

Products List/Add/Details/Edit/category/variant/image work now uses backend requests and never calls the shared mock product mutators. Other admin modules continue their prior demo or existing legacy-live behavior; none was integrated or redesigned here. The shell's demo-role preview and Reset Demo Data control remain unrelated to backend Products and cannot change its records.

Recommended next step is real authorized development acceptance of Products. After that, the next candidate module is safe Print Template metadata/drafts under a new narrow allowlist (no pair QA/printing/credentials/export); synthetic preview has its existing Linux isolation prerequisite. **Do not begin the next module in this task.**


---

# Phase 3 / Module 2 — Print Templates Management (2026-10-23)

Status: **frontend integration implemented for the narrow safe template routes; isolated checks passed; live acceptance and publication remain blocked.** This entry preserves the preceding Products record. No other module was started.

## Entry verification and independence

Reviewed the corrected inventory, mapping and plan, the preceding Products progress, final frontend review, technical design, API contract (including its 2026-10-21 template addendum), security specification and Branded QR Print Template Amendment v1.3. The corrected audit remains 162 classified operations: 42 eligible, 10 supporting, 47 QR-pair excluded, 23 quarantined, 1 blocked, 39 non-admin. Earlier API-307–310 placeholder descriptions are superseded by the current source/addendum, but source implementation does not prove operational readiness.

Products implementation exists; its live PostgreSQL/RLS, deployed JWT/MFA and Cloudinary acceptance remain outstanding as previously recorded. Templates can proceed independently: the only reused product operations are already verified catalog **reads**, contract parsers and the in-memory idempotency-key helper. No Products writes or media operations are added by this module. Previous Products test numbers are historical results, not newly rerun claims.

The actual app registers `print_templates.install` in `backend/app/main.py`, installing `backend/app/api/v1/print_templates.py` under `/api/v1`. Examined its closed schemas, `guard`, `command`, `proof`, pagination and response models. Traced each candidate through `backend/app/db/print_templates.py`, `backend/app/db/template_registry.py`, `backend/app/services/template_evidence.py`, synthetic preview code and the SQL functions/triggers in existing migrations `0033_print_template_drafts.sql` and `0034_print_template_publication.sql`. These files were read, not changed or applied.

## Strict module allowlist and per-operation decision

All paths in this table include `/api/v1`. The browser can reach them only through the closed `/admin/templates/api` BFF. UUID placeholders must be actual backend IDs. No wildcard proxy is available.

| API | Method / endpoint | Verified chain and side effects | Integration / prerequisites |
| --- | --- | --- | --- |
| 300 | GET `/admin/print-templates` | `TemplateRepository.call(list)` → `sr_template_service`; metadata reads only | Connected. Purpose/status, bounded limit, encrypted cursor. No unsupported search/revision counts. |
| 301 | POST `/admin/print-templates` | `command(create)` → `sr_template_service`; design key/name/purpose, receipt and audit | Connected. Creates zero revisions; no automatic bind, publish, inventory or credentials. |
| 302 | GET `/admin/print-templates/{template_id}` | `TemplateRepository.call(detail)` → `sr_template_service`; template/revision metadata | Connected. UUID route, row versions, ETag and paginated revisions. No description exists in this response. |
| 303 | POST `/admin/print-templates/{template_id}/revisions` | `command(revision)` → `sr_template_service`; new draft and provenance/contributor metadata | Connected. Structured Content, version note, real base revision or null for first revision; template If-Match. Existing draft/base/provenance rules remain authoritative. |
| 304 | PATCH `/admin/print-templates/{template_id}/revisions/{revision_id}` | `command(edit)` → `sr_template_service`; draft Content/contributor metadata | Connected. Draft only, version note, revision If-Match. Published/pending/retired records are read-only. |
| 305 | POST `/admin/print-templates/{template_id}/revisions/{revision_id}/preview` | `proof` → `preview_input` → fixed synthetic renderer, admission budget, reauthorization and spec comparison | Connected conditionally. Saved content, expected_revision equals revision If-Match; enrolled assets and isolated Linux renderer required. No production payload. |
| 306 | POST `/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa` | `command(submit)` prepares the same synthetic proof, then `sr_template_service`; pending_qa/fingerprint metadata | Connected conditionally. Draft, reason, current version, successful current preview and explicit UI confirmation. Result is needs_independent_physical_qa, never approval. |
| 307 | POST `/admin/print-templates/{template_id}/revisions/{revision_id}/publish` | Source is independent template evidence/lifecycle code, but requires genuine protected evidence and independent enrolled publisher | **BLOCKED, absent from BFF/client target allowlist.** No approved evidence lookup/enrollment workflow is available to this UI; no approval IDs/envelopes are invented. |
| 308 | POST `/admin/print-template-bindings` | `command(bind)` → `RegistryRepository` → `sr_template_lifecycle`; binding and product-variant catalog version changes; catalog/registry constraint checks | Connected conditionally. Published revision, exact selected variant version, complete scoped binding snapshot, expected binding ID, confirmed replacement/deactivation. Existing people/registry enrollment and compatibility rules are required; no publisher role is invented for binding. |
| 309 | GET `/admin/print-template-bindings` | `RegistryRepository` → `sr_template_lifecycle(bindings)`; metadata only | Connected on explicit user request, scoped to variant and template purpose. No nonexistent template_id filter; no global binding count inferred. |
| 310 | POST `/admin/print-templates/{template_id}/revisions/{revision_id}/retire` | `command(retire)` → `sr_template_lifecycle`; revision/template lifecycle metadata | Connected conditionally. Published revision, reason, confirmation, revision If-Match, enrolled publisher, no active bindings; history retained. Successful live retirement is not claimed. |
| supporting | GET `/admin/products`; GET `/admin/products/{product_id}` | Existing independent catalog repositories; product/variant metadata only | Connected only for explicit product picker loads, pagination and fresh variant version. No product mutations through this relay. |
| 339 | GET `/admin/catalog/approved-templates` | Safe config-backed choices previously inspected in Products; not physical QA evidence or approval authority | Not newly connected here. Products retains its existing use. It cannot authorize publish or manufacture bindings. |

**Count:** 10 template method/path operations connected (300–306, 308–310), plus 2 supporting catalog read operations. One candidate template operation (307) blocked; 339 adds no new connection. This module allowlist is narrower than the general audit eligibility list and does not reclassify unrelated admin APIs.

## Pair exclusion and indirect dependency findings

None of the connected chains generates, allocates, reserves, assigns, activates, inspects, exports credentials for or changes ownership/lifecycle of a QR pair. A template key identifies a design. Binding mutates design-to-variant metadata, not a customer/pair association. The SQL registry migration also contains order resolution/frozen snapshot/fulfillment helpers for other consumers; those helpers are **not invoked** by these template operations. Registry/catalog trigger checks enforce template eligibility and do not allocate inventory. Publication evidence is template physical QA, not pair QA.

Synthetic preview uses the fixed `https://preview.invalid/q/` test payload with a constant synthetic token, admitted enrolled font/logo assets and the existing isolated renderer. It reads no production order, pair, customer token or QR credentials. Submit re-renders/revalidates the same proof server-side; preview is never treated as independent physical QA.

The BFF rejects every unlisted route and method before backend dispatch, including publish, all `/admin/qr-inventory/batches`, batch detail, summary, codes, code detail, order qr-allocation and support independent-qr paths. Pair batch/QA/export/allocation/reservation/assignment/credentials/lifecycle operations remain excluded, including read-only and independent-typed-QR assertions. No hidden component, legacy console, hook, background prefetch or client initializer requests them. All new internal links disable prefetch. Test denylist probes are synthetic **inbound BFF validation only**, not calls to those backend endpoints.

## Screens and controls

Reused `/admin/templates`, `/admin/templates/new`, `/admin/templates/[key]`, `AdminPage`, authenticated `AdminShell`, role context and status badge. The existing dynamic folder name is retained, but `[key]` now carries the backend **template UUID**, not the display key or a demo identifier. Removed double decoding. Invalid IDs show a not-found error before dispatch.

List/create/details no longer import template mock data or fall back to demo records. Added purpose/status filters, cursor navigation, refresh, empty/error/loading states; real receipt navigation; structured Content editor; explicit base revision selection; draft edit/version notes; retained edit comparison after conflict; synthetic PDF object URL/fingerprint; QA reason/confirmation; unavailable publication explanation; explicit product/variant picker, scoped bindings/history, replacement/deactivation controls; confirmed retirement with publisher/no-active-binding guidance. Scoped styles preserve responsive shell layout and accessible labels/focus states. The backend exposes no description field, count/search API, asset enrollment picker, generic upload or approval discovery API, so none is invented.

The editor preserves all supported Content fields. Renderer/preset are fixed; dimensions use validated decimal strings; layout bounds/quiet zones/logo/font/pitch and plain bilingual text are checked; arbitrary HTML/SVG, URLs, alternate renderers and asset uploads are rejected. A new draft starts empty rather than supplying a fake enrolled asset UUID. Real asset-set enrollment remains an operator prerequisite.

Bindings load catalog data only after a click. A selected product is reread for authoritative variant version. The UI completes all pages for a specific variant/purpose before assuming an absent binding; active binding conflicts fail closed. Only actual published revisions from loaded history are offered. Deactivation requires the existing binding and an inactive variant. Backend compatibility, provenance, enrollment and availability checks remain authoritative.

## Authentication, transport, concurrency and artifacts

The existing session and `staffState` remain authoritative; demo role preview never authorizes a command. List/detail page guards follow the backend read roles: operations, security_admin, superadmin with active MFA. Creation and mutations require actual operations plus existing printing.manage capability, never implied superadmin inheritance. Backend additionally enforces verified email, live session/MFA and genuine authentication time within 300 seconds for writes; publisher assignment is an extra retirement/publication requirement. No auth_time is synthesized or authentication policy changed.

The relay requires same configured Origin on browser POST, rejects cross-site requests, forwards the genuine bearer only server-side and forwards the configured web Origin on writes. Existing `print_template_web_origin` must match that origin. No settings/environment files were modified. Request/response limits, JSON/content-type validation, encoded-body/query rejection, redirect rejection, timeouts, safe error codes, no-store/private responses and typed allowlist parsing apply. JSON is bounded at 32 KiB inbound and 2 MiB upstream; errors at 8 KiB. PDF is bounded at 2 MiB, checked for application/pdf, signature and fingerprint, with sandbox/nosniff response headers. Artifact transport is authenticated; only an in-memory browser Blob URL is exposed/revoked on selection, editing, refresh and unmount. No private provider URLs/tokens or persistent browser credentials are introduced.

Create has no If-Match. Draft creation uses template row_version; revision edits/preview/QA/retire use revision row_version; binding uses variant catalog_version and expected_variant_version. Quoted If-Match values are validated. Idempotency keys remain stable for the exact method/path/body/version intent, in form memory only. Create/revision/binding actions have immediate submit locks. Conflicts retain JSON/notes, disable revision writes until explicit latest-state reload, and expose the fresh server content for comparison. There is no automatic retry with a new key or assumed success. After a page reload following ambiguous success, operators must inspect backend state before repeating a command.

## Tests actually executed

Fixtures, shared ASGI client, auth verifier, scripted DB initialization and test setup/teardown were inspected first. No real DB, production services, secret files, workers, excluded test suite, migration or live console was used.

- `node frontend/scripts/test-templates-integration.cjs`: **60 relay/contract checks passed**, 18 strictly allowlisted synthetic upstream requests. Tests cover permissions/MFA, create/replay/key reuse, list/detail pagination, query/body/schema validation, structured geometry/text rejection, versions, preview binary/fingerprint, QA metadata, blocked publication, binding/retirement rejection, reauthentication, conflicts and unavailable/malformed responses. Denylist probes never leave the BFF.
- `backend/.venv/Scripts/python.exe -B frontend/scripts/test-templates-backend.py`: **54 passed, 14 deselected**, 53 guarded ASGI requests, zero excluded routes. Exercises actual FastAPI/JWT/AEAD/command code with scripted SQL responses: role/read/write permissions, recent MFA/session, create replay, closed schemas/geometry, revision preconditions, Origin/transport/cursors, and preview/QA/retirement unavailable rejection. Publication parametrizations are deliberately deselected. This is not PostgreSQL/RLS/registry or rendered PDF proof.
- From frontend: `node node_modules/@playwright/test/cli.js test --config playwright.templates-integration.config.ts`: **12 passed**, real source components + shell + actual BFF in a VM + in-memory upstream. Covers list/filter/paging/refresh/UUID navigation, duplicate create, draft/edit/preview/QA, retained conflict and reauth failures, product picker/scoped bindings, retirement and binding safe rejection without enrolled authority, 401/403/404/503 no fallback, mobile viewport containment. Every network request is intercepted; non-allowlisted requests fail the test. No signed approval or successful publication is fabricated. Published revision fixtures are read-only synthetic metadata for rejection tests, not a fabricated approval workflow.
- `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**.

The first browser run exposed unsupported product size/fulfillment values in the synthetic fixture; the production parser correctly rejected them. Correcting that fixture resolved the failure. Final counts above are from corrected reruns. Pytest's anyio assert-rewrite warning and Node color-environment warning did not fail checks. Browser harness uses current source and scoped template CSS with the existing local shared stylesheet artifact. Mobile screenshot: `test-results/templates-integration/mobile-templates.png`. After the final metadata/publication explanation text was added, the mobile containment test was rerun separately and passed (1/1); TypeScript was rerun and passed. No full Next production build/render sweep or deployed authenticated acceptance was run, to avoid unrelated module rendering/prefetch. Broad legacy template demo assertions were not run as integration acceptance.

## Remaining blockers and limits

- No actual local/live PostgreSQL, grants/RLS, registry migration installation, concurrent registry transition or deployed JWT/MFA acceptance was established. Backend source is independently implemented; operational acceptance is still required.
- The existing management flag must be enabled and backend web Origin configured correctly. No deployment settings were changed to force availability.
- Draft Content requires a genuinely enrolled asset-set UUID/material policy. No HTTP enrollment/list endpoint is provided. The frontend does not invent enrollment records.
- Preview and submit require enrolled immutable assets, renderer dependencies, allowed asset root and the existing Linux namespace/process/resource isolation. This Windows session did not produce a real backend PDF. Browser preview success uses a synthetic binary transport fixture only; isolated backend tests prove safe unavailability.
- Publish remains unavailable at both UI and BFF. Real unexpired independent physical QA evidence, protected custody import and enrolled independent publisher identity/assignment are required; this UI has no approved evidence discovery path. No manual arbitrary approval-ID field, enrollment endpoint or success bypass was added.
- Bind/retire are conditional frontend commands, not completed live lifecycle acceptance. Registry people/policies, a genuine published compatible revision and fresh variant/binding metadata are required for binding; retirement also requires publisher assignment and no active bindings. Rejection tests grant no authority.
- List API has no current revision/count; detail pagination supplies history. Binding API has no template filter; results are scoped and visibly labeled by selected variant/purpose. No global absence/count is inferred from one page.
- Memory-only intent keys do not provide cross-session retry receipts. Template administrative labels are primarily English within the existing bilingual shell; backend-required Urdu content is preserved and validated.

## Files changed for this module

Existing files updated:

- `frontend/app/admin/templates/page.tsx`
- `frontend/app/admin/templates/[key]/page.tsx`
- `frontend/components/admin-templates-list.tsx`
- `frontend/components/admin-create-template-key.tsx`
- `frontend/components/admin-template-details.tsx`
- `frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md` (this appended entry)

New module-scoped files:

- `frontend/app/admin/templates/api/route.ts`
- `frontend/lib/admin-templates-contract.ts`
- `frontend/lib/admin-templates-client.ts`
- `frontend/lib/api/template-relay.ts`
- `frontend/components/admin-template-bindings.tsx`
- `frontend/components/admin-templates.module.css`
- `frontend/scripts/test-templates-integration.cjs`
- `frontend/scripts/test-templates-backend.py`
- `frontend/tests/templates-fixture.cjs`
- `frontend/tests/templates-integration.spec.ts`
- `frontend/playwright.templates-integration.config.ts`

No backend, schema, migration, customer, deployment, authentication configuration, Products implementation or unrelated demo module was changed for Module 2. Existing unrelated working-tree changes were preserved.

## Mock separation and recommended next phase

Template list/create/detail/revision actions use the server relay, not mock templates or mock mutators. Unsupported publication is unavailable, never demo success. Other modules retain their prior behavior; their presence does not authorize excluded routes. First complete authorized development acceptance of Products and this template module against provisioned independent assets/registry. The next candidate is the previously allowlisted safe authorized user directory metadata, under its own verified read-only relay and acceptance plan. No next module was started.


---

# Phase 4 / Module 3 — Orders Management: verification gate BLOCKED (2026-10-23)

**No implementation performed. No endpoint connected. No API called or tested.** The request's assumption that API-080 remains eligible conflicts with the corrected audit and current source. The request requires stopping before implementation if the exclusion allowlist is inconsistent, and prohibits mixed-purpose endpoints with indirect QR-pair inspection. The three corrected reports are consistent with one another: API-080 is QUARANTINED. The incoming eligibility assumption is the inconsistency; the strict denylist is not relaxed.

## Previous implementation status

Reviewed the inventory, frontend/backend mapping, integration plan and preceding Products/Templates progress entries and implementation files. Products and Print Templates frontend implementations exist; their recorded isolated checks passed in their respective phases, but live PostgreSQL/RLS/deployed session/provider acceptance remains pending. Template publication remains blocked by genuine independent evidence/publisher prerequisites; actual Linux PDF rendering and live registry lifecycle acceptance remain unverified. None of those earlier tests was rerun or claimed as a new Phase 4 result. Orders' blocker is its own service chain, independent of these outstanding acceptance tasks.

Reviewed relevant approved technical design, API contract, database/security specifications and Copy Pricing Amendment v1.4. The amendment retains the combined 100-copy ceiling, authoritative stored totals and one QR identity per logical item regardless of copies. Those rules do not authorize identity/allocation lookups or make the mixed order-list API safe. No total was recalculated or currency converted.

## Source evidence and endpoint decisions

| Endpoint | Decision | Verified reason |
| --- | --- | --- |
| GET `/api/v1/admin/orders` (API-080) | **QUARANTINED; not connected** | Registered by `backend/app/main.py:97`, route in `backend/app/api/v1/fulfillment_queries.py:156`. It selects actual operations membership from staff_roles, chooses operations over finance (`:178`), and adds `public.sr_fulfillment_eligible(o.id)` to the operations query (`:190`). The entire mixed endpoint remains denied. |
| GET `/api/v1/admin/orders/{order_id}` (API-081) | **EXCLUDED; not called** | Existing generic detail includes pair units/QR uses and other prohibited context; current UUID frontend route mounts the legacy OrdersConsole. No new relay, hidden fetch, summary population or prefetch was added. |
| GET `/api/v1/admin/orders/{order_id}/qr-allocation` and allocation retry | **EXCLUDED/QUARANTINED; not called** | Explicit owner prohibition and allocation dependencies. Independent/typed naming is not permission. |
| Payment, print-job, shipment, cancellation, finance reconciliation/counts and all order mutations | **Outside scope / existing exclusions retained** | No supporting calls, imports, legacy console mounting, test execution or status changes were introduced. |

Verified indirect chain: `orders` operations projection → `sr_fulfillment_eligible` → legacy eligibility implementation reads `order_pair_units`, `pair_print_qa`, `order_item_qr_uses`, `qr_codes` and `tag_pairs`. Its source is `backend/alembic/versions/0018_fulfillment_eligibility.py:52` (notably pair allocation/QA at lines 56–57 and ownership/status joins thereafter). Migration 0034 wraps the previous function as `sr_fulfillment_eligible_v33` and adds template checks. Migration 0042 rewrites the wrapper to choose typed eligibility for single_qr orders while retaining the legacy branch. The list has no independent safe projection or commerce_model filter; existing legacy rows and mixed-role staff can still reach prohibited reads. These migrations were inspected only, not applied or modified. This is source evidence, not a statement about an inspected live database.

This finding concerns indirect pair **inspection**; it does not assert that listing generates or mutates pairs. Read-only operations are still prohibited where they inspect pair state. Removing fields in the frontend after fetching would not prevent the backend inspection. Forcing finance-only roles, querying a selected order number or hiding operations-only UI is not a separately authorized endpoint and would contradict the corrected whole-operation quarantine. No workaround was implemented.

## Verified contract, retained only as audit evidence

The registered list supports exact order_number (1–40 non-control characters), order_status, payment_status, fulfillment_status, timezone-aware created_from inclusive / created_before exclusive, sort newest or oldest, limit 1–100 (default 20) and an encoded cursor. Sorting uses created_at plus UUID as deterministic tiebreaker; pagination returns items/next_cursor with no total count. These capabilities were read from source, not invoked.

Common response fields are order_id, order_number, order_status, payment_status, fulfillment_status, currency_code, stored total_pkr, created_at and nullable placed_at, with a finance/operations projection discriminator. Operations also receives shipment_count, latest_shipment and fulfillment_eligible. No customer reference is supplied by this common list projection. The actual route requires live authorized operations or finance, verified account/session and staff MFA through existing backend authorization; frontend role preview cannot select a safer backend projection. Existing verifiedSession/staffState infrastructure is reusable, but does not authorize a quarantined operation.

A future independently permitted metadata response could support stored historical totals and explicit currency without recomputing current catalog prices. It would not support item/identity counts, allocation completion or full details from this list. No new backend endpoint or schema is proposed as an implemented contract.

## Frontend inspection and unchanged behavior

Inspected `frontend/app/admin/orders/page.tsx`, `[orderId]/page.tsx`, `api/route.ts`, `components/admin-orders.tsx`, its scoped CSS, legacy orders-console imports and `lib/api/orders-relay.ts` / orders-contract. The default Orders screen currently uses mock orders; `?view=live` mounts the old console, and UUID detail routes select that console automatically. The existing broad relay can dispatch list, generic detail and finance-related reads. These are **avoidance evidence**, not integration approval. None was mounted, navigated, rendered or tested in this phase. Existing unsafe legacy entry points were not rewritten because the explicit verification gate stops implementation; this report does not claim they have been disabled.

The existing AdminPage/AdminShell, card/header/badge/table/empty states and scoped responsive CSS are reusable if an independent permitted order metadata contract is later available. No live filter, cursor UI, summary panel, copy button, mutation, detail fallback or frontend control was added. No browser data was mixed with real IDs and no new mock fallback was introduced. Existing Orders demo behavior and all other modules remain unchanged.

## Tests, files and remaining blocker

- Tests run: **none**. No HTTP/ASGI/browser request, production mutation, fixture/setup/teardown, broad build or legacy suite was executed. Static source/document inspection only; zero excluded requests issued by this phase. No runtime denylist test or responsive acceptance is claimed.
- Responsive sizes 1366×768, 1440×900, 768×1024 and 375×667: **not tested**, since no authorized live Orders implementation can be mounted under the current contract.
- Files changed: **only `frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md`**, appending this Phase 4 blocked entry. Previous phase records and the corrected audit classifications remain intact. No application/backend/customer/authentication/deployment/schema/migration code was changed for Phase 4.
- Connected endpoints: **0**. Screens connected: **0**. New controls: **0**. Live Orders list, summaries, filters, pagination and historical amount display: **not implemented / blocked**. Existing Orders demo remains demo-only.
- Required resolution: a separately reviewed, already independent permitted order metadata endpoint must exist before this integration proceeds. None was identified in the current approved contract/source. Backend changes to bypass business rules, invent a new API, or alter eligibility are outside this request. The owner must resolve the contract/eligibility conflict through the approved backend process; the frontend cannot make API-080 safe by response redaction or role selection.
- Recommended next action: resolve the Orders contract blocker and finish previous modules' authorized live acceptance. Safe authorized user-directory metadata remains a candidate for a separately requested verified phase. **No next module started.**


---

# Orders blocker resolution — independent metadata design (2026-10-23)

**AUDIT/DESIGN ONLY — NOT IMPLEMENTED.** Proposed GET `/api/v1/admin/order-metadata` is documented in `frontend/ADMIN_ORDERS_METADATA_API_PROPOSAL.md` for owner/contract review. It is not registered, called, tested or added to the strict runtime allowlist. API-080 remains QUARANTINED; API-081 and all pair/allocation/QA/ownership/fulfillment operations retain their exclusions. No audit inventory operation count is changed for a proposed, unregistered path.

The proposed fixed projection selects only orders.id, order_number, order_status, payment_status, currency_code, total_pkr (response alias total_amount), created_at and placed_at. Proposed envelope is items/next_cursor/as_of. Operations/finance require current verified session/email/MFA; no superadmin inheritance or role-based enrichment. No customer reference/PII, fulfillment fields, related-table joins, pair/QR helper, worker or mutation. Query/filter, authenticated actor/filter-bound cursor, Decimal/currency, minimized response and error contracts, dependencies and planned acceptance tests are specified in the proposal.

Source review indicates existing orders columns and SELECT RLS support correctness without mandatory schema changes; installed policies/grants, crypto configuration and global keyset performance remain unverified. A performance index may require separate approval after measurement. Immutable historical amounts remain stored values; PKR price-per-copy semantics and legacy explicit currency are preserved without reading current catalog prices or inferring identities from copies.

Files changed for this design task: new `frontend/ADMIN_ORDERS_METADATA_API_PROPOSAL.md` and this appended tracker entry only. No application/backend/schema/migration/auth/deployment/customer code changed; no database/API calls, excluded functions, tests/fixtures, rendering or service execution. Test cases in the proposal are required future work, **not executed results**. Blockers: contract/operation-ID review, absent implementation, deployed schema/RLS/auth/crypto acceptance and performance checks. Previous phase live acceptance limitations remain. Return proposal for review; do not implement or start another module.


---

# Phase 3 resumed — Print Templates frontend safeguards (2026-10-23)

User explicitly selected resuming Print Templates, not implementing the Orders proposal. Reviewed the existing Phase 3 implementation and its remaining blockers; kept the prior closed template allowlist, publication prohibition and all QR-pair exclusions unchanged. No backend/environment/credentials/database probing, schema/migration/customer/auth/deployment changes or new module was undertaken.

Completed two frontend correctness fixes:

- New unsaved Content JSON now counts as dirty before a revision has been persisted. Switching to another revision or starting a fresh draft prompts before discarding that content; cancellation preserves it. Previously dirty detection only covered already selected persisted revisions.
- Binding controls clear the revision/confirmation/snapshot eligibility when refreshed revision metadata no longer contains the selected published revision. Product/variant changes clear stale revision selections and pagination state. The command handler independently requires confirmation, a currently published selection (or valid inactive-variant deactivation), and the complete scoped binding snapshot before dispatch; disabling a button alone is not the guard. Backend authorization, version checks and lifecycle requirements remain authoritative.

Files changed in this continuation only: `frontend/components/admin-template-details.tsx`, `frontend/components/admin-template-bindings.tsx`, `frontend/tests/templates-integration.spec.ts`, and this tracker append. No endpoint added or approval fabricated. The Orders metadata proposal remains NOT IMPLEMENTED.

Tests actually rerun after inspecting the existing isolated fixture, source bundler, network interception and Playwright configuration:

- From frontend: `node node_modules/@playwright/test/cli.js test --config playwright.templates-integration.config.ts`: **14 passed** (12 previous template workflows plus two new regressions). Actual source components/client/relay with synthetic auth and in-memory upstream; no application server/live DB/worker/provider. The two new tests issue metadata reads only: unsaved-draft discard confirmation and publication-state invalidation for binding. The latter changes fixture metadata directly, never fabricates approval or executes retirement. Browser assertions retain deny-by-default request interception and excluded-path checks; zero excluded requests were dispatched. Existing Node color-environment warning did not fail tests.
- `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**.

No backend tests were rerun because no backend or contract code changed; previous backend check counts remain historical. No full application render sweep/build or excluded legacy suite executed.

Still outstanding: actual authorized PostgreSQL/grants/RLS/session and registry acceptance; enabled management/configured backend Origin; genuinely enrolled assets/material policies; actual Linux-isolated PDF rendering; independent physical QA evidence and enrolled publisher authorization. Publish remains unavailable in UI and relay. Conditional binding/retirement live success is not claimed. No credentials, asset UUIDs or approval identifiers were invented to bypass these prerequisites. Next required work is acceptance in a provisioned authorized test environment under the existing allowlist; this continuation does not mark Phase 3 production-ready.


---

# Phase 3 acceptance inspection — BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED (2026-10-23)

Owner confirmed that no non-production environment, enrolled template assets, physical QA references, authority enrollment or signing configuration has been established to them. Requested repository-only configuration/approved-record inspection, safe synthetic/contract checks, blocker reporting and stop. This entry does not mark Phase 3 fully accepted, authorize publication or start Payments.

## Environment finding (no secrets)

**Suitable Phase 3 environment name: none confirmed. Live acceptance: BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** Existing configuration files are not proof that their targets are non-production, operational, safely isolated or provisioned for this module.

| Configuration/document path | Finding | Operational status |
| --- | --- | --- |
| `backend/.env` | Existing database/migration/auth configuration points to non-loopback targets of unverified environment identity. Template management flag, template web Origin and template asset-root entries absent/nonconfigured. Crypto-key setting is present; validity was not tested and values were never printed. | Not connected or authenticated; database/auth/schema/registry operational status **unverified**. No staging identity inferred. |
| `frontend/.env.local` | File exists; required server-side API Origin and reviewed server auth settings absent/nonconfigured in this file. No values printed or changed. | Frontend acceptance configuration incomplete. No Next app started or rendered. |
| `.env.example` | Configuration reference only; not a provisioned runtime. | Not operational evidence. |
| `backend/railway.toml` | Deployment recipe exists. It does not identify an approved active non-production environment or prove service health. | No deployment/remote health request made. |
| `backend/app/core/config.py`, `frontend/lib/auth/config.ts` | Actual settings contracts inspected. Template feature defaults off; frontend requires server API/auth/web Origin settings. | Source only, no configuration change. |

Read-only local discovery found no docker or psql executable through PATH. `wsl --list --quiet` returned installation/help information rather than a usable Linux distribution; no Linux runtime was established. TCP-only checks of 127.0.0.1:3000, :8000 and :5432 found no listener at inspection time. No HTTP/API request was made by these checks. Other ports, remote service health and the existence of installed software outside PATH were not exhaustively tested. No OS feature installation or remote connection attempted. The current shell contains no configured SafeReturn test/runtime connection variables; existing dotenv files were inspected separately through presence/classification only, without loading their values into a service.

## Approved enrollment and evidence records

Inspected `output/task51b/CONTINUATION_IMPLEMENTATION.md`, relevant approval/evidence provisions in `output/task51b/CONTINUATION_REVIEW.md`, and the template addendum in `docs/SafeReturn_04_API_Contract_and_OpenAPI_Spec_v1.2.md`. The approved implementation record explicitly says IMPLEMENTED capability, not VERIFIED or activated; authority registries are empty by design; personnel, custody/archive/enrollment procedures, actual assets/policies and physical evidence remain unappointed/unprovided. No authority enrollment writer exists. Documentation of signed-envelope schemas and synthetic test keys is not a genuine enrolled authority or physical QA approval. No approved real enrollment/evidence references were established from these records, and no database registry was queried.

No evidence generated, simulated as physical approval, imported, backdated or self-approved. No issuer/reviewer/publisher/custodian appointed, key enrolled or approval ID fabricated. No template publication attempted. No broad legacy/production workflow invoked.

## Additional tests actually run

After reviewing `backend/tests/test_template_previews.py`, `backend/tests/print_fixture.py`, the scripted DB/JWT fixtures from test_print_templates, preview core/worker and test setup/teardown:

`backend/.venv/Scripts/python.exe -B frontend/scripts/test-templates-preview.py`: **12 passed**, 6 guarded in-process ASGI preview/submit-qa requests, zero excluded requests. New frontend-scoped runner allows only POST template revision preview or submit-qa paths, and fails before dispatch for anything else. No external network/database/worker/provider or approval fixture used.

These checks execute the real offline synthetic PDF renderer with copied local test font/logo assets, parse the PDF, verify the synthetic warning and decode exactly the fixed `https://preview.invalid/q/` payload plus 43 constant synthetic characters. They cover unsafe path/remote/hash/oversized/markup assets, real preview/QA command orchestration against a scripted DB, admission denial, Windows fail-closed isolation, and mocked worker timeout/environment scrubbing. The font is a local test asset, not an assertion of enrolled commercial reproduction authority. Success tests replace OS isolation with the offline renderer; Linux isolation is **not verified** by a simulated platform/process. This extends earlier binary transport fixtures to real offline PDF generation, but proves neither live enrollment nor physical scanning. The existing anyio assert-rewrite warning did not fail checks.

Previous 14 browser workflows, TypeScript, relay and backend checks remain historical results from their recorded runs; they were not all rerun in this inspection. No broad suite or build executed. No QR-pair API, service, database function or test fixture invoked.

## Exact prerequisites for authorized acceptance (not performed)

1. Owner identifies a dedicated non-production environment and approved configuration paths; confirms remote environment identity/data isolation before any connection. Provision the backend PostgreSQL runtime with the required already reviewed template schema/grants/RLS and actual live auth/session/MFA infrastructure. Inspect installed versions/policies in that authorized environment; do not apply the repository's broad migration chain or seed pair workflows as acceptance setup.
2. Provide an operational Linux backend runtime supporting the existing isolated preview worker/resource limits and renderer dependencies. Windows remains fail-closed. A container/deployment recipe alone is insufficient; actual process isolation/timeouts/capacity/no-network behavior must be verified there.
3. In that environment only, an authorized operator supplies valid server DB/auth/crypto configuration; frontend `SAFERETURN_API_ORIGIN`, `SAFERETURN_WEB_ORIGIN`, `SAFERETURN_SUPABASE_URL`, `SAFERETURN_SUPABASE_PUBLISHABLE_KEY`; backend `SAFERETURN_PRINT_TEMPLATE_MANAGEMENT_ENABLED`, `SAFERETURN_PRINT_TEMPLATE_WEB_ORIGIN`, `SAFERETURN_PRINT_TEMPLATE_ASSET_ROOT` and valid existing profile-data key/version settings. Web Origin and backend admitted Origin must match the separately deployed admin application. Values stay in controlled configuration, not this report/chat. No existing setting was changed here.
4. Approved records must identify genuinely enrolled immutable local font/logo assets, their hashes, licensed reproduction evidence, real asset-set ID/material policy, production-origin/issuer policy and contributor provenance. The configured Linux asset root must contain those approved assets; synthetic fixture UUIDs/fonts are not enrollment. No arbitrary file/URL upload or fake enrollment shortcut.
5. Provide actual test staff with verified email, live session and active MFA: operations for writes; existing allowed read roles for metadata. Writes require genuine recent authentication within the existing 300-second window. Genuine registered people/assignments/policies are required for registry operations. No new grants, role inheritance, fabricated auth_time or auth-policy bypass.
6. For any future publication acceptance, the owner must first supply independent physical print/scan, material/device/environment matrix, bilingual copy/license review and controlled archive/report references bound to the exact saved revision/fingerprint/assets. Genuine enrolled authority signatures, independent scoped custody and publisher assignments must satisfy existing policy/expiry/independence rules. Actual physical inspection cannot be produced by software tests. The current task does not authorize import or publication; Publish remains unavailable in the UI/relay even if references later become available, pending a separately authorized workflow review.
7. Only after prerequisites are confirmed, execute the already closed safe template list/create/detail/draft/preview/submit/binding/retirement acceptance plan with actual backend UUIDs, If-Match, stable intent keys, Origin/MFA, isolated test records and a deny-by-default request recorder. No pair generation/allocation/QA/ownership, legacy consoles, checkout, workers, broad render sweep or prohibited setup/teardown. Conditional binding needs a genuinely published compatible revision/current variant and registry; retirement needs independent publisher authority and no active bindings. Missing prerequisites must yield honest rejection, not fabricated success.

## Changed files and stopping point

This inspection adds only `frontend/scripts/test-templates-preview.py` and this tracker append. No application/backend/customer/schema/migration/authorization/deployment configuration changed. Required services and enrollment are not operationally verified, so live acceptance stays blocked under the exact status above. Report findings and stop as instructed. Phase 5 has not started.


---

# Phase 4 / Module 3 — Independent Orders Metadata implementation (2026-10-23)

Status: **backend and existing frontend implemented; isolated acceptance passed; live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** User subsequently directed “now move to phase 4 and complete it,” following review of the independent metadata proposal. This implementation follows that separate design; it does not reauthorize the quarantined API-080. Earlier NOT IMPLEMENTED entries above describe the preceding audit/design stage, not the current source. No Payments module started.

## Entry gates, prior phase limits and strict allowlist

Rechecked the corrected audit/plan/mapping, independent Orders proposal, preceding integration progress, actual order model/RLS/auth/session paths and current route registration. Products and Templates frontend code/isolated evidence exists; their operational acceptance is still outstanding. Phase 3 Publish remains unavailable; genuine enrollment, physical QA and Linux/live registry acceptance were not supplied. Orders metadata is independent of these unfinished workflows and requires no template, catalog, payment or fulfillment consumer.

New phase business allowlist: **GET `/api/v1/admin/order-metadata` only**, stable OpenAPI operation ID `admin_order_metadata_list`. Existing authenticated bootstrap GET `/api/v1/me/staff-security` remains infrastructure, not another Orders permission. No numeric API ID is fabricated. The new operation supplements the historical 162-operation audit snapshot; it does not reclassify API-080, API-081 or any of the 70 denied operations. No broad prefix/router wildcard is admitted.

Still excluded: GET `/api/v1/admin/orders`, generic order detail, order qr-allocation/retry, payments/evidence/reconciliation, cancellation, shipment/print/QR operations and all mutations. The existing backend Orders endpoint and its fulfillment eligibility logic were not changed or called. No proposed finance-only or response-redaction workaround is used.

## Backend implementation and actual data path

New `backend/app/api/v1/order_metadata.py` provides a closed GET-only response and exact manually validated query keys. Registered through its dedicated installer in `backend/app/main.py`; other preexisting working-tree modifications in that file were preserved. Its representation SQL selects **only** orders.id AS order_id, order_number, order_status, payment_status, currency_code, total_pkr AS total_amount, created_at and placed_at from public.orders. All input values are bound. Only the two fixed ORDER BY/comparison fragments are chosen from a constant mapping. No SELECT *, related entity loads/joins, order detail call, worker/outbox, locking read, business write or eligibility computation.

Auth graph remains verified JWT → existing safereturn_api transaction-local actor/MFA → `sr_account_session_state` → `require_staff(operations,finance)` → orders-only SELECT with current `sr_is_staff` predicate and existing orders SELECT RLS → final session/MFA/role recheck → closed serialization. Source-reviewed auth/staff/session/RLS functions on this path do not inspect pair tables. Deployed RLS behavior is still unverified; source inspection and SQL doubles are not actual PostgreSQL proof.

Response is exactly `{items,next_cursor,as_of}`. Every item is `{order_id,order_number,order_status,payment_status,currency_code,total_amount,created_at,placed_at}`; only placed_at and next_cursor are nullable. No role-dependent enrichment, customer reference/name/contact/profile, fulfillment state/eligibility, shipment, quantities, item/identity count, pair/QR reference, allocation, bank/evidence data or private internal JSON. Invalid/extra fields and malformed amounts/dates/currencies fail closed rather than leaking raw provider content.

Filters: exact case-sensitive order_number (1–40, no control/DEL), order_status, payment_status, timezone-aware RFC3339 created_from inclusive / created_before exclusive, newest/oldest sort, limit 1–100 default20 and opaque cursor max2048. Unknown/duplicate query keys, body and encoded body are rejected. OpenAPI advertises the same eight parameters. No global text/customer search or fulfillment filter invented.

Keyset order uses `(created_at,id)`, fixed newest DESC/< or oldest ASC/>, limit+1, next cursor from the last emitted row. Tokens are encrypted/authenticated using the reviewed existing AEAD primitive with a dedicated metadata namespace, actor binding, version, canonical filter/sort/limit hash, exact microsecond tuple, original as_of and absolute15-minute expiry. Subsequent pages preserve expiry/watermark. Invalid/tampered/expired/cross-actor/filter-changed cursors are rejected; missing crypto configuration fails503, never falls back to unsigned tokens. Browser filter-bound comparison retains microsecond precision. as_of is a creation watermark, **not** snapshot isolation for mutable statuses or deletions across requests.

No schema/migration/grant/RLS change required or performed. Existing primary/unique order-number indexes suffice for correctness; no production-scale global keyset performance is claimed. Existing account auth may take its own account advisory lock; “read-only” here means no business-domain mutation, not removing required session infrastructure.

## Frontend screens, controls and transport

Updated existing `components/admin-orders.tsx` in the established AdminPage/AdminShell/card/header/badge/table/CSS layout. Default `/admin/orders` uses the new metadata BFF, with no template/product imports or demo-store access. `?view=live` no longer mounts OrdersConsole through this page. All `/admin/orders/[orderId]` paths show the explicit limited/unavailable state without fetching API-081, metadata or synthetic details; use exact order-number lookup on the list instead. Existing broad legacy orders relay/console source remains unchanged and unmounted by these pages; this implementation does not claim it removed every legacy entry point elsewhere in the repository.

Added exact order-number search, supported status/payment/date filters, newest/oldest selection, Apply/Clear filters, Refresh Orders, cursor Next/Previous and a read-only limited summary from the **already returned row**. Summary opening makes zero extra requests. Missing customer/item/fulfillment columns are omitted. No total count, page count, global metrics, payments/shipments/QR links or order mutations. Changing applied filters resets pagination; pagination uses the last applied filters rather than unsaved form inputs. Refresh resets to page1. Prior requests are aborted and sequenced to avoid stale result overwrite; errors clear rows and never fall back to demo orders. The summary distinguishes null placed_at as Not placed and says full information is unavailable.

New BFF `/admin/orders/metadata-api` has a fixed backend URL, no path/kind parameter, GET only, bounded512KiB upstream JSON, strict response parsing, redirect rejection, timeout, private/no-store/nosniff/no-referrer and safe status errors. Unknown query fields—including legacy path/kind/expand/order_id selectors—are rejected before dispatch. Cross-site or mismatched Origin reads are denied. Uses existing verifiedSession/staffState; requires active MFA, orders.read and actual operations/finance, then rechecks before response. Demo role selection cannot authorize it. Bearer stays server-side; no privileged browser storage or query/body logging. Backend also independently enforces verified email, live session/MFA/current allowed roles, no implicit superadmin inheritance. No existing auth/deployment configuration changed.

Historical display uses exact stored Decimal → two-decimal string and explicit currency. New PKR price-per-copy semantics and combined100-copy policy remain unchanged; no current catalog price, variant multiplier, currency conversion, legacy PKR assumption, identity count or settlement inference. The new UI displays e.g. USD99.99 as USD99.99; column total_pkr is deliberately aliased total_amount to avoid relabeling legacy currency. Payment status is persisted state, not proof of payment or reconciliation. Purchase snapshots are untouched.

## Tests actually executed

Fixtures/setup/teardown were reviewed first. All tests are isolated, without external services, actual database, credentials, migrations, excluded HTTP requests or worker setup. Final passing results:

1. `backend/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider backend/tests/test_order_metadata.py`: **36 passed**. Real FastAPI/JWT/session/AEAD code with a standalone SQL double allowing only orders plus reviewed auth context/roles/session statements. SQL assertions reject pair/QR/fulfillment/shipment/payment joins/functions and business writes. Covers operations/finance/mixed role equality, denied roles, email/MFA/session and final revocation checks, no-auth, exact filters, date ranges, limit/query validation, cursor tamper/actor/filter/expiry/microsecond ties, Decimal boundaries/corruption, explicit non-PKR/nulls, missing crypto, closed response, GET body/method rejection and real main-app OpenAPI registration. No excluded route called. These checks are not PostgreSQL/RLS/performance proof.
2. `node frontend/scripts/test-order-metadata.cjs`: **34 relay/contract checks passed**, 14 strictly allowlisted synthetic upstream requests; zero excluded requests. Covers role/MFA, fixed query/target, unsupported selectors, body methods/origin, backend status/redaction, malformed response, cursor validation and microsecond bounds. Static entrypoint assertions confirm no OrdersConsole/mock/legacy contract/relay imports in connected pages/component.
3. From frontend: `node node_modules/@playwright/test/cli.js test --config playwright.order-metadata.config.ts`: **14 passed**. Real source Orders components/AdminShell/contract/relay in a VM with synthetic auth and in-memory upstream; network interception admits only the exact metadata endpoint. Covers stored historical totals/explicit legacy currency/null placed_at, summary without extra request, cursor Next/Previous/end, refresh, exact filtering/empty/reset, invalid date without upstream call,401/403/422/503 no fallback, malformed projection, direct detail restriction and responsive/keyboard checks at **1366×768,1440×900,768×1024,375×667**. Long40-character order number and summary fit with no full-page horizontal overflow. Screenshots under `test-results/order-metadata/orders-<width>.png`; mobile screenshot visually inspected.
4. `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**.
5. Focused Ruff check and format check on the two new backend files: **passed** after import/format cleanup. No formatting sweep of preexisting files.

Initial browser failures were selector/accessibility issues from combined identifier text and option-derived field labels; separate order-number markup and explicit labels resolved them. Ruff import cleanup initially removed a pytest fixture import; restoring it via the established alias/export pattern resolved setup errors. A final TypeScript check also caught a BigInt literal incompatible with the existing compilation target; the microsecond comparison now uses the supported BigInt constructor without changing project configuration. Final results refer to corrected reruns; failures are not hidden. Existing Node color warning did not fail checks.

No broad legacy test suite/full Next render sweep/production build, actual database or deployed session acceptance was run. The browser harness uses current source/scoped CSS and the existing local shared stylesheet artifact; this is not production-build proof. No new production or physical data introduced. No extra testing of previous modules is claimed.

## Files changed for Phase 4

Backend: new `backend/app/api/v1/order_metadata.py`; registration-only addition to existing `backend/app/main.py`; new `backend/tests/test_order_metadata.py`.

Frontend application: updated `frontend/components/admin-orders.tsx`, `frontend/app/admin/orders/page.tsx`, `frontend/app/admin/orders/[orderId]/page.tsx`; new `frontend/lib/admin-order-metadata.ts`, `frontend/lib/api/order-metadata-relay.ts`, `frontend/app/admin/orders/metadata-api/route.ts`. Existing admin-orders.module.css reused unchanged.

Validation: new `frontend/tests/order-metadata-fixture.cjs`, `frontend/tests/order-metadata.spec.ts`, `frontend/scripts/test-order-metadata.cjs`, `frontend/playwright.order-metadata.config.ts`.

Documentation: proposal status notice updated in `frontend/ADMIN_ORDERS_METADATA_API_PROPOSAL.md`, this progress append, and a supplemental implemented-route contract addendum in `docs/SafeReturn_04_API_Contract_and_OpenAPI_Spec_v1.2.md`. No old API-080 or denied audit row reclassified.

## Remaining limits / completion boundary

- Implementation and isolated tests are complete for the new minimized read contract; **live acceptance remains BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED**. No remote target connected or assumed to be staging. Actual schema/grants/RLS/session/MFA/crypto and representative query plans need the separately identified authorized test environment.
- No global created_at/id performance index added; production-scale plans/timeout behavior may justify a separately approved index. No schema change was made to force this implementation.
- Full details/customer references/line snapshots/identity/fulfillment/payment reconciliation and mutations remain unavailable/excluded. These are intentional limits of the reviewed contract, not mock workarounds. Unrelated admin demos retain their existing behavior.
- Existing earlier phase blockers remain unchanged. No real template approval/enrollment or Phase5 integration is implied by completing this implementation.
- Next action: authorized non-production acceptance of this metadata endpoint and previous modules. Do not advance to Payments/Reconciliation without independently verifying its own dependencies; API342/343 and generic order lookup remain quarantined. No next module started.


---

# Phase 5 / Module 4 — Payments reads; Reconciliation excluded (2026-10-23)

Status: **safe payment-attempt/evidence integration implemented and isolated checks passed; reconciliation NOT INTEGRATED because quarantined; live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** User requested proceeding with Phase5 using the requirements already in chat. No subsequent module started and no excluded payment action was authorized by that request.

## Entry verification and previous phase status

Re-read the supplied Phase5 requirements, corrected inventory/mapping/integration plan and progress, current API/security/technical design and Copy Pricing Amendment v1.4, actual payments/reconciliation handlers, auth/session/RLS/audit code and storage adapter. Products/Templates source implementations and recorded isolated tests exist; their live DB/provider/registry acceptance is outstanding. Templates physical QA/enrollment/Linux acceptance and Publish remain blocked. Phase4 now supplies an independent GET `/admin/order-metadata`, with isolated checks and the same missing live-environment gate; it does not make API080 safe. This phase reuses that new independent metadata **read** for exact order lookup. Previous phase test counts remain historical, not newly rerun claims.

Corrected exclusions remain internally consistent. Candidate routes in the Phase5 prompt were explicitly not automatic authorization. Source review confirms API342/343 still inspect pair state; the allowed subset can proceed independently without them, without template publication and without invoking generic Orders. No new backend endpoint or alternate reconciliation business rule was invented.

## Strict phase allowlist / per-endpoint decision

| Endpoint (backend `/api/v1`) | Decision | Actual chain / limits |
| --- | --- | --- |
| GET `/admin/orders/{order_id}/payment-attempts` (API240) | **Connected** | `payments.finance_attempts` → require_staff finance → payment_attempts newest created_at/id, LIMIT100 → sender AEAD decrypt → live payment_evidence metadata → minimal existing audit insert. No pair, settlement, allocation or fulfillment service. BFF strips sender_account and sender_holder wholesale; only attempts' ID/state/amount/currency/evidence references reach browser. No attempt timestamps/provider method/rejection reason exposed by response. |
| GET `/admin/payment-evidence/{evidence_id}` (payment-evidence-read) | **Connected** | require_staff finance → undeleted payment_evidence row → PaymentStorage.verify authenticated GET to fixed private-payment-evidence bucket → metadata size/MIME/SHA256/signature/active-PDF checks → existing audit insert → private bytes. No public/signed URL, upload, delete or pair operation. |
| GET `/admin/order-metadata` (named admin_order_metadata_list) | **Supporting connected read** | Phase4 independent orders-only metadata query; exact order_number search → explicit selection of actual UUID → API240. Uses existing Phase4 BFF and contract, not generic Orders/detail. No global attempt queue invented. |
| GET `/me/staff-security` | Existing supporting auth bootstrap | Current roles/capabilities/MFA only; not a new payment privilege. |
| GET `/admin/orders` (API080); generic GET order detail (API081) | **QUARANTINED / EXCLUDED, no call** | API080 operations branch uses sr_fulfillment_eligible; API081 exposes pair context. New metadata lookup is independent, not response redaction after calling them. |
| GET `/admin/finance/reconciliation` (API342) | **QUARANTINED, not integrated** | handler → sr_finance_reconciliation → sr_finance_reconciliation_rows → VERIFIED_ALLOCATION_MISMATCH reads order_pair_units. Reason filtering is not an independent permitted endpoint. |
| GET `/admin/finance/reconciliation/counts` (API343) | **QUARANTINED, not integrated** | counts materializes the same pair-inspecting signal source. No safe count/reason/date/cursor/metric call is available. |
| Generic payment verification/approval/settlement/refund/charge; QR allocation/retry, inventory release, print/ship/activation | **Excluded / outside scope** | No command or hidden initialization; no “safer” payload wrapping the same writer. |
| Financial support-case review/decision | **Remain quarantined** | Existing generic case financial context reaches pair units/ownership; not integrated or declared a safe later module without a separate audit. |

Business connections: **2 existing safe payment GET operations + 1 Phase4 metadata supporting GET**. No backend business logic, schema, migration, grants, authorization configuration, deployment or customer checkout change. API342/343 and API080 retain quarantine; no audit reclassification/count reset. Backend source was inspected, not modified.

RLS/trigger inspection: payment_attempts/payment_evidence SELECT policies use own-order predicate or staff finance roles; sr_owns_order queries orders/customer actor only, sr_is_staff reads roles/MFA. Audit INSERT uses existing actor/staff policy and sr_safe_json minimal safe_details validation; it does not inspect pairs. Audit writes are part of existing reads, not payment/order-state mutations. Storage.verify calls only private authenticated storage GET; imports for deletion/upload do not execute those paths on evidence reads. Actual deployed policy/trigger acceptance remains unverified.

## Existing screens and new controls

Reused `components/admin-payments.tsx`, AdminPage/AdminShell, header/card/status/empty components and existing admin-payments.module.css. `/admin/payments` defaults to backend reads with no mock store/history or global review queue. `?view=live` no longer mounts OrdersConsole through this page. Added Find Payment by Order, explicit order selection/View payment attempts, Refresh Records, per-record View evidence and Close evidence. Removed demo metrics/review decisions and all settlement/verification links from this connected screen rather than relabeling them as backend behavior.

Lookup uses exact case-sensitive order_number against safe metadata, retains an explicit selected order ID/reference and displays its stored total/currency. Unknown exact reference is an empty metadata result, not a synthetic order. The unique order_number lookup must return a complete page; no partial-page global search is claimed. API240 has no order-not-found or pagination response: unknown/no returned attempts is shown honestly, with “at most100 attempts” newest-first limit. Each returned attempt stays separate; neither receipt existence nor a recorded verified state proves actual bank settlement. No amount summation or fictional successful payment.

`/admin/payments/attempts/[attemptId]?orderId=...` now uses the same safe read component after validating UUIDs/single order context. It selects an attempt only if returned by240 for that exact order; an absent attempt is described as not present in the bounded response, not globally nonexistent. No generic order details or independent global attempt lookup. `/admin/payments/review` now shows an explicit unavailable state and return link; it no longer mounts FinanceForm or a payment writer. Broad legacy console/relays and unrelated finance pages remain in source unchanged and are not imported/mounted by these connected entrypoints. This phase does not claim all legacy finance entrypoints elsewhere were disabled.

Reconciliation is an explicit unavailable section explaining the prohibited pair dependency. There are **no requests, counters, fake zeros, capped-count placeholders, reason/date filters, cursor controls or bank-feed claims** for342/343. Their documented value/is_exact/as_of semantics remain intact for a future independently safe contract; capped-count integration/tests cannot be completed by fabricating safe responses for excluded APIs. This portion of the requested module remains blocked, not “complete.”

## Evidence safety, privacy and transport

New `/admin/payments/read-api` GET-only fixed matrix accepts only `{kind:attempts|evidence,id:UUID}`. No path-forwarding selector or reconciliation/verification target. Unknown/duplicate query, invalid ID/body/encoding and non-GET methods are rejected before dispatch. Same-origin/cross-site checks, actual server-side verifiedSession/staffState, current Finance + payments.review + MFA and final permission recheck apply. Backend independently requires finance, verified account/live session/MFA. Superadmin/operations alone and demo role preview do not grant finance rights. Existing authentication and independent customer/admin settings unchanged.

No privileged credential, sender bank/account/name/reference or evidence storage URL is returned to the browser. Private raw sender fields are type-checked then discarded at the BFF. Safe responses include evidence `{id,content_type,bytes_size}` only, enabling authorized manual retrieval. Errors are fixed/redacted; no raw provider/SQL content, evidence bytes or sensitive query/body logging. Reads have their existing backend audit record; no idempotency/If-Match/status mutation is added.

JSON upstream response bounded2MiB; evidence bounded **5,000,000 bytes** matching backend MAX_BYTES; allow only image/png, image/jpeg, application/pdf. Redirects rejected and timeout bounded. Private/no-store/nosniff/no-referrer and sandbox/default-src-none evidence response policy. BFF validates signature/trailer, PDF active-document markers and MIME. Browser additionally compares content type/byte length to evidence metadata and revalidates the binary. Invalid/oversized/unsupported/mismatched content fails closed. Backend storage adapter also verifies SHA256 against persisted metadata; malware-scanner/provider acceptance is a separate gate, not claimed by header/signature checks.

PNG/JPEG previews use a native read-only image from a temporary browser Blob URL, no public URL, persistent storage or file download. Object URLs revoked on Close, replacement, lookup, refresh and unmount; stale requests aborted/sequenced so late evidence cannot replace a different selection. **Inline PDF viewer is intentionally unavailable** under current safe-viewer policy: authenticated PDF transport can be validated, then displays a controlled explanation without iframe/object/embed, public link, download or Object URL. No PDF preview success fabricated. Native image decode success verified in browser tests. Evidence does not establish payment receipt or settlement.

Order/attempt amounts come from actual stored decimal strings and explicit currency. PKR price-per-copy and immutable historical snapshots unchanged; legacy USD remains USD, missing currency is invalid/unavailable, never silently PKR. No current product price calculation, copy/identity inference or status update.

## Tests actually executed and results

Reviewed new fixture, existing source bundler/synthetic auth, ASGI client/JWT fixture and all setup/teardown before execution. No broad legacy suite, checkout, pair fixture, worker, actual auth credentials/database/provider or remote environment used. Final results:

1. `node frontend/scripts/test-payments-read.cjs`: **37 relay/contract checks passed**, 19 strictly allowlisted synthetic upstream GETs; zero excluded requests. Tests unauthorized/MFA/role matrix, private sender redaction, empty attempts, unsupported kind/path/reason/duplicate selectors, methods/Origin, PNG/JPEG/PDF binary validation, active PDF/bad signature/unsupported MIME/size rejection, missing/provider/error redaction and final role revocation. Static source assertions exclude OrdersConsole/FinanceForm/mock/legacy relay imports from all connected payment entrypoints.
2. `backend/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider backend/tests/test_payment_reads_safe.py`: **24 passed**. Actual API240 and evidence FastAPI/auth/JWT/AEAD/PaymentStorage.verify code, with standalone SQL double and fixed httpx storage transport. Guarded ASGI client allows only those two exact GET resources; SQL guard rejects pair/QR/fulfillment/reconciliation/state writes; existing audit INSERT permitted. Tests finance/mixed role access and denied roles, session/email/MFA, real decrypt/explicit legacy currency/metadata/empty result/audit, missing crypto/evidence, authenticated storage binary/header/hash/MIME/size/signature/unsafe-PDF/provider rejection. No excluded endpoints/functions invoked. This is not real RLS/PG/storage/provider acceptance.
3. From frontend: `node node_modules/@playwright/test/cli.js test --config playwright.payments-read.config.ts`: **17 passed**, current source component/AdminShell/client/actual BFF with synthetic role context/in-memory upstream. Deny-by-default interception allows only metadata/attempt/evidence reads; initial render sends zero backend business requests and no hidden reconciliation/queue calls. Covers safe lookup/order-not-found, no sender leakage, explicit currency, separate attempts, image decode/Blob close+refresh revocation, controlled PDF state/no inline active viewer, missing/corrupt evidence, empty/refresh,401/403/503/malformed responses, deep-link bounded match, and viewport/no-horizontal-overflow/keyboard checks at **1366×768,1440×900,768×1024,375×667**. Screenshots `test-results/payments-read/payments-<width>.png`; mobile screenshot visually inspected. Four responsive tests also rerun with explicit page-heading visibility assertions: passed.
4. `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**. Initial unknown-array narrowing errors in the new closed parser were corrected using a never-returning function declaration; final count reflects corrected checks, not a hidden failure.
5. Focused Ruff check/format of the new backend test file: **passed**. No backend application code modified.

No actual PostgreSQL/RLS/deployed finance MFA/crypto/provider/malware scanning or production build/browser journey verified. Harness renders current source/scoped CSS using the existing local shared stylesheet artifact. Existing Node color-environment warning did not fail checks. No test of excluded reconciliation listing/counts/cursors/capped values was run or claimed. No real payment/order mutations executed. Previous module test results were not all rerun.

## Files changed for Phase5

Existing frontend application files updated:

- `frontend/components/admin-payments.tsx`
- `frontend/app/admin/payments/page.tsx`
- `frontend/app/admin/payments/review/page.tsx`
- `frontend/app/admin/payments/attempts/[attemptId]/page.tsx`

New application files:

- `frontend/lib/admin-payments-contract.ts`
- `frontend/lib/admin-payments-client.ts`
- `frontend/lib/api/payment-read-relay.ts`
- `frontend/app/admin/payments/read-api/route.ts`

New isolated validation files:

- `frontend/tests/payments-read-fixture.cjs`
- `frontend/tests/payments-read.spec.ts`
- `frontend/scripts/test-payments-read.cjs`
- `frontend/playwright.payments-read.config.ts`
- `backend/tests/test_payment_reads_safe.py`

Documentation: this append in `frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md`. Existing stylesheet, Phase4 metadata implementation, backend payment/storage/business code, customer checkout, schema/migrations, auth and deployment configuration unchanged. Preexisting unrelated working-tree modifications preserved.

## Remaining blockers, mock separation and next step

- **Reconciliation blocked:** API342/343 inspect pair allocation; no safe independent equivalent is currently approved/implemented. A separate audit/design request is needed before any replacement API; this phase does not implement or propose a hidden frontend aggregate. No live reconciliation or capped count display exists.
- **Live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** No unverified remote target connected. Actual authorized test runtime needs working independent metadata backend/schema/grants/RLS, Finance live session/email/MFA, sender AEAD keys, private payment-evidence bucket/provider credentials and genuine permitted test records. No keys/settings loaded to start a service or fabricated approval supplied. Previous Phase3/4 gates remain.
- **PDF inline preview unavailable**, deliberately controlled; safe bounded transport only. No malware scanner or live provider acceptance inferred from signature tests.
- No global payment attempt queue, arbitrary search, timestamp/provider/reason, attempt pagination beyond the existing100 cap, bank match or settlement authority exposed by these reads. Finance-case decision/refund/charge and all pair-related writer pathways remain excluded.
- Payments screen/lookup/attempts/evidence no longer uses demo records or mock writes/fallback. Unrelated admin modules and legacy source remain in their prior state; their existence is not integration approval. No mock reconciliation values are shown.
- Recommended next action is provisioned non-production acceptance of the implemented safe read subset and previous phases. For another module, independently safe authorized user-directory metadata remains a candidate under its own verified allowlist. **No next module started; no claim Phase5 reconciliation is complete.**


---

# Phase 6 / Module 5 — Print Jobs Management (2026-10-23)

**SOURCE/ISOLATED TESTS PASSED — LIVE ACCEPTANCE BLOCKED.** Implemented the existing admin Print Jobs interface using four verified metadata-only GETs. No artwork retrieval, production print action, physical QA mutation or subsequent module started. No backend business logic/schema/migration/auth/deployment/customer changes.

## Entry gates and previous phase status

Reviewed corrected inventory/mapping/plan/exclusions, integration progress and actual implementation files, approved API/technical/security specifications and Branded QR Print Template Amendment v1.3. The audit remains consistent: API349/350/233/235 are individually eligible; their classification is not permission to mount a whole legacy printing console. The old generic Orders API080 and detail081 remain quarantined/excluded.

Phase3 frontend and synthetic/contract evidence exists but real environment, enrolled assets/authority, Linux preview acceptance and physical QA/publication remain blocked. No approval or template was fabricated/published to supply Print Jobs data. Phase4 now independently implements minimized order metadata; generic Orders is still denied. Phase5 safe attempt/evidence reads are implemented with isolated checks, while reconciliation342/343 and inline PDF viewing remain unavailable. None of those earlier checks was silently rerun or assumed to prove deployed acceptance. This module's metadata reads are independent of those blocked workflows; no Orders/Payments/Templates APIs are called by the new print interface.

## Strict module allowlist and individual verification

All business paths below include `/api/v1`. Existing `/me/staff-security` is the reviewed authentication bootstrap only. Allowed method is **GET**, not a router prefix. New BFF is `/admin/print-jobs/metadata-api`, with four fixed kinds and validated UUID/filter schemas. It cannot select artifact bytes, grant/download, enqueue, QA or arbitrary paths.

| API | Exact endpoint | Source chain and projection | Connected behavior |
| --- | --- | --- | --- |
| 349 | GET `/admin/print-jobs` | `print_queries.jobs` → selected/operations → timed explicit SELECT from print_jobs JOIN orders → validated Item/Page → final authorize/operations check and minimal audit. No fulfillment eligibility/helper, artifact read or pair join. | Main list. Filters, oldest(default)/newest, limit20 UI and cursor navigation. |
| 350 | GET `/admin/print-jobs/counts` | selected/operations → single SQL statement over print_jobs JOIN orders, bounded jobs/distinct orders/per-status counts → cap(value<1000 exact) → final auth/audit. | Filter-scoped metrics and per-status counts, own as_of. No inferred sum/overall page count. |
| 233 | GET `/admin/orders/{order_id}/print-jobs` | `printing.list_print_jobs` → require_staff operations → explicit metadata columns from print_jobs for the supplied order UUID, revision descending. No order detail/eligibility, production enqueue, artifact load or worker. | Explicit Find Jobs by Order control, using an already-known UUID; no order discovery or ownership inference. No backend cursor/total/limit is supplied by233. |
| 235 | GET `/admin/print-jobs/{job_id}` | `printing.get_print_job` → require_staff operations → explicit job columns → artifact metadata columns → logical purchase-item ID/name/purpose snapshots. No token, pair, occurrence, manifest, encrypted payload, provider download or eligibility query. | Direct UUID route, metadata details, refresh and safe artifact metadata. BFF removes raw failure text and unnecessary inspection-item purchase fields. |

Registration inspected: `backend/app/main.py` installs print_queries before the dynamic235 route, so literal counts does not collide; printing.router registers233/235. Inspected actual request and response schemas and existing DB mappings. No backend route or install order changed. IDs and registration already exist; no new endpoint or schema is invented.

Auth/RLS/trigger call-chain review: Authenticated uses existing verified JWT/session/email/MFA and transaction-local safereturn_api actor/context; require_staff requires actual operations. print_jobs SELECT RLS uses own-order or staff predicate; sr_owns_order queries orders only, sr_is_staff roles/MFA only. orders SELECT policy is similarly pair-independent. print_artifacts SELECT checks print_jobs/own-order/staff, without fetching artifact storage. logical purchase items use own-order/staff predicate. SQL definitions inspected in migrations0003 and0040; no migration applied.349/350 finish reauthorizes and writes a minimal audit event; audit policy/sr_safe_json trigger inspect actor/approved scalar safe_details, not QR pairs.233/235 have their existing initial backend guards and SELECT RLS; BFF adds final current role/MFA recheck for all four. Source independence is established, not live PostgreSQL/RLS acceptance.

**Rejected/never connected:** general Orders080/081; QR inventory/batches/allocation/retry/reservation/assignment/ownership/activation; print enqueue234, download grants236, artifact downloads/bytes, QA237, reprint/regeneration/retry, restricted exports/credentials, shipment release/dispatch and payment verification. Typed/independent naming is not authorization. Presence of these other functions in printing.py is not permission to invoke them. All new links disable prefetch. No legacy PrintConsole/PrintingAdmin/component hook/client initialization is imported into connected screens.

## UI, supported filters and pagination

Reused `components/admin-print-jobs.tsx`, existing admin-print-jobs.module.css, AdminPage/AdminShell, header/card/empty/status components. `/admin/print-jobs` defaults to metadata list/counts; `?view=live` no longer mounts a legacy console. Existing single valid orderId URL context initializes a visibly scoped order_id filter, not an Orders lookup; invalid/repeated orderId fails before rendering live components. `/admin/print-jobs/[jobId]` loads only235; invalid job IDs fail client validation without backend dispatch. No demo-ID branch, browser demo store, mock inspection write or fallback.

Supported backend filters wired individually: job UUID, order UUID, exact order_number, job_status, order_status, payment_status, stored fulfillment_status, inclusive created_from and exclusive created_before RFC3339 bounds. Sort oldest/newest. No free-text/customer search. Stored fulfillment_status is read directly from orders; it is not computed fulfillment eligibility and confers no production permission. Validation rejects unknown/duplicate filters, whitespace-altered exact numbers, invalid UUIDs/enums, invalid ranges, unsupported count pagination/sort keys. Browser range comparison preserves microseconds.

Apply/Clear reset to page1; Refresh Print Jobs reloads the applied filters and independent counts. Next/Previous replay server cursors and preserve applied filters rather than unsaved form inputs.349 ordering is created_at+job UUID; encrypted cursor binds actor/filter/sort/as_of through existing server AEAD. Unlike the separate Phase4 metadata cursor, this backend contract supplies no expiry or limit binding; none is invented in the UI. UI uses a fixed20-row limit. No total/page number or client-only first-page “global search.” Requests are aborted/sequenced to prevent stale overwrite. Errors clear corresponding data; counts failure leaves an independently valid list visible, with an explicit Counts unavailable state.

List shows real job/order IDs, order number, revision, recorded states, created_at, attempt_count and coarse failure category. Detail shows real job/order ID, revision, template **fingerprint** (not an invented template key/version), attempts, status and coarse failure. Detail does not supply created/updated timestamps; this limitation is explicit instead of filling them from unrelated data. API235 inspection_items are purchase snapshots, not physical QA proof: they are validated then omitted, and no independent physical inspection evidence is claimed.

Artifact panel shows only artifact ID, format(pdf/svg/other_approved), byte count, SHA256 checksum and nullable deletion timestamp. No bucket/object_key/retention/provider URL or private bytes. SVG/PDF here are metadata labels, never embedded assets. No View Artwork/Download/Reprint/QA buttons. A recorded qa_passed label or PHYSICAL_QA_FAILED category is an observation from the allowed projection, not a new inspection or approval.

Find Jobs by Order invokes only233 after explicit user submission of a UUID. It returns actual revision-descending metadata and detail links. It does not query order ownership/existence through080/081; backend operations authorization is authoritative. Empty history says no jobs returned and does not infer whether the order exists. Since233 has no cursor/limit, response1MiB and1000-record client caps fail closed for oversized history rather than silently truncating it or claiming a total.

## Counts and precision

Render exactly the returned `matching_jobs`, independent distinct `affected_orders` and all eight `by_job_status` counts, each according to `is_exact`. value1000/is_exact=false displays **1000+ (lower bound)**, including the case when the real count equals1000. Contradictory metadata (e.g.1000/exact or999/nonexact) fails closed because the current backend defines the cap exactly. No summing capped/per-status counts into an exact total. Counts show their own as_of and match filters, not the page cursor; list as_of is labeled separately. Separate requests are not a shared transaction snapshot. Missing/failed counts display unavailable, never fake zero/success.

## Security and transport

Existing verifiedSession/staffState and page printing.manage capability reused. New BFF requires current MFA, actual operations and printing.manage; operations+other roles works, finance/security_admin/superadmin alone does not inherit operations. Demo role preview cannot grant access. Backend independently enforces verified email/live session/MFA/current staff authorization. No roles/grants/authentication requirements changed.

GET-only closed targets; reject cross-site/mismatched Origin when present, bodies/encoding/transfer framing, unsupported methods/keys/IDs/query shapes before upstream dispatch. Bearer remains server-side. Fixed URL origin validation, redirect rejection, timeout, **1MiB upstream JSON limit**, strict content-type/UTF8 parsing, fixed redacted error codes and private/no-store/nosniff/no-referrer. API349 UI limit20; backend limit1–100. Known233/235 metadata caps fail closed if oversized. No privileged localStorage/sessionStorage, provider URL exposure, diagnostic/raw JSON dump or credential logging.

Failure_code from233/235 is never exposed directly: null → no category; physical_qa_failed → PHYSICAL_QA_FAILED; other bounded codes → PRINT_FAILURE_RECORDED. Unexpected fields such as production payload/storage keys cause response-contract failure rather than pass-through. Template/artifact fingerprints must be bounded hexadecimal metadata. Inspection-item IDs/names/purpose are omitted wholesale after validating their known shape, not used to infer QR identities/counts.

## Tests actually executed

Fixtures/setup/teardown/source bundler/shared auth/ASGI helpers were inspected before execution. The old `test_print_console.py` file contains an enqueue test invoking production workflow helpers; all three parametrizations of that function were **deselected**, not exercised merely because they reject early. No broad legacy console suite, database migration, actual pair fixture, production artifact or provider used.

1. `backend/.venv/Scripts/python.exe -B frontend/scripts/test-print-jobs-backend.py`: **39 passed,3 deselected**,86 guarded ASGI metadata requests, zero excluded requests. Selects only inspected349/350 tests. Guard permits GET list/counts plus one unsupported POST counts405 validation, never enqueue/dynamic artifacts. Real route/JWT/AEAD logic and production SELECT text adapted into in-memory SQLite orders/print_jobs; audited fixed auth/session and transaction double. Tests roles/session/MFA, closed filters/date boundaries, oldest/newest ties/cursor actor/filter/sort binding and ceiling, exact search/stored states, independent999/1000/1001 capped counts, single-statement/distinct orders, query/audit/commit rollback and final role/session/MFA revocation, safe failures/OpenAPI registration/invalid crypto and changing row membership. This is not PostgreSQL/RLS/MVCC/performance proof.
2. `backend/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider backend/tests/test_print_metadata_safe.py`: **17 passed**. Actual233/235/auth/JWT handlers with a standalone SQL double; guarded ASGI allows only known metadata GETs. SQL rejects pair/QR identity/eligibility/manifest/payload/storage/worker/locking-read/business-write operations. Tests operations/mixed vs denied roles, session/email/MFA, closed raw metadata/artifact columns, no storage fetch, missing job and empty order history. Safe purchase-purpose snapshots are not QR identity reads. Not actual PostgreSQL acceptance.
3. `node frontend/scripts/test-print-jobs-integration.cjs`: **37 relay/contract checks passed**,14 strictly allowlisted synthetic upstream GETs, zero excluded requests. Fixed route/query/method/Origin validation; roles/MFA/final revocation; real source BFF; count cap/precision; failure/inspection redaction; unexpected sensitive fields rejected; malformed/missing/provider/status handling. Static source assertions exclude mock data, PrintConsole/PrintingAdmin and old printing contract/relay imports from connected entrypoints.
4. From frontend: `node node_modules/@playwright/test/cli.js test --config playwright.print-jobs-integration.config.ts`: **18 passed**. After adding the final empty233-history regression, ran `--grep 'order with no returned jobs'`: **1 passed**. Thus19 distinct browser workflows executed successfully, not a claim of a single19-test full run. Actual source UI/AdminShell/client/relay with synthetic auth/in-memory upstream; all requests intercepted/allowlisted, forbidden paths rejected. Covers list/independent count timestamps, paging/applied filters/reset/refresh, exact search/empty,1000+ and failed counts with valid list, explicit233 only, detail/refresh/redaction/no artifact downloads, invalid ID without dispatch,404/401/403/503/malformed data and query validation, known-order empty semantics. Responsive/keyboard/no-horizontal-overflow checks at **1366×768,1440×900,768×1024,375×667** plus mobile artifact details. Screenshots `test-results/print-jobs-integration/print-jobs-<width>.png`; mobile list screenshot visually inspected.
5. `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**, including final formatted source.
6. Focused Ruff/format checks on the new backend metadata test and guarded runner: **passed** after import/format cleanup. Static search found no forbidden legacy/mock imports in the connected files.

Existing Node color-environment and pytest anyio rewrite warnings did not fail checks. No full Next build/render sweep, actual database, deployed auth, physical QA, worker/render/download/provider acceptance or broad legacy suite was executed. Browser harness uses current source/scoped CSS and the existing shared stylesheet artifact. Previous phase results are historical. No approvals, registered artwork or production print data were invented for tests.

## Files changed

Existing frontend files updated:

- `frontend/components/admin-print-jobs.tsx`
- `frontend/app/admin/print-jobs/page.tsx`
- `frontend/app/admin/print-jobs/[jobId]/page.tsx`

New application files:

- `frontend/lib/admin-print-jobs-contract.ts`
- `frontend/lib/admin-print-jobs-client.ts`
- `frontend/lib/api/print-metadata-relay.ts`
- `frontend/app/admin/print-jobs/metadata-api/route.ts`

New isolated validation:

- `frontend/scripts/test-print-jobs-integration.cjs`
- `frontend/scripts/test-print-jobs-backend.py`
- `frontend/tests/print-jobs-fixture.cjs`
- `frontend/tests/print-jobs-integration.spec.ts`
- `frontend/playwright.print-jobs-integration.config.ts`
- `backend/tests/test_print_metadata_safe.py`

Documentation: this append only in `frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md`. Reused stylesheet/shared components unchanged. Existing backend application/business services, schema/migrations, QR code, template/publication prerequisites, physical QA records, payments, dispatch, checkout/auth/deployment configuration and unrelated working-tree changes preserved.

## Completion limits / next action

**LIVE ACCEPTANCE BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** This task does not reconnect unverified remote targets or claim previously missing services/records were provisioned. Authorized future acceptance needs an identified isolated non-production runtime, installed metadata schema/grants/RLS, valid auth/live Operations+MFA, existing server AEAD keys for349 cursors, actual permitted print-job/artifact-metadata records, and current admin/backend Origins. It must not generate production jobs/pairs, publish templates or seed physical QA solely to obtain test data. Actual PostgreSQL query plans/count execution budgets/RLS and deployed browser acceptance remain unverified.

Read-only source/UI implementation is complete for the four admitted metadata operations. No production print/render/artwork/inspection/dispatch workflow is implemented or claimed. Detail timestamps/template key/version/physical inspection evidence absent from contracts stay unavailable; unbounded233 history and bounded metadata/schema failures are honest contract limits. Counts are capped, not global exact totals. No demo fallback or mock inspection mutation remains in connected Print Jobs pages; unrelated demos/legacy code retain prior state and are not integration authorization.

Recommended next action is safe non-production acceptance of implemented modules once provisioned. A separately requested authorized user-directory metadata phase remains a candidate for later verification. **Do not start another module in this task.**


---

# Phase 7 — Module 6: Shipments Management (2026-10-23)

**Status: safe shipment-items source integration and isolated verification complete; shipment listing/detail discovery BLOCKED; live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** This is a deliberately limited read-only module, not completion of shipment operations or live acceptance.

## Previous phases and authorization baseline

Read the corrected inventory, frontend mapping, plan/strict allowlist, earlier progress entries, approved API/technical/database/security documents and fulfillment requirements against actual routes and services. The corrected default-deny policy remains authoritative. No denied operation is reclassified merely because its name says typed or independent.

Phase 3 source/synthetic preview verification exists, but provisioned non-production runtime, enrolled template authority/assets and real physical QA acceptance evidence remain unconfirmed. Phase 4's original API-080/081 remains quarantined; the later separately authorized independent order-metadata implementation in this tracker does not authorize the old endpoints. Phase 5 implements the documented restricted payment reads; reconciliation stays quarantined. Phase 6 implements four metadata-only print reads with isolated verification, not production rendering, QA, artifact access or live acceptance. None of those endpoints is called to populate this Shipments view.

## Endpoint decisions / exact Phase 7 allowlist

| Endpoint | Decision | Actual dependencies / reason | Connected frontend behavior |
|---|---|---|---|
| GET `/api/v1/admin/shipments/{shipment_id}/items` (`typed-shipment-items`) | **ELIGIBLE; sole Phase 7 upstream business read** | Registered fulfillment router under `/api/v1`; `require_staff(context,"operations")`, `rows`, one shipments/orders commerce-model SELECT and one shipment_items SELECT. No pair, QA, ownership, eligibility, allocation, artifact or lifecycle helper is executed. | Explicit known-UUID lookup, direct UUID detail, refresh, four item metadata fields only. |
| GET `/api/v1/admin/shipments` (API-246) | **QUARANTINED; NOT INTEGRATED** | `fulfillment_queries.shipments`, `SHIP_COUNTS` reads shipment_pairs and invokes `sr_fulfillment_eligible`; optional requires_review filtering also invokes that function. Hiding fields or omitting the filter does not make the query safe. | No list load, status/date/carrier filtering, sorting, pagination, counters or background prefetch. Explicit unavailable state. |
| GET `/api/v1/admin/shipments/{shipment_id}` | **EXCLUDED from this phase** | Existing generic detail includes pair-membership inspection; not an alternative to the items projection. | No generic detail request. `/admin/shipments/[shipmentId]` uses only the allowed items endpoint. |
| API-080 general orders, generic order detail/QR allocation, QR inventory/batches/support independent-QR, pair generation/QA/export/assignment/reservation/ownership/lifecycle APIs | **Existing exclusions/quarantines preserved** | Prior corrected audit and source decisions remain in force. | No lookup, navigation prefetch or follow-up data requests from these connected screens. |
| Shipment creation, packing/QA confirmation, dispatch, courier booking/labels, delivery/cancel mutations; print enqueue/artwork/reprint/QA | **OUT OF SCOPE / NOT INTEGRATED** | Mixed-purpose fulfillment and prohibited workflows are not made safe by frontend labels or metadata-only display. | No mutation buttons, handlers, setup fixtures or tests. |

One eligible upstream business operation is connected. Authentication's existing verified session/staff reads remain supporting infrastructure, not new shipment APIs. API-246 stays quarantined in the existing corrected reports; this entry does not change the historical inventory totals or fabricate an API number for the named items operation.

Source evidence: `backend/app/api/v1/fulfillment.py` (`rows`, `shipment_items`); `backend/app/api/v1/fulfillment_queries.py` (`SHIP_COUNTS`, shipments and generic detail); router registration in `backend/app/main.py`; shipments/orders RLS in migration 0003 and shipment_items schema/RLS in `0042_typed_print_fulfillment.sql`. Read-only source inspection only. The shipment_items logical_item_id foreign key points to an allocation table, but a SELECT does not execute insert/update foreign-key checks or packing triggers, nor does this handler query the referenced table. Its item references and recorded packing metadata are already authorized by this explicit read contract. RLS checks staff/MFA and order authorization without calling fulfillment eligibility. No authorization or backend business rule was bypassed or changed.

## Verified contract and UI limits

Request: UUID path parameter, GET, no query/filter/cursor/body. Response is exactly:

```ts
{
  commerce_model: "single_qr" | "legacy_pair";
  items: Array<{
    logical_item_id: string; // UUID
    print_job_id: string;   // UUID reference only
    packed_qa_confirmed: boolean;
    packed_at: string | null; // timezone timestamp
  }>;
}
```

Backend requires current Operations staff authorization after normal verified-email/live-session/MFA checks. Missing shipment returns404. Invalid UUID returns422; auth errors401/403; unexpected provider failures become a redacted unavailable state. No implicit superadmin/security_admin/finance/support inheritance into Operations.

The existing Shipments entrypoint now displays **Shipment Item Metadata**, retaining AdminPage/AdminShell/AdminCard/AdminPageHeader/AdminEmptyState/AdminStatusBadge and the existing shipment stylesheet. Initial `/admin/shipments` rendering sends no shipment request. **View Shipment Items** submits an already-known backend UUID. `/admin/shipments/[shipmentId]` loads that UUID through the same narrow client. Invalid IDs fail before upstream dispatch. **Refresh Shipment Items** rereads the successfully shown UUID; it does not mutate packing state. Abort/sequence handling prevents an earlier lookup overwriting a later one. Demo role preview is not authorization.

Rows show logical item reference, print-job reference, recorded packing confirmation and nullable packed_at. These are not active QA controls, QR identities, physical quantity counts or proof of dispatch/delivery/readiness. Print-job references are plain text, not artwork links. Empty single_qr results say no item metadata returned without inferring shipment state/counts. Legacy-model empty results explicitly say logical metadata is not a complete membership view, with no pair-inspection fallback.

Shipment state, related order, carrier, tracking, customer addresses/contact data, created/updated/dispatch/delivery times and activity history are absent from the safe response and remain unavailable. No global search, sort, status/date/carrier filter, cursor, list total, fake tracking URL or invented event history. Endpoint has no pagination; a 1000-item/512KiB client/BFF cap fails closed instead of silently truncating a response or claiming completeness.

## Security and excluded-request protections

New fixed relay `/admin/shipments/items-api?shipment_id=<uuid>` uses existing verifiedSession/staffState, actual Operations, MFA and fulfillment.manage; rechecks current staff access after the response. Page guard uses the same existing capability and Operations restriction. Backend authorization remains authoritative.

Only GET to the fixed validated backend origin and the one UUID/items path is possible. Unknown/repeated query parameters, unsupported methods, bodies and transfer/content encoding framing are rejected. Cross-site and mismatched Origin requests are rejected. Server-only Bearer, private/no-store, redirect rejection, ten-second upstream timeout,512KiB streamed UTF8/JSON response limit, exact response shape, bounded fields, duplicate item rejection and fixed redacted errors. Unexpected private/customer/pair fields reject the entire response rather than pass through. No credentials in browser storage or diagnostic/raw backend dumps. No mutations means no new idempotency, If-Match or CSRF mutation flow; existing controls elsewhere remain unchanged.

Connected Shipments pages no longer mount ShipmentDiscovery or the legacy broad fulfillment relay, including `?view=live`. No legacy console, hidden component, global API initialization, order/print lookup or background polling is introduced. Existing old broad relay/discovery code remains outside this task and is not newly authorized or exercised. The unrelated Ready to Ship demo previously shared AdminShipments; its original component was preserved verbatim in `admin-shipments-demo.tsx`, with only that page's import redirected to keep its existing behavior. Its existing explicit legacy branch remains unchanged; Phase 7 does not certify that unrelated route. Connected Shipments screens never import the demo or mock service.

## Files changed / reuse

Updated existing screens/components:

- `frontend/components/admin-shipments.tsx`
- `frontend/app/admin/shipments/page.tsx`
- `frontend/app/admin/shipments/[shipmentId]/page.tsx`
- `frontend/app/admin/ready-to-ship/page.tsx` — shared demo import relocation only, no behavior integration.

New application files:

- `frontend/lib/admin-shipment-items-contract.ts`
- `frontend/lib/admin-shipment-items-client.ts`
- `frontend/lib/api/shipment-items-relay.ts`
- `frontend/app/admin/shipments/items-api/route.ts`
- `frontend/components/admin-shipments-demo.tsx` — preserved original shared demo for the unrelated Ready to Ship page.

New isolated checks:

- `frontend/scripts/test-shipment-items.cjs`
- `frontend/tests/shipment-items-fixture.cjs`
- `frontend/tests/shipment-items.spec.ts`
- `frontend/playwright.shipment-items.config.ts`
- `backend/tests/test_shipment_items_safe.py`

Documentation: this tracker append. Existing backend application code, auth/config, services, SQL/schema/migrations, QR APIs, packing/dispatch, courier, customer checkout and deployment settings were not changed in this phase. Pre-existing working-tree changes were preserved.

## Tests actually executed

Inspected the selected helpers/setup/teardown before running. No broad fulfillment/legacy suite, database setup, pair fixture, shipment creation or production service was used.

1. `node frontend/scripts/test-shipment-items.cjs`: **30 passed**,12 allowlisted in-memory upstream GETs, zero excluded requests. Actual source relay with synthetic auth: roles/session/MFA, fixed path/query/method/Origin, invalid UUID without dispatch, repeated/unsupported parameters, empty/legacy metadata, malformed/sensitive response rejection, errors, final-role revocation and source-import exclusions.
2. `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_shipment_items_safe.py -q`: **10 passed** after correcting the test SQL result double to support iteration. Actual existing route/auth/JWT handlers, guarded known-items-only ASGI GETs, standalone in-memory SQL double. Tests Operations/mixed roles vs denied roles, session/email/MFA, exact metadata/null timestamp, empty/legacy and404. Guard rejects pair/allocation/eligibility/QA/artifact/locking/business-write SQL. This is not PostgreSQL/RLS/live database proof. No backend business code was changed to satisfy tests.
3. From frontend: `npx playwright test --config=playwright.shipment-items.config.ts`: **17 passed**. Current source component/AdminShell/client/relay, isolated synthetic auth/in-memory upstream, all browser traffic intercepted and allowlisted. No list request on mount, explicit lookup/detail/refresh, four fields, empty/legacy semantics, invalid IDs without dispatch,401/403/404/503, malformed/private fields and absent mutation controls. Responsive no-full-page-overflow and keyboard checks at **1366×768,1440×900,768×1024,375×667**. Screenshots `test-results/shipment-items/shipment-items-<width>.png`;375px screenshot visually inspected. Existing shared CSS artifact plus current scoped stylesheet, not a claim of a new deployed Next build.
4. `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed**, including formatted application source.
5. Focused Ruff and Ruff format checks on `backend/tests/test_shipment_items_safe.py`: **passed**.

No excluded endpoint was called, including for failure tests, setup or rendering. Source-reading a prohibited query is not executing it. Shipment-list/filter/cursor tests are deliberately unavailable because API-246 was stopped, not tested despite its quarantine. No actual shipping/PDF/physical QA records were generated or approved. Browser synthetic packing timestamps exercise display only, never create acceptance evidence.

## Environment findings / live acceptance prerequisites

Rechecked local configuration without printing values. `backend/.env` exists with prefixed database/migration configuration; those remote targets are unverified and were not contacted. `frontend/.env.local` exists but required SAFERETURN_API_ORIGIN, SAFERETURN_WEB_ORIGIN, SAFERETURN_SUPABASE_URL and SAFERETURN_SUPABASE_PUBLISHABLE_KEY are absent. No TCP listeners at127.0.0.1 ports3000,8000,5432 during the check; that is not proof about remote service operation. No approved named non-production environment or enrolled acceptance records have been confirmed. No migrations, workers, auth setup, remote HTTP or database connections were attempted. Earlier phase environment/authority/physical QA blockers are not resolved by these isolated checks.

**LIVE ACCEPTANCE BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** Authorized acceptance requires:

- Explicitly identified isolated non-production admin/backend/auth/database environment with approved origins/server configuration and operational services.
- Existing installed shipments/orders/shipment_items schema, grants and RLS; independent review of actual PostgreSQL authorization/query behavior.
- Enrolled authenticated current Operations user, verified email/live session and MFA, plus denied-role/session cases.
- Approved already-existing shipment UUID and safe logical-item metadata records available without creating or inspecting QR pairs or running fulfillment operations to obtain data.
- Deployed browser acceptance of this one safe read, response limits, privacy/error behavior and required viewports. Do not invoke API-246 or generic detail as a test prerequisite.

No missing service, authority, physical QA or credential configuration is assumed or fabricated. No secrets appear in this report.

## Remaining blockers / recommendation

API-246/global shipment listing and generic detail remain blocked by prohibited pair dependencies. A future independently authorized metadata-only shipment list/detail backend contract would be needed for state/order/carrier/tracking/history discovery; no backend workaround or new endpoint was implemented here. Missing metadata cannot be inferred from packing flags. Very large unpaged item responses fail closed. Other modules' demo/legacy state remains outside this integration, with no demo fallback on connected Shipments screens.

Recommended next action: provision authorized non-production acceptance for the completed safe modules. A separately requested authorized user-directory metadata phase is a later candidate requiring its own call-chain audit. **No next module was started.**


---

# Phase 8 — Module 7: Users & Account Governance (2026-10-23)

**Status: three directory reads implemented in the existing admin screens and verified in isolation. Suspension, restoration and recovery escalation remain BLOCKED — APPROVED CASE/EXECUTOR/CUSTODY CONTEXT NOT AVAILABLE THROUGH A VERIFIED SAFE WORKFLOW. Live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** No account governance mutation was connected or executed.

## Verified preceding status and scope

Read the corrected API inventory/mapping/plan/strict first-phase allowlist and exclusions, previous tracker entries, approved API contract, technical/database/security requirements and current source. The original strict14 Products allowlist is historical Phase1 authorization, not a prefix grant for later modules. The corrected reports retain directory and approved account governance as eligible future candidates; this explicitly requested phase admits only the exact reads below after checking their actual dependencies. No contradictory/missing corrected allowlist was found. Historical162-operation/70-denied totals are not recalculated or reclassified here.

- Phase2: Products source integration and isolated tests exist; no live acceptance established.
- Phase3: template source/synthetic preview checks exist; real enrollment/assets/physical QA and non-production runtime acceptance remain blocked. No publication.
- Phase4: API080/081 remain quarantined for pair-dependent fulfillment inspection. Separately authorized independent order-metadata source integration exists; no authorization to use the old API.
- Phase5: restricted payment reads implemented; pair-dependent reconciliation remains quarantined.
- Phase6: four metadata-only print reads implemented; rendering/artwork/QA/dispatch and live acceptance remain outside that result.
- Phase7: safe known-shipment items read implemented; API246 list/generic shipment detail remain blocked for pair inspection. Live acceptance remains blocked.

None of those modules is called or changed to supply account context in Phase8.

## Per-endpoint decision / strict Phase 8 allowlist

| Candidate | Decision | Verified implementation and dependencies |
|---|---|---|
| GET `/api/v1/admin/users` API346 | **CONNECTED** | `staff_directory.users` → guard/security_admin → read → `sr_staff_directory(mode=list)` → auth.users minimal retained-registration projection, role/session/MFA helper; final live authorization recheck. No profile, QR/pair, ownership, allocation or fulfillment read. |
| GET `/api/v1/admin/users/count` API348 | **CONNECTED** | Same helper in count mode; exact filters and capped count, no page-derived total, no QR dependency. Registered before UUID detail. |
| GET `/api/v1/admin/users/{user_id}?include=account_security` API347 | **CONNECTED** | Directory detail plus the approved explicit account-security opt-in → `sr_staff_account_state` → auth.users/account_security_state. Missing state dependency returns STATE_UNAVAILABLE; no state inference or broader lookup. |
| POST `/api/v1/admin/users/{user_id}/suspensions` API320 | **ELIGIBLE source chain; BLOCKED prerequisite; NOT CONNECTED** | `execute` → guard/recent → sr_lifecycle_context/apply/save_receipt. Requires genuine case binding, separate approved security custodian, exact executor/action/reason/revision, Origin and idempotency. Safe context not supplied by directory. |
| POST `/api/v1/admin/users/{user_id}/restorations` API321 | **ELIGIBLE source chain; BLOCKED prerequisite; NOT CONNECTED** | Same independent account-security chain. No automatic restoration/revival of roles, grants, sessions or QR ownership. Same missing approved context. |
| POST `/api/v1/admin/users/{user_id}/recovery-escalations` API322 | **ELIGIBLE source chain; BLOCKED prerequisite; NOT CONNECTED** | Same chain writes referral/event/receipt, not password/MFA recovery, credential issuance, provider administration or QR lifecycle. Same missing approved context. |
| Generic support detail/create/change; pair/QR context, customer profile/ownership, general orders and all previously denied endpoints | **EXCLUDED / existing quarantine preserved** | No safe alternate case-binding approval workflow identified. Do not discover cases through quarantined support operations or synthesize approvals. |

Only the three GET operations are in the new source UI request budget, plus existing authentication/session/staff bootstrap infrastructure. New `/admin/users/directory-api` exposes list/detail/count selections only; POST/PUT/PATCH/DELETE/HEAD/OPTIONS reject without upstream dispatch. Existing broad users relay/legacy console remain untouched and unmounted from normal Users routes, including `?view=live`; they are not an implementation shortcut or new authorization.

Evidence inspected: router install calls in `backend/app/main.py`; `backend/app/api/v1/staff_directory.py`, `account_lifecycle.py`, `auth.py`; `0029_staff_directory.sql`, reachable account/session/custodian/lifecycle helpers in `0030_account_lifecycle.sql`, and `0031_staff_account_state.sql`; approved Doc04 Task2.3C/2.3D/5.7C and Doc07 account governance/security sections. Source migrations were read, never applied or executed. Other unrelated helper definitions in0030 do not become reachable simply because they share a migration file.

## Actual metadata, filters, pagination and precision

List item is exactly `{user_id, registered_at, email_verified, provider_access}`. User ID is UUID, registration time UTC timestamp, verification boolean, provider_access `banned|not_banned`. No name, contact (including masked email), phone, address, medical/emergency profile, QR count, last login, roles, factors, credentials, private case data or provider metadata. `not_banned` does not establish a valid session, MFA enrollment or active application state.

List returns `{as_of,items,next_cursor}`. Backend supports exact user_id, email_verified=true|false and provider_access=banned|not_banned; these are the only UI filters. No registration-period, full-name, email-address, phone, fuzzy search or custom sort API exists. UI requests20 records, backend permits1–100. Fixed registration descending/UUID descending tie order. Opaque max1024-character base64url keyset cursor binds normalized filters; pagination is not an immutable snapshot. Applied filters persist across Next/Previous; changed filters and refresh reset cursor history. Draft filter edits do not alter the applied cursor query. Browser does not filter a server page and claim global results.

Count returns `{as_of,definition,filters,count:{value,is_exact}}`, definition `retained_nonanonymous_auth_registrations_v1`. Population: retained auth registrations excluding deleted/anonymous, including banned/unverified accounts independently of profile/session existence.0–999 are exact;1000 is **1000+ (lower bound)**, including actual1000. Count uses applied filters and no cursor; no summing/estimating from page size. Separate count/list timestamps are displayed; independent requests are not one shared snapshot. Count failure shows unavailable while a valid list may remain. Auth denial clears both results.

Detail uses the authoritative returned minimal user and opt-in application state. Ready state supplies active|suspended,revision,as_of,commands_available; unavailable state supplies STATE_UNAVAILABLE. State/revision is displayed only when ready. Never infer application suspension from provider access, counts or a historical operation receipt. Direct invalid IDs fail locally before dispatch;404 stays unavailable, never synthetic. Refresh rereads the same backend UUID.

## Governance security gate / precise blocker

All three operations have pair-free reachable source behavior, but **source eligibility is not enough to enable them**. Existing commands_available means lifecycle feature/origin configured; it does not prove a case binding or approval exists. Directory list/detail/count expose no approved case IDs, subject binding, executor authorization or custodian approval. No confirmed external approved case context was supplied. Generic support detail/change/create are quarantined, and the approved directory contract explicitly does not infer an authorized subject from case opener/order/pair references. No new endpoint, direct DB access, operator provisioning or fake manual case confirmation was added.

The detail screen explains prerequisites in an unavailable governance section. No enabled Suspend/Restore/Escalate button, free-form case submission, fake confirmation, reason selector, guessed revision or mutation transport is introduced. A ready revision is usable account metadata, not sufficient authorization for any mutation. All three actions remain blocked even when synthetic test responses set commands_available=true.

Verified future command requirements (not implemented here):

- Explicit current security_admin, verified/live session and genuine signed+provider AAL2. Recognized signed recent authentication within300seconds; iat alone is insufficient. Superadmin alone cannot bypass this.
- Lifecycle opt-in and exact configured Origin; closed DTO `{case_id:UUID,expected_revision:1..2147483646,reason_code,confirmed:true}`. No If-Match substitute; expected_revision is in the body.
- Suspend reasons: suspected_compromise|abuse_review|security_review. Restore: review_cleared. Recovery: factor_loss|account_access_review. Recovery action is recovery_escalated, response202/status=referred; suspend/restore200 include fresh_sign_in_required=true.
- Existing open/investigating case, non-revoked case-to-subject binding, unexpired action approval bound to executor/subject/action/reason/revision, separate currently eligible security custodian/approver; no self-target/self-approval, last-custodian protection.
- Scoped Idempotency-Key8–160 permitted characters, encrypted replay receipt, final authority recheck, atomic account state/epoch/event/approval consumption and safe audit. Historical receipt is not current state. Fresh backend reread after confirmed success; no blind retries on timeout, same-key recovery only under the actual approved contract.
- Errors include missing key400,401/403 and REAUTH_REQUIRED,404,409 contention/invalid state/last custodian/key reuse,412 stale version,422 validation and503 disabled/dependency/crypto/DB failures. Future UI must preserve legitimate input on conflicts without asserting success or fabricating context.

Service apply writes account_security_state/invalidation epoch, account_security_events, approval consumption and audit; save_receipt stores encrypted result. It does not query pair/QR tables, mutate ownership/activation, run a QR worker or perform provider password/factor administration. Account/session denial is legitimate application governance, not a QR ownership rewrite. No such function was executed by this task.

## UI/security architecture and files

Existing Users List and User Details components were updated rather than mounting the old UserDirectory console. Reused AdminPage/AdminNotice, AdminShell/current authenticatedRoles, existing users.manage capability, AdminCard/AdminPageContainer/AdminPageHeader/AdminEmptyState/AdminStatusBadge and existing scoped stylesheet. Demo role preview never grants Security Admin authority. No mock user service or localStorage path is imported by connected pages. Minimal metadata replaces private synthetic columns rather than inventing missing API fields.

Controls: exact user UUID, email-verification/provider-access selectors, Apply/Clear filters, Previous/Next, View Details links with prefetch=false, Refresh Users/Refresh User and capped count card. User detail is a page, not an invented history/dialog. Governance explanation is informational with no request control. Read effects abort on subject/filter/unmount/visibility changes and use generation checks to reject stale results. Hidden views clear results; returning visible rereads.

New closed server relay retains Bearer server-side; verifiedSession/staffState entry/final checks require actual security_admin, MFA and users.manage. Backend independently checks JWT/live account/email/session/MFA and explicit role before/following projection. GET-only fixed validated origin and three exact path shapes, no generic URL forwarding. Closed query keys/UUID/filter/limit/cursor checks, no body/encoding/transfer framing, same-origin/fetch-site checks, redirect rejection,10-second upstream timeout,64KiB UTF8/JSON success limit and4KiB error limit, closed DTO validation, private/no-store/nosniff/no-referrer. Unexpected private fields cause contract failure. Client reads additionally have a15-second abort timeout; no polling/background unrelated endpoint or browser token persistence. Existing customer/admin deployment, cookies, auth rules and all mutation concurrency/idempotency requirements are unchanged.

Updated:

- `frontend/components/admin-users.tsx`
- `frontend/components/admin-user-details.tsx`
- `frontend/components/admin-users.module.css` — scoped metadata detail layout only.
- `frontend/app/admin/users/page.tsx`
- `frontend/app/admin/users/[userId]/page.tsx`

Added:

- `frontend/lib/admin-user-directory-client.ts`
- `frontend/lib/api/user-directory-read-relay.ts`
- `frontend/app/admin/users/directory-api/route.ts`
- `frontend/scripts/test-user-directory-integration.cjs`
- `frontend/tests/user-directory-fixture.cjs`
- `frontend/tests/user-directory-integration.spec.ts`
- `frontend/playwright.user-directory-integration.config.ts`
- `backend/tests/test_user_directory_safe.py`

Reused closed read parsers in existing `frontend/lib/users-contract.ts` without changing its governance behavior. Old users-relay/UserDirectory and shared demo service remain untouched, unmounted from these Users entrypoints. No backend application/service/auth/schema/migration/config, account provisioner, previous module or independent deployment setting changed. Existing unrelated working-tree edits preserved. This tracker append is the documentation change.

## Verification actually executed

Inspected selected fixtures/helpers/source bundler/setup/teardown. Tests use synthetic HTTP/auth and a standalone SQL double, no real customer account, DB migration, support case, independent approval or QR fixture. No broad account/legacy suite was run.

1. `node frontend/scripts/test-user-directory-integration.cjs`: **44 relay checks passed**,15 strictly allowlisted in-memory upstream GETs, zero excluded requests. Actual closed relay validates roles/session/MFA/final revocation, list/detail/count, filters/UUIDs/limit/cursor/repeated keys, rejects all mutation kinds/methods before upstream, Origin mismatch, malformed/private projections, status failures,1000+ and unavailable state; static connected-source checks reject legacy console/mock/storage/profile paths. No governance endpoint was invoked even to test a denial.
2. `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_user_directory_safe.py -q`: **10 passed**. Actual directory route/auth/JWT handlers, standalone safe SQL result double, guarded ASGI GET list/count/known detail only. Operations/support/finance/superadmin denied; security_admin/mixed role allowed; live session/email/MFA, minimal metadata, authoritative revision, disabled commands flag, empty404 and unsupported filter/ID/query validation. SQL guard rejects pair/QR/allocation/eligibility/QA/artifact/lifecycle business calls and writes. Not actual PostgreSQL RLS/managed Auth/helper predicate/count/performance proof.
3. From frontend: `node node_modules/@playwright/test/cli.js test --config=playwright.user-directory-integration.config.ts`: **19 passed**. Current AdminUsers/AdminUserDetails/AdminShell/client/relay source with synthetic auth and in-memory upstream; all network intercepted/allowlisted. List/count/detail links, applied filters across cursors/reset/refresh, exact UUID/verification/clear, capped/unavailable counts, empty records, detail revision/refresh, unavailable state, governance unavailable despite commands flag, invalid IDs without dispatch,401/403/404/503 and malformed/private projection rejection. Responsive/keyboard/no-full-page-horizontal-overflow at **1366×768,1440×900,768×1024,375×667** plus mobile detail. Screenshots `test-results/user-directory-integration/users-<width>.png`;375px screenshot visually inspected. Existing shared CSS artifact plus current scoped stylesheet, not a deployed Next build claim.
4. `node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false --project frontend/tsconfig.json`: **passed** after correcting an implicit-any annotation in the new browser test. Focused Ruff and Ruff format checks on `backend/tests/test_user_directory_safe.py`: **passed** after unused fixture-variable cleanup. Final application source was formatted; the19-browser-test suite passed again after the client timeout change.

Governance stale-revision/invalid-case/case-user/recent-auth/confirmation/reason/idempotency mutations were **not executed**, because those operations remain blocked. HTTP method rejection at the new read relay is not a test call to the governance backend. No fake approval/physical QA/authority was generated. No production render sweep, excluded API, actual database/provider integration or real account mutation was performed.

## Environment / acceptance status and exact prerequisites

Rechecked existing local config without exposing values. `backend/.env` has database/migration/auth-provider settings whose targets remain unverified; they were not contacted. staff_directory_enabled, account_lifecycle_enabled and lifecycle web origin environment settings are absent (feature defaults false). `frontend/.env.local` exists but required SAFERETURN_API_ORIGIN, SAFERETURN_WEB_ORIGIN, SAFERETURN_SUPABASE_URL and SAFERETURN_SUPABASE_PUBLISHABLE_KEY are absent. No TCP listeners at127.0.0.1:3000/8000/5432 at inspection. This does not establish the state or classification of remote services. No provisioned approved named non-production environment or approved account-governance records have been confirmed.

**Live acceptance BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** Needs an explicitly identified isolated admin/backend/auth/database environment, operational services, approved independent Origins/configuration, installed source-matching narrow helper/schema/grants/RLS and safely enrolled Security Admin live MFA user. Use approved retained-user metadata fixtures without creating QR pairs. Directory feature must be enabled through authorized environment setup; actual PostgreSQL ownership/ACL/RLS/managed columns/queries/count limits/concurrency and deployed session/SSR/privacy/accessibility remain acceptance work. No config was enabled here.

Governance additionally needs an approved safe way to supply genuine case-to-user binding and independently controlled executor/action/reason/revision approval, current independent human custody evidence and recovery drill; these cannot be inferred from a role or hand-entered UUID. Feature/origin/AEAD configuration, recent signed authentication, audit/rollback/concurrency/idempotency testing and safe disposable subject records must be verified before a future authorized command integration. Do not create a support case through quarantined APIs or provision authority merely to unblock acceptance.

## Remaining scope and next action

Safe list/count/details are source-integrated, not live accepted. Suspension/restoration/recovery escalation are **NOT IMPLEMENTED in these screens**, with explicit prerequisite blocker. Contact/profile/ownership columns and unsupported date/name/email/phone search remain unavailable; no demo fallback or mock account-status mutation remains on connected Users routes. Other legacy/demo features remain separate and unverified.

Recommended next step: provision authorized non-production directory acceptance and review a safe approved case-context handoff before enabling governance. A separately requested Notifications metadata phase is only a future candidate requiring its own per-route/worker audit. **No other module was started.**
# Phase 9 / Module 8 — Support Cases & Financial Case Review (2026-10-24)

**Status: BLOCKED at the mandatory endpoint eligibility gate. Zero APIs connected, zero screens changed, zero controls added.** The corrected allowlist/exclusion records exist and consistently quarantine all five candidates. The instruction to stop when this module cannot safely be integrated applies; no frontend-only payload restriction or custom relay can authorize these mixed backend operations.

## Verification and preceding phases

Read the corrected inventory, mapping, integration plan and prior progress; inspected current route registration, support handlers, financial guards/context calls, relevant SQL definitions and support frontend entry points. Consulted approved API contract support sections and API-323/324 governance addendum, and relevant product/design/security requirements. Existing historical approvals do not override the current task's absolute pair exclusion.

Phases 2–8 are not assumed complete: Products and Templates source integrations exist, but live acceptance remains outstanding; Phase 3 additionally requires genuine enrolled assets, physical QA, publisher authority and runtime prerequisites. Phase 4 general API-080/081 stays quarantined; separately approved independent order metadata exists. Phase 5 restricted payment reads, Phase 6 print metadata reads, Phase 7 known-shipment item reads and Phase 8 user-directory reads exist. Reconciliation, general shipment discovery and account governance mutations retain their recorded blockers. Earlier test results are historical and were not rerun here. No newly approved non-production environment or genuine acceptance prerequisites were supplied or established; no remote configuration was probed.

## Exact endpoint decisions — no Phase 9 request allowlist

| API | Registered candidate | Decision and source evidence |
|---|---|---|
| API-097 | GET `/api/v1/admin/support-cases` | **QUARANTINED.** `support_cases.cases` accepts `case_id` on the list route; there is no dedicated detail route. Assigned detail invokes `sr_support_context`, reading pair-linked order/hold context. A list-only query is not a separately admitted endpoint under the corrected audit. |
| API-098 | POST `/api/v1/admin/support-cases` | **QUARANTINED.** `create_case` calls `sr_support_create`, validating `tag_pairs`/`order_pair_units`; support insertion also reaches retention admission. Omitting pair fields does not establish a permitted endpoint. |
| API-099 | PATCH `/api/v1/admin/support-cases/{case_id}` | **QUARANTINED.** `update_case` calls `sr_support_change`; the 0035 wrapper delegates to `sr_support_change_v34`. Existing implementation includes pair/order locks and context checks. Claiming, notes, priority and status edits share this operation. |
| API-324 | GET `/api/v1/admin/support-cases/{case_id}/financial-review` | **QUARANTINED, including read-only use.** `financial_disputes.review` calls `load_context` → `sr_financial_case_context`; current 0030 definition locks `order_pair_units` and `tag_pairs`. A minimized response does not remove those dependencies. |
| API-323 | POST `/api/v1/admin/support-cases/{case_id}/financial-decisions` | **QUARANTINED.** Loads the same context before replay and calls `sr_financial_case_apply`, which also uses financial case context. No decision type is admitted as a workaround. |

Registration evidence: `backend/app/main.py` includes the support router under `/api/v1` and installs financial disputes. Dependencies inspected read-only: `backend/app/api/v1/support_cases.py`, `financial_disputes.py`; migration sources `0021_support_case_console.py`, `0025_financial_disputes.sql`, `0030_account_lifecycle.sql`, `0035_public_abuse_intake.sql`. Corrected inventory entries API-097/098/099/323/324 and integration-plan indirect-dependency table retain the same classifications. No migration/helper was executed.

## Contract/security findings retained as evidence only

Support handlers require Support authorization, not frontend preview authority. Actual filters are case_id, case_type, status, priority and queue, with limit/cursor and detail history event_limit/before_revision. No global text/date search is authorized. Creation DTO is case_type, priority, optional pair_id/order_id, description (4–2000). Update requires expected_revision, claim|update action, strict confirmed=true and optional status/priority/note (4–2000); claim cannot carry edits. Only unassigned/current-agent scope is available; revision, state/ownership, encrypted receipt/idempotency and audit rules remain backend responsibilities. No unrestricted employee assignment or invented fields/endpoints were added.

Financial guard requires Finance and enabled financial review. Writes additionally require exactly the configured Origin and recent authentication. Approved contract requires current case/order revisions, case-bound authority, explicit confirmation and scoped idempotency; confirm/resolve decisions require genuine bound evidence. Supported decisions are investigate, confirm_dispute, resolve_no_change and escalate, not refunds or generic payment verification. Existing session/email/MFA checks remain mandatory. These safeguards do not make the pair-dependent call chain eligible. No role, Origin, CSRF, auth configuration, business rule or revision control was changed.

## Frontend status and pre-existing invocation risk

Normal `/admin/support` currently renders the synthetic `AdminSupportCases`; its mock IDs/notes/actions remain demo-only. The existing `?view=live` branch mounts `SupportAdmin`, UUID detail URLs select that legacy component, and `/admin/support/new` uses its intake mode. Existing `/admin/support/api` relays the quarantined generic support operations. These pre-existing paths are **not verified safe or newly authorized by Phase 9**. They were inspected as source only, never mounted, prefetched, rendered or requested. The mandatory stop gate leaves application code unchanged; existing legacy reachability remains a blocker requiring a separately scoped containment decision.

List/filter/pagination, intake, direct details, claiming, internal note persistence and status transitions: **not integrated in Phase 9**. Financial review tab and decision form: **not implemented**. No fabricated activity/history, customer messages, financial approval, backend success, mock fallback or account recovery was added. No synthetic audit event is presented as a backend event.

## Checks, files and remaining work

- Tests executed: **none**. Static source/document inspection only. No HTTP/ASGI/browser test, fixture/setup/teardown, live case mutation, financial decision, service, worker or broad build ran. No runtime forbidden-route denylist assertion or responsive/keyboard acceptance is claimed: implementation stopped before a runnable integration existed.
- QR-pair exclusion: zero API requests issued; no pair service/helper executed or modified. Pair-related migration source was read only to establish the blocker.
- Files changed for this phase: **only `frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md`**, adding this record; all existing user changes remain intact.
- Live acceptance: **BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED**, in addition to the endpoint safety gate. No evidence establishes that the prior environment finding has changed.
- Required next action: separately approve/design an independently safe support metadata/intake/update and financial-review contract, then verify its full backend chain and explicitly revise the corrected allowlist before implementation. Existing endpoints must not be bypassed or their business logic weakened. Resolve legacy invocation containment and provision authorized non-production acceptance separately.
- Recommended next integration phase: no automatic advance. Resolve Phase 9's contract gate and prior acceptance blockers first. No subsequent module started.

## Phase 9 blocker resolution — architecture proposal only (2026-10-24)

**PROPOSED / NOT IMPLEMENTED.** Added `docs/PHASE_9_SUPPORT_DECOUPLING_PROPOSAL.md` (existing docs directory; backend/docs does not exist). No endpoint, frontend, business rule, migration, grant, configuration, role or existing quarantine changed. All five API-097/098/099/323/324 operations remain quarantined; the proposal is not an allowlist amendment or implementation authorization.

Deeper source tracing distinguishes incidental shared enrichment from essential retention/ownership/financial consistency. API-097's assigned detail invokes pair-linked context, while a separate case metadata projection can avoid it. API-099 locks orders/pairs even for claim, and invokes context for update; new narrow unrelated-case commands are only conditional candidates. Creation and status-column updates also reach `sr_retention_dispute_admission`: its helper executes an order_pair_units query even with null pair input. Consequently null frontend references alone cannot make intake/status independent. Financial review history calls the protected financial context again, not just the top-level review; changing only the initial context loader would be insufficient.

Proposed new paths under `/api/v1`, all **NOT IMPLEMENTED**, IDs unassigned:

- GET `/admin/support-case-metadata` and GET `/admin/support-case-metadata/{case_id}`: bounded existing-queue metadata without context enrichment or plaintext.
- GET `/admin/support-case-metadata/{case_id}/history`: assigned-only event metadata, no fabricated history or note contents.
- GET `/admin/support-case-metadata/{case_id}/content`: conditional modern encrypted description/notes under restricted ordinary scope and content-policy approval.
- POST `/admin/support-case-metadata/{case_id}/claim`, POST `.../notes`, PATCH `.../priority`: conditional existing-record commands, subject to scope/linkage/provisioning race proof; no status/reference column updates or old helper reuse.
- POST `/admin/support-case-intakes` and PATCH `/admin/support-case-metadata/{case_id}/status`: **BLOCKED design candidates**, not admitted operations. Existing retention/closure/abuse protections must remain intact; independent admission requires separate review.
- GET `/admin/financial-case-metadata/{case_id}`: reduced Finance/can_review view for pair-unbound explicitly bound cases only, direct bounded financial history and fence observation without protected context/history helpers, package/hold readiness, private evidence or financial mutation. Grant/account-epoch/revocation and MVCC/lock proof required.

No safe independent financial decision was established, including investigate/resolve_no_change: original authority/evidence/revision/aggregate-lock protocol remains essential. Confirm/escalate affect immutable financial fences and may affect fulfillment exceptions. No weaker approval, refund, settlement or QR lifecycle writer is proposed. Existing tables suffice for reduced projections, but new tightly scoped SECURITY DEFINER helpers/EXECUTE grants would need a separately approved additive database deployment; no broad direct finance/event table grants or duplicate state.

Proposal includes exact DTO/security/error/cursor/audit/revision/transaction requirements, protected data exclusions, frontend mapping, conditional write scope and race blockers, strict forbidden relation/function/route testing plan, risks and implementation order. Safe customer reference, summary, staff identity and updated_at are not invented. Existing legacy support mounts/relay remain a recorded containment concern for separately approved implementation.

Verification performed: static source/document review and documentation consistency checks only; no application tests, DB connections, API calls (including excluded endpoints), browser rendering, fixtures, workers or migrations. Planned tests are not passed-test claims. Live acceptance **BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED**; all prior phase/environment/physical QA/authority blockers persist.

Files changed for this design task: new proposal and this tracker entry only. Recommended next task: review/approve the read-only metadata P1–P3 contracts and exact SQL/route budget, then separately authorize backend/frontend implementation with legacy entry-point containment and isolated deny-by-default tests. No implementation or next module begun.



## Phase 9 source and local-environment recheck (2026-10-24)

The Phase9 blocker record above was already present when this request was inspected. Preserved it and independently rechecked the current source; no duplicated integration or application change was made. The exact Phase9 business-endpoint allowlist remains **empty (0 connected, 5 quarantined candidates)**. Existing audit classifications remain consistent; neither the harmless appearance of an opaque reference nor omission of a field authorizes an operation that actually inspects pair-related records.

Confirmed specific dependencies:

- API097 case_id detail for an assigned case calls sr_support_context. Its linked_orders CTE queries order_pair_units; retained finder-message hold checks join qr_codes and compare pair membership. Ordinary no-case-id listing avoids this particular branch, but remains part of the same quarantined endpoint. No separately approved metadata route exists; no list-only relay exception was introduced.
- API098 sr_support_create validates supplied pair/order associations; its support_cases INSERT reaches sr_retention_dispute_admission → sr_retention_admission (0019), whose support branch queries order_pair_units. Null pair/order payloads are not independent endpoint authorization.
- API099 claim and update both execute pair/order lock queries in the original0021 implementation before action selection.0035 delegates to the renamed sr_support_change_v34; notes-only, claim-only and priority-only requests do not remove those queries. Update also invokes sr_support_context. No note/status editor or unrestricted assignment was connected.
- API324 and API323 both call load_context → the current0030 sr_financial_case_context, which executes order_pair_units/tag_pairs locking SELECTs before returning case context. A read-only projection or investigate/escalate decision is not an independent safe path. No financial tab/form was added.

Rechecked the actual financial DTO: decisions investigate/confirm_dispute/resolve_no_change/escalate respectively bind review_started/settlement_disputed/no_financial_change/requires_review. Body requires both expected_revision and expected_order_revision, strict confirmation, and bound review reference for confirm/resolve. Read limit1–100/default20 and case/revision-bound AEAD cursor do not remove prohibited dependencies. Finance/current session/email/MFA is mandatory; writes additionally require configured Origin, recent signed authentication, independent case authority, idempotency and audit. No refund, payment verification, settlement, recovery or QR operation was enabled.

Local configuration was inspected using key-presence checks only, with no values disclosed. backend/.env exists with database/auth-provider targets unverified and not contacted; financial-review feature and financial-review Origin settings are absent. frontend/.env.local exists but SAFERETURN_API_ORIGIN, SAFERETURN_WEB_ORIGIN, SAFERETURN_SUPABASE_URL and SAFERETURN_SUPABASE_PUBLISHABLE_KEY are absent. No local TCP listeners at127.0.0.1:3000/8000/5432 during this check. No approved named isolated non-production environment is established by those files; **LIVE ACCEPTANCE BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED** remains current. A provisioned environment would not itself resolve endpoint safety.

Current recheck changed only this progress report. Zero HTTP/backend/browser requests, tests, builds, fixtures, migrations, workers or pair/database functions executed. Loopback TCP presence checks were configuration inspection, not API acceptance. No responsive, concurrency, mutation or denylist test pass is claimed. Existing legacy support entrypoints were read as source and were not mounted or followed. Their pre-existing invocation risk remains explicitly unresolved; the mandatory stop did not silently modify application behavior.

Stop result: no Phase9 list/intake/detail/claim/note/status/financial integration can be admitted under the present contracts. Required follow-up is review and approval of independently pair-free support and financial metadata/workflow contracts, explicit allowlist admission, separate legacy containment scope and non-production acceptance prerequisites. This task did not create endpoints, weaken backend rules, alter earlier phase blockers or begin the next module.

## Phase 9A — independent read-only support metadata backend (2026-10-24)

**IMPLEMENTED — PENDING ACCEPTANCE. Backend only; frontend not connected.** Read the complete decoupling proposal, prior progress, corrected inventory/plan/exclusions, API/technical/database/security requirements; reverified source registration, support/events RLS, retained abuse helpers, session/role admission and audit INSERT trigger. Existing Phase4 Orders and five quarantined support/finance APIs remain unchanged. Historical blocked entries above describe the earlier generic endpoints, not permission to use them now.

Implemented exact GET list `/api/v1/admin/support-case-metadata`, detail `/{case_id}` and history `/{case_id}/history`, with descriptive unique OpenAPI operation IDs support_metadata_list_v1/support_metadata_detail_v1/support_metadata_history_v1. Closed models, actual server filters/keyset pagination, bounded event history, explicit queue/assignment authorization and current Support+verified email+signed/provider MFA/session recheck. Case content is **BLOCKED / NOT IMPLEMENTED** for missing approved disclosure/redaction policy; detail content_available is alwaysfalse. All mutations and financial metadata/decisions remain outside Phase9A.

No new SQL helper/grant/migration: existing support/events SELECT grants, restrictive abuse RLS/readability helper and safe audit INSERT privileges suffice. Missing readability helper503; do not broaden visibility on older installed schema. SQL reads only support case/event metadata and existing auth/policy dependencies; never imports old support/financial/order modules or executes context/ownership/retention/fulfillment/pair queries. No case writes means no case admission trigger. Safe audit count uses existing allowed outcome scalar; no audit key allowlist change. No row locks in new queries; existing shared auth/policy advisory admission remains intact.

New source files: `backend/app/api/v1/support_metadata.py`, `backend/app/services/support_metadata.py`, `backend/tests/test_support_metadata.py`. `backend/app/main.py` receives only the new import/install call for this task, preserving existing uncommitted changes. Documentation: Phase9A addenda in API contract/inventory and this tracker. No frontend component/relay/page, production auth/configuration, schema, migration or protected workflow changed. SHA256 baseline comparison for original support/financial/order handlers and retention/support-history/abuse migration sources is unchanged.

Executed from backend: `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider`: **44 passed**; `.venv/Scripts/ruff.exe check app/api/v1/support_metadata.py app/services/support_metadata.py tests/test_support_metadata.py`: **passed**. Ruff formatting applied to these new files only. Isolated ASGI with real synthetic JWT/AEAD and mock JWKS transport, scripted SQL/transactions, no remote DB/provider/fixture/worker or excluded endpoint. Forbidden-route interception and SQL/service denylist active. Covers scope/roles/MFA, policy unavailability/continuation, history assignment/order/gaps/max revision, filtering/pagination/UUID/cursor validation/binding, sensitive-field exclusion, redacted errors/headers, dependency/crypto failures, rollback on final authorization denial, absent content/methods and source registration isolation.

Initial isolated checks found an exception-boundary rollback problem and test-harness route inspection mismatch; corrected without shared auth/old API changes. Final counts above are corrected reruns. Source review also found sr_safe_json rejects arbitrary count keys; bounded list count now uses its approved outcome string, and the SQL double asserts approved audit keys. No audit trigger was relaxed.

Not executed: live PostgreSQL/RLS/ACL/helper/trigger/nested-query tracing, actual migration-state/query-plan/concurrency, deployed JWT/provider/revocation, frontend/browser/responsive acceptance or broad legacy suites. **LIVE ACCEPTANCE BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED.** No evidence changed that existing finding; no unverified environment connected. SQL doubles cannot prove deployed helper internals. Need independently identified authorized isolated environment, installed source-matching existing schema/policies/helpers/grants, real permitted Support/MFA session, approved synthetic case data without pair setup and cursor keys. Earlier Phase3 physical QA/authority and other phase blockers remain.

Admission: **not added to corrected frontend integration allowlist**; no self-approval of absent security prerequisites. Next Phase9 task: review the new contracts and complete isolated PostgreSQL/nested-dependency/auth acceptance, then explicitly admit exact metadata reads and separately authorize frontend integration with legacy support entry-point containment. Do not expose old console as a shortcut. Remaining content/create/claim/note/priority/status/financial workflows retain proposal-specific blockers and need separate approval. No next module started.

## Phase 9B — acceptance assessment and frontend integration gate (2026-10-24)

**BLOCKED — NO CONFIRMED AUTHORIZED NON-PRODUCTION ENVIRONMENT. Phase9B acceptance is NOT COMPLETE. All three Phase9A endpoints remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED; frontend not connected.** Full evidence, endpoint-by-endpoint admission matrix, exact setup prerequisites and frontend mapping: `docs/PHASE_9B_SUPPORT_METADATA_ACCEPTANCE.md`.

Environment discovery used file/key-presence and URL target classification only, with no values/hostnames/credentials printed or settings loaded for service startup. backend/.env has runtime/migration/test DB and Supabase targets, all non-loopback/unverified; key presence does not establish non-production identity/isolation. Relevant process variables absent; frontend/.env.local lacks required server API/web/Supabase settings. No Compose or local Supabase config found in inspected repository paths; docker/supabase/postgres/pg_ctl/psql not on PATH. OS listener inspection was unavailable, so no claim about open ports/service absence. No unverified remote target contacted, environment modified or database created.

Existing pg_rehearsal.py creates schemas/roles and replays migrations after cross-domain metadata/count inspection; it is unsuitable for this restricted run. Integration test_support_cases.py mounts quarantined APIs, uses generic workflow fixtures and SQL-synthetic AAL2 sessions. Neither was executed. No genuine approved disposable provider/MFA identity or retained-abuse policy/case fixture was established. Do not manufacture policy/roles/MFA records or seed cases via legacy support/direct INSERT admission triggers that reach pair tables.

Source security recheck: current JWT/session/email/explicit Support/signed+provider MFA, unassigned-or-mine list/detail and assigned-only history, restrictive retained abuse-policy helper, missing-helper503 and final session/role recheck remain. Business projections are closed case/event metadata, no notes/actors/private content or pair references; content_available=false. Existing RLS/ACL/helper source retained, no context/ownership/retention/pair-row-lock path added. Nested deployed definer/policy/trigger execution and actual RLS remain unverified; shared security advisory admission is not pair-row locking.

Tests actually executed after fixture inspection: from backend `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider`: **44 passed in2.80s**; from root `backend/.venv/Scripts/ruff.exe check backend/app/api/v1/support_metadata.py backend/app/services/support_metadata.py backend/tests/test_support_metadata.py`: **passed**. These are fresh isolated new-router ASGI/JWT/AEAD/scripted-SQL results, with mock JWKS transport and forbidden route/SQL/service checks. No external network/DB/provider/lifespan or legacy setup/teardown. Covers access/scope/filter/pagination/history/minimization/content=false, policy filtering/unavailability, invalid cases/cursors/revisions, redaction and auth-recheck rollback. Not live PostgreSQL/RLS/provider/MFA acceptance; policy expiry internals are not executed by the double.

Blocked tests: actual installed schema/grants/RLS/helpers/owners/trigger/nested relation-access tracing, genuine provider MFA/session/revocation, SQL policy-retention/assignment/concurrency/query plans and deployed responses. No frontend/browser/responsive/legacy suites run. Live acceptance remains **BLOCKED — NON-PRODUCTION ENVIRONMENT NOT PROVISIONED**. Existing Phase3 physical QA/authority and other phase blockers preserved.

Admission decision for GET collection, GET UUID detail and GET UUID history: contracts/source/isolated tests verified; live auth/RLS/installed independence missing; **NOT ADMITTED** for each. Corrected allowlist unchanged; no self-approval or integration based on44 mocked tests. API097/098/099/323/324 remain quarantined. Metadata backend and protected Support/Finance/Phase4 Orders unchanged by Phase9B.

Frontend preparation only: reuse AdminSupportCases visual components/CSS and AdminPage actual Support guard; map Page/Detail/History projections, exact case ID/type/status/priority/queue filters, server keyset pages, honest loading/empty/401/403/404/409/503 states. No customer/subject/updated_at, notes/actor identities/content, mutation or financial controls. Existing support relay targets old APIs and legacy mounts (?view=live/UUID/new) must be contained in a separately authorized integration; do not mount them or widen a generic relay. Plan a closed three-GET authenticated read relay only after admission, with strict response/size/error/redirect/no-store handling, no localStorage/mock fallback, stale request guards and disabled prefetch. No frontend implementation performed.

Required next action: owner identifies and authorizes existing isolated runtime/configuration/identity/data, or separately authorizes safe provisioning design; confirm source-matching installed case/history/session/account/abuse policies, actual Support/MFA identities and already approved case/history/policy fixtures without pair setup. Review restricted PostgreSQL/auth/nested-query tracing harness; run authorized acceptance, then record governance approval/admit exact routes before separately requested frontend work. No database/configuration/identity/policy provisioning performed. Only the new assessment document and this tracker entry were written; stop at assessment/preparation.

## Phase 9C — local acceptance preparation / provisioning gate (2026-10-24)

**PREPARED, NOT PROVISIONED. Phase9B/9C acceptance remains BLOCKED; metadata reads remain NOT ADMITTED; frontend unchanged.** New `docs/PHASE_9C_LOCAL_ACCEPTANCE_ENVIRONMENT.md` records tooling, exact local design, prerequisites, initialization/auth/fixture barriers, test categories, cleanup and a narrowly scoped authorization request.

Deeper discovery supersedes the overall tooling blocker: existing ignored `.local-tools/pg17-core/pgsql/bin` contains postgres/initdb/pg_ctl/psql, all reporting **17.11** with --version. A second pg17 tool tree exists. None of docker/supabase/postgres/pg_ctl/psql/podman is on PATH; wsl is present but no distribution started. No new tool downloaded/installed. Prior portable/development authorization in LOCAL_FRONTEND_BACKEND_PHASE8.md does not authorize this new cluster or restoring its real-data backup. Existing backend DB/auth URLs remain non-loopback/unverified and were not contacted or disclosed.

Prepared inert `ops/phase9c/local-environment.example.json` and read-only `backend/scripts/phase9c_local_preflight.py`. Proposed target:127.0.0.1:55439, database safereturn_phase9c_acceptance, new workspace tmp/phase9c-local/pgdata. Preflight validates exact manifest/path containment/no state links, executes only binary --version, reports inherited DB-setting presence and never creates/starts/connects/restores/migrates. Result: tools17.11, proposed state/data directories absent, inherited DB settings absent; port availability unverified; database isolation **designed, not verified on a running cluster**. No real .env/secret/configuration/service state changed.

Provisioning gate: Phase9C section4 requires explicit existing local authorization before init/start/DB creation. No current local test configuration grants that exact action; therefore none was executed. Concrete approval request is limited to a fresh PostgreSQL17.11 cluster under E:\Projects\SafeReturn\tmp\phase9c-local\pgdata, fresh local bootstrap credential, hidden server bound127.0.0.1:55439, and empty safereturn_phase9c_acceptance DB. No migrations/auth identities/policies/support fixtures/workers/restores or remote data included. Do not infer acceptance permission from an empty local cluster.

Further blockers: existing schema requires managed Supabase auth.users/sessions and current security/policy helpers; full migration execution-path review incomplete, so no broad Alembic chain/rehearsal applied. Passive fresh pair schema is distinguished from executing pair functions/record reads; no such setup executed. Genuine local Auth/MFA stack/enrollment absent; existing auth configuration requires HTTPS and supported asymmetric JWKS, with signed/current provider AAL2. No local HTTP/TLS bypass, mock enrollment evidence or synthetic AAL2 SQL row substituted. No safe approved support-fixture creation path: open/investigating INSERT triggers retention admission's pair-link query even when references null. Trigger/RLS disablement, legacy APIs, closed-case evasion, pair fixtures and copied real-data backups remain prohibited.

Tests actually executed: read-only preflight **passed**; fresh isolated metadata suite `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider` from backend: **44 passed in2.91s**; root Ruff check of new preflight and existing metadata router/service/test **passed**. Fixture/setup/teardown inspected; only scripted SQL/mocked JWKS/synthetic JWT/AEAD, no PostgreSQL/provider/worker calls. Registered three metadata reads verified in source/isolated tests. No local PostgreSQL/RLS integration, genuine Auth/MFA, remote staging/production or frontend acceptance executed. No prohibited pair/API operation attempted. Existing metadata/security/Support/Finance/Phase4 Orders behavior unchanged.

No DB initialized, infrastructure started, migrations applied, test identities/policies/factors enrolled or support/history records created. All three endpoints remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED; no governance approval invented. Earlier phase/physical QA/security blockers persist. Required next action: explicit approval of the bounded blank-cluster step, then reviewed initializer/isolation validation; separately authorize/prepare genuine local auth and safe fixture mechanisms. Stop before provisioning and request that exact approval, as required by the user's section4.

## Phase 9C — owner-approved blank local initialization completed (2026-10-24)

**LIMITED INITIALIZATION COMPLETE; POSTGRESQL/RLS/APPLICATION-AUTH ACCEPTANCE NOT PASSED.** Owner subsequently authorized only a fresh PostgreSQL17.11 cluster at E:\Projects\SafeReturn\tmp\phase9c-local\pgdata, hidden startup bound127.0.0.1:55439, and the empty safereturn_phase9c_acceptance database. This supersedes the earlier unapproved/unprovisioned status for that narrow skeleton only. Full results and preserved historical preparation are in section9 of `docs/PHASE_9C_LOCAL_ACCEPTANCE_ENVIRONMENT.md`.

Before writes: exact paths resolved inside workspace, no links/junctions, run/data directories absent; exclusive loopback port bind succeeded, repeated before start. Tools matched17.11. Added bounded `backend/scripts/phase9c_initialize_local.py`: exact target/explicit approved flag, fresh-state-only refusal, sanitized child environment, no inherited PG*/SAFERETURN_* or existing .env, explicit local host/port/user/database/private passfile and no default connection target. Initdb used new local-only secret, SCRAM authentication and private ACLs for execution account/SYSTEM. No secret printed; temporary initdb password file removed, connection credentials retained only in private ignored state.

Initdb succeeded. pg_ctl's Windows restricted-token start failed with error87 before a server/database existed. Standard postgres.exe was then started with CREATE_NO_WINDOW under the same restricted OS account, private logs and identical loopback/SCRAM settings, without elevation or security changes. A host-address representation mismatch (/32) initially stopped verification before CREATE DATABASE; corrected via host(inet_server_addr()) after read-only identity inspection. No existing cluster was adopted/reinitialized or other server stopped.

Verified actual server data_directory, version170011 and system identifier7699958636828271396 against local pg_controldata before database creation. Only default postgres/template0/template1 existed initially. Created only safereturn_phase9c_acceptance; final catalog lists those system DBs plus this DB. netstat verified only127.0.0.1:55439 for postmaster PID1724 at verification. Empty DB:0 user relations,0 user functions, only default public schema from template initialization; bootstrap verifier SCRAM; HBA/configuration errors0. A separate final psql session with transaction_read_only=on reconfirmed local identity/empty catalogs. No pair records/tables were queried or created. PID/listener are point-in-time evidence, not a permanent health assertion.

New private ignored state: tmp/phase9c-local (PGDATA, local logs, connection passfile and non-secret initialization-result.json). Git-ignore checks passed; private-directory ACL showed only execution account and SYSTEM. No production configuration, system service/global tooling or existing environment file changed. Server left running hidden as approved. Initializer refuses the existing run directory and is not a restart/read-only verification command.

Executed only binary/path/port/isolation checks, approved local init/start/CREATE DATABASE and non-destructive catalog/config/auth-verifier/listener verification; Ruff and format checks for initializer passed. No metadata API test suite rerun in this continuation; earlier44 isolated test results remain historical. No migrations/application schema, fixtures/support records, staff/Auth identities/MFA enrollment, policies, workers, remote/staging/production connections, excluded APIs, QR operations, backend/frontend integration or protected Support/Finance/Phase4 Orders changes.

All three metadata reads remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED. Full Phase9B/9C acceptance is incomplete: genuine local Supabase Auth/TLS/JWKS/MFA, approved schema/migration execution-path and safe fixture creation mechanisms still missing. Request separate explicit authorization before any migrations/schema, fixtures, identities or MFA actions; no such work is performed under this completed limited approval. Stop after the verified empty local database and documentation.

## Phase 9D — local schema initialization preflight BLOCKED (2026-10-24)

**SCHEMA NOT INSTALLED.0 migrations executed /0 database writes.** Owner authorized existing approved non-destructive migrations on the verified local empty DB, not managed-Auth replacement tables, migration edits, identities or fixtures. Exact prerequisite failure and dependency sequence recorded in section10 of `docs/PHASE_9C_LOCAL_ACCEPTANCE_ENVIRONMENT.md`. Existing migration authorization is acknowledged; no repeat permission for the already approved command is requested.

Fresh catalog-only/read-only sessions with explicit host127.0.0.1/port55439/database safereturn_phase9c_acceptance/local private credential verified PostgreSQL17.11, exact Phase9C PGDATA and system identifier7699958636828271396. Inherited PG*/SAFERETURN_* removed; no remote/default-service/.env fallback. DB remains0 application relations/functions, no Alembic version table. auth schema/users/sessions, anon/authenticated and runtime roles absent. No production/shared/remote DB or pair record queried; server neither restarted nor reset.

Actual migration framework is Alembic+SQLAlchemy, backend/alembic.ini/env.py. Static ordered graph from0001 to0035_public_abuse_intake contains36 revisions (including0014a);0035 is needed for retained-abuse restrictions. Source head0043 does not authorize an unrelated head upgrade. Relevant schema sources:0001 staff_roles/FKs;0003 support_cases/audit/RLS/roles;0005 live session guard;0021 case revision/events/assigned-only history;0030 account-state/current session admission;0035 abuse policy/readability/restrictive RLS. Assignment is existing assigned_staff_id, not a new table.

First migration0001 upgrade explicitly requires **managed Supabase auth.users**; actual catalog confirms it absent. Approved SafeReturn migrations do not install provider-managed auth schema/baseline roles.0005 additionally requires compatible managed users/sessions fields and0030 sessions.created_at. Therefore no Alembic invocation or version-table write attempted merely to trigger a known failure. No fake auth schema, SQL patch, hand-created roles, migration edits/skips/stamps or synthetic MFA used. pg_rehearsal's temporary translated minimal auth tables are not an approved genuine provider-schema bootstrap and were not executed.

Expected support/staff/audit/account/abuse tables/functions and runtime roles/grants are absent; support/staff policy count0. This is installed-state inspection, not RLS or authentication acceptance. Passive QR definitions are distinguished from executing protected bodies/records; no prohibited operation executed. Full remaining per-migration SQL/DO/backfill/destructive/grant/trigger audit is not certified complete; execution stops at the missing external prerequisite. No later migration declared safe from name/empty DB alone.

Executed after isolated fixture inspection: from backend `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider`: **44 passed in3.24s**; Ruff check of metadata router/service/test **passed**. Only mock database/JWKS and synthetic JWT/AEAD, no fixture identities/cases or excluded APIs. No PostgreSQL/RLS/auth/MFA application acceptance suite, migration/schema tests or frontend tests executed. No application/protected Support/Finance/Phase4 Orders/frontend/environment/migration code changed. Only setup report and this tracker updated.

Separate next approval needed: reviewed genuine local Supabase Auth infrastructure/schema/baseline-role bootstrap for this exact isolated database, without identities or fixtures, using the actual provider-supported mechanism rather than replacement DDL. Then finish complete migration safety review and apply existing approved Alembic sequence through an explicitly verified local connection. Staff identities/MFA/support fixtures remain separately unauthorized/missing. All three metadata endpoints remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED; no frontend connection or next phase begun. Stop at this exact preflight blocker.

## Phase 9D.1 — genuine local Supabase Auth bootstrap assessment (2026-10-24)

**PLAN ONLY / NOT EXECUTED.** Added `docs/PHASE_9D_SUPABASE_BOOTSTRAP_PLAN.md`, covering missing managed Auth tables/roles, extensions/function/context distinctions, JWT/HTTPS/MFA and migration privileges, official alternatives, compatibility, local isolation/ports, approvals, acceptance and cleanup. Three metadata endpoints remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED. Existing Phase9C cluster unchanged and not reconnected this turn.

Required managed users/sessions columns come from0001/0005/0029/0030; baseline anon/authenticated must precede SafeReturn migrations. Actual provider runtime additionally needs its own identity/session/refresh/MFA/schema-migration infrastructure. SafeReturn creates its own runtime roles/helpers/RLS through the existing Alembic chain and uses transaction-local safereturn.actor_id/mfa_verified, not frontend roles or an auth.uid shortcut. No metadata-specific extension installation was established; core PostgreSQL17 gen_random_uuid and Python AEAD suffice for those parts. Historical Vault backup dependency is not a requirement to restore real data. Genuine email verification, live provider sessions and real TOTP AAL2 remain later runtime acceptance requirements, not satisfied by schema existence.

Official sources checked: Supabase Docker/CLI/runtime/PG17/ES256/HTTPS/TOTP documentation and official Compose/Auth source; Docker Windows prerequisites; HTTPX/PostgreSQL references linked in the plan. Recommended a **separate official Docker Compose Supabase stack with its own provider-managed PostgreSQL17 container**, preserving55439/old database/PGDATA. Docker Desktop Linux containers+Compose required for selected Windows approach; Supabase CLI optional. CLI/container is a supported alternative; documented experimental native runtime is not Windows-native. Git/Node24.21.0/wsl available; Docker/Supabase CLI absent from PATH; WSL2/virtualization/daemon capability not established. No installation/image/source clone performed.

External Postgres integration is technically represented in official Compose comments, but no reviewed safe conversion/bootstrap exists for this bare standalone cluster; it is not selected. Official Compose fixed names/port/mount assumptions need isolation overrides, not merely a project label. Proposed separate project safereturn-phase9d1-local; HTTPS55461/direct DB55462, optional disabled Studio55463 and separately approved mail capture55464, all host-loopback-only; no reservation/startup. Provider-owned default DB in this dedicated container is a new target and requires separate migration approval; do not transfer the old55439 authorization or assume Auth appears in a second empty DB.

Repository requires HTTPS origin and ES256/RS256 JWKS with exact issuer/session/audience. Official ES256 and HTTPS mechanisms exist, but actual pinned configuration needs review. HTTPX trust_env=False means a browser/Windows trust change or SSL_CERT_FILE alone is not proof of Python CA trust; plan requires approved isolated test trust configuration, never verify=False/HTTP/HS256 shortcuts. No signing secrets, tokens, connection secrets or MFA evidence printed/invented.

Next exact approval request is tooling-only: validate Windows/WSL readiness and download/install a reviewed official Docker Desktop release with Linux containers/Compose if compatible; no Windows-feature/WSL installation/update/reboot without additional decision, no images/stack/bootstrap/schema/trust changes/migrations/identities/fixtures. Later separate approvals cover pinned official artifact/config review, image/resource/provider-schema/TLS bootstrap, new-target SafeReturn migration and actual identities/MFA/safe fixtures. Retention-admission fixture barrier and full migration safety audit remain; no broad approval inferred.

Executed only static/source/tool-presence/version and public official-document research; no DB connections, infrastructure/test/API calls or suite run. Earlier44 isolated tests remain historical results. No protected Support/Finance/Phase4 Orders, migration source, existing environment or frontend change; no QR operation or remote project contact. Only plan and this tracker entry written. Stop after assessment; frontend remains unconnected and all three routes NOT ADMITTED.

## Phase 9D — owner-confirmed Cloud development acceptance preparation (2026-10-24)

**CLOUD CANDIDATE CONFIRMED BY OWNER; REMOTE ACCESS NOT AUTHORIZED OR EXECUTED.** Owner states the existing Supabase Cloud project is SafeReturn development/testing only, not production, and directs cancellation of Docker Desktop/local Supabase bootstrap. The local tooling/installation proposals above are superseded, not pending approval actions. Existing PostgreSQL17.11/55439 cluster is preserved unchanged and not connected/restarted this turn. Three metadata reads remain IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED; frontend untouched.

New `docs/PHASE_9D_CLOUD_ACCEPTANCE_PLAN.md` records the redacted configured reference **fhux…kzvq**, reference SHA256 prefix **17e54a8be1b7**, owner designation, historical installed-state evidence, runtime requirements, exact remote approval stages and impact/fixture blockers. Configuration compared in memory without printing URLs/credentials/keys: backend Auth/runtime/migration/test targets match one project; DB URLs select the same pooler endpoint/database name (session-pooler candidates), with different logins. TEST_DATABASE_URL does not supply database isolation. No explicit environment label/dedicated acceptance configuration established in inspected standard paths; designation is owner confirmation, not URL inference.

Historical LOCAL_FRONTEND_BACKEND_PHASE8.md records development migration head0043/no pending revisions and111 tables on23 October, with existing profile/staff/catalog/audit/idempotency rows preserved. This is not a fresh cloud result. Real-customer versus synthetic provenance is unverified; preserve all existing accounts/records and never use owner Operations/Finance accounts or other real accounts as fixtures. Cloud Auth/baseline roles and required0035 RLS/helpers are expected from provider/history, not verified available or source-equivalent today. No migrations/cloud grants/repairs are authorized; previous local55439 migration approval does not transfer to Cloud.

Exact next remote request **A only**, still awaiting authorization: owner confirms redacted project identity; connect via explicitly configured reviewed target/credential with TLS identity validation, timeouts and enforced read-only session; query only connection/catalog metadata, installed public.alembic_version and named Auth/support/staff/account/abuse/audit structure/RLS/grants/function/trigger definitions without executing business helpers or reading application/Auth/staff/policy/case/customer records or domain counts. Separately enumerate one bounded unauthenticated HTTPS public JWKS GET for the same project, if approved; no sign-in/enrollment. No endpoint fallback/repair, temporary schema/role or existing harness. Normal connection/access logs are possible, no application write proposed. No actual remote action performed.

Later approvals separate: genuine dedicated provider accounts/email confirmation/TOTP/Support grants; exact synthetic cases/history/retained-policy fixtures; focused restricted-role acceptance; minimal metadata GET audit INSERTs; any discovered repair/new project. Existing Support grant confers actual queue permissions, not fixture-only authority; tests must use queue=mine for dedicated new operators or exact synthetic IDs to avoid enumerating unrelated unassigned cases. No drop/helper/global-policy negative test on populated development data. Retention admission still queries pair linkage on open/investigating case INSERT even with null refs: no current safe fixture creation mechanism, no direct INSERT/old support route/trigger bypass/closed-case workaround. Cloud designation or separate empty project does not erase that blocker.

Use existing confirmed development project for read-only preflight candidate; a separate fresh cloud acceptance project is safer for later write-heavy/disposable/global negative scenarios if existing data cannot be isolated, requiring its own explicit approval and no real-data cloning. No new project created or silently substituted. Preserving append-only case/history/audit records means no promise of automatic fixture cleanup. Full migration compatibility and deployed nested SQL/JWT/session/MFA/RLS acceptance still required before admission.

Only local config/source/docs inspected; no Cloud/Dashboard/Auth/JWKS/Management API/database/DNS probe, test suite, identity/MFA/fixture/migration/QR operation or infrastructure change. Previous44 isolated results remain historical, not live acceptance. Wrote cloud plan, updated Phase9B current gate and marked old local bootstrap proposal superseded, plus this tracker entry. No protected Support/Finance/Phase4 Orders, frontend, environment, application or allowlist change. Stop after cloud plan; request exact A authorization before remote access.


## Phase 9D — authorized Cloud read-only audit (2026-10-24)

Target confirmed locally against owner-approved fhux…kzvq / reference fingerprint17e54a8be1b7. Reviewed static catalog-only query allowlist, selected existing runtime credential, explicit configured target, verify-full with Certifi, sanitized PG defaults and read-only/time-limited transaction configuration. Runtime credentials are not independently certified metadata-only, so no arbitrary/application-function queries were eligible.

**BLOCKED before SQL:** after initial network restriction, the network-permitted attempt failed PostgreSQL certificate verification (OperationalError, no SQLSTATE). No database connection/BEGIN/catalog/Alembic query occurred; server identity/read-only mode, installed head, Auth schema, roles/grants/RLS/functions remain UNVERIFIED. Historical0043_standalone_activation is not an actual observed head in this audit. No insecure retry, alternative target or improvised fix.

Exactly one public project JWKS HTTPS GET completed with verified TLS,200, no auth headers/proxies/redirects and64KiB bound. One ES256 EC/P-256 verification key (use=sig,key_ops=[verify], no private fields); discovery format matches backend verifier expectations. This does not prove issued-token/Auth/email/session/MFA or RLS acceptance.

Updated docs/PHASE_9D_CLOUD_ACCEPTANCE_PLAN.md section11 with actual results/limits and next approval. No tests/Ruff rerun;44 isolated tests are historical only. No application/domain/Auth/session/customer/case/order/payment/QR records read; no application/security-definer functions, protected routes or metadata GETs executed. No migrations/writes/identities/MFA/fixtures/local-cluster changes or application/environment/frontend/allowlist changes. Docker/local bootstrap remains cancelled.

Next: trusted provider CA/connection evidence for this exact pooler target, then separately authorized audit-only trust staging and same-target verify-full metadata retry; no repeat JWKS GET. No TLS downgrade. Dedicated genuine verified Support/MFA identities, safe pair-independent case fixtures (retention-trigger blocker unresolved), real restricted-role RLS/auth acceptance and minimal GET audit-write approval remain outstanding. All three metadata endpoints remain IMPLEMENTED — PENDING ACCEPTANCE / **NOT ADMITTED**. Stop at assessment.


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


## Phase 9 — offline read-only frontend completion (2026-10-24)

**READ-ONLY FRONTEND IMPLEMENTED — LIVE INTEGRATION DISABLED — ACCEPTANCE PENDING.** All three Support Metadata APIs remain **NOT ADMITTED**. The owner reported the cloud project had been paused and is now resuming it; that is not independent evidence of the TLS failure's cause or successful restoration. The later user instruction requests a same-target limited live check after this offline work, without enabling UI routing.

### Exact frontend files changed/added

- `components/admin-support-cases.tsx`: reused existing screen/AdminShell, AdminCard, shared status badges/table patterns and responsive module stylesheet. Replaced browser-persisted demo cases and mutations with closed metadata projections. No mock fallback or application authentication bypass.
- `lib/admin-support-metadata.ts`: typed closed list/detail/history contracts, enum/UUID/revision/date/cursor/query validation, redacted error messages and same-origin GET clients.
- `lib/support-metadata-gate.ts`: server-only admission function returns false unconditionally. No environment switch, query/localStorage/client activation or deployment activation mechanism exists. Future activation requires explicit acceptance/admission and a reviewed server-controlled release change.
- `lib/api/support-metadata-relay.ts`: prepared bounded no-store authenticated relay, exact path construction, GET-only validation, origin/fetch-site checks, verifiedSession, staffState explicit Support/capability/MFA precheck and final recheck, redacted errors. Backend retains verified email/provider session/MFA/RLS/abuse checks. Gate returns503 before authentication/staff/upstream calls.
- `app/admin/support/page.tsx` and `app/admin/support/[caseId]/page.tsx`: retain AdminPage authorization; pass disabled server gate for all URLs, including former view=live and UUID paths. No legacy console imports/mounts.
- `app/admin/support/new/page.tsx`: authenticated unavailable state; no intake or mutation console.
- `app/admin/support/api/route.ts`: quarantined original relay replaced with fail-closed no-forwarding responses. Original API097/098/099 paths cannot be reached through it; no backend handler changed.
- `app/admin/support/metadata-api/route.ts`, `app/admin/support/metadata-api/[caseId]/route.ts`, `app/admin/support/metadata-api/[caseId]/history/route.ts`: exact prepared relay entry points; force-dynamic; explicit HEAD avoids automatic GET forwarding. Disabled gate rejects direct calls, including prefetch-style requests. Unsupported methods are not forwarded.
- `tests/support-metadata-fixture.cjs`, `scripts/test-support-metadata.cjs`, `tests/support-metadata.spec.ts`, `playwright.support-metadata.config.ts`: isolated VM/route-intercepted synthetic transport and browser tests only. Test injection exists only in these fixtures. No real server/auth/database/credentials/environment files are loaded by the test harness.

### Contract mapping (prepared, not admitted)

| Backend GET contract | Frontend mapping |
|---|---|
| `/api/v1/admin/support-case-metadata` | List items: case_id,case_type,status,priority,case_revision,created_at,assignment,assigned_to_me; as_of,next_cursor. Only case_id/case_type/status/priority/queue/limit/cursor filters. Queue defaults to mine. Exact case ID, enum selects,20/50/100 page-size control; opaque next/previous navigation; refresh/filter reset to first page; no complete-directory/count claim. |
| `/api/v1/admin/support-case-metadata/{case_id}` | Exact closed metadata + content_available:false. Rejects content_available:true or extra content/customer fields. Metadata only; missing/out-of-scope cases show redacted404 state. |
| `/api/v1/admin/support-case-metadata/{case_id}/history` | case_id,case_revision,items,next_cursor; event_id,case_revision,event_type,from_status,to_status,priority,created_at only. Assigned-to-me only; explicit Load history, opaque older-history cursor and refresh. No eager history prefetch or inferred revision-gap events.409 restarts through Refresh history. |

Loading/empty/access-denied/MFA/unauthorized/missing-case/invalid-filter/stale-history/backend-unavailable states are implemented. Every Support detail/back link sets prefetch=false. No automatic backend fetch occurs during disabled rendering/effects/direct API execution. No descriptions, customer identities, assignee identities, actor identities or notes are fabricated or enriched through legacy APIs. Unsupported Create/Claim/Note/Priority/Status/Financial Decision/QR operations remain disabled; financial API323/324 remain quarantined.

### Actual isolated validation

- `node scripts/test-support-metadata.cjs`: **73 passed**, including actual disabled gate (zero auth/staff/upstream calls), exact paths/methods/query keys,403 wrong roles/no-MFA/no capability,401,404,409,422,429, unavailable errors, strict extra-field rejection, oversized response, identifier mismatch, assignment history restriction, final revocation recheck, no-store and permanently blocked original relay.
- `node node_modules/@playwright/test/cli.js test --config playwright.support-metadata.config.ts --max-failures=1`: **23 passed in36.6s** after correcting test-only stylesheet loading and accessible select names. Includes list/details/history, loading/empty/pagination/filter/reset/refresh, unauthorized/forbidden/missing-MFA/missing-case/backend failures, unsupported list/detail/history projections, disabled gate, no unexpected/prohibited requests and keyboard/mobile/tablet/desktop checks. Initial harness runs failed and were corrected; only final passes are acceptance evidence for offline behavior.
- Strengthened disabled-gate tests with server rendering + hydration; focused rerun **2 passed in6.9s**, no hydration errors or network/auth/staff calls. Browser Next Link is replaced with an ordinary anchor by the existing isolated harness, so actual Next prefetch is additionally guarded by explicit source prefetch=false; no deployed-browser acceptance is claimed.
- `npm run typecheck`: **passed**; rerun after typed enum contract refinement passed.
- backend `.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider`: **44 passed in3.96s**, after confirming in-memory SQL/JWKS/ASGI setup and no prohibited setup/teardown. No database integration or original route suite executed.
- backend Ruff on metadata router/service/tests: **passed**. No frontend lint script or installed lint executable exists; no frontend lint pass is claimed and no package was installed.
- Reviewed1366px and375px synthetic screenshots under `test-results/support-metadata/`; screenshots are mock evidence, not live customer data. Protected backend Support/Finance/Phase4 Orders SHA256 hashes remain identical to the pre-task baselines.

No live requests occurred during offline implementation/testing, no fixtures/identities/database writes/migrations/QR requests, no allowlist change and no Phase10. Existing generic legacy Support/demo suites target retired behavior and were not run; the dedicated configuration deliberately excludes them and any live fixture setup.

### Remaining acceptance and exact activation sequence

1. Complete an independently trusted verify-full same-project read-only metadata audit after restoration; verify actual installed head, managed Auth, runtime grants/RLS/function security. Resumption alone does not establish trust or schema compatibility.
2. Resolve any installed/source discrepancies through separately reviewed/authorized changes; do not bypass policies or weaken TLS/MFA.
3. Separately approve genuine dedicated verified Support/MFA identities, safe synthetic cases/assignment/history/abuse-policy scenarios and scoped actual runtime acceptance. Retention-trigger QR fixture dependency remains unresolved. Metadata GETs write minimal audits, so live API checks require explicit audit-write authorization despite read-only UI methods.
4. Establish real JWT/provider session/email/MFA/queue/RLS/fail-closed/projection/QR-independence acceptance evidence. No existing real accounts or records are test fixtures.
5. Record admission of exactly these three GET shapes, then review and approve the server-controlled gate/release configuration change. Keep the old relay blocked; run authorized staged browser checks and preservation checks before deployment. No browser state or ordinary user can activate routing today.

Support mutations, case content and independent financial review remain blocked pending separate approved contracts. Offline completion is not full Phase9 acceptance. The subsequent limited live-check result will be recorded separately below.


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


## Original Phase 9 Step 2 — runtime TLS edit stopped at proposal comparison (2026-10-24)

**NOT APPLIED.** Read tmp/phase9-step2/runtime-tls-proposal.json before editing. The proposed target is backend/.env → SAFERETURN_DATABASE_URL with sslmode=verify-full, but its sslrootcert is `E:\Projects\SafeReturn\tmp\phase9-cloud-audit\supabase-verified-root.pem`. The current authorization instead specifies `E:\Projects\SafeReturn\tmp\phase9c-local\supabase-db-ca.crt` and explicitly requires stopping if the proposal differs. These are different paths, even though prior evidence describes related CA material. Do not silently substitute or amend the reviewed proposal under that stop condition.

Stopped at the discrepancy. No backend/.env read/edit, hostname/CA revalidation, driver execution, restart/deployment, SQL/network request, certificate change, identities/fixtures/schema/record modification, QR API or frontend activation occurred in this attempt. Only this tracker entry was added. Earlier TLS proposal offline validation remains historical, not post-edit validation. Runtime fix remains pending; Step2 is not passed. All three metadata endpoints remain **NOT ADMITTED** and live gate **DISABLED**.

To proceed, resolve the exact trust-file path in the reviewed proposal versus authorization, explicitly superseding the stop condition for that identified discrepancy. No other connection setting, credential or environment variable may change.


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


## Phase 9 Support test-account provisioning — authority and mechanism findings (2026-10-24)

**PREPARED; NOT CREATED.** Owner confirms project ownership and approves the supplied Gmail address solely as the intended dedicated development Support test subject. In the follow-up the owner explicitly confirms no independent custodian/reviewer or approved role-grant procedure is yet identified, and prohibits identity creation, role grants and MFA enrollment until those prerequisites are verified. This report stays within the original Phase9 task; no new subdivision/Phase10.

Prepared the exact subject request in ignored `tmp/phase9-step2/support-test-account-request.json`; full address is kept out of this tracked report. This is a planning request, not a signed authority record, grant receipt or proof the email/user already exists. No password/token/factor seed, fabricated actor UUID or invented provisioner identity recorded.

### Findings from actual approved architecture

- **Normative BTR-01**: docs/SafeReturn_13_Blocked_Task_Contract_Review_2026-10-19.md:40–50 approves controlled provisioning outside the application, not a web role editor/new role-management API. Owner approves the subject/role/purpose/change/scope; a separately identified security custodian validates identity/MFA through a privileged controlled channel. It explicitly prohibits shared identities, self-grants and email-derived roles, and requires a real independent approver/custodian and human onboarding/revocation/recovery drill.
- **ops/STAFF_PROVISIONING.md** sections1,3,4,8 says implemented offline runbook/rehearsal, not live execution authorization. It explicitly leaves the named owner delegate/custodian/executor/channel and role-change writer unidentified; the role change/version/receipt/concurrency/execution contract remains gated. Owner/requester, independent reviewer/custodian and executor must be recorded with real authority. Different roles on one human do not provide independence; no self-grant or placeholder people. The material does not justify inventing an additional administrator role or requiring an arbitrary number of distinct people beyond its stated independence/separation rules.
- **No application role automatically provisions staff.** Support/operations/finance/security_admin/superadmin authorize only explicitly named endpoints. A security_admin label, technical migration credential or service key does not establish human staff-grant authority. The defined authority is the named, explicitly approved custodian/executor using the controlled privileged channel; **none is identified in this session or approved sources**. This is not an assertion that no authorized human exists outside the repository.
- `backend/app/db/provision_runtime.py` provisions database runtime login credentials/SQL roles, not Supabase identities or staff_roles application grants. Do not execute it for this account. `backend/app/api/v1/staff_directory.py` and sr_staff_directory/sr_staff_account_state are read helpers; account-lifecycle commands/custody helpers are not a general staff-role grant workflow. Existing integration tests insert synthetic staff rows in rehearsal schemas and are not live provisioning tools.
- Existing staff_roles schema supplies user_id,role,granted_by,granted_at,revoked_at,reason,id, active-role uniqueness and Auth FKs; runtime has only own-row SELECT, not an approved grant writer. No independently scoped live Support grant CLI/admin workflow/restricted API was found. A naked INSERT using migration credentials would bypass the required workflow and is not selected.
- Historical runbook wording about installed0021/pending0030 is stale: previously verified current head0043 and catalog include security_custodians/account_action_approvals. Their structural presence does not prove named active custodians or create a missing role-grant executor. Do not query existing private identities/custody records broadly to nominate a person automatically.

### Identity, MFA and authorization flow prepared

Existing `frontend/app/auth/actions.ts` uses official Supabase `auth.signUp` with email/password/display_name and same-origin email callback; it assigns no staff role. The supplied email is a development test subject only. Before any creation the approved operator must establish whether that exact address already exists through an authorized narrow channel; collision means stop, not reset password, change roles or repurpose an existing account. No current lookup/signup/invite/resend was performed.

Genuine email confirmation uses the supported callback exchange; no auto-confirm flag or auth.users insertion. Supported TOTP is enroll → challenge/verify → fresh signed/provider AAL2, with seed/code custody held by the real test subject and never copied into chat/logs. Existing `frontend/lib/auth/mfa-flow.ts` calls listFactors/enroll/challengeAndVerify and rechecks current backend security; no mock MFA acceptance.

**Onboarding dependency:** the existing /admin/security/mfa page/action calls staffSecurity(), and GET /me/staff-security requires an already active staff role (AAL1 bootstrap is allowed only for current staff). The runbook expects genuine identity/MFA validation before the privileged grant. Therefore a not-yet-staff user cannot use that staff page to prove pre-grant MFA. The named controlled provisioner needs a separately approved official Auth enrollment interaction outside that restricted page; do not grant temporary Support/security authority to unlock enrollment or weaken the page. No such external live enrollment tool/channel is currently identified; no new app bypass/tool was implemented here.

Support permission remains verified live email + signed/current-provider MFA + explicit current unrevoked Support + final session/role recheck. There is no separate queue-membership table/permission in this metadata contract: list/detail use mine/unassigned predicates and cases.assigned_staff_id; history is current-assignee only. Creating Support does not claim/assign cases or approve generic all-queue tests. Existing case assignment and retained sr_abuse_case_readable/current policy/triage/retention checks remain unchanged.

### Account creation and cleanup side effects

Documented expected provider effects for later approval: new Auth identity/confirmation email and provider logs/hooks; confirmation/sign-in session/refresh state and cookies; TOTP factor/challenge/AMR/session assurance changes; separately approved Support role history plus minimal grant audit/receipt. Signup supplies display_name as provider metadata but does not imply a public.user_profiles INSERT: inspected application profile insertion occurs through the separate profile-edit API. Do not invoke profile edits, activation tickets/flows, existing users or unrelated APIs as onboarding shortcuts. Use a clean dedicated browser session without stale activation/scan tickets.

Actual project's current signup/email/MFA hooks, SMTP/callback behavior and auth.users trigger dependencies have not been attested for this operation; no claim of no side effects. They need narrow authorized precreation review, especially possible notification/provider/QR effects. No unrelated Auth records or Management API queried in this task.

Cleanup is not guaranteed deletion: staff_roles user/grantor FKs, append-only audit and support event actor FKs can restrict Auth user deletion. Preserve role history; approved revocation stamps only the intended grant, never deletes/rewrites historical grants. Provider session revocation, factor removal and account deletion are distinct operations, not implicit cleanup. Review exact dependencies/retention and subject-only idempotency/collision rules before approving creation. Existing real owner/customer data must remain untouched. No cleanup or revocation executed.

### Exact current outcome

| Item | Actual status |
|---|---|
| Intended test email | Supplied/approved for this one development subject; no identity existence inferred. |
| Named authorized live provisioner | **NOT IDENTIFIED**; owner confirms no independent reviewer/executor mechanism yet. |
| Independent custodian/reviewer required? | **YES** under BTR-01 and controlled staff runbook, distinct real human/actor; authority and genuine identity/MFA evidence through a trusted privileged channel, not two role labels or simulated evidence. |
| Approved executable Support grant mechanism | **NOT FOUND / NOT VERIFIED**; controlled procedure design exists, live writer/receipt/version/authority gates remain. |
| Identity created / email verified / MFA enrolled | **NO / NOT EXECUTED / NOT EXECUTED**. |
| Support role granted | **NO**. |
| Genuine authenticated API/RLS acceptance | **NOT EXECUTED / BLOCKED**. Earlier actual unauthenticated401 and140 isolated checks remain separate evidence. |
| Approved safe case fixtures | **NOT ESTABLISHED**; retention-trigger QR dependency still blocks generic case creation. No case/assignment write. |
| Endpoint admission / live UI enable/test | **NO / NO**. All three NOT ADMITTED; gate DISABLED. |

### Shortest compliant path and exact decision needed

1. **Designate a real independent security custodian/reviewer and named controlled grant executor/channel**, with their actual authority, and the named test-account custodian. They must be independent as prescribed and cannot self-grant. Owner approval of this email/person-purpose does not fill these roles automatically. No passwords, OTPs, bearer tokens or private evidence in chat.
2. **Explicitly approve a bounded one-subject Support provisioning procedure for implementation/rehearsal**, because no executable approved grant writer exists. It must enforce current identity/MFA/actor authority, no self-grant, exact subject/role/change reference, concurrency/custodian safeguards, existing history semantics and atomic approved audit/receipt handling. Missing receipt/version storage/authority mapping needs a reviewed contract, not invented SQL/table/grants. This is controlled provisioning work under BTR-01, not a new role editor, unrestricted SQL or administrator-role invention. Naming a reviewer alone does not create this missing mechanism.
3. Once that mechanism, actual side effects and cleanup are verified, obtain explicit execution approval and perform official Auth signup for only the supplied subject, real inbox verification and genuine pre-grant TOTP through the approved controlled channel. Stop on an existing-account collision. The owner/test subject enters private credentials and authenticator codes privately.
4. Execute only the approved exact Support grant; then verify own live staff-security state/AAL2 and minimum scoped metadata acceptance. Safe case fixtures and their audit writes require their existing separate approval/mechanism. Do not call quarantined creation or treat a valid Support login alone as full assignment/RLS acceptance.
5. Preserve unresolved mandatory transport acceptance as an infrastructure gate, without repeating TLS investigations. Only after all mandatory evidence and exact allowlist admission may existing server-side development gate and real UI tests proceed.

**Stop now before all cloud writes:** no identity, role or factor action until steps1–3 prerequisites and explicit execution approval are satisfied. No provider call, SQL, secret access, unrelated test rerun, TLS change, backend/frontend code change, QR action, existing-account/case change or deployment this task. Only preparation artifact and this integration tracker updated. Phase9 remains incomplete; no Phase10 or additional subdivision.


## Phase 9 — Ahmad independent-custodian designation assessment (2026-10-24)

Owner/requester nominates real teammate **Ahmad**, a separate person with no SafeReturn staff or Supabase Auth account, as proposed independent custodian/reviewer. This records the owner's designation, **not completed independent review, authenticated authority, a custody-table enrollment or permission to grant roles**. Existing dedicated test email remains approved only as the subject; full address stays in ignored preparation request. No new phase/subdivision.

### Decisions grounded in the actual design

| Question | Determination |
|---|---|
| Can Ahmad review without an existing account? | **Potentially yes for the off-app/manual BTR-01 review.** BTR-01 explicitly places identity/MFA validation in a controlled privileged channel outside the app and does not explicitly require every manual reviewer to have a SafeReturn/Supabase account. Owner designation establishes the proposed person, not that the channel, competence, identity or evidence have been verified. The current documents do not provide a complete operational manual-attestation format/verifier; that bounded procedure still needs explicit approval before relying on it. |
| Does existing BTR-01 mandate a specific staff role for that reviewer? | **No specific application role is named as a universal BTR-01 staff-provisioning authority.** Do not translate the words security custodian into an automatic security_admin/superadmin grant. Common JWT/AAL2/recent-AMR requirements apply to authenticated protected execution; off-app evidence cannot impersonate an API principal. |
| What about sr_lifecycle_custodian? | Separate0030 account-lifecycle mechanism requires an Auth UUID, eligible/unexpired/unrevoked security_custodians entry, account epoch eligibility and active security_admin. Ahmad cannot satisfy it without onboarding and those approvals. It is not a staff-role writer or a requirement automatically transplanted onto off-app BTR-01 review. Do not call it, insert Ahmad into custody tables or grant security_admin to solve this task. |
| Must reviewer and grant executor be different humans? | **Not explicitly established as a universal BTR-01 staff-grant requirement.** The runbook records the fields separately and demands independent review/no self-grants; it does not unambiguously mandate two different people for these particular two fields. The offline reference model in tests/test_staff_provisioning_policy.py rejects subject=executor/owner/custodian and owner=custodian, but does not reject custodian=executor. This is supporting design evidence, not live authorization. Therefore do not invent a mandatory third person, and do not infer approval for combined duties. The exact one-account procedure must explicitly approve whether Ahmad is review-only or also separately authorized executor. Account-lifecycle/manufacturing distinct-executor rules are workflow-specific. |
| Independence that is mandatory | Ahmad must be a distinct real human from the owner/requester and subject as applicable to no-self-grant/independent-evidence rules; two accounts/roles on one human cannot manufacture independence. Existing owner account is not a test subject. If the requester also controls the test subject, they cannot use a second login to execute a self-grant. Record actual people/authority honestly; do not infer subject identity from an email or workspace username. |
| Approved recording mechanism | Design requires an **off-app controlled change packet plus independently held signed identity/custody/recovery evidence**, with requester/owner approver/reviewer/executor, exact subject/role/purpose/change reference/scope and decision/outcome. **No actual trusted repository/channel, signing/verification method, live encrypted grant receipt or approved recording executor is established in this session.** A tracker sentence or unsigned JSON is not Ahmad's independent approval. Do not invent an approval signature or new audit JSON fields/table. |
| Exact authorized executor and grant mechanism | **Still NOT IDENTIFIED.** Project ownership is product/approval authority, not automatically direct SQL authority. The design calls for a named explicitly authorized controlled privileged operator; no general application role grants staff. Existing staff directory/custody/lifecycle readers and db/provision_runtime.py do not provision Support identities/application roles. No live approved Support-role writer/API/admin workflow found. Neither a migration credential nor a service key alone supplies missing human authority. |
| Does Ahmad need a new limited staff account? | **Not proven necessary for manual/off-app review. Do not create one now.** No separate limited custodian/reviewer role exists in the approved role enum. If the chosen execution path later requires an authenticated application actor, approve exact least-privilege onboarding/purpose, genuine email/MFA and any custody evidence through the reviewed mechanism first. Do not bootstrap a broad role just to unlock the mechanism; no new role is invented. |

### Source references and interpretation limits

- docs/SafeReturn_13_Blocked_Task_Contract_Review_2026-10-19.md:40–50 (BTR-01): controlled provisioning outside app; named owner decision, separate security custodian, no self-grants/email-derived roles, serialized custody checks, audit/history and offline recovery evidence. Its authority/common-rule sections distinguish design approval from real execution and retain signed/live verified identity/MFA/recent authentication requirements for applicable protected actions.
- ops/STAFF_PROVISIONING.md sections1,3,4,6,8: offline runbook, no live grant writer/receipt/version mechanism, named authorities/channel still required; private evidence outside application cases/logs. Its historical0021/pending0030 text is not current installation evidence; verified current head0043 remains unchanged.
- backend/tests/test_staff_provisioning_policy.py Packet/Rehearsal: synthetic independence examples only; explicitly not production schemas/auth/receipts/executor. No test labels/counters can designate Ahmad or approve a real grant.
- backend/alembic/versions/0030_account_lifecycle.sql sr_lifecycle_custodian/sr_lifecycle_context: specific authenticated security-admin/custody/independent lifecycle decision predicates, not generic staff onboarding. No existing staff permission was inspected from real user records.

**Assessment distinction:** absence of an explicit account requirement permits considering a manual reviewer; it does not certify a missing manual evidence process. Likewise absence of an explicit reviewer/executor inequality is not execution approval. Choose/approve a bounded authority mapping rather than silently weakening or expanding existing policy.

### Shortest compliant procedure for the one proposed Support identity

1. **Approve the bounded manual authority/evidence mapping.** Confirm Ahmad's intended off-app reviewer scope, a trusted owner↔Ahmad identity-confirmation channel, how Ahmad verifies the test person's genuine email/MFA evidence, how his independently authenticated/signed approval is retained and verified, and the exact named grant executor. State explicitly whether reviewer and executor are different people or combined under a reviewed authorization. Do not require Ahmad to acquire Security Admin simply to witness evidence; do not treat a chat nomination as a completed signed review.
2. **Approve the missing one-subject grant procedure for implementation/rehearsal.** Restrict it to the exact resulting provider UUID and Support role with named grantor/change reference, no self-grant, existing-history preservation, controlled concurrency/last-custodian protection, authoritative expected-state semantics and approved atomic audit/receipt. The current application has no approved executable writer; an unreviewed INSERT in the Dashboard is not that procedure. No unrestricted SQL, new web editor or broad administrator grant. Resolve missing authority/receipt contract explicitly; do not invent database storage or bypass existing fields.
3. After those preconditions, separately authorize only the supplied subject's **official Auth signup → real email confirmation → genuine TOTP enrollment/challenge/verification** with user-held secrets, reviewed signup/email/hook side effects and existing-account collision handling. Existing /admin/security/mfa requires a current staff role, so a controlled official provider enrollment interaction is needed to obtain genuine pre-grant MFA evidence without a temporary privilege grant. That interaction/tool must be named/approved, not faked. Ahmad may witness/validate the evidence without receiving a staff account if the approved manual procedure allows it; do not disclose passwords, tokens, TOTP seeds/codes or identity documents in chat/repo.
4. Named executor applies only the approved grant after Ahmad's valid review and current evidence checks; real backend verifies verified email, live signed/provider AAL2 and exact unrevoked Support. Owner/test subject does not self-grant. No case/queue assignment is implied by the grant.
5. Use only separately approved safe fixtures and minimal audit-write scope for list/detail/history/RLS acceptance. Retention-trigger pair dependency still blocks generic case creation; no existing real cases are adopted. Keep mandatory transport evidence unresolved without re-investigating it here. Only then formal admission/server-gate activation and real UI acceptance.

**Exact next action needed:** the owner must approve a concrete one-account manual review/execution procedure with Ahmad's review channel/evidence handling and a named authorized executor, explicitly resolving any combined reviewer/executor duties. In the same bounded design decision, authorize implementation/rehearsal of the missing restricted Support grant mechanism and name the supported pre-grant Auth/MFA interaction. This is not permission to create/grant/enroll yet; after verification, execution must be explicitly authorized. Another nominal custodian account or broad staff role is not the next step.

### Actual outcome / preservation

Ahmad's nomination is recorded in the existing ignored preparation request (`tmp/phase9-step2/support-test-account-request.json`) with review_completed=false and no executor/writer identity or provider UUID invented. No signed approval or completed MFA attestation was fabricated. No Supabase/SQL/Auth/Management call, account creation, grant, MFA enrollment, fixture/action, backend/frontend code change, QR operation, protected Support/Finance/Phase4 Orders change or test rerun in this assessment. Only this tracker and local preparation request updated. All three APIs **NOT ADMITTED**, live gate **DISABLED**; real Support acceptance remains blocked, Phase9 not complete, no Phase10.


## Phase 9 — final Support provisioning procedure / self-grant decision (2026-10-24)

Current decision supersedes the earlier nomination-only status. The owner now confirms personally controlling the supplied test account and proposes executing its grant. **That arrangement is prohibited by BTR-01's no-self-grant rule.** Ahmad's independent approval cannot waive it, and another Auth login for the same human does not supply independence. No account, role or MFA change was attempted.

Concrete procedure and contract-change proposal: [SUPPORT_TEST_ACCOUNT_PROVISIONING_PROCEDURE.md](../docs/SUPPORT_TEST_ACCOUNT_PROVISIONING_PROCEDURE.md). Private unsigned packet: tmp/phase9-step2/support-test-account-request.json, request SR-SUPPORT-DEV-84bcdd96-522d-4953-8f6c-a899dde084ba. Contains approved target email, Support-only scope, proposed people, preparation timestamp, empty email/MFA/authority/signature evidence references and expiration/revocation/cleanup conditions. Ahmad has NOT signed or completed review. Proposed signed-document/archive process and24-hour approval window are proposals requiring selection/approval, not an installed trusted channel. All live permission flags remain false.

| Requirement | Actual result |
|---|---|
| Owner as requester and executor | Not universally prohibited for a different subject, but ownership supplies no execution authority. **Present arrangement FAILS because owner controls subject.** |
| Ahmad as off-app reviewer | Designated; no application account automatically required; genuine identity/channel/independent signed review still missing. No security_admin/superadmin grant. |
| Restricted grant writer | **NOT IMPLEMENTED.** User's explicit stop condition applies: Security Specification Task2.3B and ops runbook leave authority/expected-state/idempotency/encrypted receipt/audit mapping and fencing contracts unapproved. No new SQL/API/migration or policy bypass. |
| Offline rehearsal | Entire existing staff policy test and pytest configuration inspected: in-memory only, standard library/pytest, no conftest files found or provider/database setup. Command: backend/.venv/Scripts/python.exe -B -m pytest backend/tests/test_staff_provisioning_policy.py -q -p no:cacheprovider. **34 passed in0.17s.** |
| Rejection/replay/rollback/concurrency | Existing synthetic cases passed for missing approval/email/MFA/authority, self-grant, stale/replayed/conflicting commands and simulated atomic rollback/last-custodian serialization. Not a real writer or PostgreSQL concurrency result. |
| Exact email/UUID/wrong executor/signature/audit authenticity | **NOT EXECUTED:** live exact-account/authority/signature/audit/receipt contract and implementation do not exist; generic fixture labels cannot prove these. |
| Genuine Auth/MFA/role/RLS/API/UI acceptance | **BLOCKED / NOT EXECUTED.** No live identity creation, enrollment, grant, case fixture or test account session. |
| Three metadata endpoints / frontend live gate | **NOT ADMITTED / DISABLED**, unchanged. |

**Exact next decision:** approve a bounded BTR-01/runbook addendum resolving the owner-controlled subject versus owner-account exclusion and naming a genuinely different, authorized grant executor; alternatively select a different-human test subject and approve its email. Ahmad remains proposed review-only unless separately appointed/verified; his designation alone does not authorize execution. Approve the specific trusted archive/signature/revocation verification, provider evidence interaction, least-privilege writer authority, expected-state/lock/fencing, atomic audit and encrypted idempotent receipt mappings laid out in the procedure before writer coding. Do not interpret this as authorization for an unrestricted INSERT or a self-grant exception.

After compliant design, implementation and disposable database/human rehearsal, request separate exact cloud authorization for the sole subject's official signup/email verification and genuine MFA, narrowly scoped subject evidence reads, one reviewed Support grant with atomic audit/receipt, and grant verification. API acceptance additionally needs approved access-audit writes and safe fixtures; no QR-dependent creation shortcut. Upstream transport evidence remains an existing infrastructure acceptance item; no renewed TLS investigation here.

Files changed for this task: the new procedure, this tracker and the ignored preparation JSON only. No remote contact, SQL, migration, cloud write, live account/factor/role change, application code change, protected Support/Finance/Orders or QR change. Phase9 incomplete; no new subdivision or Phase10.


## Phase 9 — proposed BTR-01 development exception amendment (2026-10-24)

Owner authorized **preparation**, not execution, of a one-subject development self-grant exception. Created [BTR-01-DEV-SUPPORT-20261024 v1.0 DRAFT](../docs/BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.0_DRAFT.md), with restricted grant implementation plan and exact review/approval gates. Original BTR-01 and Security Specification remain unchanged; prior self-grant decision is preserved. Added a pending-amendment cross-reference to the existing provisioning procedure. No additional roadmap phase.

| Requirement | Actual status |
|---|---|
| Exact environment/subject | Draft pins project fhuxryfkfrvycsojkzvq (known reference fingerprint17e54a8be1b7), expected Supavisor endpoint/database and the sole previously approved email. Verified against local configuration only; no remote call. Provider subject/executor UUIDs remain unverified/unbound. |
| Owner as controller/requester/executor | **PROPOSED narrowly scoped exception**, not yet ratified; does not confer database privilege or alter production prohibition. Existing owner account/grants untouched. |
| Ahmad | Independent off-app reviewer; actual verified channel/key binding, signature, evidence review and approval still absent. No staff account/role assigned. |
| Scope | support only, own assigned/redacted unassigned intake, current-assignee history; metadata-only privilege fence required, no assignment/case mutations or protected API use. |
| Expiry | Proposed min(commit+24h,2026-11-07T18:59:59Z); packet expires min(signature+24h,hard sunset). Actual API/database expiry enforcement and authenticated historical revocation must be designed/reviewed/implemented; scheduler or packet date alone insufficient. |
| Writer/DB dependencies | **NOT IMPLEMENTED.** Exact least-privilege executor, trusted verifier/archive/revocation, state/lock mapping, additive one-use grant/expiry storage, audit/encrypted receipt and central scope/expiry enforcement require review. No RLS weakening or QR policy changes permitted. |
| Tests | None rerun for documentation-only work. Prior34 synthetic rehearsal tests do not validate the proposed exception, genuine MFA or PostgreSQL atomicity/RLS. Future focused offline/disposable-PG/human review and revocation tests are specified in the draft. |
| Account/grant/permission changes | **NONE.** No SQL, remote contact, migration, email, identity/factor/grant/fixture or application code changes. |
| Admission/live gate | **NOT ADMITTED / DISABLED** for all three metadata endpoints. |

**Exact next review:** owner reviews/ratifies the identified v1.0 amendment and its project/subject/self-grant/scope/expiry limits; Ahmad independently reviews and actually signs through the selected verified channel. Then approve the exact implementation specification and isolated rehearsal, including any separately reviewed schema/permission design, before coding a writer. Later authorize subject-only official signup/email/MFA/evidence checks and then the exact single grant/audit/receipt transaction separately; draft preparation authorizes neither. No secrets or signatures are fabricated. Genuine Auth/MFA/assignment/abuse/RLS/API acceptance, safe fixtures and required upstream transport evidence remain outstanding; Phase9 incomplete, no Phase10.


## Phase 9 — owner-approved v1.1 exception and restricted implementation (2026-10-24)

**Current status: PHASE 9 READ-ONLY SUPPORT INTEGRATION — IMPLEMENTED; EXTERNAL APPROVAL OR ACCEPTANCE PENDING.** The remaining approval is exact cloud-operation authorization, not Ahmad's approval. The owner explicitly withdrew third-person review for this single development subject. [BTR-01 exception v1.1](../docs/BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md) is the current owner-approved scoped policy; v1.0 and original BTR-01 history are preserved. No independent custodian/signature is required or fabricated for this workflow; all other production/general/lifecycle/finance custody rules retain their original meaning.

### Actual implementation

- Restricted local command: backend/app/support_provisioning_cli.py and services/support_provisioning.py. Fixed project/email, support only, exact bound subject/executor UUID, owner intent and reviewed-source hashes, closed packet, no generic role interface. No real owner command manifest/credential/UUID binding supplied. Default/template/check are offline and cannot grant.
- Dedicated fixed technical login safereturn_support_command is required (not created); only SET ROLE safereturn_support_provisioner may be appointed. No runtime/migration credential fallback, no broad service key. Command URL and database session checks reject a different/broad/inheriting login or extra memberships. Certificate and hostname verification with the existing validated CA remains required.
- Existing JWT verification and provider-side exact-subject email/session AAL2/verified TOTP/account epoch checks; recent signed AMR within300s. Caller evidence strings/booleans cannot replace genuine provider checks. No password/OTP/seed handling by the CLI; private bearer input is local operator transport only, never chat/arguments/logs/source.
- Additive Alembic source0044_support_dev_exception after0043: empty singleton consumption/expiry and encrypted receipt storage, fixed grant/revoke functions and restricted NOLOGIN database role, atomic generated audit/receipt, one-use/replay/lock/rollback protections and restrictive Support case/history SELECT policies. No historical migration changed, no new staff roles/permissions or fixtures seeded. **NOT APPLIED.** Cloud head remains previously verified0043; local source head is now0044 pending approval/application.
- Central Auth route fence for only the configured exception UUID, final current-state checks, and authenticated own-session loopback readiness endpoint. Startup code fingerprint and actual binding/fence must match before CLI grant/revoke; a stale/disabled backend fails readiness. Fixed metadata scope excludes quarantined/mutating/Orders/QR paths without changing their handlers/policies. ASGI tests caught and corrected this FastAPI version's relative route-template behavior.
- Real provider pre-grant enrollment adapter at /dev/support-onboarding, development/loopback/fixed-project/email only, disabled by default and exact UUID bound before enrollment. Uses official Supabase signup/email flow and SDK TOTP enrollment/challenge/verification; no temporary role or factor deletion. Provider enrollment image remains only in the authenticated subject browser; raw seed/URI/password/token/code is not logged or returned as packet evidence. No real flow invoked.
- Effective lifetime <=24h and hard sunset2026-11-07T18:59:59Z (23:59:59 Pakistan time). Backend and relevant database Support read fences deny on expiry/revocation without a scheduler. Historical role cleanup/revoke requires the reviewed command; no promise of instantaneous offline withdrawal or automatic account/factor deletion.

Operational contract, exact credential/manifest/readiness setup and mutation boundaries: [ops/SUPPORT_DEVELOPMENT_EXCEPTION.md](../ops/SUPPORT_DEVELOPMENT_EXCEPTION.md). General staff runbook/security specification/provisioning proposal now cross-reference the narrowly scoped exception; original BTR-01 is unchanged.

### Tests actually executed

| Check | Actual result / limits |
|---|---|
| New restricted provisioner/fence tests | **73 passed**. Closed owner intent/schema, project/email/role/UUID/expiry/AMR denial, real AEAD receipt rollback/binding, actual ASGI route/final guard, mocked loopback readiness and SQLite-adapted actual subject-only provider predicates. No real Auth/PostgreSQL transaction proof. |
| Existing Support metadata / staff rehearsal | **44 +34 passed**, alongside73 new tests (151-test final focused run). |
| Existing JWT/auth and lifecycle regressions | **142 passed** in separate final run. Synthetic public-key transport/in-memory or SQLite setup; inspected, no live database/provider. |
| Existing frontend Support metadata checks | **73 passed**; disabled gate makes zero auth/staff/upstream calls. |
| Existing Support browser checks | **23 passed**; isolated intercepted requests only, including list/detail/history/filter/pagination/loading/empty/error/disabled-gate behavior. Not real Cloud browser acceptance. |
| New onboarding adapter checks | **12 passed**; mocked provider only, no account/factor mutation. |
| TypeScript / scoped Ruff | **PASSED**; no new type/lint failure remains. |
| Safe real preparation dry-run | Default/template generation produced incomplete, non-executable packet. --execute without packet blocked PACKET_REQUIRED; actual offline packet check blocked TRUST_NOT_CONFIGURED before JWT/network/database. Expected fail-closed outcomes, not successful provisioning. |
| Migration ordering | Alembic ScriptDirectory (no env.py/database execution) confirms sole local source head0044_support_dev_exception. DDL/ACL/RLS/concurrency/atomicity/expiry on actual PostgreSQL **NOT EXECUTED**. |

Distinct isolated coverage:293 backend tests and108 frontend/browser checks =401; includes preserved original140 +34 rehearsal checks. These totals are not live acceptance. Protected support_cases.py, financial_disputes.py and order_metadata.py hashes match recorded baselines. Existing frontend Support implementation/gate, verified runtime TLS/configuration and standalone PostgreSQL17.11 cluster remain unchanged.

### Current acceptance and exact next action

| Requirement | Status |
|---|---|
| v1.1 policy / removing Ahmad dependency | **APPROVED / DONE**, single development exception only. No third-person approval is pending. |
| Restricted source implementation / isolated checks | **IMPLEMENTED / PASSED** as above; real database behavior not yet verified. |
| Cloud migration / restricted login appointment | **NOT EXECUTED — exact authorization required** under the latest user boundary. |
| Dedicated identity / genuine email and MFA | **NOT VERIFIED / no account or factor created by this task.** Exact provider UUID unknown; no identity enumeration. |
| Live grant / revocation | **NOT EXECUTED**, no live owner operation permit supplied or authorized. |
| Genuine Auth/MFA/queue/assignment/abuse/RLS/API acceptance | **BLOCKED**, cannot substitute fixture-only results. |
| Safe Support cases/history fixtures | **NOT VERIFIED**; no existing real data adopted, no QR-dependent creation. |
| SSL enforcement / upstream transport evidence | Existing infrastructure acceptance item remains OPEN where mandatory; no repeated TLS architecture audit. |
| Three metadata endpoints / existing live Support gate | **NOT ADMITTED / DISABLED**, no allowlist or activation changes. |
| Real Cloud UI acceptance / Phase9 completion | **NOT EXECUTED / NOT COMPLETE**; no Phase10 or new roadmap subdivision. |

**Next exact operation package for approval:** apply only the reviewed0044 source to project fhuxryfkfrvycsojkzvq and appoint only the fixed restricted technical command login/membership via an approved secret mechanism; no broad credential/grants. Separately authorize sole-subject official signup/email/MFA and minimal evidence inspection, bind the dedicated UUID and verify the running backend fence. Authorize explicit same-project subject-scoped rollback-only PostgreSQL tests (or an approved disposable database) before the one committed grant. No Docker/local Supabase workflow or new cloud project is imposed. Finally authorize the exact owner packet/grant/expiry/audit/receipt operation and permitted access-audit/fixture acceptance scope. No case-creation shortcut or live activation by implication.

Only after genuine acceptance and formal admission may the existing development server-side Support gate be enabled and actual list/detail/history UI verified. Private preparation artifacts under tmp/phase9-step2 contain no active approval, credential, MFA secret or forged third-person evidence. Source0044 and pending exact owner intent are concrete reviewable outputs, not permission to execute them.

### Migration 0044 execution readiness — actual continuation (2026-10-24)

**NOT READY FOR EXECUTION.** This updates the existing Phase9 operation; no new task/subdivision was opened. The user authorized completion of readiness checks and real testing only on an authorized isolated disposable database, while excluding development migration application, credentials/identities/Support grants, QR APIs, frontend activation and Phase10. Those boundaries were preserved.

| Check | Actual outcome |
|---|---|
| Hashes versus prior deployment review | MATCH, no0044 SQL/Python edit. SQL17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d; wrapper67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30. |
| Development catalog | Actual verified-TLS READ ONLY transaction, then ROLLBACK: PostgreSQL17.11, sole installed0043; command/provisioner roles/membership absent, command DSN unconfigured, exception tables absent. Required helper ownership/search_path/default ACL metadata and existing Support policies recorded. No domain/Auth/Storage/QR rows or QR functions accessed. |
| Existing RLS/grants | Selected protected application/Storage relations have RLS enabled. No PUBLIC relation/column ACL in public/auth/storage; PUBLIC database CONNECT/TEMPORARY and public-schema USAGE persist. Three PUBLIC sr_* trigger helper EXECUTE entries recorded; no protected QR command entry among that list. This does not prove future login's full effective permissions. Shared grants were not changed. |
| Isolated environment discovery | Configured test URL is the same development project, not disposable: rejected without testing. Portable PostgreSQL17.11 available; Docker/Supabase CLI not on PATH, standard Docker install absent. Preserved55439 standalone skeleton lacks managed Auth and is not adopted/connected/restarted. No suitable authorized isolated target found. |
| Real PostgreSQL security/rollback/concurrency/expiry/replay tests | **NOT EXECUTED**, no fabricated PASS. Existing namespace-rewriting/fake-Auth fixture was not run. Prepared assertion matrix covers actual SQL/wrapper rollback/lock timeout, real-login role/table/function denial, atomic audit/receipt failure, same-key replay/one-use, RLS scope/clock expiry/revoke, concurrency and session closeout. No validated new real-PG test driver is claimed. |
| Credential requirements | Defined operator/SYSTEM ACL + current-user DPAPI storage, fixed verified-TLS session-pooler endpoint, unique SCRAM credential, <=60-minute per-operation validity, same-role rotation and NOLOGIN/password/membership/EXECUTE/session closeout. Numeric packet/receipt retention and actual key/storage custody still need owner decision before live grant. No credential, file/ACL at the proposed private path or role appointment created. |
| Recovery preparation/verification | Added backend/scripts/support_0044_recovery.py: hash-only default PASSED, scoped Ruff PASSED, real READ ONLY0043 assessment returned0044_NOT_INSTALLED. Existing runbook now gives executable inspect/offline-check/revoke commands and failure/replay/expiry/forward-repair decisions. Post-installation/positive command/revoke/rollback paths remain untested. No destructive downgrade or broad restore. |
| Other tests | Historical134 focused offline checks were not rerun, and no unrelated suite executed. |

Evidence: `tmp/phase9-step2/readiness-0044-evidence.json`, generated by the catalog-only `inspect_0044_readiness.py` at2026-10-24T07:00:29Z. Expanded findings and exact unresolved gates: [deployment review](../docs/PHASE_9_MIGRATION_0044_DEPLOYMENT_REVIEW.md), [existing operations runbook](../ops/SUPPORT_DEVELOPMENT_EXCEPTION.md#migration-0044-readiness-completion-review--2026-10-24).

**Exact missing approval:** one <=24-hour **no-data Supabase preview branch** `sr-support-0044-readiness`, distinct verified reference, approved provider charge, no merge/seed/customer copy/parent mutation, reviewed data-free0043/custom-role baseline and unchanged0044 installation/rollback only on that branch. Availability is not assumed; if unsupported, stop before proposing an empty managed test-project substitute. Positive tests also need an explicit disposable-only exception authorizing the short-lived restricted test credential, genuine owner-operated fixed-email/TOTP subject and exact test-only grant/revoke/audit/receipt transactions, with any additional fixtures separately listed. No target/identity/grant on fhuxryfkfrvycsojkzvq is authorized by that package. The live CLI's project pin remains intact.

Final Cloud execution authorization is **WITHHELD** until real test outcomes and the guarded deployment/credential package pass review. Candidate appointment now specifies CONNECTION LIMIT1 and explicit public-schema USAGE; source0044 hashes are unchanged. No application schema/migration, staff grant, Auth identity/factor, Storage record, customer/Orders/QR record or frontend configuration changed during this continuation. Support metadata endpoints remain NOT ADMITTED, live gate DISABLED, Phase9 incomplete and Phase10 not started.

## Phase 10 — Notifications Management (2026-10-24)

**IMPLEMENTED — ISOLATED CONTRACT/BROWSER CHECKS PASSED; LIVE ACCEPTANCE BLOCKED.** Owner explicitly paused Phase9 and authorized only existing Admin Notifications integration. Phase9 status is **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED.** No Support/provisioning/0044 changes or new infrastructure environment were made. Phase10 is not live-complete; Phase11 was not started.

### Independently traced API budget and admission

| Operation | Source-chain decision | Integration/admission |
|---|---|---|
| GET `/api/v1/admin/notification-outbox` — API-101 | SOURCE-SAFE candidate. Actual router in main.py, notification_operations.notifications -> require_staff(operations,security_admin) -> bounds/page_cursor -> sr_notification_metadata. Metadata definer checks sr_is_staff; reads notification_outbox/notification_attempts; sr_notification_retry_gate optionally reads finder_messages/auth.users. No QR/pair lookup. | Strict GET contract implemented for list and detail-by-id/history. **NOT LIVE ADMITTED**; notificationReadAdmitted() is literal false. |
| POST `/api/v1/admin/notification-outbox/{id}/retry` — API-102 | SOURCE-SAFE candidate with externally consequential mutation. require_staff -> bounded key validation -> actor/operation/key advisory lock -> encrypted idempotency receipt replay or sr_notification_retry -> row lock/expected attempt check/retry_gate -> outbox status+next attempt/audit/receipt in API transaction. Worker chain detailed below; no QR/pair work reachable. | Strict POST contract and controlled dialog implemented for isolated acceptance only. Mutation acceptance/activation approval remains pending. **NOT LIVE ADMITTED**; notificationRetryAdmitted() is separately literal false. No real retry issued. |
| GET `/api/v1/me/staff-security` | Existing authenticated own-role/MFA/capability bootstrap; no QR operations. | Reused through existing staffState before and after the outbox request. Not a generic API allowance. |

The original corrected Products allowlist, all70 QR-pair excluded/quarantined operations, Phase4 independent Orders endpoints and Support non-admission remain unchanged. No notification candidate was found source-unsafe, so neither is falsely marked QR-quarantined. Eligible source is distinct from live admission. Arbitrary paths, generic Support/Finance/Orders, worker/provider APIs, Compose/Bulk Send/SMS/Email Send, recipient lookup and invented notification-detail APIs are excluded. A UUID/query/view flag cannot mount the older console or bypass either server gate.

### Complete reachable security/worker trace

Router registration: app/main.py includes notification_operations_router at /api/v1; exact decorated methods are API-101/102. CatalogRoute only formats errors; imported fulfillment helpers are bounds/page_cursor/paged, not fulfillment/detail operations. Base authentication validates JWT signature/issuer/audience/type/expiry and current provider session/email/AAL2 through sr_account_session_state (0030), Auth/account-security state and current staff_roles. Explicit Operations or Security Admin is required; Support, Finance and Superadmin alone do not inherit this authority. The existing Phase9 exceptional-subject fence is unchanged and cannot confer Notifications access.

0020 notification metadata/retry routines are SECURITY DEFINER with pg_catalog search_path and API-only entry EXECUTE; helper routines have no public/browser delegation. sr_is_staff -> actor/MFA/staff_roles. Definer-owned direct outbox/attempt reads do not use the broader API outbox SELECT policy's sr_can_message branch; verified ownership/source/RLS fidelity remains a deployed acceptance prerequisite. Metadata returns only the minimized event/attempt projection and fixed current-template metadata. No recipient reference, address, related record, provider ID, payload or body is projected. Channel is **not a response field**: only finder_message.created is recognized as an email event from the actual worker code; other events display Not provided.

Retry gate (0020): dead/supported event, attempt budget, first attempt within23h, no successful attempt, reviewed safe transient/recoverable failure, matching undeleted finder-message recipient and eligible confirmed/nonanonymous/unbanned Auth user. sr_notification_retry locks the exact outbox row, compares expected_attempt_count and updates only status/next_attempt_at, then records safe audit metadata. Existing lease-transition trigger is worker-context validation; 0014a sr_outbox_relation validates immutable event/recipient association and write-once recipient snapshot using finder_messages only. Deferred sr_finder_outbox_check preserves finder-message/outbox association, without invoking public finder submission or querying QR rows. Idempotency guard/RLS and audit JSON guard concern actor/safe event data only. Context dependency finishes transaction before protected response; encryption failure rolls it back. Python replay/crypto was exercised, SQL concurrency was not.

Queued retry can later execute workers/notifications: _claim_one leases outbox and inserts an attempt; _prepare_recipient -> 0014a sr_notification_recipient reads outbox/finder_messages/auth.users under lease and writes encrypted owner-email snapshot; existing AEAD decrypts it; provider.send can call Resend; _finish updates attempt/outbox and the same notification-only triggers. No QR lookup/allocation/inspection/credential/export/lifecycle, Support handler, Finance handler or original Orders-list request is reachable in this reviewed notification chain. The worker/provider was **not started or called** by integration. API202 means queued, `sent`/attempt success means recorded provider acceptance, never proof of inbox delivery or returned property. Full deployed nested-SQL/provider acceptance remains unverified.

### Existing screens, controls and files

Existing `/admin/notifications` and `/admin/notifications/[id]` now mount the same AdminNotifications design with AdminPage/AdminShell authorization. Removed their mock/legacy `?view=live` switch and synthetic-ID adoption; no second Notifications application was introduced. Legacy components/notification-admin.tsx remains unmounted; its old live/fixture suites were not used. No localStorage/sessionStorage notification data or fallback fixtures remain in the active render path.

Controls: supported backend status filter, exact notification UUID filter, opaque cursor Next/Previous, refresh, loading/empty/error/denied states, status/channel/attempt count/timestamps/safe failure code, detail-by-id and bounded older attempt history, current-template metadata without historical-version fabrication, page-local derived channel filter (never sent as unsupported API query), honest page count instead of fabricated totals. Detail fields wrap on mobile; list table scrolls within its region. Links disable prefetch. Recipients/message contents/provider IDs remain unavailable. No Compose/Bulk Send/Email/SMS actions were added.

Retry: unavailable by default, even for eligible rows. Isolated approved-contract branch has a modal, reviewed reason allowlist, unchecked confirmed=true requirement, expected count snapshot and a UUID idempotency key. Focus starts on Cancel; Tab stays inside the dialog; Escape cancels before submission. Unknown result freezes count/body/reason/key in memory and offers only explicit same-request reconciliation; no automatic retry or delivery-success claim. 412/409 refusal refreshes eligibility and requires a new human review; terminal success says only Retry queued. Role preview never grants real permission.

Changed implementation files:

- app/admin/notifications/page.tsx; app/admin/notifications/[id]/page.tsx; app/admin/notifications/api/route.ts.
- components/admin-notifications.tsx; components/admin-notifications.module.css.
- lib/admin-notification-contract.ts; lib/api/notification-relay.ts; lib/notification-gate.ts.
- tests/notification-fixture.cjs; tests/admin-notifications-screen19.spec.ts (replaces historical demo tests); scripts/test-notifications.cjs; playwright.notifications.config.ts.
- backend/tests/test_notification_frontend_contract.py (new isolated actual-router checks; **no backend application handler/schema/migration edited**).
- This tracker and the existing inventory/mapping/plan Phase10 admission records.

Relay security: gates precede session/staff/upstream work, including direct legacy API-route invocation. Reuses verifiedSession, staffState and backend authorization; requires current MFA, explicit role and notifications.manage, then rechecks staff after response. Fixed method/path/query/body budget; UUID/enum/strict integer/key validation; rejects unknown/duplicate queries, body extras, wrong-origin/cross-site requests and unsupported encoding. Request body<=2048 bytes, upstream JSON<=262144 bytes, content-type/status/schema/ID binding checks, ten-second upstream deadline, no redirects, no-store and nosniff/no-referrer. Error bodies/transport/provider secrets never pass through. Separate retry gate denies before Auth/network when reads alone are admitted.

### Tests and actual outcomes

Fixtures/setup were inspected first. New browser/Node transport is in-memory and denies any backend path except exact outbox GET/retry POST; it never loads .env, opens a server, reads a database, creates identities or invokes a provider. New backend harness mounts only the actual notification router, real JWT/AEAD, public synthetic JWKS via httpx.MockTransport and scripted SQL; no migrations/Auth schema/fixtures/engines. Existing test_notifications provider requests and worker database are mocked. Existing integration/test_notification_operations.py and old notification-operations/notification-privacy browser suites require fixture mutation/quarantined setup and were **not run**. No new infrastructure workflow or Phase9 tests.

| Verification | Result / limits |
|---|---|
| `node scripts/test-notifications.cjs` | **74 passed**: closed request/response contracts, auth/MFA/forbidden roles, filters/cursors/detail/history, invalid reason/attempt/key/confirmation, idempotency replay/conflict, stale412, request/response limits, error redaction, gate zero-call behavior, final staff denial, prohibited-route budget. In-memory transport, not DB concurrency. |
| `npx playwright test --config playwright.notifications.config.ts` | **25 passed in the final run**, including the wrapping mobile detail layout and existing compiled Admin CSS. Actual React component + actual server relay through isolated transport: list/empty/loading, filters/pagination/refresh/history, redacted failures, forbidden roles/MFA, disabled SSR/hydration effects, controlled retry, stale attempt, lost committed response/same-key reconciliation,1366/768/375 widths, no browser storage. Initial first-case timeout was an ambiguous wrapped-select label; explicit accessible names fixed it. No unresolved failure. |
| Backend focused check | **46 passed**: tests/test_notification_frontend_contract.py + tests/test_notifications.py; actual API registration/model/role/email/MFA/list/pagination/retry/JWT/AEAD/scripted rollback checks and mocked provider/worker regressions. No PostgreSQL/RLS/concurrency or real sending proof. |
| TypeScript | **PASSED** (`npm run typecheck`), including the changed pages and browser tests. |
| Scoped backend Ruff | **PASSED** for new test file. |
| Visual inspection | Mobile metadata rendering inspected; replaced wide detail summary with wrapping facts. Screenshots remain synthetic under tmp/phase10-notifications, never live account/evidence/provider data. |

### Live status, blockers and next module

**Live integration: NOT EXECUTED / NOT ADMITTED; both gates remain disabled.** No appropriate privately supplied live session and safe outbox/attempt fixture were established for this operation, and deployed notification helper/owner/RLS/trigger behavior, real concurrent retry, provider eligibility/suppression/domain/copy and side-effect acceptance are unverified. No existing users or outbox were enumerated/adopted as fixtures. Working verify-full Supabase runtime architecture is reused by the relay; no .env/TLS investigation, credential/production Auth setting, Cloud database reset/migration/new0044 application or infrastructure target was introduced.

Remaining blockers are recorded acceptance/admission for metadata, and separately approved exactly scoped retry/real-provider acceptance with authorized test identity and safe data. A source-safe operation is not declared live-safe from scripted tests. Do not enable gates or use old routes as a workaround. Phase9 remains paused with its original Support endpoints/frontend/gate/not-admitted status, unapplied0044 and provisioning restrictions intact; Phase4 Orders, pricing, QR/Support/Finance handlers and other Admin modules were not edited.

Recommended next module: **Audit Logs metadata**, after a separate per-operation source/allowlist review. It has not been started. Phase11 is not authorized by this report.

## Phase 11 — Privacy Requests & Export Review (2026-10-24)

**PHASE 11 — IMPLEMENTED; LIVE ACCEPTANCE PENDING**, limited to source-safe export-request metadata. API-327 decisions remain quarantined and are not implemented as an actionable workflow. Owner selected OptionA: preserve Phase9/10 implementation and disabled gates, continue remaining modules, consolidate pending live acceptance in Phase14. No Phase9/10 acceptance restarted, infrastructure created,0044 applied or Phase12 begun.

### Independently verified candidates and exact budget

| Candidate | Fresh source-chain result | Frontend disposition |
|---|---|---|
| API-330 GET `/api/v1/admin/privacy/exports` | ELIGIBLE/SOURCE-SAFE metadata, under reviewed definer ownership/RLS semantics. Actual main.py privacy_exports_router registration -> listing -> verified/email/MFA/current Security Admin guard -> bounds/page_cursor ->0022 sr_export_list -> sr_is_staff + sr_export_authorized (latest0030) + sr_export_status. No export worker, QR helper/relation or audit INSERT is reached. | Prepared through the existing admin API route, now a dedicated GET-only metadata relay. Server gate privacyMetadataAdmitted() is literal false. **NOT LIVE ADMITTED** pending Phase14 evidence. |
| API-327 POST `/api/v1/admin/privacy/exports/{request_id}/decisions` | **QUARANTINED, unchanged.** Approval changes status to approved, making the request claimable by privacy_exports worker -> snapshot -> sr_export_page -> `tag_pairs` and `order_item_qr_uses` (pairs/occurrences).0043 adds standalone categories but preserves those existing pair branches. | No decision dialog or mutation transport. Legacy admin POST/PUT/PATCH/DELETE/HEAD/OPTIONS return405 before Auth/upstream work. Reject/escalate are not independently exposed or admitted; no frontend payload workaround. |
| Supporting own GET `/api/v1/me/staff-security` | Existing verified own-role/MFA/capability bootstrap, no QR operation. | Reused before/after safe metadata response via staffState. No new bootstrap or privilege source. |

No other SafeReturn operation is permitted by this module. Customer request/status/download-grant/download API-325/326/328/329, Support/Finance handlers, generic Orders list, case context/provisioning, export/erasure workers, storage/provider calls and QR routes remain outside the admin budget. Original corrected Products allowlist and70 exclusions/quarantines are preserved. API-327 was already quarantined; historical inventory counts are not inflated by counting it again. Source eligibility is not live admission.

### Authorization, schemas, revision and side-effect review

API-330 requires explicit `security_admin`, confirmed eligible current provider account/session and verified MFA through existing JWTVerifier/get_auth_context/require_staff. Superadmin, Operations, Finance and Support alone do not inherit access. No recent-auth300s requirement is invented for this read endpoint. Backend own-session/epoch enforcement remains unchanged; the shared Phase9 fence cannot confer Privacy permission. Page uses existing AdminPage(capability=`privacy.exports`) and AdminShell; relay separately enforces current role+MFA+capability and rechecks staff after fetching. Client role preview is never authority.

sr_export_list is SECURITY DEFINER, pg_catalog search_path, delegated only to safereturn_api. It checks sr_is_staff, then reads privacy_exports with sr_export_authorized for each case. The current0030 authorization helper reads privacy_export_authorities, privacy support-case type/status/opener, staff_roles, reviewer Auth eligibility and both reviewer/authorizer account epochs (NULL issuance denies old untimestamped authority after invalidation). It does not call quarantined Support handlers, retention-admission mutations, sr_export_current, preflight, decision, grant, consume or page export helpers. sr_export_status projects stored request metadata and computes ready->expired using the database clock. Reading stored manifest metadata does not regenerate an export. Under source ownership semantics the definers bypass broader case RLS; deployed ownership/ACL/RLS/function fidelity is still an acceptance requirement, not proven by these tests.

Actual API-330 parameters: limit(default20,max100), optional opaque timestamp+UUID cursor. No status/id/customer/case filter or standalone admin detail endpoint is registered. Its response is `{items,next_cursor}`; each raw item has request_id,case_id,status,revision,scope_version,manifest_version,manifest_id,categories,created_at,ready_at,expires_at. Statuses: requested/reviewing/approved/building/ready/expired/rejected/escalated/held/retry. There is **no updated_at field** and no complete total. The dedicated relay validates the source shape, then forwards only eight fields: request_id,case_id,status,revision,scope_version,created_at,ready_at,expires_at. Entire categories/manifest IDs/counts/snapshot metadata are discarded, without traversing them or adding enrichment. No subject/customer identity, export payload, object key, checksum, receipt, provider locator or download link is sent to the browser or logs.

API-327 contract was inspected, not executed: UUID request/case IDs; explicit Security Admin and verified account/MFA plus signed authentication event within300s; current-case preflight/subject epoch before receipt replay; strict confirmed=true; expected_revision int1..2147483647; scope_version basic_v1; choices approve/reject/escalate; reason codes scope_reviewed/scope_not_supported/identity_review_failed/requires_review; Idempotency-Key through existing command helper.0030 sr_export_decide locks case/request, requires current case-bound authority and subject epoch, matches revision, rejects self-approval and invalid state, increments revision and appends decision+audit. Replay uses actor/operation/key serialization and encrypted receipts; Python/SQL failure remains transactional. Approval admits the pair-reading worker chain, so **the whole endpoint remains blocked regardless of revision, reason or selected choice**. No authority registry, case, approval, worker job, note or audit record was created. No positive/stale decision API behavior is claimed tested; only model validation and unconditional frontend rejection were exercised.

Privacy/security specification review preserved least privilege, separately established case authority, private storage/download controls, data minimization/no sensitive audit/error data and stricter default-deny exclusions. No legal identity-verification, erasure, disclosure, completion, download authorization or retention compliance is inferred from a metadata status/revision.

### Existing screens and implemented controls

Existing `/admin/privacy/exports` and `/admin/privacy/exports/[requestId]` reuse AdminPrivacyRequests/Admin UI cards, tables, badges, layout and styles. Active pages no longer mount legacy PrivacyExports/admin broad relay, `?view=live` console, browser mock requests, fake deletion/access queue or mock review-note mutations. The shared customer privacy relay/components were left unchanged and are not reachable from the admin pages.

Implemented: authorized export metadata list; supported request/case references, status/revision/scope and created/ready/expiry timestamps; bounded page size20/50/100; cursor Next/Previous; refresh; loading/empty/denied/redacted-failure states; page-local status/reference filters with explicit labels and no unsupported backend query; cursor-preserving request metadata details; unavailable actions with no fake buttons. Detail links carry only the source-page limit/cursor. A direct request URL searches **only the loaded authorized list page**, not a fictional detail API or automated directory scan. Missing data says “Request not present on this authorized page,” never a global404 assertion. Linked-cursor position is labelled and a refresh preserves it unless page size changes. Updated timestamp, global counts, case content, historical decisions/notes and export/download controls are unavailable.

Relay security: all non-GET methods are denied405 before authentication/body parsing; unadmitted GET is denied503 before session/staff/fetch. Fixed one-path budget and strict allowlisted limit/cursor query with duplicate/unknown rejection. Wrong-origin/cross-site GET, body/nonzero length and unsupported transfer/content encodings fail closed. verifiedSession, staffState before/after, backend security remain necessary. Upstream deadline10s, no redirects, JSON+200 only, rejects attachment headers, streamed response<=262144bytes, closed validated schema/IDs/timestamps/status/revision and fresh minimized projection. Responses use private/no-store, nosniff and no-referrer; upstream error bodies/details/credentials never pass through. Neither query flags, browser state nor environment variables can open the gate. Client uses abort/generation protection, clears stale records on loading/denial, and clears hidden-tab records. No personal export/browser-storage persistence.

### Files changed

- app/admin/privacy/exports/page.tsx; app/admin/privacy/exports/[requestId]/page.tsx; app/admin/privacy/exports/api/route.ts.
- components/admin-privacy-requests.tsx (existing screen replaced with real-contract implementation); existing module CSS reused without edits.
- lib/admin-privacy-metadata.ts; lib/api/privacy-metadata-relay.ts; lib/privacy-metadata-gate.ts.
- tests/privacy-metadata-fixture.cjs; tests/admin-privacy-screen20.spec.ts (replaces historical mock-screen tests); scripts/test-privacy-metadata.cjs; playwright.privacy-metadata.config.ts.
- backend/tests/test_privacy_admin_metadata.py; no backend handler/security/schema/migration changed.
- Existing inventory/mapping/plan and this tracker for the exact admission/quarantine/status record.

### Actual tests and preservation evidence

Fixtures/setup/teardown were inspected before execution. New Node/browser harness is fully intercepted and rejects every upstream method/path except exact API-330 GET; no .env, network service, Auth/DB fixture, worker or storage. Browser tests render actual React code and actual server relay through that in-memory transport. Backend harness mounts the actual privacy router with real signed synthetic JWT/JWKS mock and scripted SQL only; its request helper can address **only API-330 GET** and its SQL driver rejects export command/page/grant/consume/Support/Finance/QR/mutation statements. No positive decision API, database migration, installed RLS or worker executed. Existing live/customer/integration export/privacy suites were not run because their wider fixtures/workers/routes are outside scope. Phase9/10 acceptance tests were not rerun.

| Check | Actual result / limit |
|---|---|
| `node scripts/test-privacy-metadata.cjs` | **73 passed**: list/page limits/cursors/empty, unauthorized/forbidden/MFA/capability, final staff denial, origin/request guards, redacted statuses/transport failure, response size/type/attachment/private-extra rejection, eight-field minimization including nested payload/count canaries; every approve/reject/escalate/invalid or stale-revision POST blocked405 without upstream calls; gate zero-call behavior and active-path legacy/mock exclusions. |
| `npx playwright test --config playwright.privacy-metadata.config.ts` | **28 passed in the final run**. List/local filters/cursor and page-size navigation/refresh, loading/empty, detail source-page cursor, honest missing request, invalid ID/query, denied/MFA/role, clearance on authorization loss, sensitive-data rejection, disabled SSR/hydration/effects,1366/768/375 and RTL layouts, zero browser storage. No decision dialog or export actions mounted. |
| `.venv/Scripts/python.exe -B -m pytest tests/test_privacy_admin_metadata.py -q -p no:cacheprovider` | **19 passed**: real API-330/JWT/model/registration/paging/auth/redaction and scripted authority absence; offline Decision schema negative cases only; source graph verifies source-safe list versus pair-reading worker. An initial source assertion named order_pair_units; corrected to the actual order_item_qr_uses occurrence relation, then all19 passed. This was a test assertion correction, not a backend change or safety bypass. |
| TypeScript | **PASSED**, including the new relay/pages and browser tests. |
| Scoped backend Ruff | **PASSED**. |
| Protected-file hash comparison | **25 checked,0 changed**:0043/0044, provisioning, Support/backend protected handlers, Support gate/frontend, Phase10 gates/contracts/relay/component/pages, Phase4 Orders, shared customer Privacy relay/route. Snapshot: tmp/phase11-privacy/protected-before.json. |
| Visual inspection |375px request details inspected; existing Admin design wraps metadata with no document overflow. Synthetic screenshots under tmp/phase11-privacy; no live personal data. |

### Live acceptance and remaining blockers

API-330 live routing is **DISABLED / NOT ADMITTED** pending consolidated Phase14 verification of source-equivalent installed functions/ownership/ACL/RLS, real current Security Admin/MFA/case-bound authorization/epoch behavior, pagination and data-minimization under actual safe fixtures. No private session, case authority or customer request was created/enumerated/adopted. No live acceptance, cloud read/write/reset/migration, new infrastructure, TLS investigation or provider/storage operation was performed for Phase11.

API-327 is not merely awaiting a frontend switch: its approved branch still reaches prohibited pair exports. It remains unavailable under this exclusion policy; an independent approved backend contract or an explicit future policy change would be required before considering it, not a reject-only payload, borrowed Support endpoint or arbitrary approval. Phase14 acceptance does not itself lift quarantine or authorize export/download/erasure.

Phase9 remains **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED**. Phase10 Notifications remains implemented with both live gates disabled.0044 remains unapplied. Protected25-file hashes match. Live acceptance is consolidated for Phase14 by owner direction; no Phase14 environment/workflow was started here.

Recommended next phase: **Phase12, Storage metadata only**, subject to its own exact source/allowlist review; generic retention holds/releases/cleanup retries remain quarantined. **Phase12 has not started.**

## Phase 12 — Finance Sheet Sync and Storage/Retention — 24 October 2026

**PHASE 12 — IMPLEMENTED; LIVE ACCEPTANCE PENDING applies to API-238 Finance metadata, the controlled API-239 retry implementation and API-242 Storage metadata only. API-243 hold creation, API-244 hold release and API-245 cleanup retry are NOT IMPLEMENTED / QUARANTINED.** All six independent production admission functions are literal false. No live request, Cloud project operation, migration, provider mutation, account or infrastructure creation occurred. Phase14 remains the consolidated live acceptance stage; it does not automatically authorize quarantined operations.

### Source review and corrected strict allowlist

Reviewed the inventory/mapping/plan, corrected exclusions, approved API Contract, Technical Design, Security/Privacy and Finance/Storage requirements. Historical 162-operation counts, corrected 70 exclusions/quarantines and 14-operation Products budget remain historical; this addendum records independent source eligibility, not live admission. Existing main.py registers retention.router under /api/v1. Exact route contracts and service chains are in backend/app/api/v1/retention.py; no backend implementation or schema changed.

| Operation | Actual source chain and decision | Live routing |
|---|---|---|
| API-238 GET /admin/finance/sheet-sync | require_staff finance/security_admin/superadmin; current verified email/session/MFA; finance_sheet_sync JOIN orders, durable_jobs finance.sync state projection. No general Orders API, allocation or provider call. SOURCE ELIGIBLE. | false, read gate;503 before auth/upstream |
| API-239 POST /admin/finance/sheet-sync/{sync_id}/retry | Same roles/MFA; row FOR UPDATE; eligible failed/retry or non-synced with dead finance.sync job; UPDATE sync status, enqueue only finance.sync if no active job, audit finance.sheet_sync_retry. Worker run_one_finance_sync -> claim_finance_job (finance.sync only) -> process_sheet_sync -> masked approved Sheets projection/provider upsert -> lease/version-fenced completion. Finance advisory serialization; no dispatch to allocation/retention cleanup. SOURCE ELIGIBLE; actual concurrency/provider acceptance outstanding. | false, independent retry gate |
| API-242 GET /admin/storage/artifacts | operations/finance/security_admin/superadmin, same email/session/MFA; print_artifacts JOIN print_jobs UNION payment_evidence JOIN payment_attempts; sr_retention_held reads authorized hold/order linkage, latest retention.cleanup job metadata. No provider/object fetch or cleanup execution. SOURCE ELIGIBLE independently of mutations. | false, independent read gate |
| API-243 POST /admin/storage/artifacts/{artifact_id}/retention-holds | Security Admin/Superadmin; strict reason_code syntax, advisory/resource locks, generic print/payment/order/finder resource resolution, insert hold + legacy hold reason + audit. Finder branch reaches0021 sr_support_finder_hold_lock -> qr_codes pair reference, order_pair_units/orders/tag_pairs locks. Entire generic endpoint QUARANTINED; no print-only payload workaround. | false; relay always405 before auth/body/upstream |
| API-244 DELETE same retention-holds path | Security Admin/Superadmin; locks resource, releases active holds, clears legacy reason, audits. No required request reason/version/idempotency key in source. Release can admit the pair-dependent destructive retention worker; eligibility/authority evidence incomplete. Entire endpoint QUARANTINED; release does not itself prove deletion. | false; relay always405 |
| API-245 POST /admin/storage/artifacts/{artifact_id}/cleanup-retry | Security Admin/Superadmin; RetentionHoldRequest reason_code ->0019 sr_retention_retry, dead job retry/reset + audit. Worker cleanup_private_artifact -> sr_retention_prepare reads support disputes via order_pair_units; policy/hold/lease checks precede provider delete and completion tombstone. Irreversible provider operation and prohibited pair dependency. QUARANTINED. | false; relay always405 |

All paths in the table have prefix /api/v1. No separate recent-authentication event requirement appears in these handlers; existing session/Auth/MFA enforcement remains necessary. RLS/ACL/helper inspection included0003,0019_retention_recovery.py and0021_support_case_console.py. Finance worker lease/aggregate binding and RLS are source evidence only, not proof of installed PostgreSQL functions or enforcement. Sharing a worker Python module with cleanup does not mean the finance.sync branch dispatches cleanup; its reviewed claim/process path is separate. No worker was run.

### Module A — Finance implementation and limits

Existing list/detail pages and AdminFinanceSync reuse AdminPage/AdminShell, cards, tables, status badges, CSS and AdminConfirmDialog. Removed active mock/localStorage financial projections and the legacy FinanceStorageAdmin fallback. List shows only sync/order references, backend status, attempt count, export version, updated/last-synced times. No created timestamp is supplied. Page-local status/reference filters, backend limit/cursor, Next/Previous, cursor-preserving detail links, refresh, loading, bounded absence and redacted denied/unavailable states are implemented. No general Orders enrichment, financial amounts, reconciliation totals or external sheet reads.

Actual API-238 response has13 fields per row and items/next_cursor. Relay projects eight fields, dropping sheet_row_key, payment/fulfillment status, currency and total. Unknown error strings become unrecognized_failure; raw provider errors are never reflected. Statuses pending/synced/retry/failed are distinct; Retry queued never claims sheet completion or payment invalidity.

API-239 accepts an EMPTY upstream POST and returns202 {id,order_id,status:retry}. It has no backend reason, confirmed, expected revision/attempt count or client Idempotency-Key contract. The local exact {id,confirmed:true} confirmation envelope is stripped by the relay; no unsupported fields/headers are fabricated. Eligible failed/retry detail action requires a confirmation dialog and independent admission. An immediate ref blocks double submission. Confirmed202 displays queued semantics and refreshes GET metadata;404/409/422/429 refusal requires review after refresh. Unknown transport/response outcome locks retries in this mounted screen, never automatically replays, and directs authorized review. GET refresh cannot unlock that state. This in-memory lock is not cross-tab/reload idempotency or durable reconciliation. Backend row locking/active-job coalescing is not a request replay key or exactly-once guarantee; genuine concurrent/replay/timeout/provider acceptance is a Phase14 prerequisite.

### Module B — Storage implementation and limits

Existing Storage list/detail pages reuse Admin UI/CSS and replace active demo/legacy controls. Only authorized metadata is loaded: artifact ID/type, owner reference, format/size, retention/deleted timestamps, boolean hold and safe cleanup job ID/status/attempt/error metadata. Bucket, object key, checksum, private hold reason and unknown error text are dropped. No signed/public object URL, object contents, credentials, private file download, bucket mutation or deletion control exists.

API-242 returns {items}, at most limit50 default/100 maximum, and no cursor/complete total/created/updated timestamps. Filters are resource_type (print_artifact/payment_evidence), order_id, job_id and limit; a print-job filter excludes payment evidence in backend SQL. UI offers those filters and a labelled local hold filter; no invented next page. Details search only the authorized bounded result, carrying its query. Missing data does not establish global absence. Hold reported / No hold reported / Deletion recorded describe returned metadata, not actual object availability or policy-approved deletion eligibility. A completed cleanup job alone does not prove provider deletion. Hold reasons/revisions/retention legal periods are not invented. Hold creation/release/cleanup controls remain unavailable; no positive mutation request was sent, even in test fixtures.

### Security controls and files

Six independent server-only literal-false gates in lib/finance-storage-gate.ts cannot be enabled by query, browser storage or environment. Non-GET Storage methods are unconditionally405. Finance permits only GET/POST to two fixed backend paths. Both reads remain independent of mutation eligibility. Pages enforce existing authenticated capability and role/MFA guards; the relay rechecks verifiedSession/staffState before and after upstream work. Existing backend remains authoritative.

Relay rejects cross-site/wrong-origin requests; POST requires the configured exact origin. Query keys/duplicates/UUID/cursor/limit and exact local confirmation are validated; encodings, GET bodies, unsupported methods and arbitrary paths fail closed. Deadline10s, redirect rejection, bounded request2048bytes, streamed JSON response262144bytes, exact200/202 schema and attachment rejection; private/no-store, nosniff, no-referrer and redacted errors. Read hooks abort superseded requests, suppress stale responses and clear hidden/denied data. No sensitive browser storage or speculative prefetch.

Implementation files (frontend-relative):
- app/admin/finance/sheet-sync/page.tsx, [syncId]/page.tsx and api/route.ts; app/admin/storage/page.tsx, [recordId]/page.tsx and api/route.ts.
- components/admin-finance-sync.tsx; components/admin-storage-retention.tsx. Finance module CSS fixes confirmation-button contrast; Storage CSS/shared UI unchanged.
- lib/finance-storage-contract.ts; lib/finance-storage-gate.ts; lib/use-finance-storage-read.ts; lib/api/finance-storage-relay.ts.
- tests/finance-storage-fixture.cjs; tests/phase12-finance-storage.spec.ts; scripts/test-finance-storage.cjs; playwright.finance-storage.config.ts. Superseded mock-only admin-finance-sync-screen21.spec.ts and admin-storage-screen22.spec.ts removed; new combined suite tests the current screens.
- backend/tests/test_finance_storage_frontend_contract.py (tests only).
- ADMIN_BACKEND_API_INVENTORY.md, ADMIN_FRONTEND_BACKEND_MAPPING.md, ADMIN_BACKEND_INTEGRATION_PLAN.md and this tracker.

### Actual isolated verification

Fixtures were inspected before execution: synthetic exact-path fetch only for API-238 GET, API-242 GET and API-239 empty POST. No .env, DB engine, cloud account, migration, provider, worker, setup/teardown QR operation or storage object is used. Backend uses actual FastAPI router, signed synthetic JWT/JWKS MockTransport and scripted SQL; SQL forbids pair and retention command/prepare/delete statements. Quarantined retention reason validation is model-only, never endpoint execution. Existing broader finance/storage/retention integration suites were not run because their fixtures exceed this scope. No Phase9–11 acceptance tests were rerun.

- Node relay/contract checks: **65 passed**. Role/MFA/capability and final-role enforcement; query validation, gate zero-call behavior, exact empty retry POST, confirmation/unsupported-field rejection, origin protection, redacted errors, oversized/attachment/malformed/network rejection, sensitive-field canaries, all retention methods405 including missing reason; six production gates false and no legacy page mounts.
- Scoped backend: **28 passed** with --noconftest. Real router/JWT role matrix, email/MFA, list fields/cursor/limits, retry202/audit/FOR UPDATE scripted SQL and404/409; model-only invalid reasons and source quarantine evidence. Initial source test used nonexistent SQL migration filenames; corrected to actual0019/0021 Python migrations and reran successfully. No backend implementation changed.
- TypeScript: **PASSED**. Scoped Ruff: **PASSED** after test-only style fixes.
- Browser: **31 passed** using playwright.finance-storage.config.ts. Actual React screens and relay exercise Finance filters/cursor/refresh, confirmation cancel/Escape, queued receipt,409 refresh, unknown-outcome lock without replay; Storage backend/local filters, hold metadata and no mutation/download controls; disabled gates and401/403/503 redaction. List/detail layouts passed1366x768,1440x900,768x1024 and375x667 without document overflow.375px retry dialog keyboard wrap and double-click suppression passed. No unexpected requests or browser storage. Synthetic screenshots under tmp/phase12-sync-storage;375px Finance details, Storage list and retry dialog visually inspected. A white-on-white confirmation style found during visual review was fixed in Finance-scoped CSS; the mobile dialog check now asserts computed foreground/background colors. After this CSS fix, both confirmation/mobile-dialog tests passed again (2/2), and TypeScript passed again.
- Protected-file snapshot tmp/phase12-sync-storage/protected-before.json: **39 checked,0 changed**. Includes0043/0044, provisioning, Phase4 Orders, Support/Notifications/Privacy components/contracts/gates/routes, backend protected handlers/Auth/runtime/main and retention/worker/source migrations.0044 hash remains17B3B5BD5964F6DFB7A1B610BCE455D32FC805539282E3ECB7D79A9E39A19A2D. No migration was applied.

### Outstanding live acceptance / next phase

Phase14 must establish source-equivalent installed functions/ownership/ACL/RLS, actual current role/MFA/capability and category/record authority, safe pagination/minimization, provider policy/configuration, real finance worker lease/version/concurrency/timeout/replay behavior and approved provider mutation acceptance using separately authorized fixtures. Isolated checks do not demonstrate actual PostgreSQL locks, transaction rollback, RLS or real Sheets/Storage behavior. The retry gate must remain false until those requirements pass; lists have independent gates. No new testing environment or approval request is introduced here.

API-243/244/245 remain quarantined under the absolute QR-pair exclusion. Phase14 does not lift that exclusion; an independently approved safe backend contract or explicit policy change is needed before reconsideration. No alternate Support/Orders API, generic proxy or restricted-looking payload may bypass it.

Phase9 remains **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED**; Phase10 Notifications remains **IMPLEMENTED — LIVE ACCEPTANCE PENDING**, both gates false; Phase11 Privacy export metadata remains **IMPLEMENTED — LIVE ACCEPTANCE PENDING**, API-330 gate false and API-327 quarantined. Their detailed blockers above remain unchanged.0044 remains unapplied, no identity/role/provisioning or frontend Support activation occurred. Recommended next phase: Phase13 only upon owner direction; **not started**. Consolidated live acceptance stays in Phase14.

## Phase 13 — Dashboard, Audit, My Security and Monitoring — 24 October 2026

**PHASE 13 — IMPLEMENTED; LIVE ACCEPTANCE PENDING** applies to prepared/tested API-345 Trends, API-100 restricted Audit metadata, current-user staff-security panel and API-001 process Liveness adapter. **API-344 Summary remains QUARANTINED / NOT INTEGRATED.** No summary KPI or revenue total is fabricated. Five separate server-only admission functions are literal false, including the conservatively disabled public Liveness adapter. Existing global authentication bootstrap remains active and unchanged. No Phase14 work, Cloud request, provider operation, database/schema change, migration, infrastructure or real identity/role provisioning occurred.

### Review, strict allowlist and exact service chains

Rechecked the current inventory/mapping/plan and corrected strict allowlist/exclusion records, approved API Contract (including Task5.7B), Technical Design, Database/Migration and Security/Privacy specifications. Historical162-operation totals,70 exclusions/quarantines and Products14-operation budget remain unchanged. The corrected allowlist is present and internally consistent:344 quarantined,345/100 eligible, own staff-security supporting and001 public liveness. A role-limited request to344 is not an exception to its endpoint-level quarantine.

| Candidate | Actual registration and source chain | Independent decision |
|---|---|---|
| API-344 GET /api/v1/admin/dashboard/summary | main.install_dashboard -> dashboard.summary -> explicit current five-role/email/session/MFA guard, feature flag, role projection ->0028 sr_dashboard_summary. Operations fulfillment metrics call sr_fulfillment_eligible.0018 legacy path reads order_pair_units/pair_print_qa;0034 wraps retained v33 helper and0042 single_qr branch still retains legacy ELSE path. No request group selector can guarantee safe branches. | QUARANTINED entire endpoint. Overview never requests it. Relay returns503 SUMMARY_QUARANTINED before module auth/fetch even if a synthetic admission is true. No safe-role/payload workaround. |
| API-345 GET /api/v1/admin/dashboard/trends | Same registration -> dashboard.trends -> current five-role/email/session/MFA + dashboard_enabled ->0028 sr_dashboard_trend for shipments_dispatched and notifications_created only -> scalar retained shipments/notification_outbox counts. orders_placed is unavailable without SQL. Final current session/MFA/roles reread. | SOURCE ELIGIBLE independently of344. Prepared typed chart/table UI and fixed-path relay; live gate false. |
| API-100 GET /api/v1/admin/audit-events | main audit_events_router -> search -> explicit security_admin + MFA + recent() (signed AMR authentication timestamp within300s; fresh token iat is insufficient). audit_events SELECT seven metadata fields, keyset paging; unknown action/type redacted; INSERT only audit.search/audit_search without filters/private details.0003 audit SELECT/INSERT RLS, append-only and safe_json trigger; no contextual delegation, pair lookup, provider or worker. | SOURCE ELIGIBLE. Prepared restricted list/filter/cursor/detail projection; live gate false. Superadmin alone is denied. Read has the documented audit-search append side effect, not a silent pure SELECT claim. |
| GET /api/v1/me/staff-security | main account_router -> current Authenticated principal -> require_verified_account -> nonrevoked staff_roles WHERE user_id=current principal -> fixed capability registry gated by actual MFA. Three fields only: roles,mfa_verified,capabilities. No arbitrary subject lookup, global role editor or pair service. Existing AAL1 bootstrap is intentional. | SUPPORTING / SOURCE ELIGIBLE. Separate current-user panel gate false; existing AdminPage/staffState bootstrap and Auth settings unchanged. No query/subject selector accepted by panel relay. |
| API-001 GET /api/v1/health/live | main health_router -> live -> Liveness(status=ok). Public, no dependency/session/database/provider/worker call. | SOURCE ELIGIBLE. Fixed process-observation adapter prepared; independent gate conservatively false. API-002 readiness is excluded and never called. Browser page/adapter retain existing Operations/Security Admin, MFA and notifications.manage guard; no JWT forwarded to public001. |

Trends and Summary require dashboard_enabled in the backend; Phase13 changes no backend feature configuration. Existing0003 sr_is_staff/context and dashboard0028 helper role/search_path/EXECUTE guards were reviewed in source. Shipments RLS ownership helper reads orders only; notification metadata aggregate uses the authorized narrow SECURITY DEFINER helper, not raw Operations table access or message enrichment. Actual installed function ownership/ACL/RLS, migrations and query-budget behavior remain unverified. No source review constitutes live acceptance.

### Dashboard implementation and unavailable metrics

Existing /admin and OverviewDashboard keep AdminPage/AdminShell/shared cards and module navigation. Replaced demo analytics, local audit/governance panels and synthetic financial totals. No legacy AdminDashboard is mounted. Removed quarantined inventory/batches/ready-to-ship/reconciliation quick links from this overview's existing module list; no unrelated module or global navigation was redesigned. Summary unavailable state explains that summary/revenue/customer/inventory/fulfillment KPIs are not loaded; unavailable does not mean zero.

API-345 accepts only display_timezone=UTC|Asia/Karachi, defaults UTC. No custom date range or interval exists. Window is exactly30 completed UTC days ending current UTC midnight, half-open daily buckets; current day excluded. Role series: shipments_dispatched Operations; notifications_created Operations/Security Admin; orders_placed Operations/Finance is unavailable/DRILLDOWN_UNAVAILABLE. Finance/Support/Superadmin can have no ready series; no fabricated chart. UI shows actual as_of, UTC range, display timezone, count precision, unavailable reason, loading/no-series/error and Refresh Dashboard Trends. CSS bars have an accessible per-day table with exact start/end/count/precision. No drilldown fetch or target enrichment. No interpolation; invalid/missing ready buckets fail closed. Counts0..999 are exact;1000 is a capped lower bound displayed1000+, not an exact total or a guessed statistical estimate. Counts reflect currently retained evidence, so later reads may differ; as_of is an observation time, not a freshness SLA or reconstructed historical snapshot.

### Audit implementation and privacy

Existing /admin/audit and /admin/audit/[eventId] reuse AdminAuditLogs/shared UI; removed query-selected AuditSearch and mock localStorage fallbacks. Eight supported query parameters only: actor_id,target_id,target_type,action,start,end,limit,cursor. UUID references, closed action/type lists, timezone-aware ISO start/end,0<range<=31days, limit1..100 (UI20/50/100), descending timestamp/UUID cursor. Initial/default seven-day window is frozen explicitly so refresh/paging preserves bounds; applying filters resets cursor. Next/Previous navigation and detail links carry the authorized query. Detail is only a view of the loaded authorized list page, not an invented detail API or global search. Missing event does not establish global absence.

Seven fields shown: id,occurred_at,actor_kind,actor_user_id,action,target_type,target_id. Missing references say Not provided; actor names are not invented. Backend restricted_event/restricted redactions are preserved and unknown strings are mapped to those safe constants again in the relay. References, including historical QR target metadata, are inert text; no QR/user/order/profile target is followed or enriched. React escapes content. No raw safe_details, before/after snapshots, reason text, raw payload download, full-text search, audit export or fabricated audit events. User-facing note explains recent authentication and the audit.search append.

### My Staff Security implementation

Existing Staff Permissions page now shows current-user roles, actual MFA verification and capabilities via its own read-only adapter. No selected staff query or role preview determines authority. Missing/invalid fields fail closed; missing MFA displays No and no privileged capabilities; empty capability list is explicit. Existing AdminPage still requires MFA and redirects real AAL1 staff into the existing MFA flow before rendering the page; the underlying current-user endpoint/relay retain the existing AAL1 bootstrap contract. Isolated component tests cover the false-MFA projection without weakening the real page guard.

Refresh My Security rereads the current principal only. Other accounts, authentication assurance level, recent-authentication timestamp and global permission configuration are Not Available because the three-field contract does not supply them. Role creation/editing/grants, MFA removal, recent-auth bypass, development self-grant and0044 provisioning have no controls or relay methods. No Users API is used to enrich this panel. Capability omission is not interpreted as a grant, nor does a role label prove MFA enabled.

### Monitoring implementation

Existing /admin/system now mounts AdminSystemMonitoring only; no ?view=live SystemHealth console, demo jobs/alerts, provider controls or polling. Public001 exact200 JSON {status:ok} is validated by the server adapter and again by the browser. UI reports Backend reachable — process responded, actual status and last CLIENT check completion time. Failed/timeout/refused checks clear earlier success and say reachability unconfirmed; transport failure alone is not a diagnosed backend outage. Manual refresh only, apart from ordinary page load and visibility refresh. Response never establishes fully healthy system or database readiness.

Database readiness/pool, CPU, memory, providers, email, storage availability/usage, workers, backups and incidents all show Not Available. No internal readiness token/path, provider request, background job execution, bucket or infrastructure control exists. No server heartbeat/as_of is invented for001.

### Relay and browser security

lib/phase13-gate.ts has five independent literal-false functions; query/browser storage/environment cannot admit a route. Summary has an unconditional additional quarantine. Existing global AdminPage verifiedSession/staffState authentication is preserved; module gates reject before module auth/fetch. All non-GET methods reject405 before module auth/body/upstream, including staff role mutations and monitoring controls.

Closed same-origin adapters reuse verifiedSession, staffState and configured origin validation. Origin mismatch/cross-site, unknown/duplicate query, unsupported body/encoding, arbitrary subject/path/method fail closed. Current staff role/MFA/capability checked before and after privileged fetches; Trends payload roles must match both observations. Audit recent-auth remains authoritatively enforced by the unchanged backend. No frontend approximation of signed authentication time. Staff-security fetch is itself the current-user security projection. Public Liveness receives no JWT or readiness credential.

Fixed upstream paths only, redirect rejection, no-store,10s deadline (Liveness5s), streamed JSON200 only, attachment rejection, redacted error statuses and fresh schema projection. Dashboard preserves approved64,000-byte response cap; other metadata reads cap262,144bytes. Responses are private/no-store,nosniff,no-referrer. Browser hooks use abort/generation protection,15s deadlines, clear old data on refresh/denial/hidden tab, and suppress late unmounted responses. No tokens/results persisted in local/session storage and no speculative prefetch. No earlier module gate, authentication configuration or backend implementation changed.

### Actual isolated checks and results

Fixtures/setup/teardown inspected before execution. Only synthetic GET requests for345,100,current staff-security and001 are accepted by the fetch harness; Summary and all writes are forbidden. Browser interception blocks every other network path; actual React components and actual Next route/relay code run through the synthetic harness, without a listener. Backend uses actual FastAPI routers, signed synthetic JWTs, fixed JWKS MockTransport and scripted SQL. SQL rejects summary/fulfillment/pair queries and business mutations; only the documented audit.search append is scripted. No .env, DB engine, migration, real Auth account, worker, provider, storage, QR API, readiness or protected setup fixture is used. Broader legacy dashboard/audit/staff/system integration suites were not run because their fixtures/contracts exceed this scope. Earlier phase acceptance suites were not restarted.

| Check | Actual result and limit |
|---|---|
| node scripts/test-phase13.cjs | **115 passed** final run: four read contracts, all five gates, zero-call Summary quarantine, methods/queries/origins, role/MFA/revocation, error redaction, oversize/attachment/malformed/timeout rejection, capped/missing buckets, no credential forwarding, no legacy/mock mounts, independent64,000-byte Dashboard bound. |
| npx playwright test --config playwright.phase13.config.ts | **51 passed** full run. Trends precision/range/timezone/table/unavailable/empty; Audit filters/frozen window/cursors/detail/redaction/missing references/denial/invalid query; My Security current-user/MFA/capability gaps/no role controls; Liveness response/failed observation/no invented readiness; four gates, loading,401/403/503, keyboard and all four requested viewport sizes. Initial45-test run had3 failures: tablet audit overflow, exact Audit action label, and test expecting a table disclosure to remain open across replaced data. Fixed scoped min-width, explicit accessible select label and reopened disclosure in test; targeted3 passed, then full51 passed. No failure was ignored. |
| .venv/Scripts/python.exe -m pytest --noconftest tests/test_phase13_frontend_contract.py -q | **29 passed**: actual read router/JWT contracts, Trends fixed range/cap/role projections/unsupported queries/default-feature gate; Audit redaction/paging/search audit, explicit roles and signed AMR300s vs token iat; current-principal staff projection/MFA gap; public Liveness zero Auth/DB; source Summary quarantine and independent safe Trends graph. Scripted SQL is not installed RLS/query/transaction acceptance. |
| Scoped Ruff | **PASSED** for the new backend test. |
| npm run typecheck | **PASSED** for new/changed modules and browser tests. |
| Responsive/visual |1366x768,1440x900,768x1024,375x667 passed for all four panels;375px uses RTL. Tables scroll within their card; no document overflow; keyboard reaches controls.375px Audit and1440px Trends screenshots visually inspected under tmp/phase13-dashboard-audit-security. |
| Protected-file hash comparison | **59 checked,0 changed**, snapshot tmp/phase13-dashboard-audit-security/protected-before.json. Includes0043/0044, provisioning, Phase4 Orders, Phase9–12 implementations/gates/routes/contracts, protected backend handlers/Auth/runtime/main, Finance/Retention worker and migrations, candidate Phase13 backend handlers/helpers and existing staff authentication contracts.0044 remains unapplied. |

Final source-only refinement retained the approved64,000-byte Trends cap, initialized linked timezone labels and clarified retained-evidence semantics. Node115 and TypeScript passed again, and the affected Trends browser case passed again (1/1). These isolated results do not establish real Auth/MFA/RLS, managed migration state, MVCC/query plans/resources, live provider health or actual browser sign-in acceptance.

### Files changed — 32 source/test/document paths

17 existing files modified:
- frontend/app/admin/page.tsx; frontend/app/admin/audit/page.tsx; frontend/app/admin/audit/[eventId]/page.tsx; frontend/app/admin/staff-permissions/page.tsx; frontend/app/admin/system/page.tsx.
- frontend/app/admin/dashboard/api/route.ts; frontend/app/admin/audit/api/route.ts; frontend/app/admin/system/api/route.ts; frontend/lib/api/dashboard-relay.ts.
- frontend/components/admin-overview.tsx; frontend/components/admin-audit-logs.tsx; frontend/components/admin-staff-permissions.tsx; frontend/components/admin-system-monitoring.tsx.
- frontend/ADMIN_BACKEND_API_INVENTORY.md; frontend/ADMIN_FRONTEND_BACKEND_MAPPING.md; frontend/ADMIN_BACKEND_INTEGRATION_PLAN.md; frontend/ADMIN_BACKEND_INTEGRATION_PROGRESS.md.

11 new files:
- frontend/app/admin/staff-permissions/api/route.ts; frontend/components/admin-phase13.module.css.
- frontend/lib/phase13-gate.ts; frontend/lib/phase13-contract.ts; frontend/lib/use-phase13-read.ts; frontend/lib/api/phase13-relay.ts.
- frontend/tests/phase13-fixture.cjs; frontend/tests/phase13.spec.ts; frontend/scripts/test-phase13.cjs; frontend/playwright.phase13.config.ts; backend/tests/test_phase13_frontend_contract.py.

4 obsolete mock-only suites removed, replaced by the current combined Phase13 browser suite: frontend/tests/admin-overview-screen2.spec.ts; frontend/tests/admin-audit-screen23.spec.ts; frontend/tests/admin-staff-screen24.spec.ts; frontend/tests/admin-system-screen25.spec.ts. Generated screenshots/hash evidence are excluded from the32-path source manifest. No unrelated source was reverted or committed.

### Remaining blockers and recommended Phase14 requirements — not started

All five module gates remain false. API-344 cannot be admitted under the current exclusion even after ordinary acceptance: an independently approved backend contract that avoids every prohibited branch, or explicit policy change, is needed before reconsideration. Existing supporting staff-security authentication bootstrap is unchanged and is not blocked by the new panel gate. Public001 needs no database readiness authorization; its adapter is conservatively held pending consolidated deployment/origin/error acceptance.

Recommended Phase14 evidence, when separately authorized: source-equivalent installed helpers/migration graph/ownership/ACL/RLS and configured dashboard flag; real current staff roles/MFA/live session/revocation behavior; Audit signed recent-auth/time windows/cursors/privacy/search audit; own-user identity/MFA/capability projection; safe Trends authorization, retained evidence, capped counts, UTC/Karachi boundaries and SQL savepoint/timeout/query-budget behavior; real same-origin Next/Auth/browser flows and process-only Liveness timeout behavior. No new infrastructure/provisioning/migration application/provider mutation is authorized by this recommendation. Verify earlier phase-specific prerequisites from their existing entries without lifting quarantines by a frontend flag.

Phase9 remains **PAUSED — READ-ONLY IMPLEMENTATION COMPLETE; LIVE ACCEPTANCE BLOCKED**. Phase10 Notifications gates remain disabled. Phase11 export metadata gate remains disabled; API-327 decisions quarantined. Phase12 eligible238/239/242 implementation remains live-disabled;243/244/245 retention actions remain quarantined with documented concurrency/provider/RLS blockers.0044 is unapplied; no Support activation, test identity, role grant, provisioning change or protected Phase4 Orders change. **Phase14 has not started.**

## Phase14 shared live acceptance — partial actual execution,25 October2026

Authorized non-destructive execution reused development fhuxryfkfrvycsojkzvq and current FastAPI configuration. Verified actual local FastAPI liveness200; nine eligible anonymous reads401/no-store; verified-TLS runtime/catalog Cloud connectivity and sole0043 revision (runtime version read denied42501, existing catalog-inspection connection used with READ ONLY/ROLLBACK); selected RLS/policy/helper/role metadata; actual SQLAlchemy runtime connection; public Auth ES256 JWKS. No private domain/Auth/QR rows enumerated, no migrations, permissions, identities, credentials, settings or gates changed. FastAPI test process stopped afterward.

No supplied/reusable genuine staff session found in checked inputs; four required frontend runtime values are absent in its checked environment. Signed-in role/MFA/RLS/pagination/redaction acceptance remains **NOT EXECUTED**. Source review confirms authenticated Support reads and Audit search require audit INSERTs, so their success paths were not attempted under the read-only scope. Existing backend dashboard/template/directory feature flags remain false. No live admission is inferred.

Backend wheel built offline with existing setuptools tooling;93 Python file bytes matched source and wheel import/liveness passed. SHA256 cdb58130a4fa7f3f20417b1cb8baf1a29c425f81e9e2caa4ea8ca8f5a198cef3. Docker unavailable: configured Python3.12/nonroot/Linux image acceptance remains pending; local smoke uses existing Python3.14.8. Only21 narrow safe quarantine boundary tests rerun/passed; full frontend suite/build evidence reused. New runnable read check backend/scripts/run_admin_read_acceptance.py passed scoped Ruff; optional real-token branches not exercised.27 protected hashes match.

Actual evidence, individual admission gaps, categories (live verified/offline only/authorization missing/provider pending/quarantined) and exact owner-controlled next actions are in ADMIN_FINAL_INTEGRATION_REPORT.md section8 and tmp/live-acceptance-2026-10-25.0044 remains unapplied, all quarantines/gates preserved, no provider/mutation/deployment or new numbered phase. **Phase14 PARTIALLY EXECUTED — NOT READY; genuine staff session, approved read fixtures/access-audit authority, per-feature configuration approval and backend container acceptance remain outstanding.**

## Development staff login setup — 25 October 2026

Owner confirms an existing authorized staff account. Configured the four existing public frontend runtime settings in ignored .env.local using the existing development publishable key; no credential created. Exact variables, Windows commands and existing sign-in/MFA steps are in final report section9. Added an owner-operated ephemeral browser helper and stdin/session-only support to the existing acceptance runner; scoped syntax/Ruff checks passed. Corrected sandbox network denial by restarting the existing frontend with network access; public Auth settings HTTP200 verified. Genuine sign-in/MFA still pending owner completion; no live read acceptance claimed, audit-writing Support/Audit paths unexecuted, gates/permissions/0044/quarantine unchanged.

Live owner login now succeeded after the network correction: actual /auth/continue, successful MFA action and /admin HTTP200, confirmed by owner. This was the Codex side window, separate from the private runner context. The first helper timed out without capturing a session and was reopened; automated current-user receipt remains pending owner completion in that separate Chromium window. No tokens exported, no module admission inferred, no gates enabled. Next.js startup also emitted a dependency security warning; no dependency upgrade performed within this authentication setup task.

**Final login result: PASSED**, superseding pending above. At2026-10-25T06:55:14Z the secure helper supplied a genuine owner-authenticated MFA session over stdin to the existing session-only runner. Real GET /api/v1/me/staff-security200; schema validated; mfa_verified=true; existing roles finance/operations. Non-secret receipt: tmp/live-acceptance-2026-10-25/genuine-staff-login.json. Helper closed its ephemeral window normally. Development login needs no further configuration/onboarding. Module-specific RLS/pagination/redaction and audit-writing acceptance remain unexecuted; no gates, permissions, credentials, migrations or quarantine changed. Overall launch NOT READY; shared login prerequisite resolved.

## Print Template development activation — 25 October 2026

Explicit owner authorization applied only to fhuxryfkfrvycsojkzvq/local8030/3100. Backend management flag now true and matching template origin configured after successful candidate metadata acceptance. Actual owner-authenticated MFA live checks: API300 list200, API301 synthetic create201/replay201/changed-intent409, API302 detail200/ETag/no-store; normal frontend relay200 and fixture visibly rendered. One explicitly approved draft metadata fixture dev-acceptance-20261025 remains; no revisions, assets, approvals, product bindings or publications created. Audit/idempotency writes were explicitly included in fixture approval. No credentials exported.

Actual deployed aggregate prerequisites:0043 unchanged, template count1, active assets0, valid authorities0, QA approvals0, asset root absent, Windows preview unsupported. Listing/create/details are now independently functional; full design/preview/QA/approval/binding remains BLOCKED. API307 stays unavailable in frontend. No invented authority or physical evidence. New precise error codes distinguish disabled gate, origin, assets and isolation from genuine300-second reauthentication. Official MFA-in-new-tab recovery retains unsaved input; fixed closed return path and mobile overflow. Product editor links directly to templates while preserving server publication/price/size rules.

Validation:207 distinct selected backend template/security cases passed across runs after explicit supported-platform simulation was added to scripted preview orchestration tests;57 further product publishing/price/assets cases passed;60 template relay checks;131 quarantine tests;19 distinct template browser cases across runs after mobile sizing fix; TS/scoped Ruff/fresh offline-network production webpack build passed. Fixed-port legacy picker browser test unexecuted because3100 hosts the owner's dev session. Real Linux/physical QA remains unverified.27 protected hashes unchanged. Next.js dependency warning unresolved.

Receipts and exact API matrix/recovery/owner actions: final report Print Template development activation section and tmp/template-activation. Rollback: backend python scripts/configure_template_development.py --rollback then restart only local backend; no destructive database rollback. Remaining owner inputs: genuine reviewed/licensed font/logo assets and controlled enrollment, supported isolated Linux runtime, actual physical scan/copy/license evidence plus existing authority/policy/signature process before live approval/binding acceptance. Development metadata gate ENABLED; complete product-publishing workflow NOT READY. No0044, cloud permission change, unrelated gate, production deployment, QR service or new phase.
