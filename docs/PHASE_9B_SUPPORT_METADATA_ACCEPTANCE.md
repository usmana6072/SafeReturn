# Phase 9B — Support metadata acceptance and frontend integration gate

Assessment date: 2026-10-24 (Asia/Karachi).

**CURRENT GATE: owner-confirmed Supabase Cloud development/test project selected as candidate; remote access and live acceptance NOT AUTHORIZED/NOT EXECUTED. Phase9B acceptance is not complete.** Follow `PHASE_9D_CLOUD_ACCEPTANCE_PLAN.md` for updated identity/evidence, scoped remote-audit proposal, preservation and separate identity/fixture/acceptance approvals. All three endpoints remain **IMPLEMENTED — PENDING ACCEPTANCE / NOT ADMITTED**. Earlier sections below retain historical environment-discovery findings; the owner's new designation does not retroactively establish live acceptance or authorize a remote connection. Docker/local Supabase workflow is cancelled; existing PostgreSQL17.11 cluster unchanged.

## Environment discovery and limits

Configuration values, hostnames, credentials and tokens were not printed. Files were parsed for key presence and target classification only; values were not loaded into application settings or used for connections.

| Evidence inspected | Finding | Acceptance implication |
|---|---|---|
| `backend/.env` | Runtime, migration and test database keys and auth URL are present, but all URL targets classify as non-loopback and unverified. Auth publishable-key and profile crypto settings are present; validity/provenance not tested. | A TEST_DATABASE_URL name is not evidence of non-production identity, isolation, approved data or permission. No remote target contacted. |
| Process environment | Relevant runtime/migration/test database, Supabase, admin origin and profile crypto keys absent in this shell. | No explicitly selected acceptance configuration. |
| `frontend/.env.local` | Required server API/admin-web origin and reviewed Supabase URL/publishable-key settings absent. | Later SSR/frontend acceptance configuration is incomplete. No values/settings changed. |
| `.env.example` | Example-only configuration, not an enrolled environment. | Not acceptance evidence or authorization. |
| Local infrastructure | No repository Compose configuration or Supabase `config.toml` found in inspected workspace paths. docker/supabase/postgres/pg_ctl/psql are not discoverable on PATH. | No reusable local stack established; does not prove no software is installed elsewhere. |
| TCP listeners | OS listener inspection was unavailable. | No claim that ports/services are absent, running or healthy. No TCP connection probe was substituted. |
| `backend/tests/integration/pg_rehearsal.py` | Requires explicit test DB URL, inspects installed catalog/domain counts, creates temporary schemas/roles and runs Alembic rehearsal. Current-head assumptions include old table-count baselines. | Not run: neither an approved target nor a restricted metadata-only setup; generic catalog/count/setup can touch excluded domain relations. Do not run broad migration chain as acceptance setup. |
| `backend/tests/integration/test_support_cases.py` | Uses legacy `/admin/support-cases`, workflow_sample, old revision rehearsal and SQL-created session/AAL2 fixtures. | Not run. It invokes quarantined workflows and its synthetic session rows do not establish genuine disposable provider/MFA identities. |
| `backend/tests/test_support_metadata.py` | Own isolated FastAPI app, only new metadata router, `_env_file=None`, synthetic EC JWT signing, mocked JWKS transport and in-memory scripted transaction/SQL double; no external DB/client lifecycle. | Safe isolated verification, not PostgreSQL/RLS/provider acceptance. Teardown closes the mock verifier only. |

Prior DB-01/DB-02/AUTH-01/QA-02 and environment/physical QA blockers remain. No approval or genuine Support/MFA/policy fixture record was identified in the reviewed configuration/tests/progress. Deployment recipes and historical source implementation do not establish provisioned resources. No database or auth provider was contacted to discover records on unverified targets.

## Contract and source security verification

Read the current integration progress, corrected inventory/plan/exclusions, complete decoupling proposal, API-contract Phase9A record, relevant Security/Privacy requirements, new router/service/tests, authentication code, support/events RLS, retained abuse-policy helper chain and legacy frontend entry points. No application code changed during this assessment.

All paths below start `/api/v1/admin/support-case-metadata` and accept GET only:

- Collection: exact optional case_id UUID; case_type activation|lost_tag|payment|privacy|ownership_dispute|other; status open|investigating|resolved|closed; priority low|normal|high|urgent; queue all(default)|mine|unassigned; limit1–100(default20); cursor<=2000. Unknown/duplicate query keys rejected; no date/customer/text/employee search.
- `/{case_id}`: no query; metadata only, `content_available:false`.
- `/{case_id}/history`: limit/cursor only; assigned-actor events, descending revision. No actor IDs or plaintext notes.

`CaseMetadata` is exactly case_id,case_type,status,priority,case_revision,created_at,assignment,assigned_to_me. List adds as_of/items/next_cursor; detail adds content_available=false; history is case_id/case_revision/items/next_cursor, event items exactly event_id/case_revision/event_type/from_status/to_status/priority/created_at. All DTOs closed. UTC timestamps; no authoritative updated_at exists in this projection. List as_of is observation start, not a database/cross-page snapshot. Assignment is mine/unassigned, never an employee UUID. No customer/subject reference or safe summary is invented.

Authentication chain: signed JWT → live session admission → verified email + signed/current provider MFA → explicit non-revoked Support role; final session/role recheck before return. Other roles do not inherit Support. Case visibility is explicitly narrowed to unassigned/current-actor cases in list/detail, and current assignee only for history, independently of broader base case RLS. Policy-readable case scope is mandatory in all SELECTs; a missing `sr_abuse_case_readable` helper is503, never legacy fallback. Abuse-linked cases additionally require current policy/triage and unexpired report/case retention; no abuse row is not the same as a missing policy for a retained abuse case.

Cursor AEAD binds actor, purpose/version and normalized filters or history case/revision. Changed history revision409. Current visibility is reevaluated each request; no immutable snapshot or cursor-expiry promise is added. Errors are redacted, headers private/no-store/nosniff/no-referrer, missing/inaccessible detail/history404, empty lists200, invalid query400/422, unavailable dependencies503. Read audit INSERTs remain transactional; only approved scalar audit fields are written. No case mutation or retention-admission trigger is reached.

### Source independence trace and limits

New service's direct business reads are support_cases/support_case_events only; safe audit INSERT is the only write. No original support/finance/order service is imported. Existing policy path is `sr_abuse_case_readable` → abuse_reports / marker → support_cases/Support-role check; policy → abuse_intake_policies/shared abuse-policy admission. Existing auth/session/account admission reads auth/session/roles/account-state; audit RLS uses staff-role helpers and sr_safe_json inspects JSON through pg_catalog. No pair/QR/ownership/allocation/QA/credential/fulfillment context is reachable in this reviewed source path. Existing shared security advisory admission remains; it is not a pair row lock.

This is **source evidence plus application-boundary SQL denial in a double**, not proof of installed SECURITY DEFINER internals, owners, ACL/RLS, hidden deployed policies/triggers, execution plans or live lock behavior. Nested SQL and deployed auth must still be independently verified before admission. No restricted API was called to verify preservation.

## Tests actually executed in Phase 9B

After fixture/setup/teardown inspection, from backend:

```
.venv/Scripts/python.exe -B -m pytest tests/test_support_metadata.py -q -p no:cacheprovider
```

**44 passed in 2.80 seconds.** This is a fresh Phase9B rerun, not a historical count. Real synthetic JWT signature validation/AEAD, mock JWKS and scripted SQL only. Coverage includes authorized list/detail/history; missing/invalid/expired JWT; verified email, live session and signed/provider MFA rejection; explicit-role rejection; unassigned/mine/other queue scope; assigned-only history; policy-helper unavailability and policy filtering on continuation; revision conflict; field minimization/no notes/actor IDs; content_available=false; malformed UUID/query/response handling; filter/keyset pagination and actor/filter/purpose/tamper cursor rejection; empty history/revision gaps/maximum revision; crypto/dependency failure; auth-recheck rollback; headers/absent content/methods; SQL/service/route denylist and registration isolation.

From repository root:

```
backend/.venv/Scripts/ruff.exe check backend/app/api/v1/support_metadata.py backend/app/services/support_metadata.py backend/tests/test_support_metadata.py
```

**Passed.** No formatting or application edits requested by this run. Whitespace validation of assessment documentation also performed before delivery.

