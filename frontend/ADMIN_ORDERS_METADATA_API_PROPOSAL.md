# Independent Admin Orders Metadata API — review proposal

Current status: **IMPLEMENTED for Phase 4; isolated checks passed, live acceptance blocked.** The original proposal below is retained as design history. The user subsequently requested proceeding with Phase 4; implementation uses the stable named operation `admin_order_metadata_list` without inventing a numeric API ID. See `ADMIN_BACKEND_INTEGRATION_PROGRESS.md`, Phase 4 implementation entry. Existing API-080 remains quarantined.

Original proposal status: **PROPOSED — NOT IMPLEMENTED — NOT ALLOWLISTED FOR CALLS**. Date: 23 October 2026. Audit and design only. No application code, schema, grants, policies, deployment or existing API changed. No API/database request, service/function invocation, migration, test, fixture or rendering performed. SQL and JSON below describe a future contract, not executable changes or current behavior.

## Decision for review

Propose **GET `/api/v1/admin/order-metadata`**, a separate read-only, fixed metadata projection. Do not modify, wrap, call or reuse the handler for GET `/admin/orders`, its detail endpoint or its fulfillment logic. Proposed OpenAPI operation name: `admin_order_metadata_list`; numeric API ID must be assigned by the approved contract owner before implementation. No detail route or mutation is proposed.

The existing orders table supports the proposed fields without a data-model change. This is a source-level conclusion conditional on verifying the installed schema, grants and RLS. Performance at production scale and deployed security are not established. This document does not authorize implementing or calling the proposal.

## Inspected sources and safety boundary

- `backend/app/db/commerce.py`: `Order` (orders aggregate), `OrderItem`, `OrderLogicalItem`, `OrderItemSize` and their stored snapshot fields. `backend/app/db/models.py` provides Base/identity/timestamps rather than the commerce Order mapping. orders contains UUID id, unique order_number, statuses, currency, NUMERIC(12,2) aggregates and timestamps. Its private customer ID and payment snapshot fields are deliberately omitted.
- `backend/alembic/versions/0002_commerce.py`: frozen orders DDL, constraints, primary/unique indexes and customer/date index; RLS enabled. Existing fields require no new column/backfill. Inspecting these definitions does not apply migrations.
- `backend/app/api/v1/fulfillment_queries.py:156–229` and `backend/app/main.py:97`: current API-080 registration and SQL projection. Operations membership adds `sr_fulfillment_eligible`; finance-only branching is not independent authorization. Existing bounds/date ideas can be specified independently, but importing this router or its broad response/service is unnecessary.
- Existing eligibility definitions/wrappers in migrations 0018, 0034 and 0042 confirm reachable legacy pair inspection. The proposal must have **no dependency** on those functions, the typed alternative, template registry order resolution or any allocation/QA/ownership helper.
- `backend/app/api/auth.py`: verified principal, `Authenticated`, authorize and require_staff. `backend/app/db/runtime.py`: transaction-local safereturn_api role, actor and MFA context. These common auth/transaction utilities do not require pair reads on their proposed path.
- `backend/alembic/versions/0003_workflows_security.py:406–411,885`: `sr_is_staff` reads MFA context/staff_roles; orders SELECT policy uses customer actor equality or staff role checks. It does not query QR tables or fulfillment eligibility. Customer foreign key does not cause a SELECT-time join to auth.users. UPDATE/INSERT triggers and foreign-key checks are not activated by plain SELECT.
- `backend/alembic/versions/0030_account_lifecycle.sql:82` session-state function: auth users/sessions and account_security_state with an account advisory lock; no QR inspection. Existing security-context setup uses transaction-local configuration, so do not blindly force a database read-only transaction before proving compatibility with this authorization function. Business-data operations here are SELECT-only; no order/identity/worker mutation or row locks are added.
- `backend/app/api/v1/account.py` STAFF_CAPABILITIES: orders.read is operations/finance. RLS is broader, but the proposed API preserves the narrower existing route authority.
- Approved technical design, database design, API contract, Security and Privacy Specification v1.2 and Product Copy Pricing Amendment v1.4: authoritative historical decimal snapshots, least privilege, verified session/MFA, no client price authority. Existing integration inventory/mapping/plan and Products/Templates/blocked Orders progress remain authoritative historical evidence, not new endpoint approval.

Future reachable graph must be: verified JWT → existing transaction/account-session/MFA checks → require_staff(operations, finance) → explicit orders SELECT with current staff predicate under existing RLS → closed metadata serialization. A final account-session/MFA/role recheck before response serialization must fail closed on observed revocation. No read can promise immediate revocation after its final check; no cross-request authorization cache is introduced. Auth bootstrap may separately read `/me/staff-security` through existing infrastructure, never an Orders console.

