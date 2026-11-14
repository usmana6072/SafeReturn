# SafeReturn — AI Agent Instructions & Coding Standards v1.2

> **Owner-delegated contract review, 2026-10-19:** [BTR-20261019](SafeReturn_13_Blocked_Task_Contract_Review_2026-10-19.md) records reviewed/corrected decisions for all thirteen formerly blocked task cards. Its explicit design approvals amend conflicting proposals for those tasks only; runtime roles, live/destructive authorization and existing acceptance evidence are unchanged. Provider/legal/physical/recovery gates remain explicit. Reserved API IDs are contracts, not implemented endpoints.


**Document ID:** SR-AGENT-004 | **Version:** 1.2 proposed implementation governance | **Updated:** 12 October 2026  
**Project:** SafeReturn — Lahore pilot | **Repository target:** `docs/05-agent-instructions.md`  
**Audience:** Founder, Codex, Google Antigravity, development team, reviewer, security/finance/operations owners  
**Scope:** Agent permissions, step-by-step delivery controls, implementation conventions, architecture invariants, test gates, PR and release evidence.

> **Document reading rule:** Part A is the **current v1.2 agent policy**, including the v1.1 rules it explicitly retains. Part B is the complete supplied v1.1 policy preserved as an archived reference for unchanged details. When conflicting, follow the approved PRD and ADRs, then v1.2 TDD/DB/API, then Part A; do not implement conflicting archived examples. This is a proposed coding policy, **not proof of deployment, tested migrations, verified external vendor capability or security certification**.

# PART A — CURRENT v1.2 POLICY

## 0. How agents must read the project

### 0.1 Governing sources and precedence

1. **`docs/01-PRD.md` v1.2**, including the founder-approved multi-product and multi-pair amendment (FR-201–FR-211) and the unchanged v1.1 rules.
2. Approved founder Architecture Decision Records (ADRs), contractual pricing/security/operational decisions.
3. **`docs/02-technical-design.md` v1.2**: bounded FastAPI modular monolith, scan activation, providers, workers, and QR print architecture.
4. **`docs/03-database-design.md` v1.2**: relational contract, migrations, reservations, order QR occurrences, payments, privacy, retention.
5. **`docs/04-api-contract.md` v1.2**: API-001…existing contracts, additive API-200–244, error/DTO semantics, OpenAPI fragment governance.
6. This v1.2 agent policy, followed by implementation backlog, security, tests, deployment, physical SOP and UI/UX specifications. Documents 06–11 currently supplied as v1.1 must be updated before claiming complete cross-document v1.2 consistency.

**Precedence rule:** A coding agent may not decide unresolved product/business/security questions by choosing the easiest implementation. Describe discrepancy, cite document section or contract ID, propose options, wait for necessary founder approval on affected critical paths; unrelated tasks may proceed. Archived sections are not independent directions to deploy obsolete assumptions. The original full v1.0 PRD is not among these supplied sources; do not assert that it was fully verified.

### 0.2 Agent startup checks (mandatory)

- Inspect actual repository, branch, dirty state, environment/example configuration and relevant tests before changing files; do not assume code exists merely because documents propose it.
- Read root `AGENTS.md` if present and this complete policy; read task-relevant PRD/TDD/DB/API sections, current migrations, and release state.
- List involved UI routes, API endpoints, DB relations, roles, states, background jobs, webhooks, file objects and security invariants.
- Identify which rules are **P0 operational** vs **P1 schema-ready but feature disabled**.
- Draft bounded files/edits/test plan with acceptance evidence and rollback. Obtain approval before new high-risk requirements, destructive migrations, production deploys or real fund verification.
- Execute one bounded task per branch/worktree. Don't allow two agents to simultaneously edit migration chains, the same transaction service or shared generated contract.

### 0.3 Never silently make these changes

Never independently alter: pair ownership or activation semantics; verification of bank payments; activation-credential custody; publicly exposed emergency information; minor/guardian consent; medical publication and contact reveal behavior; retention/legal holds; live payment providers; pricing; new-product launch; production credentials, DNS, payment accounts; production migrations or deletion; or source of truth. Do not treat screenshots, webhook payload text, spreadsheet rows or AI opinions as trusted settlement events.

## 1. Canonical cross-domain invariants

| ID | Rule | Mandatory evidence |
|---|---|---|
| AG12-001 | One *new* QR pair has exactly one current Lost and one current ICE identity, one Pair ID, one separate concealed activation secret; ownership is pair-level. | PostgreSQL constraints, atomic activation/replacement tests |
| AG12-002 | Any user can own multiple distinct pairs. Each tag has its own independent editable per-tag profile. | Cross-pair isolation, lost/ICE edit tests |
| AG12-003 | Three physical copies of one Lost QR are three artwork occurrences, **not** three identities; editing that QR changes all copies. | Order/PDF count assertions |
| AG12-004 | Future keychain/badge may print an eligible already-owned QR or ask for one new complete pair; never mint an unpaired independently owned child by accident. | Mode, ownership, feature-flag tests |
| AG12-005 | Only sticker SKUs sold at P0; product/variant/schema foundation present, future publishing/reuse gated for P1. | Flags and catalog/API tests |
| AG12-006 | Order history stores product and variant IDs **plus immutable purchase-time name, SKU, specification and price snapshots**. | Update/archive product regression tests |
| AG12-007 | Reservation and final allocation are unique, transactional and race-safe; submitted payments undergoing review must not be released casually. | Last-pair concurrency, late-payment tests |
| AG12-008 | Payment amount/order linkage and normalized status are provider-independent; current manual finance review is required; future gateways must verify signed events and settlement. | Provider contract tests and replay tests |
| AG12-009 | Supabase PostgreSQL is authoritative, private Supabase Storage holds payment evidence and print PDF; Cloudinary only approved public product media. | Authorization and private URL tests |
| AG12-010 | Google Sheets is masked, asynchronous finance reporting only; failing sync never revokes trusted paid status. | Outbox/retry/dedupe tests |
| AG12-011 | Print pages contain the correct sizes and purchased Lost occurrences **before** ICE occurrences; center logo cannot break scanning or quiet zone. | Manifest/PDF and physical scan QA |
| AG12-012 | Temporary PDF/evidence cleanup is policy-driven, auditable, legal-hold-aware; durable order, printed copies and payment outcome remain. | Retention, failure, reprint tests |
| AG12-013 | Scanning unactivated QR offers activation; pre-auth context survives login; only an entitled verified account may claim and activate the full pair. | Redirect/session, hijack and expiry tests |
| AG12-014 | Public Lost/ICE scanning is anonymous; no unapproved owner data leaks; full ICE contact never in initial SSR/HTML/hydration/API payload. | Public privacy/network tests |
| AG12-015 | WhatsApp is opt-in and reveals selected number; location is optional and one-time; finder message + notification outbox transaction is atomic. | Consent/privacy/outbox tests |
| AG12-016 | Customer/admin/catalog/finance/fulfillment roles are verified server-side; every mutable owner resource checks ownership at each operation. | Cross-owner and role matrix tests |
| AG12-017 | Every meaningful mutation uses applicable idempotency, transaction, versioning and audit. | Retry, conflict and audit tests |
| AG12-018 | Public bilingual English/Urdu interface; accessible scan and emergency experience; planned dashboard translation scope follows approved UI spec. | RTL and accessibility tests |

## 2. Supported technology and trust boundaries

- Frontend: **Next.js App Router, TypeScript, Tailwind**, reviewed server/client split, translated `en`/`ur` public pages; Next.js page routes are not FastAPI routes.
- Backend: **FastAPI + Pydantic**, modular monolith. The original v1.1 baseline adopts **SQLAlchemy 2.x and Alembic**. Although future development can use explicit parameterized SQL in reviewed repositories, **a raw-SQL-only rewrite is not silently authorized** by these documents; record and approve any change of persistence architecture.
- Supabase Auth for identity; Supabase PostgreSQL with least-privilege business DB access; private Supabase Storage for proof/PDF; private storage access only through audited backend grants.
- Cloudinary for public product images and approved media; hosted media URLs must be from validated allowlisted origins. No production PDFs, sender-account evidence, private medical notes or activation inserts in public image/CDN buckets.
- Resend transactional email via existing durable outbox; independent queue/job worker for printing, finance mirror and cleanup (reuse durable Postgres outbox/leases). Use rate limits and adaptive protection for ICE contact reveal; no mandatory blind CAPTCHA when emergency fallback policy demands access.
- Google Sheets restricted service-account **reporting mirror**. No direct customer browser service account access.
- Manual bank/Raast provider adapter P0. Gateway/webhook P1 is disabled until selected, authenticated, signed, replay-tested and approved.
- Hosting: Vercel frontend, Railway API and separate worker are **proposed**, subject to actual provider checks; never assert vendor pricing/limits without verification.

**Always separate:** transport/controller → authorization/validation → service transaction → repository/DB → durable event → worker/provider adapter. No external provider request while holding critical DB locks. No asynchronous fire-and-forget in request handler as the sole durable processing mechanism.

## 3. Repository and module organization

Proposed layout from TDD v1.2; adapt to real existing repository without destructive refactor:

```text
safereturn/
  AGENTS.md
  .env.example
  .gitignore
  docs/01-PRD.md ... 11-ui-ux-spec.md
  frontend/
    app/                    # public, auth, customer, admin routes
    components/
    features/               # QR, activation, shop, orders, catalog, admin
    lib/                    # typed API, auth, i18n
    messages/en.json
    messages/ur.json
    tests/
  backend/
    app/
      main.py
      core/                 # config, logging, errors, audit
      api/v1/               # thin routers and request/response DTOs
      domains/
        catalog/ inventory/ activation/ profiles/ checkout/
        orders/ payments/ printing/ fulfillment/
        finder/ contact_reveal/ notifications/ admin/
      db/                   # sessions, repositories and model mappings
      integrations/
        supabase_storage/ cloudinary/ google_sheets/ payment/
      worker/               # durable jobs, leases, retry, cleanup
      security/
    alembic/                # reviewed migrations only
    tests/unit/
    tests/integration/
    tests/contract/
    tests/security/
  .github/workflows/
```

For a task that needs a small implementation, keep it small: one cohesive router, service, repository and adapters as needed. No circular imports, miscellaneous `utils.py` business logic, duplicate payment status engines, or massive catch-all `main.py`. No extra frameworks unless a measured task requires them.

## 4. Mandatory task protocol and response evidence

1. **Inspect:** task ID, requirements/endpoint IDs, repository, tests, migrations, branch state.
2. **Design:** state sequence, ownership, transaction boundary, feature flag, rollback, error contract, idempotency, retention impact.
3. **Agree scope:** present files to change, risks, acceptance cases, open ADR blockers. Do not invent required customer/business decisions.
4. **Implement:** minimal cohesive diff, parameterized DB operations, typed DTOs, DB constraints, audited privileged commands, no secrets.
5. **Test:** unit, real PostgreSQL integration for locking/constraints, OpenAPI diff, Playwright for customer journeys, physical QR sampling as appropriate.
6. **Review:** run lint/static/type/security checks supported by actual repository; inspect changed SQL and secrets; verify provider failures and retries.
7. **Report:** changed files, exact commands and outcomes, contracts updated, migrations and rollback, unresolved risks, what is not tested. Never say production-ready on simulated tests alone.

