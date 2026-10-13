# SafeReturn — Deployment & Operations Runbook v1.2

**Document:** SR-OPS-008 (Document 09 of 11)  
**Version:** 1.2 · **Prepared:** 12 October 2026 · **Status:** proposed implementation and operations contract; requires founder/technical/security approval  
**Scope:** Lahore pilot; current public paired QR sticker product and future-ready feature-gated multi-product capabilities  
**Repository destination:** `docs/09-deployment-operations.md`  
**Inputs:** SafeReturn Documents 01–08 v1.2, prior Deployment & Operations Runbook v1.1.

> **Important:** This document specifies procedures to implement and verify; it is **not** evidence that provider accounts, backups, CI, payment integrations, domains, credentials, or deployments are operational. Provider capabilities, plan limits, pricing, UI screens, regions and API behavior must be confirmed in the user's accounts before launch. Never execute destructive or production commands merely because they appear here.

## 0. Authority, precedence and operational contract

1. Approved Product Requirements v1.2 and formal founder ADRs govern commercial, safety and privacy behavior.
2. Technical Design v1.2 governs architecture, authentication, transaction boundaries and jobs.
3. Database Design v1.2 governs migration/DDL/constraints and state transitions; **do not independently invent or rename schema fields**.
4. API Contract v1.2 governs exact routes/DTOs; this operations document uses conceptual endpoint names, not replacements for the canonical API.
5. Agent Instructions v1.2 govern AI-assisted changes and secrets.
6. Implementation Plan v1.2 governs ticket ordering, owners and release gates.
7. Security & Privacy v1.2 governs access, retention, secure files, consent, incident response and necessary approvals.
8. Test Plan v1.2 governs test IDs, fixtures, evidence, physical print tests and stop-ship findings.
9. Original v1.1 runbook is preserved in **Part B**, as reference where not superseded; Part A wins on v1.2 changes.

**Release principle:** never reconcile different table names/statuses/paths automatically. Open a named ADR, update Docs 01–08 where required, generate reviewed migration + contract changes, and record a test. Parent/child tag rules, bank approval and public ICE privacy are security boundaries, not configuration conveniences.

### 0.1 Non-negotiable operational invariants

- One **new** Pair ID has two *current* unique public QR identities (`lost`, `ice`), one activation entitlement/credential, and pair-level atomic ownership. One account can own many such pairs. Lost and ICE details remain independently editable, with server-side ownership checks per requested QR.
- Buying three Lost stickers and two ICE stickers for one newly purchased pair means **two unique URLs and five physical copies**, not five pairs. Multiple copies of an existing QR share its editable profile. Future add-ons may reuse an authorized existing tag or buy a new pair; feature-gate this until approved.
- Scan-to-activate preserves a non-secret pending scan context over login, but scans alone never authorize claiming ownership. Activated tag pages stay anonymously usable for finders/emergency responders.
- Customer-facing price totals, product/variant snapshots, reservation ownership, allocation, payment state and print manifest are authoritative **only in Supabase PostgreSQL** through the backend.
- Manual transfer evidence is never proof of settlement; finance checks trusted bank records. Future gateway webhook calls must be verified, idempotent and safely switchable without replacing the order model.
- Sensitive PDFs, concealed activation materials, and payment images use **private Supabase Storage** with short-lived server-authorized access; public product photographs/marketing images may use Cloudinary. Do not upload confidential PDFs or evidence to public Cloudinary delivery.
- PDF source QR artwork remains readable: logo must not break contrast, quiet zone, print size or physical scan QA. Prefer vector QR drawings and compact PDF compression; no unnecessary full-page rasterized QR imagery.
- Google Sheets is a delayed, least-privilege **finance mirror**, never source of truth or a payment processor. Retries are durable; finance updates must not depend on Sheets availability.
- A delivery status must not erase orders, allocated tag IDs, product/variant snapshots, payment review/audit or lawful recordkeeping. Delete temporary objects only after an approved retention window and, when applicable, verified delivery and absence of holds.
- Customer/admin/public endpoints, ICE phone reveal, WhatsApp consent, finder messages, geolocation, transactional email outbox, English/Urdu, and physical credential concealment retain prior v1.1 protections.

## 1. Production topology and trust boundaries

```mermaid
flowchart TD
  BR[Browser: customer / finder / admin] -->|HTTPS| V[Vercel: Next.js]
  V -->|HTTPS /api/v1| API[Railway: FastAPI API]
  BR -->|Auth supported flow| AUTH[Supabase Auth]
  API --> DB[(Supabase Postgres: sole business truth)]
  API --> ST[(Supabase private Storage: evidence and print PDFs)]
  API -->|public media metadata| CL[Cloudinary: public product assets]
  API -->|token verification| TURN[Cloudflare Turnstile]
  W[Railway: background worker / scheduler] --> DB
  W --> ST
  W -->|outbox| RE[Resend]
  W -->|approved finance mirror| GS[Google Sheets API]
  BANK[Finance staff / future payment webhook] -->|verified events| API
  STAFF[Authorized finance / fulfillment admin] --> V
```

**Deployment units:** one frontend, one FastAPI modular monolith, and at least one separately running durable-job worker. A lightweight scheduled invocation may enqueue database-backed jobs; avoid mandatory Redis/Kafka/Celery for pilot unless justified and approved. Payments, emails, printing, Sheets sync and cleanup should share consistent job leasing, backoff, dedupe and audit semantics, but can be separately rate-limited. A single worker outage must not corrupt completed transactional writes.

| Component | Responsible for | Must not hold/do |
|---|---|---|
| Vercel web | public storefront, activation UI, dashboard, admin UI, bilingual/RTL QR pages | service-role keys, raw bank credentials, private PDF URLs in public HTML |
| Railway API | JWT validation, price/stock/ownership checks, idempotent order/payment transitions, signed object access | silently confirm payments, trust user-supplied owner IDs |
| Supabase Postgres/Auth | transactionally consistent entities, constraints, identity, audit, outbox | public reads of restricted business tables |
| Supabase Storage | private screenshot and printable-artifact bytes | permanently public print URLs or unrestricted client listing |
| Cloudinary | public product photos, responsive marketing thumbnails | payment evidence, emergency profiles, QR activation secrets |
| Worker/scheduler | retryable email, PDF, Sheets, retention, reconciliation jobs | non-idempotent side effects without state checking |
| Resend | transactional messages | authoritative finder message persistence |
| Sheets | restricted finance export | approving payments or determining allocated inventory |

### 1.1 Separate failure domains

Web availability, API health, DB transaction health, Storage download, outbox mail delivery, finance mirror delivery and printing are distinct. Monitoring must expose each. `HTTP 200` on homepage is not adequate readiness evidence. Provide `/health/live` for process liveness and a protected or sanitized readiness check testing required dependencies; do not leak connection details.

## 2. Environments, tenancy and safe promotion

| Resource | Local | Staging | Production |
|---|---|---|---|
| Frontend/API | localhost separate ports | independent Vercel/Railway deployments | approved customer domains |
| PostgreSQL/Auth | local/disposable dedicated project | separate Supabase project | isolated production Supabase project |
| Storage buckets | disposable test objects | staging private buckets | production private buckets |
| Cloudinary | test folder/cloud | staging prefix or independent cloud | public product assets only |
| Google Sheets | test spreadsheet | non-production test spreadsheet | restricted finance spreadsheet |
| Payment | synthetic/manual sandbox | synthetic/manual, provider sandbox later | manual verified settlement; gateway feature-off |
| Email | intercepted or test-only | authorized test recipients | verified domain and restricted secrets |
| QR public host | synthetic URL | staging token host, never printed to customers | verified long-lived canonical domain |

Never share production tokens, personally identifying rows, medical notes, actual payment images or customer location with development/test/AI tools. Use synthetic fixtures. Enforce separate secrets, DB credentials, buckets, service accounts, sheets, and provider accounts where practical. No staging deployment may write into production Sheets or cloud object prefixes.

### 2.1 Release promotion

Code goes `feature branch -> pull request -> CI -> review -> staging migration -> staging smoke, payments and physical QA -> explicit production approval -> ordered production release -> postdeploy smoke`. Enable new product and payment features using server-side feature flags **after** code and schema backward compatibility are verified. Staff may not toggle a flag to bypass auth, payment verification, medical consent or print QA.

## 3. Account ownership and launch prerequisites

Maintain an offline approved inventory of account owner, recovery contact, billing account, region, plan, quota, MFA status, callback domains and named backups. Services: DNS/domain registrar, Vercel, Railway, Supabase (Auth, DB, Storage), Cloudinary, Resend, Turnstile, Google Cloud project/service account/Sheets, transfer/bank account, and later gateway merchant account. Enforce hardware/passkey/TOTP MFA where provider supports it; finance/admin app requires the Document 07 approved MFA policy.

**Before printing real product:** domain ownership, permanence/redirect policy, SSL/TLS, QR route, final logo and quiet-zone geometry, weather/resolution/material print scans and fulfillment credential concealment are signed off. A staging QR URL must never enter physical customer inventory.

## 4. Repository and service structure (proposed, not an assertion of an existing repo)

```text
safereturn/
  AGENTS.md
  docs/01-PRD.md ... docs/09-deployment-operations.md
  backend/
    app/main.py
    app/core/config.py
    app/db.py
    app/routers/           # auth, public, scans, me, catalog, checkout, payments, admin
    app/services/          # authorization, qr, catalog, orders, payments, storage, print, sheets
    app/integrations/      # bank_manual, payment_gateway, supabase_storage, cloudinary, resend, sheets
    app/workers/           # outbox, print, cleanup, reconciliation
    migrations/            # reviewed Alembic migrations only
    tests/
    requirements.txt
    requirements.lock.txt  # pinned via actual selected package workflow
  frontend/
    app/                   # Next.js App Router
    components/
    lib/
    public/
  scripts/                 # safe operational scripts, NO prod default
  .github/workflows/
  .env.example
  .gitignore
```

This proposed structure aligns with the selected stack in the existing v1.2 documents, not a license for agents to implement alternative schema/route contracts. Database implementation follows the approved SQLAlchemy/Alembic approach in Docs 02–06; any requested switch to handwritten SQL for all runtime queries requires its own reviewed ADR and compatible migrations.

## 5. Secrets and configuration matrix

