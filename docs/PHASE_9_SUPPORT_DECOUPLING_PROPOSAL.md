# Phase 9 — Support Cases & Financial Review Decoupling Proposal

Date: 2026-10-24 (Asia/Karachi). **ARCHITECTURE PROPOSAL ONLY — NOT IMPLEMENTED, NOT AN ALLOWLIST CHANGE.**

`backend/docs` does not exist; this proposal uses the existing repository `docs` directory. No application, endpoint, migration, configuration or protected workflow is changed. All five original operations remain quarantined. New paths and DTOs below require approval and separate implementation; operation IDs remain unassigned pending contract review.

## 1. Executive summary

The architectural problem is shared context/admission, not simply a frontend exposing a pair button. Generic support details combine case content with order/pair-derived retention context. Generic updates take order/pair locks before even claiming a case; updates additionally calculate protected closure eligibility. Inserts and certain status updates independently trigger retention admission. Financial reads, history and decisions share a context helper that locks the full order/payment/unit/pair/case/authority aggregate.

Separate metadata reads are feasible without changing those workflows. Narrow notes, priority and claim commands are technically separable for unrelated ordinary cases, subject to proving eligibility and concurrency under existing triggers. Non-QR creation is **not presently independent**, because the existing insert trigger executes a pair-table query even for null references. General status changes and every financial decision remain blocked. A reduced financial metadata/history view is feasible for **pair-unbound, explicitly provisioned payment cases**; it must not compute full review readiness, package exceptions, ownership validity or settlement approval.

No data-table migration or duplicate case state is proposed for the first reads. Narrow privileged SQL helpers and EXECUTE grants will nevertheless need an additive, reviewed database deployment; existing finance tables are intentionally inaccessible directly to the API role. Installed schema is unverified. No live acceptance environment is confirmed.

## 2. Evidence and current transaction model

Reviewed sources:

- Approved Documents 02 Technical Design, 03 Database Design, 04 API Contract (API-097–099 and owner-approved API-323/324 addendum), 07 Security/Privacy; Document 13 blocked contract review, BTR-07; `docs/BACKEND_GAP_TRACKER.md` (DB-01/02, AUTH-01, API-01, WEB-01, CFG-01, RET-01).
- Corrected `frontend/ADMIN_BACKEND_API_INVENTORY.md`, `ADMIN_FRONTEND_BACKEND_MAPPING.md`, `ADMIN_BACKEND_INTEGRATION_PLAN.md` and Phase 2–9 entries in `ADMIN_BACKEND_INTEGRATION_PROGRESS.md`. Earlier approved financial design does not override this task's absolute pair exclusion.
- `backend/app/main.py`: support router registration and `install_financial_disputes`.
- `backend/app/api/auth.py`: `get_principal`, `get_auth_context`, `authorize`, `require_staff`; `backend/app/db/runtime.py:api_transaction`; `backend/app/db/session.py:Database.transaction`.
- `backend/app/api/v1/support_cases.py`: `Intake`, `Change`, `command`, `cases`, `create_case`, `update_case`; `backend/app/db/abuse_intake.py`: `available`, `case_clause`, `case_policy`.
- `backend/app/api/v1/financial_disputes.py`: all DTOs, `guard`, `load_context`, `evaluate`, `review`, `decide`, cursor helpers; `privacy_exports.py:recent`; `catalog.py:Closed`, `CatalogRoute`.
- `backend/alembic/versions/0003_workflows_security.py`: support schema/RLS; `0019_retention_recovery.py:sr_retention_admission`; `0021_support_case_console.py`: context/create/change/events; `0025_financial_disputes.sql`: bindings/grants/context/history/apply/fences/guards; `0030_account_lifecycle.sql`: current financial context and account-epoch/session admission; `0035_public_abuse_intake.sql`: abuse policies, support wrapper and update guard.

Bearer JWT verification validates the principal; `Authenticated` enters `api_transaction` as `safereturn_api`, sets transaction-local actor context and calls `sr_account_session_state`. Signed MFA claim must agree with current provider session AAL2. `require_staff` checks verified email, MFA and an explicit non-revoked requested role; superadmin does not inherit Support or Finance. The function-scoped yield dependency commits/rolls back before sending the protected response. SQL exceptions become unavailable errors. No network/provider I/O belongs inside proposed row-lock sections.

`support_cases.command` requires Idempotency-Key (8–160 characters, `[A-Za-z0-9._:-]`), takes a scoped advisory transaction lock, hashes the body, reads an encrypted receipt FOR UPDATE, and rejects changed-key reuse. Fresh work executes inside a savepoint; receipt encryption/storage and the enclosing transaction are atomic. Standard receipts expire after one day; abuse-linked handling has separate policy/expiry/reauthorization. SQL work writes its own events/audit, not `command` itself. Reusing this helper wholesale is not an independence or replay-authorization proof.