Require a real verification artifact or reproducible command output for any “passed” claim. Mark mocks as mocks. Don't fabricate CI, screenshots, print QA, finance settlement or live provider validation.

## 5. Python, API and domain service standards

- Python type hints for service boundaries and repository methods; Pydantic request models use `extra='forbid'` for sensitive commands; Decimal for PKR, timezone-aware UTC datetimes, UUID identifiers, bounded strings and sizes.
- Thin HTTP routers validate schema and identity, call services; services enforce invariants and transaction lifecycle. Never trust submitted `owner_user_id`, role, price, currency, printed tag token, reservation state, pair entitlement or Cloudinary URL.
- Use precise safe error codes from Document 04: `AUTH_REQUIRED`, `FORBIDDEN`, non-disclosing `NOT_FOUND`, `CONFLICT`, `QR_REVOKED`, `VERSION_MISMATCH`, `FILE_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `RATE_LIMITED`, `PROVIDER_UNAVAILABLE`, `IDEMPOTENCY_KEY_REUSED`.
- Match `/api/v1` route registry precisely, retaining v1.1 compatibility: existing API-030–032, API-040–049, API-060–064, API-080–096; additive API-200–244. **API-090** remains batch generation; **API-241** canonical v1.2 payment review; legacy API-083 compatibility must not become a separate review implementation.
- `Idempotency-Key` on payment/order/reservation/activation/print commands; same key+same canonical payload returns stable result; same key+different payload is `409`. Prefer DB uniqueness; not only process memory.
- Require optimistic version/`If-Match` for mutable profiles/product inventory metadata; return 409/412 for stale updates, never last-writer-wins for sensitive preferences.
- Only render public QR links from verified canonical origin and secure high-entropy server token. Never put activation credential in QR URL or logs.
- Audit sensitive state transitions with actor, role, target, timestamp, reason, previous/new state, safe request ID. Avoid full medical info or payment identifiers in audit text.

## 6. Catalog, variants, images and order snapshots

- `products` (name, category, description, published/featured, etc.) are **not QR identities**. `product_variants` define SKU, optional size/material/color, price/availability, production template. Images are Cloudinary media references with consistent alt text and ordering.
- Launch only approved QR sticker variant(s); unapproved keychain, badge or multi-product publishing must remain blocked by feature flags and server checks (not merely hidden in frontend).
- Admin catalog staff may create, update, publish, feature and archive under permissions defined in Document 04 (API-220–229). Do not hard delete referenced products/variants; preserve history and verify variant-specific manufacturing template before allowing sale.
- Featured-products homepage carousel uses `GET /public/catalog/featured` (API-201) and public catalog endpoints, responsive keyboard-accessible arrows plus swipe, and "View all" path; never hardcode active products in UI.
- Snapshot purchased `product_id`, `variant_id`, product name, SKU, variant attributes, unit price, quantity, rendered specification and currency at quote/order confirmation. Product edits later must never rewrite past order descriptions or totals.
- Separately store QR uses/copies for lines; never conflate order line quantity, new pair units, unique QR count and physically produced copies.

## 7. Independent QR profiles, ownership and activation

- A user can own **many** pairs. Every pair always has one current `lost` and one current `ice`. Each QR has its own profile; profile edits scoped by `qr_id` and authenticated pair ownership.
- Existing lost-item and ICE profile CRUD from API-040–049 remains the profile authority. New API-205/206 expose owner-scoped tag collection/detail; avoid duplicating profile persistence in a product table.
- Reusing an existing QR on a future physical item (P1) must verify tag ownership, non-revocation, print eligibility and explicit user choice; edits intentionally affect all physical copies sharing the URL. Choosing a *new identity* creates a **new complete pair**; do not create an independent one-child owner record.
- Public scan of an unactivated QR presents an activation action but no private pair/owner data. API-207 can expose only minimal safe activation context; API-208 creates a scoped expiring activation intent. Authentication redirect preserves opaque context through approved state/session handling, never raw secrets in query parameters. Account must pass entitlement/secret requirements; wrong owner cannot claim by merely having token.
- API-032 activates both current tags atomically with pair-level ownership, after verified entitlement. Retries are idempotent; failed child activation rolls back. Lost/ICE public scan never requires finder login.
- For minors/elderly medical use, keep guardian/legal approval and safe-default data publication behind product and public-profile policy controls; do not expose addresses or medical details merely because product SKU indicates a child's badge.

## 8. Checkout, QR copies, transactions and inventory

- Customer chooses size/variant and **Lost/ICE copy counts separately**; e.g. 3 Lost + 2 ICE on one new pair = **two unique QR identities** and **five PDF sticker occurrences**. Additional sizes create separate variant lines but don't mint extra pair IDs.
- Quote via API-203 includes authoritative server price, delivery, taxes/discount rules, address/contact snapshot, quantities and expiration. Confirm via API-204 and/or approved API-060 order flow; **do not create two independent order/reservation paths**. Validate approved feature flags and cart line consistency.
- At checkout, lock eligible QA-accepted unsold pairs (e.g. `FOR UPDATE SKIP LOCKED`) and establish exclusive TTL reservation within an ACID DB transaction; handle stock exhaustion without oversell. Approval→final allocation is idempotent and transactional.
- Payment under review requires a protected/review state; reservation expiry alone cannot release it while credible payment may be settling. Have a documented maximum review/grace/reconciliation policy, late-settlement exception path and owner/admin visible status. Never silently reassign an already settled/printed pair.
- A future existing-owned reprint order need not reserve new pair inventory; link line to eligible current owned QR and apply reprint/abuse/fulfillment authorization. Multiple new pairs per order require explicit rollout approval and correct line→pair mapping.
- DB constraints and service checks together enforce: one current Lost and ICE per pair; one live exclusive allocation/reservation; integer positive copies; QR type matches requested use; existing-owned QR belongs to user; line quantity = sum of QR use copies across relevant rows.

## 9. Payments: replaceable verification and secure evidence

- Create provider-independent `payment_attempts` and normalized payment status, linked to immutable order total/currency. Keep provider-specific details behind `PaymentProvider` interface/adapter.
- Manual P0: customer supplies sender holder and account identifier/reference as allowed plus optional screenshot. Capture intent/attempt, uploaded proof reference, timestamp and `under_review`, never `verified` solely because customer clicked Confirm or screenshot exists. Finance role + MFA independently verifies settlement from a trusted bank channel.
- Future gateway P1: add adapter and authenticated webhook (`POST /payments/webhooks/{provider_key}`, API-214). Check provider signature, timestamps, matching order/amount/currency, replay/deduplication, terminal status semantics and DB state transition. Do not expose bank credentials or implement signature verification from untrusted headers without provider-specific audited logic.
- Single normalized `PaymentVerified` transition drives downstream allocation, print job and finance sync **once**. Repeated admin clicks or webhook deliveries must be idempotent. Reject invalid transitions/refunds/races with appropriate escalation rather than overwriting verified state.
- Evidence uploads: API-211 generates short-lived narrowly scoped authorization to private Supabase bucket, API-212 validates size, MIME/magic, object path ownership, attempt and upload state; scan/re-encode or quarantine as risk policy requires. Sender account numbers and names must be protected/redacted in logs and finance mirror.
- An explicit provider-disabled feature flag prevents accepting unconfigured gateway payments. Always preserve original order IDs, allocations, fulfillment and finance audit during eventual migration to automatic verification.

## 10. Storage, Cloudinary, PDF rendering and production QA

- **Supabase Storage:** private payment proof objects and temporary private print PDFs with short-lived authorized download grants, backend checking payment/fulfillment/role. Do not assume a storage URL grants access correctly; verify bucket policy and signing behavior.
- **Cloudinary:** approved public product marketing images; validate file type, transform sizes, pixel dimensions, alt text, folder and deletion on archive according to policy. Never upload a private PDF/screenshot there to simplify implementation.
- PDF must be generated **after verified payment and final allocation**, from immutable order item snapshots, QR-use rows and an approved template version. Render Lost first then ICE; correct exact physical size, 4-module quiet zone, centered small logo, bilingual labels, cut guides and print-accurate scale; never scale PDF to fit unpredictably or embed visible secret credentials.
- Optimize with vector QR paths/SVG, small logo assets, reuse identical vector objects, compress resources and avoid full-page rasterization. Measure actual byte sizes in fixtures; do not invent fixed universal MB limits. Store content checksum, bytes, template revision, object key, expiration and job state.
- Only verified+allocated+PDF-ready+QA-approved orders reach the appropriate Ready to Ship state. Distinguish "print-ready", physical QA, "packed", "shipped", "delivered"; download alone is not evidence of shipping.
- Reprints require authorized reason, audit, revalidation of current tokens and production revision. Old revoked QR must not be reprinted. Activation code inserts have a separate secure template and custody flow.
- Cleanup of PDFs is after verified delivery and approved grace/dispute/hold policy (delivery + 7 days is a *candidate*, not a binding law); evidence has separately approved dispute/retention policy. Delete object with idempotent job, update artifact tombstone, preserve metadata, order snapshots, pair/tag identities, payment decision and print counts. Respect active jobs, legal hold and reconciliation. Deletion of remote object is not transactional with Postgres: plan retries and reconciliation.

## 11. Google Sheets finance reporting

- Sync from durable, committed DB `payment` and `order` changes through separate event/outbox worker. A Sheets outage does not block approved payment, shipping transition or customer status.
- Sheet row uses stable `order_id`/`attempt_id` correlation, masked sender identifier, amount, method, reviewed status/time and authorized reference — no full bank identifiers, plaintext private URL, raw screenshot, private medical details or service secrets.
- Idempotent upsert or deduplicated append with unique external event key, exponential retry, worker lease, dead-letter/exception visibility, and authorized manual retry via API-238/239. Never accept Sheet edits as finance authority or read them back to mark paid.
- Restrict spreadsheet/service-account scopes and sharing; support integration disabled mode without compromising core order flows.

## 12. Security and privacy invariants retained from v1.1

These controls are unchanged and **must** remain implemented even if v1.2 task focuses on commerce:

1. Unauthenticated finder and ICE views expose only approved published public data, without account registration or payment prompts.
2. Full ICE numbers absent from initial HTML, SSR/RSC payloads, hydration, metadata and public profile API; reveal only through separately protected, rate-limited request with approved emergency fallback.
3. WhatsApp off by default; enabling warns explicitly that selected phone number becomes available to QR scanners; WhatsApp chat is external and not part of SafeReturn finder inbox.
4. Browser geolocation asked only upon user action, one-time optional consent, denial nonblocking; minimize, encrypt and retain according to approved schedule.
5. Finder message and durable email outbox entry insert in the **same DB transaction**; outbox worker retries Resend; at-least-once dispatch is not a guarantee of one email or successful inbox arrival.
6. Public QR tokens use CSPRNG high entropy, never activation credentials; no token or sensitive payload in ordinary logs/analytics; revoke old tag tokens on replacement while preserving audit history.
7. Sensitive staff mutations use server-controlled roles, MFA, audit, and least privilege. Service-role keys never reach frontend; do not rely on RLS if backend uses a bypass key.
8. Public content bilingual Urdu/English with correct RTL, numeric bidi, accessibility and mobile low-bandwidth behavior; test physical printed bilingual captions.
9. No production live settlements, provider account actions, data deletion or emergency policy changes performed by AI without explicit operator authorization.

## 13. Database, migrations and schema-governance rules

- Before touching SQL, inspect current migrations and the *real* schema. The v1.2 DB SQL includes **logical target DDL**, not safe drop-in migrations for an already populated database; author additive Alembic revisions with controlled backfill.
- Do **not** create parallel replacement `order_items` or duplicate payment state tables because target examples use `CREATE TABLE IF NOT EXISTS`. Reconcile with historical schema. Never edit `auth.users` or Supabase-managed `storage` tables.
- Use named CHECKs/UNIQUE/FK/indexes, UUIDs, UTC timestamptz, numeric money and parameterized SQL. Make explicit transactional isolation/locks and test with PostgreSQL, not SQLite, for races.
- Apply expand → dual-read/backfill if necessary → validate → contract, test on staging with sanitized realistic records and production-like RLS. Provide roll-forward recovery and snapshot/restore constraints; no destructive startup migrations or unapproved live migration.
- For consistency of QR uses and orders, verify same order linkage, pair unit, tag type, current non-revoked token, positive quantities, account ownership, and sum of per-item copies. Cross-row invariant checks belong in locked service transactions or reviewed constraint triggers, not unprotected frontend logic.

## 14. Frontend/UX agent rules

- Implement exact UI route and screen contract as the approved final UI/UX specification is revised to v1.2. Do not invent routes because an API endpoint exists, and do not treat API-xxx as a Next.js route.
- QR activation: show non-activated public state with Activate CTA; store minimal opaque scan context across login/signup then return to confirm without rescanning. Recovery handles expired/invalid/claimed intents with safe localized states. Ensure assistive tech supports flow.
- QR dashboard: list many pairs with per-tag cards. Manage separate Lost and ICE profile editor per QR; never bind both cards to one shared form object by default. Same QR's multiple physical copies clearly share an identity/profile.
- Cart: independent lost/ICE size/copy selectors, pricing from server quote, shipping/contact review and payment status progression. No hardcoded final totals. Do not show `paid` until trusted backend confirmation.
- Admin catalog: products, variants, images and published/featured flags; responsive homepage featured carousel with keyboard controls, swipe, lazy media and graceful empty state.
- Admin ops: inventory low-stock, Generate Batch (API-090), payment review, Sheets sync exceptions, print queues, Ready to Ship, print QA and delivery status. File actions require signed limited grants and staff authorization.
- Test loading/empty/error/offline and Urdu states; do not hide critical payment/retry errors behind generic toasts. Redact bank identifiers and medical info from UI analytics and client logs.

## 15. Testing policy and release gates

### 15.1 Required suites

| Level | Representative must-pass scenarios |
|---|---|
| Unit | Decimal money, copy count validation, status transition guards, new/existing QR selection, entitlement rules, QR logo layout bounds |
| DB integration | Pair uniqueness/atomic activation; reserved last pair race; payment under-review expiry; cross-order QR use; archival and immutable snapshots; retention holding |
| API contract | Exact API-200–244 schemas, v1.1 compatible endpoints, Auth/RBAC/MFA, idempotency, 409/412 version checks, max payloads |
| E2E | Scan→signup/login→return→activate; own multiple QR editors; custom size/cart→payment→review→order status; admin print/ship |
| Security | IDOR cross-user/profile, unowned existing QR checkout, contact/medical leak, screenshot access, forged gateway webhook, sheets permissions, path traversal |
| Production/physical | Logo-centered QR scan after print on target phones/sizes, cut/quiet zone, correct PDF occurrences, printer scale, credential concealment |
| Resilience | Worker restarts/leases/dedupe, provider timeout, repeated finance approval, Sheets offline, storage delete error, paid-but-PDF-failed recovery |

### 15.2 Stop-ship criteria

- Any leak of activation secret, full ICE number in initial payload, private evidence to unauthorized browser, or child-profile cross-owner edit.
- Any double allocation, loss of paid order, misbound pair, screenshot-only automatic approval or spoofable payment webhook.
- Any PDF whose token, count, type or size differs from paid order; unscannable printed logo layout; unauthorized Ready to Ship access.
- Any unreviewed destructive migration, secret exposure or inability to safely replay outbox/worker operations.
- Any severe anonymous emergency availability regression or failure to deliver required Urdu/English public content.

### 15.3 Example commands (only where configured)

```bash
# Run only after inspecting actual repository/toolchain:
# backend: pytest -q && alembic check
# frontend: npm run lint && npm run typecheck && npm run test
# browser: npx playwright test
# compare generated FastAPI OpenAPI with approved contract and documented diffs
```

Never claim these commands exist or passed without inspecting current scripts and actual logs. CI should block unreviewed migrations, critical failed tests and contract drift.

## 16. OpenAPI and contract lifecycle

- Document 04 v1.2 is a Markdown specification with **OpenAPI 3.1 fragments**, not an already validated standalone `openapi.yaml`; generate canonical FastAPI `openapi.json` in implementation and review every route/DTO/security/error diff.
- ID discipline: API-207 public safe activation context; API-208 authenticated intent; API-203/204 quote/confirm; API-209–214 payment; API-220–229 catalog; API-230 stock; API-232–237 prints/Ready to Ship; API-238–244 Sheets/evidence retention and payment review. Preserve v1.1 API IDs and all defined security semantics.
- Before changing a schema, update and cross-check DB migration, Pydantic models, UI API typing, contract tests, docs, versioning and consumer compatibility. Don't amend the OpenAPI schema to paper over an implementation bug.

## 17. Branching, review, release and secret hygiene

- One scoped issue/branch/worktree per agent. Never overwrite user's uncommitted files, force push or skip tests. Use reviewed migrations and release approvals.
- `.env.example` contains **names only**, never values. Keep production `SUPABASE_SERVICE_ROLE_KEY`, DB URLs, Cloudinary credentials, Google service-account credentials, Resend keys, encryption keys and future payment webhook secrets out of repository, browser, screenshots and test logs.
- Add `.gitignore` coverage for `.env*` except `.env.example`, generated artwork, PDFs, screenshots, backups, token dumps, provider keys and temporary exports. Check before staging every commit.
- Separate roles: catalog editor does not approve payment; finance cannot quietly generate inventory; fulfillment cannot mark own bank settlement. Sensitive overrides require documented authorization and audit.
- A code agent may deploy only when specifically authorized and with release procedure. Never trigger production QR batch/finance transactions/retention deletes as incidental tests.
- Add bounded metrics for failing print jobs, Sheets retries, reservations under review, low stock, retained bytes, storage cleanup dead letters and unauthorized access. Avoid raw PII, QR token and activation secret values in metrics labels.

## 18. Standard templates for implementation agents

### 18.1 Bounded task prompt (copy and fill)

```text
You are implementing SafeReturn. Read AGENTS.md, docs/05-agent-instructions.md,
then the current v1.2 PRD/TDD/DB/API sections for TASK_ID.
Task: <one measurable behavior>
Contracts: <API IDs, tables and v1.2 requirement IDs>
Feature gate: <P0 or P1, current enable state>
Editable files: <list>. Exclusions: <list>.
Before coding: inspect repo/migrations/tests and report conflicts/ADRs.
Implement only agreed scope, preserve ownership/activation/payment/PII rules,
add transaction, retries and regression tests. No live production actions.
Report files changed, actual command results, tests and outstanding blockers.
```

### 18.2 Backend/API task

```text
Implement <API-ID> precisely as Doc 04 defines. Keep router thin; DTOs
validated; service owns authorization, idempotency, DB transaction and
outbox; repositories use explicit boundaries; provider adapter mocked.
Test owner, unauthorized, stale version, duplicate request, invalid state,
provider failure, and persisted DB consequences. Regenerate OpenAPI and
compare it to approved contract. Do not invent endpoint variants.
```

### 18.3 Migration task

```text
Inspect real schema and previous Alembic heads. Map v1.2 target logical
schema to additive modifications. Supply forward migration, staged backfill,
constraint/index changes, rollback/recovery and PostgreSQL integration tests.
Never run migrations on production without approval. Avoid duplicate tables.
```

### 18.4 Print and fulfillment task

```text
Implement order snapshot -> QR use list -> deterministic Lost-before-ICE
vector PDF generation -> private Supabase object -> metadata -> print QA.
Use exact per-variant dimensions/quiet zone, central logo scan QA,
restricted activation-insert handling, audited signed download, idempotent
job/reprint. Test counts, checksum, size, unavailable storage, retries.
```

### 18.5 Payment and integration task

```text
Implement manual provider adapter using normalized payment attempts.
Proof is untrusted; finance verifies trusted settlement independently.
When verified, emit durable events once for allocation, print and restricted
Google Sheets mirror. Keep gateway adapter disabled until external approval;
future webhooks require verified signatures and replay protection.
```

### 18.6 Frontend/QA task

```text
Implement exact approved user/admin screen. Test per-tag independent editors,
scan-context return after login, purchased copy count, quote/address review,
finance statuses, featured carousel, empty/offline cases, English/Urdu,
keyboard/RTL and protected data. Do not expose staff or storage credentials.
```

### 18.7 Security review task

```text
Act as read-only reviewer. Check authz per route, SSR/privacy leaks, cross
owner access, wallet/transfer evidence exposure, payment replay, duplicate
reservations, signed PDFs, durable jobs, retention, migration rollback,
minor/guardian constraints, barcode/logo print integrity. Report concrete
files/lines, severity, exploit preconditions and minimally scoped fixes.
No production changes.
```

## 19. PR/review acceptance format

Every task completion report must include:

```text
Task ID / branch / approved scope:
Requirement IDs and API IDs:
Files added or changed:
DB migration + data backfill strategy (or none):
State machine / authz / ownership checks:
Idempotency, job semantics and rollback:
Privacy, retention and evidence effects:
Exact tests run and actual results:
Unrun tests and limitations:
Contract/OpenAPI drift check:
Feature-flag state / launch scope:
Open decisions, risks, operator actions needed:
```

**Definition of done:** Reviewed minimal diff, approved schema/API alignment, appropriate tests actually run, access/retention examined, rollback and operational ownership documented. The phrase “implemented” requires committed source; “deployed” requires release evidence; “tested” requires test logs. None is implied by this policy document.

## 20. Proposed root `AGENTS.md` (create when scaffolding repo)

```markdown
# SafeReturn Coding Agent Rules