| Config (example name; reconcile with actual checked-in config) | Owner | Scope and safeguards |
|---|---|---|
| `DATABASE_URL` | API/worker/migrations | TLS, secrets manager, dedicated least-privilege DB roles |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | frontend where appropriate | public key may ship; use correct project/RLS design |
| `SUPABASE_SERVICE_ROLE_KEY` | server-only when absolutely needed | bypasses RLS; never in browser, logs, CI artifacts |
| `SUPABASE_JWT_*` / verifier config | API | validate issuer/audience/signature/expiry; use supported JWKS rotation |
| `STORAGE_PRIVATE_BUCKET_EVIDENCE` | server | payment evidence access-controlled |
| `STORAGE_PRIVATE_BUCKET_PRINT` | server | PDFs and concealed insert private |
| `CLOUDINARY_CLOUD_NAME` | frontend/server | public identifier only |
| `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | trusted backend | signed admin uploads, no browser exposure |
| `RESEND_API_KEY`, `RESEND_FROM` | worker | verified sender, restricted mail purpose |
| `TURNSTILE_SITE_KEY` | client | public challenge site key |
| `TURNSTILE_SECRET_KEY` | server | never client; fallback by approved ICE policy |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | server/worker | restricted spreadsheet, no public link |
| `GOOGLE_SERVICE_ACCOUNT_JSON` or workload identity | worker | grant sheet minimum permission; never commit JSON |
| `PAYMENT_MODE` / gateway settings | backend | `manual` in pilot; sandbox/real gating audited |
| `PAYMENT_WEBHOOK_SECRET` | backend when provider enabled | exact raw-body verification, replay resistance |
| `PUBLIC_APP_URL`, `PUBLIC_API_URL`, `QR_CANONICAL_ORIGIN` | environment | controlled CORS and redirect allowlists |
| `APP_ENV`, `LOG_LEVEL`, `SENTRY_*` if approved | relevant service | sanitize PII and credentials |
| `FEATURE_*` flags | server-side | explicit product and provider release gates |

Use `.env.example` with empty or synthetic values. `.env`, secret JSON, PDF manifests, screenshots, service-role keys, token-bearing logs and local exports must be ignored by Git. Any leaked credential requires revocation, rotation, incident assessment and verification before resuming deployment. Review Vercel `NEXT_PUBLIC_` naming to avoid accidentally publishing server secrets.

## 6. Supabase database, Auth and private Storage

1. Create isolated project, choose region using user/latency/legal/privacy requirements (verify actual availability).
2. Configure Auth redirect URL allowlists and verified email for sensitive ownership transitions; check JWT validation in FastAPI.
3. Review access roles: migration role, API least-privilege role, worker role, support/finance/fulfillment app roles. Enable RLS on all business tables; do not rely on RLS when service-role credentials are used.
4. Create **private** storage buckets for `payment-evidence` and `print-artifacts` (exact bucket labels decided/configured consistently). Restrict object path prefixes and allowed MIME/types; content scanning/validation, byte limits, image pixel limits and PDF generation controls apply.
5. Keep object metadata (`storage_key`, owner, job ID, retention/disposition) in DB. Payment screenshots must not be enumerable by customers; print PDFs only downloadable to assigned fulfillment roles through bounded access.
6. Do not expose unprotected `/storage/v1/object/public/...` locations for evidence, PDFs or secrets. Return a signed download URL only after backend authorization and short expiry, with `Cache-Control: private, no-store` for sensitive responses where controllable.
7. Confirm storage backup semantics separately from database PITR; **a DB backup does not necessarily back up object bytes**. Back up critical artifacts only for their approved retention window; verified deletion must also apply to managed replicas according to provider guarantees.
8. Test RLS cross-owner access, old/signed URL expiry, role revocation, deleted-object behavior, malware/image mismatches and duplicate/missing object recovery.

### 6.1 Object key design

Use opaque keys not including customer emails, phone numbers, medical content, account numbers, raw activation secrets or public QR tokens. Example *shape*, not a canonical API: `payment-evidence/<random-object-id>.webp`, `print-artifacts/<random-job-id>.pdf`. Database joins provide ownership. Storage uploads first enter a temporary quarantined status until server-side verification completes; reconciliation deletes orphan uploads. Never treat a client-supplied storage key as authorized without DB ownership and role checks.

## 7. Cloudinary media operations

Cloudinary serves **only approved public catalog/marketing imagery** in v1.2. Product photo records store an opaque provider asset/public ID, width/height, ordering and allowed transformation metadata; archived product orders retain snapshots without relying on a mutable remote title or variant price. Admin upload runs through an authenticated backend-created signed policy/preset with MIME, size and transformation limits; moderate unsafe/misleading content as needed. For unpublish/delete, disallow new frontend display, invalidate cached images if appropriate, and follow image retention/copyright policy. Do not use Cloudinary public URLs for private payment evidence or production PDFs. For future customer asset media, do not assume public media policy suffices; add ADR and separate private delivery design.

## 8. Railway API/worker deployment and scheduling

Configure independent Railway services for API and durable worker, sharing the same reviewed version/build and proper server-only secrets. API uses the production ASGI entrypoint, readiness/liveness health checks, explicit allowed hosts/CORS, TLS from ingress to database, bounded request bodies, safe concurrency/pool limits and graceful shutdown. Worker leases due rows in Postgres with transactions (`FOR UPDATE SKIP LOCKED` when specified by the approved DB contract); jobs track state, attempt count, retry-at/lease expiry, idempotency key and last sanitized error.

| Job type | Input / source of truth | Retry and safety condition |
|---|---|---|
| Finder notification | committed finder message + transactional outbox | at-least-once attempt; no lost message on Resend outage |
| PDF rendering | payment-confirmed, allocated, immutable print manifest | deterministic job key; regenerate same content if retried |
| Sheets finance sync | committed payment/order event | upsert by stable order/payment record key, never append duplicate rows |
| Retention cleanup | eligible DB metadata with expiry and no legal hold | mark-delete-confirm workflow; retry provider failures |
| Orphan reconciliation | incomplete uploads/queued artifacts | identify and remove only confirmed unreferenced objects |
| Reservation cleanup | lease state and payment submission status | do not release a pair while valid payment is under review |
| Payment reconciliation | pending bank manual status or verified gateway event | no automatic approval from screenshot |
| Notification to staff | committed admin event | backoff/rate limiting; no sensitive payload in logs |

**Scheduling:** choose an approved low-cost recurring trigger/worker loop compatible with Railway and database load; avoid fixed sub-minute polling when unnecessary. Job leases must recover after a worker crash, using DB idempotency and reconciliation. Do not generate production PDFs inside a synchronous customer API request. Keep one writer per job and audit reprints.

### 8.1 Deployment-safe worker compatibility

For each migration deploy, verify that old worker and new API can co-exist temporarily. Introduce nullable/additive schema first, deploy compatible reader/writer, backfill safely, switch logic/flags, and remove old data only in a later authorized release. Worker rollback must not resurrect duplicate payment confirmations or reorder already-dispatched shipments.

## 9. Vercel frontend and canonical QR domain

Connect repository and appropriate framework runtime. Inject only public environment variables in client bundles. Configure approved API origin(s), secure cookies/session model, CSRF protection where cookie-based auth applies, security headers, Next.js server/client boundaries, language routing (English/Urdu and RTL), low-bandwidth fallbacks, and strict cache controls on accounts/admin/ICE/private activation content. Public scan routes must remain accessible without account creation.

Activation deep-link logic: `/q/{token}` resolves a public QR, shows Activate QR if eligible/unactivated, stores only non-secret pending context across auth redirects, and backend rechecks entitlement when user confirms. Ensure failed/pending/expired scan returns a humane bilingual state rather than leaking pair ownership or internal DB data. Prevent open redirects and token leakage through third-party analytics or referer headers.

Canonical QR URLs printed on physical inventory must never be casually changed; if changing website host, use permanent, tested redirects to the same token handler, retain DNS/TLS and verify after deploy. Emergency responder service must remain accessible during admin/reporting dependency outages as far as approved safe degradation allows.

## 10. Product catalog, variant launch and homepage operations

P0 published product is QR stickers; future keychains, badges and attachment products are in data model but **must remain unlisted/unpurchasable** unless approvals/tests pass. Admin product creation requires role authorization; publish/unpublish and featured ordering are audited. Each variant has immutable SKU or catalog identity, price and applicable size/material/template validation. Store purchased product and variant snapshots (ID, SKU, name, selection and charged price) in the order transaction, so later edits cannot mutate prior orders. Featured homepage carousel must only query approved published products and must fail gracefully if Cloudinary is unavailable.

Operational flags (names illustrative): `MULTI_PRODUCT_ENABLED`, `EXISTING_QR_REUSE_ENABLED`, `NEW_PRODUCT_PRINT_TEMPLATES_ENABLED`. Enable separately after legal/privacy, fulfillment, manufacturing, QA and secure profile-isolation tests. A keychain may use existing QR or issue a new pair; repeated copies on one QR share one editable profile. If a new pair is ordered, both current children are provisioned, not a lone unpaired keychain tag.

## 11. Checkout, inventory and payment operations

### 11.1 Inventory reservation correctness

At checkout, backend validates catalog variant availability, calculates totals in integer-decimal PKR representation, captures purchase snapshots, and reserves exactly the necessary *new pairs* with exclusive database locking. Copies of one QR do not consume extra pair identities. A reused QR requires proof of ownership; allocation may not point to someone else's QR. Reservations have an approved TTL and state transitions but are not forcibly released when a valid manual-payment submission is awaiting investigation. Reconcile abandoned carts separately from pending review orders.

### 11.2 Manual settlement now; gateway later

```mermaid
flowchart LR
  O[Confirmed order and reserved identities] --> P[Payment intent / manual reference]
  P --> S[Customer submits reference + optional evidence]
  S --> R[Pending human review]
  R -->|trusted bank confirmation| C[Paid event, transactionally recorded]
  R -->|no settlement, policy applied| D[Rejected / needs action]
  C --> A[Final allocation + print job enqueue]
