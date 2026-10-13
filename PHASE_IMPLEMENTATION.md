# SafeReturn — Phase Implementation Plan & AI Handoff

**Status:** Development started. `/docs` is authoritative; supplied UI references are actually in `/mock-ui` (not `/mocUI`). Historical implementation records describe code absent from this workspace; task status below follows actual source and tests.

## 1. Mission and working rules

Build a functional SafeReturn application, incrementally, with working code as the primary output. Review `/docs` for product requirements, approved stack, schema/API constraints and acceptance criteria. Review `/mocUI` for UI behavior and visual direction. If documents conflict, note the exact conflict briefly and choose a reversible implementation or request a decision only if genuinely blocking. Do **not** substitute this provisional phase list for an existing approved specification.

- Use **one normal project checkout** by default. Do not create Git worktrees, extra branches or elaborate tracking systems unless requested.
- Do not overwrite unrelated user changes, delete existing files, or make destructive database changes.
- Prioritize implementation over reporting. For every phase: inspect only relevant files, implement a small end-to-end slice, run focused checks, fix issues, then update the handoff.
- Follow the technology stack actually specified in `/docs`. Based on existing discussion, expected components include FastAPI, PostgreSQL/Supabase, SQLAlchemy 2 + psycopg, Alembic, and a web UI; **verify against `/docs`**. Preserve approved raw SQL/no-ORM conventions if documented.
- Keep secrets in ignored local environment files; never print, log or commit credentials. Development migrations can run only with authorized access to the correct nonproduction database. Production changes, destructive actions, and credential rotations require appropriate approval.
- Do not spend cycles repeating already-known warnings or running broad audits unrelated to the feature. If a blocker affects only one feature, progress on another independent feature.
- Don't declare tests passed or features done without checking. A phase is `DONE` only when its acceptance criteria are demonstrated.

## 2. Source-of-truth paths

| Path | Purpose |
| --- | --- |
| `/docs/` | Requirements, architecture decisions, API/database rules, business logic, acceptance criteria |
| `/mock-ui/` | Actual supplied mock UI assets/screens and interaction references; prompt spelling `/mocUI/` maps here |
| `/PHASE_IMPLEMENTATION.md` | Short phase status, next action and durable handoff for another AI |
| Project code folders | Actual application source; follow approved repo layout, do not assume it |

## 3. Implementation phases

The order below is a provisional development sequence. Align each phase with tasks and release gates already defined in `/docs` before coding. Deliver usable functionality rather than documentation alone.

### Phase 0 — Repository and build foundation
**Outcome:** An app that can start locally and a clear architecture matching the docs.

- Inventory `/docs`, `/mocUI`, current source, build commands and package configuration once.
- Identify existing code; preserve it rather than rebuilding blindly.
- Set up missing project skeleton/configuration, example environment variables without secrets, minimal health endpoint, and frontend run/build setup as applicable.
- Confirm a local run/build or record exactly why execution is unavailable.

**Done when:** main application entrypoints launch (or build) and the result is verified.

### Phase 1 — Database schema and migrations
**Outcome:** Versioned schema supporting actual SafeReturn requirements.

- Derive schema from `/docs`, including users, physical products, QR identities/ownership, profiles, and other documented objects.
- **Important invariant:** A user can own multiple separately editable QR profiles. A paired Lost/ICE product has two distinct identities/profiles, activated or owned together, but independently editable. Multiple printed copies of the *same* QR share one profile. Future product types can have independent QR identities.
- Create Alembic migrations, constraints, indexes and local migration tests, following the approved database style.
- Apply non-destructive migrations only to the confirmed nonproduction database with approved access.

**Done when:** migrations and schema constraints have been tested; do not mark applied unless confirmed on the target DB.

### Phase 2 — Authentication and account foundation
**Outcome:** Register/login/session behavior and user-account APIs as described in `/docs`.

- Implement account flows, validation, authorization and relevant tests.
- Wire frontend login/register screens from `/mocUI` where applicable.

**Done when:** a user can complete the approved account flow end-to-end.

### Phase 3 — QR activation, ownership and profiles
**Outcome:** Core Lost/ICE functionality works through backend and UI.

- Implement QR lookup, activation, access permissions, paired activation, and independent editing for each QR identity.
- Support multiple products and QR identities under one account.
- Build/edit relevant screens based on `/mocUI` and connect to live APIs.
- Test public-vs-private fields and cross-user authorization.

**Done when:** a user can activate, manage and edit multiple QR identities without affecting unrelated profiles.

### Phase 4 — Public scan experiences and messaging
**Outcome:** A finder/emergency contact scanning a QR sees only the intended public experience.

- Implement Lost and ICE scan views, contact interactions, privacy rules and abuse handling specified in `/docs`.
- Build responsive UI and test phone-sized layouts and invalid/inactive QRs.