Read `docs/05-agent-instructions.md` and relevant v1.2 PRD/TDD/DB/API
before making changes. Preserve one Pair ID/two current QR identities,
atomic pair activation, independent Lost/ICE profiles, multiple pairs per
account, and physical QR copies separate from identities.

Payment proofs are never payment verification. PostgreSQL is source of truth.
Private PDFs/evidence go to Supabase Storage; public media to Cloudinary;
Google Sheets is restricted reporting only. P1 product publishing, existing
QR reuse and gateway features stay disabled without approved release.

Use scoped edits, reviewed migrations, backend authz, idempotent jobs,
privacy-safe logs, English/Urdu public flows and real test evidence.
Never perform production writes, payments, deletes or deployment without
explicit authorized human approval. Report conflicts; do not invent decisions.
```

## 21. Reconciliation and founder decision register

| Decision | Currently supported/default | Required approval/verification before release |
|---|---|---|
| New product publishing | P0 catalog foundations, QR sticker product only | P1 enablement, product print templates, admin roles |
| Existing-owned QR reuse | Schema/API planned, P1 feature-off | Entitlement/anti-fraud UX, reprint policy, staff QA |
| SQL vs ORM | SQLAlchemy/Alembic existing v1.1 standard | Any raw-SQL-only architectural replacement |
| QR dimensions/branding | M/Q base and 4-module quiet zone; optimize/logo-test | Exact printer/media, centered logo/ECC device QA |
| Reservation hold | Exclusive and time-limited; protect under-review payments | Hold duration, payment grace and late-settlement procedure |
| Payment provider | Manual bank/Raast review only | Gateway selection, webhook signing, settlement rules |
| Evidence/PDF retention | Private; time-limited, legal-hold-aware | Approved evidence window; print delivery grace and reprint rights |
| Cloudinary | Public marketing/catalog imagery | Cloudinary product account integration, allowed transformation defaults |
| Google Sheets | Masked eventually consistent finance mirror | Service-account scope, column access, provider operational limits |
| Guardian/medical data | Safe-by-default, no public private details | Minor/guardian and legal/privacy approval |
| Deployment/hosting | Proposals in TDD, not verified accounts | Environment configs, vendor quotas and provider tests |
| Legacy v1.1 contracts | Archive retained for unaffected rules | Route/schema reconciliation and approved ADRs where different |

**Approval gate:** Technical architecture and sensitive business features may remain specified but disabled until the relevant ADR/operations decision is signed. Never make up pricing, retention law, vendor quotas, account ownership, production domain or status of third-party integration.

## 22. Cross-document map / downstream work

| Documents | v1.2 agent-policy references and expectations |
|---|---|
| 01 PRD v1.2 | FR-201–211; QR copies, orders, finance, printing, service boundaries |
| 02 TDD v1.2 | Sections 3–10, 12–18 and founder extensibility amendment |
| 03 DB v1.2 | Part A §§4–13; snapshot `order_items`, `order_item_qr_uses`, payment attempts, artifacts and jobs |
| 04 API v1.2 | Part A §§A1–A16 and retained v1.1 API-001…096; additive API-200–244 |
| 06 Plan (currently v1.1) | Must add catalog/multi-QR/payment-adapter/print/sync/retention tasks |
| 07 Security (currently v1.1) | Must add child/guardian profile boundaries, proof/PDF, Sheets privacy, webhook design |
| 08 Test Plan (currently v1.1) | Add QR copy/paired identity, concurrency, PDF and provider-failure tests |
| 09 Operations (currently v1.1) | Add Supabase buckets, Cloudinary images, Sheets credentials, cleanup and gateway rollout |
| 10 Physical SOP (currently v1.1) | Add customer sizes, centered-logo print QA and per-order copies |
| 11 UI/UX (currently v1.1) | Add multiple QR profile UI, expandable catalog, featured carousel and payment/provider states |

**Document 05 stop point:** This file is the only newly created document for this task. No changes to Documents 06–11, application code or actual production resources are performed here.

---

# PART B — ORIGINAL v1.1 AGENT INSTRUCTIONS (ARCHIVED REFERENCE)

> Preserved in full from the user's uploaded `SafeReturn_05_AI_Agent_Instructions_and_Coding_Standards_v1.1(1).md`. This archive retains task patterns, checklists, and legacy operational guidance, **but superseded requirements do not override Part A**. In particular, older notions of pair-count-based cart lines, pre-v1.2 print production, manual-payment-only forever, or sticker-only permanent catalog limitations are obsolete when they conflict with v1.2.

# SafeReturn — AI Agent Instructions & Coding Standards

**Document ID:** SR-AGENT-004  
**Version:** 1.1-draft  
**Prepared:** 11 October 2026  
**Project:** SafeReturn, Lahore pilot  
**Intended users:** Founder/developer, Google Antigravity Pro, OpenAI Codex Plus, human reviewers  
**Status:** Proposed repository governance; adopt after reviewing open decisions  
**Deliverable:** This is **Document 4 only**. UI screens, route-by-route navigation, and visual design belong in the **final UI/UX document**, not here.

> **Mission:** Build a secure, bilingual, production-minded modular monolith for paired QR recovery and emergency identification. AI agents are implementation assistants, not product owners. Follow approved documents, preserve user privacy, verify changes, and never represent untested code as production-ready.

---

## 0. Read me first: how to apply this document

This is the **master AI-agent policy**. Store it at:

`docs/05-agent-instructions.md`

Also create a short root-level `AGENTS.md` **later, when scaffolding the repository**, that links to this policy and lists non-negotiable rules. Codex should read `AGENTS.md` from the repository. Configure Antigravity's workspace/project rules according to the features supported by the installed version; **do not assume a particular proprietary rule-file name or automatic discovery behavior**. When necessary, paste the scoped rules and document links directly into the Antigravity task.

### 0.1 Governing documents, in order

1. Approved SafeReturn PRD v1.0 plus v1.1 amendment: product requirements and acceptance criteria.
2. Approved founder decisions / ADRs, especially TDD ADR-001–008 and DB-DEC-01–14.
3. `docs/02-technical-design.md`: system architecture and trust boundaries.
4. `docs/03-database-design.md`: relational model, constraints, migration rules.
5. `docs/04-api-contract.md`: proposed REST endpoint behavior and OpenAPI fragments.
6. This AI Agent Instructions document: implementation process and code standards.
7. `docs/06-implementation-plan.md`: approved task order, scope, and definition of done (to be created next).
8. Security, test, deployment, physical-product, and final UI/UX documents when available.

**Conflict rule:** Do not invent a resolution. Report exact conflicting statements, impact, recommended options, and the smallest decision needed. Obtain founder approval for any change affecting privacy, security, ownership, payment, physical printing, or public emergency availability.

**Important contract caveat:** Document 3 contains detailed API specifications and OpenAPI 3.1 **fragments**, not a verified full machine-readable OpenAPI file. The implementation must produce and validate a canonical complete `openapi.yaml` or generated `openapi.json`, with drift checks. Never claim it already exists.

### 0.2 Work that an AI agent may not decide alone

- New business features, pricing, subscription models, or changes to paired-kit product scope.
- Whether WhatsApp reveals the owner's number: it does; explicit consent is mandatory.
- Whether emergency contact access is blocked during Turnstile outage: requires founder approval of the adaptive fallback.
- Data retention, legal notice wording, and medical/emergency liability wording.
- Replacing manual Raast/bank verification with automatic approval.
- Splitting ownership of Tag A and Tag B.
- Exposing Supabase service credentials or weakening row/route authorization.
- Changing database schema, API routes, or QR encoding without a reviewed change request.
- Publishing real domains, production secrets, or physical activation credentials in sample code.
- Deploying to production, running destructive commands, or sending live customer emails without explicit authorization.

---

## 1. SafeReturn project-specific invariants

All agent changes must preserve these rules.

| ID | Invariant | Required verification |
|---|---|---|
| INV-001 | One kit has one Pair ID, one credential, two **current** tags (`lost`, `ice`) | DB constraints + activation tests |
| INV-002 | Both current tags activate atomically | Concurrency/rollback integration test |
| INV-003 | Public QR tokens are distinct from activation credentials and unguessable | Token generation tests |
| INV-004 | Pair-level owner is authoritative | Authorization tests |
| INV-005 | Finder and ICE scan do not require login | E2E anonymous tests |
| INV-006 | Initial ICE HTML, hydration, API response omit full contact number | DOM/network privacy tests |
| INV-007 | Phone reveal is a protected interaction with abuse controls | API/security tests |
| INV-008 | WhatsApp is opt-in, off by default, and discloses the chosen number | Consent and link tests |
| INV-009 | WhatsApp-only chat is external; not logged as a SafeReturn message | Copy and API tests |
| INV-010 | Finder location is one-time, optional, explicitly consented | Browser/API tests |
| INV-011 | Finder message and outbox insert share a transaction | DB failure tests |
| INV-012 | Resend sending happens in worker, not the finder request transaction | Retry tests |
| INV-013 | Payment screenshot never auto-verifies bank transfer | Permission/workflow tests |
| INV-014 | Order quantity and allocation units are paired kits | DB and API tests |
| INV-015 | English and Urdu are P0 for public QR pages and physical materials | Localization review |
| INV-016 | Indoor QR ≥30×30 mm; outdoor ≥35×35 mm, including quiet zone | Print QA |
| INV-017 | QR ECC M or Q; 4-module white quiet zone | Artwork validation |
| INV-018 | Activation secret concealed by QA-approved packaging | Physical SOP |
| INV-019 | No raw private data, credentials, or precise coordinates in logs | Log inspection |
| INV-020 | Old QR token is revoked on replacement; history retained | DB/API tests |

### 1.1 Canonical pair schema decision

The database specification chooses `qr_codes.pair_id` as canonical membership and a **partial unique index** on `(pair_id, tag_type) WHERE is_current = true`. Historical revoked tags remain in the database. The exactly-two-current-tags invariant requires transaction checks and DB guard logic; a unique index alone is insufficient.

**Agents must not**:
- add independent `owner_user_id` to `qr_codes`;
- add circular `tag_pairs.tag_id_lost` / `tag_id_ice` FKs by default;
- replace the partial index with unconditional uniqueness and break replacements;
- activate just one child;
- delete old QR records to simplify a replacement.

### 1.2 Privacy decisions to preserve

- Account phone is not an automatically published ICE or WhatsApp number.
- ICE phone is **not** included in initial DOM, SSR payload, metadata, or hydration JSON.
- Optional geolocation is validated before encryption, then stored in `finder_message_locations` (the approved normalized alternative to PRD illustrative same-table fields).
- Finder inbox is tied to the **recipient owner at submission**; a new pair owner does not inherit previous owner's finder messages.
- WhatsApp destination must not contain activation secrets, medical notes, or coordinates.
- Sensitive admin access is least-privilege and audited.

---

## 2. Supported stack and boundaries

| Layer | Standard | Agent responsibilities |
|---|---|---|
| Frontend | Next.js App Router + TypeScript | Typed API client, accessible UI, locale-aware public flows |
| Styling | Tailwind CSS | Shared tokens, responsive and RTL-safe classes |
| API | FastAPI + Pydantic | Request validation, OpenAPI, authorization, explicit DTOs |
| ORM | SQLAlchemy 2.x | Domain repositories and transactions |
| Migration | Alembic | Reviewed revisions, no production `create_all()` |
| DB | Supabase PostgreSQL | Constraints, indexes, RLS/grants, integrity |
| Identity | Supabase Auth | JWT verification, session handling, verified-email checks |
| QR | Segno | Stable random token QR generation and export |
| Email | Resend | Durable outbox and independent worker |
| Bot controls | Cloudflare Turnstile | Server verification, rate limits, availability policy |
| Hosting | Vercel + Railway | Environment-specific configuration, health checks |
| Tests | pytest + Playwright + TS tooling | Repeatable tests and CI |
| Package management | Lockfiles | Pin after compatibility check; avoid unnecessary dependencies |

**Do not invent exact framework versions** or assume a plugin/tool is installed. Inspect manifests and lockfiles first. Prefer official maintained libraries and documented provider APIs. Never call provider APIs with invented endpoints or undocumented SDK methods.

### 2.1 Architectural rules

- Modular monolith: **one FastAPI API + one independently deployed outbox worker**.
- PostgreSQL is the source of truth.
- Public business data flows through FastAPI, not anonymous direct table writes.
- Supabase Auth handles identity, but FastAPI still checks object ownership and role permissions.
- No Redis, Celery, Kafka, microservices, paid external services, or heavy orchestration in P0 unless approved.
- External WhatsApp is a `wa.me` link, **not** WhatsApp Cloud API integration.
- No database schema generation by unreviewed `Base.metadata.create_all()` in production.
- No silent refactors while implementing unrelated features.

---

## 3. Repository layout and file ownership

Proposed layout, consistent with the TDD:

```text
safereturn/
├── AGENTS.md                     # Short entry-point for agents
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── 01-PRD.md
│   ├── 02-technical-design.md
│   ├── 03-database-design.md
│   ├── 04-api-contract.md
│   ├── 05-agent-instructions.md
│   ├── 06-implementation-plan.md
│   ├── 07-security-privacy.md
│   ├── 08-testing-plan.md
│   ├── 09-deployment-runbook.md
│   ├── 10-physical-product-sop.md
│   ├── 11-ui-ux-spec.md          # CREATE LAST
│   └── adr/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── messages/en.json
│   ├── messages/ur.json
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── api/v1/
│   │   ├── domains/
│   │   ├── db/
│   │   ├── security/
│   │   └── worker/
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── scripts/
└── .github/workflows/
```

### 3.1 File placement rules

- HTTP routing and HTTP-specific status mapping: `backend/app/api/v1/`.
- Domain decisions and state transitions: `backend/app/domains/<domain>/services.py`.
- Persistence queries: `backend/app/domains/<domain>/repositories.py` or shared DB module.
- ORM tables: domain models or central `db/models/` **choose one convention and use it consistently**.
- Pydantic schemas: named request/response models near domain API boundaries.
- Secrets/configuration: `backend/app/core/config.py` backed by environment.
- Security utilities: `backend/app/security/`.
- Email templates and dispatch: `notifications/` and `worker/`.
- Reusable frontend primitives: `frontend/components/`.
- Feature-specific frontend logic: `frontend/features/`.
- API client and type contracts: `frontend/lib/api/`.
- Translation dictionaries: `frontend/messages/`.
- Alembic revisions: `backend/alembic/versions/`.

Do not scatter business logic into Next.js route handlers, React components, or FastAPI `main.py`.

### 3.2 Change ownership in multi-agent work

| Work area | Preferred primary agent | Independent review |
|---|---|---|
| Database model/migrations | Codex | Human + optional Antigravity review |
| API domain logic | Codex | Human + independent test review |
| Frontend components/UX | Antigravity | Human + Codex accessibility/security review |
| Integration E2E tests | Either, assigned per task | Other agent reviews |
| Security-sensitive flows | One designated agent | Mandatory human review |
| Deployment | Human-led, agent-assisted | Human approval |

These are **suggested working roles**, not claims about tool superiority. Choose based on the actual task and tool capabilities. Never allow two agents to edit the same file or migration branch simultaneously.

---

## 4. Mandatory workflow for every AI coding task

### Phase A — Inspect

1. Read `AGENTS.md`, the task ticket, and relevant document sections.
2. Inspect repository tree and existing implementation before writing code.
3. Inspect package manifests, Python settings, lockfiles, migrations, and tests.
4. Check Git status; **do not overwrite pre-existing user changes**.
5. Identify exact files to modify and dependencies.
6. Identify relevant requirement IDs and security constraints.

### Phase B — Plan

Before changes, output:
- task summary;
- acceptance criteria;
- files to create/modify;
- relevant PRD/TDD/DB/API sections;
- migration and API compatibility impact;
- tests to add/run;
- risks and assumptions;
- approval blockers.

For large changes, ask founder approval before editing. For a clearly scoped low-risk change, proceed within approved boundaries.

### Phase C — Implement

1. Make the smallest coherent change.
2. Follow established patterns and type conventions.
3. Keep external I/O at adapters; business rules in services.
4. Add authorization and server validation before happy-path UI.
5. Add tests alongside code.
6. Add migration if schema changes; never alter production tables manually.
7. Update docs/contracts when behavior changes.
8. Preserve backward compatibility unless change is explicitly approved.

### Phase D — Verify

1. Run formatting/lint/type checks.
2. Run focused tests for changed behavior.
3. Run relevant integration and security tests.
4. Run migrations against disposable/staging Postgres.
5. Inspect generated OpenAPI diff for endpoint/schema changes.
6. Inspect Git diff for secrets, PII, unexpected changes.
7. Record commands and outcomes accurately.

### Phase E — Report

Every agent completion message must include:
- **Implemented:** exact behavior and files.
- **Not implemented:** scope left out.
- **Tests:** exact commands, pass/fail/skipped.
- **Security:** authorization/privacy checks performed.
- **Migrations/API changes:** revision IDs and contract updates.
- **Risks:** remaining issues and founder decisions.
- **Suggested next task:** one bounded follow-up.

**Never say "all tests pass" if tests were not run.** If network, credentials, browser, database, or package install is unavailable, report the limitation and mark the task unverified.

---

## 5. Task sizing and scope discipline

### 5.1 Good task boundaries

A task should ideally:
- address one user story or one infrastructure primitive;
- touch a manageable number of modules;
- have independent acceptance tests;
- be reviewable in a single pull request;
- not require the agent to invent new product rules.

**Good examples:**
- "Add `tag_pairs` and `qr_codes` migrations with current-child uniqueness and DB tests."
- "Implement `POST /api/v1/.../activations` according to approved contract, including atomic transaction and race tests."
- "Implement anonymous finder submission persisting outbox event atomically, without sending Resend in the request."
- "Add Urdu translations and RTL support to the existing public QR page without changing API behavior."
- "Add worker lease-recovery tests."

**Bad examples:**
- "Build all of SafeReturn."
- "Make the database secure."
- "Create every frontend page and backend API in one prompt."
- "Fix any problems you see" on a dirty production branch.
- "Optimize all code" without benchmarks or scope.

### 5.2 Stop-and-escalate triggers

Stop and request a decision when:
- approved documents disagree;
- an endpoint is missing from the API contract;
- a migration would destroy or backfill production data ambiguously;
- an owner might gain access to another owner's private data;
- a public response may disclose a phone number or medical detail;
- a credential or secret would appear in a print/export file;
- a proposed feature adds recurring cost or new external vendor;
- emergency contact access becomes unavailable on bot-provider outage;
- an AI tool requests excessive permissions or a production secret;
- a test reveals a critical invariant failure.

---

## 6. Python and FastAPI coding standards

### 6.1 Python style

- Python type hints on public functions and domain boundaries.
- Clear descriptive names; `snake_case` functions/variables, `PascalCase` classes.
- Small functions with one responsibility.
- Avoid wildcard imports, mutable global state, and broad `except Exception` without structured handling.
- No synchronous blocking network I/O inside async request handlers.
- Use timezone-aware UTC timestamps.
- Use `Decimal` for money.
- Use `secrets`/cryptographically secure randomness for tokens.
- No hardcoded credentials, email sender secrets, JWT signing keys, or URLs that vary by environment.
- Prefer dependency injection for DB sessions, current user, clocks, email adapters, and external API clients.

### 6.2 FastAPI layering

```text
router -> auth/validation dependencies -> service -> repository -> DB
                                           |
                                           +-> outbox insert in same transaction
