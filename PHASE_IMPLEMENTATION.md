# SafeReturn — Phase Implementation Plan & AI Handoff

**Status:** Development started. `/docs` is authoritative; supplied UI references are actually in `/mock-ui` (not `/mocUI`). Historical implementation records describe code absent from this workspace; task status below follows actual source and tests.

**Planning revision clarification (2026-10-18):** The source code and recorded development evidence now exist. The original code-absence warning above is historical, not a finding that verified services disappeared. This owner-requested roadmap expansion preserves every original task/status/history block; see the revised register and Sections 4A–4B. Planning only: no application/database/deployment changes are authorized here.

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


#### New follow-ups in this phase (2026-10-18 revision)

Original task IDs and their evidence remain unchanged. Cards below are new work, grouped after the milestone they extend. All new contracts are proposals until reviewed; this planning request authorizes no implementation.

**Placement group: after original Task 2.3.**

<a id="task-2-3a"></a>

##### 2.3A — Staff MFA enrollment, verification and secure recovery entry

**Status:** IMPLEMENTED · **Phase placement:** Phase 2, after original 2.3.

- **Existing verified dependency:** `2.1`, `2.2`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Make current staff accounts able to satisfy the existing MFA guard through supported Supabase factors.
- **Existing implementation to reuse:** JWT/session/role guards, SSR cookies, signed AMR checks and existing auth screens; preserve the owner's operations and finance grants.
- **Missing behavior:** Enrollment, challenge, factor-state UI, step-up return handling and safe factor-loss escalation.
- **Backend / endpoint changes:** Review a minimal current-staff/capability DTO; retain live account/session/AAL checks. Any new capability endpoint needs a Doc 04 contract before exposure.
- **Frontend pages / changes:** Proposed /admin/security/mfa plus protected challenge/enrollment screens; accept only fixed same-origin return paths.
- **Database / migration:** Reuse staff_roles and narrow Auth-state functions; no direct runtime Auth SELECT, credential reset or role rewrite.
- **Security and privacy:** TOTP/approved factors via supported Supabase flows; no local MFA flags, token-iat shortcut or recovery bypass; never persist factor secrets in browser storage/logs.
- **Automated tests:** Synthetic enrollment/challenge success/failure, expired session, AAL1/AAL2 mismatch, revoked role, CSRF, replay and open-redirect negatives.
- **Manual tests:** Owner-controlled disposable staff enrollment/challenge and lost-factor escalation; real enrollment only with the user present.
- **Explicit acceptance criteria:** Eligible staff can enroll and reach an allowed route after genuine MFA; unsupported/failed MFA denies every privileged action; both existing owner roles remain.
- **External credentials / services:** Existing Supabase Auth configuration and owner-controlled authenticator; no secret supplied in chat.
- **Dependencies / blockers:** Factor/recovery UX must follow existing security policy; live acceptance needs an interactive authorized account. Task 2.3's remaining email acceptance is retained separately.

**Implementation evidence (2026-10-18):** `/admin/security/mfa` supports explicit Supabase TOTP enrollment, factor status and challenge/verification. Setup key is transient action/UI state only (no browser storage/logging); existing factors are never removed. Exact-Origin server actions recheck provider identity and backend live staff/session/AAL before mutation and after verification; fixed same-origin return allowlist. Existing staff forms step up through this page, with destination backend role checks unchanged. `/me/staff-security` is a no-store AAL1 bootstrap read documented in Doc 04; no new database grants/migration or Auth runtime SELECT. Account links to security; factor loss gives trusted-channel security-owner escalation, no reset/bypass.

**Focused verification:** 57 cryptographic auth tests + five staff-bootstrap unit tests PASS; six existing real-PostgreSQL synthetic guard cases PASS (139.97s), covering banned/deleted/anonymous/expired sessions, missing session/subject mismatch, signed/live AAL mismatch and revoked role. Rehearsal cleanup verifies installed revision/table counts/runtime roles/catalog unchanged. Read-only owner lookup confirms active `finance` and `operations`. Frontend: 14 SDK cases + eight return-path cases PASS; seven MFA action-flow cases PASS (Origin, post-verification assurance, revoked access, provider failure, fixed return and untrusted prior-state redirect injection). One bounded anonymous Chromium flow PASS on temporary port 3032 (9.9s); temporary server stopped. Frontend typecheck and scoped backend Ruff lint/format PASS; repository has no frontend lint configuration/package, so no frontend-lint pass claimed. Initial browser attempt on existing 3031 returned old-build 404; initial DB attempt lacked explicit env, then sandbox network denied; final authorized isolated DB run passed (one pytest cache warning). No full suite/build run.

**Remaining acceptance gate:** Owner-controlled disposable staff enrollment/challenge through a refreshed running frontend/API, genuine privileged-route success, and lost-factor escalation review. No real account enrolled/reset/removed, no real email or external write. Thus IMPLEMENTED, not VERIFIED. Original 2.3 email acceptance remains separate. At the 2.3A handoff, local URL `http://localhost:3031` / API 8030 was preserved and its running build was not restarted; see 5.7A below for the subsequent authorized runtime refresh.

**MFA troubleshooting follow-up (2026-10-19):** Owner reports authenticator codes rejected and intermittent blank display inside phone app. Read-only Supabase timing check: HTTP 200 and computer/provider difference ~1.3s; owner factor metadata shows one TOTP factor still unverified (no secret queried). Found presentation bug: every challenge failure was labeled invalid/expired. Added fixed safe categories/messages for bad code, expired challenge/session, rate limit, changed connection, missing factor, policy denial and provider outage. Server logs record only fixed categories, never submitted codes, keys, tokens, IDs or raw provider messages. Added fresh-code/phone-time instructions; existing factor/session/AAL/role/Origin verification unchanged. Seventeen focused MFA SDK/action cases PASS and frontend typecheck PASS; existing synthetic browser provider now emits the SDK's known bad-code error enum. No real enrollment/challenge/reset/removal performed; root cause of owner's rejected code needs one owner-controlled retry with precise error reporting. Real MFA acceptance remains pending.

**Owner-controlled MFA acceptance (2026-10-19):** Owner confirms MFA now works after correcting the authenticator entry type; the previous entry required manual refresh, and the corrected time-based entry succeeds. Owner reports working access, with current browser context at /admin. This is owner-reported real MFA success, separate from synthetic evidence. No agent enrollment/reset/factor removal occurred. The real MFA/login gate is satisfied; lost-factor escalation review and remaining module-level manual accessibility/native Urdu acceptance are not claimed complete. Statuses remain IMPLEMENTED pending remaining gates.

<a id="task-2-3b"></a>

##### 2.3B — Controlled staff onboarding, role grants and revocation policy

**Status:** BLOCKED · **Phase placement:** Phase 2, after original 2.3.

- **Existing verified dependency:** `2.1`, `2.2`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Establish an auditable least-privilege provisioning/revocation procedure before adding any staff-management writer.
- **Existing implementation to reuse:** staff_roles, revoked_at history, current explicit require_staff role lists and MFA enforcement.
- **Missing behavior:** Approved grant authority, separation of duties, last-authorized-admin protection and revocation/session procedure.
- **Backend / endpoint changes:** Contract review only until approved; prefer controlled operations provisioning initially. No assumed role-management API or automatic superadmin inheritance.
- **Frontend pages / changes:** Role/security help and safe status in 2.3A/5.7A; self-service role editor remains optional O-02.
- **Database / migration:** Preserve active-role uniqueness and append-only revocation history; rehearse any future narrowly granted helper migration.
- **Security and privacy:** No self-grant, shared admin identity or broad Auth/service-role privilege. Test with disposable staff, never revoke the owner's real grants incidentally.
- **Automated tests:** Policy tests for cross-role escalation, concurrent last-admin changes, revoke-during-request and stale sessions.
- **Manual tests:** Security owner approves grant/revoke evidence, break-glass custody and support escalation steps.
- **Explicit acceptance criteria:** A named authority, reviewed permission matrix and reproducible grant/revoke runbook exist; every approved change is audited and effective on the next protected request.
- **External credentials / services:** Named security owner and controlled privileged provisioning access, held outside the web app.
- **Dependencies / blockers:** Approval of staff authorization, dual-control/last-admin rules and recovery authority; this plan does not authorize real grants or revocations.

<a id="task-2-3c"></a>

##### 2.3C — Safe staff user-directory and account-state read APIs

**Status:** TODO · **Phase placement:** Phase 2, after original 2.3.

- **Existing verified dependency:** `2.1`, `2.2`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Supply bounded, permission-checked account metadata for user management and registered-user counts.
- **Existing implementation to reuse:** user_profiles, existing narrow account/session functions, audit and role guards.
- **Missing behavior:** Search, cursor paging, allowed sorting and safe verification/suspension summaries; no customer-profile or medical lookup.
- **Backend / endpoint changes:** PROPOSED read-only user list/detail/count contracts; approve field projections and permitted roles before assigning API IDs. Use a narrow pinned helper if Auth metadata is necessary.
- **Frontend pages / changes:** 5.7C consumes these APIs; this task defines typed DTOs and unavailable/denied states.
- **Database / migration:** Inspect existing account-state storage; add only reviewed query indexes/helper grants. Runtime logins receive no general Auth-table access.
- **Security and privacy:** Security/superadmin scope requires explicit grant policy; support gets only approved case-specific fields. Counts are authorized data too.
- **Automated tests:** Search/paging ties, maximum limits, revoked staff, role-filtered counts, hidden email/PII fields and query-plan tests.
- **Manual tests:** Compare synthetic directory rows/counts with fixture SQL under each approved role.
- **Explicit acceptance criteria:** No unbounded Auth fetch or client-side enumeration; unauthorized users cannot infer account existence; lists/counts match documented predicates.
- **External credentials / services:** No new external provider credential; approved metadata projection needed.
- **Dependencies / blockers:** New read-contract and support-field review; high-risk mutation rules remain in 2.3D.

<a id="task-2-3d"></a>

##### 2.3D — Account suspension/restoration and recovery escalation

**Status:** BLOCKED · **Phase placement:** Phase 2, after original 2.3.

- **Existing verified dependency:** `2.1`, `2.2`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Give authorized security staff reviewed account lifecycle actions without changing ownership or resetting credentials casually.
- **Existing implementation to reuse:** Existing account/session rejection, user state, immutable order/QR history and audit.
- **Missing behavior:** Approved suspend/restore commands, conflict handling, session invalidation and case-linked recovery escalation.
- **Backend / endpoint changes:** PROPOSED versioned security commands after policy approval; recovery routes open a controlled case, never reveal passwords/OTP or silently change email.
- **Frontend pages / changes:** 5.7C adds reason/confirmation/step-up controls only once contracts and permissions are approved.
- **Database / migration:** Inspect current account-state mechanism; forward migration only if necessary, with reconciliation against Supabase account/session state.
- **Security and privacy:** Current MFA and recent reauthentication, narrow role, audit, no self-escalation, no blind last-admin lockout; preserve paid allocations and legal records.
- **Automated tests:** Suspend versus active request, restore idempotence, stale version, concurrent changes, protected self-action and restricted-role negatives.
- **Manual tests:** Review account-takeover and lost-factor playbooks with the security owner using disposable accounts.
- **Explicit acceptance criteria:** Suspended accounts fail protected requests; restoration does not restore revoked staff privileges; recovery requires documented evidence and leaves history intact.
- **External credentials / services:** Authorized Auth administration channel only if the approved design needs it.
- **Dependencies / blockers:** Identity-proofing, suspension consequences, restoration authority and break-glass approval are unresolved.


### Phase 3 — QR activation, ownership and profiles
**Outcome:** Core Lost/ICE functionality works through backend and UI.

- Implement QR lookup, activation, access permissions, paired activation, and independent editing for each QR identity.
- Support multiple products and QR identities under one account.
- Build/edit relevant screens based on `/mocUI` and connect to live APIs.
- Test public-vs-private fields and cross-user authorization.

**Done when:** a user can activate, manage and edit multiple QR identities without affecting unrelated profiles.


#### New follow-ups in this phase (2026-10-18 revision)

Original task IDs and their evidence remain unchanged. Cards below are new work, grouped after the milestone they extend. All new contracts are proposals until reviewed; this planning request authorizes no implementation.

**Placement group: after original Task 3.5.**

<a id="task-3-5a"></a>

##### 3.5A — Admin inventory and batch read/query foundation

**Status:** IMPLEMENTED · **Phase placement:** Phase 3, after original 3.5.

- **Existing verified dependency:** `3.1`, `3.2`, `3.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Make existing pair generation and lifecycle data discoverable without exporting activation credentials.
- **Existing implementation to reuse:** API-090, qr_batches, tag_pairs, qr_codes, reservation/allocation constraints and existing QA.
- **Missing behavior:** Canonical API-084/085/091/092 list/detail services, safe stock counts, filters and stable pagination; reconcile API-230 stock contract.
- **Backend / endpoint changes:** Implement approved inventory/batch read endpoints and typed low-stock projections; reuse actual reservation/payment-review eligibility.
- **Frontend pages / changes:** 5.7D consumes query contracts; no duplicate generation service.
- **Database / migration:** Review query indexes; preserve two-current-tag and unique live reservation/allocation invariants.
- **Security and privacy:** Operations+MFA according to existing guards; metadata never contains activation verifiers, sealed-insert plaintext or broad private customer data.
- **Automated tests:** Concurrent generation/query, count ties, active-review reservations, zero stock, unauthorized reads and safe projection tests.
- **Manual tests:** Compare pair/tag/batch totals and low-stock warnings with isolated SQL fixtures.
- **Explicit acceptance criteria:** Pairs and identities are counted separately; available stock is not inferred from elapsed timers; approved lists are bounded and contain no credentials.
- **External credentials / services:** Existing generation keys only for explicitly authorized generation tests; read tests use synthetic fixtures.
- **Dependencies / blockers:** Approve the low-stock threshold and API-230 exact shape; no invented production threshold.

**Implementation evidence (2026-10-19):** Added canonical API-084/085 pair list/detail, API-091/092 batch list/detail and API-230 stock summary in `backend/app/api/v1/inventory_queries.py`, registered in existing app. Typed DTOs and Doc 04 exact projections/filters/cursors; no new frontend pages or generation/allocation/release/export writer. Existing live session/email/signed+live MFA and explicit operations guard protect every read; no security_admin/superadmin inheritance. Pair/tag identities and historical replacements are counted separately; list/history limits 1–100, stable immutable created_at/UUID ties. Latest QA and live allocation are bounded metadata only. Activation credentials/verifiers, sealed inserts, public tokens, owner/contact/medical/address data and free-text QA notes are excluded. Available stock mirrors `sr_checkout_reserve`; expired timers never release live claims. Optional `inventory_low_stock_threshold` defaults unset, producing null threshold/indicator; no ignored environment edit or threshold chosen.

**Focused verification:** Initial five-case isolated real-PostgreSQL run: four PASS, one fixture privacy-canary failure (615.23s). The generic replacement helper used the same synthetic string as serial and public token; replaced it with distinct synthetic values without weakening the API projection or assertion. Reran only paging/privacy/read-only case: PASS (342.66s including fixture/cleanup). All five cases pass across these runs: tied pair/batch/history paging and exact filters; empty batch/zero stock; latest-QA/no-join-fanout counts; checkout-capacity SQL comparison; expired reservations, genuine synthetic settlement/allocation; unknown/configured threshold boundaries; customer/finance/support/security/superadmin/AAL mismatch and revoked role/session denial; malformed bounds/cursors and absent detail; concurrent generation sees only whole 4-pair/8-tag batches; unchanged synthetic row fingerprints. Existing pair-batch/current-tag/live-claim indexes reviewed and bounded filtered EXPLAIN checked on fixture data; no production-scale performance claim or migration. Rehearsal preservation/owned-schema cleanup PASS. Scoped Ruff lint/format and five typed OpenAPI GET IDs PASS; API-090 POST preserved. No full suite, frontend build/typecheck or browser run (no frontend changes).

**Runtime/preservation:** Prior local servers were no longer listening; restored API 8030 and configured frontend at `http://localhost:3031`, using unchanged ignored env and the existing Auth allowlist launcher. Running OpenAPI includes API-230; anonymous new collections/summary return 401. Frontend/API health 200 after startup (first health attempt preceded frontend readiness). No worktree/commit/push/deployment or installed migration/grant change. Read-only installed check confirms exactly finance+operations for owner and head `0019_retention_recovery`. Only synthetic fixture generation/payment/QA/replacement records were written in UUID rehearsal schemas; no real email/payment/Sheets/storage/factor/credential mutation.

**Remaining gate:** Operations approval of the low-stock threshold and operational interpretation/acceptance of the documented API-230 projection. Unset remains unknown; no stock notifications or invented threshold. Therefore IMPLEMENTED, not VERIFIED. Inventory screens belong to separate 5.7D; dashboard 5.7B still needs its other query dependencies and metric approvals. Stop before another task unless separately requested.

<a id="task-3-5b"></a>

##### 3.5B — Owner disable/history and paired security lifecycle commands

**Status:** TODO · **Phase placement:** Phase 3, after original 3.5.

- **Existing verified dependency:** `3.2`, `3.3`, `3.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Expose approved lifecycle controls while preserving current identity, purpose and pair ownership.
- **Existing implementation to reuse:** Current status enums, replacement/revocation guards, owner checks and append-only activation/audit records.
- **Missing behavior:** Canonical API-034 history, API-035 owner public-status controls and API-088 paired suspension; review restoration/revocation extensions explicitly.
- **Backend / endpoint changes:** Implement existing contracts with parent locking and versions; any additional restore/revoke endpoint remains PROPOSED pending contract/security review.
- **Frontend pages / changes:** Owner QR status/history controls and later 5.7D security actions; publish safe unavailable states on old/public routes.
- **Database / migration:** Reuse lifecycle state and immutable token/history guards; do not mint tokens on disable/restore or move a single child.
- **Security and privacy:** Owner disable is not staff suspension; security actions need reason/MFA and reviewed authority. Recheck in-flight activation, publication, print and fulfillment.
- **Automated tests:** Disable versus reveal/activation/print races, cross-owner writes, both-tag suspension, replay, rollback and old-token privacy.
- **Manual tests:** Scan both synthetic tags through each permitted state and verify owner/staff messages in English/Urdu.
- **Explicit acceptance criteria:** Every permitted transition has a documented actor and audit; no unauthorized reactivation, hidden pair split or history loss.
- **External credentials / services:** No live provider credential; synthetic URLs only.
- **Dependencies / blockers:** Restore/revoke scope and policy require review before enabling extensions; independent tag transfer stays excluded.

<a id="task-3-5c"></a>

##### 3.5C — Approved damaged/compromised tag replacement workflow

**Status:** BLOCKED · **Phase placement:** Phase 3, after original 3.5.

- **Existing verified dependency:** `3.1`, `3.2`, `3.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Complete API-089's controlled replacement without changing the pair's owner or the unaffected identity.
- **Existing implementation to reuse:** Existing current-child uniqueness, replaces_qr_id chain, sealed credential custody and print/fulfillment gates.
- **Missing behavior:** Approval proof, replacement eligibility, compromised-label response and safe pending-order/reprint handling.
- **Backend / endpoint changes:** API-089 through a locked, audited, idempotent approved service; no general reassignment or activation-secret reveal.
- **Frontend pages / changes:** 5.7D case-linked replacement request/decision/history, disabled until policy and physical release approval.
- **Database / migration:** Use existing replacement chain; inspect whether explicit approval/version records need a forward migration.
- **Security and privacy:** Revoke the retired public identity atomically; preserve one current Lost and one current ICE; invalidate relevant grants and recheck print sources.
- **Automated tests:** Two concurrent replacements, stale worker/download, old-token denial, wrong-pair approval and transaction rollback.
- **Manual tests:** Security/operations approve a synthetic compromised-label drill and physical replacement/packaging checklist.
- **Explicit acceptance criteria:** Exactly one replacement succeeds; the old token cannot disclose content; no paid order or unrelated QR is silently rebound.
- **External credentials / services:** Approved printer/artwork and controlled physical replacement procedure.
- **Dependencies / blockers:** Replacement entitlement, approval authority, fees/reprint policy, compromised-credential custody and physical release rules.


### Phase 4 — Public scan experiences and messaging
**Outcome:** A finder/emergency contact scanning a QR sees only the intended public experience.

- Implement Lost and ICE scan views, contact interactions, privacy rules and abuse handling specified in `/docs`.
- Build responsive UI and test phone-sized layouts and invalid/inactive QRs.

**Done when:** scan-to-action flows work end-to-end against development backend.


#### New follow-ups in this phase (2026-10-18 revision)

Original task IDs and their evidence remain unchanged. Cards below are new work, grouped after the milestone they extend. All new contracts are proposals until reviewed; this planning request authorizes no implementation.

**Placement group: after original Task 4.4.**

<a id="task-4-4a"></a>

##### 4.4A — Live Turnstile and trusted-proxy abuse acceptance

**Status:** BLOCKED · **Phase placement:** Phase 4, after original 4.4.

- **Existing verified dependency:** `4.1`, `4.2`, `4.3`, `4.4`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Close the recorded live challenge and deployment-peer/IP trust gates without weakening emergency protections.
- **Existing implementation to reuse:** Existing Siteverify adapter, bound single-use proofs, committed budgets and bilingual public forms.
- **Missing behavior:** Real allowed-domain/widget acceptance, proxy topology review and outage/fallback decision.
- **Backend / endpoint changes:** Validate deployed peer extraction and fixed provider contract; never trust arbitrary forwarded headers or enlarge JWT/rate-limit allowances.
- **Frontend pages / changes:** Exercise real widget/expiry/retry on Lost/ICE and no-location submission; retain accessible outage states.
- **Database / migration:** No assumed schema change; retain proof digests and bounded privacy-safe budgets.
- **Security and privacy:** No public token/IP/location in telemetry; no automatic emergency challenge bypass.
- **Automated tests:** Existing mocks plus staging spoofed-proxy, proof replay, provider timeout and keyboard/no-location regression.
- **Manual tests:** Explicitly authorized staging challenge acceptance on approved domains and real mobile browsers.
- **Explicit acceptance criteria:** Actual hostname/action/resource binding works; provider outage follows an approved fail-closed/fallback policy, with recorded evidence.
- **External credentials / services:** Existing Turnstile keys, approved hostname and deployed proxy configuration; values stay secret.
- **Dependencies / blockers:** Live-provider test authorization, staging domain/proxy configuration and founder/security emergency fallback decision.

<a id="task-4-4b"></a>

##### 4.4B — Canonical public abuse reporting and moderation intake

**Status:** TODO · **Phase placement:** Phase 4, after original 4.4.

- **Existing verified dependency:** `4.1`, `4.2`, `4.3`, `5.7`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Connect public abuse reporting to a controlled moderation case without disclosing owner or finder content.
- **Existing implementation to reuse:** API-014 specification, committed abuse budgets, support_cases and owner message flagging.
- **Missing behavior:** Public API-014 implementation, bounded duplicate-resistant intake, report receipt and safe staff linkage.
- **Backend / endpoint changes:** Implement canonical /public/abuse-reports with reviewed schema/rate/challenge controls and minimal queued case metadata.
- **Frontend pages / changes:** Accessible report action on public QR/status pages; no invented public chat or generic support mutation.
- **Database / migration:** Inspect abuse_flag/support-case representation; add only necessary approved report/dedupe state and restricted RLS.
- **Security and privacy:** Do not accept public actor/owner authority, expose reported content, or let reports automatically suspend tags/accounts.
- **Automated tests:** Spam/concurrent duplicates, invalid token non-enumeration, provider outage, malicious text and staff/owner isolation.
- **Manual tests:** Moderation owner reviews escalation/false-report examples and both language receipts.
- **Explicit acceptance criteria:** A report is safely persisted and queryable through a restricted synthetic case fixture; 5.7I later supplies the console. Reports never automatically suspend users/tags.
- **External credentials / services:** Existing challenge provider for live acceptance only; synthetic tests by default.
- **Dependencies / blockers:** Approve report fields, evidence minimization, report retention and moderation escalation SLA.

<a id="task-4-4c"></a>

##### 4.4C — Approved notification templates and live deliverability acceptance

**Status:** BLOCKED · **Phase placement:** Phase 4, after original 4.4.

- **Existing verified dependency:** `4.3`, `4.4`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Finish template/version/domain acceptance while preserving the verified generic-email privacy design.
- **Existing implementation to reuse:** Durable Resend worker, stable provider keys, attempts, dead letters and the single previously authorized received email.
- **Missing behavior:** Reviewed template/copy versions, domain authentication and bounded deliverability/recovery evidence for release.
- **Backend / endpoint changes:** Version templates in reviewed code/config; expose metadata in 5.7H. No arbitrary live HTML editor or bulk-send API.
- **Frontend pages / changes:** Clear saved-versus-notified copy and template-version metadata; customer preferences stay limited to approved features.
- **Database / migration:** Retain recipient snapshots and attempt history; a template/version reference migration is conditional on audit requirements.
- **Security and privacy:** No finder text, contacts, coordinates, medical data, credentials or private URLs in emails/logs; preserve the 23-hour ambiguous-delivery review cutoff.
- **Automated tests:** Template allowlists, broken-link/privacy canaries, lost-ack/retry and version rollback regression.
- **Manual tests:** New explicit authorization for every additional real delivery; verify approved sender domain and receipt with disposable recipients.
- **Explicit acceptance criteria:** Approved template versions and real sender/delivery evidence are recorded; failures never roll back saved finder messages.
- **External credentials / services:** Resend domain/account, SPF/DKIM/DMARC and approved recipient; no new email is authorized by this planning request.
- **Dependencies / blockers:** Sender/copy approval, delivery test authorization and provider/domain acceptance.

<a id="task-4-4d"></a>

##### 4.4D — Public policy/configuration and support-channel completeness

**Status:** TODO · **Phase placement:** Phase 4, after original 4.4.

- **Existing verified dependency:** `0.2`, `4.1`, `4.3`, `5.7`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Provide the approved public information needed for scanning, consent, privacy and support.
- **Existing implementation to reuse:** Existing bilingual public help, no-JavaScript rendering, locale cookie and safe QR status copy.
- **Missing behavior:** Canonical API-005 safe config and reviewed privacy/terms/contact/policy surfaces; inspect all existing footer links.
- **Backend / endpoint changes:** Implement /public/config allowlist only; static contact/help must not invent a ticket API.
- **Frontend pages / changes:** Review proposed /privacy, /terms and /contact against the UI registry; public English/Urdu pages and working legal/support links.
- **Database / migration:** No database migration expected; store reviewed policy versions as controlled content/config, not credentials.
- **Security and privacy:** No private thresholds, provider keys, internal origins or misleading erasure promises in public config/copy.
- **Automated tests:** Public access, no-JS/RTL, broken-link, closed DTO and secret-canary checks.
- **Manual tests:** Founder/legal/native-language approval of notices, support channel, retention/backups explanation and emergency wording.
- **Explicit acceptance criteria:** Public policies match actual behavior and approved versioned consent; unavailable policy decisions visibly block launch rather than fabricate values.
- **External credentials / services:** Approved support contacts/domain and legal/native-language copy.
- **Dependencies / blockers:** Publication requires policy/copy approval; development can add safe structure without inventing legal terms.


### Phase 5 — Remaining approved product features
**Outcome:** All other features required in `/docs` implemented in priority order.

- Inventory uncovered required screens/endpoints from the documents and `/mocUI`.
- Build features one vertical slice at a time with focused tests.
- Avoid inventing large optional features or expanding scope without approval.

**Done when:** every required capability has an implementation and verified acceptance check.


#### New follow-ups in this phase (2026-10-18 revision)

Original task IDs and their evidence remain unchanged. Cards below are new work, grouped after the milestone they extend. All new contracts are proposals until reviewed; this planning request authorizes no implementation.

**Placement group: after original Task 5.1.**

<a id="task-5-1a"></a>