**Done when:** scan-to-action flows work end-to-end against development backend.

### Phase 5 — Remaining approved product features
**Outcome:** All other features required in `/docs` implemented in priority order.

- Inventory uncovered required screens/endpoints from the documents and `/mocUI`.
- Build features one vertical slice at a time with focused tests.
- Avoid inventing large optional features or expanding scope without approval.

**Done when:** every required capability has an implementation and verified acceptance check.

### Phase 6 — Integration, deployment preparation and release checks
**Outcome:** Deployable application matching the approved release criteria.

- Integrate frontend/backend/database and verify real critical workflows.
- Address accessibility, responsive behavior, basic observability, essential security, deployment configuration and documented acceptance gates.
- Treat unresolved approved logo/font/artwork decisions and unavailable source references as explicit release gates, not reasons to stop unrelated development.
- Do not deploy to production without authorization.

**Done when:** agreed tests pass, remaining release blockers are explicit, and deployment instructions are reproducible.

## 4. Development task division and progress

Execute tasks in order within each phase, respecting dependencies. User authorized the next task, 1.3, after completing 1.2. Tasks 1.1–1.3 are now verified against authorized development Supabase. Keep task counts and statuses current after meaningful progress. Next eligible task is 1.4; stop after the current bounded task/report.

| Phase | Practical implementation tasks in dependency order |
| --- | --- |
| 0 — Foundation | **0.1:** Runnable FastAPI configuration + API-001/002 health + tests. **0.2:** Next.js/TypeScript/Tailwind app with approved bilingual layout, local run/build. **0.3:** Typed API transport and local frontend/backend integration. |
| 1 — Database | **1.1:** SQLAlchemy 2/psycopg session lifecycle and real DB readiness. **1.2:** Alembic identity/pair/QR/credential/profile schema and exactly-two current-tag constraints. **1.3:** Catalog, immutable orders/QR uses, reservations, payment and fulfillment schema. **1.4:** Messaging, encrypted location, audit, durable outbox/jobs/intent schema and least-privilege/RLS. **1.5:** PostgreSQL migration/constraint/race verification. |
| 2 — Authentication | **2.1:** Supabase JWT validation and account/role/ownership guards. **2.2:** Signup/login/session frontend and account APIs. **2.3:** Auth integration and negative authorization tests. |
| 3 — QR management | **3.1:** Secure paired inventory generation and credential handling. **3.2:** Scan intent and atomic entitlement-bound activation/idempotency. **3.3:** Independent Lost/ICE profile APIs, versioning and consent. **3.4:** Multiple-pair dashboard/editors and activation return flow. **3.5:** Cross-owner, rollback and concurrency integration checks. |
| 4 — Public scans | **4.1:** Safe anonymous QR projections and bilingual scan pages. **4.2:** Protected ICE reveal and opt-in WhatsApp. **4.3:** Finder message + optional consented location + atomic notification outbox. **4.4:** Durable email worker/retries and phone-sized privacy/accessibility checks. |
| 5 — Remaining features | **5.1:** Admin catalog/variants/public assets + dynamic featured storefront. **5.2:** Decimal quotes, independent copy counts, immutable checkout/address + exclusive reservations. **5.3:** Private payment evidence + manual finance review and exactly-once allocation. **5.4:** Approved branded QR/vector PDF jobs and private download/print QA. **5.5:** Fulfillment/orders/copies UI + admin operations. **5.6:** Asynchronous masked Sheets mirror, retention/legal holds and recovery. **5.7:** Remaining approved account/inbox/help/settings screens and acceptance coverage. Future non-sticker products/gateway features remain disabled until approved. |
| 6 — Integration/release | **6.1:** Real end-to-end critical workflows and failure recovery. **6.2:** Responsive/RTL/accessibility and security acceptance. **6.3:** Deployment configuration, observability, backup/rollback checks. **6.4:** Physical QR/artwork/font/Urdu/provider release gates and pilot acceptance; no production deployment without authorization. |

Task states: TODO / IN PROGRESS / IMPLEMENTED / VERIFIED / BLOCKED. Phase completion requires all relevant tasks and acceptance checks; a verified bootstrap does not complete Phase 0.

### Task count and status register

**Current roadmap: 31 tasks across 7 phases. Completed/VERIFIED: 6. Remaining: 25.** IMPLEMENTED awaiting verification: 0; IN PROGRESS: 0; TODO: 25; BLOCKED: 0. Completed means VERIFIED. Remaining includes every task not VERIFIED. Counts describe task completion, not percentage of engineering effort; update them if approved task division changes. TODO does not assert all future provider prerequisites are available.