```

- Router validates transport, maps errors to HTTP responses.
- Service owns business decisions and transaction boundaries.
- Repository encapsulates SQLAlchemy persistence.
- Worker owns outbound Resend call.
- Pydantic response models whitelist fields; **never return ORM objects raw**.
- Do not put permission checks only in frontend code.

### 6.3 Pydantic

- Explicit request and response models.
- Use `extra='forbid'` on sensitive write models where appropriate.
- Validate phone normalization, text length, language, coordinates, and IDs.
- Use separate models for public, owner, and admin representations.
- Never use a single "Tag" schema for all three trust levels.
- Avoid leaking private columns via `model_dump()` on broad internal objects.

### 6.4 SQLAlchemy

- SQLAlchemy 2.x style; explicit session lifecycle.
- Transactions owned by application service, not implicitly committed in repositories.
- Parameterized queries; no SQL concatenation with user input.
- Use `SELECT ... FOR UPDATE` for pair activation/allocation concurrency.
- Use deterministic lock ordering to reduce deadlocks.
- Use explicit eager-loading where needed to avoid N+1 queries.
- Avoid lazy-loading sensitive relationships during response serialization.
- Never call `session.commit()` halfway through atomic activation.

### 6.5 Errors

Use typed domain exceptions with stable error codes mapped to the approved API envelope:

```json
{
  "error": {
    "code": "PAIR_ALREADY_ACTIVATED",
    "message": "This kit is already activated.",
    "request_id": "req_example",
    "details": {}
  }
}
```

- No stack traces in public JSON.
- No secret-validity hints during failed activation.
- Localize public user-facing error copy to English and Urdu.
- Keep error codes stable and language-independent.
- Distinguish validation (4xx), authorization (401/403), conflict (409), throttling (429), and unexpected server failure (5xx).

---

## 7. Database and Alembic coding standards

### 7.1 Before creating a migration

1. Read `03-database-design.md`.
2. Inspect current Alembic head(s) and migration history.
3. Compare proposed model change with approved schema.
4. Identify data compatibility, locks, index costs, and rollback strategy.
5. Obtain approval for changes to sensitive columns or ownership semantics.

### 7.2 Migration rules

- Never run `create_all()` in production.
- Never delete/recreate tables to "fix" a mismatch.
- Prefer additive expand/backfill/contract migrations.
- Explicitly name constraints and indexes.
- Test migration against clean DB and previous-revision snapshot.
- No fake data inserted into production.
- No production schema change hidden in application startup.
- No silently squashed migrations once shared.
- Do not add circular `tag_pairs` child FKs unless ADR changes.
- Implement current-child uniqueness as partial index.
- Implement exact-two guard at activation and DB transition.
- Preserve historical QR records on replacement.

### 7.3 Transaction patterns

**Pair activation:** lock pair, credential, current children; validate entitlement and secret; update both tags + owner + consumed secret + audit + outbox; one commit.

**Finder message:** validate; insert message + optional encrypted location + outbox; one commit; email later.

**Pair allocation:** lock order item + candidate pairs; verify payment and quantity; insert allocations + update status + audit; one commit.

**Payment approval:** independent bank verification; lock submission/order; insert review + status + audit; one commit.

### 7.4 Supabase rules

- Treat `auth.users` as Supabase-managed.
- Do not modify Supabase-managed tables directly.
- Keep service-role keys off the frontend.
- Enable restrictive RLS/grants on exposed business tables.
- Remember `service_role` bypasses RLS: backend authorization remains mandatory.
- Test real deployment credentials and roles, not just SQL policy text.
- Store payment proof in private object storage with short-lived authorized access.

---

## 8. TypeScript, Next.js, and frontend coding standards

**This section sets engineering rules only. The detailed list of screens, page routes, navigation, visual hierarchy, and UI state diagrams will be in the final UI/UX document.**

### 8.1 TypeScript

- Enable strict mode.
- No unexplained `any`; prefer `unknown` and narrow safely.
- Define DTOs from approved API contract.
- Use typed API client functions and centralized error mapping.
- Do not duplicate business rules in components; server remains authoritative.
- Avoid stale frontend hardcoded enums when backend contract changes.
- Never expose private env vars through `NEXT_PUBLIC_*`.

### 8.2 Next.js App Router

- Deliberately separate server and client components.
- Browser geolocation and `window` usage must remain client-side.
- Do not SSR sensitive ICE contact numbers.
- Public QR content must not be cached as if it were static permanent content.
- Respect `Cache-Control: no-store` for contact reveal and other sensitive responses.
- Use a safe auth/session integration; validate JWT on backend.
- No database service-role access in frontend.
- Avoid storing activation secrets or ICE numbers in local storage.
- Do not put credentials into URL query parameters.

### 8.3 Components

- Components should have typed props and clear boundaries.
- Separate presentation from data fetching and mutations.
- Use semantic HTML and accessible labels.
- Handle loading, error, success, empty, and offline/timeout states.
- Use native buttons/links for keyboard interaction.
- No direct DOM manipulation unless justified.
- No unreviewed `dangerouslySetInnerHTML`.
- Do not add animations that delay emergency contact access.

### 8.4 Styling

- Tailwind classes and centralized design tokens.
- Responsive mobile-first layout.
- Support RTL using logical CSS properties/utilities where possible.
- No fixed pixel assumptions for Urdu text expansion.
- Avoid visual-only indication of status.
- Keep emergency touch targets large and easy to reach.
- Do not add arbitrary UI libraries or icon packages without approval.

### 8.5 Accessibility

- Aim for WCAG 2.2 AA in public flows.
- Semantic headings, labels, focus order, contrast, keyboard operation.
- Screen-reader announcements for submission and reveal results.
- Meaningful error text in selected language.
- Avoid requiring drag/drop, hover, or precise gestures.
- Respect reduced-motion preferences.

---

## 9. Localization and Urdu/English requirements

### 9.1 P0 scope

All **public QR landing pages** and physical tag/packaging copy must support English and Urdu, including:
- lost-item instructions;
- finder form labels and errors;
- location consent;
- WhatsApp opt-in/public disclosure wording;
- ICE publication disclaimers;
- contact reveal and bot-challenge instructions;
- revoked/unactivated/error states;
- confirmation messages.

Authenticated customer/admin localization is P1 unless founder approves otherwise.

### 9.2 Implementation

- Version-controlled translation dictionaries, e.g. `messages/en.json`, `messages/ur.json`.
- Same key structure in both files; missing keys fail CI.
- Use `lang="ur"` and `dir="rtl"` for Urdu content.
- Render phone numbers, URLs, QR tokens, and coordinates in LTR spans as needed.
- Switching language should preserve unsent finder form values.
- No runtime automatic translation for security/medical consent.
- Use reviewed translations, especially for emergency terms and disclosure.
- Support Unicode Urdu in DB, API, search, and tests.
- Date/time and numbers formatted intentionally; do not assume RTL flips all values.

### 9.3 Translation review checklist

- [ ] English and Urdu keys match.
- [ ] No untranslated fallback on public error pages.
- [ ] Correct RTL layout and punctuation.
- [ ] Phone numbers and links remain readable.
- [ ] Consent text understandable to nontechnical users.
- [ ] No clipped Urdu glyphs on mobile or printed labels.
- [ ] Human review of emergency copy completed.

---

## 10. Public QR token and activation-secret standards

### 10.1 Public tokens

- Generate with CSPRNG (`secrets` in Python).
- At least 128 bits entropy.
- Use URL-safe encoding.
- Unique DB constraint on token.
- Stable token once printed; never embed owner phone or Pair ID as a substitute.
- Never log full tokens unnecessarily or expose token-to-owner exports publicly.
- Print only production-domain QR URLs after domain verified.

### 10.2 Activation secrets

- Separate from public token.
- High entropy and non-guessable.
- Store only approved verifier, with key/pepper management.
- Print in concealed insert, not on visible tag.
- Verify in constant-time as applicable.
- Lock/rate-limit repeated attempts.
- One secret activates both tags atomically.
- Never expose secret in API response, logs, screenshots, analytics, or test reports.

### 10.3 Replacement

- Old tag remains historical and revoked.
- New tag receives new token and serial.
- One current child per pair/type at commit.
- Public scan of old tag displays safe revoked state.
- Replacement is audited and permission-controlled.

---

## 11. ICE and emergency privacy rules

### 11.1 Initial scan response

Allowed: tag type, published display fields, emergency instructions, opaque contact IDs, relationship labels, safe feature flags.

Forbidden: full phone numbers, `tel:` links, ciphertext fields, account phone, private owner data, activation credentials.

### 11.2 Contact reveal

1. Finder/responder explicitly taps reveal.
2. Client requests protected endpoint with token/contact ID.
3. Backend verifies contact belongs to scanned active ICE tag.
4. Apply rate limits and abuse detection.
5. Verify Turnstile server-side for elevated-risk requests.
6. Return number only on successful authorized reveal.
7. Use no-store and no PII logging.

**Founder decision:** The TDD recommends adaptive fallback during Turnstile outages to avoid blocking urgent contact. If strict mandatory Turnstile is required by the PRD interpretation, obtain explicit decision and test outage behavior. **Agent must not choose silently.**

### 11.3 Medical notes

- Owner must explicitly publish each sensitive field.
- Never auto-copy private account data.
- Show owner-provided/unverified disclaimer.
- Encrypt at rest.
- No medical data in analytics, WhatsApp prefills, or finder email unless explicitly approved.

---

## 12. Finder messaging, geolocation, and WhatsApp rules

### 12.1 Finder form

- Anonymous submission; no account required.
- Validate message size, contact method, abuse controls, and tag state.
- Persist message + outbox in one transaction.
- Return success after commit, not after email delivery.
- Do not claim item recovery is guaranteed.

### 12.2 Location

- Browser asks for location **only after user action**.
- No automatic location on page load.
- No background tracking.
- Denial/timeout must not block form submission.
- Validate latitude/longitude ranges and accuracy.
- Encrypt precise coordinates before storage.
- Save consent timestamp/version.
- Only authorized owner views location.
- Build Google Maps link from validated coordinates.
- Retention/deletion follows approved privacy policy.

### 12.3 WhatsApp

- Default off.
- Explicit owner consent to public phone disclosure.
- Use user-initiated `wa.me` click-to-chat only.
- No WhatsApp Cloud API in P0.
- Never claim that SafeReturn records external WhatsApp chats.
- Do not create fake outbox events for a click that did not submit a SafeReturn message.
- URL-encode safe prefilled text; no secrets, medical notes, or precise coordinates.
- Keep a usable SafeReturn finder form available.

---

## 13. Resend and durable outbox rules

### 13.1 Required architecture

- API writes `notification_outbox` in same DB transaction as domain event.
- Worker claims due rows with PostgreSQL `FOR UPDATE SKIP LOCKED`.
- Worker sends Resend outside DB transaction.
- Store provider result and update outbox status.
- Retry transient failures with bounded exponential backoff/jitter.
- Mark exhausted/permanent failures dead and alert operations.
- Reclaim expired worker leases.

### 13.2 Semantics

At-least-once delivery processing, not exactly-once guarantee. Worker crash after provider acceptance may cause duplicate email. Use provider idempotency where available, stable event keys, and duplicate-tolerant templates.

### 13.3 Resend account constraints

- General customer email requires a verified sending domain.
- Test sender addresses may be restricted to authorized test recipients.
- Never put Resend API key in Next.js public env.
- No email sends from React components.
- Do not promise delivery simply because Resend accepted an API request.

### 13.4 Required tests

- Outbox insert failure rolls back finder message.
- Resend timeout causes retry.
- Duplicate worker claims prevented.
- Lease expiration recovers stuck event.
- Permanent provider rejection marks dead.
- Provider idempotency behavior documented.
- No private message text in logs.

---

## 14. Orders, payment, and fulfillment standards

- One order item unit is **one pair**, not one sticker.
- Backend computes prices and totals with `Decimal`.
- Payment proof upload must be private and validated.
- Never approve payment from screenshot alone.
- Admin must independently verify transfer via approved bank/Raast channel.
- Record payment review and staff actor in audit.
- Only verified orders allocate eligible QA-passed pairs.
- Unique active allocation per pair.
- Allocation locks inventory to prevent double assignment.
- Physical QA requires both QR tags and concealed credential.
- No shipment of mismatched pair IDs or exposed credentials.
- Cancellation/refund after activation or dispatch requires an explicit operations workflow.

---

## 15. Security standards for all agents

### 15.1 Authentication and authorization

- Validate Supabase JWT signature, issuer, audience, expiry, and token type in FastAPI.
- Do not trust request-body owner IDs or admin flags.
- Verify email when activation requires it.
- Enforce ownership through `tag_pairs.owner_user_id`.
- Restrict admin functions by permission and MFA.
- Do not expose private finder inbox across pair transfers.
- Test IDOR, cross-tenant access, and role escalation.

### 15.2 Inputs and output

- Validate every public input server-side.
- Limit body sizes and field lengths.
- Use parameterized SQL.
- Escape user content on rendering.
- No executable HTML in finder messages.
- Validate uploaded file type/size/content and keep private.
- Do not return ORM objects or raw DB error text.
- Rate-limit scan/reveal/message/activation endpoints appropriately.
- Turnstile tokens must be verified server-side.

### 15.3 Secrets

- `.env` and credentials never committed.
- `.env.example` includes **names and fake placeholders only**.
- No hardcoded DB passwords, JWT secrets, Resend API keys, Turnstile secrets, or service-role keys.
- No secrets in browser bundles or public `NEXT_PUBLIC_*`.
- Rotate any secret exposed in chat, terminal history, logs, commits, or screenshots.
- Avoid passing production secrets to AI agents unless absolutely required and securely scoped; prefer local test credentials.

### 15.4 Logging and observability

Safe fields: request ID, route template, latency, status, sanitized error code, environment, release ID.

Never log: activation secret, JWT, full phone, finder body, precise location, medical notes, payment proof contents, API keys.

### 15.5 Dependency safety

- Add libraries only when necessary.
- Verify package name, maintainer, version compatibility, license, and known advisories.
- Do not execute untrusted installation scripts or copy shell commands from arbitrary sources without review.
- Commit lockfiles.
- Run security scans in CI.
- Keep transitive dependency changes visible in PR.

### 15.6 Tool permission boundaries

AI agents may inspect, edit, and test in the **approved local/staging workspace**. They must request approval before:
- connecting to production databases;
- applying migrations to production;
- deleting real data;
- sending live notifications;
- changing DNS or verified email sender;
- changing deployment environment variables;
- publishing/revoking production QR tags;
- approving payments or shipping orders;
- installing high-privilege plugins or browser extensions.

---

## 16. Testing policy

### 16.1 Test pyramid

1. **Unit:** pure validation, token generation, state machines, localization.
2. **Integration:** PostgreSQL constraints, transactions, auth, worker.
3. **API contract:** Pydantic/OpenAPI request/response compatibility.
4. **E2E:** anonymous finder, owner activation, ICE reveal, admin payment.
5. **Security:** IDOR, brute force, contact scraping, sensitive data leakage.
6. **Physical:** scan and label QA on real substrate and representative devices.

### 16.2 Test requirements per change

| Change type | Minimum tests |
|---|---|
| New API endpoint | Happy path, validation, unauthorized, forbidden, conflict, errors |
| Database migration | Upgrade, constraints, representative existing data, rollback plan |
| Activation | Atomicity, idempotency, concurrent owners, invalid secret |
| Finder message | Accepted storage, outbox rollback, spam control |
| ICE reveal | No initial number, protected reveal, cross-QR denial, outage |
| WhatsApp | Off by default, explicit consent, safe `wa.me` encoding |
| Location | Denied/timeout, valid coordinates, encrypted storage, deletion |
| Orders | Backend totals, verified payment gate, double allocation |
| Localization | English/Urdu keys, RTL, preserved form state |
| Worker | Retry, lease expiry, duplicate send tolerance |
| Security refactor | Relevant regression tests plus targeted abuse tests |

### 16.3 Tests must be truthful

Agents must state:
- commands actually run;
- environment used;
- number of passed/failed/skipped tests if available;
- why tests could not run;
- remaining manual verification;
- any fixture or mock limitation.

Do not mark manual phone scanning, bank confirmation, or real email delivery "passed" merely because a unit test mocked it.

---

## 17. OpenAPI contract governance

Document 3 is a **detailed Markdown contract with fragments**. Build a machine-readable canonical OpenAPI 3.1 contract during implementation.

### 17.1 Contract-first steps

1. Locate endpoint family in Document 3.
2. Resolve any open decisions and exact route naming.
3. Define request/response schemas and error codes.
4. Implement FastAPI endpoint and generate OpenAPI.
5. Validate generated schema using an OpenAPI validator.
6. Compare with canonical contract and fail CI on unexplained drift.
7. Generate or validate TypeScript API types from the approved contract.
8. Update examples, tests, and documentation.

### 17.2 Compatibility policy

- Do not rename paths, fields, or error codes casually.
- New optional response fields may be additive.
- Breaking changes require API version/rollout decision.
- Never change public QR URL semantics after printing without a compatibility plan.
- Keep both frontend and backend aligned to one contract version.
- Reject unknown sensitive request fields rather than silently accepting privilege-related properties.

---

## 18. Git, branches, and review standards

### 18.1 Branch naming

Suggested:
- `feat/pair-activation`
- `feat/finder-outbox`
- `fix/ice-phone-leak`
- `test/pair-concurrency`
- `docs/api-contract`
- `chore/ci`

### 18.2 Commit conventions

Use clear messages such as:
- `feat(activation): atomically activate both tags`
- `test(db): reject missing current ICE tag`
- `fix(public): remove ICE phone from initial payload`
- `docs(adr): approve contact reveal fallback`

### 18.3 Pull request checklist

- [ ] Task ID and requirement IDs linked.
- [ ] Scope limited and unrelated changes explained.
- [ ] API and DB contract compatibility reviewed.
- [ ] Authorization tested.
- [ ] PII/secret logging reviewed.
- [ ] Tests run and results recorded.
- [ ] Migration reviewed if present.
- [ ] English/Urdu coverage reviewed if public-facing.
- [ ] No production secrets or test customer PII.
- [ ] Rollback/feature-flag strategy documented if risky.
- [ ] Human reviewer approved sensitive changes.

### 18.4 Agent collaboration

Do not allow Antigravity and Codex to operate on the same working tree concurrently. Prefer separate Git branches or isolated worktrees, with one integration owner. Merge in sequence after tests. An agent must not revert or overwrite another agent's uncommitted work.

---

## 19. CI quality gates

Suggested CI pipeline, adapt commands to actual project configuration:

```bash
# Frontend (run from frontend/)
npm ci
npm run lint
npm run typecheck
npm run test