##### 5.1A — Catalog administration completion and actual public-image acceptance

**Status:** TODO · **Phase placement:** Phase 5, after original 5.1.

- **Existing verified dependency:** `5.1`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Complete documented catalog workflows by extending the existing tested editor rather than rebuilding it.
- **Existing implementation to reuse:** API-220–229, /admin/products, signed raster upload/verified attachment, immutable order snapshots and archive semantics.
- **Missing behavior:** Audit remaining category/variant/media-order/publication/price/template controls, search/paging and bilingual administrative states against ADM-20–24.
- **Backend / endpoint changes:** Reuse current commands; approve a contract only for a demonstrated missing media/order/read field. No new product category enablement.
- **Frontend pages / changes:** Extend existing catalog components and connect them to 5.7A navigation; keep publish/archive/version conflicts explicit.
- **Database / migration:** Existing catalog tables and versions first; no destructive product/image deletion or historical repricing.
- **Security and privacy:** Existing explicit operations/security/superadmin permissions and current MFA stay intact; finance alone cannot edit catalog.
- **Automated tests:** Reuse catalog integration/browser tests; add only uncovered wizard/media-order/role/version cases.
- **Manual tests:** Explicitly authorized Cloudinary upload of one disposable public image, approved preset/folder/cleanup and native copy review.
- **Explicit acceptance criteria:** A permitted operator can complete every approved catalog workflow; current screenshots/order snapshots stay unchanged; actual upload acceptance is separately evidenced.
- **External credentials / services:** Existing Cloudinary account/preset and founder-approved sellable sizes/prices/templates; no credentials overwritten.
- **Dependencies / blockers:** Actual Cloudinary upload acceptance and commercial/artwork approval; P1 products remain disabled.

**Placement group: after original Task 5.2.**

<a id="task-5-2a"></a>

##### 5.2A — Saved shipping-address CRUD and checkout selection

**Status:** TODO · **Phase placement:** Phase 5, after original 5.2.

- **Existing verified dependency:** `2.2`, `5.2`, `5.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Close the expressly deferred saved-address workflow without changing frozen purchase addresses.
- **Existing implementation to reuse:** shipping_addresses, encrypted inline quote/order snapshots and current checkout forms.
- **Missing behavior:** API-067–070, address list/add/edit/delete/default selection and reference-aware deletion behavior.
- **Backend / endpoint changes:** Implement canonical owner-only CRUD; review default-address and quote-selection DTO extension before exposing it.
- **Frontend pages / changes:** Approved customer address screen, accessible selector in checkout and private masked summaries.
- **Database / migration:** Inspect row/version/default representation and references; add a narrowly scoped forward migration only where absent, preserving order snapshots and referenced records.
- **Security and privacy:** Owner-only access, encrypted names/phones/street, strict versions/Origin, no address data in localStorage or analytics.
- **Automated tests:** Cross-owner CRUD, concurrent default selection, deleted/referenced address, quote/edit race, rollback and immutable historical snapshots.
- **Manual tests:** Create/select/change/delete disposable addresses in English/Urdu, verify shipping history remains frozen.
- **Explicit acceptance criteria:** Saved-address changes never edit placed orders; invalid/foreign/default races fail safely; referenced-address policy is enforced.
- **External credentials / services:** Existing encryption keyring; no new provider integration.
- **Dependencies / blockers:** Confirm default-address and active-order deletion rules against API/DB contract; do not invent legal retention periods.

**Placement group: after original Task 5.3.**

<a id="task-5-3a"></a>

##### 5.3A — Customer cancellation requests and controlled reservation release

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.3.

- **Existing verified dependency:** `5.2`, `5.3`, `5.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Add canonical API-065 without losing a potentially settled transfer or paid allocation.
- **Existing implementation to reuse:** Order/payment states, under-review holds, reservations, support cases and encrypted idempotent receipts.
- **Missing behavior:** Approved cancellation eligibility, request-versus-final-cancel handling and reconciliation before stock release.
- **Backend / endpoint changes:** API-065 through a locked, versioned, audited service; cancellation of review/paid orders routes to authorized review.
- **Frontend pages / changes:** Owner order cancellation request/status and later 5.7E decision context; no instant refund promise.
- **Database / migration:** Reuse reservation/order guards; add approval/request history only if existing state cannot represent the reviewed workflow.
- **Security and privacy:** Order→attempt→reservation lock order; client time or screenshot cannot authorize release; preserve pair ownership/history.
- **Automated tests:** Cancel versus settlement/allocation/expiry races, duplicate request, foreign order, partial failure and stale worker.
- **Manual tests:** Finance/operations approve scenarios for unpaid, transfer-reported, verified, printed and dispatched orders.
- **Explicit acceptance criteria:** No stock is released until the approved settlement check passes; replay returns the same outcome and audit history remains.
- **External credentials / services:** Approved cancellation/refund and reservation-review policy; no real cancellation/payment operation in tests.
- **Dependencies / blockers:** Founder/finance rules for eligibility, pending transfer reconciliation and fulfillment cutoff.

<a id="task-5-3b"></a>

##### 5.3B — Financial-dispute review and refund-policy decision

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.3.

- **Existing verified dependency:** `5.3`, `5.5`, `5.6`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Complete immutable financial-dispute review and decide refund scope; do not promote optional money-moving automation to a mandatory feature.
- **Existing implementation to reuse:** Normalized payment states, append-only reviews, duplicate settlement protection, order/QR guards and holds.
- **Missing behavior:** Case-linked finance dispute decisions, fulfillment/entitlement consequences and a written approved-or-disabled refund policy.
- **Backend / endpoint changes:** Approve bounded financial dispute-review contracts reusing the settlement service; no direct status editor. Refund execution/provider disbursement is excluded until optional O-06 is approved.
- **Frontend pages / changes:** 5.7E displays dispute/request/history and the approved outcome; refund execution controls stay absent unless separately approved and implemented.
- **Database / migration:** Review append-only dispute/decision references and uniqueness; never overwrite the original approved payment review or manufacture refund settlement evidence.
- **Security and privacy:** Finance plus current MFA/recent authentication, approved separation of duties, exact Decimal amounts and idempotence.
- **Automated tests:** Dispute versus dispatch/reprint races, duplicate review, wrong-role decisions, rollback and disabled-refund negative tests.
- **Manual tests:** Finance/legal approve synthetic dispute cases, settlement evidence and whether refunds remain disabled or require a separately scoped implementation.
- **Explicit acceptance criteria:** Disputes have authorized auditable review and approved downstream rules. Refund eligibility/channel/authority is documented or explicitly disabled; no real funds move in this task.
- **External credentials / services:** Finance/legal policy owner and approved dispute/settlement evidence; no bank/provider write credential needed for review.
- **Dependencies / blockers:** Dispute authority/downstream rules and refund policy decision; optional execution is O-06 and is not silently added to mandatory launch scope.

<a id="task-5-3c"></a>

##### 5.3C — Authoritative finance reconciliation and suspicious-reference queries

**Status:** TODO · **Phase placement:** Phase 5, after original 5.3.

- **Existing verified dependency:** `5.3`, `5.5`, `5.6`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Expose actionable settlement inconsistencies from PostgreSQL without trusting Sheets or screenshots.
- **Existing implementation to reuse:** Exact verified settlements, keyed reference dedupe, payment reviews, order allocation and finance_sheet_sync.
- **Missing behavior:** Bounded oldest-first exception/read projections for review backlog, repeated references and ledger-versus-workflow mismatches.
- **Backend / endpoint changes:** Approve narrowly scoped finance reconciliation/count DTOs; reuse API-240/241 and do not create a second payment writer.
- **Frontend pages / changes:** 5.7E finance queue and 5.7B metrics consume these projections; include safe reason codes and as-of time.
- **Database / migration:** Review supporting indexes/projections; no raw bank-data replication, silent repairs or new payment provider.
- **Security and privacy:** Finance+MFA; reporting must not expose full bank identifiers, medical/profile data, unprotected evidence links or keys.
- **Automated tests:** Amount/reference/order mismatch fixtures, duplicate joins/counting, role denial, read-only behavior and query bounds.
- **Manual tests:** Finance compares synthetic exceptions with independent fixture ledger evidence; no real payment initiation.
- **Explicit acceptance criteria:** Each exception has a documented predicate and permitted remediation path; Sheets outage never changes authoritative state.
- **External credentials / services:** Approved finance reconciliation rules and manual bank-evidence process; automated bank feeds are not assumed.
- **Dependencies / blockers:** Finance approves exception definitions and aging thresholds; suspicious matches remain review signals, not automatic rejection.

**Placement group: after original Task 5.4.**

<a id="task-5-4a"></a>

##### 5.4A — Controlled manufacturing batch export and credential custody

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.4.

- **Existing verified dependency:** `3.1`, `3.5`, `5.4`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Complete missing API-093 batch production transport, distinct from the verified customer order PDF renderer.
- **Existing implementation to reuse:** API-090 sealed generation payloads, existing pair QA, locked render assets, private grants and print worker fencing.
- **Missing behavior:** Approved printer delivery, sealed credential-insert custody, batch export/re-export authority and release records.
- **Backend / endpoint changes:** API-093 with bounded durable jobs, MFA, encrypted receipts and explicit printer authorization; no plaintext secret recovery.
- **Frontend pages / changes:** 5.7D batch export status/release metadata; existing order-job download UI is reused only where semantics match.
- **Database / migration:** Inspect whether batch export/approval records need an additive migration; preserve all QR URLs, credentials and generated batch history.
- **Security and privacy:** Credential plaintext never reaches ordinary admin tables, logs, browser storage or public assets. Re-export must follow approved sealed-insert custody.
- **Automated tests:** Export replay, stale lease, wrong printer/role, partial upload, secret canaries and exactly-two-tags/count manifests.
- **Manual tests:** Approve artwork/fonts/native copy, physical batch scan/packaging and printer custody using disposable specimens.
- **Explicit acceptance criteria:** A batch can be exported and reconciled without re-minting QR identity or exposing credentials; physical release still requires 6.4.
- **External credentials / services:** Approved artwork/template bundle, printer public key/custody, materials and authorized physical/provider tests.
- **Dependencies / blockers:** Printer transport/approval protocol, credential custody, template/font/native copy and physical release decisions.

**Placement group: after original Task 5.5.**

<a id="task-5-5a"></a>

##### 5.5A — Admin shipment/order query contract completion

**Status:** IMPLEMENTED · **Phase placement:** Phase 5, after original 5.5.

- **Existing verified dependency:** `5.3`, `5.4`, `5.5`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Make fulfillment discoverable without requiring operators to know an order/shipment UUID.
- **Existing implementation to reuse:** API-081/232/233/235/095/096, immutable shipping snapshots and 0018 eligibility guard.
- **Missing behavior:** Bounded cross-order shipment list/detail and sorting/filter DTOs where existing order projections are insufficient.
- **Backend / endpoint changes:** Implement canonical API-080 as appropriate with 5.7E; proposed shipment GET list/detail paths require Doc 04 review, as flagged by UI §11.3.
- **Frontend pages / changes:** 5.7G reuses current ready-to-ship/shipment forms and adds discovery/deep links.
- **Database / migration:** Reuse shipments, shipment_pairs, order snapshots and indexes; never widen finance shipping-address access.
- **Security and privacy:** Operations+MFA; authorized finance order read remains masked and cannot gain packing or shipment write capabilities.
- **Automated tests:** Status/date paging ties, returned/exception packages, forbidden roles, stale shipment transitions and safe address projections.
- **Manual tests:** Trace synthetic order→package→tracking→delivery/return through existing APIs and query pages.
- **Explicit acceptance criteria:** Queues and details agree with canonical states and eligibility; no public tracking address leak or duplicate shipment.
- **External credentials / services:** Approved carrier/delivery-evidence policy for actual dispatch acceptance; no carrier action is authorized here.
- **Dependencies / blockers:** Approve missing shipment read contracts; preserve existing API-095/096 state vocabulary.

**Implementation/evidence (2026-10-19):** Added `backend/app/api/v1/fulfillment_queries.py`, registered in the existing application: typed canonical API-080 order list and proposed API-246/247 shipment list/detail. Doc 04 amendment documents exact fields, roles, filters, cursors and errors before exposure. Operations receives bounded shipment summaries/current 0018 eligibility; finance receives only the explicit common order metadata projection. Timestamp+UUID paging uses existing cursor validation; pair detail is UUID-paged. Exact filters, aware half-open date ranges, stable ties, returned/exception packages, package counts without item fanout and no-store responses are covered. No address/contact/customer identifier, QR token, storage/bank/evidence field or packed-by identity is added. Existing audited API-081 address read and API-095/096 writers/guards remain unchanged. Every route reuses genuine signed JWT/live session, email, JWT+session AAL and explicit role checks; representation SQL also checks the current explicit role. No inherited superadmin capability.

**Focused verification:** `tests/integration/test_fulfillment_queries.py`: **4 PASS in 598.80s**, one clean real-PostgreSQL run using existing UUID-isolated guarded/commerce fixtures, synthetic signed Auth/JWKS and metadata-only settlement/QA/artifact rows (no payment/provider/object or physical acceptance). Covers both paging directions/ties, filters/date boundaries, exact decimals, finance masking, safe package/pair projection, read-only row fingerprints, anonymous/support/security_admin/superadmin/finance denials, AAL mismatch, expired live session/revoked role, invalid queries/missing detail, live eligibility loss and unchanged API-096 stale 412/ineligible 409 behavior without mutation or receipt. Rehearsal installed metadata/row preservation and owned schema/NOLOGIN-role cleanup assertions passed. Scoped Ruff lint/format, diff checks and typed OpenAPI IDs PASS, including existing API-095/096. Fresh read-only installed head remains `0019_retention_recovery`; owner active roles exactly finance+operations. No migration, grant or ignored-env change. No frontend change, so no frontend rebuild/typecheck/browser rerun. Refreshed only the verified local API process; configured app stays http://localhost:3031 / API 8030. App/API liveness 200; all three new reads anonymous 401. A transient upstream catalog connection timeout recovered: canonical public catalog 200 on a later bounded check; an external DNS diagnostic was rejected before execution and replaced with local OS DNS/TCP checks.

**Remaining acceptance gate:** Owner review/approval of the proposed API-246/247 metadata contract, plus the specified manual synthetic order→package→tracking→delivery/return trace through query pages when Task 5.7G supplies those pages. Automated read/guard evidence is complete; this is IMPLEMENTED, not VERIFIED. Actual carrier/delivery-evidence policy and dispatch acceptance remain separate; no carrier action, real Auth change, role/factor/credential mutation, email/payment/Sheets/storage write/deletion, worktree, commit, push or deployment. Stop before another task.

**Placement group: after original Task 5.6.**

<a id="task-5-6a"></a>

##### 5.6A — Actual masked Google Sheets configuration and acceptance

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.6.

- **Existing verified dependency:** `5.3`, `5.6`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Close the real-provider gate for the existing durable mirror, not replace PostgreSQL as payment storage.
- **Existing implementation to reuse:** Approved-flag guard, stable-key RAW upserts, provider retries/fencing, finance sync state and safe projections.
- **Missing behavior:** Approved spreadsheet/tab/header/service-account sharing contract and controlled live acceptance/reconciliation.
- **Backend / endpoint changes:** Configure existing adapter only through secret management; document exclusive mirror-range ownership, quotas and operator handling of duplicates/schema conflicts.
- **Frontend pages / changes:** 5.7L shows lag/errors and authorized retry; no bank-data editing/import from Sheets.
- **Database / migration:** No schema migration expected; retain authoritative sync jobs/audit and reviewed monotonic export semantics.
- **Security and privacy:** Share only the dedicated reporting sheet; no full bank IDs, signed/private URLs, medical/location or activation secrets in cells/logs.
- **Automated tests:** Retain existing outage, lost-ack, stale-worker and permanent-permission-failure tests; add approved real tab/header contract check.
- **Manual tests:** Explicitly authorized dedicated synthetic worksheet write/upsert/retry and finance row-by-row reconciliation; never incidental edits to the real finance sheet.
- **Explicit acceptance criteria:** Real permissions, masking, stable-key recovery and freshness are evidenced; outages preserve payment/allocation/shipment truth.
- **External credentials / services:** Existing SAFERETURN_GOOGLE_SHEETS_* variables, service-account JSON, Sheets API and spreadsheet/tab approval; secrets never pasted into this plan/chat.
- **Dependencies / blockers:** PRD12-DEC-08 mapping/sharing and live-write authorization; SAFERETURN_GOOGLE_SHEETS_APPROVED remains false until accepted.

<a id="task-5-6b"></a>

##### 5.6B — Approved object retention activation and orphan reconciliation

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.6.

- **Existing verified dependency:** `5.3`, `5.4`, `5.5`, `5.6`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Activate distinct PDF/evidence policies safely and reconcile abandoned uploads without deleting unknown objects.
- **Existing implementation to reuse:** 0019 deletion intent, authoritative Storage absence checks, tombstones, holds, lease fencing and immutable history.
- **Missing behavior:** Signed separate policy approvals, scheduler deployment, bounded orphan inventory/quarantine and reconciliation of ambiguous uploads/deletes.
- **Backend / endpoint changes:** Reuse existing approved-policy scheduler/recovery; design orphan admission and exact-key ownership proof before any remote delete.
- **Frontend pages / changes:** 5.7L exposes policy/version/deadline/hold/recovery metadata; no arbitrary object browser/delete button.
- **Database / migration:** Rehearse any additional orphan inventory state; no bulk retention deadline assignment or object erasure without explicit scope.
- **Security and privacy:** Delivery, reconciliation, active work, formal holds and late-intent rules remain authoritative; never infer ownership from a filename alone.
- **Automated tests:** Upload/finalization crash, active download/reprint, hold/delete race, stale worker, remote uncertainty and repeated delete using fresh disposable objects.
- **Manual tests:** Legal/finance/operations approve distinct durations and a synthetic retention/recovery drill; document caches/backups separately.
- **Explicit acceptance criteria:** Only approved, due, reconciled test-owned objects are deleted; all core transactional/QR/audit history and recovery evidence survive.
- **External credentials / services:** Separate PDF and payment-evidence approval references and existing private Storage access; message/account policies belong to 5.7K.
- **Dependencies / blockers:** PRD12-DEC-05/06, review/grace/late-upload/orphan policy and explicit live disposable-object authorization; no periods invented.

**Placement group: after original Task 5.7.**

<a id="task-5-7a"></a>

##### 5.7A — Shared protected admin shell and role-aware landing