```

Documented maker-checker principle: finance reviewer confirms account settlement using trusted bank-side records, not screenshot text, Google Sheets row, or AI analysis. Avoid displaying full sender account identifiers to non-finance roles; use masking. Treat customer-entered holder name/account as untrusted evidence and prohibit auto-payment confirmation. Resolve duplicate amount/reference and split payments via a documented exception workflow; never silently allocate from unverified payment.

### 11.3 Gateway adapter evolution / cutover

- Keep a stable order/payment-intent record, payment-event history, `provider`, `provider_reference`, `verification_state`, and immutable idempotency/audit fields in approved DB schema. Any gateway can only update payment through a reviewed adapter and common payment state machine.
- Introduce provider keys and callback route only server-side in staging first. Validate webhook authenticity over raw body, expected merchant/account, event type, currency, amount, destination order and replay/idempotency; do not trust browser `success` redirect.
- Replay duplicate, late, failed, out-of-order, refund, reversed and disputed events through staging. No duplicated pair allocation, printed sheet, shipping release or finance rows.
- Deploy manual and gateway paths side-by-side behind flags; **existing manual payment orders stay in their original mode**, and their review workflow continues until resolved. Never rewrite pending orders en masse to the new gateway.
- Flip new-checkout mode only after bank/reconciliation sign-off and rollback plan. Disable provider capture on incident; reconciliation remains authoritative and refunds/chargebacks have documented operational handling.
- Set up merchant dispute/reversal review; verified paid status may need separate post-settlement reversal states without erasing the prior approval event.

## 12. Google Sheets finance mirror

Dedicated Google Cloud project/service account (or equivalent reviewed delegated identity); share **only** the target spreadsheet with the service account and restrict human access to finance roles. If connected via an app integration, verify account permissions and quotas. Suggested columns: stable `order_id`, `payment_id`, timestamp, masked account/reference, product/variant summary (non-sensitive), total, method, authoritative status, last-sync time, review actor ID, and authorized evidence *reference* where safe. Do **not** embed raw screenshot bytes, full account numbers, or unrestricted signed storage URLs.

Workflow: Postgres transaction commits order/payment change and durable sync event → worker reads authoritative DB snapshot → Google Sheets upsert by stable ID/key → record sync success/retry state in DB. If Sheets API returns 429 or transient 5xx, retry with capped exponential backoff/jitter; classify persistent permission/schema errors for alerting. Never reverse payment status because Sheets is unavailable. Protect against duplicated rows on retry and worksheet reordering; prefer a stable-key lookup/mapping strategy documented in code. Periodically reconcile committed DB finance events with sheet rows and report inconsistencies without auto-editing bank data.

## 13. QR generation, print jobs, compact PDF and fulfillment

### 13.1 Batch manufacture and stock

Admin enters requested count of **pairs**; server generates `2 × count` distinct QR tokens, one lost and one ICE per pair, and one concealed activation credential/entitlement. Mark print/QA status accurately. Inventory alert thresholds are settings monitored in DB, not an automatic uncontrolled batch-generation loop. Generated tokens must point to finalized canonical domain. Owner/email/private ICE information and activation secrets must never appear in publicly visible QR payloads. Full pair QA precedes shipment.

### 13.2 PDF render contract and byte discipline

For a verified-paid allocated order, generate a print manifest with immutable line snapshots and per-tag size/counts. Output ordering: **Lost QR copies first, Emergency QR copies second**; grouped by appropriate size, cutting/bleed/quiet-zone arrangement and bilingual text; print each selected count of the **same QR URL**, not fresh tokens. For each QR: center small SafeReturn logo with controlled obstruction, ECC/contrast validated against approved physical specification; preserve minimum quiet zone and approved minimum finished dimensions. Pair Reference and hidden activation insert are production artifacts that must stay distinct and protected.

PDF optimization: embed **vector modules and vector/plain logo where licensed/available**; raster assets only where needed at print-appropriate resolution; subset fonts; avoid repeating large encoded images; compress streams when compatible; generate in-memory/temporary scratch within resource limits, upload private object after QA, then immediately remove worker scratch. Store exact byte size, SHA-256/content hash, document version and printer template version, render attempt, object path and retention cutoff in metadata. Avoid conflating PDF compression success with QR scan quality—test final physical print across devices and worn/small samples.

### 13.3 Ready to Ship queue

Only paid/confirmed, allocated, successfully rendered, authorization-approved and QA-passed orders reach Ready to Ship. Fulfillment admin downloads short-lived authorized PDF, prints/cuts, checks count/dimensions/token labels, seals matching credentials and records carrier dispatch/tracking. Order transitions require valid predecessor state and audit. For bad print, create authorized versioned reprint, recording reason and invalidating outdated print-job outputs where needed; never generate alternate tokens as a side effect of printer retry. Multi-product items require approved product-specific template/manufacturing route before being eligible for automated physical release.

## 14. Retention, deletion, backups and legal holds

The actual durations require founder/privacy/legal review; **do not silently turn example numbers into fixed production policy**. Default proposed operating pattern:

| Object / record | Lifecycle trigger | Keep/delete policy (approval required) |
|---|---|---|
| Payment screenshots | payment review completed | keep only through approved dispute/fraud window; delete byte objects after deadline/no hold |
| Print PDFs | verified delivery and fulfilled/reprint window | delete after configured grace period (illustrative 7 days), if no open dispute/reprint/hold |
| Worker temporary files | successful upload / failed render | delete as soon as no longer needed |
| Cloudinary public product images | product archived/removed | approved asset/brand retention; invalidate display and cache |
| Order line snapshots | order completed | retain per approved records policy, even if PDFs deleted |
| Allocated QR IDs + copy/size specifications | order completed | retain required history for support, legitimate reprints, audit |
| Public QR tokens | tag replaced / ownership changes | preserve historical revocation reference; never recycle tokens |
| Payment attempts/verified events | financial record | retain protected history as legally/operationally required |
| Finder messages/location/ICE data | lifecycle-specific | follow previously approved Document 07 retention, consent and erasure process |

**Deletion procedure:** (1) query eligible object with DB lock and policy version, (2) recheck holds, fulfillment and payment-reconciliation state, (3) mark pending deletion, (4) call storage provider delete with retry idempotency, (5) verify absence or documented provider acknowledgment, (6) record timestamp/disposition and leave non-sensitive audit metadata. Failure remains retryable/alerted, not silently marked successful. Consider object copies, CDN caches, backups and signed URL expiry; explain any delayed backup purge in privacy notice. Allow narrowly permissioned manual delete when approved, never as a route to erase transaction evidence before review.

## 15. Backup, disaster recovery and restoration

Backups: verify managed Postgres backup/PITR availability for **the actual purchased plan**; define schedule, geographic/legal risk, encryption, export custody, retention and named operator. Object storage backups/versioning (if required) must be separate from DB backup; Cloudinary public assets can be restored from source originals if policy allows. Protect Sheets reconciliation state in DB; Sheets can be reconstructed from authorized masked DB snapshots. Do not assume email-provider and payment-provider events can be reconstructed if not persisted.

Restore drill at least before launch and periodically afterwards: create isolated environment; restore DB and required private objects; validate pair/child uniqueness, orders and payment histories, QR token routing, revoked IDs, secrets and authorization policies. Reconcile artifacts missing from private storage; do not automatically rerender a PDF if order has no verified allocation. RTO/RPO are **pending approval**, not invented. Test failure mode where database restore precedes newest payment provider events; replay only verified/idempotent events and require finance reconciliation before dispatch.

## 16. CI/CD, migrations, rollout and rollback

### 16.1 CI checks

Run formatting/lint/type checks, dependency/secret scans, pytest API/unit/security cases, PostgreSQL integration & migration tests on real Postgres, generated OpenAPI drift validation, frontend TypeScript/build tests, Playwright bilingual flows and role-based access, storage ACL tests, image/PDF fixture size limits, QR image scan tests and job retry tests. Preserve synthetic fixtures only. Published results distinguish *CI simulated*, *staging provider-verified* and *actual physical printed* evidence; never claim unrun suites passed.

### 16.2 Migration release procedure

1. Backup/snapshot verified as available and tested; confirm scope and migration locks.
2. Compare live migration revision against approved schema in Document 03 and reviewed Alembic revision, not against guessed table names.
3. Add new tables/nullable columns/constraints in a safe expand phase; run dry migration on production-like staging and review query plans/index sizes.
4. Backfill in bounded idempotent batches while old code still works. Reconcile foreign keys, exclusive pair reservations, product snapshots and payment history.
5. Deploy compatible API and workers; only then feature-enable new logic. Check rollback compatibility before deleting old columns.
6. Record migration checksum, reviewer, release ID, timestamp, environment, logs and post-migration data assertions.
7. Contract/removal migrations happen in a later approved deployment with a separate backup/rollback strategy.

Example *read-only* preflight on a trusted workstation (commands must be reconciled to actual repo and credentials):

```bash
# From backend/; read-only migration inspection only
alembic current
alembic history --verbose
# Do NOT run "alembic upgrade head" on production until authorized migration review.
```

### 16.3 Ordered deploy

Release sequence generally: approve decisions → preflight and backup → compatible DB expansion → worker/API rollout → frontend rollout → staging+production smoke → progressive feature-flag activation → monitor and reconcile. Old frontend/API callers must not break while caches roll over. Rollback means revert code/flags to compatible state, **not** automatically downgrade a destructive schema or erase postdeploy orders. Announce planned maintenance for high-risk identity/payment operations if zero-downtime safety cannot be proven.

## 17. Monitoring, alerts and operational dashboards

Track alerts by environment, service, severity, on-call owner, runbook link, sample-size threshold, dedupe and acknowledgement. Logs must be structured (`request_id`, coarse event type, service/version, safe resource ID) and redact tokens, full phones, bank details, finder messages, geolocation, medical notes, activation secrets, signed URLs, service-account JSON and raw webhook bodies.

| Signal | Risk | Response |
|---|---|---|
| public QR route 5xx / latency spike | finders/ICE unavailable | page operations; test canonical domain/API/DB; apply approved emergency fallback |
| login/activation failures; duplicate claim attempts | account takeover / usability | inspect sanitized auth telemetry, rate-limit, check pair entitlement |
| reservation mismatch / negative available pairs | overselling or double allocation | pause checkout/allocation, reconcile locks and payments |
| payment review queue stale | delayed shipment | notify finance reviewer; never auto-approve screenshot |
| webhook signature failures / unexpected retries | gateway spoof/replay | disable gateway flag if warranted, preserve raw evidence only in restricted incident store |
| PDF generation failure / large output | missing shipment file, storage costs | retry safely, inspect template/font/asset growth, enforce budget/quota |
| Ready to Ship backlog | fulfillment blockage | escalate staffing, QA/carrier investigation |
| Storage growth, orphan evidence/PDFs | quota/cost exposure | audit retention jobs and holds, reconcile before delete |
| Sheets lag / 403/429/5xx | finance reporting drift | retry, rotate service permissions under change control |
| outbox lag / Resend errors | finder mail delays | preserve DB messages, retry with backoff, communicate limitations |
| Cloudinary 404 / high egress | product-media UX | temporary catalog fallback, inspect transformation/caching |
| consent/phone leak indicator | sensitive data exposure | security incident process, revoke access, evaluate notification |
| unsuccessful backup/restore drill | data-loss risk | stop launch/release gate, repair before proceeding |

Use provider metrics, Railway logs, Vercel telemetry, Supabase insight tools and a carefully scoped dashboard. Set cost alarms for Storage bytes/egress, Railway CPU/memory/worker runtime, Vercel bandwidth/builds, Cloudinary transforms/storage, email sends, Sheets API quotas and DB connections. Alert thresholds and SLOs are measurable release decisions, not default guarantees.

## 18. Incident response and common failures

For any incident: classify impact, page owner, disable risky feature flags if safe, preserve audit trail without copying sensitive user data into chats, identify last known good release, communicate with approved templates, remediate, test, and write an action-oriented postmortem. Security & Privacy Document 07 governs legal/consent/escalation responsibilities.

| Incident | Contain / recover | Never do |
|---|---|---|
| Suspicious bank screenshot / mismatch | hold payment review; independent bank reconciliation, audit result | set `paid` from screenshot text |
| Gateway webhook outage | queue verified events and provider reconciliation; gate new checkouts if necessary | trust browser callback or duplicate allocation |
| PDF object missing | check job/metadata; authorized deterministic regeneration if paid and allocated | generate new QR identity because PDF is missing |
| Supabase private bucket becomes public | revoke public access, rotate affected keys/URLs, incident review | assume deleting frontend link restores privacy |
| Sheets inaccessible | retry durable sync; keep Postgres authoritative | roll back valid bank verification |
| Cloudinary outage | show placeholder and still allow existing published product pages as appropriate | expose private storage media as fallback |
| User sees another QR profile | disable affected endpoint, IDOR incident response, query audit and fix policy | rely solely on hiding UI button |
| Reservation expires during valid payment review | preserve hold, finance exception reconciliation | reallocate pair to another order |
| Worker repeated jobs | stop worker, dedupe by idempotency key, inspect lease state | remove history to hide duplicates |
| Invalid QR scans/print mismatch | quarantine print batch, version revised artwork, physical QA repeat | ship without rescan or change token silently |
| ICE reveal dependency outage | apply only founder-approved security/availability fallback | silently expose full phone in initial page markup |
| Account compromise | revoke sessions, MFA reset process, inventory/QR ownership review | transfer tags without verification/audit |

## 19. Security and privacy release checklist

- [ ] Verify authorized customer can manage their own many pairs and **cannot** edit another customer's QR/tag/profile, including attachment/reuse workflows.
- [ ] Verify lost vs ICE profiles remain independent; ICE full phone absent from HTML/SSR/hydration/public JSON until protected reveal.
- [ ] Verify pending QR scan survives login but cannot substitute for activation entitlement.
- [ ] Verify price calculations, order/product snapshots, inventory locks, payment events and role checks are backend-controlled.
- [ ] Verify finance/fulfillment/admin separation, MFA, review audit and manual bank verification.
- [ ] Verify Cloudinary carries no confidential objects; Supabase Storage stays private and object downloads are short-lived authorized.
- [ ] Verify screenshot and PDF retention/cleanup holds are approved, testable and audit-preserving.
- [ ] Verify Sheets mirror stores masked fields and retry does not duplicate rows.
- [ ] Verify QR logo/cut dimensions, quiet zone, ECC and real device scan tests; activation insert concealed.
- [ ] Verify public anonymous Lost/ICE use, bilingual RTL and optional finder location/WhatsApp consent.
- [ ] Verify secret scanning, backups, restore drill, emergency rollback/feature flags and alert notifications.

## 20. Acceptance evidence and launch gates

Evidence packet includes: reviewed ADR list, release Git SHA/CI artifact, approved migrations/backfill report, clean CI and staging suite results, OpenAPI drift result, RLS cross-owner screenshots/logs with synthetic data, webhook replay test if gateway enabled, controlled finance review test, vector PDF size/print QA measurements, QR scans on actual substrates/devices, spreadsheet outage recovery, Storage signed-access/delete test, backup+restore drill and on-call/incident simulation. Tie evidence to Document 08 cases (including new QR and print/payment scenarios) and Document 06 release gates; do not call a test passed until executed.

**Stop-ship:** successful unauthorized activation or cross-user profile access, exposed initial ICE numbers, evidence/PDF public-read exposure, duplicate pair allocation, screenshot-triggered auto-payment approval, irreproducible payment order state, unsafe QR prints, broken canonical QR routing, untested restore, or critical/high unresolved security defects. Founder cannot waive critical risks silently.

## 21. First controlled production rollout

| Step | Owner | Gate/evidence |
|---|---|---|
| Approve unresolved ADRs incl. retention, domain, gateway flag and ICE outage | founder/security/privacy | signed decisions |
| Verify account ownership, budgets, domain and private storage | operations | account checklist |
| Provision secrets, RLS and CI/staging | engineering/security | least-privilege test |
| Test migrations on production-shaped staging data | DB owner | migration report and restore |
| Deploy isolated API/worker/frontend | release owner | health and version checks |
| Confirm manual finance, Sheets mirror and Supabase access | finance/engineering | synthetic verified review and sync failure test |
| Confirm QR batch/inventory, logo sticker and PDF sizes | fulfillment/QA | calibrated physical scans and cut tests |
| Verify scan-login-activate and per-tag edit flows | product QA | E2E traces with synthetic users |
| Enable sticker storefront only | founder | signed release gates |
| Make one controlled pilot order, print, ship, confirm delivery and retention eligibility | ops | audit trail and customer sign-off |
| Expand traffic gradually and watch alerts/quotas | operations | pilot review |

## 22. Operational schedules and maintenance

Use actual workload and provider quotas rather than assuming constant traffic. Suggested initial jobs: outbox prompt retry when pending; print worker on demand; Sheets sync soon after authoritative events; daily inventory threshold check; daily deletion-eligibility/orphan reconciliation; daily payment review age escalation; backup health inspection each day; periodic restore drill (e.g., quarterly if resources allow); weekly dependency/security alerts and cost review. Final frequency, budgets and staffing require approval. Avoid jobs with destructive side effects running automatically before policy and hold checks are verified.

## 23. Sample operational records (fill with real approved data outside this file)

### 23.1 Release record

| Field | Value |
|---|---|
| release ID / commit | `TBD` |
| environment / region | `TBD` |
| approving founder / reviewer | `TBD` |
| migrations + checksums | `TBD` |
| approved flags | `TBD` |
| smoke, PDF, security, restore evidence | `TBD` |
| rollback point and operator | `TBD` |

### 23.2 Incident / retention audit record

`case_id`, `environment`, `timestamp`, `actor_role`, `resource_type`, `opaque_resource_id`, `reason_code`, `approval_reference`, `prior_state`, `result_state`, `external_provider_status`, `follow_up_ticket`, `evidence_location (restricted)`. Never store secrets or raw private payment evidence in a routine ticket.

## 24. Open decisions to resolve before launch

| Decision | Why required | Proposed option, not yet a final approval |
|---|---|---|
| Production QR host and redirect guarantees | printed permanence | one controlled, verified canonical domain |
| ICE reveal fallback during bot provider outage | emergency usability/privacy | founder-approved risk-adaptive rate-limited fallback |
| Screenshot retention duration | disputes/privacy | minimal approved finite window |
| Print PDF post-delivery grace period | reprints/storage budget | illustrative 7-day hold then delete, if no exception |
| Invoice/payment record retention | compliance/disputes | privacy/legal-approved policy |
| Reservation TTL vs pending manual bank review | oversell/fraud | expiry for unpaid checkout only; explicit pending review hold |
| QR product sizes / substrates / minimum printable dimension | logo QR readability | physically QA-approved variants only |
| Product keychain/badge existing QR reuse | identity and manufacturing | gated after profile-isolation + manufacturing tests |
| Payment gateway vendor, callback and reversal policy | future swap safety | provider-neutral intent/event contract now |
| Google Sheets service-account auth/sharing | finance privacy | minimum scoped spreadsheet access |
| Storage quotas, cloud egress and PDF byte budget | cost | measure representative real orders and set ceilings |
| RTO/RPO, monitoring SLO and on-call contact | continuity | measured target after drills |
| Actual schema/API naming reconciliation | implementation drift | finalize migrations/contracts per Docs 03/04 |

## 25. Cross-document implementation traceability

| v1.2 requirement | Documentation to validate | Operating check |
|---|---|---|
| one pair, multiple copies, per-QR editable profiles | Docs 01–04, 07–08 | ownership E2E, print count assertions |
| new vs reused existing QR for future physical products | Docs 01–06 | product feature flags, authorization |
| catalog home carousel + admin product updates | Docs 01–04, 08 | publish/unpublish and Cloudinary fallback |
| reservation + manual payment review | Docs 01–04, 07–08 | double allocation, hold age and bank check |
| gateway portability | Docs 02–05, 07–08 | provider simulator, webhook signature and replay |
| private Supabase evidence/PDFs | Docs 02–04, 07–08 | unauthorized access, retention and restore |
| Cloudinary images | Docs 02–04, 07 | public-only image policy, admin signing |
| Sheets async sync | Docs 02–04, 07–08 | outage/retry/dedup and masking |
| vector PDFs, concealed secret, physical QA | Docs 01–04, 08 and upcoming Doc 10 | actual scans, prints, shipped-kit audit |
| finder/ICE/consent/notifications | Docs 01–08, archived v1.1 | bilingual public QR, ICE reveal and worker retry |
| deploy/backup/incident control | Docs 05–08, this runbook | full staging release packet and restore drill |

## 26. Handoff, sign-off and next document boundary

Document 10 (Physical Product & Fulfillment SOP v1.2) should operationalize this runbook's size variants, print artifact handling, logo QA, hidden activation inserts, fulfillment inspection, PDF reprints, product-specific fabrication, shipment verification and retention handoff. Document 11 (UI/UX v1.2) will enumerate visual surfaces, flows and navigation. **Neither document is created here.**

Required sign-offs before production: founder/product, engineering/database, security/privacy, finance and operations/physical QA. Any unapproved item remains an explicit blocker or gated future feature; no implicit launch authorization.

---

# PART B — ORIGINAL DEPLOYMENT & OPERATIONS RUNBOOK v1.1 (ARCHIVED REFERENCE)

The following original v1.1 text is included verbatim for traceability and preservation of unaffected operating requirements. **Part A v1.2 supersedes any conflicting operational assumption, especially single-product order quantity, private media handling, payment provider separation and additional job/retention controls.** Retained legacy prose and example commands are not automatically verified against the live account or repository.

---

# SafeReturn — Deployment & Operations Runbook

**Supporting document:** 8 of 10 · **Repository target:** `docs/09-deployment-operations.md`  
**Version:** 1.1 — implementation-ready proposal, approval pending · **Date:** 11 October 2026  
**Deployment topology:** Next.js/TypeScript → Vercel; FastAPI/SQLAlchemy/Alembic → Railway web service; separate Railway outbox worker; Supabase Postgres/Auth/private Storage; Resend; Cloudflare Turnstile.  
**Pilot:** Lahore, Pakistan; physical paired lost-item and ICE QR kits.  
**Audience:** founder, technical owner, release operator, security/privacy reviewer, Antigravity Pro, Codex Plus.

> **Safety and accuracy:** This is a procedural specification, not a record of a deployed system. Vendor menus, pricing, free-tier restrictions, regions, CLI flags and secret names can change. Confirm them against each provider's current documentation and actual project settings. All domains, names and commands below are **illustrative** unless explicitly marked as requirements. Do not paste real secrets into chat, source control, CI logs or support tickets.

## 0. Source-of-truth and how to use this runbook

1. **PRD v1.1** governs product behavior and launch requirements.
2. **Document 1 — Technical Design** governs modular-monolith architecture, pair activation, public scan and worker topology.
3. **Document 2 — Database Design & Migrations** governs actual table names, migration order, constraints, RLS and transactional invariants.
4. **Document 3 — API Contract/OpenAPI** governs endpoint names, schemas, error codes and authentication. This document does **not** invent new public routes.
5. **Document 4 — AI Agent Instructions** governs agent permissions, review, branches and coding standards.
6. **Document 5 — Implementation Plan** governs milestones, tickets and definition of done.
7. **Document 6 — Security & Privacy** governs consent, secrets, sensitive data, incident handling and founder decisions.
8. **Document 7 — Test Plan** governs test case IDs, fixtures, release evidence and launch gates.

**Precedence:** approved PRD and founder ADRs → approved technical/API/DB contracts → this operational procedure. If conflict exists, stop, open ADR, update affected documents, and obtain approval. No AI agent may autonomously deploy production, run production migrations, rotate production keys, delete production data, send live mail, or approve a bank payment.

### 0.1 Operational invariants

- One physical kit = **one Pair ID**, **two current QR tags** (`lost`, `ice`), **one concealed activation credential**; atomic pair activation.
- Public QR token is high entropy and **not** the activation secret.
- Anonymous QR pages support English and Urdu; public ICE initial HTML/hydration/API never contains full emergency phone.
- Protected ICE reveal obeys an **approved** Turnstile outage/fallback policy; decision pending.
- Finder browser geolocation is optional, one-time, explicitly consented and never required to send a message.
- WhatsApp link is owner-opt-in; external chats are not SafeReturn messages or Resend notifications.
- Finder message + outbox event commit in one database transaction; separate worker sends email with at-least-once semantics.
- Raast/bank transfers are manually verified; screenshots do not prove settlement.
- QR artwork/print production requires verified permanent domain, minimum dimensions and physical scan QA.
- Logs, traces, backups, metrics and alerts must not leak activation secrets, ICE phones, medical notes, message text, precise coordinates, or payment proof.

### 0.2 Who can perform what

| Role | Local/staging | Production |
|---|---|---|
| Codex / Antigravity | Build code, tests, docs, inspect synthetic fixtures; staging deploy only with explicit instruction | **No autonomous changes**; read-only review if approved |
| Developer | Code, staging migrations and smoke tests | Submit reviewed release, no unsupervised migration |
| Release operator | Approve staging promotion, maintain release log | Executes controlled deploy/rollback after authorization |
| Security/privacy reviewer | Test consent/auth/secrets, review redacted logs | Approves high-risk changes and incident containment |
| Founder | Approves policy, domains, budget and launch | Final go/no-go and business-critical actions |
| Finance operator | Synthetic payment reviews | Independent real bank confirmation; no AI approval |

### 0.3 Runbook conventions

- `[example]` values must be replaced with approved environment-specific values.
- Commands use a suggested monorepo `backend/` and `frontend/`; inspect actual repository before executing.
- `DATABASE_URL` is a **server-only** connection string; never print it in CI or frontend logs.
- Use a named **release ID**, Git commit SHA, operator, environment and timestamp for every change.
- Each section specifies prerequisites, actions, validation, failure behavior and rollback where relevant.

---

## 1. Architecture, regions and deployment topology

```mermaid
flowchart TD
    User[Owner / Finder / Responder] -->|HTTPS| DNS[Controlled QR / app domain]
    DNS --> V[Vercel Next.js frontend]
    V -->|HTTPS API calls| A[Railway FastAPI web]
    V -->|Supported auth flow| AUTH[Supabase Auth]
    A -->|TLS / least privilege| PG[(Supabase PostgreSQL)]
    A -->|Private object access| ST[Supabase Storage]
    A -->|Verify token server-side| CF[Cloudflare Turnstile]
    A -->|Atomic outbox write| PG
    W[Railway outbox worker] -->|Lease + update| PG
    W -->|Transactional send| RE[Resend]
    Admin[Authorized operations staff] -->|MFA / HTTPS| V