## Proposed authentication and authorization

Require existing Supabase bearer verification (signature, issuer, audience, expiry, supported session/subject, MFA claims), live non-revoked session, verified email and active backend MFA. Use `Authenticated` and `require_staff(context, 'operations', 'finance')`; no browser/body role override, service-role shortcut, security-definer endpoint wrapper or RLS disabling. Customer, support-only, security_admin-only and superadmin-only users receive 403 unless they independently hold operations or finance. No implied role inheritance. Mixed operations/finance users receive the **same minimized schema**, with no operations-specific enrichment.

Recheck the allowed staff predicate in the representation SQL as existing APIs do. Retain safereturn_api role and orders RLS; do not grant broader access. Do not expose the customer's identity just because RLS internally compares customer_user_id. Owner-based RLS alone is not API authorization: a customer cannot use this staff route even to read their own order.

No mutation means no idempotency key, If-Match, confirmation or extra recent-auth requirement beyond existing privileged-read policy. Preserve current MFA/authentication requirements; any new freshness policy would require separate approval. Session-state account lock behavior is existing auth infrastructure, not a lock on order, pair or fulfillment rows.

## Exact proposed request

Only GET; no request body. Unknown or duplicate query keys and bodies rejected, no expand/include/fields/projection/path/role/customer parameters. Values are bound parameters, never SQL fragments.

| Query | Contract |
| --- | --- |
| order_number | Optional exact, case-sensitive stored match, 1–40 characters, no control/DEL characters; no wildcard/substring/PII search. No implicit trimming or case folding. |
| order_status | Optional enum draft, placed, processing, fulfilled, cancelled. |
| payment_status | Optional enum awaiting_transfer, proof_submitted, under_review, verified, rejected, refunded; stored state only, no reconciliation. |
| created_from | Optional RFC3339 timezone-aware timestamp, inclusive; normalize UTC, preserve PostgreSQL microsecond precision. |
| created_before | Optional RFC3339 timezone-aware timestamp, exclusive; must be greater than created_from if both present. |
| sort | newest (default) or oldest; fixed created_at + id direction only. |
| limit | Integer 1–100, default 20; reject booleans, decimals and alternate encodings. |
| cursor | Optional opaque authenticated/encrypted token, maximum 2048 URL-safe characters. See pagination below. |

Deliberately omit fulfillment_status/filter, fulfillment eligibility, commerce-model branch selectors, item counts, shipping, customer identifiers and monetary search in the first version. Stored fulfillment_status is technically readable from orders without a helper, but omitting it prevents this design from promising or inspecting operational eligibility. Payment_status is merely the persisted enum; this API neither verifies payment nor reads payment records.

## Exact proposed success schema

HTTP 200 application/json. Every object is closed (`additionalProperties: false`); every listed property required. Arrays bounded by limit. No role-dependent fields. Amounts serialize as decimal **strings**, never JSON numbers. Dates serialize UTC RFC3339 with up to six fractional digits; UUIDs use canonical lowercase form.

```json
{
  "items": [
    {
      "order_id": "10000000-0000-4000-8000-000000000001",
      "order_number": "SR-EXAMPLE-001",
      "order_status": "placed",
      "payment_status": "awaiting_transfer",
      "currency_code": "PKR",
      "total_amount": "1250.00",
      "created_at": "2026-10-23T04:15:00.123456Z",
      "placed_at": "2026-10-23T04:16:00Z"
    }
  ],
  "next_cursor": null,
  "as_of": "2026-10-23T05:00:00Z"
}
```

The example uses synthetic documentation values only, not records or fixtures created in a database.

| Property | Exact type/source/constraint |
| --- | --- |
| items | Array 0..limit of OrderMetadata; unique order_id in each page. |
| order_id | UUID string from orders.id; no pair/customer/identity semantics. |
| order_number | String 1..40 from orders.order_number; output safely escaped as text. Unexpected malformed historical identifiers fail contract validation, never repaired in place. |
| order_status | Exact five-value enum defined above from orders.order_status. |
| payment_status | Exact six-value enum defined above from orders.payment_status. |
| currency_code | Exactly three uppercase ASCII letters from orders.currency_code; not hardcoded PKR and not inferred. |
| total_amount | Alias of stored orders.total_pkr, nonnegative NUMERIC(12,2), regex `^(0|[1-9][0-9]{0,9})\.[0-9]{2}$`, at most 9999999999.99; format with Decimal, no float conversion. |
| created_at | Required UTC timestamp from orders.created_at. |
| placed_at | UTC timestamp from orders.placed_at or null; null is meaningful for unplaced records, never invented. |
| next_cursor | Opaque string <=2048 or null; present only if limit+1 fetch found another eligible row. |
| as_of | UTC upper creation-time watermark chosen on first page, repeated through that cursor chain; **not** a transaction-wide snapshot of changing status/amount values. |