## 3. Exact root causes and endpoint dependency table

Classification: **A** incidental coupling for a smaller operation; **B** needed for particular categories/actions; **C** essential to the original full operation; **D** security/ownership/financial consistency requirement. A dependency can be A for a new projection while remaining C/D for the existing operation.

| Endpoint and models | Actual reachable chain, locks, side effects | Classification and conclusion |
|---|---|---|
| API-097 GET `/api/v1/admin/support-cases`; query parameters, no explicit Pydantic response_model | `cases` → Support guard → bounds/cursor → abuse policy clause → scoped SELECT. Only unassigned or actor-assigned cases. `case_id` is the actual detail selector. Assigned detail reads encrypted description/reference fields → `sr_support_context` → `order_pair_units`, finder messages/`qr_codes`, artifact/evidence/retention relations; decrypts modern description and event notes, bounded history; writes `support_case.read`. List alone does not invoke context. | **A/B** for metadata versus assigned details; **D** for retention/closure facts. New metadata route can omit enrichment, but original mixed API stays quarantined. Do not claim list-only payloads authorize API-097. |
| API-098 POST same collection; `Intake`, untyped helper JSON receipt | Support guard → encrypt description → `command` → `sr_support_create` → optional pair/order validation → support INSERT → `sr_retention_dispute_admission` → `sr_retention_admission` → pair-linked orders and deletion fencing. Creates actor-opened, actor-assigned case, revision-1 `created` event and `support_case.created` audit; encrypted replay receipt. | Reference validation **B/D**. Trigger admission **C/D** for linked disputes; its unconditional pair query is incidental for a truly unrelated intake but remains reachable. Null frontend fields alone cannot decouple creation. |
| API-099 PATCH `/api/v1/admin/support-cases/{case_id}`; `Change`, untyped receipt | Support guard → abuse case policy and actor/unassigned scope → `command` → encrypted optional note → `sr_support_change` (0035) → abuse gate/closure restriction → `sr_support_change_v34` (0021 body). Order rows first, then `tag_pairs` via `order_pair_units`, then scoped case FOR UPDATE; expected revision/state checks. Claim increments assignment/revision; update calls `sr_support_context` even for note/priority-only edits. UPDATE of status triggers retention admission if NEW open/investigating. Appends `claimed`/`updated` event and `support_case.changed` audit. | Locks/enrichment **A** for narrow unrelated claim/note/priority; **B/C/D** for linked context, closure, retention races. Cannot route a safe command through the old helper. Status-column mention matters even if value is unchanged. |
| API-324 GET `/api/v1/admin/support-cases/{case_id}/financial-review`; `ReviewProjection`, `HistoryEntry` | Finance/feature guard → `load_context(false)` → latest `sr_financial_case_context` (0030): grant/account-epoch checks, immutable binding, order FOR UPDATE, all order attempts FOR UPDATE, order units FOR UPDATE, pairs FOR UPDATE, case and eligible grant FOR UPDATE; membership validation. Reads verified reviewers/review reference, fence, shipments, holds. `sr_financial_case_history` calls the same context **again**, audits `finance.case.read`, returns bounded decisions. AEAD cursor binds case revision. | Shared write-context locks **A** for reduced observation, but membership check **D** for pair-bound cases. Full readiness/exceptions and original guarantees **C/D**. Independent view must omit pair-bound cases and write readiness. Reusing history helper remains unsafe. |
| API-323 POST `/api/v1/admin/support-cases/{case_id}/financial-decisions`; `FinancialDecision` → `DecisionReceipt` | Finance/feature + exact Origin + recent auth → `load_context(true, reference)` **before receipt replay** → case can_decide, no self-provision/settlement-reviewer conflict → `command` → `evaluate` → `sr_financial_case_apply`, which re-enters context and revalidates body/revisions/evidence/dispatch. Increments case revision, appends financial decision; confirm/escalate can add immutable fence, increment order revision via trigger, and move preparing/packed shipment/order fulfillment state to exception. Audit `finance.case.decided`; encrypted receipt. | **C/D**. Aggregate locking serializes evidence, membership, dispatch and fencing. Even investigate/resolve_no_change use this protocol and advance shared revision. No weaker alternate decision route proposed. |

No original endpoint performs an external bank verification merely by rendering review data. Confirmation relies on existing immutable bank-verified review provenance and exact amount/currency; it does not reverse settlement. Resolve-no-change never removes an existing fence. Shipment dispatch can convert confirm-dispute into escalation. Protected financial guards extend downstream allocation/paid claims/printing/download/fulfillment and direct writers; they must remain intact.