```

**Three independent failure domains:** frontend, API/worker, and managed database/providers. A healthy Vercel page does not prove the API, DB or worker is healthy. A successful API request does not prove an email was delivered to the recipient inbox.

### 1.1 Production topology

| Component | Suggested service | Purpose | Public exposure | Key risk |
|---|---|---|---|---|
| Next.js frontend | Vercel project `safereturn-web-prod` | Public QR pages, owner/admin app | Public HTTPS | Wrong API URL, exposed env, SSR phone leak |
| FastAPI API | Railway service `safereturn-api-prod` | Auth, pair/owner/admin business logic | HTTPS only | Auth bypass, DB outages |
| Outbox worker | Railway service `safereturn-worker-prod` | Resend retries and lease handling | **No public ingress** | Silent notification backlog |
| PostgreSQL | Supabase project `safereturn-prod` | Business DB + Auth integration | Restricted TLS connections | RLS/grants, migrations, backups |
| Storage | Supabase private bucket | Payment proofs | Signed, authorized URLs only | Proof exposure |
| Transactional email | Resend | Finder-submission notifications | Outbound only | Sender domain / deliverability |
| Bot mitigation | Cloudflare Turnstile | ICE reveal / abuse defense | Public widget, private verification | Emergency availability |
| DNS | Domain registrar/DNS provider | App/QR/API and mail records | Public DNS | QR print permanence, spoofing |

Use provider-supported regions close to target users **after** checking legal/privacy processing, latency, availability, backup capabilities and cost. Do not assume Lahore/Pakistan regions exist for any vendor. Document actual selected regions in the deployment register.

### 1.2 Canonical host policy

| Purpose | Example placeholder | Requirement |
|---|---|---|
| App and public QR | `https://app.example.com` | Stable HTTPS host under controlled domain |
| API | `https://api.example.com` | Stable HTTPS, CORS allowlist |
| Sender | `notify@example.com` | Resend-verified domain/sender |
| Staging app | `https://staging.example.com` | Isolated from production |
| Staging API | `https://api-staging.example.com` | Isolated from production |

**These domains are placeholders, not links to live SafeReturn services.** Print production labels only after the actual QR host, routing, certificate, redirect policy and domain renewal ownership are verified. QR public URL must remain valid for years; avoid preview deployment URLs, shorteners or ephemeral Railway/Vercel hostnames on stickers.

---

## 2. Environment separation and release promotion

| Property | Local | Staging | Production |
|---|---|---|---|
| Data | Synthetic only | Synthetic/test accounts and pairs | Real customer and operations data |
| Supabase | Local stack or isolated dev project | Separate staging project | Separate production project |
| Vercel | `next dev` | Preview or dedicated staging project | Production project |
| Railway | Local Uvicorn + worker | Separate API/worker services | Separate API/worker services |
| Resend | Fake transport or controlled sandbox | Verified sender to allowlisted test inboxes | Verified sender to approved recipients |
| Turnstile | Documented test keys | Test or staging-specific keys | Production site/secret keys |
| Payments | Simulated | Fake receipts only | Human verified bank/Raast |
| QR tags | Fake tokens, never shipped | Synthetic test prints | Approved print batches only |
| Admin | Test role accounts | Test MFA | Named staff + MFA |
| Backup | Optional disposable snapshots | Restore rehearsal | Scheduled backup + restore proof |

### 2.1 Promotion rules

1. Code moves **local → CI → staging → production**; data does **not** move backward from production into staging.
2. Staging uses separate secrets, domains, Supabase Auth users, buckets and database.
3. Never copy production finder messages, ICE medical data, payment proofs or location into a test fixture.
4. Preview deployments must not receive production service-role credentials or production database access.
5. Production release requires a signed go/no-go record and a verified migration/rollback plan.
6. Treat any staging link that exposes real ICE phone data as a security incident, not a convenience.

### 2.2 Environment inventory template

```text
Environment: [local | staging | production]
Git repository / commit:
Vercel project / deployment ID:
Railway project / API service / worker service:
Supabase project reference / region / plan:
Resend domain / sender:
Turnstile widget hostname(s):
App domain / API domain:
DB migration revision (alembic current):
Release operator / reviewer:
Last backup / last successful restore test:
Alert routing owner:
Status / exceptions:
```

---

## 3. Prerequisites and account ownership

**Founder/owner checklist**

- [ ] Own a domain and registrar account; enable MFA, registrar lock if supported, renewal alerts and backup recovery codes.
- [ ] Set up Git repository with branch protection and required review.
- [ ] Establish separate Supabase staging/production projects with budget controls and recovery access.
- [ ] Establish Vercel staging/production isolation and deployment approvals.
- [ ] Establish Railway staging/production isolation and separate API/worker services.
- [ ] Verify Resend sender domain; record sending restrictions, rate limits and sender identity.
- [ ] Register Turnstile widgets for exact allowed staging/production hostnames.
- [ ] Approve bank transfer instructions, payment review roles, shipping/fulfillment and refund exceptions.
- [ ] Approve ICE reveal fallback, privacy notice, WhatsApp consent, location retention, child/guardian policy and Urdu copy.
- [ ] Identify incident commander, release operator, privacy contact and finance backup.
- [ ] Confirm selected plans provide required backups, outbound networking, background workers, custom domains and runtime limits.

**Never use one person's private email account as the only recovery channel** for registrar, database, cloud and sender provider. Use organization-controlled ownership and at least one authorized backup where provider policy permits.