No customer_user_id/reference/name/email/phone/address; no payment instructions, bank data, proof or attempts; no product catalog prices; no line/SKU/size/print snapshots, qr type, identity_group, QR count, credentials, pair status, shipment reference, fulfillment status/eligible flag, cancellation context, invoice URL or raw internal JSON. Omitted fields are absent, not fabricated null placeholders. All fields other than placed_at/next_cursor are non-null.

A future UI can show a read-only summary **from these returned values only**, labeled limited metadata. It must state: “Detailed order information is unavailable through the currently approved admin API integration.” Direct full-detail URLs remain unavailable until separately authorized; do not reconstruct them using API-081.

## Query/repository design (not implemented)

Use a dedicated module and response DTO/repository; no `SELECT *`, ORM full-entity serialization, relationships/eager loads, view with hidden functions, generic order-detail service or post-load enrichment. Select only:

`o.id AS order_id, o.order_number, o.order_status, o.payment_status, o.currency_code, o.total_pkr AS total_amount, o.created_at, o.placed_at`

From **public.orders o only**, with `public.sr_is_staff(ARRAY['operations','finance'])`, fixed optional equality/range predicates, `o.created_at <= :as_of`, optional keyset tuple comparison, fixed ORDER BY and LIMIT :limit_plus_one. No FOR UPDATE/SHARE. Direction and comparison are selected from a fixed two-case map, not interpolated caller strings. Bound-filter values appear only as parameters. Do not query related tables to validate amount, identities or fulfillment.

The only allowed database functions on this path are reviewed auth/session/context/staff functions and ordinary built-in timestamp/formatting primitives. This is an allowlist of intended dependencies, not permission to call any function sharing a prefix. orders RLS and all installed policy dependencies must be reverified in the authorized test database before release. Runtime DB connection/session configuration and event hooks must not add an unreviewed callback. No worker, notification, outbox, audit-write trigger, payment reconciliation or template resolution is scheduled by this GET. Existing access/security logging can record request ID, actor, route, status and latency; redact query strings, cursor contents, customer/order data and bearer tokens.

### Cursor contract

Keyset order `(created_at,id)` descending for newest, ascending for oldest; comparisons `<`/`>` respectively. Fetch limit+1; emit at most limit and encode the **last emitted row**, never the extra row. No next_cursor on empty/end pages, no total/count/page-number fiction. Preserve original filter set during Next/Previous; Previous can replay stored page-start cursors. Reset cursors on filter/sort/limit change. Empty exact lookup is 200 with items empty, not 404.

Use a dedicated namespace with the existing reviewed AEAD/profile-crypto primitive (not the old unauthenticated cursor decoder). Token envelope version, key version, actor ID binding, authorization contract version, canonical hash of all filters including limit/sort, UTC as_of, exact microsecond last created_at, last UUID and 15-minute absolute expiry. Bind route namespace and actor in authenticated data; do not expose plaintext internals. Subsequent pages retain the original expiry/as_of; rotation must fail closed if the old key is unavailable. Cursor schema and canonicalization are versioned and specified in implementation tests. Token is no substitute for live authorization. Copied between actors, changed filters, tampering, unknown version, invalid timestamp/UUID, overlength or expiry → 422 INVALID_CURSOR. Auth/role failures take precedence over cursor validation.

Configured crypto keys are an operational prerequisite, not a new database table; never synthesize keys or reuse QR secrets. Existing crypto helper review and a worst-case encoded-token length test must confirm the 2048 bound before contract approval. Missing/invalid crypto configuration → sanitized 503, no unsigned-token fallback.

Creation watermark excludes normal new rows after the first page, but backdated inserts/deletions and changes to mutable status filters can change membership between requests. It is not snapshot isolation across HTTP calls; immutability of financial snapshots is independent of pagination consistency. If strict repeatable exports become a requirement, design a separate authorized reporting contract rather than adding hidden snapshot tables here.

## Historical pricing, snapshots and identity semantics