| Phase | Total | VERIFIED task IDs | IN PROGRESS | TODO task IDs |
| --- | --- | --- | --- | --- |
| 0 — Foundation | 3 | 0.1, 0.2, 0.3 | — | — |
| 1 — Database | 5 | 1.1, 1.2, 1.3 | — | 1.4, 1.5 |
| 2 — Authentication | 3 | — | — | 2.1, 2.2, 2.3 |
| 3 — QR management | 5 | — | — | 3.1, 3.2, 3.3, 3.4, 3.5 |
| 4 — Public scans | 4 | — | — | 4.1, 4.2, 4.3, 4.4 |
| 5 — Remaining features | 7 | — | — | 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7 |
| 6 — Integration/release | 4 | — | — | 6.1, 6.2, 6.3, 6.4 |

### Current task

- **0.1 — FastAPI backend foundation:** VERIFIED; five focused ASGI health/contract tests pass, Ruff lint/format pass, pip check passes, real Uvicorn HTTP liveness smoke passes. Readiness truthfully returns 503 until database integration.
- **0.2 — Next.js frontend foundation:** VERIFIED; production build, TypeScript check and 9 Playwright checks pass. English/Urdu server rendering and persistent language switch, responsive marketing layout, native mobile navigation/FAQ, keyboard skip link and truthful empty catalog. Screenshots reviewed at desktop English and mobile Urdu.
- **0.3 — Typed API/local integration:** VERIFIED; server-only origin/client, runtime response validation, no-store requests, timeout and safe errors; web GET /api/health/live reaches API-001. Production build/typecheck, 16 checks against real servers and backend-outage check pass. Public web readiness remains absent; no CORS or backend changes needed.
- **1.1 — Database sessions/readiness:** VERIFIED against authorized development Supabase. SQLAlchemy/psycopg lazy engine, bounded pool/timeouts, safe parameters, service transaction/read scopes, request session dependency and lifespan disposal; authenticated readiness queries SELECT 1. Real commit/rollback, returned connections and protected 200 readiness/lifecycle checks pass. No persistent schema changes.
- **1.2 — Initial identity/pair/QR/profile schema:** VERIFIED; additive Alembic revision `0001_identity_profiles` applied to authorized development Supabase after metadata inspection and rollback-only migration tests. Ten SQLAlchemy-mapped domain tables, independent Lost/ICE profiles, encrypted-field/consent checks, immutable QR identity/replacement guards, partial current-tag uniqueness, immediate parent locks and deferred exactly-two constraints. 24 new PostgreSQL checks pass; installed schema matches mappings. No API/UI implementation added.
- **1.3 — Commerce/payment/fulfillment schema:** VERIFIED; additive `0002_commerce` applied after inspecting installed metadata and testing upgrade with representative previous-revision data. Sixteen new SQLAlchemy-mapped tables, Decimal catalog/order snapshots, independent QR-copy uses, immutable placed order/address records, exclusive reservations and payment review holds, provider-independent attempts/private evidence/append-only reviews, and paid allocation/physical-QA shipment guards. 55 new PostgreSQL checks pass; all 26 domain tables are RLS protected and contain zero persistent test rows. Services/API/UI remain later tasks.
- **All other tasks:** TODO, as individually enumerated above.

### Phase summary

Only edit this section after *actual* progress. Keep entries short. Do not create a new log file per task.

| Phase | Status | Evidence / main files | Remaining issue |
| --- | --- | --- | --- |
| 0 — Foundation | DONE | All 3 tasks VERIFIED: backend startup, frontend production build, typed local integration + 16 checks and outage check | Database readiness belongs to Phase 1 |
| 1 — Database | IN PROGRESS | Tasks 1.1–1.3 VERIFIED; installed `0002_commerce` after `0001_identity_profiles`; 101 backend tests including 82 real PostgreSQL checks; Alembic consistency PASS | Task 1.4 messaging/location/audit/outbox/jobs/intents + least-privilege/RLS; comprehensive migration/race verification remains 1.5 |
| 2 — Authentication | NOT STARTED | — | — |
| 3 — QR management | NOT STARTED | — | — |
| 4 — Public scans | NOT STARTED | — | — |
| 5 — Remaining features | NOT STARTED | — | — |
| 6 — Integration/release | NOT STARTED | — | — |

**Allowed task states:** TODO · IN PROGRESS · IMPLEMENTED · VERIFIED · BLOCKED. Phase DONE requires its complete acceptance criteria.