# Backend (run from backend/, after environment setup)
python -m pytest -q
python -m alembic upgrade head

# E2E (requires configured test services)
npx playwright test
```

These are **illustrative commands**. Do not invent `npm run typecheck` or `npm run test` scripts if package.json does not define them; create and document scripts as part of approved scaffolding.

### 19.1 Required CI gates

- Lint and format.
- Type checks.
- Unit and integration tests.
- Database migration upgrade against disposable PostgreSQL.
- OpenAPI schema validation and drift check.
- Security/dependency scan.
- Secret scanning.
- Critical Playwright smoke tests.
- Translation key parity check.

### 19.2 Release gates

No production deployment if:
- atomic activation tests fail;
- ICE phone leaks in initial HTML/JSON;
- unauthorized customer can access another customer's data;
- finder location collected without explicit consent;
- outbox transaction is not durable;
- payment screenshot auto-verifies payment;
- pair allocation can double-sell stock;
- public Urdu critical copy is missing;
- physical QR QA fails;
- rollback/backup is unverified.

---

## 20. Performance and reliability guidelines

- Measure before optimizing.
- Public token lookup must use unique index.
- Avoid N+1 queries in customer pair list.
- Use pagination for inbox, orders, inventory, and audits.
- Keep external Resend calls out of API transaction.
- Use short DB transactions and bounded retries.
- Avoid blocking emergency reveal on nonessential analytics.
- Set request/network timeouts intentionally.
- Ensure mobile pages remain usable on slower networks.
- Prefer graceful degraded behavior to blank screens.
- Rate limits must be shared across instances if scaling beyond one process.
- Never claim performance targets met without measurements.

### 20.1 Suggested performance evidence

For meaningful performance changes, report:
- test environment;
- input size;
- baseline and after;
- p50/p95 latency where applicable;
- DB query count;
- index/query plan if relevant;
- tradeoffs.

---

## 21. Documentation maintenance

When an implementation changes an approved contract:
1. Record reason and founder approval.
2. Update ADR or decision register.
3. Update affected PRD/TDD/DB/API document.
4. Update implementation plan and test cases.
5. Update code and migration.
6. Verify frontend compatibility.
7. Link all changes in PR.

Never let code and documents drift silently.

### 21.1 Document status tags

Use one of:
- `Proposed`
- `Approved`
- `Implemented`
- `Verified`
- `Deprecated`

A detailed specification is **not** automatically implemented or verified.

---

## 22. Prompt template: Antigravity Pro

Use this template for a bounded implementation task. Paste relevant file paths and sections; do not paste the entire PRD every time unless needed.

```text
You are implementing one scoped SafeReturn feature in the existing repository.