### Trigger details that determine the design

`0019:sr_retention_dispute_admission` is BEFORE INSERT OR UPDATE OF status,order_id,pair_id on support_cases, WHEN NEW.status is open/investigating. Its helper executes `UNION SELECT order_id FROM order_pair_units WHERE pair_id=NEW.pair_id`, locks related orders and rejects admission during artifact/evidence deletion. With a null pair parameter it still contains a prohibited relation access; do not base safety on an optimizer skipping it. This protects a dispute from racing irreversible private-evidence deletion.

The original support change locks orders/pairs before case locks to cooperate with retention/printing admission. Resolving/closing payment/privacy/ownership cases or held cases is rejected. Abuse-linked cases cannot be detached or resolved/closed; their policy persists independently of public feature disablement. New metadata projections must not disclose policy-expired content or treat arbitrary `other` cases as ordinary.

## 4. Safe versus protected data

| Existing record | Proposed exposure and limits |
|---|---|
| support_cases.id, case_type, status, priority, case_revision, created_at | Safe bounded metadata within existing queue authorization. Enum values remain activation/lost_tag/payment/privacy/ownership_dispute/other; no new category taxonomy. |
| updated timestamp | No authoritative `updated_at` column found in support schema. Do not invent one or use created_at. Latest event time may be named `last_support_event_at`, not last case update: finance advances revision outside support event history. Initially omit. |
| assigned_staff_id | Existing queue projection reveals only assigned_to_me/can_claim, not arbitrary employee identity. Preserve these booleans and `assignment=mine|unassigned`; no staff directory join. |
| description and event.note | Encrypted free text, not an inherently safe summary. Metadata list/detail never decrypt it. Optional content/history reads only for assigned actor in the restricted ordinary scope below, modern description_format=1, bounded data and existing AEAD bindings. Legacy description remains unavailable; no fabricated summary. User text is displayed as text and may still contain inappropriate sensitive data; policy/redaction review is required before enabling content. |
| support_case_events | Existing append-only created/claimed/updated events; revisions need not be contiguous because finance also increments case_revision. Metadata history may return event ID/revision/type/from/to/priority/created_at without actor IDs or note content; assigned-only. Never manufacture missing events. |
| opened_by_user_id | An opener is not necessarily a customer or verified account subject; staff intake sets it to staff actor. Omit from initial contracts. No safe customer reference available generically without a separately approved subject-binding projection. |
| pair_id, order_id and description_format | Internal eligibility predicates are permitted case-row reads; pair_id is never returned or dereferenced. Support metadata omits related references. Financial view returns only its independently authorized order/attempt binding. |
| financial bindings/authorities/decisions/fences; orders/payment_attempts | Reduced financial metadata and safe decision history under existing explicit can_review grant. No bank/sender/reviewer PII, review notes, evidence objects, URLs or decrypted payment data. |
| QR credentials, pair ownership/lifecycle, finder/medical/recovery data, private evidence, derived fulfillment eligibility | Excluded. No joins, helper calls, SQL grants, prefetch, setup or background tasks through these resources. |

### Restricted ordinary write/content scope (O)

Initial conservative scope: case_type=other, pair_id IS NULL, order_id IS NULL; unassigned/current-actor assignment as appropriate; no abuse report marker, financial binding, account_case_binding, privacy-export case linkage, or account.deletion.requested audit marker. Unknown/missing policy or required relation/helper means unavailable, never assume ordinary. All checks use case/linkage/security tables only, without pair lookup. The client cannot certify this scope.

O is necessary but not automatically sufficient: protected linkage provisioning must serialize with the same case lock and must not race eligibility. Existing provisioning does not universally prove that protocol (e.g. finance binding guard locks the order, not an existing case row). Therefore proposed writes are **conditional design candidates**, not implementation-ready until a reviewed FK/row-lock/provisioning race proof passes; otherwise keep writes blocked. Do not claim an `other` category or null refs proves lifetime unrelatedness. No category/reference/description edits, deletion, hold release or detachment is allowed through new commands.

## 5. Proposed independent API contracts — ALL NOT IMPLEMENTED

Prefix `/api/v1`. Proposed new resource namespace `/admin/support-case-metadata` avoids changing the meaning of quarantined `/admin/support-cases`. IDs are UUIDs. Exact method/path allowlisting only; no generic relay/router permission. All DTOs closed, strict revisions, duplicate/unknown query keys rejected. No operation IDs reserved by this proposal.

### Shared security, transport and errors