### Latest handoff (update in place, max ~12 lines)
- **Date:** 2026-10-13 (Asia/Karachi).
- **Current phase/task:** Phase 1 Task 1.3 VERIFIED. Total 31, verified 6, remaining 25. User authorized next bounded task after 1.2; stop after this report.
- **What works:** Applied commerce schema for categories/products/variants/images; Decimal orders and purchase-time line/print/price/contact/address snapshots; pair reservation/allocation units and independent QR-copy mappings; provider-independent payment attempts/private evidence/append-only bank reviews; shipments/membership and physical pair QA. Five copies use two existing QR identities and one pair. No actual catalog products/prices, gateway, bank processing or Storage objects were provisioned.
- **Invariants:** Placed order/customer/price/address/line/QR-use history cannot be rewritten, even after cancellation. Deferred guards check line totals/currency, per-line copy sums, both Lost/ICE copies per new pair and shipping snapshot. Partial uniqueness prevents two live claims; review-state payments block release; allocated entitlement cannot be recycled. Manual-bank verification requires matching settlement plus bank-confirmed review; duplicate settlement fingerprints/idempotency/provider IDs are constrained. Shipment creation/release requires matching verified settlement, allocated membership and latest physical QA; refund/order status reconciliation is checked.
- **Files:** Added backend/app/db/commerce.py, alembic/commerce_guards.sql/versions/0002_commerce.py, tests/integration/test_commerce_schema.py/test_commerce_upgrade.py; updated Alembic mapping registration, identity test head expectation, backend/README.md and this record. Existing uncommitted Task 1.1/1.2 implementation and initial migration preserved. Ignored backend/.env explicitly loaded without printing credentials.
- **DB inspection/application:** Existing PostgreSQL revision 0001 and ten domain tables inspected; commerce/legacy competing tables absent, core row counts zero. Rollback-only 0002 upgrade preserved representative prior QR/profile records (version 7). Final pre-application suite: 55 passed in 169.77s. Safe `alembic upgrade head` applied 0002; current reports `0002_commerce (head)`; `alembic check` reports no new upgrade operations. Final metadata confirms 26 RLS-protected domain tables, zero persistent domain rows; managed Auth was not persistently changed.
- **Final tests:** From backend: `.venv/Scripts/python.exe -m dotenv -f .env run -- .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -W error`: 101 passed in 200.34s, exit 0 (55 new + 27 previous real PostgreSQL checks + 19 local checks). Covers real COMMIT rejection/rollback, migration preservation/collision refusal, immutable snapshots after account/catalog changes, SQL bypasses, copy-versus-pair counts, reservation/payment holds, verified allocation, QA/membership/refund dispatch. Ruff check/format (20 Python files), pip check and git diff --check PASS. Frontend source unchanged; no frontend rerun claimed.
- **Safety/recovery:** 0002 adds 16 tables, indexes/functions/triggers without altering prior identity/Auth tables, seeding pricing, or dropping data. Transactional DDL, five-second lock timeout and collision detection prevent partial destructive adoption. Browser grants revoked/RLS enabled; runtime least-privilege role/policy work remains 1.4. Downgrade refuses deletion; use reviewed additive forward fixes. Test inserts/deletes touch only rollback-only synthetic records. No worktree, deployment or push; user subsequently authorized a local commit of Tasks 1.1–1.3.
- **Fixes:** Corrected ambiguous PL/pgSQL record/table alias and fixture/test insertion issues. Review found refund/dispatch consistency gap; added matching-settlement and deferred reconciliation checks with three regression tests. An accidentally overlapping DDL check safely timed out; switched to serial runs. A larger pre-application run had 74 passes then transient DNS failure on final connection; final serial and full runs passed with strict warnings and assertions unchanged.
- **Unresolved/limits:** No Task 1.3 blocker. Actor/MFA authorization, encryption/key normalization/rotation, actual bank review, checkout idempotency/audit/outbox, storage policies/retention, approved commercial pricing, digital-artwork eligibility versus physical QA, and audited reshipments remain their later tasks/policy gates. Existing-QR ordering/future products/gateways stay feature-gated; schema does not certify those workflows. Comprehensive race/clean-install/recovery tests remain 1.5; no broad concurrent reservation suite claimed. Working MVP requires verified end-to-end tasks and resolved release gates; production deployment still needs approval.
- **Next exact task:** Task 1.4 — inspect installed 0002 metadata and relevant approved DB/security/API contracts; add messaging, encrypted optional location, audit, durable outbox/jobs/activation-intent/idempotency schema and least-privilege runtime roles/RLS. Preserve current migrations, independent profile/recipient ownership history and commerce snapshots; verify on real PostgreSQL and apply only safe authorized development changes.

## 5. Handoff instructions for a new AI session

1. Read `/PHASE_IMPLEMENTATION.md`, then only the relevant `/docs` files and `/mocUI` assets for the current task.
2. Check real Git changes and code before deciding what to do; never trust status notes over repository state.
3. Resume the **next exact action** and write code. Do not restart the project plan or introduce worktrees.
4. Run focused tests/builds; update the phase table and latest handoff with concrete evidence, blockers, and next action.
5. End with a concise report: implemented, tested, blocked, next.