**Status:** IMPLEMENTED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `2.1`, `2.2`, `5.1`, `5.3`, `5.4`, `5.5`, `5.6`, `5.7`.
- **Additional dependencies:** [2.3A](#task-2-3a).
- **Objective:** Provide the missing /admin entry and one operational navigation system over existing verified modules.
- **Existing implementation to reuse:** Current products/payments/print-job/ready-to-ship/shipments pages, same-origin relays and explicit backend role/MFA guards.
- **Missing behavior:** Admin layout, role-aware post-login landing, capability-filtered sidebar, breadcrumbs, responsive drawer and shared state components.
- **Backend / endpoint changes:** Approve minimal staff capability/session DTO with explicit per-action permissions; backend remains authoritative on every request.
- **Frontend pages / changes:** /admin shell and security entry; embed existing routes unchanged where possible. Add links only when a permitted implemented page exists.
- **Database / migration:** Read existing roles/session state; no role grant, new broad Auth access or migration expected.
- **Security and privacy:** Customer/anonymous denial, current MFA, exact-Origin writes, no permission based only on hidden links; multi-role users keep both role sets.
- **Automated tests:** Every role/route/expired-MFA/revoked-role combination, direct URL/RSC denial, CSRF and safe return paths.
- **Manual tests:** Keyboard, 320/375/768/1440px and English/Urdu RTL checks across all existing pages and shared navigation.
- **Explicit acceptance criteria:** One sign-in/valid MFA opens a coherent console; operations+finance sees the union of explicitly granted capabilities without becoming superadmin.
- **External credentials / services:** Existing Supabase Auth only; real account/MFA use remains owner-controlled.
- **Dependencies / blockers:** 2.3A and approved capability contract. Do not replace existing working forms or infer role hierarchy.

**Implementation evidence (2026-10-18):** `/admin` provides a shared staff workspace with permitted implemented modules only, responsive sidebar/dialog menu, active navigation, breadcrumbs, loading/error/empty/forbidden states and English/Urdu RTL. Existing catalog/payment/fulfillment/print-detail modules are reused; each page checks current backend capability before rendering its module (not only in a layout). Security remains reachable at AAL1. `/auth/continue` revalidates provider/session and routes customer → account, staff AAL1 → MFA → console, staff AAL2 → console; signed activation and password-recovery precedence remain intact. Doc 04 extends the existing staff-security DTO with four explicit capabilities; operations+finance gets their union, security_admin/superadmin get catalog only unless separately granted other roles. No new business endpoint/metric, runtime grant or migration.

**Focused verification:** 17 bootstrap/capability unit cases PASS. First isolated PostgreSQL run: three API/guard cases PASS (live capability matrix for all five roles + combined roles, signed/live AAL mismatch, expired/revoked role/session; existing explicit-role/session-subject guards); browser failed only on an ambiguous test selector matching Next's route announcer (overall 1 failed/3 passed, 284.61s). That run also passed 10 frontend capability/landing cases and seven existing MFA action/Origin/return cases. Corrected selector; browser-only isolated rerun PASS (230.65s including rehearsal/cleanup, browser 2.0min), without repeating passing API/unit cases. Browser demonstrates synthetic login → invalid code denial → successful MFA → combined-role console, existing modules, all five roles × five module URLs/RSC requests, revoked-role/customer denial, no browser storage, 320/375/768/1440px, mobile Escape/focus restoration and English/Urdu RTL. English/Urdu screenshots in `frontend/test-results/staff-console-en.png` and `staff-console-ur.png` visually inspected. Production frontend build, final typecheck and scoped Ruff lint/format PASS; no frontend linter configured, no frontend-lint pass claimed. No full suite.

**Runtime/preservation:** Rebuilt/restarted only the identified local SafeReturn frontend/API at `http://localhost:3031` / API 8030, using unchanged ignored configuration. New MFA route responds 200; anonymous staff-security API 401, API liveness 200. Read-only check confirms owner roles exactly finance+operations and installed `0019_retention_recovery`; rehearsal teardown verified installed metadata/table counts/runtime roles/catalog unchanged and removed only its UUID schemas/NOLOGIN roles. No real factors/credentials/role grants modified, no real emails/payments/Sheets/storage writes/deletion, worktree, commit, push or deployment.

**Local login runtime correction (2026-10-18):** The first 5.7A refresh incorrectly launched plain `next start`; `frontend/.env.local` contains no server Auth/API configuration, so login returned service unavailable before contacting Supabase. Restarted through existing `frontend/scripts/run-configured.py`, which loads only its Auth/signing allowlist from unchanged ignored `backend/.env` and strips database/worker/migration URLs. Launcher now forwards optional Next CLI arguments to preserve host/port. Runtime uses web origin `http://localhost:3031`, API origin `http://127.0.0.1:8030`, bound to 127.0.0.1:3031. Actual Chromium login action with intentionally invalid fields reaches validation instead of unavailable (no provider login); frontend→API health 200. Scoped launcher Ruff lint/format PASS. No rebuild or real-account action required; owner login remains manual.

**Remaining acceptance gate:** Owner-controlled real/disposable staff MFA/login acceptance from 2.3A, plus manual module-level keyboard/screen-reader/responsive and native Urdu review. Synthetic provider evidence does not substitute for real MFA acceptance. Both 2.3A and 5.7A remain IMPLEMENTED, not VERIFIED. Stop before 5.7B or another follow-up until separately requested.

<a id="task-5-7b"></a>

##### 5.7B — Real dashboard overview, counts, trends and actionable exceptions

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`.
- **Additional dependencies:** [5.7A](#task-5-7a), [2.3C](#task-2-3c), [3.5A](#task-3-5a), [5.3C](#task-5-3c), [5.5A](#task-5-5a).
- **Objective:** Build ADM-01 with permission-checked PostgreSQL metrics and links to real queues.
- **Existing implementation to reuse:** Existing operational tables/services and metric definitions in this plan; use server aggregation, not all-page client fetches.
- **Missing behavior:** Typed bounded aggregation, as-of/lag/error states, charts and role-scoped queue summaries.
- **Backend / endpoint changes:** PROPOSED bounded summary/trend DTO after contract approval; group queries by permission, fixed time range/timezone and documented counting unit.
- **Frontend pages / changes:** /admin cards, real charts, actionable warnings, partial-widget failures and filtered drill-downs; unknown is never shown as zero.
- **Database / migration:** Inspect EXPLAIN/indexes and only necessary restricted aggregate helpers; no blanket Auth SELECT or unsanctioned analytics warehouse.
- **Security and privacy:** Aggregate counts are protected; unauthorized metrics/series are omitted and browser payloads contain no private fields.
- **Automated tests:** Known synthetic cardinalities, fan-out/duplicate/late-event cases, role scopes, time boundaries, outages and query limits.
- **Manual tests:** Compare each chart/card to fixture SQL and finance/ops interpretation; screen-reader/chart-table and RTL checks.
- **Explicit acceptance criteria:** Every displayed number satisfies the metric register, has freshness and a permitted drill-down; no invented revenue, scan tracking or provider health.
- **External credentials / services:** No new credential; finance/security approve metric meaning, data access and relevant alert thresholds.
- **Dependencies / blockers:** Metrics/role-contract approval; unresolved policy-dependent net-refund metrics remain unavailable.

<a id="task-5-7c"></a>

##### 5.7C — Admin user directory and safe account-case screens

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`.
- **Additional dependencies:** [5.7A](#task-5-7a), [2.3C](#task-2-3c).
- **Objective:** Allow approved staff to find and inspect safe account state and linked cases.
- **Existing implementation to reuse:** 2.3C metadata APIs, existing account and support/audit records; no customer medical/profile editor.
- **Missing behavior:** User list/detail filters, paging, verification/status summaries and case links.
- **Backend / endpoint changes:** Consume 2.3C read contracts. Add 2.3D mutation controls only after its separate approval/completion.
- **Frontend pages / changes:** PROPOSED /admin/users and /admin/users/[userId]; role-filtered safe fields, case/audit links and clear unavailable states.
- **Database / migration:** No extra user copy or role migration expected.
- **Security and privacy:** Case-specific support access, security-only high-risk actions; no raw contact/location/medical data or direct credential reset.
- **Automated tests:** Search ties, protected direct URLs, field projection, role changes during paging and disabled unauthorized actions.
- **Manual tests:** Support/security review least-necessary account data and escalation copy on synthetic users.
- **Explicit acceptance criteria:** Permitted staff can find users and linked reviews; absence of suspension/recovery approval cannot be bypassed through UI or API.
- **External credentials / services:** No new provider credential; real suspension/recovery needs explicit case authorization.
- **Dependencies / blockers:** 2.3C; 2.3D remains a separate blocker for mutations, not a reason to fake completed recovery.

<a id="task-5-7d"></a>

##### 5.7D — Inventory, generation, batches and QR lifecycle admin screens

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `3.1`.
- **Additional dependencies:** [5.7A](#task-5-7a), [3.5A](#task-3-5a), [3.5B](#task-3-5b).
- **Objective:** Connect existing generation/QA and new safe inventory queries into usable operations pages.
- **Existing implementation to reuse:** API-090/094, 3.5A read APIs, 3.5B status/history and existing print/QA service components.
- **Missing behavior:** Inventory list/detail, batch list/new/detail, low-stock state and case-linked lifecycle controls.
- **Backend / endpoint changes:** Reuse API-084/085/090–094 and approved lifecycle APIs; never create a second allocation or QR-generation writer.
- **Frontend pages / changes:** /admin/inventory, /admin/inventory/[pairId], /admin/batches, /admin/batches/new, /admin/batches/[batchId], /admin/qa/[pairId].
- **Database / migration:** No new inventory model; preserve exactly-two current children, sealed generation output and reservation/allocation history.
- **Security and privacy:** Operations+MFA, security-only suspension and approved replacement/export; no plaintext activation secret in table or client storage.
- **Automated tests:** Concurrent generation, zero/low stock, scoped batch history, role/CSRF negatives, failed QA and deep-link tests.
- **Manual tests:** Synthetic batch creation/read/QA with measured copy counts; keyboard/RTL; no real physical release.
- **Explicit acceptance criteria:** An operator can discover inventory and use approved operations from the console; blocked 3.5C/5.4A actions stay unavailable.
- **External credentials / services:** Existing generation/printer keys only for separately authorized tests; physical release remains gated.
- **Dependencies / blockers:** Replacement and manufacturing export depend separately on 3.5C/5.4A; do not mark those gates complete with this UI.

<a id="task-5-7e"></a>

##### 5.7E — Unified order search, payment review queue and reconciliation UI

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `5.3`, `5.5`.
- **Additional dependencies:** [5.7A](#task-5-7a), [5.3C](#task-5-3c).
- **Objective:** Remove manual-ID-only administration while preserving the verified settlement writer.
- **Existing implementation to reuse:** API-081/240/241, current FinanceForm, attachment read safeguards and order snapshots.
- **Missing behavior:** Canonical API-080/082 discovery and filters, oldest-first finance queues and full safe order/payment histories.
- **Backend / endpoint changes:** Implement approved list contracts and make legacy API-083, if retained, a compatibility delegate to API-241, never a separate reviewer.
- **Frontend pages / changes:** /admin/orders, /admin/orders/[orderId], existing /admin/payments and canonical payment detail deep links.
- **Database / migration:** Use current order/payment/review records and reviewed indexes; immutable review/snapshot constraints remain.
- **Security and privacy:** Operations and finance see different detail fields; finance+MFA alone reviews settlement, evidence retrieval remains audited and no-store.
- **Automated tests:** Queue ties, stale review, exact amount/currency, duplicate references, CSRF, role/IDOR and settlement/dispatch races.
- **Manual tests:** Finance/operations trace synthetic review/rejection/more-info and filtered queues; verify bilingual errors and independent bank assertion.
- **Explicit acceptance criteria:** Permitted staff can find and act on real queue records; finance actions use existing transactional rules; optional cancellation/refunds remain gated.
- **External credentials / services:** Approved bank instructions and reconciliation rules; no real payment or refund authorization.
- **Dependencies / blockers:** 5.3A/B govern cancellation/refunds; those unsupported actions stay disabled rather than silently editing status.

<a id="task-5-7f"></a>

##### 5.7F — Cross-order print queue, QA and controlled reprint console

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `5.4`.
- **Additional dependencies:** [5.7A](#task-5-7a), [3.5B](#task-3-5b).
- **Objective:** Make the existing per-job print workflow discoverable and recoverable across orders.
- **Existing implementation to reuse:** API-233–237, canonical /admin/print-jobs/[jobId], protected grants and durable render worker.
- **Missing behavior:** Global print-job search/list, failure/QA aging, safe retained/tombstoned artifact state and authorized reprint entry.
- **Backend / endpoint changes:** PROPOSED bounded global print list/count contract; reuse existing enqueue/download/QA services and eligibility checks.
- **Frontend pages / changes:** Proposed /admin/print-jobs list plus current detail page; expose frozen version/current QR validation and reasoned reprint.
- **Database / migration:** Existing jobs/artifacts/QA/grants; indexes only if measured; no token or template reminting.
- **Security and privacy:** Operations+MFA and current entitlement; never download private PDFs/credentials through public links or browser storage.
- **Automated tests:** Dead/stale job, deleted artifact, frozen reprint, role/CSRF, grant expiry/single-use and QR revoked during download.
- **Manual tests:** Synthetic render/download/QA/reprint drill; confirm physical QA boxes are never pre-approved.
- **Explicit acceptance criteria:** An operator can find failed/ready/QA jobs and safely recover an eligible artifact; printing stays disabled without approved assets/physical gates.
- **External credentials / services:** Existing private Storage and approved test bundle; real printing remains subject to 5.4A/6.4.
- **Dependencies / blockers:** Global read-contract approval; a successful development PDF is not retail artwork approval.

<a id="task-5-7g"></a>

##### 5.7G — Integrated fulfillment, packing and shipment discovery UI

**Status:** IMPLEMENTED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `5.5`.
- **Additional dependencies:** [5.7A](#task-5-7a), [5.5A](#task-5-5a).
- **Objective:** Connect verified packing/dispatch operations to coherent discoverable queue/detail pages.
- **Existing implementation to reuse:** Current ready-to-ship/shipments UI and API-081/232/095/096.
- **Missing behavior:** Approved shipment list/detail navigation, filters, exception/returned handling and package timeline integration.
- **Backend / endpoint changes:** Consume 5.5A read contracts; all writes continue through the verified fulfillment service.
- **Frontend pages / changes:** Existing /admin/ready-to-ship and /admin/shipments plus reviewed /admin/shipments/new/[shipmentId] deep links where needed.
- **Database / migration:** No new fulfillment state machine; preserve shipment membership, frozen addresses and immutable packing evidence.
- **Security and privacy:** Operations+MFA; finance has no full shipping view or dispatch write; legal/reconciliation pauses remain visible.
- **Automated tests:** Queue/detail consistency, stale next-state form, duplicate package, returned/exception paths and forbidden role.
- **Manual tests:** Synthetic package→packed→dispatch→delivery/return flow; keyboard/mobile/RTL and carrier/tracking validation.
- **Explicit acceptance criteria:** No operator must guess an ID or fabricate a shipment state; dispatch cannot bypass payment/current QR/physical QA gates.
- **External credentials / services:** Carrier/delivery policy for live acceptance; no real dispatch or notification is authorized.
- **Dependencies / blockers:** 5.5A query contract and existing physical/provider release approvals.

**Implementation (2026-10-19):** Owner approved the documented API-246/247 metadata-only scope in this task. Reviewed Doc 04 shipment amendment, Doc 11 ADM-12/13/14, Doc 07 role/privacy constraints, Task 5.5A queries, existing admin/MFA shell and fulfillment writers. `/admin/shipments` now discovers every package independently with exact order/carrier/tracking, status/review/date/sort filters and bounded cursor pages. Filters persist in the URL. `/admin/shipments/[shipmentId]` has validated fixed local navigation, recorded milestone timestamps, bounded pair packing evidence and terminal exception/returned handling; no inferred delivery/exception timestamps. Ready-to-ship cards link to actual package IDs; existing creation/packing service is reused. No migration, grant, carrier integration or new writer.

**Guard preservation:** Existing protected admin shell/capability/session/AAL checks and live backend explicit operations guards remain. Relay GET allowlist accepts only approved metadata parameters, bounded pair-detail queries and existing audited order-address retrieval; rejects external paths, duplicate query keys and unapproved reads. Metadata detail contains no address/contact/QR token/private evidence. Address disclosure is explicit, transient UI state through audited API-081 only. Every mutation uses verified API-095/096, request idempotency and expected stored state. Packing confirmation remains unchecked; current eligibility failure hides outbound options while allowing exception/return. A 409/412 refreshes canonical detail for review rather than silently advancing or replaying a changed command. Finance receives no shipping-address or dispatch capability; owner operations+finance preserved.

**Focused evidence (2026-10-19):** `pytest tests/test_fulfillment_validation.py -q`: **9 PASS, 2.27s**. `pytest tests/integration/test_fulfillment_queries.py -q -p no:cacheprovider --tb=line` with the existing ignored development environment: **4 PASS, 328.18s**; exact list/detail consistency, stable tied paging/filter boundaries, finance-only projections, forbidden explicit roles/session/AAL/revocation, returned/exception metadata, current eligibility and stale/ineligible 412/409 writes. Existing rehearsal cleanup and installed metadata/catalog preservation assertions passed. Initial sandbox connection attempt failed before setup; approved network retry produced this passing result. Frontend `npm run typecheck` and `npm run build` PASS, including the new dynamic detail route; scoped Ruff service/input/test lint and wrapper formatting PASS after import formatting correction. No frontend lint script is configured. Read-only installed check: `0019_retention_recovery`, owner roles exactly `finance,operations`.

**Writer/browser evidence:** With `SAFERETURN_CHECKOUT_BASE_REVISION=0019_retention_recovery`, `pytest tests/integration/test_shipment_discovery.py -q -s -p no:cacheprovider --tb=line --basetemp=../tmp/task57g-browser-2` completed **5 writer PASS / 1 browser FAIL, 851.75s**. Writer passes: exact membership/address and duplicate-package/idempotency concurrency; ordered physical packing/tracking/dispatch/delivery and stale 412; exception cannot bypass dispatch and can return; audited operations address read with finance address/create denial; refunded payment pauses outbound while permitting exception/return. Browser failure was the test's outdated `/account` login expectation; the existing protected staff flow correctly landed at `/admin`. Corrected only that expectation and reran only the browser: same command with `-k test_shipment_discovery_browser --basetemp=../tmp/task57g-browser-3` **1 PASS / 5 deselected, 443.05s**, nested Playwright **1 PASS, 1.7m test / 1.8m run**, bounded at 240s. No clean six-case run is claimed, and passing writers were not repeated. The successful flow covered anonymous denial, real synthetic signed staff login, queue creation/deep link, list/detail consistency, no address auto-disclosure, duplicate 409, concurrent-update stale-form 412 with canonical refresh, tracking, dispatch→exception→returned, terminal action removal, exact returned/order filtering, keyboard field focus, empty localStorage, external-path denial, mobile overflow and Urdu document direction. Both rehearsals completed their installed metadata/catalog and owned-fixture cleanup assertions. An earlier missing-fixture-import wrapper attempt exited before DB setup/browser execution. No full suite or live provider run.

**Visual evidence/limit:** Inspected `frontend/test-results/task57g-discovery-mobile.png` and `frontend/test-results/task57g-detail-rtl.png`. English mobile shows the returned package and filter layout without horizontal overflow, while a refresh was still pending. Urdu shows the RTL shell/detail loading state, not loaded package content; do not claim loaded RTL detail or native-copy acceptance from this capture. This is recorded as a remaining manual gate, without repeating the passing browser flow merely for screenshots. Final configured frontend home and liveness HTTP 200; configured runtime/auth settings were not restarted or changed. The tested build ran only on isolated 3100/8115. Final read-only 3031 route probe: `/admin/shipments` 200, new `/admin/shipments/00000000-0000-0000-0000-000000000001` 404 (rather than reaching its new protected route). The existing configured frontend process therefore still needs an authorized refresh to the tested build; no claim that the new detail UI is active on 3031.

**Remaining acceptance gate:** Before VERIFIED, refresh the existing configured frontend to the tested build while preserving its 3031/Auth/API configuration, then perform the Task 5.7G card’s manual synthetic package→packed→dispatch→delivery/return review, carrier/tracking validation and keyboard/mobile/RTL review. In particular, loaded Urdu package/timeline/forms and native-copy review have not been demonstrated. Automated evidence does not claim actual physical QA, carrier handoff or delivery. Live carrier/physical/provider/production acceptance remains separate. No migration is needed or requested.

<a id="task-5-7h"></a>

##### 5.7H — Notification delivery, dead-letter and template-version operations

**Status:** IMPLEMENTED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `4.4`.
- **Additional dependencies:** [5.7A](#task-5-7a).
- **Objective:** Expose safe notification operations without exposing finder content or duplicating delivery.
- **Existing implementation to reuse:** Durable outbox/attempts, lease fencing, stable provider keys and ambiguity cutoff.
- **Missing behavior:** Canonical API-101/102, safe filters/detail metadata, authorized retry and worker-lag visibility.
- **Backend / endpoint changes:** Implement bounded metadata list and audited idempotent retry; refuse active/leased or ambiguous-old sends that require manual review.
- **Frontend pages / changes:** /admin/notifications and approved detail route; receipt state separate from email state; reviewed template versions only.
- **Database / migration:** Reuse outbox/attempt history; no deletion/reset of prior attempts or new finder message on retry.
- **Security and privacy:** Explicit approved ops/security role list and MFA; support sees case-safe metadata only if separately approved.
- **Automated tests:** Concurrent retry/claim, cutoff, stale worker, provider timeout, duplicate key and response/log privacy canaries.
- **Manual tests:** Synthetic dead-letter and reviewed retry drill; any new actual email needs separate authorization under 4.4C.
- **Explicit acceptance criteria:** Staff can discover and safely recover permitted delivery failures; no automatic bulk resend or unauthorized content inspection.
- **External credentials / services:** No real Resend call for development verification; 4.4C owns live template/domain acceptance.
- **Dependencies / blockers:** Confirm retry delegation with existing worker policy; no UI template editor without O-05 approval.

**Implementation (2026-10-19):** Reviewed canonical Doc 04 API-101/102, Doc 11 ADM-18, security/privacy requirements, verified worker/recipient projection and existing role/AAL/session/admin shell. Clarified bounded exact-ID/status/cursor/attempt metadata and retry body/errors in Doc 04 before implementation; no new API endpoint or role is invented. `/admin/notifications` and validated local UUID detail use only API-101/102. Added explicit `notifications.manage` navigation capability for operations/security_admin only, never implicit superadmin, finance or support. Existing owner operations+finance grants remain untouched.

**Behavior/security:** Metadata projection omits recipient/aggregate/message IDs, email/body/location, ciphertext, provider message IDs/keys and worker identities; unknown codes map to `provider_failure`. Due age is per-event lag, not a fabricated fleet-health threshold. Provider acceptance, retry receipt, inbox receipt and item return remain distinct. Bounded attempt history is retained. Template view exposes only current code identity/fingerprint and explicitly says historical versions are unrecorded; no editor, version selection, publication or retrospective approval claim. 4.4C copy/domain review remains separate. Retry requires explicit unchecked confirmation, fixed safe reason, exact attempt count, actor-scoped idempotency and live operations/security_admin+MFA. Existing encrypted idempotency receipts are reused; SQL event/audit mutation and receipt write commit together or roll back. Original provider key, attempt count/history, recipient snapshot and existing worker fencing/cutoff stay unchanged; API never calls a provider. Active/leased/sent, unsupported, exhausted, invalid/deleted recipient/message, unrecognized failure and >=23-hour ambiguity require refusal/manual review. Stale forms refresh canonical metadata rather than blindly resend.

**Migration/application gate:** Prepared `backend/alembic/versions/0020_notification_operations.py`, parent `0019_retention_recovery`: four narrowly scoped functions, PUBLIC/anon/authenticated/worker execution revoked, only bounded metadata and guarded retry functions executable by safereturn_api. No table, raw Auth access grant, broad RLS grant, staff-role row, prior attempt or provider-key reset. Existing audit allowed keys and encrypted receipt store reused. Isolated rehearsal includes installed-0019 catalog comparison, upgrade→rollback/absence→reapply, and owned-schema/NOLOGIN-role cleanup with installed metadata/catalog preservation. Initially held unapplied pending owner authorization. **Owner explicitly approved application on 2026-10-19; exact 0020 is now committed and read back on development.** See application evidence below. No catch-all upgrade was used.

**Focused evidence:** `pytest backend/tests/test_notifications.py backend/tests/test_staff_security.py -q -p no:cacheprovider`: **37 PASS, 2.03s**, including provider timeout/network classification, idempotency-conflict classification, safe provider errors and role/MFA capability matrix. Frontend typecheck PASS. Complete isolated source build under `tmp/task57h-web` (with original proxy and synthetic configuration, no environment-file copy) PASS; configured frontend build/runtime left untouched. Initial Turbopack fixture-junction resolution failure fixed using a fixture-only workspace root; initial incomplete fixture copy was corrected to include proxy before the final build. Scoped Ruff lint/format and diff checks PASS. Initial migration rehearsal failed at SQLAlchemy literal parsing (3 setup errors, 115.79s); corrected without installed application. A five-case run then had **2 PASS / 3 FAIL, 264.83s**: metadata/role/projection and stale-worker/provider-key preservation passed; retry failed against incompatible audit lookup fields, fixed by reusing encrypted receipts and approved audit details. Only the three failed cases were retried: **2 PASS / 1 fixture FAIL, 263.29s**; concurrent same-key replay/changed-key refusal, stale count/confirmation and original-key worker acceptance PASS; nested bounded Playwright **1 PASS, 50.1s test / 51.9s run**, including discovery/detail, reviewed retry, synthetic worker acceptance, stale refresh, hostile Origin/unapproved query, finance direct URL/RSC/API denial, security-admin access, empty browser storage and loaded mobile RTL with no horizontal overflow. No clean five-case-suite pass is claimed. Remaining fixture case was corrected to satisfy existing due-retention metadata before simulating deleted message. `pytest tests/integration/test_notification_operations.py::test_cutoff_budget_recipient_and_active_refusals -q -p no:cacheprovider --tb=short`: **1 PASS, 156.19s**, covering >=23-hour cutoff, exhausted budget, deleted message/recipient eligibility, active and expired leases and missing event. All five focused cases have passing evidence across targeted runs; no single clean five-case run is claimed. Rehearsal rollback/reapply, installed metadata/catalog preservation and owned fixture cleanup assertions completed. No passing browser/worker/metadata cases were repeated merely to obtain a clean-suite claim.

**Visual/artifact evidence:** Inspected loaded RTL sent-event/attempt history at `output/task57h/loaded-rtl.png`; no automatic native-copy approval is claimed. The first browser attempt used Playwright's shared output directory and automatically removed `frontend/test-results/task57g-discovery-mobile.png` and `frontend/test-results/task57g-detail-rtl.png`. This artifact-preservation error is explicitly recorded; those screenshots are not claimed to remain available, and were not fabricated or regenerated by rerunning Task 5.7G. Its written evidence, IMPLEMENTED status and remaining gates are unchanged. Future Task 5.7H harness output is isolated at `tmp/task57h-playwright`, and screenshots live outside Playwright cleanup at `output/task57h`.

**Remaining gate:** The card's human synthetic dead-letter/reviewed-retry drill/native Urdu review. Migration 0020 application is complete; this does not satisfy manual acceptance. Migration SHA-256: `393f72dbf6b9dbffec8d855e2ac47106625aab1ec1f544ac69f316611a0b8b48`; sole code and installed head `0020_notification_operations`. Actual email/template/domain acceptance remains 4.4C and is not authorized. Task 5.7G and all its previous gates remain IMPLEMENTED/unchanged. No real credentials/roles/factors, email/delivery replay, payments/Sheets/storage writes/deletion, environment-file edits, deployment, worktree, commit or push.

**Runtime restoration (same configuration):** Final probes found 3031 and 8030 unavailable with no configured Node runtime present; these processes had not been stopped by Task 5.7H. Restored API via existing unchanged backend `.env` on 127.0.0.1:8030 (launcher PID 2744) and the complete tested source-copy build at `tmp/task57h-web` on localhost:3031 through `tmp/task57h-restore-frontend.py` (launcher PID 14956). The frontend launcher mirrors the existing run-configured Auth/signing allowlist and strips database/worker/migration configuration; origins and real credentials/factors/roles are unchanged. No notification worker, migration or real login/email was run. Final API and frontend liveness and login HTTP 200. The restored frontend is the tested build, and migration-backed operations became available following the separately approved 0020 application below; Task 5.7G is not advanced or its manual gates declared complete. Generated runtime stdout/stderr live only under tmp. This restoration is local only, not a deployment.

**Approved development application (2026-10-19, Asia/Karachi):** In response to the owner's explicit “yes do it”, ran `pytest`-independent `tests/integration/apply_notification_operations_migration.py` through the existing ignored development environment and configured migration identity. It required the exact approved SHA-256 and installed parent 0019, locked the revision row, invoked `command.upgrade(..., "0020_notification_operations")` only, and checked preservation before committing. **PASS, exit 0:** all existing public domain rows, Auth user/factor rows, staff-role rows, role memberships, table grants, table/RLS/column/index/constraint/trigger definitions and existing function bodies/ACLs unchanged. Only the four approved functions and the two API execution grants were added; PUBLIC/anon/authenticated/worker execution denial verified. Owner roles remain exactly finance+operations. Commit completed; a fresh connection read installed `0020_notification_operations` back successfully. No migration was replayed to obtain readback. Final runtime health: frontend 3031 and API 8030 HTTP 200; notification relay and backend anonymous reads 401. No event retry, notification worker/provider call, real email, credential/factor/role mutation, deployment or unrelated task. Task 5.7H remains IMPLEMENTED; prior acceptance tests were not rerun unnecessarily. The rehearsal metadata helper and scoped H fixture now recognize installed 0020 without assuming an unapplied parent baseline.

<a id="task-5-7i"></a>

##### 5.7I — Support/dispute and privacy-review case intake console

**Status:** IMPLEMENTED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`.
- **Additional dependencies:** [5.7A](#task-5-7a), [4.4B](#task-4-4b).
- **Objective:** Make existing account-deletion and abuse/dispute requests operationally reviewable.
- **Existing implementation to reuse:** support_cases, API-023 privacy case/audit marker, message flagging, order/pair references and legal holds.
- **Missing behavior:** Canonical API-097/098/099, scoped case detail, assignments, allowed transitions, encrypted notes and audited access.
- **Backend / endpoint changes:** Implement canonical queue/create/update; use filtered list detail only if contract sufficient, otherwise approve a specific detail endpoint.
- **Frontend pages / changes:** /admin/support, /admin/support/new and /admin/support/[caseId], linked account/order/pair and escalation actions.
- **Database / migration:** Inspect note/assignment/version history; add an audited additive case-event model only if needed, retaining original case/audit rows.
- **Security and privacy:** Support is case-scoped, no blanket medical/location/message read. Security-only holds; high-risk outcome requires approved authority.
- **Automated tests:** Case IDOR, closed/stale/concurrent edits, encrypted-note privacy, hold/print/delete races and assignment authorization.
- **Manual tests:** Support/security exercise synthetic abuse, ownership dispute and account privacy requests; verify audit and escalation.
- **Explicit acceptance criteria:** Every received request is findable with status/actor/history; closing a case cannot itself erase records, transfer a pair or settle payment.
- **External credentials / services:** Named support/security owners and approved SLA/escalation/copy.
- **Dependencies / blockers:** Approve detail/notes/redaction and assignment rules. Actual export/erasure is separately 5.7J/K.

**Implementation / approved scope (2026-10-19):** Owner explicitly approved redacted unassigned metadata, atomic self-claim and private detail/notes only for the assigned support agent; other agents’ cases return 404. Reassignment, security-only hold commands and high-risk resolutions remain unavailable. Doc 04 records the reviewed API-097/098/099 clarification before implementation. Exact-ID filtered discovery supplies detail without a new endpoint. Existing signed JWT/live session/email/AAL/explicit-role guards and admin shell are reused; only explicit support receives `support.manage`, with no inherited security/superadmin/finance access.

**Behavior / privacy:** `/admin/support`, `/admin/support/new`, `/admin/support/[caseId]` provide bounded filtered/cursor discovery, intake, safe local detail, revisioned claim/updates, paginated append-only history and encrypted case notes. Metadata excludes private context, notes and ciphertext/key fields. Assigned private reads are audited. Legacy API-023 reasons remain restricted even after claim; the original account-deletion audit marker remains distinguishable. Actor-scoped encrypted idempotency receipts, expected revisions, closed-case immutability, normal state transitions and high-risk/active-hold refusal are enforced server-side. Closure touches only case/history/audit/receipt records, never erasure, ownership or payment. UI has unchecked review confirmation, canonical refresh after stale/conflicting actions and no browser persistence of private data.

**Migration (APPLIED with owner approval):** Additive `0021_support_case_console` follows installed 0020: three case columns with safe legacy defaults, one RLS-protected append-only encrypted event table, three API-executable scoped functions and one non-callable finder-hold trigger function. Existing retention admission is preserved; order/pair locking serializes hold admission with case transitions, including finder-message holds. No hold-writing permission is added. SHA-256 `342fc6721d0c1af2108e82e53cb55b13d3408ccedfe1f51525f5ac932c255b12`. Owner explicitly approved this exact migration on 2026-10-19. `tests/integration/apply_support_case_migration.py` hash-checked the artifact, required installed 0020, applied only 0021 in one transaction, and committed after exact original domain/Auth user/MFA-factor value hashes, staff roles, prior DDL, table/function grants and role-membership assertions passed. Added columns were excluded only from original-value comparison; their constraints/defaults and empty RLS event table were checked separately. Fresh connection readback of head and original value hashes PASS. Installed head is now 0021; owner finance+operations unchanged. No case intake/change, provider call or worker was run during application. Scoped application-runner Ruff/format PASS.

**Evidence so far:** Corrected focused API run: 6 PASS / 1 deselected (234.06s), including roles/AAL, IDOR, metadata/private projections, legacy-reason privacy, concurrent claims/edits, encrypted notes, append-only history, idempotency, stale/terminal transitions and all three high-risk types. Initial six failures were synthetic fixture verifier wiring, corrected without weakening runtime guards. Seventeen staff-security tests PASS (1.98s); 12 navigation/contract checks PASS (1.3s). Frontend typecheck and isolated production build PASS, including proxy and all support routes. Outputs use `tmp/task57i-*`, source/build copy `tmp/task57i-web`; current `tmp/task57h-web` runtime and artifacts preserved. Final migration rehearsal/hold/browser run: 2 PASS / 6 deselected (241.66s), including transactional 0021 rollback/reapply, narrow function ACLs, order/finder hold serialization, deletion-intent admission refusal, and installed metadata/catalog preservation with owned cleanup. Earlier targeted run: 2 FAIL / 6 deselected (387.82s): hold assertions passed before an unsettled-print fixture was rejected by the existing print guard; browser timed out on exact select-label matching despite rendered form. Corrected synthetic settlement metadata and role-based combobox selectors; no production guard weakened. Six-case API evidence preceded the final finder-hold addition; updated SQL is exercised by the final targeted run, not a claimed clean combined suite. One corrected bounded browser scenario PASS (1.4m as reported): intake, queue/detail consistency, safe projection, normal closure, stale refresh/unchecked confirmation, foreign-case 404, finance URL/RSC/API denial, hostile-Origin/query rejection and loaded mobile RTL/no browser persistence. Inspected `output/task57i/loaded-rtl.png`; first failed browser artifacts preserved in `tmp/task57i-playwright-attempt1`, successful run in `tmp/task57i-playwright`; future attempts now generate unique output directories.

**Remaining gates:** Promotion of the tested local runtime while preserving configured Auth/3031; human support/security synthetic abuse, ownership-dispute and account-privacy intake/escalation/audit drill; native Urdu/accessibility and named-owner/SLA/copy acceptance. Actual export/erasure remains 5.7J/K. Tasks 5.7G/H retain their IMPLEMENTED statuses and all existing manual gates. Prior 0020 migration retained in the chain, owner finance+operations, ignored environments and localhost:3031/API8030 runtime preserved; no real provider/notification/dispatch/payment/email/Sheets/storage write/deletion or Auth changes.

<a id="task-5-7j"></a>

##### 5.7J — Reviewed data-access/export request and secure delivery

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `2.1`, `2.2`, `5.7`, `5.6`.
- **Additional dependencies:** [5.7I](#task-5-7i).
- **Objective:** Complete lawful account data access with scoped, recoverable export instead of ad hoc database dumps.
- **Existing implementation to reuse:** Privacy cases, actor/owner/recipient boundaries, encryption, private Storage and durable jobs.
- **Missing behavior:** Approved request/status/authorization/export schema, sensitive-third-party redaction and expiring delivery.
- **Backend / endpoint changes:** PROPOSED customer request/status and case-linked staff approval contracts; immutable scoped manifest and bounded retryable export worker.
- **Frontend pages / changes:** Customer privacy request/status and 5.7I reviewer controls; explicit authenticated short-lived export retrieval.
- **Database / migration:** Review durable request/artifact/receipt state and narrow RLS; no runtime Auth SELECT or generic SQL export.
- **Security and privacy:** Recent reauthentication, identity proof and case authority; filter third-party finder/contact data, secrets and credentials; audit every grant.
- **Automated tests:** Cross-user/recipient export, reused/expired grant, interrupted worker, key/provider failure, legal hold and redaction canaries.
- **Manual tests:** Legal/security approve a synthetic manifest and delivery/download/expiry drill.
- **Explicit acceptance criteria:** Only the approved subject's allowed records are delivered, with completeness/redaction evidence and no raw secret leakage.
- **External credentials / services:** Approved identity-proofing/export scope, encrypted object storage and separate export-expiry policy.
- **Dependencies / blockers:** Legal/security authority, third-party data boundaries, delivery/expiry policy and new request/download contracts.

<a id="task-5-7k"></a>

##### 5.7K — Reviewed account/message erasure and backup-aware privacy execution

**Status:** BLOCKED · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `5.6`.
- **Additional dependencies:** [5.7I](#task-5-7i).
- **Objective:** Complete the explicitly deferred erasure workflow while retaining mandatory legal/payment/QR/audit history.
- **Existing implementation to reuse:** API-023 reviewed requests, hidden message requests, holds, durable jobs, deletion-intent/tombstone lessons and audit.
- **Missing behavior:** Identity/authority review, staged data classification, approved message/account policies, backup/cache treatment and recovery.
- **Backend / endpoint changes:** PROPOSED approval/status/execution services after legal review; idempotent bounded plans and reconciliation, never direct auth.users cascade-delete.
- **Frontend pages / changes:** Case-linked reviewer approvals, customer-safe status and truthful delayed/held outcomes; no claim of irreversible erasure while backups exist.
- **Database / migration:** Forward migration likely for execution/checkpoint/policy approval history; preserve pair and purchase references and append-only evidence.
- **Security and privacy:** Security/legal authority plus MFA/recent reauth; active jobs, disputes, legal holds and original-recipient data constrain every step.
- **Automated tests:** Concurrent hold/erase, active export/print/delivery, partial remote failure, stale worker, rollback/retry and redaction/history preservation.
- **Manual tests:** Authorized synthetic erasure/restore drill; legal sign-off on key retirement, backups, vendor caches and retained records.
- **Explicit acceptance criteria:** Approved data is erased or explicitly retained with reason; a request never implies instant account deletion and repeated execution is safe.
- **External credentials / services:** Legal/finance retention authority, key/backup custody and approved provider erasure procedures.
- **Dependencies / blockers:** No account/message erasure policy, timeline, retained-history mapping or backup/legal approval has been granted.

<a id="task-5-7l"></a>

##### 5.7L — Finance mirror and storage/retention administration UI

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `5.6`.
- **Additional dependencies:** [5.7A](#task-5-7a).
- **Objective:** Expose verified finance-sync/retention operations as usable role-scoped console modules.
- **Existing implementation to reuse:** API-238/239/242–245 and their existing role/MFA/audit/deletion-intent rules.
- **Missing behavior:** Finance sync and metadata-only storage pages, filters, retry/hold confirmations and safe exception timelines.
- **Backend / endpoint changes:** Reuse existing endpoints; review strict per-resource metadata scoping without widening the original grants.
- **Frontend pages / changes:** /admin/finance/sheet-sync and /admin/storage with status, as-of, approval/reference metadata and authorized reasoned actions.
- **Database / migration:** No new storage/finance model or migration expected; no direct provider-object browsing or irreversible-delete shortcut.
- **Security and privacy:** Finance retries; approved ops/finance metadata only; security/superadmin alone place/release holds or recover cleanup under existing guards.
- **Automated tests:** Role matrix, MFA, stale/duplicate retry, pending intent/late hold conflict, no private URL and CSRF/browser-storage tests.
- **Manual tests:** Synthetic sync failure/hold/release/recovery workflow in English/Urdu; no real Sheet/object mutation.
- **Explicit acceptance criteria:** Operators see actionable exceptions and only allowed controls; actual policy/provider gates stay visible and fail closed.
- **External credentials / services:** 5.6A/B own actual Sheet/retention configuration; no new credentials for UI development.
- **Dependencies / blockers:** Metadata review and shared shell; no UI approval flag may activate an unapproved retention policy.

<a id="task-5-7m"></a>

##### 5.7M — Restricted audit and security-event search

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `2.1`, `5.7`.
- **Additional dependencies:** [5.7A](#task-5-7a).
- **Objective:** Provide searchable immutable operational evidence without a generic audit-data dump.
- **Existing implementation to reuse:** Append-only audit_events and existing safe details, request IDs and privileged read audits.
- **Missing behavior:** Canonical API-100 bounded search/filter/paging and role/case-scoped event timelines.
- **Backend / endpoint changes:** Implement reviewed projections; action/actor/time/target filters, approved sorting and no raw reason/ciphertext blanket export.
- **Frontend pages / changes:** /admin/audit plus case/order links where explicitly authorized; safe event labels and separate security exceptions.
- **Database / migration:** Existing audit indexes first; no audit update/delete or unrestricted SQL interface.
- **Security and privacy:** Security/superadmin roles explicitly authorized, MFA/recent auth for sensitive retrieval; ordinary ops/finance/support receive only approved contextual events.
- **Automated tests:** Role/IDOR, pagination ties, log/response canaries, injection filters, immutable events and query-plan bounds.
- **Manual tests:** Security reviews synthetic timelines and confirms sensitive details/URLs never appear.
- **Explicit acceptance criteria:** Permitted events are findable, immutable and attributable; no hidden full-profile or medical disclosure through audit search.
- **External credentials / services:** No new provider credential; security approves field allowlist and audit access/retention.
- **Dependencies / blockers:** Contextual role delegation and sensitive event projection require review; no superadmin permission inheritance is assumed.

<a id="task-5-7n"></a>

##### 5.7N — System, integration and worker health console

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`, `1.1`, `4.4`, `5.4`, `5.6`.
- **Additional dependencies:** [5.7A](#task-5-7a).
- **Objective:** Show actionable operational status without exposing credentials or offering arbitrary configuration execution.
- **Existing implementation to reuse:** Liveness/restricted readiness, durable jobs/outbox, safe error codes and deployment/runbook artifacts.
- **Missing behavior:** Approved operational status DTO, queue/lease/lag metadata, freshness/unknown states and backup-evidence references.
- **Backend / endpoint changes:** PROPOSED internal role-protected status contract; bounded checks, no send/payment/delete side effects and no provider calls on every page/readiness probe.
- **Frontend pages / changes:** Proposed /admin/system with API/DB/job/Resend/Cloudinary/Turnstile/Sheets/private Storage status, alerts and runbook links.
- **Database / migration:** Reuse queue/attempt state; add only reviewed narrow health/heartbeat metadata if required. 6.3A supplies deployed worker observations.
- **Security and privacy:** Explicit operations/security read scope; never display env values, service-account JSON, credentials, raw logs or SQL. Safe config editing remains O-05.
- **Automated tests:** Unconfigured/idle/stale/provider-down states, role denial, timeout bounds and secret-canary tests.
- **Manual tests:** Simulated outages and stale backup/worker evidence; verify unknown never becomes a green healthy badge.
- **Explicit acceptance criteria:** Configured, observed healthy, unavailable, stale and unconfigured are distinct; liveness 200 is not provider readiness or proof of a backup.
- **External credentials / services:** Existing provider metadata/config only; actual monitoring/alerts and provider acceptance remain release gates.
- **Dependencies / blockers:** Approve health projection, visibility, observation windows and alert ownership/thresholds; no automatic vendor configuration changes.

<a id="task-5-7o"></a>

##### 5.7O — Complete customer privacy history and request-status navigation

**Status:** TODO · **Phase placement:** Phase 5, after original 5.7.

- **Existing verified dependency:** `5.7`.
- **Additional dependencies:** None beyond the verified foundations.
- **Objective:** Extend the verified minimal privacy UI without misrepresenting recorded historical consent as current permission.
- **Existing implementation to reuse:** API-022's explicit recorded_event semantics, API-023 case marker and current settings/help/account forms.
- **Missing behavior:** Full stable pagination beyond latest 100, safe request-status read and approved customer links to 5.7J/K.
- **Backend / endpoint changes:** Review additive cursor/status contracts; original actor scoping remains. Do not reconstruct missing old contact identity or infer inherited consent after transfer.
- **Frontend pages / changes:** Settings/privacy history, accessible purpose labels, pending/held/closed request state and support escalation links.
- **Database / migration:** Reuse immutable events/cases; if future consent-subject detail is needed, add versioned new evidence rather than rewriting historical events.
- **Security and privacy:** Subject-only access, no staff notes or third-party reasons in customer status, same-origin writes and no browser storage.
- **Automated tests:** More-than-100/tied events, original actor after ownership change, foreign status request, stale cursor and historical-state labelling.
- **Manual tests:** Customer/support review privacy wording, multilingual keyboard/mobile paths and no false completion promises.
- **Explicit acceptance criteria:** Users can traverse their full available history and see accurate safe request state; unapproved export/erasure actions stay disabled.
- **External credentials / services:** No new provider credential; legal/native copy approval for release.
- **Dependencies / blockers:** Status/paging contract review; 5.7J/K approval is required before exposing execution/delivery controls.


### Phase 6 — Integration, deployment preparation and release checks
**Outcome:** Deployable application matching the approved release criteria.

- Integrate frontend/backend/database and verify real critical workflows.
- Address accessibility, responsive behavior, basic observability, essential security, deployment configuration and documented acceptance gates.
- Treat unresolved approved logo/font/artwork decisions and unavailable source references as explicit release gates, not reasons to stop unrelated development.
- Do not deploy to production without authorization.

**Done when:** agreed tests pass, remaining release blockers are explicit, and deployment instructions are reproducible.


#### New follow-ups in this phase (2026-10-18 revision)

Original task IDs and their evidence remain unchanged. Cards below are new work, grouped after the milestone they extend. All new contracts are proposals until reviewed; this planning request authorizes no implementation.

**Placement group: after original Task 6.1.**

<a id="task-6-1a"></a>

##### 6.1A — Reproducible cross-domain and admin regression automation

**Status:** TODO · **Phase placement:** Phase 6, after original 6.1.

- **Existing verified dependency:** `1.5`, `3.5`, `5.7`.
- **Additional dependencies:** `6.1`.
- **Objective:** Make approved customer and new admin workflows repeatable in CI after their individual development acceptance.
- **Existing implementation to reuse:** Existing focused PostgreSQL/Playwright tests, exact preservation runners and current quality workflow.
- **Missing behavior:** A bounded CI fixture/runtime strategy, current-head integration coverage and new-admin role/MFA/race journeys.
- **Backend / endpoint changes:** No new business writer; review CI database provisioning and service/worker test orchestration.
- **Frontend pages / changes:** Exercise 5.7A–O implemented routes using synthetic Auth/providers; no new feature UI.
- **Database / migration:** Ephemeral synthetic schemas/NOLOGIN roles or disposable CI DB with the real Alembic chain; exact cleanup/preservation must be proved.
- **Security and privacy:** No production DB secret or managed Auth fixture seeding; no real payment/email/Sheet/object writes in default CI.
- **Automated tests:** Critical journeys, all explicit roles, AAL/revocation, transaction failure, duplicate requests, provider outages, stale workers and leakage checks.
- **Manual tests:** Reviewer reproduces commands on the supported Linux/runtime stack and inspects clean evidence rather than counts alone.
- **Explicit acceptance criteria:** CI has a reviewed source of test DB/runtime configuration, bounded runs and honest skips/interruption reporting; no clean full-suite claim from partial runs.
- **External credentials / services:** Approved CI secrets/test environment or ephemeral database service; no production provider credentials.
- **Dependencies / blockers:** Run after applicable new modules are individually accepted; keep original 6.1 status and criteria intact.

**Placement group: after original Task 6.2.**

<a id="task-6-2a"></a>

##### 6.2A — Measured API/frontend capacity and performance acceptance

**Status:** TODO · **Phase placement:** Phase 6, after original 6.2.

- **Existing verified dependency:** `1.5`, `5.2`, `5.5`.
- **Additional dependencies:** [5.7A](#task-5-7a), [5.7B](#task-5-7b), [5.7N](#task-5-7n).
- **Objective:** Establish production-relevant latency, throughput and resource evidence without inventing SLOs.
- **Existing implementation to reuse:** Existing bounded APIs, query indexes, liveness/readiness and privacy-safe logging.
- **Missing behavior:** Approved workloads/budgets, representative synthetic data volume, aggregation/queue plans and mobile performance measurements.
- **Backend / endpoint changes:** Measure public QR, auth, checkout, finance/queue queries and worker throughput; tune only demonstrated bottlenecks in a later scoped change.
- **Frontend pages / changes:** Measure public scan and admin table/chart payloads, hydration/navigation and mobile constrained-network behavior.
- **Database / migration:** EXPLAIN/bounded connection/lock tests; index changes need reviewed migrations and preserved data.
- **Security and privacy:** No real load against production or abuse-provider endpoints; load fixtures contain no real PII and no raw token metrics.
- **Automated tests:** Synthetic load, p50/p95/p99, query/lock/connection budgets, worker backlogs and frontend resource checks with reproducible parameters.
- **Manual tests:** Approve budgets, devices, data size, concurrency and cost ceiling; compare observed results against those approved values.
- **Explicit acceptance criteria:** Recorded measured values meet signed budgets or block launch; missing budgets/results cannot pass as healthy.
- **External credentials / services:** Authorized staging/load environment, representative synthetic dataset and owner-approved SLO/cost targets.
- **Dependencies / blockers:** Budget and staging load authorization; no arbitrary pass thresholds or vendor SLA assumptions.

**Placement group: after original Task 6.3.**

<a id="task-6-3a"></a>

##### 6.3A — Separate worker/scheduler deployment and operational readiness

**Status:** TODO · **Phase placement:** Phase 6, after original 6.3.

- **Existing verified dependency:** `1.4`, `4.4`, `5.4`, `5.6`.
- **Additional dependencies:** [5.7N](#task-5-7n).
- **Objective:** Turn existing one-shot worker CLIs into reviewed deployable services with safe scheduling and visibility.
- **Existing implementation to reuse:** Dedicated restricted worker DB URL, lease-fenced notification/print/finance/retention CLIs and API container/runbook.
- **Missing behavior:** Independent service commands, scheduler ownership, graceful drain, bounded concurrency, heartbeat/lag observations and alert routing.
- **Backend / endpoint changes:** Define Linux/native-font/render and provider timeout compatibility; preserve API/worker separation and deployment-safe payload versions.
- **Frontend pages / changes:** Feed factual deployed observations to 5.7N; no simulated green health or browser-run workers.
- **Database / migration:** No automatic schema migration at service startup; if heartbeat state is needed, use a narrow reviewed helper/table and no business-role privilege widening.
- **Security and privacy:** Secrets injected server-side, isolated worker identities, no fallback to admin/API credentials, retention disabled without approvals.
- **Automated tests:** Process kill/restart, deploy/drain, stale claim, double scheduler, retry exhaustion, queue fairness and safe log/metric tests.
- **Manual tests:** Explicitly authorized staging worker/scheduler rollout, failure alerts and rollback exercise; no production daemon started by this plan.
- **Explicit acceptance criteria:** Workers recover safely and alarms reach named owners; disabled jobs/policies stay disabled, and deployments cannot overlap incompatibly.
- **External credentials / services:** Authorized Railway/staging services, provider credentials where approved, approved fonts/assets and alert recipient.
- **Dependencies / blockers:** Service/scheduler/concurrency and monitoring approval; 6.3 retains its deployment acceptance obligations.

<a id="task-6-3b"></a>

##### 6.3B — Cross-service disaster recovery, private-object restore and key custody

**Status:** BLOCKED · **Phase placement:** Phase 6, after original 6.3.

- **Existing verified dependency:** `1.5`, `5.4`, `5.6`.
- **Additional dependencies:** [5.7K](#task-5-7k).
- **Objective:** Prove recoverability beyond a database backup badge, including private artifacts, encryption keys and privacy holds.
- **Existing implementation to reuse:** Migration/rollback rehearsals, immutable specs/tombstones, storage reconciliation and deployment/incident runbooks.
- **Missing behavior:** Approved RPO/RTO, backup custody, isolated restoration, key availability/rotation and recovery of worker/hold state.
- **Backend / endpoint changes:** Document and rehearse safe rehydration/reconciliation, reprint eligibility and prevention of duplicate provider sends after restore.
- **Frontend pages / changes:** 5.7N links to signed restore evidence/freshness only; never shows backup objects, keys or an unrestricted restore button.
- **Database / migration:** Restore only into an authorized isolated target; preserve identities/constraints/audits and reconcile DB versus provider object/tombstone state.
- **Security and privacy:** No backup copy into ordinary development without data authorization; least-privilege keys, audited custody and no secrets in reports.
- **Automated tests:** Synthetic DB/object restore integrity, key-version round trip, expired grant invalidation, worker replay and held-data preservation.
- **Manual tests:** Database/security owners conduct full isolated restore and timed cutover/rollback; verify private objects and key custody separately from PITR.
- **Explicit acceptance criteria:** Measured recovery meets approved RPO/RTO and proves object/key/lease/hold reconciliation; cannot claim erasure while recoverable backups remain under policy.
- **External credentials / services:** Authorized backup/PITR/object backup environment, key escrow/custody, recovery operators and approved privacy/retention policy.
- **Dependencies / blockers:** RPO/RTO, backup access and restore authorization, key custody and 5.7K backup-aware policy. No actual restore is authorized in this request.


## 4. Development task division and progress

Execute tasks by the dependency graph within the phase catalogue, preserving original IDs and verification scope. Task 2.3 remains IMPLEMENTED: signup/sign-in are user-confirmed, while confirmation/recovery/password-change browser acceptance remains unverified. Phase 3 is complete. Tasks 4.1–4.4 are VERIFIED for development; Phase 4 is DONE for development, with production release gates retained. Tasks 5.1–5.7 remain VERIFIED for development in their original scope. New follow-ups are listed in the owning phases; 2.3A and 5.7A are now IMPLEMENTED with interactive acceptance gates; further follow-ups need separate authorization. Dummy credentials belong only in isolated tests; runtime sensitive operations remain fail-closed. Preserve uncommitted work; no worktrees, deployment, destructive domain changes, commit or push.

| Phase | Practical implementation tasks in dependency order |
| --- | --- |
| 0 — Foundation | **0.1:** Runnable FastAPI configuration + API-001/002 health + tests. **0.2:** Next.js/TypeScript/Tailwind app with approved bilingual layout, local run/build. **0.3:** Typed API transport and local frontend/backend integration. |
| 1 — Database | **1.1:** SQLAlchemy 2/psycopg session lifecycle and real DB readiness. **1.2:** Alembic identity/pair/QR/credential/profile schema and exactly-two current-tag constraints. **1.3:** Catalog, immutable orders/QR uses, reservations, payment and fulfillment schema. **1.4:** Messaging, encrypted location, audit, durable outbox/jobs/intent schema and least-privilege/RLS. **1.5:** PostgreSQL migration/constraint/race verification. |
| 2 — Authentication | **2.1:** Supabase JWT validation and account/role/ownership guards. **2.2:** Signup/login/session frontend and account APIs. **2.3:** Auth integration and negative authorization tests. |
| 2 — New follow-ups (not complete) | **[2.3A](#task-2-3a):** Staff MFA enrollment, verification and secure recovery entry (IMPLEMENTED); **[2.3B](#task-2-3b):** Controlled staff onboarding, role grants and revocation policy (BLOCKED); **[2.3C](#task-2-3c):** Safe staff user-directory and account-state read APIs (TODO); **[2.3D](#task-2-3d):** Account suspension/restoration and recovery escalation (BLOCKED) |
| 3 — QR management | **3.1:** Secure paired inventory generation and credential handling. **3.2:** Scan intent and atomic entitlement-bound activation/idempotency. **3.3:** Independent Lost/ICE profile APIs, versioning and consent. **3.4:** Multiple-pair dashboard/editors and activation return flow. **3.5:** Cross-owner, rollback and concurrency integration checks. |
| 3 — New follow-ups (not complete) | **[3.5A](#task-3-5a):** Admin inventory and batch read/query foundation (IMPLEMENTED); **[3.5B](#task-3-5b):** Owner disable/history and paired security lifecycle commands (TODO); **[3.5C](#task-3-5c):** Approved damaged/compromised tag replacement workflow (BLOCKED) |
| 4 — Public scans | **4.1:** Safe anonymous QR projections and bilingual scan pages. **4.2:** Protected ICE reveal and opt-in WhatsApp. **4.3:** Finder message + optional consented location + atomic notification outbox. **4.4:** Durable email worker/retries and phone-sized privacy/accessibility checks. |
| 4 — New follow-ups (not complete) | **[4.4A](#task-4-4a):** Live Turnstile and trusted-proxy abuse acceptance (BLOCKED); **[4.4B](#task-4-4b):** Canonical public abuse reporting and moderation intake (TODO); **[4.4C](#task-4-4c):** Approved notification templates and live deliverability acceptance (BLOCKED); **[4.4D](#task-4-4d):** Public policy/configuration and support-channel completeness (TODO) |
| 5 — Remaining features | **5.1:** Admin catalog/variants/public assets + dynamic featured storefront. **5.2:** Decimal quotes, independent copy counts, immutable checkout/address + exclusive reservations. **5.3:** Private payment evidence + manual finance review and exactly-once allocation. **5.4:** Approved branded QR/vector PDF jobs and private download/print QA. **5.5:** Fulfillment/orders/copies UI + admin operations. **5.6:** Asynchronous masked Sheets mirror, retention/legal holds and recovery. **5.7:** Remaining approved account/inbox/help/settings screens and acceptance coverage. Future non-sticker products/gateway features remain disabled until approved. |
| 5 — New follow-ups (not complete) | **[5.1A](#task-5-1a):** Catalog administration completion and actual public-image acceptance (TODO); **[5.2A](#task-5-2a):** Saved shipping-address CRUD and checkout selection (TODO); **[5.3A](#task-5-3a):** Customer cancellation requests and controlled reservation release (BLOCKED); **[5.3B](#task-5-3b):** Financial-dispute review and refund-policy decision (BLOCKED); **[5.3C](#task-5-3c):** Authoritative finance reconciliation and suspicious-reference queries (TODO); **[5.4A](#task-5-4a):** Controlled manufacturing batch export and credential custody (BLOCKED); **[5.5A](#task-5-5a):** Admin shipment/order query contract completion (TODO); **[5.6A](#task-5-6a):** Actual masked Google Sheets configuration and acceptance (BLOCKED); **[5.6B](#task-5-6b):** Approved object retention activation and orphan reconciliation (BLOCKED); **[5.7A](#task-5-7a):** Shared protected admin shell and role-aware landing (IMPLEMENTED); **[5.7B](#task-5-7b):** Real dashboard overview, counts, trends and actionable exceptions (TODO); **[5.7C](#task-5-7c):** Admin user directory and safe account-case screens (TODO); **[5.7D](#task-5-7d):** Inventory, generation, batches and QR lifecycle admin screens (TODO); **[5.7E](#task-5-7e):** Unified order search, payment review queue and reconciliation UI (TODO); **[5.7F](#task-5-7f):** Cross-order print queue, QA and controlled reprint console (TODO); **[5.7G](#task-5-7g):** Integrated fulfillment, packing and shipment discovery UI (IMPLEMENTED); **[5.7H](#task-5-7h):** Notification delivery, dead-letter and template-version operations (IMPLEMENTED); **[5.7I](#task-5-7i):** Support/dispute and privacy-review case intake console (TODO); **[5.7J](#task-5-7j):** Reviewed data-access/export request and secure delivery (BLOCKED); **[5.7K](#task-5-7k):** Reviewed account/message erasure and backup-aware privacy execution (BLOCKED); **[5.7L](#task-5-7l):** Finance mirror and storage/retention administration UI (TODO); **[5.7M](#task-5-7m):** Restricted audit and security-event search (TODO); **[5.7N](#task-5-7n):** System, integration and worker health console (TODO); **[5.7O](#task-5-7o):** Complete customer privacy history and request-status navigation (TODO) |
| 6 — Integration/release | **6.1:** Real end-to-end critical workflows and failure recovery. **6.2:** Responsive/RTL/accessibility and security acceptance. **6.3:** Deployment configuration, observability, backup/rollback checks. **6.4:** Physical QR/artwork/font/Urdu/provider release gates and pilot acceptance; no production deployment without authorization. |
| 6 — New follow-ups (not complete) | **[6.1A](#task-6-1a):** Reproducible cross-domain and admin regression automation (TODO); **[6.2A](#task-6-2a):** Measured API/frontend capacity and performance acceptance (TODO); **[6.3A](#task-6-3a):** Separate worker/scheduler deployment and operational readiness (TODO); **[6.3B](#task-6-3b):** Cross-service disaster recovery, private-object restore and key custody (BLOCKED) |

Task states: TODO / IN PROGRESS / IMPLEMENTED / VERIFIED / BLOCKED. Phase completion requires all relevant tasks and acceptance checks; a verified bootstrap does not complete Phase 0.

### Task count and status register

**Current roadmap: 70 tasks across the same 7 phases. VERIFIED: 26; IMPLEMENTED but unverified: 12; IN PROGRESS: 0; TODO: 19; BLOCKED: 13. Remaining not VERIFIED: 44.**

**Original baseline retained:** 31 tasks, 26 VERIFIED for development, 5 IMPLEMENTED (2.3, 6.1–6.4). **New:** 39 tasks, none VERIFIED (7 IMPLEMENTED, 19 TODO, 13 BLOCKED). Optional decisions O-01–06 are not tasks and are excluded from totals. Counts measure task records, not equal effort or production readiness. Original verified implementations are not downgraded by new prerequisites.

| Phase | Total | VERIFIED | IMPLEMENTED | IN PROGRESS | TODO | BLOCKED | Original IDs / new follow-ups |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 — Foundation | 3 | 3 | 0 | 0 | 0 | 0 | Original 0.1, 0.2, 0.3; no additions |
| 1 — Database | 5 | 5 | 0 | 0 | 0 | 0 | Original 1.1, 1.2, 1.3, 1.4, 1.5; no additions |
| 2 — Authentication | 7 | 2 | 2 | 0 | 1 | 2 | Original 2.1, 2.2, 2.3; new [2.3A](#task-2-3a), [2.3B](#task-2-3b), [2.3C](#task-2-3c), [2.3D](#task-2-3d) |
| 3 — QR management | 8 | 5 | 1 | 0 | 1 | 1 | Original 3.1, 3.2, 3.3, 3.4, 3.5; new [3.5A](#task-3-5a), [3.5B](#task-3-5b), [3.5C](#task-3-5c) |
| 4 — Public scans | 8 | 4 | 0 | 0 | 2 | 2 | Original 4.1, 4.2, 4.3, 4.4; new [4.4A](#task-4-4a), [4.4B](#task-4-4b), [4.4C](#task-4-4c), [4.4D](#task-4-4d) |
| 5 — Remaining features/admin | 31 | 7 | 5 | 0 | 12 | 7 | Original 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7; new [5.1A](#task-5-1a), [5.2A](#task-5-2a), [5.3A](#task-5-3a), [5.3B](#task-5-3b), [5.3C](#task-5-3c), [5.4A](#task-5-4a), [5.5A](#task-5-5a), [5.6A](#task-5-6a), [5.6B](#task-5-6b), [5.7A](#task-5-7a), [5.7B](#task-5-7b), [5.7C](#task-5-7c), [5.7D](#task-5-7d), [5.7E](#task-5-7e), [5.7F](#task-5-7f), [5.7G](#task-5-7g), [5.7H](#task-5-7h), [5.7I](#task-5-7i), [5.7J](#task-5-7j), [5.7K](#task-5-7k), [5.7L](#task-5-7l), [5.7M](#task-5-7m), [5.7N](#task-5-7n), [5.7O](#task-5-7o) |
| 6 — Integration/release | 8 | 0 | 4 | 0 | 3 | 1 | Original 6.1, 6.2, 6.3, 6.4; new [6.1A](#task-6-1a), [6.2A](#task-6-2a), [6.3A](#task-6-3a), [6.3B](#task-6-3b) |
| **Total** | **70** | **26** | **12** | **0** | **19** | **13** | Original IDs/statuses preserved; all 39 new cards above |

The original unverified tasks remain 2.3 and 6.1–6.4. New task readiness, field-level contracts, decisions and production gates are separate. The previous stop-before-6.1 instruction remains historical; no implementation begins during this documentation request.

### Phase 4 implementation file register for later verification

Tasks **4.1–4.4 and 5.1–5.7 are VERIFIED for development** by the evidence below. Other tasks follow the status register; their implementations remain unverified. Recheck their files, apply only scoped authorized migrations, and run required acceptance before changing status.

| Task | Implemented files | Later recheck focus |
| --- | --- | --- |
| 4.1 | `backend/alembic/versions/0012_public_qr_projection.py`; `backend/app/api/v1/public_qr.py`; `backend/app/main.py`; `backend/tests/test_health.py`; `frontend/app/q/[token]/page.tsx`; `frontend/app/globals.css`; `backend/README.md` | VERIFIED: API allowlist/status/privacy, transactional migration rollback/retry and applied 0012, 8 real browser checks including bilingual/RTL and initial HTML/RSC privacy |
| 4.2 | `backend/alembic/versions/0013_public_contact_actions.py`; `backend/app/api/v1/public_contacts.py`; router composition in `public_actions.py`; `backend/app/core/turnstile.py`; settings; `test_public_contacts.py`, `test_turnstile.py`, runtime login checks; public action/challenge components and scan page; `.env.example`; READMEs | VERIFIED scoped development behavior: locked publication/membership/consent rechecks, committed budgets, server-verified bound single-use proof, AES-GCM decryption, 38 integration cases + 16 browser checks across focused runs, 12 actual restricted-login checks. Live keys/provider smoke and any founder-approved emergency fallback remain release gates |
| 4.3 | `backend/alembic/versions/0014_public_finder_messages.py`; `backend/app/api/v1/public_actions.py`; `backend/app/main.py`; `backend/tests/test_health.py`; `frontend/app/q/[token]/finder-message.ts`; `frontend/components/finder-message.tsx`; `frontend/app/q/[token]/page.tsx`; `frontend/app/globals.css`; `backend/README.md` | VERIFIED for development: explicit consent, encryption, committed peer/QR budgets, bound single-use Turnstile, atomic outbox/retry rollback and concurrent idempotency. 12 integration checks, 3 browser checks, 14 restricted-login checks and 146 local tests; applied only 0014. Live provider acceptance remains a release gate |
| 4.4 | `backend/alembic/versions/0014a_notification_delivery.py`; `backend/app/workers/notifications.py`; notification local/integration/live tests; runtime-login tests; `frontend/components/finder-message.tsx`; `frontend/tests/notification-privacy.spec.ts`; `backend/README.md` | VERIFIED for development: 17 integration checks across focused runs, 6 browser checks, 16 restricted-login checks, 159 local tests and one live Resend test with user-confirmed receipt. Applied only 0014a; production release gates remain |
| 5.1 | `backend/alembic/versions/0015_public_catalog.py`; `backend/app/api/v1/catalog.py`; `backend/app/main.py`; `frontend/lib/catalog.ts`; `frontend/app/page.tsx` | VERIFIED for development: applied only 0015 after rollback/retry rehearsal; canonical API-200–202/220–229, versioned audited operations/MFA writes, verified asset association, publication gates, concurrent retries, immutable snapshots, English/Urdu storefront and admin browser checks. Live Cloudinary/upload and physical/configuration gates remain |
| 5.2 | `backend/alembic/versions/0016_checkout_quotes.py`; `backend/app/api/v1/checkout.py`; `backend/app/main.py`; `backend/tests/test_health.py`; `backend/README.md` | VERIFIED for development: only 0016 applied after rollback/retry rehearsal; 17 integration, 7 browser, 20 restricted-login and 192 local checks PASS. Decimal frozen quotes/address, copy counts, expiry, idempotency, exclusive one-pair reservation, future-reuse ownership and rollback verified; approved commercial/physical configuration remains gated |
| 5.3 | `backend/app/api/v1/payments.py`; `backend/app/integrations/payment_storage.py`; payment tests; `frontend/components/payments.tsx`; payment pages/relay; `backend/README.md` | VERIFIED for development: 9 integration checks including 4 browser checks and live private Storage upload/finalize/denial/cleanup; 20 restricted-login and 205 local tests; no migration required, installed head remains 0016 |
| 5.4 | `0017_print_download_grants.py`; printing API/worker, `print_render.py`, `print_storage.py`; print tests; `/admin/print-jobs/[jobId]` and relay | VERIFIED for development: scoped 0017 applied after rollback/retry, 11 focused integration scenarios including live private PDF acceptance and 3 canonical-route browser checks, 22 restricted-login and 213 local tests; physical/artwork approvals remain release gates |
| 5.5 | `0018_fulfillment_eligibility.py`; `fulfillment.py`; allocation status correction in `payments.py`; fulfillment/runtime/validation tests and `ops/verify-task55.py`; customer order pages; `/admin/ready-to-ship`, `/admin/shipments` and relay; `fulfillment-admin.tsx`, `order-status.ts`; local launcher/docs | VERIFIED for development: 19 unique integration scenarios across focused runs, 5 browser checks, 24 actual restricted-login and 222 local tests; scoped 0018 installed after real rollback/retry; exact existing data/roles/DDL preserved |
| 5.6 | `backend/app/api/v1/retention.py`; `backend/app/workers/finance_retention.py`; `backend/app/main.py`; `backend/app/core/config.py`; `backend/tests/test_health.py`; `backend/README.md` | VERIFIED for development: scoped 0019, finance/retention recovery and lease fencing, 15 focused integration functions, three browser checks, disposable private Storage acceptance and exact installed preservation; actual Sheet and retention approvals remain gates |
| 5.7 | `backend/app/api/v1/messages.py`; `account.py`; inbox/account local and integration tests; `frontend/app/inbox-actions.ts`; customer inbox/settings; public `frontend/app/help/page.tsx`; `frontend/proxy.ts`; `frontend/tests/inbox.spec.ts`; API contract/README | VERIFIED for development: original-recipient isolation after synthetic ownership change, tied pagination, encrypted location/reason, held-message hiding, concurrent legal hold and request retry, consent history and reviewed deletion requests; four focused DB/API integration cases, two browser checks, 26 actual restricted-login regressions and 261 local tests |
| 6.1 | `backend/tests/integration/test_critical_workflows.py`; `backend/README.md` | Run authorized PostgreSQL rollback-only end-to-end checks for order/payment/allocation/print/QA/shipment, failed-write rollback, provider retry preservation, active retention holds, and recovery/replay behavior |
| 6.2 | `frontend/tests/release-accessibility.spec.ts`; `frontend/app/page.tsx`; `frontend/components/customer.tsx`; `frontend/app/globals.css`; `PHASE_IMPLEMENTATION.md` | Run desktop/mobile/RTL keyboard and assistive-technology acceptance, verify no horizontal overflow, focus visibility, touch targets, reduced-motion/forced-colors behavior, and unauthenticated private-content denial |
| 6.3 | `backend/Dockerfile`; `backend/.dockerignore`; `backend/railway.toml`; `backend/app/core/observability.py`; `backend/app/main.py`; `backend/app/api/auth.py`; `backend/tests/test_health.py`; `frontend/vercel.json`; `.github/workflows/quality.yml`; `ops/release-preflight.ps1`; `backend/README.md`; `frontend/README.md`; `PHASE_IMPLEMENTATION.md` | Verify staging deployment with authorized provider accounts, protected readiness, sanitized logs/alerts, backup/PITR and private-object restore drill, migration compatibility, rollback rehearsal, worker service and production smoke checks |
| 6.4 | `ops/validate-pilot-gates.py`; `ops/pilot-release-gates.example.json`; `backend/tests/test_release_gates.py`; `backend/README.md`; `PHASE_IMPLEMENTATION.md` | Record founder/print/security approval, two locked bilingual templates, font/artwork fingerprints, exact dimensions/quiet zone, real device/material scans, provider smoke evidence, and pilot sign-off; keep physical/provider gates unverified until executed |

Historical verification/implementation entries below are retained verbatim. Their dated next/stop instructions are historical; the latest handoff and dependency graph govern future work.

### Current task

- **0.1 — FastAPI backend foundation:** VERIFIED; five focused ASGI health/contract tests pass, Ruff lint/format pass, pip check passes, real Uvicorn HTTP liveness smoke passes. Readiness truthfully returns 503 until database integration.
- **0.2 — Next.js frontend foundation:** VERIFIED; production build, TypeScript check and 9 Playwright checks pass. English/Urdu server rendering and persistent language switch, responsive marketing layout, native mobile navigation/FAQ, keyboard skip link and truthful empty catalog. Screenshots reviewed at desktop English and mobile Urdu.
- **0.3 — Typed API/local integration:** VERIFIED; server-only origin/client, runtime response validation, no-store requests, timeout and safe errors; web GET /api/health/live reaches API-001. Production build/typecheck, 16 checks against real servers and backend-outage check pass. Public web readiness remains absent; no CORS or backend changes needed.
- **1.1 — Database sessions/readiness:** VERIFIED against authorized development Supabase. SQLAlchemy/psycopg lazy engine, bounded pool/timeouts, safe parameters, service transaction/read scopes, request session dependency and lifespan disposal; authenticated readiness queries SELECT 1. Real commit/rollback, returned connections and protected 200 readiness/lifecycle checks pass. No persistent schema changes.
- **1.2 — Initial identity/pair/QR/profile schema:** VERIFIED; additive Alembic revision `0001_identity_profiles` applied to authorized development Supabase after metadata inspection and rollback-only migration tests. Ten SQLAlchemy-mapped domain tables, independent Lost/ICE profiles, encrypted-field/consent checks, immutable QR identity/replacement guards, partial current-tag uniqueness, immediate parent locks and deferred exactly-two constraints. 24 new PostgreSQL checks pass; installed schema matches mappings. No API/UI implementation added.
- **1.3 — Commerce/payment/fulfillment schema:** VERIFIED; additive `0002_commerce` applied after inspecting installed metadata and testing upgrade with representative previous-revision data. Sixteen new SQLAlchemy-mapped tables, Decimal catalog/order snapshots, independent QR-copy uses, immutable placed order/address records, exclusive reservations and payment review holds, provider-independent attempts/private evidence/append-only reviews, and paid allocation/physical-QA shipment guards. 55 new PostgreSQL checks pass; all 26 domain tables are RLS protected and contain zero persistent test rows. Services/API/UI remain later tasks.
- **1.4 — Durable workflows and runtime security:** VERIFIED; additive `0003_workflows_security` and corrective `0004_runtime_privacy` applied. Fourteen mapped workflow tables, encrypted location/recipient snapshots, atomic outbox, append-only audit, idempotency/activation intents, leased jobs/print/finance/retention records, and separate restricted API/worker logins with RLS. Final suite: 181 passed, including 154 real PostgreSQL checks. No provider services or API/UI flows activated.
- **1.5 — PostgreSQL migration/constraint/race verification:** VERIFIED on development PostgreSQL 17.11. Twenty new real PostgreSQL checks rehearse the actual Alembic chain in isolated UUID namespaces with temporary NOLOGIN roles; verify populated upgrades, exact structural catalog equality, DDL failure/rollback/retry, real deferred COMMIT rejection, savepoint/client-close recovery, repeated concurrent tag retirement/replacement and last-pair reservation, exactly-once paid allocation, and outbox/job claim/reclaim/stale-ack fencing including SKIP LOCKED. Full suite: 201 passed in 626.33s, no skips or warnings (174 PostgreSQL + 27 local). Applied 0001–0004 and runtime credentials unchanged; cleanup confirms zero temporary schemas/roles and zero persistent domain rows.
- **Other tasks:** Follow the status register; later Copilot implementation notes remain unverified.
- **2.1 — Supabase JWT validation and account/role/ownership guards:** VERIFIED. Strict ES256/RS256 verifier, bounded JWKS cache, private dependencies, live account/session/email/MFA/DB-role and concealed ownership guards. Forward `0005_account_session_guard` applied after metadata inspection and rollback rehearsal. Full regression: 274 passed, two local collection-time future-timestamp failures in 778.58s; all 192 PostgreSQL/provider checks passed. Fixed timestamps to evaluate during execution; all 84 local tests then passed in 5.71s. Ruff, pip check and Alembic consistency pass; 40 RLS tables, zero domain rows/temporary objects. No Auth writes or runtime Auth SELECT grants.
- **2.2 — Signup/login/session frontend and account APIs:** VERIFIED. Approved bilingual auth/confirmation/recovery routes, maintained server-only SSR with Secure/HttpOnly/Lax cookies, exact-Origin actions, PKCE fixed callbacks, signed recovery authorization; account GET/PATCH with conditional versions and atomic minimal audit. No new migration. Evidence: 16 real PostgreSQL checks, 84 local checks, build/typecheck, 30 local web/integration checks and outage check pass. Actual confirmed development user passed live login/signature/restricted account API/refresh/local-session revocation; real browser login/account/cookies/logout-denial passed in 12.7s. Read-only browser test preserved installed metadata/domain row counts and unrelated sessions. Live signup/email/recovery delivery and broader negative matrix remain Task 2.3; no users/emails/profile edits made by live checks.
- **2.3 — Auth integration and negative authorization tests:** IMPLEMENTED; signup and sign-in browser checks are now user-confirmed working. Added 15 request-level PostgreSQL JWT/session negatives, 6 real Next callback/forged-cookie/CSRF cases and 5 controlled SDK failures. Prior evidence: 84 local backend tests, 39 web checks (4 explicit skips), 16 account PostgreSQL checks and 7 live login/security checks passed; broader corrected-clock run completed 42 cases before interruption. Earlier localhost account loading failed because the backend process had no outbound network access; restarted with restricted API database/Supabase settings, and database/JWKS reachability plus API liveness now pass. Confirmation/recovery/password-change acceptance remains unverified because the user asked to skip that manual testing; no further automatic emails or provider changes.
- **3.1 — Secure paired inventory generation and credential handling:** VERIFIED. Added API-090 with operations+current-MFA authorization, strict batch/template/ECC/material/environment/symbol-size validation, CSPRNG pair/token/credential generation, versioned keyed HMAC verifiers, printer-public-key sealed inserts, atomic minimal audit and idempotency. Forward migrations `0006_qr_batch_template` and `0007_qr_batch_environment` add nullable template/environment metadata; both were applied after inspecting installed heads, RLS, roles and inventory counts. Verification: 89 local backend tests and 7 isolated real-PostgreSQL API cases pass (generation, pair/token uniqueness, verifier/sealed-insert checks, audit, idempotent replay, duplicate label, staff/MFA denial, missing-key fail-closed and outdoor-size rejection); Ruff, compileall and OpenAPI contract checks pass. Final inspection shows head 0007, 40 RLS tables, no temporary schemas; two public domain rows (one profile and one audit) were left untouched. Local key settings are intentionally absent, so live batch creation stays fail-closed until the dedicated verifier and printer public keys are configured. No physical print/email/user-data operation performed.

- **3.2 — Scan intent and atomic entitlement-bound activation/idempotency:** VERIFIED. API-207 exposes only minimal anonymous activation context; API-208 creates a 15-minute actor-bound intent after live account/email verification and independent paid-allocation or concealed-credential proof. API-032 requires explicit confirmation and canonical actor-scoped idempotency. Fixed-search-path API-only procedures recheck entitlement/current children/inventory/credential under locks, then atomically consume intent and credential, assign owner, activate both tags, and persist minimal audit, outbox and stable idempotency decisions. Existing profile publication/consent is untouched; replay timestamps derive from immutable intent consumption. Dedicated versioned HMAC verification uses a fixed-length constant-time comparison, with committed guess accounting, credential lockout and durable account/direct-peer limits. Forward `0008_atomic_activation` and `0009_activation_rechecks` were individually metadata-inspected, rollback-rehearsed and applied; previous revisions through 0007 were preserved. Evidence: 89 local tests pass in 6.27s; final broader PostgreSQL run had 28 passes and two synthetic-order fixture failures (omitted required totals), corrected without schema changes; both corrected cases then passed in 202.92s. Thus all 22 activation cases plus 8 actual restricted-login cases are verified across focused runs, not a claimed full-suite pass. Ruff lint/format, compileall and pip check pass. Isolated-fixture cleanup confirms exact installed catalog/row-count preservation: head 0009, 40 RLS tables, two existing public domain rows unchanged, and owned temporary namespaces/roles removed. Missing verifier keys keep concealed claims fail-closed; paid-order claims do not need that key. Live reservations/allocations cannot be bypassed with a secret; allocated third-party gift claims remain gated by PRD12-DEC-04 security review. Browser continuation remains Task 3.4; deployment proxy/IP policy remains a release configuration gate. No managed Auth writes, emails, physical prints, deployment, commit or push.

- **3.3 — Independent Lost/ICE profile APIs, versioning and consent:** VERIFIED. API-040–049 now implement per-QR Lost/ICE reads/edits, masked encrypted ICE contacts and opt-in WhatsApp preferences. Verified-owner writes require quoted If-Match versions; contacts share the ICE profile version, while Lost/ICE/WhatsApp resources otherwise version independently. GET returns private defaults without creating rows; omitted update fields are preserved. Publication requires versioned consent, with signed recent AMR authentication (not refreshed JWT iat) for medical publication. Medical notes/phones use AES-256-GCM with random nonces and authenticated QR/field/contact/key-version binding. Removing a contact unpublishes and soft-removes it; privacy disabling remains available without encryption keys, with retained secrets explicitly redacted. Changes and minimal consent/publication audit commit atomically. Forward `0010_profile_consent` adds nullable contact consent/removal metadata and preference versions; `0011_profile_owner_locks` supplies an API-only ownership-rechecking lock function without widening inventory UPDATE policy. Both revisions were metadata-inspected, rollback-rehearsed and applied, preserving prior migrations, runtime roles and the two existing public domain rows. PostgreSQL failures exposed the restrictive row-lock policy and a test namespace rewriter corrupting hyphenated consent identifiers; both were corrected safely. Final evidence: 99 local tests PASS (6.10s); 29 real PostgreSQL checks PASS (21 profile/consent/encryption/rollback/race cases plus 8 actual restricted-login checks, 280.35s), no skips/warnings. Alembic schema/model check, Ruff lint/format, compileall, pip check and diff checks pass. Cleanup validates exact catalog/count preservation and removes only owned synthetic namespaces/roles. New runtime secret required: `SAFERETURN_PROFILE_DATA_KEYS` (JSON version-to-base64url independent random 32-byte keys), active `SAFERETURN_PROFILE_DATA_KEY_VERSION=1`; dummy keys were used only in isolated tests, and no real .env was changed. No new external API credential needed. Preflight observed 7,181 seconds client/database clock skew; live provider reauthentication/browser acceptance is not claimed, and no clock or JWT leeway was changed. No managed Auth/user-data edits, external messages, printing, deployment, commit or push. Next is Task 3.4; not started.

- **3.4 — Multiple-pair dashboard/editors and activation return flow:** VERIFIED. Added owner-only API-030/031/205/206 with bounded timestamp/UUID cursor paging, owner-scoped label search, type/status/publication filters, current identities, safe label/version summaries and caller-owned order-product/copy references. No schema, grant or migration change. Next routes `/dashboard`, `/my-qr`, `/my-qr/[qrId]`, `/kits`, `/kits/[pairId]`, legacy per-kit editor redirects and `/activate` support independent Lost/ICE profiles, masked contact CRUD, opt-in WhatsApp preferences, consent, conditional versions, draft summaries, unsaved-change warnings and section-level unavailable/privacy-disable controls. The minimal inactive `/q/[token]` entry preserves signed short-lived HttpOnly/Secure/Lax scan context across login/signup callback; only fixed `/activate` returns are used. Actor-bound confirmation retains one idempotency key across retries and activates both tags through the existing API-032 transaction. Concealed credentials stay in POST bodies and are not copied into cookies or redirects. Tests exposed form resets after validation and edits racing pending saves; prevented reset on error, disabled pending fields and remounted successful forms by returned versions. Isolated fixture failures from missing Chromium, Windows text encoding, ambiguous locators, assertion latency and rapid repeated-login throttling were corrected without weakening application auth/rate limits. Final evidence: 106 local backend tests PASS (6.33s); 10 final owner PostgreSQL cases PASS within a focused run whose browser wrapper initially failed; 21 profile + 8 restricted-login regressions PASS within the earlier 38-case PostgreSQL run; final isolated browser wrapper PASS (233.08s), with all 24 Playwright cases PASS (10 real Next/API/PostgreSQL browser cases, 2 ticket/transport cases, 12 simulated Auth SDK cases). Build/typecheck, Ruff lint/format, pip check, diff and secret checks PASS; English desktop and Urdu mobile screenshots reviewed. Real Auth provider, email delivery and production readiness are not claimed. User-supplied profile keyring contains a valid 32-byte key at version 1; corrected only the invalid non-secret active-version setting to `1` in ignored backend/.env and verified a synthetic AES-GCM round trip, preserving keyring bytes. Final metadata: installed head 0011, 40 RLS tables, two original domain rows, zero temporary schemas/roles; current client/database UTC skew measured 18,000 seconds. No real user/profile edits, managed Auth writes, emails, deployment, commit or push. Next: Task 3.5, not started.

- **3.5 — Cross-owner, rollback and concurrency integration checks:** VERIFIED. Added 39 real-PostgreSQL cases in `backend/tests/integration/test_phase3_integrity.py`: foreign customer/staff writes, wrong-purpose/contact-ID swaps, consent/encrypted profile/contact rollback, shared and independent version races, maximum-contact concurrency, actor-scoped activation idempotency races, audit/child/deferred-COMMIT activation rollback and retry, and ownership/dispute rechecks after actual parent-lock contention. Assertions inspect complete relevant database consequences, minimal audit/outbox and stable replay. Tests use separate actual PostgreSQL backend PIDs, bounded barriers and `pg_blocking_pids`; all synthetic faults/data remain in owned UUID rehearsal namespaces. A deterministic revocation between authorization and detail SELECT exposed an unhandled missing-row 503; owner pair details now conceal it as 404. Cold remote connections initially timed out before the race barrier; prewarming connections outside the synchronized section fixed the harness without changing application timeouts. Final combined Phase 3 regression slice: **107 passed in 1591.42s**, including all 39 new checks, 7 inventory, 22 activation, 21 profiles, 10 owner collection and 8 actual restricted-login checks; no skips. Local backend checks: **106 passed in 6.65s**. Ruff lint/changed-Python format, pip check and diff/secret checks PASS. No frontend change or new frontend acceptance claim. Metadata inspected before setup; every rehearsal verifies exact installed catalog/count preservation. No migration/grant change; head 0011, 40 RLS tables, two existing domain rows and runtime credential separation preserved; zero owned temporary schemas/roles after cleanup. Existing uncommitted Task 3.4 work and ignored .env preserved. No new credentials needed; activation/printer configuration and prior live-auth/clock/gift/proxy/physical gates remain unresolved. No managed Auth writes, real user-data edits, email, printing, deployment, commit or push. Next exact task: **4.1 — Safe anonymous QR projections and bilingual scan pages**, not started.

- **4.1 — Safe anonymous QR projections and bilingual scan pages:** VERIFIED (2026-10-16). Reviewed and corrected Copilot's unapplied 0012/API-010/page implementation without applying later tasks. Fixed ambiguous SQL token lookup, missing ICE-profile handling, unpublished/removed/unapproved-consent ICE contact disclosure, explicit response allowlists and no-store/referrer/robots headers. Added a distinct durable public-scan enumeration budget (100/direct peer/15 minutes), counting invalid/missing tokens without trusting forwarded headers or consuming activation budgets; no raw IP/token is stored in its audit event. Published medical notes remain null under the approved API-010 DTO; full phones/ciphertext/private owner/pair IDs never enter initial projection/HTML/RSC. Public page now prioritizes scan content, renders contact-only ICE profiles, retains the same scan URL on language changes and always includes visible English/Urdu critical instructions. Existing later-task UI/actions are preserved, not verified here. Evidence: **24 Task 4.1 cases PASS in 232.42s**, including **8 real Next/API/PostgreSQL browser checks**, migration DDL rollback/retry, anonymous/wrong-bearer access, safe unavailable/current-token states, publication/consent filtering, missing-profile defaults, rate denial/spoofed-forwarded-IP checks and privacy-safe outage responses. English desktop and Urdu 320px screenshots reviewed; escaped owner text does not execute. **101 focused local backend tests PASS in 7.23s**; frontend production build/typecheck, API-010 OpenAPI anonymous/closed-schema check, changed-Python Ruff lint/format, pip check and diff/secret checks PASS. Initial test-only parameter-type and browser response-capture failures were corrected; production timeouts/security rules were not weakened. Metadata inspection found head 0011, 40 RLS tables and three pre-existing domain rows before setup. After isolated rehearsal passed, applied **only 0012_public_qr_projection** transactionally to authorized development: exactly two new API-only functions; previous function definitions, table catalog, row counts and runtime role attributes unchanged. No migration through 0011 edited; 0013–0017 remain unapplied. **10 actual API/worker login checks PASS in 36.43s**, including new-function grants, API-only projection execution, denied worker contact reads, no cross-role escalation and pool-context reset. The initial worker test expected an empty result where the correct policy rejects SELECT; corrected the assertion without widening privileges. Final cleanup: 40 RLS tables, three preserved rows, zero temporary schemas/roles; current UTC skew rounds to zero, with no clock/JWT-leeway change. Existing Copilot/Phase 3 changes and ignored .env preserved. No new credentials or provider calls needed, no Auth/user-data writes, deployment, commit or push. Next exact task: **4.2 — Protected ICE reveal and opt-in WhatsApp**, not started by this agent.

- **4.2 — Protected ICE reveal and opt-in WhatsApp:** VERIFIED (2026-10-16), with explicit live-provider/configuration release gates. Reviewed and corrected Copilot's unapplied 0013 implementation. API-012/013 now use a separate bounded-JSON route and closed response DTOs, generic non-echoing errors, no-store/no-referrer headers and deliberate anonymous POST actions. Fixed ambiguous SQL token parameters and the anonymous RLS-blocked QR-ID lookup by returning only internal ciphertext/key/QR context from API-only fixed-search-path functions. Current tag state, exact ICE-contact membership, publication, recognized consent version, non-removal and WhatsApp opt-in are rechecked under row locks; ICE unavailable states return safe 409, other unavailable contacts/links remain concealed. AES-GCM AAD and strict ASCII E.164 validation prevent corrupt/misbound ciphertext from becoming a dial/link response. Independent attempt limits (20 peer / 10 peer+QR / 5 peer+QR+contact or WhatsApp, per 15 minutes) commit before challenge/membership/key failures, ignore spoofed forwarded headers and remain separate from activation/finder accounting. Server-side fixed-endpoint Turnstile checks success, configured hostname, action, hashed resource cData and five-minute token age outside DB locks; a committed proof digest prevents concurrent replay. Missing keys/provider failures do not disclose phones; no unapproved emergency fallback was introduced (Security §8.4), and initial emergency content remains readable. Frontend mounts a compact challenge only after explicit action, refreshes it after repeated identical failures, uses bilingual status/disclosure and LTR phone rendering, and offers a separate noopener/noreferrer WhatsApp link without auto-navigation or message/outbox insertion. Evidence: initial 30 PostgreSQL cases PASS (324.05s); expanded run **38 integration cases PASS** with its browser wrapper initially failing only ambiguous alert selectors (493.69s). Corrected selectors to the contact form; final focused browser wrapper **PASS in 195.33s**, with **all 16 browser checks PASS** (8 new contact flows + 8 Task 4.1 scan regressions). This is focused evidence, not a claimed coherent full-suite pass. Replay-race and both actual pg_blocking_pids lock-wait revocation cases pass. **119 local backend tests PASS (8.84s)**; build/typecheck, API-012/013 OpenAPI closed-schema/anonymous checks, changed-Python Ruff lint/format, pip check and diff/secret checks PASS. English and 320px Urdu synthetic contact screenshots reviewed. After metadata inspection and isolated DDL rollback/retry, applied **only 0013_public_contact_actions** to development: five new API-only functions and a scoped API-010 availability update; table catalog, unrelated functions, all 40 RLS tables, runtime roles and three pre-existing rows preserved. Prior migrations through 0012 remain unchanged; 0014–0017 remain unapplied. **12 actual API/worker login checks PASS (42.80s)**; zero temporary schemas/roles and no UTC skew at final inspection. Existing uncommitted/Copilot work and ignored .env preserved. New runtime configuration needed: backend `SAFERETURN_TURNSTILE_SECRET_KEY` + `SAFERETURN_TURNSTILE_EXPECTED_HOSTNAME`; frontend `NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY`. Only synthetic test configuration was used; no real values written. Controlled Siteverify/widget tests do not establish live Cloudflare acceptance, and the provider widget's language support is distinct from the bilingual application. No Resend/Meta credential, Auth/user-data write, actual message, printing, deployment, Git commit or push. Next exact task: **4.3 — Finder message + optional consented location + atomic notification outbox**, not started by this agent.

- **4.3 — Finder message, optional consented location and atomic notification outbox:** VERIFIED for development (2026-10-16). Corrected Copilot API/migration/form implementation. Canonical API-011 `/messages` and API-015 `/finder-messages` compatibility route use bounded JSON, closed receipts, non-echoing validation and no-store responses. Explicit contact consent, 10–1,000 meaningful Unicode characters, ASCII E.164 contact/selection validation and finite consented coordinates are enforced; documented nested consent and existing form fields are supported. Separate committed budgets cap 20 peer/5 peer+QR attempts per 15 minutes; fixed-endpoint Turnstile verifies hostname/action/resource/age outside DB locks and committed proof digests prevent reuse. Final current/publication/owner checks hold row locks. Encrypted message/contact/location, recipient snapshot, short-lived scoped retry record and minimal notification outbox commit together; identical/concurrent retries deduplicate, changed payloads return safe 409. Frontend preserves typed fields, resets verification, discards stale geolocation after withdrawal, permits no-location submission and has readable 320px English/Urdu forms. Final evidence: **12 integration checks PASS (349.62s)** including migration DDL rollback/retry, exact preservation of the previous projection except two finder flags, encryption, disabled states, budgets, replay, concurrent retries, injected outbox failure/recovery and browser wrapper; **3 Playwright checks PASS**, screenshots reviewed. **146 local tests PASS (7.15s)**; build/typecheck, focused Ruff lint/format and diff checks PASS. Applied **only 0014_public_finder_messages** transactionally with exact table/role/row/unrelated-function preservation: 40 RLS tables, three existing domain rows. **14 actual restricted-login checks PASS (71.58s)**, including API-only execution of the three new finder functions. Real Turnstile settings are present, values unchanged and undisclosed; Siteverify/widget tests remain simulated. No real messages/emails, Auth writes, production deployment, commit or push. Local backend 8030 and frontend 3030 health/page checks return 200. Next: **4.4 — Durable email worker/retries and phone-sized privacy/accessibility checks**; provider delivery remains unverified.

- **4.4 — Durable notification delivery and mobile privacy:** VERIFIED for development (2026-10-16). Claims and encrypted original-recipient snapshots commit before provider HTTP; completion uses a separate transaction with worker/numbered-attempt/unexpired-lease fencing. Worker-only lease-scoped helper resolves verified active Auth email without granting Auth-table reads. Stable provider idempotency keys, durable attempts, bounded jittered retries/Retry-After, dead letters and a 23-hour ambiguous-delivery manual-review cutoff cover recovery. Generic email excludes finder/contact/location/medical data. Dedicated worker-URL CLI supports one-shot operation; no daemon was started. Forward migration 0014a fixes finder parent-lock upgrade contention and freezes recipient snapshots without weakening payload immutability. Awaited frontend actions and reset prevention preserve consent/fields on failure; location remains optional and saved receipts do not promise email. Evidence: **17 integration checks across focused runs**, **6 browser checks**, **16 actual restricted-login checks**, **159 local tests**, build/typecheck, focused Ruff/format, pip and diff checks PASS. English/Urdu 320px screenshots reviewed. **One authorized live Resend test PASS; user confirmed Received.** Only 0014a applied: 40 RLS tables, three original domain rows, roles and unrelated functions preserved; isolated fixture cleanup verified. Unapplied 0015 dependency follows 0014a; 0015–0017 remain unapplied. Ignored env values unchanged; no managed Auth/customer-domain writes, deployment, commit or push. Live Turnstile, prior credential-exposure review and production/physical release gates remain. Next: **5.1**, not started.

- **5.1 — Admin catalog, variants, public assets and dynamic featured storefront:** VERIFIED for development (2026-10-16). Reviewed PRD product amendment, DB §4, API A2–A6/registry, UI storefront/admin sections, print amendment size definition, actual source and Git changes. Fixed Copilot's broken product SQL parameters, invalid migration bind syntax, slug-as-SKU resolution, hardcoded Cloudinary account and unordered/ungated projection. Canonical API-200–202/220–229 replace unapproved API-110–113 routes. Added draft/create/edit/archive, categories, variant activation/prices/template versions, approved public-image attachment/unlinking, quoted version checks, parent locking, encrypted idempotent receipts and existing minimal append-only audits. Existing operations/MFA delegation retained (plus existing security/superadmin); no role provisioning. Public reads expose only active QR-sticker configuration; future categories, QR reuse and non-sticker fulfillment remain disabled. All catalog reads use no-store, avoiding stale publication caches. Cloudinary attachment verifies the controlled folder/account, public raster upload metadata and versioned URL; missing provider configuration fails closed. Unlink never deletes a provider asset. Publishing requires verified image, QR-symbol size >=30 mm and configured approved template_key@version; this is not physical QA approval. Added `/admin/products`, URL-backed `/shop` search/category and canonical SKU detail fetching (independent of list-page limits), strict server catalog parsing, manual accessible featured scroller, empty/outage states and English/Urdu/RTL controls. **Final evidence: 11 integration checks PASS (273.23s)** including rollback/retry rehearsal, signed-JWT roles/MFA, publication/asset gates, versions, Decimal prices, archive, projection allowlists/order, concurrent idempotency/version races, immutable historical order snapshots, signed upload authorization/idempotency and browser wrapper. **All 9 final Playwright checks PASS (1.2m)** against real Next/API/isolated PostgreSQL; simulated Auth/Cloudinary only, including real browser multipart upload and server-verified attachment, authenticated CSRF rejection and detail-page outage fallback. A prior upload-caption assertion failed only because the rehearsal translates standalone schema words in fixture text; using a non-colliding synthetic caption gave the coherent final 11/9 pass. Urdu 320px/1440px screenshots reviewed; no horizontal overflow. **174 local tests PASS (8.65s)**; final production build/typecheck, focused Ruff/format, pip and diff checks PASS. Applied **only 0015** transactionally: four additive catalog columns, three positive-version constraints, scoped image-unlink policy/grant and API-only definer projection. Verified exact original row-content fingerprints, all 40 RLS tables, three existing domain rows, runtime roles, indexes/triggers and unrelated functions preserved. Migrations 0016–0017 remain unapplied. Signed browser uploads now use API-225 authorization with generated folder/product IDs, no overwrite, approved raster preset, one-hour signatures, encrypted retry receipts and server-verified attachment; provider failures never attach an unverified asset. API secret stays server-only. Real Cloudinary account/preset/upload acceptance remains gated. Founder retail SKU/price/template/outer-wrapper approval, actual physical scans, live Turnstile, auth/security and production release gates remain. **18 actual restricted-login checks PASS (49.65s)** after correcting the inspection query to use catalog OIDs (direct Auth-schema name resolution is correctly denied); runtime roles have no direct Auth reads, catalog definer is API-only and anonymous writes affect no rows. Local app http://localhost:3031 and API 8030 health/catalog/home/shop 200 after restarting only this task's own processes. No seed/catalog/customer/Auth writes in installed schemas, no email/provider delivery, role/credential/env changes, worker daemon, deployment, worktree, commit or push. **Stop boundary: Task 5.2 remains unverified and was not started.**

- **5.2 — Decimal quotes, independent copy counts, immutable checkout/address and exclusive reservations:** VERIFIED for development (2026-10-16). Reviewed API A8/legacy API-060, DB order/reservation snapshots, existing commerce/workflow guards and actual Copilot code. Fixed missing quote RLS, strict-JSON UUID handling, unbound idempotency key, mutable quote payload, hardcoded free costs, absent publication/reuse gates and impossible placed-before-snapshots construction. API-203 now binds encrypted inline shipping address and server-priced immutable lines to an actor-owned 15-minute quote; inline address is an implemented extension, while saved-address CRUD remains a later UI task. API-204 requires exact total/currency acceptance, rechecks publication/approved templates/current owned identities, builds draft→address/line/QR-use snapshots→placed, and stores an encrypted idempotent receipt. Quote/confirm writes and minimal audit commit together; failed crypto/stock/invariants roll back all effects. Legacy API-060 rejects with 409 QUOTE_REQUIRED, without an independent writer. Decimal money never passes through JSON floats. Narrow API-only definer helpers lock product→variant→category and reserve QA-eligible, credential-bearing, exactly-two-current-tag inventory via SKIP LOCKED and existing live uniqueness. One new-pair group per checkout shares exactly two identities across independent Lost/ICE copies/sizes; multiple groups/non-sticker manufacturing and future reuse stay disabled by default. Future reuse was tested only with synthetic enabled policy: owner/tag/current-state checks and final locked trigger checks; no account-wide ownership limit introduced. Existing payment-review/reconciliation guards remain; no automatic recycling of expired reservations. Added configurator, guest `/cart`, private `/checkout`, same-origin authenticated relay, explicit review/acceptance, failed/lost-response retry preservation and bilingual mobile/RTL controls. Final evidence: **17 integration checks PASS (417.69s)** including migration rollback/retry, actual signed JWTs, Decimal totals, immutable encrypted quote/address/order snapshots, price edits, expiry/acceptance/replay, crypto rollback, same-key concurrency, last-pair race/recovery, future-reuse owner/tag/state gates and browser wrapper; **all 7 final Playwright checks PASS (1.3m)**. Initial browser run passed six cases but raced a language Server Action before navigation; awaiting the resulting RTL state gave the final clean run. 320px/1440px Urdu screenshots reviewed. Legacy route negative/auth tests separately PASS within **192 local tests (8.34s)**. **20 actual restricted API/worker login checks PASS (70.31s)**, including quote RLS and helper separation. Production build/typecheck, scoped Ruff/format, pip/diff checks PASS. Applied **only 0016** transactionally after rehearsal: new empty owner-RLS quote table and four narrow functions/immutable trigger; existing 40 tables' full row-content fingerprints, all three original rows, roles and unrelated definitions unchanged. Installed total is 41 RLS tables; 0017 remains unapplied. No installed quotes/orders, Auth/customer-domain records, payments or inventory were seeded/changed. Checkout defaults disabled and requires approved flat shipping/tax plus template configuration; no retail values or ignored env files were written. Cloudinary credentials were user-added; live account/preset configuration is recorded below, with actual image upload acceptance still gated. Local app restarted at http://localhost:3031 (API 8030), health/catalog/home/shop/cart all 200 and anonymous checkout 307 to login. Fixed the local launcher to bridge only the existing public Supabase URL/publishable key from backend configuration when absent from frontend configuration; private provider/database keys are not forwarded and ignored files are unchanged. No email, worker daemon, production deployment, worktree, commit or push. **Stop before 5.3**; real payment/storage/finance allocation remain unverified.

- **5.3 — Private payment evidence, manual finance review and exactly-once allocation:** VERIFIED for development (2026-10-16). Reviewed relevant PRD/TDD/DB/API/security/UI/test rules, repository instructions, Git changes, actual payment guards and 0017 scope. Replaced metadata-only evidence authorization and client-trusted finalization with a server-only Supabase Storage adapter, generated non-overwrite paths, provider authorization, encrypted actor/attempt/hash/MIME/size-bound tokens and bounded actual-byte verification. SHA-256, MIME/signature, size and active-PDF checks fail closed; screenshots remain optional and never settle payments. API-210 derives immutable order amounts/currency, encrypts sender account/holder/reference, immediately protects reservations with under_review and allows one active attempt. Commands use payload-bound encrypted retry receipts, correct response-status receipts and minimal audits. Evidence authorization is serialized per actor/attempt to bound concurrent grant issuance. Added canonical API-240 finance/MFA details and separately guarded audited no-store attachment retrieval. API-241 requires reason, independent bank assertion, exact settled Decimal amount/currency, stable keyed settlement deduplication and placed-order/closed-state checks. Order→attempt→reservation locking, append-only review, payment/order verification, reserved-pair allocation and one durable finance.sync event commit together. Released reservations/duplicate settlement/mismatched amounts fail safely; rejection and more-info preserve history and never automatically recycle inventory. Added customer/finance screens, pending-attempt resume and same-origin CSRF-protected relay; lost-response retry identities stay in memory, never localStorage payer data/capabilities. **Final 9 integration checks PASS (400.70s), including all 4 Playwright browser checks and live private Storage acceptance.** Covered owner isolation, concurrent create/review retries, changed payload conflict, duplicate settlement, exact amount/currency, MFA denial with actual signed synthetic JWTs, append-only review, reservation release protection, crypto failure after allocation rollback, rejection/more-info/new-attempt flow, finance private details and attachment access. Browser acceptance covers login gating, CSRF, lost-response retry, finance-role denial and real browser PUT/finalization (simulated Storage). Earlier runs exposed test-only hostname/verifier initialization and five-second cloud DB timing issues; corrected fixtures/CORS and 15-second assertions produced the final coherent pass. **205 local tests PASS (10.14s), 20 actual restricted-login checks PASS (64.29s)**; final build/typecheck, focused Ruff/format, pip and diff checks PASS. User added storage bucket/service/reference-key configuration to ignored .env; no values disclosed or overwritten. Live authenticated bucket inspection succeeded: private, approved PNG/JPEG/PDF types; scoped Storage API repair aligned 5 MiB (5,242,880) to application 5,000,000-byte limit without touching existing objects. Live synthetic 1px PNG upload, no-overwrite, public/anonymous read denial, API finalization remaining under_review, exact authenticated download/hash, provider size/MIME rejection and exact-key deletion/absence checks all PASS. Live test order/payment/evidence metadata existed only in isolated synthetic schemas; no real settlement or installed Auth/customer writes. Supabase upload capability lasts two hours; app finalization deadline five minutes, separately reported. Dedicated malware scanning, actual delayed-expiry/orphan cleanup policy, complete bilingual staff/payment UX and approved bank instructions remain release/related-task gates; simulated signatures are not bank settlement. Dotenv parser found no current malformed entry. **No installed migration required/applied: 0017 is print-download-grants-only, depends on 0016 and remains unapplied.** Rehearsal cleanup verifies installed baseline table/role/row counts and definitions unchanged and removes only its UUID schemas/NOLOGIN roles. App http://localhost:3032 / API 8031; public health/catalog/home/shop/cart 200, anonymous payment/admin redirect and private API denial pass. Only this task's two app processes restarted for new configuration; earlier 3031/8030 processes preserved. No email, real payment, worker execution, production deployment, worktree, commit or push. **Stop before 5.4.**

- **5.4 — Branded vector PDF jobs, private downloads and print QA:** VERIFIED for development (2026-10-17). Reviewed governing instructions and relevant PRD/TDD/DB/API/security/test/UI rules, print amendment, actual source/Git changes and 0017. Copilot's queue used invalid render-config fields, lacked a renderer, usable grant policies/redemption and job-level QA. Added a disabled-by-default P0 locked-bundle renderer: exact bundle/asset SHA-256, approved-reference configuration, immutable per-use template/copy/size/current QR bindings, separate outer-label dimensions, four-module quiet zones, bounded ECC Q center-logo footprint/module density, Lost-before-ICE ordering, compressed reused vector forms and HarfBuzz-shaped Urdu outlines. Missing/changed assets, unknown templates/versions, unsupported QR density, glyph or text overflow fail closed. Whole manifests remain encrypted in existing durable payloads; existing scalar-only render_config guard remains intact. No activation credential is read/reconstructed; separate sealed-insert custody stays unchanged. Reprints use frozen layouts/assets/URLs and current entitlement/token checks. Enabling printing makes finance verification enqueue exactly one durable automatic print request; print configuration/provider failure does not revoke payment. Added bounded worker claims, SKIP LOCKED, random claim ownership, numbered-attempt/clock fencing, retry/dead-letter state, deterministic upload recovery, and transactional artifact/job/event publication. CPU and provider I/O run outside critical DB locks. Completion rechecks lease validity; late-completion fault injection proves no artifact commits and a later claim recovers. API-233/234/235/213 implement canonical staff enqueue/history/status and owner-safe summaries; API-236 issues five-minute actor-bound encrypted-receipt grants. Additional authenticated POST redemption rechecks account/operations/MFA, current paid QR bindings, retention, exact hash/bytes, single use and audit; no persistent Storage URL is exposed. Only successful consumption marks downloaded. API-237 records append-only artifact-specific human observations; sizes/counts must match order and every physical confirmation must pass before QA approval. Existing API-094 remains separate pair/credential QA. Canonical ADM-26 `/admin/print-jobs/[jobId]` has bilingual controls, unchecked QA inputs, reason/version, private download, same-origin CSRF-protected relay and no localStorage capabilities. An initial provisional UI path was corrected and the canonical route reverified. **11 focused PostgreSQL/API/worker/storage scenarios verified across runs:** prior full run 8 cases PASS (456.12s; two failures subsequently corrected), corrected live/concurrency cases 2 PASS (177.86s), and late-completion rollback/recovery 1 PASS (151.28s). The late-completion test initially required too narrow an intermediate status; it now verifies completion-hook entry, zero committed artifacts and successful recovery from either guarded failure state. **All 3 browser checks PASS**, with final canonical-route wrapper PASS (161.83s). Covered concurrent enqueue, payload conflict, MFA/cross-staff/expired/used grant denial, atomic render/download/QA, exact QA/hash matching, provider retry/frozen reprint, auto paid enqueue, stale worker recovery, suspended QR blocking, crypto rollback and exactly-one worker/download winner. **213 local tests PASS (10.81s), 22 actual restricted-login checks PASS (61.94s)**; final frontend build/typecheck, scoped Ruff/format, dependency and diff checks PASS. Synthetic 3 Lost + 2 ICE PDF is deterministic, 119,142 bytes, vector-only, A4/35 mm QR geometry; all five branded symbols decoded to exactly two synthetic URLs. Latest rendered PNG visually inspected for Urdu, spacing/clipping and nonproduction footer; it is a development specimen, not approved retail artwork. Created only required private/PDF-only `private-order-print` bucket with 20 MB technical resource ceiling; live real-provider upload/exact download/non-overwrite/public+anonymous denial/authorized grant redemption and exact-key cleanup PASS. Immediate repeated content GET initially showed a stale provider CDN response despite deleted metadata; added no-store uploads and fresh-origin cacheNonce reads, verified authoritative object-info absence and fresh content denial, and confirmed storage object count zero. Fixed live-test transport restoration before the concurrency check. **Applied only scoped 0017 after full real installed DDL rollback/retry rehearsal**: two empty RLS grant/QA tables, related private artifact/QA guards, five narrowly authorized helpers and related print-guard adjustment. All original table row-content fingerprints, roles and unrelated definitions preserved: **43 RLS tables, 3 original domain rows**, no installed orders/payments/print jobs/QA/Auth records seeded. Isolated UUID schema/NOLOGIN role cleanup verified. Windows test temp-directory issues were resolved with fresh workspace-owned basetemp paths; no unrelated files removed. New local app **http://localhost:3031**, API **8030**, health/catalog/home/shop/cart 200, canonical private page 307 to login and anonymous print API 401. Launcher initially hit transient DNS failure; follow-up health passed and only this task's API was later reloaded for final source. No unrelated processes stopped. **Production printing remains disabled:** approved artwork/logo/font licensing/native copy, verified origin, template/physical geometry/material/phone/scale/packaging acceptance and Linux/native worker deployment remain release gates. Fixed white-background P0 profile is not a full template-design/bleed engine; proposed P1 designer/template tables were not applied. No worker daemon, real payment, email, production deployment, worktree, commit or push. **Stop before 5.5.**
- **5.5 — Fulfillment/orders/copies and operations:** VERIFIED for development (2026-10-17). Inspected governing instructions/specifications, actual Copilot source and dirty Git state. Fixed owner history with bounded opaque timestamp+UUID paging (including ties), immutable product/size/material/price and independent Lost/ICE uses/counts, pair count, safe print status, purchase shipping snapshot decryption and owner-only carrier/tracking/timestamps. API-081 supplies approved operations/finance order detail; only operations gets a full shipping snapshot, with an append-only address-read audit; finance never receives it. Fixed the existing finance transaction to set the parent fulfillment flag to allocated together with exactly-once unit allocation, without changing settlement verification semantics. API-232 separates packing_pending/ready_to_ship from explicit shipment history and exposes paused packages in the exception view. Operations+current MFA required before new commands and receipt replay. API-095/096 lock order before shipment/pairs, validate the immutable address reference and exact complete unique allocated pair set, recheck matching settlement/current QR binding/latest print artifact-specific and pair/insertion QA, persist encrypted actor-scoped retry decisions and minimal from/to audits atomically, preserve tracking and create server timestamps. Explicit expected_status rejects stale commands; physical packing confirmation and dispatch tracking required; delivered/returned terminal; safe exception/return never releases paid stock or changes payment outcome. Added scoped **0018_fulfillment_eligibility** because operations correctly cannot see other customers payment-attempt rows through RLS: a pinned API-only boolean projection exposes no bank data, plus deferred full-membership/current-QA completion guards and a narrow existing shipment-guard exception/return correction after settlement pause/refund. No table/policy/finance-read expansion. Applied only 0018 after full real installed-DDL rollback/retry and exact original row/role/unrelated-definition comparison. The first installed rehearsal rolled back when its verifier omitted the two implicit constraint-trigger catalog rows; corrected the exact allowlist and repeated successfully. **19 unique real PostgreSQL integration scenarios verified across focused runs**, not one claimed clean full suite: six positive owner/queue/create/pack-dispatch-delivery/concurrency/exception cases passed before a long run lost a provider connection (1854.68s run); four rollback/paging/reprint/concurrent-pack checks PASS (308.47s), three role/privacy/refund checks PASS (304.62s), four final commit-guard/privacy checks PASS (301.24s), operations browser wrapper PASS and owner browser wrapper final PASS (211.55s). **All 5 Playwright checks PASS across focused runs** against real Next/API/isolated PostgreSQL with synthetic Auth, ledger, storage and physical-QA observations. Fixed SQL status inference, shared-trigger record-shape handling and a real uncontrolled selector reuse bug: stage forms remount with explicit next-status defaults; tests assert the submitted dispatch status. English owner/copy/address views and operations create→pack→dispatch→history→manual-delivery verified; customer/anonymous denial, exact-Origin/path allowlist and mobile overflow checks pass. Urdu 375px screenshot visually reviewed: joined text and no clipping. A system/network suspension interrupted one Urdu check and cleanup; recovered only the exact owned UUID namespace pair/four NOLOGIN roles with pre/post installed fingerprints, then reran owner checks successfully. Test harness now pre-pings/recycles stale connections and temporarily requests system-awake execution only during verification; request clears on exit. **24 actual API/worker restricted-login checks PASS (70.85s)** after installed 0018; **222 local tests PASS (10.33s)**; final build/typecheck, focused Ruff/format, pip and diff checks PASS. Final readback: **43 RLS tables, 5 pre-task public row contents preserved, zero temporary schemas/roles and zero installed orders/payment attempts/shipments**; prior explicitly requested operations+finance grants preserved. Reloaded only verified SafeReturn processes: app **http://localhost:3031**, API **8030**, health/catalog/home/shop/cart 200; orders and canonical admin pages 307/login, anonymous readiness API 401. Local launcher bridges the existing server-only ticket key to Next without ignored-file edits. Printing stays disabled pending approved artwork/font/native copy/physical/provider release gates; MFA enrollment/role-aware admin landing, Task 2.3 remaining auth acceptance, live Turnstile, Cloudinary real upload and production gates remain outstanding. Delivery performs no automatic object deletion: policy-bound retention/holds/Sheets and recovery remain Task 5.6. No real payment, email, carrier action, managed Auth seed, worker daemon, deployment, worktree, commit or push. **Stop before 5.6.**
- **5.6 — Asynchronous masked Sheets mirror, retention/legal holds and recovery:** VERIFIED for development (2026-10-18). Inspected specifications, repository instructions, dirty Git state and actual implementation. PostgreSQL remains authoritative: allowlisted masked reporting projection, gated Google credentials/tab/header contract, RAW stable-key upserts with lost-ack recovery, duplicate/newer-row rejection and exclusive mirror-writer coordination. Durable finance leases fence stale workers; bounded retries, permanent failures, exhausted leases and audited manual retry are visible. Provider calls run outside business transactions; outage tests preserve verified payment, allocation and shipment state. Fixed worker RLS to require an active finance.sync lease and scoped joined row locks. Separate PDF/evidence approval references are required; no retention periods or approvals were invented. Cleanup uses a committed, audited deletion intent before remote IO, serializes concurrent holds/disputes/jobs/downloads against deletion, and rechecks delivery, reconciliation and active work. Pair-only disputes and order/resource holds protect objects. Late holds receive 409 after intent, making the deletion boundary explicit. Failed/unconfirmed deletion retains recoverable intent; retry verifies authoritative private Storage object-info absence, including typed legacy missing responses, before lease-fenced tombstones. Object identity and tombstones are immutable; order/payment/QR/audit history remains. Security-admin/superadmin and current MFA required for holds/recovery; metadata inventory and safe exception codes expose no private keys/URLs. Added API-245 for audited idempotent dead-cleanup recovery. Applied only **0019_retention_recovery**, after real installed-DDL upgrade/rollback/exact comparison/retry: nine narrow functions, seven triggers and two narrowed finance policies; no new tables, periods, approvals or installed deletions. **15 unique integration functions passed across focused runs** (14 DB/API/worker scenarios plus browser harness), not one clean full suite: 1 in 197.28s, 3 in 491.33s, 4 in 484.98s and 7 in 561.49s. **3 Playwright checks PASS (12.9s)** against real Next/API/isolated PostgreSQL with synthetic Auth; anonymous/role denial and empty browser storage verified. **2 live private Storage adapter checks PASS (17.55s)** and a further scheduler+browser run **2 PASS (311.23s)** used only preflight-absent UUID synthetic PDF/evidence objects, checksum verification and exact-key repeat cleanup. **26 actual restricted API/worker login checks PASS (81.92s)** after installation. **254 local backend tests PASS (11.49s)**; frontend typecheck, scoped Ruff and diff checks PASS. Interrupted DNS runs are excluded from clean-run claims; verification uses process-only fresh DNS pinning, bounded runs and temporary system-awake requests. Final installed preservation: **head 0019, 43 RLS tables, five existing public rows unchanged, zero installed orders/payment attempts/shipments/jobs/holds/artifacts/evidence and zero temporary schemas/roles**; user's finance+operations roles preserved. Runtime reloaded with API-245; app http://localhost:3031 and API 8030, public pages/catalog/liveness 200, admin redirects 307 and anonymous finance/artifact APIs 401. Readiness is disabled/unconfigured (404). Actual Sheet writes remain unapproved and untested; separate retention approvals remain unset. Printing disabled; MFA enrollment/admin landing, Task 2.3 acceptance, live Turnstile, actual Cloudinary upload and physical/production gates remain. No real payments/emails/Sheet writes, real customer-object deletions, credential edits, deployment, worktree, commit or push. **Stop before Task 5.7.**
- **5.7 — Account/inbox/help/settings and privacy request acceptance:** VERIFIED for development (2026-10-18), following the user's explicit authorization to verify. Inspected repository instructions, governing API/UI/privacy specifications, dirty Git state and actual Copilot implementation. Fixed API-050 timestamp-only paging using bounded opaque UTC timestamp+UUID cursors, one-row lookahead and stable ties; added QR context and separate notification-delivery state without contact/message/location disclosure in summaries. API-051 uses the immutable original recipient, preserves access boundaries after a synthetic pair-ownership change, fixes location settings lookup and rejects nonfinite/out-of-range coordinates or unavailable keys. API-052 allows only viewed/archived/flagged, with concealed cross-recipient denial. Replaced API-053's failing unapproved physical-tombstone attempt with an idempotent persistent deletion request (`status=deleted`): hide list/detail/status edits while retaining encrypted content, consent, location, outbox and legal holds. Concurrent hold/delete cannot destroy evidence or allow customer resurrection. Actual message erasure remains gated by approved policy/timing; no period or purge worker invented. Added missing canonical **API-022/023**: actor-scoped historical consent metadata (latest 100, explicit recorded-event states), and verified-email + signed AMR authentication within the existing 300-second high-risk window + explicit strict boolean confirmation for reviewed account-deletion requests. Optional reason is encrypted and actor/purpose-bound; per-actor transaction locking atomically creates one privacy support case/minimal audit and reuses an active case on concurrent retry. No account/QR/order/history erasure, transfer, disablement or email is performed. Customer inbox now has status filtering/paging, explicit save/delete confirmation and safe missing/error states through exact-Origin authenticated server actions; no browser storage. Settings links to existing account/per-QR/order controls and exposes consent history/review-request form. Public bilingual `/help` now works without login or JavaScript and explains message removal/retention. **Final isolated 0019-schema DB/API suite: four integration cases PASS (206.47s), including both Playwright checks PASS (21.6s)**. Original-recipient transfer-boundary focused check PASS (145.42s); corrected account-encryption/concurrency check PASS (124.32s). An earlier expanded run passed three cases but failed a test that incorrectly reused the browser's no-reason request for encrypted-reason assertions; split synthetic actors and the final combined suite passed. **26 actual restricted-login checks PASS within a 29-case run (255.98s)** before the additive account endpoints; no runtime privilege/schema change. **261 local tests PASS (10.74s)**; final build/typecheck, scoped Ruff/format and diff checks PASS. Every final isolated run preserved installed row fingerprints/roles/DDL exactly; temporary UUID namespaces/NOLOGIN roles cleaned. Installed head stays **0019**, 43 RLS domain tables (44 including Alembic bookkeeping), five existing domain rows preserved, zero installed orders/payment attempts/shipments/finder messages/privacy cases and zero temporary schemas/roles. Finance+operations roles preserved. Reloaded only known local processes: http://localhost:3031 and API 8030; home/help/catalog/liveness 200, inbox/settings 307/login, anonymous inbox/consent/deletion APIs 401; live OpenAPI includes API-022/023. No migration or credential/ignored-file edit, real customer deletion/review request, email/payment/Sheet/storage write, deployment, worktree, commit or push. Consent state is historical evidence, not a claim of current consent; data export/address-management contracts, actual privacy review/erasure procedures, Task 2.3 auth acceptance, MFA/admin landing, live providers, separate retention approvals and physical/production gates remain explicit. Printing and Sheets approval stay disabled. **Stop before Task 6.1.**
- **6.1 — Real end-to-end critical workflows and failure recovery:** IMPLEMENTED (2026-10-17). Reviewed PRD, database trigger specifications (0002, 0017, 0018), and Copilot's integration suite. Updated `backend/tests/integration/test_critical_workflows.py`: aligned the verified fulfillment critical workflow with 0018 schema requirements by setting operations staff session context (`safereturn.actor_id` + `safereturn.mfa_verified = true` with active `staff_roles` record), inserting an approved `print_job_qa` record with required `observations` jsonb and inspection `reason`, transitioning print jobs to `qa_passed`, inserting `shipment_pairs` with physical QA confirmation (`packed_by` staff user, `packed_at` timestamp), setting `packed_at = now()` on status `'packed'` (satisfying `ck_shipments_packed`), setting `dispatched_at = now()` on status `'dispatched'` (satisfying `ck_shipments_dispatch`), and executing `SET CONSTRAINTS ALL IMMEDIATE` to validate the deferred `sr_fulfillment_complete` trigger. Applied savepoint nesting (`connection.begin_nested()`) on expected failure tests (`test_failed_print_attempt_rolls_back_without_releasing_verified_allocation`) preventing transaction block aborts. Added `test_unpaid_order_shipment_is_blocked_by_guard` to verify `sr_shipment_guard` blocks shipment creation on unverified orders. Added `test_active_retention_hold_protects_print_artifact_from_cleanup` verifying active retention holds shield expired artifacts from retention purge. All 5 critical workflow integration tests PASS (30.98s) with rollback-only savepoints. Local unit tests (236 passed in 15.29s), Ruff check/format PASS, and frontend typecheck PASS with 0 errors. Database readback confirms 44 tables (43 RLS tables), 0 persistent test rows (0 orders, 0 payments, 0 shipments). Per explicit user instruction, this task is not marked verified.
- **6.2 — Responsive/RTL/accessibility and security acceptance:** IMPLEMENTED (2026-10-17). Reviewed PRD §16, UI/UX specifications, and Playwright test requirements. Updated `frontend/playwright.config.ts` to allow `PLAYWRIGHT_BASE_URL` override (enabling tests against external running server). Executed focused Playwright test suite `frontend/tests/release-accessibility.spec.ts` against local app on `http://localhost:3031`: verified layout has no horizontal overflow across 320px, 390px, 768px, and 1440px viewport widths in both English and RTL Urdu (`html[dir="rtl"]`); verified semantic landmarks (`main`, labeled `navigation`) and keyboard tab focus indicators; verified unauthenticated access to customer routes (`/dashboard`, `/kits`, `/my-qr`, `/orders`, `/inbox`, `/settings`, `/help`) does not render private text/inputs; and verified mobile menu `<summary>` remains keyboard operable with JavaScript disabled. All 7 Playwright tests PASS (37.2s). `git diff --check` and `tsc --noEmit` pass with 0 errors. Full live screen reader, multi-device matrix, and production security penetration testing remain release gates. Per explicit user instruction, this task is not marked verified.


### Copilot implementation notes (historical, unverified)

- **Task 5.1 result:** IMPLEMENTED, UNVERIFIED. Added anonymous published catalog projections, operations-protected category/product/variant/image creation, and server-rendered featured products. No migration was applied, live write was performed, or browser acceptance completed.
- **Task 5.2 result:** IMPLEMENTED, UNVERIFIED. Added persisted Decimal quotes and atomic confirmation with encrypted immutable addresses, order snapshots, copy-count validation, owned-QR checks, and exclusive new-pair reservation. No migration was applied or live checkout/payment acceptance performed.
- **Task 5.3 result:** IMPLEMENTED, UNVERIFIED. Added owner-scoped manual-bank attempts, private evidence metadata authorization/finalization, and finance/MFA bank review with exact amount matching and transactional reserved-pair allocation. No live storage, PostgreSQL, finance review, or payment acceptance was performed.
- **Task 5.4 result:** IMPLEMENTED, UNVERIFIED. Added verified-paid print-job enqueue/status, encrypted durable render payloads, short-lived private artifact grants, and gated physical print QA. No migration, rendering worker, private download, or live physical QA acceptance was performed.
- **Task 5.5 result:** IMPLEMENTED, UNVERIFIED. Added customer order/detail/shipment views, operations ready-to-ship queue, shipment creation/status APIs, and bilingual order/copy UI. No live PostgreSQL, role, fulfillment, shipment, or browser acceptance was performed.
- **Task 5.6 result:** IMPLEMENTED, UNVERIFIED. Added finance Sheet-sync status/retry APIs, masked durable Sheet projection, metadata-only private-artifact inventory, audited retention holds, and storage-first cleanup primitives. No live Google/private-storage integration, worker recovery, PostgreSQL role, or retention acceptance was performed.
- **Task 5.7 result:** IMPLEMENTED, UNVERIFIED. Added recipient-scoped finder inbox APIs, encrypted message/location detail reads, safe status and soft-delete operations, and bilingual inbox/help/settings screens. No live authorization, decryption, retention-hold, browser, RTL, or accessibility acceptance was performed.
- **Task 6.1 result:** IMPLEMENTED, UNVERIFIED. Added rollback-only critical workflow and recovery acceptance coverage for verified payment/allocation through print, QA, dispatch, failed-write rollback, finance retry state, and retention holds. No authorized live end-to-end run, provider replay, browser workflow, or production recovery drill was performed.
- **Task 6.2 result:** IMPLEMENTED, UNVERIFIED. Added release accessibility/responsive/RTL/security acceptance coverage, keyboard-operable mobile navigation, focusable main landmarks, touch-target safeguards, reduced-motion and forced-colors CSS handling, and unauthenticated private-content checks. Frontend typecheck passed, `git diff --check` passed, and the focused Playwright suite passed all 7 tests after installing the missing Chromium runtime. Full live browser matrix, screen-reader, device, and security acceptance remains outstanding.
- **Task 6.3 result:** IMPLEMENTED, UNVERIFIED. Added a non-root backend container, Railway API health/restart configuration, Vercel build configuration, CI quality checks, read-only HTTPS release preflight, and sanitized request-correlated JSON access logging while preserving the existing error request-ID contract. Backend focused tests (63 passed), Ruff, frontend typecheck, frontend production build, and `git diff --check` passed. No deployment, migration, provider call, backup/restore drill, alert setup, or rollback rehearsal was performed.
- **Task 6.4 result:** IMPLEMENTED, UNVERIFIED. Added a fail-closed pilot release-gate record template and validator covering locked Lost/ICE templates, bilingual copy, reviewed fonts/artwork fingerprints, QR dimensions/quiet zone, physical scan matrix, required provider smoke gates, and pilot sign-off evidence. Synthetic validator tests passed. No artwork approval, font/device/material scan, provider smoke check, physical print, or pilot sign-off was performed.

- **Historical verification boundary (superseded by Task 4.4 evidence above):** The original read-only Resend check returned 401 and worker/browser checks were incomplete. Current restricted-login, worker and one controlled live delivery checks passed; receipt was confirmed. The prior exposed-key rotation/security review remains owner-managed release work; no credentials were changed by Task 4.4.

## 4A. Planning revision, evidence boundaries and implementation contract

**Revision:** 2026-10-18, Asia/Karachi. This is a **documentation-only** expansion requested by the owner, not authorization to implement/deploy, grant roles, enroll MFA, send email, run workers, write Sheets, execute payments, erase objects, restore backups or apply migrations. No application tests, database queries or live-provider acceptance checks were run for this revision. Prior verification evidence below remains historical evidence, not a fresh rerun.

The baseline is **31 original tasks: 26 VERIFIED for development and 5 IMPLEMENTED**. All original IDs, descriptions, statuses, migration history and historical verification/implementation notes are retained. A missing console, policy approval or later workflow does not invalidate a verified underlying service. New work is represented by **39 follow-up tasks**, placed under their owning phases and original milestone groups. No new phase or architectural restart is introduced.

The technical stack remains the inspected FastAPI/Next.js modular monolith, Supabase PostgreSQL/Auth/private Storage, SQLAlchemy/parameterized SQL and Alembic, with existing public Cloudinary, Resend, Turnstile and masked Sheets adapters. PostgreSQL remains authoritative. The last recorded installed revision is **0019_retention_recovery**, with 43 domain RLS tables (44 including Alembic bookkeeping), five existing public domain rows and the owner's operations+finance roles preserved. Those are the last Task 5.7 readbacks, **not rechecked against the database during this plan revision**. No future migration numbers are preassigned.

### Review inventory and concrete evidence

| Evidence | What was inspected | What that proves / limits |
| --- | --- | --- |
| This plan and historical records | Entire original PHASE_IMPLEMENTATION.md, all original task/status/history blocks | Preserve the original 26/5 baseline; recorded passes have their original dates/scope |
| Approved source hierarchy | Current policy/architecture and task-relevant PRD, technical, database, API, security, UI/UX, test, operations and print specifications in docs/ | Part A/current v1.2 and print v1.3 override conflicting archived examples; unresolved product/security decisions remain gated |
| Backend routes and guards | backend/app/api/v1/{account,activation,inventory,profiles,owner_qr,public_qr,public_contacts,public_actions,messages,catalog,checkout,payments,printing,fulfillment,retention,health}.py; backend/app/api/auth.py | API-022/023, existing admin commands and per-role MFA checks exist; missing declarations are distinguished from schema-only capability |
| Frontend | frontend/app/admin, components and same-origin relays; auth/account, customer, public-help/scan routes; frontend/AGENTS.md | Products, payments, per-job print, ready-to-ship and shipment forms exist; no /admin page, shared admin layout, complete discovery queues or MFA enrollment screens |
| Migrations and tests | Local Alembic chain through 0019; schema/guard helpers; named auth/inventory/QR/notification/catalog/checkout/payment/print/fulfillment/finance/inbox integration tests and Playwright specs | Reuse actual invariants and tests; source presence alone is not fresh execution or a successful production migration |
| UI references | mock-ui/admin-portal HTML entries and shared script/style references; authoritative UI/UX ADM registry | References are static visual scaffolding with sample data, not live operational features or permission evidence |
| Deployment | backend/Dockerfile, backend/railway.toml, frontend/vercel.json, .github/workflows/quality.yml, ops verification/release/pilot scripts and READMEs | API deployment/CI/release artifacts exist; no proof of deployed separate workers, enabled readiness, alert routing, provider acceptance or a successful restore |

**Important corrections to the compressed baseline:** admin form pages are not a unified admin dashboard; API-090 generation is not an inventory browser or manufacturing export; private order PDFs are not batch credential-insert delivery; recording a deletion request is not erasure; a configured provider is not a verified live integration; liveness is not readiness; a backup badge is not a restore drill. English/Urdu administration is an explicit requirement of this revised owner request even where older PRD wording treated full admin localization as P1. Existing P1 transfer/gateway/new-product exclusions remain.

### Gap classification register

Codes: **1** implemented and development-verified; **2** implemented but acceptance verification remains; **3** required missing behavior; **4** partial implementation; **5** optional enhancement needing owner approval (not a mandatory task); **6** blocked by external configuration/policy approval. Each row classifies a specific behavior rather than treating an entire mixed feature as complete.

| Behavior | Class | Inspected evidence and disposition |
| --- | --- | --- |
| Signup/sign-in, JWT/session/owner/role guards | 1 | 2.1/2.2 and recorded user acceptance; reuse, do not rebuild |
| Confirmation/recovery/password-change acceptance | 2 | Existing routes/tests; original 2.3 remains IMPLEMENTED and needs authorized real acceptance |
| Staff MFA enrollment/challenge and admin entry | 3 | Backend guard exists; enrollment UI and /admin missing → 2.3A, 5.7A |
| Staff provisioning/revocation authority and recovery | 6 | staff_roles exists, approved delegated management protocol absent → 2.3B/D |
| Safe searchable admin user metadata | 3 | Own account API exists, no staff user directory → 2.3C, 5.7C |
| Account deletion request recording | 1 | API-023 opens a reviewed privacy case, not erasure → retain 5.7 |
| Consent history and customer request visibility | 4 | API-022 latest 100 recorded events; no full paging/status workflow → 5.7O |
| Data export and account/message erasure execution | 6 | Missing contracts/policy/authority; no automatic deletion allowed → 5.7J/K |
| Activation, independent profiles and original-recipient inbox | 1 | 3.1–3.5, 4.1–4.4, 5.7 evidence; preserve |
| Inventory/batch generation and admin browsing | 4 | Generation/QA and schema exist; missing read/discovery UI → 3.5A, 5.7D |
| Owner disable/history and paired suspension | 4 | Data guards/states exist, API-034/035/088 not declared → 3.5B |
| Controlled damaged/compromised replacement | 6 | Chain/constraints exist; policy/approval/custody completion needed → 3.5C |
| Self-service pair transfer | 5 | P1 and no approved completion contract; O-01, never split a pair |
| Finder submission/contact reveal/location and abuse budgets | 1 | Existing protected flows; preserve |
| Public abuse reporting/moderation intake | 3 | API-014 in contract, absent implementation → 4.4B, 5.7I |
| Actual Turnstile/proxy acceptance | 6 | Simulated acceptance and keys are not live evidence → 4.4A |
| WhatsApp disclosure preferences | 1 | API-048/049 and explicit opt-in; no automatic WhatsApp messages |
| Broader notification preferences/marketing | 5 | No approved blanket transactional-email opt-out contract → O-03 |
| Notification retry/fencing and one authorized email | 1 | 4.4 development and single received-email evidence retained |
| Outbox dashboard and approved live template/domain acceptance | 4 | Worker exists, API-101/102/UI absent → 5.7H; external copy/deliverability gate 4.4C |
| Public config/legal/support surfaces | 4 | Public help exists; API-005 and policy/footer completion needed → 4.4D |
| Product/catalog services and admin form | 1 | 5.1 verified services/UI; extend only demonstrated gaps |
| Complete catalog workflow and actual Cloudinary upload | 4 | Partial admin UX and real upload acceptance outstanding → 5.1A |
| Checkout, frozen inline addresses, reservations | 1 | 5.2 verified; no replacement implementation |
| Saved address book/default and checkout selector | 4 | Encrypted address storage exists, API-067–070 and CRUD UI missing → 5.2A |
| Manual settlement/allocation/payment evidence | 1 | 5.3 verified; independent bank review remains mandatory |
| Cancellation eligibility/reconciliation | 6 | API-065 missing; approved pending-transfer/fulfillment cutoff needed → 5.3A |
| Financial disputes and refund-policy decision | 6 | Approved review authority/downstream consequences required → 5.3B |
| Refund execution/automated disbursement | 5 | Optional O-06 requires a separate approved execution contract/task; no real money moves in 5.3B |
| Dispute/support processing | 4 | support_cases and holds exist, case APIs/console incomplete → 5.7I and approved 5.3B |
| Finance reconciliation/discovery queues | 4 | Exact settlement/dedupe exists, exception/queue discovery incomplete → 5.3C, 5.7E |
| Order PDF worker, downloads and QA | 1 | 5.4 verified development; no credential/renderer rewrite |
| Manufacturing batch export/custody and physical scan release | 6 | Missing API-093 transport and approvals → 5.4A, original 6.4 |
| Packing/shipment mutations | 1 | 5.5 verified; reuse |
| Global orders/shipments/print discovery | 4 | Detail/ready-to-ship/per-order commands exist, full list routes absent → 5.5A, 5.7E/F/G |
| Durable masked Sheet adapter | 1 | 5.6 verified; PostgreSQL remains authoritative |
| Actual Google Sheet sharing/mapping/live acceptance | 6 | Approval false, real sheet untouched → 5.6A |
| PDF/evidence recovery/holds and tombstones | 1 | 5.6 verified implementation; keep policies separate |
| Retention activation and orphan reconciliation | 6 | Distinct approvals unset; never invent periods → 5.6B |
| Complete admin shell, metrics, support, audit and system views | 3 | Static references/isolated forms are insufficient → 5.7A–N |
| Separate worker/scheduler production operation | 3 | CLIs exist, deployed supervision/observations absent → 6.3A |
| Accessibility/RTL release matrix | 2 | Existing 6.2 implementation/tests, full acceptance outstanding; extend to new admin routes |
| Public bilingual behavior | 1 | Existing development evidence; native copy/physical approvals still required |
| Deployment/config/logging artifacts | 2 | Original 6.3 remains IMPLEMENTED; no staging/production deployment asserted |
| Measured performance/capacity | 3 | No accepted load/SLO evidence found → 6.2A |
| Backup/key/private-object recovery acceptance | 6 | No authorized isolated restore/RPO/RTO proof → 6.3B and original 6.3 |
| Controlled pilot/production launch | 2 | Gate validator exists; original 6.4 remains IMPLEMENTED and launch is blocked |

### Complete admin module and endpoint plan

Every module below uses the common 5.7A shell and the security/acceptance contract on its own task card. Existing pages/writers are reused. **PROPOSED** means a planning contract only: reconcile with Doc 04/DB/security, allocate a non-conflicting API ID and approve the field/role contract before coding/exposure. No new endpoint in this plan is claimed implemented.

| Admin module | Pages | Backend contracts / PostgreSQL dependencies | Authorization / task / required proof |
| --- | --- | --- | --- |
| Entry/security | /admin, proposed /admin/security/mfa | Existing Auth/session/roles plus proposed minimal capability read; no direct Auth grants | Live role/AAL every action; 2.3A/B, 5.7A; multi-role union, revoked session, CSRF/IDOR |
| Overview | /admin | Proposed bounded aggregate/trend contract; orders/attempts/pairs/jobs/outbox/cases/audit and narrow registered-user projection | Per-metric capability, not blanket staff; 5.7B; fixture totals, UTC windows, freshness, no leakage |
| Users | Proposed /admin/users and /admin/users/[userId] | Proposed safe directory/detail + separately approved suspend/restore/escalation; user_profiles, narrow Auth state, cases | Approved security/superadmin directory; support case-specific only; 2.3C/D, 5.7C; no medical/password access |
| Inventory/batches/QA | /admin/inventory, /admin/inventory/[pairId], /admin/batches, /admin/batches/new, /admin/batches/[batchId], /admin/qa/[pairId] | API-084/085/088–094; review API-230; tag_pairs, qr_codes, qr_batches, reservations, approval/export records | Explicit ops MFA; security lifecycle approval; 3.5A–C, 5.4A, 5.7D; two-tag/secret/export race checks |
| Products/catalog | Existing /admin/products and approved ADM-20–24 editor/detail routes | Existing API-220–229, products/categories/variants/images, frozen order lines | Existing explicit catalog role list + MFA; 5.1A; publication/version/archive/media tests |
| Orders/payments/reconciliation | /admin/orders, /admin/orders/[orderId], existing /admin/payments and approved payment detail | API-080/081/082, normalized API-240/241, legacy review delegates only; attempts/reviews/reservations/order snapshots | Ops versus finance projections; finance review requires finance MFA; 5.3A–C, 5.7E; exact amounts/dedupe/holds |
| Print/reprint | Proposed /admin/print-jobs list + existing /admin/print-jobs/[jobId] | Proposed global list; existing API-233–237, jobs/artifacts/QA/grants | Ops MFA, current entitlement and approved physical release; 5.7F; lease/grant/QR revocation tests |
| Fulfillment/shipping | Existing /admin/ready-to-ship, /admin/shipments; reviewed new/detail deep links | API-232/095/096 and approved shipment query extensions from 5.5A; shipments/pairs/snapshots | Ops MFA; finance has no full address/dispatch capability; 5.7G; canonical package transition tests |
| Notifications | /admin/notifications and reviewed detail view | API-101/102, outbox/attempts/template version/worker metadata | Explicit approved ops/security list; no broad finder content; 4.4C, 5.7H; retry ambiguity/cutoff/idempotence |
| Support/privacy | /admin/support, /admin/support/new, /admin/support/[caseId] | API-097–099; proposed detail/status/export/erase contracts; support_cases, safe audit, holds, request checkpoints | Case-specific support; security/legal/finance for high-risk outcome; 5.7I/J/K; identity/hold/replay tests |
| Finance mirror | /admin/finance/sheet-sync | Existing API-238/239 and authoritative sync state/jobs | Existing explicit finance/security/superadmin list + MFA; 5.6A, 5.7L; no bank/Sheets authority leakage |
| Storage/retention | /admin/storage | Existing API-242–245; print/evidence metadata, policies, holds and cleanup intent | Existing permitted metadata reads; holds/recovery security/superadmin only; 5.6B, 5.7L; no direct object browser |
| Audit/security history | /admin/audit | API-100, immutable audit projection and contextual timelines | Explicit authorized security/superadmin; others only approved contextual fields; 5.7M; no raw sensitive details |
| System/operations | Proposed /admin/system | Proposed bounded health/status metadata; queues, safe observations and backup evidence references | Approved operations/security reads; no env/SQL editor; 5.7N, 6.3A/B; unknown/stale/outage tests |
| Staff assignments | Controlled operations runbook; UI only if O-02 approved | staff_roles, provisioning audit, existing Auth operations | Named approved authority, no self-grant or implicit escalation; 2.3B; manual/audited grants initially |

### Administrative permission matrix

This is a **least-privilege planning boundary**, not a new grant. Preserve exact current endpoint guards/RLS until an approved change says otherwise. In particular require_staff checks explicit roles: security_admin/superadmin do **not** automatically inherit operations/finance access. Existing catalog and Sheets endpoints explicitly include broader role lists; payment review/printing/generation/shipping currently require their named operational role. One account can hold multiple independent roles. The owner's operations+finance roles must both survive every task.

| Capability | Operations | Finance | Support | Security admin | Superadmin |
| --- | --- | --- | --- | --- | --- |
| Catalog CRUD | Existing explicit permission | No | No | Existing explicit permission | Existing explicit permission |
| Payment/settlement/evidence review | No | Existing explicit permission | No | Only with explicit finance grant/approved change | Same, no implicit finance override |
| Generate batches / print / QA / pack / ship | Existing explicit permission | No | No | Only explicit ops grant/approved change | Same, no implicit ops inheritance |
| Orders | Operations projection incl audited necessary shipping | Finance masked projection | Approved case projection only | Approved contextual scope | Approved explicit scope |
| Sheet sync read/retry | No unless also granted finance | Existing explicit permission | No | Existing explicit permission | Existing explicit permission |
| PDF/evidence inventory | Existing permitted metadata only | Existing permitted metadata only | No blanket access | Existing permitted metadata | Existing permitted metadata |
| Legal holds / cleanup recovery | No | No | Request/escalate only | Existing explicit permission | Existing explicit permission |
| User directory | No blanket access; aggregate capability needs approval | No blanket access | Approved case-specific subset | Proposed scoped read | Proposed explicit scoped read |
| Suspend / restore / staff roles / erase approvals | No | No | Escalate | Only approved authority in 2.3B/D/5.7K | Only approved authority; protect self/last-admin cases |
| Support queue / notes | Contextual case if approved | Financial case if approved | Proposed case-scoped service | Explicit approved case scope | Explicit approved case scope |
| Outbox / audit / system | Proposed safe outbox/system; no blanket audit | Own finance-context evidence | Approved case metadata | Proposed safe outbox/audit/system | Explicit approved projections only |
| Medical/precise finder content | No blanket access | No blanket access | Only separately approved case need | Only audited, separately justified case need | Same; role is not unconditional consent |

Every new staff surface must have current MFA, backend authorization and safe no-store responses; sensitive changes also require signed recent authentication, reason, confirmation, version/idempotency and audit according to the approved contract. Menu visibility is convenience, never authorization. No arbitrary SQL execution, unrestricted environment editor, production secret viewer, mass data export or hidden privilege escalation.

### Dashboard metric register — counting rules before charts

All results are server-side PostgreSQL projections with an explicit counting unit, permission capability, as-of timestamp, UTC half-open range and requested display timezone. Charts must say which timestamp/state is used. Aggregation must not multiply rows through items/attempts/pairs. Counts and financial amounts require the same authorization discipline as detail records.

| Metric | Authoritative definition and guard |
| --- | --- |
| Registered users | Distinct retained Auth identity IDs in approved environment, with verified/suspended/deletion-pending breakdowns separately defined. No total reconstructed from sessions or user_profiles. Narrow approved count helper; no runtime Auth-table SELECT. Role visibility requires approval. |
| Active/inactive QR identities | Count distinct current qr_codes, separately by unactivated/active/owner_disabled/admin_suspended/revoked. Effective live/public status additionally checks active pair and publication. Do not equate status=active with published medical consent. |
| Products / variants / pairs | Distinct products by draft/published/archived; variants separately. Distinct pairs by ownership/inventory state, separate from two current tags and any number of physical copies. |
| Available/reserved inventory | Reuse canonical eligible reservation/allocation predicates. Reserved pair units with active payment review do not become free merely because a timer elapsed; show holds/reconciliation separately. Low-stock threshold needs approval. |
| Orders / payment status | Count distinct orders by independent order/payment/fulfillment state; pending finance queue counts distinct submitted/under_review attempts, with reviewed backlog definition approved by finance. Never count screenshots as settled orders. |
| Verified settlements / revenue | Exact Decimal per-currency verified settlement records, deduplicated by authoritative settlement identity. Explicitly name gross verified amount and time basis; refunds/disputes are separate approved events. No profit/net-revenue/refund-adjusted chart until that accounting contract exists. Sheets rows never contribute financial truth. |
| Print jobs / QA | Distinct jobs or artifacts, labelled separately; canonical queued/rendering/ready/dead and artifact-specific QA predicates. Downloading a PDF is not physical QA or shipping. |
| Pending shipments / ready-to-ship | Distinct shipments by preparing/packed/dispatched/exception/returned; unshipped eligible orders are separate and reuse 0018 checks. Delivery timestamps require trusted approved evidence, not a provider guess. |
| Failed notifications / worker exceptions | Outbox events, attempts and durable jobs counted separately; retryable/dead/ambiguous/leased-expired status mapped to actual stored enums. Show last observation/lag and approved alert threshold. A retry attempt is not a new finder message. |
| QR activation / operational trends | Pair activations from consumed intents/immutable activation evidence by approved time bucket; order/settlement/dispatch trends use their own canonical event time. No fake historical scan series from rate-limit counters or invented geolocation analytics. |
| Pending support/privacy | Distinct open/investigating cases; distinguish account-deletion marker from generic privacy case. Export/erasure completion counted only from approved execution evidence, not request creation or case closure. |
| Recent security/audit | Bounded role/case-scoped event metadata, action codes, timestamps and safe resource/actor IDs. No blanket raw reason/details payload or sensitive profile field. |
| Actionable operational warnings | Document predicate, severity, owner, runbook, threshold and observed freshness. Missing configuration/data is unknown/unconfigured, not zero or healthy. Reconciliation warnings never mutate bank/order state. |

For fixtures, use explicit expected numbers including duplicate child joins, one pair with many copies, multiple attempts for one order, refunds/disputes, held expired reservations and timezone boundaries. For production queries require query-plan, bounded range/paging, role-denial and freshness/error evidence. New aggregate endpoints need contract approval; do not sum all pages in the browser.

### Admin UI/UX completion contract (all 5.7A–N modules)

Reuse current design tokens/components and approved mock-ui visual direction without its sample numbers. Shared desktop sidebar and mobile accessible drawer; logical groups, breadcrumbs and role labels; English/Urdu content, RTL logical layout and isolated IDs/currency. Add real sorting/search/filter URL state, bounded cursor pagination, labelled tables/forms, confirmation dialogs with focus return, pending/disabled states, recoverable errors, partial-widget failure, empty states and safe success feedback. Charts need a text/table equivalent. Test keyboard/focus, screen-reader semantics, zoom, reduced motion, forced colors, contrast, touch targets and narrow/large widths. Never persist private rows, payer data, signed capabilities, MFA secrets or export contents in browser storage; never load third-party analytics with sensitive payloads.

### Optional / decision-only register — excluded from the 70 task total

| Decision | Disposition |
| --- | --- |
| O-01 Pair transfer completion / gifting outside approved claim rules | P1; security/consent/ownership protocol required. Keep transfer completion UI hidden and API-033 gated; no independent Tag A/B transfer. Current gift PRD12-DEC-04 review remains. |
| O-02 Self-service staff assignment UI | Current docs have no dedicated role-management API. Controlled audited provisioning in 2.3B is mandatory; dashboard grants/editor only after explicit authorization model/contract approval. |
| O-03 Broader email/notification preferences or marketing | Do not silently let users disable essential transactional/security notifications or claim a global opt-out exists. Approve purposes/delivery/consent rules before adding a task. Existing WhatsApp opt-in remains verified. |
| O-04 Automatic gateways, bank feeds, WhatsApp Cloud sending, future products/reuse and template designer | Preserve P1 flags and provider abstraction. No new gateway/webhook, automated settlement, non-sticker launch, pair splitting or free QR download without a change request. |
| O-05 Live template editing / safe configuration writers / custom scan analytics | Reviewed file/config deployment and read-only status are the default. Any runtime editor requires an explicit field/action allowlist, version/audit/rollback and security approval; no arbitrary env, SQL, raw-token or location analytics. |
| O-06 Refund execution / automated disbursement | Requires an explicit channel, eligibility/amount/authority/entitlement contract and a separately activated scoped implementation task. Mandatory 5.3B records dispute decisions and approved-or-disabled refund policy; it does not authorize real fund movement. |


## 4B. Dependency overlays, production acceptance and decisions

### Execution order and scope boundaries

Task IDs are stable anchors, not permission to ignore dependency edges. All additions are after their owning original milestone in the phase catalogue. Earlier phases may depend on a later **already verified** foundation (for example 4.4B reuses 5.7's case representation); this does not invalidate the original phase. A TODO may start design/synthetic work once its prerequisites are available. A BLOCKED task names a real policy/configuration/authority dependency; never invent a value or treat elapsed time as approval.

1. **2.3A and 5.7A are IMPLEMENTED**, with owner-controlled MFA and manual acceptance outstanding. The local staff console now reuses existing operations+finance capabilities; request another task separately.
2. Complete **2.3C, 3.5A, 3.5B, 5.3C and 5.5A** query/lifecycle foundations, then **5.7C/D/E/F/G**. Reuse current forms and settlement/print/shipment writers.
3. Build **5.7B** from approved bounded metric projections, and **5.7H/I/L/M/N** for notifications, support, retention, audit and operations. Unimplemented cards/actions must be unavailable rather than backed by sample data.
4. Complete **5.1A, 5.2A, 4.4B/D and 5.7O**, retaining all existing checkout/profile/recipient invariants.
5. Resolve decisions for **2.3B/D, 3.5C, 4.4A/C, 5.3A/B, 5.4A, 5.6A/B, 5.7J/K**; work on independent approved tasks while blocked. Policy decisions may explicitly exclude an optional feature; no mandatory feature is silently declared complete.
6. Perform original **2.3 and 6.1–6.4** acceptance and the new **6.1A/6.2A/6.3A/B** work in dependency order. Do not start those implementations as part of this planning request.
7. Launch only after every applicable mandatory gate below has signed current evidence. New optional features require approval and their own tests/tasks before enablement.

**Original-task status overlay (no redefinition or downgrade):**
- 2.3 remains IMPLEMENTED; its original confirmation/recovery/password-change acceptance still needs authorization and evidence, not another auth rewrite.
- 6.1 remains IMPLEMENTED. Final expanded critical-journey acceptance covers applicable completed Phase 2–5 follow-ups; 6.1A automates repeatability after that scope is accepted.
- 6.2 remains IMPLEMENTED. Its final acceptance must include the expanded admin routes, public-help semantics and new UI states; performance is separately 6.2A.
- 6.3 remains IMPLEMENTED. Existing configuration is not deployment/restore proof. New 6.3A/B are prerequisites for the relevant worker/DR production gates, not evidence that 6.3 has already passed.
- 6.4 remains IMPLEMENTED. The existing gate validator and physical/pilot criteria remain; it must consume actual approvals and measurements rather than fabricate signs of completion.
- Original Phase 3/4/5 DONE statements below describe the original verified development scope. Expanded phase scope is pending follow-ups; no VERIFIED task is changed to incomplete.

### Production acceptance gates — all applicable rows must pass

For each gate store the immutable code/config/migration version, environment, UTC test time, approved fixture/real-data boundary, command or manual procedure, actual result, expected result, sanitized evidence location, approving owner and recovery/rollback path. Reuse the existing pilot gate record; do not invent an already deployed gate store. NOT RUN, unconfigured, stale, partial, interrupted and unknown evidence are not PASS. A development VERIFIED state alone cannot satisfy staging/production acceptance.

| Gate | Required evidence / stop condition | Owner and task mapping |
| --- | --- | --- |
| G01 Auth and staff access | Actual authorized signup/confirmation/recovery/password-change and MFA/session revocation; no role/AMR/CSRF/IDOR bypass. No real email or account change without explicit authorization. | Security/owner; 2.3, 2.3A–D, 5.7A, 6.2 |
| G02 Customer critical journeys | Staging scan→login→saved activation return, multiple independent Lost/ICE profiles, quote/address→manual payment review→allocation→PDF/QA→packing/dispatch/delivery, inbox/privacy request; include rollback/concurrency/outage paths. | Product/engineering/finance/ops; 6.1/6.1A and owning verified services/follow-ups |
| G03 Admin/staff journeys | Role-aware /admin navigation, every allowed module, forbidden direct API/URL/RSC access, revoked roles/MFA and contextual data; preserve multi-role separation. | Security/ops/finance; 5.7A–O, 6.1/6.2 |
| G04 Payments/reconciliation | Approved bank instructions and independent exact settlement evidence, duplicate references, unpaid/rejected/review-held orders, cancellation/dispute policy and disabled optional refund/gateway paths; no incidental real payments. | Finance; 5.3A–C, 5.7E, 6.1 |
| G05 Real provider acceptance | Separately recorded actual Resend receipt/domain, Turnstile allowed-domain/proof flow, Cloudinary disposable image upload/attachment, private Storage upload/read/anonymous-denial/delete recovery and dedicated authorized masked Sheet upsert/reconcile. Existing single received email is retained evidence, not authorization for another send. | Provider owners/security/finance; 4.4A/C, 5.1A, 5.6A/B, original 6.3/6.4 |
| G06 Physical QR/artwork | Approved licensed artwork/fonts/native copy and immutable template fingerprints; measured symbol/label/quiet zone/logo/print scale, materials, packing/credential custody and real phone/lighting scan matrix. Printing remains disabled before approval. | Founder/print/security; 5.4A, 6.4 and physical SOP/print amendment |
| G07 Authorization/privacy abuse | Cross-owner/recipient/role/MFA, token enumeration/rate/challenge, injection/CSRF, private evidence/export, sensitive HTML/RSC/log/browser-storage canaries and no unintended medical/location disclosure. | Security; 3.5B/C, 4.4A/B, 5.7C–O, 6.2 |
| G08 Encryption/secrets | Environment separation, key-version round trip/rotation/recovery, server-only provider secrets, narrow runtime roles, controlled custody and production native rendering; no credentials in bundles/CI evidence. | Security/platform; existing crypto/roles, 2.3B, 5.7J/K, 6.3A/B |
| G09 Privacy/retention | Signed distinct PDF/evidence/message/account/export policies where applicable, identity/authority review, holds, active work/delivery/reconciliation, provider cache/backup treatment and truthful delayed erasure. Requests/case closure are not erasure proof. | Legal/security/finance/ops; 5.6B, 5.7I/J/K/O |
| G10 Backup/restore/DR | Approved RPO/RTO and retention, isolated actual restore, private objects and key custody, exact integrity/hold/lease/provider-state reconciliation, measured cutover and recovery/rollback drill. Backup presence alone fails this gate. | Database/security/ops; 6.3 and 6.3B |
| G11 Worker reliability | Separate deployed worker/scheduler commands; kill/restart, lease expiry/fencing, ambiguous delivery/deletion, bounded retries/dead letters, backlog recovery and alert receipt. No admin-credential fallback or unapproved retention daemon. | Platform/ops; 6.3A and original 4.4/5.4/5.6 |
| G12 Performance/capacity | Approved workload/data size/device/concurrency and p95/p99/resource/queue budgets; actual API/DB/frontend/render results and connection/cost limits meet those budgets. No invented pass thresholds. | Product/platform; 6.2A |
| G13 Responsive/accessibility | Desktop/laptop/tablet/mobile, keyboard/screen-reader/zoom/focus/contrast/touch/reduced-motion/forced-colors; all empty/loading/partial/failure/confirmation states and chart alternatives. | UX/accessibility; 6.2, all new admin modules |
| G14 English/Urdu | Public safety/consent/legal/help, owner forms and requested administration; native copy review, real RTL/long identifiers/numbers and rendering/print shaping. | Native reviewer/UX/print; 4.4C/D, 5.7A–O, 6.2/6.4 |
| G15 Deployment/rollback | Authorized isolated staging first, reviewed migrations and current head, actual restricted runtime logins, secured readiness, fixed origins/TLS, compatible API/worker/frontend release and rollback/drain rehearsal. No automatic production migration or deployment. | Release/database/security; 6.3/6.3A/B |
| G16 Monitoring/support | Real alert delivery, severity/owner/runbook, queue/provider/backup/availability freshness, cost/connection alarms and staffed escalation. Green liveness or config presence cannot substitute. | Ops/support/security; 5.7H/I/N, 6.3/6.3A |
| G17 Pilot and go/no-go | Explicitly authorized real pilot with informed participants, successful customer/staff/physical journeys, reconciled incidents, rollback readiness, signed acceptance and continued post-launch observation. | Founder plus finance/security/ops; original 6.4 |
| G18 Commercial/legal readiness | Approved SKU/price/tax/shipping/bank instructions, carrier/delivery evidence, public policies/support contacts and optional-feature decisions; missing approvals keep checkout/printing/relevant functions disabled. | Founder/finance/legal/ops; 4.4D, 5.1A–5.6B, 6.4 |

### Decisions, credentials and approvals still required

No secret values belong in this file. Existing ignored configuration, roles and credentials must be preserved. This plan adds no implied authorization for any live action.

| Decision / external gate | Required owner decision or secure configuration | Affected work |
| --- | --- | --- |
| D01 Staff powers and metric visibility | Explicit roles/capabilities (no implicit superadmin inheritance), support case fields, aggregate user/finance counts, self/last-admin protections, onboarding/revocation and factor recovery | 2.3A–D, 5.7A–N |
| D02 Identity, privacy and data scope | Verification for export/erase, third-party finder/contact redaction, case access/notes, response times and reviewed legal authority | 5.7I/J/K/O |
| D03 Distinct retention policies | Separate signed PDF/evidence/message/account/export/caches/backups policies and safe orphan/late-upload rules; PRD12-DEC-05/06 remain unresolved, candidate durations are not approvals | 5.6B, 5.7J/K, 6.3B |
| D04 Cancellation/dispute/refund | Reservation/payment-review grace and reconciliation, cancellation cutoff, dispute consequences, approved-or-disabled refund policy and any later O-06 implementation authority | 5.3A/B/C, 5.7E |
| D05 QR lifecycle/manufacturing | Replacement/compromised-label entitlement and custody; PRD12-DEC-04 gifting review, batch export printer protocol and current-token reprint rules | 3.5B/C, 5.4A, optional O-01 |
| D06 Public safety/abuse/copy | Trusted proxy topology, live Turnstile domains, explicit emergency fallback decision, abuse/moderation SLA and native/legal/sender copy | 4.4A–D |
| D07 Actual integrations | Supabase project/private buckets and runtime access, approved Resend sender/domain, Cloudinary account/preset/folder, Turnstile keys/domain, restricted Google service-account JSON/spreadsheet/tab/header/sharing | 4.4A/C, 5.1A, 5.6A/B, G05 |
| D08 Commercial/physical launch | PRD12-DEC-01/03/09/10/12: prices/sizes/materials, shipping/tax, review grace, artwork/fonts/native copy, carrier proof and screenshot policy | 5.1A–5.5A, 6.4 |
| D09 Recovery/operations | RPO/RTO, backup/private-object coverage, key escrow/custody, restore target/access, worker deployment identity/concurrency/scheduling, on-call and alert destinations | 5.7N, 6.3A/B |
| D10 Measurable release budgets | Representative workloads, latency/throughput/error/queue/cost budgets, inventory/backlog/lag thresholds and actual pilot/physical device matrix | 3.5A, 5.7B/N, 6.2A/6.4 |
| D11 Live-action authorization | Separate permission before actual emails, provider writes, payments/refunds, real object erasure, managed Auth changes, physical release, backup restoration or staging/production deployment | All manual/provider/release gates |
| D12 Proposed API contracts / optional scope | Review new directory/capability/aggregate/shipment-detail/print-list/privacy/status/health contracts in Doc 04/DB/security; optional O-01–06 require explicit activation before new implementation tasks | Relevant TODO design steps; no silent endpoint invention |

### Evidence and safety protocol for every future task

Use the existing workspace and preserve all unrelated uncommitted work; no worktrees/commit/push/deployment without the owner's instruction. Inspect actual source and Git state first. Reuse verified services and update only the scoped missing behavior. For schema changes: inspect installed revision/dependencies read-only, rehearse on isolated synthetic schemas with exact row/role/DDL fingerprints, review a forward migration and require authorized development application; never run a catch-all upgrade or rewrite an old applied migration casually.

Use bounded focused backend/API/real-PostgreSQL/worker/browser tests appropriate to the change. Default providers are synthetic, destructive tests use fresh preflight-absent exact-key owned objects, and cleanup is limited to verified UUID namespaces/NOLOGIN roles. Handle stale connections/DNS/suspension with the existing preservation/awake/reconnect approach; never replay a mutation because a readback timed out. Record partial/interrupted runs and explicit skips honestly. Keep unconfigured integrations fail closed. Separate local development verification, real staging-provider acceptance and production release sign-off in the evidence ledger.

Implementation may proceed only when separately requested. New-task completion needs its own passing acceptance and evidence; none of the 39 additions is complete today. A valid policy deferral must be explicit and cannot erase a required launch gate or relabel a blocked implementation VERIFIED.

### Phase summary

Only edit this section after *actual* progress. Keep entries short. Do not create a new log file per task.

**Expanded scope (planning change, not a downgrade of verified tasks):**

| Phase | Current roadmap state | Preserved original evidence / new work |
| --- | --- | --- |
| 0 / 1 | Original DONE unchanged | 3 / 5 original VERIFIED tasks; no new foundation/schema rewrite |
| 2 | Original acceptance + follow-ups pending | 2 VERIFIED, 2.3 IMPLEMENTED; MFA IMPLEMENTED (interactive acceptance pending), directory TODO, provisioning/suspension policy BLOCKED |
| 3 | Original DONE; new lifecycle/query work pending | All five originals VERIFIED; 3.5A IMPLEMENTED, 3.5B TODO, 3.5C BLOCKED |
| 4 | Original DONE for development; new safety/provider/policy work pending | All four originals VERIFIED; four new follow-ups, no repeat notification implementation |
| 5 | Original DONE for development; admin/compliance expansion pending | All seven originals VERIFIED; 24 new follow-ups, 5 IMPLEMENTED / 12 TODO / 7 BLOCKED |
| 6 | Original IMPLEMENTED, acceptance not complete | Four originals unchanged; CI/performance/worker follow-ups TODO, DR policy/access BLOCKED |

#### Original phase summary retained (pre-expansion baseline)


| Phase | Status | Evidence / main files | Remaining issue |
| --- | --- | --- | --- |
| 0 — Foundation | DONE | All 3 tasks VERIFIED: backend startup, frontend production build, typed local integration + 16 checks and outage check | Database readiness belongs to Phase 1 |
| 1 — Database | DONE | All 5 tasks VERIFIED; installed `0004_runtime_privacy`; 201 backend tests including 174 real PostgreSQL checks; isolated clean-install/upgrade/race/recovery evidence; Alembic consistency PASS | No Phase 1 blocker; service/API, cryptography and operational release checks remain later phases |
| 2 — Authentication | IN PROGRESS | 2.1/2.2 VERIFIED; 2.3 IMPLEMENTED; user confirms signup/sign-in; prior 84 local + 39 web + 16 account + 7 live login/security checks pass | Confirmation/recovery/password-change browser acceptance |
| 3 — QR management | DONE | All 5 tasks VERIFIED; 107 combined Phase 3 PostgreSQL checks and 106 local checks PASS; ownership-read revocation fix; installed head 0011 unchanged | Activation/printer configuration, prior 5-hour clock skew/live provider acceptance, allocated-gift review and physical/proxy release gates remain |
| 4 — Public scans | DONE for development | 4.1–4.4 VERIFIED for development; applied through 0014a; Task 4.4: 17 focused integration, 6 browser, 16 restricted-login, 159 local checks and one live received email PASS | Live Turnstile, credential/security review and production/physical release gates remain; not a production-readiness claim |
| 5 — Remaining features | DONE for development | 5.1–5.7 VERIFIED for development; final Task 5.7 four DB/API and two browser checks, 261 local tests; installed 0019 unchanged | Real print/packing/carrier acceptance, MFA setup/role-aware admin landing, Cloudinary real upload, policy-bound retention and production gates remain |
| 6 — Integration/release | IN PROGRESS | 6.1–6.2 IMPLEMENTED with fixes (unverified per instruction); Copilot implementations for 6.3–6.4 present | Tasks 6.3–6.4 await verification/refinement |

**Allowed task states:** TODO · IN PROGRESS · IMPLEMENTED · VERIFIED · BLOCKED. Phase DONE requires its complete acceptance criteria.

### Historical handoff — Task 5.7 completion before this planning revision
- **Date/current task:** 2026-10-18 (Asia/Karachi). Task 5.7 VERIFIED for development; Phase 5 DONE for development. Total 31: 26 VERIFIED, 5 IMPLEMENTED (2.3, 6.1–6.4).
- **Inbox:** Stable tied pagination, original-recipient isolation, safe encrypted location reads, QR/email-delivery context, status/filter/paging controls and confirmed idempotent deletion requests. Hiding preserves encrypted records, consent, outbox and legal holds; no physical erasure policy invented.
- **Account:** Added canonical API-022 consent-history metadata and API-023 reviewed deletion requests. Strict confirmation, verified email, signed recent AMR, encrypted optional reason, concurrent dedupe and minimal atomic audit; accounts/orders/pairs/history remain intact.
- **UI:** Authenticated server actions enforce exact Origin; settings uses existing controls plus privacy history/request; public English/Urdu help works without login/JavaScript. No browser storage of messages or reasons.
- **Evidence:** Final four-case 0019-schema DB/API suite PASS (206.47s); two Playwright checks PASS (21.6s), including Urdu mobile/no-JS help. Focused original-recipient check PASS (145.42s) and corrected account scenario PASS (124.32s). Earlier fixture-order failure is not a clean-suite claim.
- **Regression:** 26 actual restricted-login checks passed within a 29-case run (255.98s); 261 local tests PASS (10.74s), build/typecheck/scoped Ruff/format/diff PASS. No new runtime grants or schema changes.
- **Preservation:** Exact installed rows/roles/DDL preserved. Head 0019; 43 domain RLS tables (44 including Alembic), five existing domain rows; zero installed orders/payment attempts/shipments/finder messages/support cases and zero temporary schemas/roles. User retains operations+finance.
- **Runtime:** http://localhost:3031; API 8030. Home/help/catalog/liveness 200; inbox/settings redirect; anonymous inbox/consent/deletion APIs 401. Actual OpenAPI has API-022/023; readiness remains disabled/unconfigured.
- **Gates:** Actual erasure/review procedures, message-policy timing, data-export/address-management contracts, Task 2.3 acceptance, MFA/admin landing, live Turnstile/Cloudinary/Sheet, separate PDF/evidence approvals, physical/production gates remain. Printing disabled; Sheets approval false.
- **Safety/next:** No migration, credential/ignored-file edit, real user deletion/review request, payment/email/Sheet/storage write, deployment, worktree, commit or push. Stop before Task 6.1; await the user's next instruction.

### Latest handoff (update in place, max ~12 lines)

- **Date/task:** 2026-10-19 (Asia/Karachi). Task 5.7I IMPLEMENTED pending gates; stop before any other task. 5.7G/H remain IMPLEMENTED with their recorded gates intact.
- **Counts:** 70: 26 VERIFIED, 12 IMPLEMENTED, 0 IN PROGRESS, 19 TODO, 13 BLOCKED. Register summary reconciled with task cards; no prior task status changed.
- **Approved behavior:** Canonical API-097/098/099 only; redacted unassigned metadata, atomic self-claim, assigned-agent private detail/encrypted notes/audited history; foreign cases 404. Owner approved this conservative scope explicitly. No reassignment, security hold commands or high-risk resolution.
- **Guards/privacy:** Existing signed JWT/live session/email/AAL/explicit support and shell reused. Finance/operations/security/superadmin alone denied. Restricted legacy API-023 reasons never decrypted; closure does not erase, transfer ownership or settle payment. Encrypted idempotency receipts and revisions fence duplicate/stale/concurrent commands.
- **Migration:** 0021_support_case_console APPLIED with explicit owner approval on 2026-10-19; SHA-256 342fc6721d0c1af2108e82e53cb55b13d3408ccedfe1f51525f5ac932c255b12. Add three safe-default case columns, RLS/append-only encrypted history, three scoped API functions and non-callable finder-hold lock trigger. Hash-locked application runner precommit preservation and fresh readback PASS; installed head now 0021. Exact original domain/Auth/factor values, staff roles, prior DDL/grants and role memberships preserved; only approved additive objects installed. Runner scoped Ruff/format PASS.
- **Local evidence:** 17 staff-security tests PASS (1.98s); 12 navigation-contract checks PASS (1.3s); frontend typecheck, isolated production build including proxy/support routes and scoped Ruff PASS. Formatting corrected and checked. No full suite.
- **API evidence:** Initial six fixture-verifier failures corrected; six focused cases PASS / one browser deselected (234.06s). Roles/AAL, IDOR, safe projections, restricted legacy reason, concurrent claim/edit, encryption, idempotency, append-only/stale/closed history and three high-risk types covered. No clean combined-suite claim.
- **Final targeted evidence:** 2 PASS / 6 deselected (241.66s): final 0021 rollback/reapply/ACL checks, order/finder hold serialization, deletion-intent admission refusal and owned cleanup/installed catalog preservation. Earlier 2-failure run (387.82s) corrected only synthetic settlement metadata/select selectors; no clean combined-suite claim. Corrected bounded browser scenario PASS (1.4m): intake/queue/detail, closure/stale refresh, IDOR and finance URL/RSC/API denial, safe projections, mobile RTL/storage. Inspected output/task57i/loaded-rtl.png; failed output retained separately.
- **Runtime/build paths:** Existing http://localhost:3031 and API8030 health 200; configured authentication untouched. Running frontend remains tmp/task57h-web via tmp/task57h-restore-frontend.py. New isolated tested source/build tmp/task57i-web; isolated ports3100/8115 and tmp/task57i-* output only.
- **Preservation:** Owner uaa007079@gmail.com still finance+operations, 0020 retained in the chain; current head 0021. Earlier output/task57h/loaded-rtl.png intact; G screenshots remain historically missing as recorded, never regenerated. Unrelated dirty work and ignored environments preserved.
- **Remaining/safety:** Local runtime promotion (3031 still serves the previous tested H build), human support/security synthetic intake/escalation/audit drill, native Urdu/accessibility and SLA/copy/owner acceptance. Export/erase stays 5.7J/K. No real Auth changes, contact/replay/dispatch/payment/email/Sheets/storage write/deletion, worktree, commit, push or deployment.