Support endpoints: `Authenticated` + `require_staff(context, 'support')`, existing queue/policy and assignment checks; no authority from a frontend preview or broader RLS policy alone. Writes additionally require exactly one approved configured admin Origin, strict confirmed=true and scoped Idempotency-Key; retain current MFA/session checks. No new recent-auth requirement is inferred for ordinary notes/claim/priority, but it may be added only by contract approval. Finance view requires explicit Finance + can_review, revocation and both grant recipient/provisioner epoch validity; no Support privilege inheritance. Missing dependencies/feature/configuration fail closed.

Responses private/no-store, nosniff; safe generic error `{error:{code,request_id}}`, never raw validation text, SQL or submitted content. 400 invalid key/query, 401 unauthenticated/session invalid, 403 explicit role/MFA/Origin denial, 404 inaccessible/missing/ineligible case (same outward behavior), 409 invalid state/key reuse/stale cursor, 412 stale command revision, 422 invalid DTO/cursor, 413 size limit, 503 unavailable/dependency/crypto/lock timeout. Do not use error differences to enumerate protected case IDs. Invalid Origin checked before DB mutation. No automatic redirects, browser tokens/storage or blind mutation retries.

Common candidate write input `expected_revision: strict int 1..2147483646, confirmed: true`; encrypted receipts are actor+case+operation+key scoped. Recheck authorization/O before replay; response is a historical receipt, not current state. Same key/body recovers uncertain results; changed key/body rejects. Expired receipt fails according to approved retention contract, not a new blind mutation. New writes adopt existing one-day ordinary support receipt policy only after policy review; no new retention duration invented.

### P1. GET `/admin/support-case-metadata`

**NOT IMPLEMENTED; recommended first implementation.** Query: optional case_id UUID, case_type existing enum, status existing enum, priority existing enum, queue=all|mine|unassigned (default all), limit strict integer 1–100 (default20), cursor opaque <=2000 characters. No date/free-text/staff-ID filter.

200 `{as_of:UTC timestamp,items:[CaseMetadata],next_cursor:string|null}`; `CaseMetadata={case_id,case_type,status,priority,case_revision,created_at,assignment:mine|unassigned,assigned_to_me:boolean}`. No can_claim readiness assertion on this first read. Scope: `(assigned_staff_id IS NULL OR assigned_staff_id=actor)` AND current abuse readability policy. No encryption/content/context/ownership access. Single bounded query snapshot; sort created_at DESC,id DESC; authenticated opaque keyset cursor bound to actor, normalized filters and version, not a global snapshot. Changed filters reset pagination. Each page reauthorizes. Audit `support.metadata.list` with request ID and bounded count, no search text or case content. No row locks for observations. Tests: filters/cursor/scope/abuse expiry plus forbidden relation/function checks.

### P2. GET `/admin/support-case-metadata/{case_id}`

**NOT IMPLEMENTED; recommended with P1.** No query/body. Same CaseMetadata plus `content_available:boolean` only if assigned and O/content policy satisfied; if eligibility cannot be safely evaluated return false, do not infer an error-free workflow. It is not a write capability. 404 outside current queue; no separately invented old detail endpoint. One bounded snapshot; audit `support.metadata.read`. No pair context or related record expansion. Tests: direct invalid UUID, missing/other-assignee, policy expiry and metadata-only projection.

### P3. GET `/admin/support-case-metadata/{case_id}/history`

**NOT IMPLEMENTED; assigned-only metadata history candidate.** Query limit1–100 default20 and opaque actor/case/revision-bound cursor. Response `{case_id,case_revision,items:[{event_id,case_revision,event_type,from_status:null|status,to_status,priority,created_at}],next_cursor}`. No actor UUID or decrypted note; note-presence may be omitted. Existing events only; no contiguous revision guarantee. Snapshot case authorization/history together; changed revision invalidates cursor with409. Audit `support.metadata.history.read`. SELECT support_case_events retains assigned-only restrictions. Tests include finance-induced revision gaps, policy gating and bounded projection.

### P4. GET `/admin/support-case-metadata/{case_id}/content`

**NOT IMPLEMENTED; conditional content-policy approval.** Assigned actor + O only. Query limit1–100 default20/cursor for note-bearing history. Response `{case_id,case_revision,description:string|null,description_available:boolean,notes:[{event_id,case_revision,text,created_at}],next_cursor}`. Modern description only using existing support_description AEAD; notes use original event UUID/support_note binding. No legacy text, opener, attached records or synthetic history. Fail closed on crypto/schema/policy failure. Audit `support.content.read` without plaintext. Snapshot and cursor rules as P3. Tests verify AEAD subject/purpose, legacy denial, authorization/redaction and zero context invocation. If free-text exposure cannot meet policy, omit P4 and keep notes editor/read unavailable rather than claiming text is sanitized.