FIRST READ:
- AGENTS.md
- docs/05-agent-instructions.md
- relevant PRD v1.1 requirements: [IDs]
- docs/02-technical-design.md sections: [...]
- docs/03-database-design.md sections: [...]
- docs/04-api-contract.md sections: [...]

TASK:
[One concrete feature only.]

ACCEPTANCE CRITERIA:
1. [...]
2. [...]
3. [...]

RULES:
- Inspect the current code and Git status before editing.
- Plan the files and tests first.
- Preserve pair-level ownership and two-tag atomicity.
- No secrets or private ICE phone in public SSR/HTML.
- No new dependencies or schema/API changes without explanation.
- Use strict TypeScript, accessible components, and locale-aware public UX.
- Do not change unrelated modules or overwrite existing work.
- Do not deploy or modify production.

DELIVER:
- Changed files
- Tests run with results
- Security/privacy checks
- Open questions and exact next task

If any requirement conflicts with the repository, stop and ask.
```

### 22.1 Antigravity usage notes

- Use the workspace rules mechanism supported by the installed version; verify that the rules were actually read.
- For UI tasks, supply design screenshots/mockups **only if they are approved** and available.
- For browser-assisted verification, use staging or local test accounts; never expose real customer data.
- Do not let autonomous browser actions approve payments, send production messages, or edit live inventory.
- Review generated CSS for RTL and accessibility; visual similarity is not proof of correctness.
- Ask for a diff summary and test evidence after each task.

---

## 23. Prompt template: Codex Plus

```text
You are Codex working on the SafeReturn repository.