Current product price_per_copy is PKR and common across sizes. The combined configured copy ceiling is 100 under Amendment v1.4; historical unit_price_snapshot/line_total and aggregate amounts retain the server quote after catalog edits. The proposed API reads aggregate total_pkr only; it never multiplies today's price by quantities, joins products/variants, updates snapshots, backfills currency or “fixes” legacy totals. Although the column is named total_pkr, currency_code is authoritative for display: a legacy USD record returns USD and the same stored number, with no conversion or PKR relabeling. Unexpected unsupported currency/invalid amount fails closed and is reviewed outside this endpoint.

OrderItem, OrderLogicalItem and OrderItemSize show that line/size snapshots exist and could support a separately reviewed purchase-metadata extension. They are not needed here and are not queried; print_spec_snapshot and identity_group are specifically excluded. No unit price or size-level price is invented for this aggregate response. Financial snapshots remain immutable under existing rules; order/payment statuses are current mutable metadata, not immutable historical values. Nothing here claims all draft totals are final.

Exactly one unique QR identity per logical item remains the domain rule, independent of copy count. This API neither checks nor exposes whether that rule has been fulfilled. No identity count is inferred from item/size/copy quantities, and no QR information is returned.

## Transport, errors and future frontend boundary

Reuse approved error envelope with required `error: {code, message, message_ur, request_id, details}`; details is empty or fixed non-sensitive field identifiers, never provider/SQL text or echoed inputs. Proposed statuses: 401 AUTH_REQUIRED (missing/invalid/revoked session); 403 FORBIDDEN (email/MFA/role); 422 VALIDATION_ERROR / INVALID_FILTER / INVALID_DATE_RANGE / INVALID_CURSOR; 405 METHOD_NOT_ALLOWED; 429 RATE_LIMITED if existing gateway/read budget applies; 503 PROVIDER_UNAVAILABLE for DB/auth/crypto/response-contract failure. No resource-level 404 needed for exact list lookup. Do not promise a new rate-limiter implementation as already available; confirm infrastructure limit policy before release.

`Cache-Control: private, no-store`, nosniff, no-referrer and request ID on success/errors. No redirect following, authenticated public CDN cache or sensitive diagnostics. Proposed request URL cap 8 KiB; bounded upstream JSON response 512 KiB (100 minimized rows fit); invalid/oversized response fails closed. Browser request is GET-only with no body, same-origin BFF checks rejecting cross-site/mismatched Origin when supplied; backend retains existing CORS/auth rules. No unsafe methods supported; no new CSRF exemption or auth config changes. Status/amount values are HTML-escaped, never rendered as markup.

After separate approval and backend implementation, a dedicated fixed-target relay may use existing verifiedSession/staffState, enforce orders.read plus actual roles/MFA and forward only this exact endpoint/query schema. Do not extend the current broad orders relay with a generic selector or mount OrdersConsole; no payment/ship/detail calls on rendering, prefetch or navigation. Customer/admin independent deployment configuration remains unchanged. The current broader legacy entry points remain unchanged by this design, and must not be used for acceptance tests.

## Database feasibility and dependencies

**No mandatory schema change for correctness identified.** All eight row fields exist in orders; data minimization is an explicit SELECT and closed DTO; current orders SELECT RLS and staff/session checks have no pair dependency on the reviewed path. No materialized view, new SQL function, new permission, schema migration or backfill is required by this minimal design. SELECT does not execute DML triggers or FK checks. Existing update/fulfillment business rules remain untouched.

This is not a claim that the broader runtime role cannot read other tables: safereturn_api is shared and existing RLS is broad. Enforce the narrow path in code, contract tests and SQL dependency checks; do not claim column-level DB isolation that does not exist. Installed grants/RLS may differ and must be inspected in a separately authorized test environment. Any need to alter them becomes a new review blocker, not automatic permission to broaden grants.

Primary key and unique order_number exist. The known customer/created_at index does not guarantee efficient global staff keyset scans. No dedicated global `(created_at,id)` index was identified in reviewed migration definitions. Test representative worst-case filters/sorts with an authorized PostgreSQL plan and statement timeout. An additive performance index could become necessary at scale, but would require its own explicitly approved migration; do not call the current proposal schema-dependent before measurement, or claim production performance from bounded response size.

Implementation dependencies if approved: new backend route/closed schemas + dedicated orders-only query module; existing auth/runtime/Decimal/AEAD utilities reviewed for this namespace; explicit registration/OpenAPI and approved operation ID; configured crypto/DB/auth prerequisites; independent tests. Then, only after backend acceptance, a fixed server relay and existing Orders UI adaptation under a new strict module allowlist. Existing API-080/API-081, checkout, pair services/functions, fulfillment rules and migrations remain unchanged throughout.

## Required verification before implementation/release

Design/contract approval comes first. The following are **planned tests, NOT RUN**:

1. Static call graph/SQL allowlist: only orders plus auth/session/staff/security-state tables for this route, no related entity loads, no fulfillment/template resolver, pair/QR/QA/allocation/owner helper, worker/outbox or write. Inspect actual installed RLS/function dependencies and SQLAlchemy hooks. Fail if new enrichment or extra response field is introduced.
2. Auth matrix with actual existing verification: unauthenticated/expired/wrong-signature/revoked/banned/deleted session → 401 as appropriate; unverified email/no MFA/role revoked → 403; operations, finance and mixed users receive identical minimized schema; support/security/superadmin/customer-only denied. Verify own-order RLS cannot bypass staff guard, and final-check revocation fails closed. No real credentials in fixtures/logs.
3. Isolated PostgreSQL/RLS test under actual safereturn_api context, seeded only through inspected direct test fixtures: orders with financial/status metadata and reviewed auth/session records; no pair/QR rows, checkout, workers or prohibited API/setup/teardown calls. Ensure safe output works for both legacy and single_qr order metadata without validating their workflows. Capture executed application SQL and review policy dependencies; reject all prohibited function/table accesses, not merely prohibited HTTP URLs. Do not invoke an excluded helper just to see it fail.
4. Filters: exact case-sensitive order_number, enum values, UTC offset/microsecond ranges, inclusive/exclusive boundaries, invalid range, unknown/duplicate query keys, body/expand/path rejection, parameterized injection payloads, newest/oldest stable UUID ties. No client-only search presented as global.
5. Pagination: 0/1/limit/limit+1, multiple pages each direction, last emitted tuple, no duplicates for unchanged data, filters preserved/reset, actor/filter/limit/sort-bound expiry/tamper/rotation, max token length and timestamp precision. Test documented concurrent insertion/status/deletion behavior without claiming snapshot exports.
6. Data minimization/serialization: exact closed keys, Decimal zero/maximum/two-decimal formatting without float loss; stored PKR and legacy non-PKR values; null placed_at; malformed stored timestamps/currency/money reject safely. Catalog-price-change regression must not change historical returned totals; fixture must not call checkout/catalog mutation APIs. Do not assert a draft amount is a confirmed purchase.
7. No business mutations: no DML/sequence/job/notification writes or order/pair locks on the query path. Allow only existing auth transaction setup/advisory lock. Metadata does not verify payments or infer QR/fulfillment state. Observe logging redaction and no-store error/success headers.
8. HTTP/BFF deny-by-default test: exact GET proposed path only, never generic /admin/orders or details, allocation, payments, print, shipment, pair APIs. Fixtures/setups/teardowns inspected before execution. Synthetic negative requests go only into a local fixed relay validator; no prohibited backend requests. Response size/content-type/redirect/timeout/malformed/provider failures fail closed. Do not run broad legacy suites.
9. After separately approved UI work: existing table/filters/Next-Previous/refresh/limited summary/direct refresh, no mock fallback, null handling and current stored currency; viewport checks 1366×768, 1440×900, 768×1024, 375×667; keyboard focus and long identifiers. Network interception and SQL assertions prove zero excluded calls, including prefetch/background rendering.
10. Acceptance evidence must distinguish isolated doubles, actual PostgreSQL/RLS, deployed auth and real browser checks. No test of this proposal has run in this audit. Existing phase test results are historical, not validation of a nonexistent endpoint.

## Review blockers and approval boundary

1. **Contract approval pending:** new named path, response alias total_amount, role scope, omitted fulfillment/customer fields, query set, cursor design and OpenAPI ID need review; no silent expansion of the existing audit allowlist/counts.
2. **Implementation absent:** no handler/repository/relay/schema registration/test/UI connection exists for this proposal. Existing Orders integration remains blocked; no frontend-only workaround.
3. **Environment verification absent:** actual installed schema/grants/RLS/session definitions and safe crypto configuration require authorized test acceptance. No DB/environment probed here.
4. **Performance unverified:** representative query plans/global keyset index may require separately approved work; no schema change made or promised unnecessary at all scales.
5. **Capability limitations intentional:** no full order details, customer directory/profile lookup, line/size/identity counts, fulfillment eligibility, shipment/payment context, exports or mutations. Additional fields require their own safety/privacy review.
6. **Existing risks not remediated here:** legacy Orders console/relay entry points remain in source, unchanged and unmounted. Approval of this metadata design would not authorize them. Previous Products/Templates live acceptance and template publication blockers also remain.

Requested review decision: approve or revise this independently named, orders-only minimized read contract and its test/dependency boundaries. Implementation must be a separate explicitly authorized task after review; this proposal does not itself add any endpoint to the strict runtime allowlist.