### P5. POST `/admin/support-case-metadata/{case_id}/claim`

**NOT IMPLEMENTED; conditional O/concurrency proof.** Body common write input only. O + unassigned + status open/investigating. Assign only actor; no employee input. Scoped receipt advisory lock, case row lock, locked recheck O/current role, expected revision; update **only assigned_staff_id and case_revision** (no status assignment even to itself). Existing assigned-staff FK validation concerns auth.users, not pair tables. Append `claimed` support event and `support_case.changed` audit with reason support_case_claim; commit receipt/event/change atomically. Receipt200 `{case_id,status,priority,case_revision,assignment:'mine'}`. Concurrent claimant gets404 after scope change or409 claim conflict without disclosing assignee; stale authorized claimant412. Tests: double claim, stale revision, linkage race, rollback and replay authorization.

### P6. POST `/admin/support-case-metadata/{case_id}/notes`

**NOT IMPLEMENTED; conditional O/concurrency/content approval.** Body common fields plus `note: trimmed string 4..2000`. O + assigned actor + status not closed. Encrypt existing event-scoped support_note; case row lock and expected revision; update **only case_revision**, append existing `updated` event with unchanged status/priority and note ciphertext. Audit `support_case.changed` with reason support_case_note, no text. Receipt200 `{case_id,status,priority,case_revision,event_id}`; subsequent explicit content read is separate. Same lock/replay rules as P5. No plaintext in receipt/logs, no delivery/customer message. Tests: nonempty/limits, one event on exact replay, crypto failure rollback, lost-response recovery, assignment revocation/O race and protected-trigger nonentry.

### P7. PATCH `/admin/support-case-metadata/{case_id}/priority`

**NOT IMPLEMENTED; conditional O/concurrency proof.** Body common fields plus priority=low|normal|high|urgent. O + assigned actor + status not closed; same priority is409 NO_CHANGE. Locked revision update **only priority and case_revision**, append unchanged-status `updated` event/audit support_case_priority; receipt200 same fields as P5 without assignment. No status/order/pair column in SET list. Tests: no-op, stale version, role/assignment/O, rollback and old triggers unchanged.

P5–P7 independence candidate: new narrowly scoped helper, never sr_support_change/context. Existing retention trigger fires only for listed column updates; these statements do not mention them. Existing abuse guard still executes and remains intact; O excludes abuse-linked cases. Helpers must enforce every predicate in SQL, not trust a previous Python check; events insert needs privileged encapsulation because API role currently has SELECT-only event access. No runtime broad event-table grants. Unknown deployed trigger/function graph blocks rollout.

### P8. POST `/admin/support-case-intakes`

**NOT IMPLEMENTED; BLOCKED, not an eligible candidate today.** Reserved design candidate, no request dispatch allowed. If later approved after an independent admission proof: body `{case_type:'other',priority:enum='normal',description:trimmed string4..2000,confirmed:true}`, Idempotency-Key; no pair/order/customer reference or initial note field. Support creates actor-opened/actor-assigned open case with encrypted format1 description, revision1 created event, audit and receipt; response201 `{case_id,status:'open',case_revision:1}`. No source of customer identity is invented.

Current support INSERT necessarily reaches retention trigger and its pair SQL; no independent implementation can be claimed under unchanged triggers. A future separately approved guard proving both refs null **before executing any pair SQL**, preserving the linked-case branch verbatim, could be evaluated, but changes protected admission and is outside this task/initial implementation recommendation. If that change is unacceptable, P8 stays blocked. Do not use a duplicate case table, skip triggers, session flags, direct DB relay or insert a closed case then reopen. Tests would require trigger-level relation-access proof, linked-dispute retention-race preservation, rollback/idempotency and FK/security checks under explicit later authorization.

### P9. PATCH `/admin/support-case-metadata/{case_id}/status`

**NOT IMPLEMENTED; BLOCKED pending independent admission/closure proof.** Candidate DTO `{expected_revision,confirmed:true,status}`; no automatic reason field because original support contract provides no reason-code taxonomy. Original transitions only open→investigating→resolved→closed, assigned-only. Protected payment/privacy/ownership/abuse/held closure restrictions remain. Future receipt200 `{case_id,status,priority,case_revision}` would require existing event/audit/closed_at semantics and revision/idempotency rules.

Do not enable even open→investigating now: UPDATE OF status with NEW investigating invokes retention pair query. Resolved/closed does not satisfy that trigger WHEN, but proving absence of relevant holds/links without racing protected provisioning is not currently established. No automatic has_active_hold=false, no closure based only on case_type=other. Errors preserve ESCALATION_REQUIRED/INVALID_TRANSITION without leaking protected context; tests would cover admission/hold/provisioning races, never deleting evidence or weakening old locks.