---

## 4. Proposed monorepo layout and process contracts

```text
safereturn/
├── AGENTS.md
├── docs/
│   ├── 01-prd.md
│   ├── 02-technical-design.md
│   ├── 03-database-design.md
│   ├── 04-api-contract.md
│   ├── 05-agent-instructions.md
│   ├── 06-implementation-plan.md
│   ├── 07-security-privacy.md
│   ├── 08-testing-plan.md
│   └── 09-deployment-operations.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── domain/
│   │   ├── services/
│   │   ├── infrastructure/
│   │   └── worker/
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── tests/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── messages/
│   └── package.json
└── .github/workflows/
```

Paths are **proposed**. Do not force a refactor solely to match this tree. Exact import paths, package manager and worker module must be checked against implemented code.

### 4.1 Process start contracts

| Process | Expected command pattern | Important note |
|---|---|---|
| Local API | `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` | Run from `backend/`; dev only |
| Railway API | `python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}` | `${PORT}` assigned by host; verify Railway expansion semantics |
| Local/hosted worker | `python -m app.worker.main` | **Illustrative** entrypoint; implement/verify first |
| Local Next.js | `npm run dev` | Run from `frontend/`; match actual package manager |
| Frontend production | Vercel framework build | Do not run local dev server in production |
| Migration | `python -m alembic upgrade head` | One reviewed, explicit migration job only |

**Shell portability:** Railway process command parsing differs from local Bash/CMD. Prefer an entrypoint script that reads `PORT` from environment and uses Python `os.environ`, or a Railway-supported command form validated in staging. Do not assume literal `${PORT}` expands in every deployment configuration.

---

## 5. Local developer setup — Windows-friendly and cross-platform

### 5.1 Prerequisites

- Supported Python version selected by `pyproject.toml` and dependency compatibility; do not assume newest Python is supported by all packages.
- Supported Node.js LTS matching `package.json` `engines` and lockfile.
- Git; a PostgreSQL instance compatible with Supabase Postgres (Docker/local Supabase CLI optional).
- VS Code or equivalent; Python venv and pinned package manager.
- Staging/test-only Supabase and provider accounts if local emulation is insufficient.

### 5.2 Clone and initialize

```bash
git clone <approved-repository-url> safereturn
cd safereturn
git status --short

# Backend (POSIX)
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'  # only if pyproject defines this extra

# Frontend
cd ../frontend
npm ci   # use pnpm/yarn instead only if that is the repo lockfile
```

Windows PowerShell equivalents:

```powershell
cd safereturnackend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
cd ..rontend
npm ci
```

If PowerShell activation is restricted, use `.venv\Scripts\python.exe` directly rather than weakening machine-wide security settings.

### 5.3 Create local configuration

- Copy committed `.env.example` to untracked local files; never commit `.env`.
- Set **local or staging** database and provider credentials only.
- Ensure frontend public variables contain only public site keys/URLs.
- Use a fake Resend transport for unit tests; if testing actual sending, allowlist controlled test inboxes.
- Configure local browser CORS origin exactly, e.g. `http://localhost:3000`.

```bash
# From backend/ (disposable development database only)
python -m alembic current
python -m alembic upgrade head
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# In a second terminal from frontend/
npm run dev
npm run lint
npm run typecheck   # only if package.json defines this script
npm run test        # only if package.json defines this script
```

### 5.4 Local smoke tests

1. API process starts with no unhandled exception and a **non-sensitive** liveness endpoint responds. Use the approved API health route or an explicitly defined ops-only route; do not guess the URL.
2. Readiness check confirms DB connectivity and expected migration head without returning credentials.
3. Frontend loads English and Urdu public test page.
4. Synthetic pair has exactly two current tags and one credential; activation is atomic.
5. ICE phone is absent from initial page source and network payload.
6. Finder submission persists with a pending outbox event; fake worker marks test event delivered.
7. Location denial still allows submission; WhatsApp off by default.
8. Authenticated owner sees only their synthetic records; admin endpoint rejects customer.
9. No real emails, bank actions or public print exports occur.

**Troubleshooting:** If browser says “backend not connected,” distinguish API process crash, wrong public API base URL, CORS mismatch, HTTPS mixed content, 401 auth failure, DNS and DB readiness. Check browser Network tab + sanitized Railway/Vercel logs; do not paste secrets into troubleshooting chats.

---

## 6. Configuration and secrets matrix

> Names below are a **proposed naming convention**; align them with actual typed configuration and Document 3. Do not copy an example `.env` into production without validation.

| Setting | Frontend browser? | API? | Worker? | Required control |
|---|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | No | No | HTTPS production API, no trailing-path mismatch |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | No | No | Public project URL only |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` / publishable key | Yes | No | No | Public key only, never service role; match SDK generation |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | Yes | No | No | Public site key; hostname restrictions |
| `NEXT_PUBLIC_APP_URL` | Yes | No | No | Verified canonical app URL |
| `DATABASE_URL` | **No** | Yes | Yes | TLS, scoped credentials, pooled/direct variant as required |
| `SUPABASE_URL` | No | Yes if needed | If needed | Backend project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **No** | Only if required | Only if required | Avoid if scoped DB role can suffice |
| `SUPABASE_JWT_ISSUER` / `AUDIENCE` / `JWKS_URL` | No | Yes | If needed | Must match actual Auth signing configuration |
| `FRONTEND_ORIGINS` | No | Yes | No | Exact allowed origins, not `*` with credentials |
| `TURNSTILE_SECRET_KEY` | **No** | Yes | No | Server-side verification only |
| `RESEND_API_KEY` | **No** | No unless justified | Yes | Verified sender, worker-only |
| `RESEND_FROM_EMAIL` | No | No | Yes | Domain-verified sender |
| `DATA_ENCRYPTION_KEY_*` | **No** | Yes | Only if needed | Versioned AEAD keys, secret manager |
| `ACTIVATION_PEPPER_*` | **No** | Yes | No | Versioned secret separate from DB |
| `PUBLIC_QR_BASE_URL` | No | Yes | If generating notices | Permanent controlled HTTPS host |
| `OUTBOX_POLL_SECONDS` | No | No | Yes | Tunable, bounded worker polling |
| `OUTBOX_MAX_ATTEMPTS` | No | No | Yes | Dead-letter policy |
| `LOG_LEVEL` | No | Yes | Yes | Never DEBUG with sensitive payloads in production |
| `SENTRY_DSN` / monitoring config | Maybe public DSN if used | Optional | Optional | PII scrubbing; provider selection not assumed |

**Avoid secret echoing:** never run `printenv`, `env`, `railway variables`, `vercel env pull`, or `cat .env` in shared logs without redaction and approval. Never commit downloaded production env files.

### 6.1 Environment validation at startup

- Use typed configuration validation (Pydantic settings or equivalent).
- Fail fast for missing required settings; report **setting name only**, never value.
- Reject `http://` production API/QR base URLs.
- Reject staging hostnames or test Turnstile keys in production.
- Validate `FRONTEND_ORIGINS` against exact production hosts.
- Validate Resend sender and public QR base domain against approved deployment register.
- Worker fails fast if sender/API key missing; API must still persist finder messages if worker down.
- Forbid service-role and encryption keys in any `NEXT_PUBLIC_` setting.

### 6.2 Secret rotation

1. Open change ticket and identify impacted components.
2. Provision new key/version with least privilege.
3. Deploy dual-read or overlap where supported (encryption keys and JWT verification need special handling).
4. Switch writers/clients; test staging and controlled production.
5. Revoke old secret after verifying no dependents remain.
6. For compromised secret, revoke immediately and invoke incident response.
7. Record rotation evidence without copying key material.

---

## 7. Supabase setup — PostgreSQL, Auth, Storage

### 7.1 Create isolated projects

1. Create separate **staging** and **production** projects under controlled organization.
2. Record project reference, region, plan, database version, backup/PITR capability and Auth configuration.
3. Enable MFA for console administrators and restrict project membership.
4. Configure Auth site URL and approved redirect URLs per environment; no wildcard production redirects.
5. Select supported JWT signing scheme and implement backend JWKS/signature/issuer/audience validation accordingly.
6. Document email verification requirements and account recovery flow.
7. Restrict network access where supported; require TLS for database connections.

### 7.2 Choose DB connection correctly

- Supabase offers connection methods that may differ in IPv4 support, transaction/session pooling, port, and prepared-statement behavior. Use the **actual connection string supplied for the selected environment**.
- Use a **migration-compatible direct/session connection** for Alembic as required; transaction poolers may not support all DDL/session behavior.
- API/worker may use provider-recommended pooling after testing SQLAlchemy behavior.
- Never place a literal password with special characters into an unescaped URI; use the provider string or correctly percent-encode credentials.
- Keep separate credentials and least-privilege roles where feasible; do not assume `postgres`/service-role is appropriate for all runtime processes.
- Set bounded connection pools based on provider limits and service replica count.

### 7.3 Initialize database through migrations

```bash
# Staging only, with reviewed credentials supplied via secret manager
cd backend
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
python -m alembic current
```

- Apply Document 2 migration sequence; inspect constraints for exactly-two current tags, partial unique current tag indexes, allocation uniqueness, outbox and consent.
- Verify `alembic current` equals the reviewed release revision.
- Check row-level security and grants using **actual runtime roles**.
- Never `create_all()` as a substitute for production migrations.
- Do not seed synthetic users or tags into production.

### 7.4 Auth and RLS verification

- Confirm anonymous browser cannot query private business tables directly.
- Confirm customer token cannot access another customer's pair, finder inbox, location or payment proof.
- Confirm service-role credentials are never exposed to frontend.
- Confirm staff roles cannot be self-assigned from browser requests.
- Check actual JWT issuer, audience and signing keys; a JWT that decodes is not necessarily trusted.

### 7.5 Storage configuration

1. Create **private** payment-proof bucket; public bucket setting must be disabled.
2. Use generated opaque object keys scoped to authorized order, not user filenames.
3. Validate MIME/signature/size before upload and on review.
4. Access through backend-authorized short-lived signed URLs only.
5. Define retention/deletion and incident response for proofs.
6. Test direct object enumeration and cross-order signed URL access.

### 7.6 Backups and PITR

- Verify what the purchased Supabase plan **actually** backs up (database, storage objects, Auth, configuration, PITR window).
- Back up non-DB configuration separately as permitted: DNS records, provider config, migrations, print manifests **without raw activation secrets**.
- Encrypt and restrict backup access; keep data-encryption key recovery separate.
- Schedule restore rehearsals in isolated staging environment.
- Record achieved RPO/RTO rather than asserting untested numbers.

---

## 8. Railway setup — API and separate worker

### 8.1 Staging first

1. Create staging Railway project/environment with source repository connected.
2. Configure API service root directory `backend/` (or matching monorepo configuration).
3. Set reproducible Python build from pinned dependencies and a supported runtime.
4. Configure start command pointing to implemented ASGI app; bind `0.0.0.0` and platform-assigned port.
5. Set API environment secrets; restrict public domain to API service only.
6. Configure a health check endpoint that is inexpensive and safe.
7. Set bounded instance count and connection pool; check Railway limits/costs.
8. Create **separate worker service** using same commit/build or a dedicated Docker target, with worker entrypoint and **no public HTTP domain**.
9. Configure worker-only `RESEND_API_KEY`, sender and retry/lease settings.
10. Verify worker process remains running under Railway's process model and is restarted on crash.

### 8.2 API liveness versus readiness

| Probe | Checks | Must not do |
|---|---|---|
| Liveness | Process/event loop alive | Query external providers or dump secrets |
| Readiness | DB connectivity, required schema revision, critical dependencies needed to serve | Depend on Resend availability for all API traffic |
| Synthetic public scan | Known **staging** QR token resolves correct public DTO | Include private contact/activation fields |
| Worker health | Recent successful poll, lease reclaim, backlog age | Expose internal queue payloads publicly |

Exact health endpoint names are operational additions requiring alignment with Document 3; keep internal readiness restricted if not part of public API contract.

### 8.3 Railway runtime limits

- Set graceful shutdown timeout long enough to finish/return leased jobs.
- Limit worker concurrency to DB/provider capacity; avoid many replicas without shared throttling.
- Keep one migration job per release; **never run Alembic automatically from each API replica**.
- Ensure Railway restart/redeploy does not drop messages because they are persisted in DB outbox.
- Use outbound TLS and verified sender; restrict logs to redacted structured fields.

### 8.4 Deployment smoke test

1. Check deployment status and commit SHA.
2. API health responds over HTTPS; no 5xx storm.
3. Confirm actual DB revision and Auth validation.
4. Anonymous test QR resolves correct tag mode; no phone in initial payload.
5. Submit a synthetic staging finder message; DB outbox event appears.
6. Worker claims it and sends to allowlisted staging inbox.
7. Simulate Resend failure; retry/dead-letter behavior works without losing message.
8. Restart worker; expired leases recover without stuck jobs.
9. Confirm no worker public ingress and no secret logs.

---

## 9. Vercel setup — Next.js frontend

### 9.1 Project setup