**Not executed:** PostgreSQL, actual RLS/role/ACL/helper/policy behavior, nested SQL tracing, provider email/MFA enrollment/session revocation, database concurrency/query-plan/lock tests, broad legacy suites, excluded routes, frontend rendering/browser/responsive acceptance. Missing-policy tests model unavailable/filtered results; they do not execute expiry/triage SQL. Synthetic AAL2 claims and session doubles do not count as enrolled live MFA acceptance.

## Per-endpoint admission decision

| Endpoint | Implementation/contract | Authentication | RLS/case/policy acceptance | Data minimization | Pair independence | Final admission |
|---|---|---|---|---|---|---|
| GET collection | Implemented; schema/filters/cursors verified in source and isolated tests | Isolated pass; provider/live session BLOCKED | Source checks + scripted scope pass; PostgreSQL BLOCKED | Closed projection isolated pass; deployed response pending | Source + SQL-double denylist; nested installed chain pending | **NOT ADMITTED** |
| GET `/{case_id}` | Implemented; metadata/content=false verified | Isolated pass; provider/live session BLOCKED | Scoped404/source+double pass; PostgreSQL BLOCKED | No content/identity/reference fields; deployed response pending | Same restricted source path; installed chain pending | **NOT ADMITTED** |
| GET `/{case_id}/history` | Implemented; revision paging/gaps verified | Isolated pass; provider/live session BLOCKED | Assigned-only source+double pass; PostgreSQL BLOCKED | No actor IDs/note text/raw audit; deployed response pending | Event/case SELECT only in source; installed chain pending | **NOT ADMITTED** |

No admission approval has been recorded for these endpoints. This acceptance-assessment request is not permission to waive missing checks. Corrected allowlist unchanged. Original API-097/098/099/323/324 remain quarantined; Phase4 Orders source unchanged. Phase9B is not marked complete.

## Exact prerequisites to unblock acceptance

1. Owner identifies and authorizes an existing isolated non-production environment, approved configuration paths and resource owner. Independently verify target identity, data isolation, runtime role restrictions and permitted acceptance actions **before** any connection. Otherwise request explicit separate provisioning authorization; do not create a DB, local stack, namespace or configuration in this task.
2. Authorized operator establishes source-matching installed support_cases/support_case_events, staff/session/account admission and retained abuse-policy dependencies. Relevant repository sources include 0003 case RLS/audit, 0005 staff/session security, 0021 history, 0030 account admission and 0035 restrictive abuse helpers. Inspect actual installed versions/definitions/owners/EXECUTE/SELECT/audit grants/RLS and policies; do not assume a migration number alone proves the graph. No new Phase9A migration is needed or authorized; no broad chain/legacy seeds as setup.
3. Supply approved disposable test identities with genuine provider email verification, Support role and enrolled MFA/live signed+provider AAL2, plus authorized negative-role/session cases. Do not fabricate provider MFA by inserting auth.sessions rows or trust role preview. Explicitly approve any fixture manipulation in isolated data; no production credentials or unrelated staff-role changes.
4. Supply already provisioned, authorized metadata/history fixtures: current-assignee, unassigned and other-assignee cases, inaccessible/missing references, actual retained-abuse policy cases with approved policy/version/retention/triage scenarios, and existing event rows with note/identity fields to prove they are excluded. Do not seed through old support APIs, execute support creation or use generic direct INSERTs as a shortcut: existing retention-admission triggers can reach pair linkage even for null pair input. Fixture preparation needs its own safe reviewed path/authorization if appropriate records are absent.
5. Verify server profile AEAD key/version availability for cursor tests, actual issuer/audience/JWKS/session configuration and bounded audit permissions/rollback. Values stay in protected configuration; presence checks here do not validate them. No new policy/retention duration, grant or approval record may be invented.
6. Use a new metadata-only focused acceptance harness. Inspect and approve its setup/teardown; deny all legacy/quarantined endpoints and pair/QR SQL/functions. Demonstrate nested function/policy/trigger relation-access tracing under the actual runtime/definer owners and lock observation without reading pair records. Revoking API table permission alone is insufficient for definer paths. If proof would require prohibited setup/execution, keep acceptance blocked and obtain a separately safe plan.
7. Run and record the endpoint matrix for real role/session/MFA, case assignment, retained-policy fail-closed/RLS, filters/cursors/revisions, minimized responses and audit/rollback, using only authorized disposable records. Require actual results, environment identity and unresolved risks. No production/shared-data tests.
8. Record the project/owner governance admission decision (reviewer, date, exact three GET shapes/query/response limits, evidence and remaining restrictions) after required acceptance succeeds. This assessment does not appoint an approver or self-approve omitted controls. Only then amend the corrected allowlist and separately authorize frontend integration. Provide API/admin origin and SSR auth configuration through the controlled deployment process at that stage.