## 6. Independent financial observation — P10

### GET `/admin/financial-case-metadata/{case_id}`

**NOT IMPLEMENTED; feasible reduced read subject to contract/security approval and database proof.** No alternate mutation route. Query limit1–100 default20, opaque cursor<=2000. Finance role/session/email/MFA plus existing enabled financial review prerequisite and a current unrevoked **can_review** grant. Preserve recipient/provisioner `sr_account_epoch_allows(..., grant.created_at)` behavior and fail closed if helpers/tables missing. No authority writer or provisioning automation. Finance need not be Support assignee, matching existing separate grant semantics; Support cannot use it through support.manage.

Require c.case_type=payment, **c.pair_id IS NULL**, immutable financial_case_bindings with c.order_id=b.order_id, and bound attempt.order_id=b.order_id. Pair-bound cases return404 without attempting membership validation; this is a narrower population, not removal of original ownership checks. No deriving grant or subject from opener/order. Even a null-pair payment case may refer to an order containing pairs: the view observes core metadata only and makes no statement about them.

Closed200:

```
{
  as_of, case_id, case_status, case_revision,
  order_id, order_revision, attempt_id,
  amount, currency, settlement_state, order_payment_status,
  dispute_fence: "active" | "none",
  prior_decisions: [{decision_id, revision, decision, effective_decision, reason_code, created_at}],
  next_cursor,
  financial_decisions_available: false,
  refund_execution_enabled: false
}
```

Types/enums and decimal-string regex match existing ReviewProjection/HistoryEntry for these retained fields; timestamps UTC, IDs UUID, revisions positive, no float money. `as_of` marks observation; no new review-state enum or bank verification result. Settlement_state is stored payment_attempts.state, not a fresh independent settlement verdict. Do not infer missing evidence, hold absence, package readiness or authority to decide from this response. Omit exceptions/shipments/active-hold/evidence/review-reference fields entirely, rather than false/empty placeholders implying checked prerequisites.

New SECURITY DEFINER observation/history helper(s) with fixed search_path and bounded fields read only financial_case_bindings, financial_case_authorities, support_cases, orders, payment_attempts, order_financial_fences, financial_case_decisions plus existing auth/role/account-state helpers; write only safe audit `finance.case.metadata.read`. No `SELECT *` expansion, `sr_financial_case_context`, `sr_financial_case_history`, `load_context`, `sr_financial_case_apply`, `sr_fulfillment_eligible`, shipment/evidence/helper enrichment or workers. Read fence table directly inside narrow privileged helper, not a generic context wrapper. It has no trigger side effect merely by SELECT.

Observation must preserve grant/revocation serialization: preliminary actor/grant identity reads, shared account-epoch admissions for actor/provisioner in deterministic order, then order FOR SHARE (the existing provisioning/revocation guard takes order FOR UPDATE), case FOR SHARE and grant FOR SHARE with final relationship/role/epoch recheck. Recheck immutable binding after obtaining the order lock. These are core/case/grant locks, never units/pairs; no core changes. Use the documented global lock order; abort rather than upgrade/reorder after an obsolete preliminary selection. A consistent SQL snapshot for projected values/history plus cursor revision binding is required; do not assemble independently timed autocommit reads. The exact MVCC isolation/lock schedule must be rehearsed against concurrent old financial commands before approval; source review is not that proof. Audit and read complete in one API transaction. Avoid excessive page-limit lock duration; lock timeout becomes503.

This is a **read-only business operation with audit writes**, not a PostgreSQL READ ONLY transaction. Cursor binds actor, case, revision and projection/filter version, and grant must be revalidated on every page. Changed case revision409; no frozen multi-page snapshot promise. Error set follows shared contract; no can_decide boolean or evidence-fetch URL is returned. Required tests: grant revocation/account epoch race, missing/rebound context, null-versus-nonnull pair exclusion, no forbidden relation/function access, decimal precision, revision pagination, exact projection, audit rollback and old workflow unchanged.

### Why financial mutations remain blocked

Investigate and resolve_no_change do not themselves activate a new fence; this is useful side-effect classification, not permission for an alternate writer. They still use shared financial authority, settlement evidence where required, case/core revisions and decision history. Confirm_dispute/escalate activate a fence consumed by pair allocation/printing/fulfillment; dispatch affects effective outcome. Pair locks and binding verification are essential to the original financial consistency protocol. This review supplies no safe independent financial mutation. No copied weaker approval, manual bank_verified checkbox, refund, fence clearing or settlement endpoint is proposed. An ordinary internal note is never recorded as a financial decision.

## 7. Database implications and independence obligations