1. Connect Git repository; set Root Directory `frontend/` and framework Next.js.
2. Select Node version supported by repository; install from lockfile.
3. Configure environment-specific public keys and API base URL.
4. Set staging/production domain mapping and redirects.
5. Configure Supabase Auth redirect URLs to the exact deployed hosts.
6. Use HTTPS only for production; verify no mixed-content requests.
7. Configure security headers/CSP with Turnstile/Supabase allowances after browser testing.
8. Ensure preview deployments do not connect to production Supabase or Railway API.
9. Confirm SSR and client components never serialize full ICE phone or private profile data.

### 9.2 Public env and client bundle inspection

**Safe in browser if approved:** public API base URL, Supabase publishable/anon key, Turnstile site key, locale defaults. **Never safe:** service-role key, DB password, Turnstile secret, Resend key, encryption key, activation pepper.

Build checks:

```bash
cd frontend
npm ci
npm run lint
npm run build
# Then inspect generated bundles / deployment config for known canary secrets
# without printing real secret values.
```

Use synthetic canary values in CI secret-leak tests; avoid grepping real production secrets into shared logs.

### 9.3 Next.js public page caching

- Public QR page may contain owner-controlled published data that changes/revokes. Use a caching policy consistent with rapid revocation.
- **ICE reveal and owner/private API responses must use `Cache-Control: no-store`.**
- No full phone in SSR, RSC, hydration, metadata, preload state, static export, search indexing or analytics.
- Revoke old QR token on replacement and verify old cached page does not show stale private content.
- Use `Referrer-Policy: no-referrer` on token-bearing QR routes to avoid token leakage to third parties.

### 9.4 Frontend verification

- Test English and Urdu (RTL) on real mobile viewport.
- Confirm canonical QR links route to correct public mode, not a login wall.
- Verify no location permission request on page load.
- Confirm WhatsApp link absent until opt-in.
- Confirm API requests go to production API domain (not `localhost` or preview API).
- Confirm owner/admin navigation authorization is server-enforced; frontend route guards alone are insufficient.

---

## 10. Resend setup and durable outbox operations

### 10.1 Domain verification

1. Add sender domain in Resend dashboard.
2. Copy the **current** DNS records supplied by Resend (SPF/DKIM and any required verification/return-path records); do not assume fixed record values.
3. Add records at DNS provider and verify without deleting existing mail configuration.
4. Confirm sender domain is marked verified; check DMARC policy and alignment for your actual sending setup.
5. Create API key with minimum available permissions and store **worker-only**.
6. Use `from` address under verified SafeReturn-controlled domain.
7. In staging, send only to approved test inboxes; production sends only after sign-off.
8. Confirm current account sending restrictions/quotas and any sandbox-only recipient limitations.

**Important:** Resend's `onboarding@resend.dev`-style testing sender is not a substitute for verified production sending to arbitrary customers. A recipient does **not** need a Resend account to receive email from an appropriately verified sender.

### 10.2 Outbox worker state machine

```text
PENDING --claim lease--> PROCESSING --provider accepted--> SENT
   ^                          |
   |                          +--transient failure--> RETRY_WAIT
   |                          +--permanent/max retry--> DEAD_LETTER
   +----------------------lease expired / retry due---------+
```

Actual enum names must match Document 2; diagram shows **semantics**, not a mandatory schema rename.

Worker loop:

1. Claim a bounded batch with transaction-safe lease (`FOR UPDATE SKIP LOCKED` or approved equivalent).
2. Load notification payload under minimum DB privilege.
3. Send through Resend with stable event/provider idempotency when supported.
4. Persist provider message ID and sanitized result; mark sent.
5. On transient failure, calculate capped exponential backoff with jitter and attempt counter.
6. On permanent/max failure, dead-letter with sanitized error code and alert.
7. On worker crash, expired leases are reclaimed safely.
8. Never drop or mark a message sent solely because the HTTP request timed out.

**Delivery semantics:** at least once. If provider accepts email but worker crashes before saving acknowledgment, duplicate email may occur. Use stable event IDs and idempotency features where available, but do not claim exactly-once delivery.

### 10.3 Outbox monitoring and recovery

| Metric | Meaning | Suggested response |
|---|---|---|
| Oldest pending age | Delay since finder message | Alert when above approved threshold |
| Pending/retry/dead-letter count | Queue health | Investigate sustained growth |
| Lease-expired count | Worker crashes or slow jobs | Check worker capacity/restarts |
| Provider 4xx | Invalid sender/recipient/config | Fix permanent error, avoid blind retry |
| Provider 429/5xx | Quota/rate/temporary outage | Backoff, capacity planning |
| Duplicate provider IDs | Idempotency anomaly | Review retry logic |

**Manual replay:** authorized operator selects a dead-letter event ID, verifies original recipient and reason, records ticket, requeues idempotently, monitors delivery. Never directly edit customer email addresses or copy message text into support chat. Do not delete outbox records to hide a failure.

### 10.4 Email content and privacy

- Prefer notification containing a link to authenticated owner inbox rather than full finder text or precise coordinates.
- If product requires message excerpt or Maps link in email, obtain explicit privacy review and consent wording first.
- Never include activation credential, full ICE phone, medical note, or bank proof.
- WhatsApp-only chats never generate SafeReturn outbox records.

---

## 11. Cloudflare Turnstile deployment and emergency fallback

1. Create separate staging and production widgets/site keys with allowed hostnames.
2. Store public site key only in frontend and secret only in FastAPI.
3. Backend verifies challenge response with Cloudflare server-to-server; enforce hostname/action where supported.
4. Reject invalid/expired/replayed tokens according to provider behavior.
5. Use independent rate limits; Turnstile is not authorization.
6. Test accessibility, Urdu/English context, slow network and provider outage.
7. Monitor challenge failure, reveal success and time-to-contact without storing phone.

### 11.1 Unresolved founder decision

PRD v1.1 calls for protected ICE phone reveal. Technical Design recommends a **risk-adaptive, tightly rate-limited emergency fallback** during Turnstile outages. This is **not approved by this runbook**. Do not deploy an unreviewed fail-open or fail-closed behavior.

Proposed staged drill:
- Normal: challenge verification per approved risk policy.
- Elevated abuse: stricter challenge and limits.
- Provider outage: approved temporary degraded mode with conservative quotas, alert, expiry and incident record.
- Sustained scraping: targeted blocks without removing initial public emergency instructions.

Release is blocked until policy is signed, implemented and tested against Document 7's ICE cases.

---

## 12. DNS, TLS, sender authentication and domain continuity

### 12.1 DNS change workflow

1. Record current DNS zone snapshot and TTLs.
2. Determine exact Vercel/Railway verification records from current provider UI.
3. Configure app and API custom domains; validate HTTPS certificates.
4. Add Resend verification/SPF/DKIM records as supplied; review existing SPF to avoid multiple conflicting SPF TXT records.
5. Configure DMARC per domain mail policy and confirm alignment.
6. Validate resolution from multiple networks and HTTPS requests.
7. Check redirects: HTTP → HTTPS, apex ↔ subdomain according to canonical policy.
8. Test printed QR URLs before ordering physical stock.
9. Record domain renewal date, DNS owner, registrar MFA and incident recovery contacts.

### 12.2 Suggested checks

```bash
# Substitute your approved domain. Output contains only public DNS records.
nslookup app.example.com
nslookup api.example.com
# HTTPS and redirect/header checks; use a synthetic staging QR token.
curl -I https://app.example.com/
curl -I https://api.example.com/<approved-health-path>
```

`curl -I` uses HEAD; an endpoint may legitimately not support HEAD. Use a GET smoke test if the API contract specifies GET only.

### 12.3 QR domain migration policy

A domain printed on physical stickers is a long-lived product dependency. Do not retire it without maintaining safe HTTPS redirects to the new host and confirming old token resolution. Maintain registrar renewal, DNS backups and certificate monitoring. A redirect must not leak activation secrets, downgrade to HTTP, or change lost/ICE tag role.

---

## 13. CI/CD, branch controls and artifact provenance

### 13.1 Required checks by change type

| Change | CI gates |
|---|---|
| Python backend | Ruff/format, type checks, pytest, dependency/secret scan |
| DB/Alembic | Disposable Postgres upgrade, revision chain, constraints, auth/RLS tests |
| API contract | OpenAPI 3.1 validation, generated schema drift, negative auth cases |
| Next.js frontend | ESLint, TypeScript, build, translation parity, Playwright smoke |
| ICE/finder/WhatsApp | Privacy leak tests, consent, rate limits, geolocation denial |
| Payment/admin | Finance role/IDOR, proof privacy, manual approval and audit |
| QR generation | Token entropy, ECC/size, print manifest consistency |
| Deployment config | Secret exposure scan, environment isolation, health/rollback plan |

### 13.2 Proposed GitHub Actions pipeline

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test_only
          POSTGRES_DB: safereturn_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U test -d safereturn_test"
          --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'  # example; align with pyproject and support matrix
      - run: python -m pip install -e '.[dev]'
        working-directory: backend
      - run: python -m alembic upgrade head
        working-directory: backend
        env:
          DATABASE_URL: postgresql+psycopg://test:test_only@localhost:5432/safereturn_test
      - run: python -m pytest -q
        working-directory: backend
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'  # example; align with lockfile and Next.js support
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

**Illustrative, not copy-and-run:** lock action versions to reviewed commit SHAs; adjust Python/Postgres/Node versions and dependency extras to repo. Supabase-specific schemas/extensions may require a Supabase-compatible test DB, not plain Postgres. Add actual security scans, API validation, type checks and Playwright in real CI. Do not give PR jobs production secrets.

### 13.3 Promotion gates

- Pull request requires code owner review and passing CI.
- Main merge triggers staging deploy only, or controlled staging workflow.
- Production deploy requires named approval and immutable commit/release ID.
- Database migrations are an independent reviewed job, not hidden in API startup.
- Artifact digest/commit must match across API, worker and frontend for release.
- Keep prior deploy IDs and config snapshot for rollback.

---

## 14. Database migration release procedure

### 14.1 Before applying

1. Identify current production Alembic revision and intended target.
2. Review SQL/DDL, indexes, constraints, locks, data migration, estimated runtime and rollback.
3. Confirm current backup and recent successful restore test.
4. Check long-running transactions and provider maintenance notices.
5. Verify application compatibility with both old/new schema for rolling deploy.
6. Schedule release window and responsible operator.
7. Run migration on staging clone/synthetic scale and record timing.
8. Freeze conflicting writes for high-risk migrations if required by approved plan.

### 14.2 Expand → migrate → contract

**Preferred pattern:**

1. **Expand:** add nullable columns/new tables/indexes in backward-compatible way.
2. **Deploy compatible API/worker:** reads both versions, writes new shape as appropriate.
3. **Backfill:** idempotent, batched, monitored, with validation counts and pause/restart support.
4. **Switch:** enable new code path after data validation.
5. **Contract:** remove obsolete columns only in a later approved release after rollback window.

Avoid destructive `DROP`, non-null additions without backfill, table rewrites and long blocking locks in one blind step. For `CREATE INDEX CONCURRENTLY`, use an Alembic autocommit-compatible block and validate provider support; PostgreSQL forbids it inside a normal transaction. Verify partial unique indexes and deferred pair guards before enabling activation.

### 14.3 Execution checklist

```bash
# Example; credentials injected securely, not echoed.
cd backend
python -m alembic heads
python -m alembic current
python -m alembic upgrade <reviewed_target_revision>
python -m alembic current
```

- Run exactly once from a controlled job.
- On failure, **do not** automatically retry unknown DDL or run `downgrade -1` in production.
- Determine whether migration transaction committed, whether DDL was nontransactional, and whether backfill is partial.
- Use a reviewed forward-fix or restore procedure based on evidence.

### 14.4 Migration verification queries (read-only, illustrative)

```sql
SELECT version_num FROM alembic_version;
-- Current tags: one of each type for every activatable pair.
SELECT pair_id, tag_type, COUNT(*) AS n
FROM qr_codes
WHERE is_current = true
GROUP BY pair_id, tag_type
HAVING COUNT(*) <> 1;
-- This query detects duplicates; a separate query is needed to detect missing tag roles.
SELECT p.id
FROM tag_pairs p
LEFT JOIN qr_codes q ON q.pair_id = p.id AND q.is_current = true
WHERE p.activation_status = 'active' -- replace with actual Document 2 status column/value
GROUP BY p.id
HAVING COUNT(*) <> 2 OR COUNT(*) FILTER (WHERE q.tag_type = 'lost') <> 1
   OR COUNT(*) FILTER (WHERE q.tag_type = 'ice') <> 1;
```

**Important:** This SQL is a template, not a verified match to Document 2's exact status column or enum. Inspect the checked-in models and migrations first. Never use unverified SQL against production. Also check order allocation uniqueness, outbox pending counts and orphaned sensitive child rows.

---

## 15. Release sequencing and zero-surprise production deployment

### 15.1 Standard sequence