Read AGENTS.md and docs/05-agent-instructions.md first.
Read only the relevant PRD/TDD/DB/API sections for this task.

TASK: [bounded implementation]

CONTRACT:
- API: [exact route, request, response, errors]
- Database: [tables, constraints, migration IDs]
- Security: [actor permissions, privacy invariants]
- Tests: [specific unit/integration/concurrency cases]

WORKFLOW:
1. Inspect Git status, files, and tests.
2. Propose a short implementation plan.
3. Implement the smallest coherent diff.
4. Add and run tests.
5. Validate migration and OpenAPI drift if relevant.
6. Report exact changed files, commands, outcomes, and risks.

Do not:
- alter unrelated code;
- change approved API/schema without a decision;
- bypass authorization or RLS assumptions;
- store raw activation secrets or expose ICE phone in initial payload;
- deploy or connect to production without explicit permission.

Stop if the specification is contradictory.
```

### 23.1 Codex review-only prompt

```text
Review the current diff only; do not edit files.

Compare changes against:
- docs/05-agent-instructions.md
- relevant PRD v1.1 acceptance criteria
- relevant database and API contracts

Prioritize:
1. privacy/security vulnerabilities;
2. pair activation and allocation races;
3. API/schema incompatibilities;
4. missing negative tests;
5. real functional bugs.

Return findings ranked Critical / High / Medium / Low.
For each: file path, line, exploit/failure scenario, and minimal fix.
Do not invent defects or claim tests were run.
```

---

## 24. Prompt template: database migration

```text
Implement one reviewed Alembic revision for SafeReturn.