Reuse authoritative support cases/events, existing ciphertext purposes, immutable financial bindings/grants/decisions/fences and scoped encrypted receipts. No new case table, replicated payment state, timestamp column, category, migration application, FK weakening or privileged browser token. Existing schema can represent reduced reads and candidate narrow edits; it cannot make current creation/status paths pair-free by itself.

Future additive SQL helper/grant installation is still a database change and needs a reviewed migration/deployment plan. Do not edit historical migrations or replace/revoke existing functions/policies/triggers. Runtime finance table reads are revoked; do not solve this by broad SELECT grants. New definer functions must enforce explicit role, live actor, scope, fixed projection, policy and bounded input independently of the HTTP handler. New event writers must enforce revision/event uniqueness and full transaction rollback. No broad new table write grant or bypass of RLS through unchecked definer functions.

For P5–P7, prove eligibility checks and protected link insertion cannot race, including FK locking behavior and privileged provisioning. If proof requires changing the protected workflow, defer those commands to separate approval. Existing FK references alone do not prove the correct lock protocol. Reads may observe current metadata of protected cases without claiming they can mutate them. For P10, preserve current epoch invalidation semantics for both recipient and grant provisioner, even on cursor continuation; do not grant authority because a previous response succeeded.

## 8. Frontend mapping — no integration in this task

| Existing route/component | Later approved contract | Enabled behavior / unavailable behavior |
|---|---|---|
| `/admin/support`, `components/admin-support-cases.tsx` | P1 | Existing design, real queue metadata/filters/keyset pages, explicit loading/empty/error; remove demo fallback for live integration; no invented summary/customer/staff columns. |
| `/admin/support/[caseId]` | P2/P3; conditional P4 | Direct safe UUID metadata/history; assigned approved content only if policy passes. Invalid/inaccessible IDs honest unavailable. No context-prefetch or pair reference link. |
| Existing internal-note, claim and priority controls | Conditional P5–P7 | Enable only after server-proven O and concurrency approval; explicit confirmation/revision, duplicate protection and conflict drafts. Metadata visibility alone never enables a command. |
| `/admin/support/new` | P8 blocked | Create Case unavailable with architectural blocker until independently authorized intake exists. Never mount legacy SupportAdmin intake as substitute. |
| Existing status dialog | P9 blocked | No status mutation or fake demo success in live mode. |
| Compact Financial Review panel | P10 | Finance + server case grant, reduced observed metadata/history; no full review checklist, bank evidence, order/fulfillment lookup or decision form. |

Existing support page `?view=live`, UUID detail and new-case routes mount `components/support-admin.tsx`; `/admin/support/api/route.ts` forwards quarantined support calls. A future approved integration must contain those paths and replace entry-point dispatch deliberately; hiding one button is insufficient. No legacy console mounting, effects/prefetch, generic relays or finance-storage console reuse. Current `AdminSupportCases` mock notes/state and synthetic audit remain strictly separate. Preserve AdminPage verifiedSession/staffState, backend role enforcement, current components/dialogs, no-store/Origin and bounded response parsing; role preview never grants authority. Unrelated modules unchanged. Responsive/accessibility acceptance later at 1366×768,1440×900,768×1024,375×667.

## 9. Required tests and acceptance plan — NOT EXECUTED