1. **Change freeze:** lock scope, confirm approved PR and commit.
2. **Preflight:** check provider status, backup, migrations, security gates, physical print/domain readiness.
3. **Staging:** deploy same commit; run all required smoke/E2E tests and synthetic email.
4. **Approval:** founder/release/security sign-off; record known risks and rollback owner.
5. **Database expand migration:** apply reviewed compatible migration if required.
6. **API:** deploy FastAPI; verify readiness, JWT, public QR and no ICE phone leak.
7. **Worker:** deploy compatible outbox worker; verify claim/retry/lease health.
8. **Frontend:** deploy Vercel release with correct production API base and public keys.
9. **Controlled smoke:** use **designated test account/pair**, not a customer's live tag.
10. **Observe:** watch 5xx, latency, outbox age, ICE reveal, activation errors and auth failures.
11. **Go/no-go:** keep release or execute rollback/containment based on gates.
12. **Record:** deployment IDs, migrations, tests, operator, approval and incidents.

If worker and API schema compatibility requires a different order, follow an approved dependency-specific plan; do not blindly use this default.

### 15.2 Production preflight checklist

- [ ] Approved founder decisions, privacy notices, Urdu/English copy, ICE fallback.
- [ ] Domain, TLS, DNS, sender verification and renewals valid.
- [ ] Current backup and tested restore; RPO/RTO approved.
- [ ] Migration reviewed and tested in staging; compatibility known.
- [ ] CI green including security, OpenAPI, DB and E2E gates.
- [ ] No unresolved Critical/High bugs from Document 7.
- [ ] Production secrets set server-side; no preview env cross-contamination.
- [ ] Admin MFA, RLS and storage privacy verified.
- [ ] Outbox worker alive; sender domain verified.
- [ ] No ICE phone in initial HTML/JSON; contact reveal works per policy.
- [ ] Location denial and WhatsApp off-by-default work.
- [ ] Real bank approval remains manual; finance operator ready.
- [ ] Physical QR pilot samples meet minimum 30/35 mm and quiet zone/ECC requirements.
- [ ] Incident on-call and rollback operator available.

### 15.3 Production smoke sequence

| # | Action (synthetic test pair) | Expected |
|---|---|---|
| 1 | Open canonical HTTPS app URL | Valid certificate, expected deployment |
| 2 | Open synthetic lost QR | Correct bilingual public lost mode |
| 3 | Open synthetic ICE QR | Correct public ICE mode; **no phone initially** |
| 4 | Protected ICE reveal | Approved challenge/fallback, no-store response |
| 5 | Finder submits without location | Message saved and owner inbox accessible |
| 6 | Finder submits with explicit location | Encrypted coordinates; owner-only access |
| 7 | Worker processes event | Resend accepted to controlled test inbox |
| 8 | WhatsApp off/on/revoke | Consent respected; no false inbox record |
| 9 | Test owner pair management | No cross-owner access |
| 10 | Finance/admin role checks | Customer cannot approve payment |
| 11 | Review logs/metrics | No raw secrets or sensitive payloads |
| 12 | Check DB/worker state | No stuck leases, correct revision |

**Do not activate real inventory just to perform a smoke test.** Maintain clearly marked internal test pairs and exclude them from sale/shipment.

---

## 16. Monitoring, dashboards and alerts

### 16.1 Golden signals and product-critical metrics

| Component | Metric | Alert principle |
|---|---|---|
| Frontend | 5xx/failed navigation, page load, QR route errors | Elevated failures against baseline |
| API | Request rate, 4xx/5xx, latency percentiles, saturation | Persistent 5xx or slow public scan |
| Database | Connection failures, active connections, slow queries, storage | Connection exhaustion / capacity risk |
| Auth | JWT validation failures, suspicious sign-in/admin actions | Sudden increase / privileged anomaly |
| Outbox | Pending count, oldest age, retry, dead-letter, worker heartbeat | No processing or aging messages |
| Resend | Provider 4xx/429/5xx, accepted vs delivered if available | Sustained failure; sender-domain issue |
| ICE reveal | Success/failure, challenge failure, provider outage | Emergency access degradation or scraping |
| Finder | Accepted submissions vs DB errors | Lost-message risk |
| Activation | Success, conflict, repeated invalid secret attempts | Fraud or race anomaly |
| Payments | Unreviewed queue age, duplicate references, abnormal approvals | Finance fraud or backlog |
| QR physical | Scan success, batch rejection, replacement rate | Manufacturing problem |
| Security | IDOR attempts, admin elevation, secret scans, bulk reads | Investigate immediately |

### 16.2 Alert ownership and severity

- **Critical:** public ICE phone leak, cross-owner access, activation split state, leaked service role, unauthorized payment approval, QR host hijack. Page incident commander immediately and disable affected flow.
- **High:** persistent QR 5xx, outbox message loss, worker backlog beyond approved limit, inability to reveal ICE contact under approved policy, unverified print batch shipped. Page on-call and pause pilot expansion.
- **Medium:** elevated retry, degraded latency, temporary provider throttling. Triage during support hours with documented owner.
- **Low:** cosmetic or noncritical metrics drift. Ticket and monitor.

Thresholds are **to be calibrated** from staging/pilot baselines and founder-approved SLOs. Do not invent guaranteed 99.9% uptime or delivery time without operational evidence.

### 16.3 Logging and tracing rules

Allowed: request ID, sanitized actor ID, route **template**, response status, latency, deployment version, error code, event ID, worker attempt count.  
Forbidden: full token-bearing QR URL, activation credential, JWT, cookie, ICE/WhatsApp phone, medical note, finder message text, precise coordinates, proof bytes, secret values.

- Configure error tracking to scrub PII **before sending**.
- Disable request-body logging for sensitive routes.
- Redact Authorization, Cookie, Set-Cookie and provider headers.
- Keep structured audit trail for activation, transfer, payment and admin actions with minimal fields.
- Protect log access and retention; test redaction with synthetic canaries.

### 16.4 Daily / weekly / monthly operations

| Cadence | Task | Evidence |
|---|---|---|
| Daily during pilot | QR/API health, oldest outbox, dead letters, pending payment reviews | Dashboard snapshot and exceptions |
| Daily | Confirm domain/TLS and provider status if incident suspected | Incident/ops note |
| Weekly | Review suspicious ICE reveals, activation attempts, admin changes | Sanitized security report |
| Weekly | Test one synthetic finder-to-email workflow | Test event ID and status |
| Weekly | Reconcile inventory, pair allocations and print rejects | Batch ledger |
| Monthly | Review secrets/roles, costs, quotas and dependency updates | Access/budget review |
| Scheduled | Restore backup to isolated environment | Restore evidence and actual RPO/RTO |
| Before any release | CI, migration review, staging E2E, rollback readiness | Signed release record |

---

## 17. Backup, restore and disaster recovery

### 17.1 What must be recoverable

- Supabase PostgreSQL business data, Auth linkages and Alembic revision.
- Private Storage payment proofs subject to retention policy.
- Encryption key versions and secret custody (separately secured).
- Canonical DNS/domain control and provider configuration.
- Outbox pending/lease/dead-letter state.
- Printed pair manifests and shipment ledger with sensitive secrets omitted.
- Git release artifacts, migration scripts and approved config changes.

### 17.2 Restore rehearsal

1. Open rehearsal ticket; identify backup timestamp, restore environment and target RPO/RTO.
2. Provision **isolated** DB/project with no production outbound email or public DNS.
3. Restore backup using provider-supported procedure.
4. Restore required encryption key versions through authorized secure channel.
5. Verify Alembic revision and migration consistency.
6. Validate exactly-two current tags, ownership, outbox and order allocation integrity.
7. Run read-only application smoke tests with synthetic or redacted fixtures; do not expose restored customer data to staging users.
8. Disable real Resend/WhatsApp external actions; prevent accidental customer notifications.
9. Measure elapsed time, data age, failures and operator steps.
10. Destroy isolated copy per privacy/retention policy; record results.

**Never restore production backup into a publicly accessible staging project.** Backup capability and PITR vary by provider plan; verify current entitlements before claiming recovery objectives.

### 17.3 Disaster recovery decision tree

```mermaid
flowchart TD
 A[Incident detected] --> B{Is customer data integrity at risk?}
 B -->|Yes| C[Freeze affected writes and preserve evidence]
 B -->|No| D{Single provider/component failure?}
 D -->|Yes| E[Contain/restart or roll back component]
 D -->|No| F[Coordinate multi-provider incident]
 C --> G{Restore needed?}
 G -->|No| H[Forward-fix with review]
 G -->|Yes| I[Approve recovery point + privacy impact]
 I --> J[Restore isolated and validate]
 J --> K[Controlled cutover]
 E --> L[Verify critical synthetic flows]
 F --> L
 H --> L
 K --> L
 L --> M[Monitor + postmortem]
```

---

## 18. Rollback and failed-deployment handling

### 18.1 Application rollback

1. Identify first bad deployment, last known-good commit and database compatibility.
2. Pause rollout; avoid repeated automatic deploy loops.
3. If schema backward-compatible, redeploy previous Railway API/worker and Vercel frontend as needed.
4. If schema changed incompatibly, **do not** roll code back blindly; use approved forward-fix/compatibility layer or restore decision.
5. Verify public QR, ICE reveal, finder persistence, worker, Auth and payment permissions.
6. Monitor and record incident; do not discard pending outbox.

### 18.2 Migration rollback

- PostgreSQL DDL may be transactional, but `CONCURRENTLY` and external backfills can create partial states.
- Never assume Alembic `downgrade` restores deleted data.
- Prefer reviewed forward-fix for data-preserving schema mistakes.
- Restore DB only after evaluating lost writes, outbox replay, Auth consistency, privacy and printed QR continuity.
- Take an incident snapshot/backup before any destructive recovery action if feasible.

### 18.3 Worker-specific rollback

- Stop worker process, not finder API, if sending is faulty; new finder submissions continue to persist in DB.
- Preserve outbox rows and leases.
- Redeploy last known-good worker; inspect retry/deduplication before replay.
- Notify support if customer notifications are delayed.

### 18.4 Turnstile-specific degradation

- Use only founder-approved emergency fallback.
- Never silently disable all reveal controls.
- Preserve public emergency instructions even if contact reveal is degraded.
- Alert and record outage window, abusive traffic and recovery.

---

## 19. Incident response — on-call playbooks

### 19.1 General SEV workflow

1. Detect and open incident ticket with timestamp, severity, affected services and commander.
2. Preserve privacy-safe evidence; restrict incident channel membership.
3. Contain: disable feature, revoke keys/tokens, block abusive traffic, pause shipment/payment as applicable.
4. Investigate scope and actual data access, including provider logs.
5. Fix and validate in staging; obtain security review.
6. Recover carefully, replaying outbox only with idempotency.
7. Consult legal/privacy owner on notices and obligations; no guessed legal deadlines.
8. Publish internal postmortem with action items and owners.

### 19.2 Scenario-specific playbooks

| Scenario | First actions | Verification before reopening |
|---|---|---|
| **Public ICE phone leaked** | Disable affected public response; purge caches; revoke leaked credentials if any; assess exposure | DOM/RSC/JSON/network negative tests pass |
| **Activation secret/batch exposed** | Quarantine batch; suspend unactivated pairs; audit attempts; reissue per policy | New credentials concealed, manifest reconciled |
| **QR domain/cert down** | Check DNS, registrar, Vercel, TLS; restore canonical host | Existing printed QR URLs resolve over HTTPS |
| **API 5xx/DB unreachable** | Check Railway deploy, DB connections, Supabase status | Health, owner auth, public scan, finder persistence |
| **Outbox backlog/Resend down** | Verify worker heartbeat, sender domain, provider quota; preserve queue | Staging synthetic event delivered; retry count falls |
| **Turnstile outage** | Activate only approved fallback; tighten monitoring | Reveal works for legitimate test user; no bulk leak |
| **Cross-owner inbox/location** | Disable affected endpoint; audit access; notify security/privacy | IDOR and transfer tests pass |
| **Fraudulent bank approval** | Pause allocation/shipments; compare bank ledger; suspend role | Independent reconciliation, audit complete |
| **Private proof bucket exposed** | Revoke public access/signed URLs; audit reads | Direct URL enumeration fails |
| **Compromised admin account** | Revoke sessions, remove roles, rotate impacted keys | MFA and permission audit pass |
| **Wrong QR printed/shipped** | Stop batch; quarantine inventory; revoke tokens as needed | Two-tag QA and batch reconciliation pass |
| **Data corruption/migration** | Freeze writes; capture state; choose forward-fix/restore | Invariants, migration and outbox checks pass |

### 19.3 Incident record template

```text
Incident ID / SEV:
Detected at (timezone):
Commander / scribe:
Affected services / data classes:
Customer impact (confirmed vs suspected):
Containment action and timestamp:
Evidence locations (redacted):
Root cause / timeline:
Recovery validation tests:
Legal/privacy notification decision owner:
Customer communication approved by:
Follow-up tickets / deadlines:
Closed at / reviewer:
```

---

## 20. Capacity, performance and cost operations

### 20.1 Capacity baseline