## Prepared frontend mapping — NOT CONNECTED

| Current surface | Reuse after admission | Required later work / limits |
|---|---|---|
| `frontend/app/admin/support/page.tsx` and `components/admin-support-cases.tsx` | AdminPage Support guard; AdminPageContainer/Header/Card/EmptyState/StatusBadge, current table and scoped CSS | Map new Page/CaseMetadata. Columns case ID/type/status/priority/assignment/created_at/revision only. Remove synthetic customer/subject/updated time from live projection. Do not import mock hooks into a live component. |
| List filters | Existing status/priority/category presentation | Category maps exact backend case_type values, not demo labels. Replace demo free-text search with exact Case ID; add queue selector. No date/global search or one-page filtering presented as global. Apply/Clear and limit/cursor with Previous/Next history; filter changes reset cursor and pending history, preserve applied filters across pages. |
| `/admin/support/[caseId]` | Detail layout/cards and metadata badges | Direct valid UUID fetch through new metadata detail, no legacy SupportAdmin UUID dispatch. Show content unavailable; no customer/reference/description section or invented updated_at. Invalid ID rejected locally;404 honest inaccessible/not found. |
| Existing history panel | Event presentation layout only | Fetch new History only for actor-assigned detail; unassigned history not available, backend remains authoritative. Render event type/from/to/priority/revision/time only; no actor column or notes/raw audit. Preserve server ordering/gaps, page cursors;409 explicitly reloads detail and resets history. |
| `frontend/app/admin/support/api/route.ts` | Reuse verifiedSession and trusted server-only transport patterns | Existing relay targets quarantined `/admin/support-cases` and exposes POST/PATCH. It cannot be reused unchanged. Future implementation needs a separately scoped read-only relay with exactly three admitted GET shapes, validated UUID/query keys, bounded closed request/response/error parsing, redirect rejection/timeouts and private/no-store. No arbitrary backend path or mutation forwarding. No relay created here. |
| `?view=live`, UUID detail and `/admin/support/new`; legacy `components/support-admin.tsx` | No legacy console mounting | Current entry points can invoke old support APIs. Separately authorized integration must contain these dispatch paths and prevent mount/prefetch/effects/relays reaching the five quarantined operations. Merely hiding buttons is insufficient. No such containment change made during this assessment. |

Future response types must match backend closed DTOs exactly; use actual explicit authenticated Support role and server/backend permission checks, not frontend preview. Clear live data on401/403;404 displays unavailable,503/service/network/malformed response displays unavailable with explicit retry. Loading and empty states distinct; no demo fallback on any error. Abort/generation-check stale requests on subject/filter/auth/unmount changes. Do not persist records/cursors/privileged tokens in localStorage or synthetic audit storage; demo mock state stays separate and labelled. View Details links must not prefetch excluded paths. No browser/dependency/UI build was run here.

No Create/Claim/Edit Priority/Add Note/Change Status/financial action controls, content requests or actor identity links in the proposed live metadata screen. Safe read controls only after admission: Apply/Clear filters, Previous/Next, View Metadata/History and Refresh. Responsive/keyboard validation is a later UI acceptance requirement, not a result of this document.

## Outcome and recommended next task

Only this assessment document and the Phase9B tracker entry were written. No frontend, protected Support/Finance, metadata backend, Phase4 Orders, deployment or environment code changed. No excluded API/pair operation, migration, worker, database connection or real provider call was executed. Isolated ASGI/JWKS calls stayed in mocked transports.

**Next task: owner identifies/authorizes the existing isolated acceptance environment and approved identities/policy/case fixtures, or separately authorizes a safe provisioning design.** Then review a metadata-only PostgreSQL/auth/nested-dependency acceptance harness. Frontend implementation waits for acceptance evidence and recorded allowlist admission. Stop at this assessment and prepared mapping.