Read docs/03-database-design.md and current migration heads.
Change requested: [exact tables/columns/indexes].
Invariants: pair owner at parent; partial unique current children;
exactly-two activation guard; preserve replacement history.

Before coding:
- Show current revision and proposed revision.
- Explain FK/delete actions, index choice, and rollback.
- Identify compatibility with existing rows.

Implement:
- Migration and ORM updates.
- Integration tests on disposable PostgreSQL.
- No production execution.

Report:
- Revision ID
- Upgrade and downgrade/forward-fix behavior
- Tests and results
- Data-loss/lock risks
```

---

## 25. Prompt template: security audit

```text
Perform a read-only SafeReturn security review.

Scope: [specific feature/endpoint/branch].
Review approved PRD/TDD/DB/API documents.

Check:
- Authn/authz and IDOR
- Public token enumeration
- Activation brute force/races
- Initial ICE phone exposure
- WhatsApp consent disclosure
- Finder location consent and storage
- Resend outbox integrity
- Payment approval permissions
- Logging of secrets and PII
- RLS/service-role misuse

Do not change code.
Provide reproducible findings, severity, affected path, evidence,
recommended fix, and missing tests.
Clearly distinguish verified findings from hypotheses.
```

---

## 26. Prompt template: test generation

```text
Add tests for [specific SafeReturn feature] without changing production
behavior except for minimal testability fixes approved in scope.

Requirements: [IDs].
Existing implementation: [paths].
Expected edge cases: [cases].

Use real PostgreSQL transactions for concurrency/invariant tests,
not mocks that cannot detect race conditions.
Mock external Resend/Turnstile calls in unit tests.
Keep all fixtures synthetic.
Run the tests and report exact outcomes.
```

---

## 27. Agent response format and acceptance evidence

Agents should return:

```text
TASK: [ID and title]
STATUS: Implemented / Partially implemented / Blocked

SCOPE COMPLETED:
- ...

FILES CHANGED:
- path — purpose

DATABASE/API:
- migration ID, contract changes, compatibility

SECURITY:
- checks performed, concerns

TESTS:
- command — PASS/FAIL/SKIPPED
- manual checks pending

UNRESOLVED:
- decision needed, risk, impact

NEXT SUGGESTED TASK:
- one bounded follow-up
```

**Human acceptance:** The founder/reviewer should independently inspect critical diff, migrations, and test results. A green AI summary is not an acceptance test.

---

## 28. Task-specific quality checklists

### 28.1 Pair activation

- [ ] Verified user and entitlement.
- [ ] Secret verifier checked securely.
- [ ] Lock pair, credential, and current children.
- [ ] Exactly one current lost and ICE tag.
- [ ] Both statuses updated in same transaction.
- [ ] Credential consumed.
- [ ] Audit/outbox committed with state.
- [ ] Idempotency and race tests.
- [ ] No secret in logs or response.

### 28.2 ICE reveal

- [ ] Initial HTML/JSON/hydration contains no phone.
- [ ] Only published contact IDs/labels visible.
- [ ] Reveal validates QR/contact relationship.
- [ ] Rate limits and adaptive challenge behavior.
- [ ] `no-store` and no phone in analytics.
- [ ] Emergency outage fallback decision documented.
- [ ] Urdu/English reveal/error copy tested.

### 28.3 Finder message

- [ ] Anonymous form works.
- [ ] Server validation and anti-spam.
- [ ] Location only after explicit action.
- [ ] Permission denied still submits.
- [ ] Message/location/outbox one transaction.
- [ ] Resend worker retry.
- [ ] Owner-only inbox.
- [ ] No location or message text in logs.

### 28.4 WhatsApp

- [ ] Default disabled.
- [ ] Explicit public phone consent.
- [ ] Correct normalized `wa.me` link.
- [ ] No private data in prefilled text.
- [ ] External conversation limitation stated.
- [ ] SafeReturn form still available.
- [ ] Disable takes effect immediately.

### 28.5 Orders/fulfillment

- [ ] Quantity measured in pairs.
- [ ] Backend price calculation.
- [ ] Manual bank verification required.
- [ ] No double pair allocation.
- [ ] Only QA-approved pairs shipped.
- [ ] Two QR labels and concealed secret.
- [ ] Physical size/ECC/quiet zone QA.
- [ ] Admin actions audited.

---

## 29. Common AI-generated mistakes to reject

1. A "working" demo that stores users in an in-memory Python dictionary.
2. SQLite used for concurrency tests that must reflect PostgreSQL locking.
3. One QR token used for both lost and ICE tags.
4. Public QR token reused as activation secret.
5. Separate activation of Tag A and Tag B.
6. Duplicate child FKs creating circular inconsistent pair membership.
7. Deleting historical QR records during replacement.
8. Direct frontend writes to private Supabase business tables.
9. Supabase `service_role` key in browser code.
10. JWT payload decoded but signature/audience/issuer not verified.
11. Phone number included in initial ICE page source and hidden only by CSS.
12. Turnstile client-side only, without server verification.
13. Finder location requested automatically on page load.
14. Finder location silently required for form submission.
15. Email sent in request before finder message commit.
16. FastAPI `BackgroundTasks` treated as durable queue.
17. WhatsApp-only chats described as stored/audited.
18. Bank payment screenshot treated as successful payment.
19. Order quantity interpreted as individual stickers.
20. `float` used for money.
21. Production schema mutated using `create_all()`.
22. API endpoint invented without updating contract.
23. PII or activation secrets printed in logs.
24. English-only error state on an Urdu public page.
25. Placeholder QR graphic shipped instead of scan-tested QR artwork.
26. Unverified test claims or fabricated benchmark results.
27. An agent changing unrelated files while "cleaning up".
28. Production deployment without founder approval.

---

## 30. Sample root `AGENTS.md` (copy later when repo exists)

> **Note:** This is an embedded example inside Document 4. The user requested only one downloadable file now; do not create a second `AGENTS.md` artifact in this step.

```markdown
# SafeReturn Agent Rules

Read `docs/05-agent-instructions.md` before editing.

Product: paired physical QR kit (lost + ICE), one Pair ID, one activation
credential, atomic activation, pair-level ownership.

Source documents:
- docs/01-PRD.md
- docs/02-technical-design.md
- docs/03-database-design.md
- docs/04-api-contract.md
- docs/05-agent-instructions.md

Non-negotiable:
1. Never expose secrets or Supabase service-role key to browser.
2. No initial ICE phone in HTML, SSR, hydration, or public scan JSON.
3. Finder location requires explicit opt-in and is optional.
4. Finder message + outbox must commit atomically.
5. WhatsApp is opt-in external click-to-chat, not audited messaging.
6. Manual bank verification required before pair allocation.
7. Public QR flows support English and Urdu.
8. Use Alembic; no production create_all().
9. No unrelated changes or destructive commands.
10. Plan, implement scoped diff, test, and report evidence.

Stop on conflicts between approved documents.
Do not deploy to production without explicit approval.
```

---

## 31. Example end-to-end AI work session

**Feature:** SafeReturn finder message + durable email notification.

**Step 1 — Founder creates ticket**
- Goal: Finder can submit anonymous message on Tag A.
- Acceptance: persists even if Resend unavailable; optional location; owner inbox; bilingual errors.
- Docs: PRD FR and AC IDs; TDD §§8–9; DB §§8–9; API §§8,14,21.

**Step 2 — Codex backend task**
- Inspect existing code.
- Implement Pydantic request validation and service.
- Insert finder message, optional encrypted location, and outbox row in one transaction.
- Add tests for denied location, rollback, duplicate submission, owner authorization.
- Report exact tests.

**Step 3 — Antigravity frontend task**
- On a separate branch/worktree after backend contract stabilizes.
- Implement existing approved public finder form.
- Request location only after explicit click.
- Preserve input when language switches.
- Add loading/success/error states.
- Do not implement WhatsApp automatically unless separately tasked.

**Step 4 — Codex review-only**
- Check initial public response for private data.
- Verify API DTO matches contract.
- Check input validation, abuse controls, outbox transaction.
- Flag evidence-backed findings.

**Step 5 — Human acceptance**
- Merge after tests.
- Check real mobile browser, English/Urdu, location denied.
- Test Resend outage in staging.
- Confirm no PII in logs.

**Step 6 — Next ticket**
- Add outbox worker retry/lease logic as a separate bounded task.

---

## 32. Decision register and required approvals

| ID | Decision | Default / source | Agent action |
|---|---|---|---|
| AG-DEC-01 | Paired kit product | Two fixed modes | Preserve |
| AG-DEC-02 | Pair membership | DB normalized model | Preserve unless ADR changes |
| AG-DEC-03 | Replacement history | Partial unique current child | Preserve |
| AG-DEC-04 | ICE challenge outage | Adaptive fallback proposed | **Ask founder** |
| AG-DEC-05 | WhatsApp phone disclosure | Explicit opt-in, default off | Preserve |
| AG-DEC-06 | Finder location storage | Encrypted child table | Confirm with DB approval |
| AG-DEC-07 | Finder retention | Proposed <=180 days | **Ask founder/legal** |
| AG-DEC-08 | QR ECC | Q preferred; M if QA | Physical QA decision |
| AG-DEC-09 | Print credential packaging | QA-approved scratch-off or sealed | Operations decision |
| AG-DEC-10 | Email sender domain | Verified production domain | Confirm before sending |
| AG-DEC-11 | API source of truth | Complete validated OpenAPI to be generated | Implement later |
| AG-DEC-12 | Frontend route inventory | Final UI/UX document | Do not invent final route map here |

---

## 33. Final adoption checklist

- [ ] Founder reviewed and approved this agent policy.
- [ ] PRD v1.1, TDD, DB, and API docs are committed to repository.
- [ ] Unresolved architecture/privacy decisions assigned.
- [ ] Root `AGENTS.md` created after repository scaffolding.
- [ ] Antigravity workspace rules configured and verified.
- [ ] Codex can read root `AGENTS.md`.
- [ ] Branch/worktree ownership prevents simultaneous conflicting edits.
- [ ] Test scripts are real and executable.
- [ ] CI checks are configured.
- [ ] Staging and production credentials isolated.
- [ ] No raw customer data supplied to agents.
- [ ] Sensitive changes require human review.
- [ ] Database migrations require approval and test evidence.
- [ ] OpenAPI drift is checked.
- [ ] Public bilingual QA is enforced.
- [ ] Agent reports distinguish implemented from verified.
- [ ] UI/UX screen and navigation document remains scheduled **last**.

---

## 34. Next document

After founder review of this policy, the next requested artifact is:

**Document 5 — SafeReturn Implementation Plan & Task Backlog** (`docs/06-implementation-plan.md`).

It should break the approved architecture into small, ordered tasks for Antigravity and Codex, with dependencies, exact acceptance criteria, files/modules, test gates, and review checkpoints. **Do not create that document until explicitly requested.**

**End of Document 4.**