- Record expected pilot kits, scan rate, peak concurrent public scans, finder submissions/day, reveal attempts/day and email volume.
- Size DB connection pools across all Railway replicas; avoid exhausting Supabase connections.
- Use a small bounded worker batch and concurrency, then tune based on measured Resend limits.
- Benchmark anonymous QR resolution, finder submission, ICE reveal and activation with **synthetic data**.
- Test degraded DB/provider behavior and load-induced rate-limit fairness.
- Avoid scaling API replicas without shared rate-limit state.

### 20.2 Budget controls

| Provider | Track | Action when nearing threshold |
|---|---|---|
| Vercel | Build/requests/bandwidth/function usage | Optimize cache/public pages without leaking private data |
| Railway | CPU/memory/service uptime/outbound usage | Profile API/worker; avoid unnecessary replicas |
| Supabase | DB size, connections, backups, Storage, Auth quotas | Archive/delete per approved policy, optimize queries |
| Resend | Monthly sends, API quotas, bounce rate | Throttle worker, improve delivery/recipient quality |
| Cloudflare | Widget/challenge limits and availability | Validate provider policy and fallback |
| Domain/DNS | Renewal and certificate validity | Automatic renewal + backup owner |
| Printing/shipping | Pair-level rejects, replacement and dispatch cost | QA, batch reconciliation |

Do not state current provider pricing or guarantee a free tier. Verify current billing terms and enable alerts before launch.

---

## 21. Operational security and privacy checklist

- [ ] Production secrets exist only in server/worker secret stores; not in Vercel public env.
- [ ] Database credentials use TLS and least privilege; RLS/grants tested.
- [ ] Staff MFA enforced; finance and fulfillment separation documented.
- [ ] QR token not logged in full URL or analytics; referrer policy applied.
- [ ] ICE full phone absent from initial HTML, hydration, metadata and API JSON.
- [ ] Reveal response `no-store`, protected and monitored.
- [ ] WhatsApp default off; owner consent and external number exposure explicit.
- [ ] Geolocation not requested automatically; coordinates encrypted and owner-scoped.
- [ ] Finder message + outbox atomic; Resend worker independently recoverable.
- [ ] Payment proof bucket private; bank verification manual and audited.
- [ ] Retention and deletion jobs tested; backups expiry accurately disclosed.
- [ ] Structured logs redacted; alerts routed to a human.
- [ ] No production PII in agent prompts, CI logs or test fixtures.
- [ ] Domain/QR print permanence, packaging concealment and physical QA complete.

---

## 22. Acceptance tests and release evidence mapping

Use Document 7's exact test identifiers and its launch go/no-go gates; this runbook defines operational evidence, not a replacement test catalog.

| Evidence ID | Procedure | Required result | Source |
|---|---|---|---|
| OPS-DEP-01 | Staging/production secret isolation | No cross-env credentials/data | Security doc; Test Plan |
| OPS-DEP-02 | Railway API health/readiness | DB and migration head correct | TDD; Test Plan |
| OPS-DEP-03 | Worker restart and lease reclaim | No lost outbox; retries resume | DB/API/Test Plan |
| OPS-DEP-04 | Resend verified sender | Controlled test email accepted | TDD; Test Plan |
| OPS-DEP-05 | ICE initial page inspection | No phone in SSR/hydration/network | Security; Test Plan |
| OPS-DEP-06 | Turnstile outage drill | Approved fallback works | Security; Test Plan |
| OPS-DEP-07 | Supabase grants/RLS | No anonymous/cross-owner private reads | DB; Test Plan |
| OPS-DEP-08 | Alembic upgrade in staging | Target revision, invariants pass | DB; Test Plan |
| OPS-DEP-09 | Backup restore rehearsal | Data, keys, schema, outbox consistent | Security; Test Plan |
| OPS-DEP-10 | Rollback rehearsal | Safe code rollback/forward-fix verified | Test Plan |
| OPS-DEP-11 | DNS/HTTPS/QR permanence | Printed URLs work on controlled domain | PRD; TDD |
| OPS-DEP-12 | Urdu/English mobile smoke | Public flows work in both languages | PRD; Test Plan |
| OPS-DEP-13 | Finder without location | Durable submission, no location data | PRD; Security |
| OPS-DEP-14 | WhatsApp opt-in/revoke | No unconsented link; no outbox for external chat | PRD; Security |
| OPS-DEP-15 | Finance verification | No approval without bank confirmation | PRD; Security |
| OPS-DEP-16 | Log redaction audit | No PII/secrets in provider logs | Security; Test Plan |
| OPS-DEP-17 | Physical pair QA | Both correct QR tags + concealed secret | PRD; Test Plan |
| OPS-DEP-18 | Incident simulation | Named commander, containment and recovery | Security; Test Plan |

**Evidence format:** test ID; environment; release SHA; UTC timestamp + local time; operator; command/steps; expected/actual result; sanitized screenshots/logs; pass/fail; defect link; reviewer approval.

---

## 23. First production launch — executable checklist

### Phase A — 7–14 days before planned pilot (indicative)

1. Approve outstanding founder ADRs, especially ICE fallback, consent/retention and admin MFA.
2. Verify production domains, DNS ownership, TLS and Resend sender.
3. Confirm provider plans support backup/restore and worker runtime.
4. Complete full staging E2E, security and physical QR QA.
5. Rehearse migration, restore, worker outage and rollback.
6. Review all production environment variables with a **names-only** checklist.
7. Approve pilot size, support staffing, refund/return and payment SOP.
8. Establish metrics baselines and alert ownership.

### Phase B — release day, before customer access

1. Record release commit, operator, change ticket and approvals.
2. Verify latest backup and status pages.
3. Apply approved backward-compatible migration once.
4. Deploy API, then compatible worker, then frontend (unless approved dependency plan differs).
5. Check each deployment commit/revision and public TLS.
6. Run OPS-DEP-01–18 relevant release checks with synthetic test data.
7. Review sanitized logs, outbox lag and security alerts.
8. Founder signs go/no-go; if failed, rollback or disable affected flow.

### Phase C — first pilot customers

1. Allocate QA-approved physical pairs only after verified payment/approved pilot entitlement.
2. Confirm packaging includes two correct labels and concealed credential.
3. Observe first activations and scans without recording secret/PII.
4. Test finder message and controlled notification with consent.
5. Monitor ICE reveal availability, Turnstile, WhatsApp consent and location opt-in.
6. Record user support issues, physical scan failures and security anomalies.
7. Pause new kit distribution if Critical/High incident occurs.

### Phase D — 24/48/72-hour reviews

- Review QR scan failures, activation conflicts, finder persistence, outbox oldest age, delivery errors and customer support.
- Review finance reconciliation and shipment QA.
- Review suspicious ICE reveal, consent changes, location requests and logs.
- Publish a short internal incident/risk report; decide continue, pause or rollback.

**Pilot thresholds:** define with founder using observed staging baseline. Do not invent numerical SLOs or claim launch readiness from this document alone.

---

## 24. Quick troubleshooting matrix

| Symptom | Likely categories | Safe first checks | Escalate if |
|---|---|---|---|
| Frontend “cannot connect to backend” | Wrong API base URL, CORS, HTTPS, Railway crash, DNS | Browser Network request URL/status; sanitized API health | Production outage or secret leak |
| 401 for all owner requests | Wrong JWT issuer/audience/JWKS, expired session, Auth redirects | Verify staging JWT config, issuer and signing scheme | Cross-user auth behavior |
| 403 only for admin | Missing staff role/MFA, role grant issue | Review audited staff-role assignments | Privilege escalation suspected |
| Public QR 404 | Wrong domain, token revoked, incorrect batch, route mismatch | Check canonical URL and synthetic known token | Printed batch affected |
| ICE phone appears in page source | SSR/API DTO leak, caching | Disable affected response, preserve evidence | **Immediate SEV-1** |
| ICE reveal fails | Turnstile secret/hostname, rate limit, provider outage | Inspect sanitized error codes and policy | Emergency contact inaccessible |
| Finder accepted but no email | Worker stopped, backlog, Resend domain/quotas | Check outbox pending/oldest age and worker heartbeat | Lost message or sustained delay |
| Finder message missing | DB transaction failure, incorrect recipient | Check transaction errors and idempotency | **Stop-ship** |
| DB connection timeout | Wrong pooler/host/SSL, pool exhaustion, outage | Supabase status, sanitized connection metrics | Persistent 5xx |
| Alembic fails | Revision mismatch, incompatible pooler, lock, privilege | Inspect current/heads, migration logs (redacted) | Partial nontransactional DDL |
| Payment screenshot “verified” automatically | Unsafe business logic | Freeze finance/fulfillment; inspect audit | **Immediate stop-ship** |
| WhatsApp link appears without consent | Cache or consent bug | Disable link and purge caches | **Privacy incident** |
| Browser requests location on load | Frontend regression | Disable auto-request and verify consent | **Privacy incident** |
| Email sender rejected | Unverified sender/domain, provider restrictions | Resend domain status, sanitized 4xx | Live notifications blocked |
| Railway deploy healthy but worker silent | Worker service not started, wrong entrypoint/env | Worker process logs/heartbeat | Outbox backlog |
| Old tag works after replacement | Cache/revocation check missing | Revoke token, verify no-store | Owner privacy risk |

---

## 25. Operations templates

### 25.1 Release record

```text
Release ID:
Change request / PR:
Git SHA:
Operator:
Approvers:
Staging build / test evidence:
DB before/after Alembic revision:
Backup timestamp and restore rehearsal:
Vercel deployment ID:
Railway API deployment ID:
Railway worker deployment ID:
Supabase project reference (no secrets):
Smoke test IDs and results:
Monitoring baseline / observation window:
Rollback/forward-fix plan:
Known risks and exceptions:
Final GO / NO-GO and time:
```

### 25.2 Daily operations log

```text
Date/time and operator:
App/API/DB status:
Outbox pending/oldest/dead-letter:
Resend delivery incidents:
ICE reveal success/error anomalies:
Activation and QR errors:
Finance queue and reconciliation:
Print/shipment rejects:
Security/privacy alerts:
Actions taken / tickets:
Next on-call handoff:
```

### 25.3 Secret inventory (metadata only)

```text
Secret name:
Environment:
Owning service:
Provider/secret-manager location:
Access roles:
Created / last rotated / next review:
Dependent components:
Compromise runbook:
NEVER RECORD THE SECRET VALUE HERE.
```

### 25.4 Restore test record

```text
Backup reference / timestamp:
Restore target (isolated):
Operator / reviewer:
Started / completed:
Achieved RPO and RTO:
Migration revision:
Pair/QR and outbox consistency checks:
Key decryption validation:
Storage objects tested:
Failures and remediation:
Cleanup/destruction confirmation:
```

---

## 26. Explicit unresolved decisions and stop conditions

| ID | Decision / missing confirmation | Impact |
|---|---|---|
| OPS-DEC-01 | Production domain, QR hostname and ownership | Blocks physical production print |
| OPS-DEC-02 | ICE Turnstile outage fallback approval | Blocks emergency reveal launch |
| OPS-DEC-03 | Actual provider regions/plans and data-processing review | Blocks production configuration |
| OPS-DEC-04 | Finder/location, medical, payment-proof retention | Blocks privacy/legal sign-off |
| OPS-DEC-05 | Admin MFA and emergency access policy | Blocks finance/admin live operations |
| OPS-DEC-06 | Supabase Auth session/JWT scheme and SDK configuration | Blocks auth security acceptance |
| OPS-DEC-07 | Encryption key custody and recovery | Blocks sensitive data production |
| OPS-DEC-08 | RPO/RTO and backup/PITR entitlements | Blocks resilience sign-off |
| OPS-DEC-09 | Bank/Raast reconciliation, refunds and exception owner | Blocks real payment acceptance |
| OPS-DEC-10 | Resend verified sender and current sending restrictions | Blocks customer notifications |
| OPS-DEC-11 | Shared rate limiting if API horizontally scaled | Blocks multi-replica scale-up |
| OPS-DEC-12 | Approved incident contacts and customer notice workflow | Blocks pilot readiness |
| OPS-DEC-13 | Actual source entrypoints, health routes, package versions | Blocks copy/paste deployment commands |
| OPS-DEC-14 | Physical QR substrate and secret concealment sign-off | Blocks shipment |

**Never represent an unresolved decision as a configured feature.** A green CI run does not imply these operational gates are satisfied.

---

## 27. Handoff to next document and sign-off

| Signatory | Approval | Date | Scope |
|---|---|---|---|
| Founder / product owner | Pending | — | Product/pilot/finance decisions |
| Technical owner | Pending | — | Architecture and deploy process |
| Security/privacy reviewer | Pending | — | ICE, consent, data protection |
| Operations/release owner | Pending | — | Monitoring, backups, incident readiness |
| Physical fulfillment owner | Pending | — | QR QA and batch custody |

**Next document, not created now:** Document 9 — **SafeReturn Physical Product & Fulfillment SOP** (pair printing, packaging, activation secret concealment, QA, inventory, payments, dispatch, returns and replacement).  
**Last document remains Document 10 — UI/UX Design Specification**, including complete screens, navigation routes, transitions, states and bilingual RTL behavior. No UI/UX document is generated here.

**End of Document 8 — Deployment & Operations Runbook.**