1. Static closed dependency graph for each new method/path through imports/helpers, SQL functions, policies, triggers, FKs/defaults/generated expressions, audit and receipt writes. Allow auth/security and exact case/finance relations only. Deny `tag_pairs`, `order_pair_units`, `qr_codes`, shipment_pairs/other QR identity/inventory/ownership tables, and all pair/context/fulfillment/allocation functions. Extend denylist against actual schema; string matching alone is insufficient for dynamic SQL/definers/triggers.
2. Isolated dependency tests mount only new routers with synthetic principal/session doubles. Reject every unexpected SQL/helper/provider call and every nonallowlisted HTTP dispatch; deny all five old endpoints, generic Orders, payment verification, QR inventory/generation/QA/allocation and legacy relays in fixtures/setup/teardown. Test exact DTO/error/projection/limits, no plaintext logs, no redirects and unavailable dependencies. No original excluded endpoint is called even for regression coverage.
3. Provisioned isolated PostgreSQL role/function harness, not production/migrations-as-setup: inspect installation/owners/ACL/RLS first. Use approved synthetic null-pair case records and explicit dummy grant/decision history only; never create pairs or run full legacy seed chains. Instrument SQL relation/function access including nested definer and trigger execution (plan/function audit hooks or equivalent reviewed tracing); mere absence of returned pair data is not proof. Test explicit forbidden table/function permissions with care: definer owner privileges mean revoking API SELECT alone cannot prove independence. Missing adequate tracing is an acceptance blocker.
4. Verify support role/MFA/live session, cross-agent denial, restrictive abuse policy, assigned-only events/content, crypto-purpose binding, field minimization, SQL injection/query-key rejection, size/time limits, audit failure rollback and stale cursor/revision. Test foreign role combinations, revoked role and malicious frontend preview. Use isolated direct repository calls/approved fixture setup, never quarantined APIs.
5. For conditional writes: exact-key replay once, changed key409, expired/unauthorized replay, lost response, ciphertext/receipt rollback, competing claim/note/priority, unique event/revision, protected provisioning arriving before/during/after case lock. Confirm UPDATE column list does not invoke retention admission, not merely that a null parameter returns no rows. Existing abuse guard still active. Any unresolved interleaving keeps writes disabled.
6. Financial read: can_review versus Finance alone, revoked grant/provisioner/recipient, account invalidation, nonnull pair404 without lookup, bound order/attempt mismatch, history/page limit, case revision gap/conflict, exact decimal strings and excluded evidence/PII. Race observation with controlled order/case/grant updates in an approved isolated repository harness; no execution of original pair-dependent financial decision/helper. If full old/new lock interoperability cannot be tested without prohibited execution, record that gap and leave release blocked pending separately authorized acceptance.
7. Original protected endpoints/helpers unchanged: compare application/SQL source hashes/diffs against captured baseline, verify no changed registrations/guards/lock statements/policies/triggers. This is a preservation check, not a claim of runtime regression acceptance. No broad legacy test suite; original payment/fulfillment/retention concurrency rehearsal is separate authorization if it would invoke prohibited operations.
8. Future frontend isolated HTTP fixtures: no demo fallback, filter-reset/preserved pagination, direct details,403/404/409/412/503 and malformed responses, preserved drafts/confirmation/idempotency, forbidden-route denylist, mobile containment and keyboard access. Mutation fixtures simulate HTTP only; no remote side effects.

Current work performed **static source/document review only; zero tests, API calls, DB connections, browser renders, workers or migrations executed**. No live acceptance claim. Previously recorded DB/provider/grants/auth/migration/runtime blockers persist.

## 10. Risks and unresolved approval questions

- Approve reduced metadata disclosure versus content; no updated_at/customer/summary/staff identity is invented. Review lawful staff access to free-text notes; modern encryption is not content sanitization.
- Approve narrower O scope and explicitly decide whether any writes can be accepted with existing provisioning races. Missing proof means read-only delivery.
- Decide whether a future minimal null-reference admission branch is acceptable under separate protected-trigger approval; otherwise creation/status stay blocked. No such change is authorized by this proposal.
- Approve P10's narrower pair-unbound population and omitted readiness/holds/packages; ordinary observers must understand it is not API-324 parity. Pair-bound financial cases remain unavailable.
- Rehearse exact lock/MVCC/revocation behavior, default/trigger graph, installed migration state, helper ownership/ACL/RLS, bounded query plans and audit failure semantics. Static source references are not evidence of deployed installation.
- No grant/provisioner enrollment UI or evidence mechanism is added. Existing genuine authority must be supplied through its approved controlled workflow; if unavailable, financial view stays unavailable.
- New operation IDs, approved API/security contract addenda and corrected allowlist entries must be reviewed before implementation. Existing five quarantines remain untouched.
- DB-01/02/AUTH-01/RET-01 and prior Phase 3 physical/authority/non-production prerequisites persist. No auto-advance to another module.

## 11. Recommended implementation order

1. Review/approve this proposal's P1–P3 read-only metadata contracts, exact SQL dependency budget, operation IDs and additive helper deployment design; preserve all old quarantines. Include explicit legacy support entry-point containment in that separately authorized implementation.
2. Implement **only P1–P3** in an isolated backend/contract harness, then bind existing frontend list/detail/history without mounting old support consoles; no content/create/status/financial mutation. This is the recommended next implementation task, **not authorized or performed here**.
3. Approve/implement P10 reduced financial observation with its own helpers/grant/lock/MVCC proof. No decisions or private evidence retrieval.
4. Resolve content policy and scope/provisioning concurrency proof before P4–P7. Keep unsupported actions unavailable; do not stretch metadata contracts into authority.
5. Address P8/P9 admission/closure design only in a separately approved protected-workflow review. All financial decisions remain on the original protected path and excluded from this integration unless a later explicit safety/authorization review changes the boundary.
6. Provision independently identified non-production environment and genuine authorized records, inspect deployed SQL/auth/grants and perform approved acceptance without pair setup. No production/live approval follows from this document.

Stop after this proposal. Phase 9 remains **NOT IMPLEMENTED / BLOCKED pending contract approval and safety proofs**.
