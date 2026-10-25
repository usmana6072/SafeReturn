# Phase 9 — restricted Support test-account provisioning proposal

**Current policy update, 2026-10-24:** [v1.1 owner-approved development exception](BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md) explicitly permits this sole development owner-controlled subject/executor and removes Ahmad's approval requirement. The prior self-grant findings and v1.0 proposal below are preserved historical decisions, not current blockers for this amended workflow. Restricted local tooling now exists; see [operational runbook](../ops/SUPPORT_DEVELOPMENT_EXCEPTION.md). Live migration/account/grant operations and genuine acceptance remain pending exact authorization/evidence. No production or general staff-policy exception.

Assessment date: 2026-10-24 (Asia/Karachi). **DRAFT: NOT EXECUTABLE; no live writer implemented or authorized.** This is part of the existing Phase 9 plan, not a new phase. The private, unsigned preparation packet is `tmp/phase9-step2/support-test-account-request.json` (outside version control). Its request ID identifies preparation only, never approval or a grant receipt.

## Governance decision

The owner has confirmed that **the owner will personally control the intended test account**. The proposed owner-as-executor arrangement therefore constitutes a self-grant and is **not permitted** under BTR-01. Ahmad's independent review does not waive this rule; a second Auth UUID for the same human does not create independence. No grant may proceed under this arrangement.

BTR-01 does not expressly prohibit a requester from executing a grant for a different human merely because requester and executor coincide. However, product ownership does not confer privileged execution authority. A named operator, verified authority, trusted channel and an approved writer contract remain necessary. This distinction does not authorize the present owner-controlled subject/executor combination.

Ahmad may be considered for **off-app review without an application account**: BTR-01 does not universally require that reviewer to hold an application role. His designation is not completed identity verification, signed approval or authority to execute grants. Do not grant him security_admin/superadmin or reuse the separate account-lifecycle custody workflow. The current proposed reviewer and executor are different humans; no universal additional third-person requirement is invented here.

The release gate also says the owner account is not a test subject. The existing owner account remains excluded. Whether a distinct, dedicated but owner-controlled development identity is permissible needs an explicit bounded security decision; this document does not silently reinterpret that exclusion. Even such a decision must preserve no-self-grant and independent review.

## Sources and missing implementation contract

- `docs/SafeReturn_13_Blocked_Task_Contract_Review_2026-10-19.md`, authority/common rules and BTR-01: explicit authority, separate human review, no self-grants, recent signed authentication, serialization/history, minimal audit and signed offline evidence.
- `docs/SafeReturn_07_Security_and_Privacy_Specification_v1.2.md`, Task2.3B controlled provisioning boundary: **authority/expected-state/idempotency/receipt/audit-reference and regrant/job fencing contracts require approval before affected implementation**.
- `ops/STAFF_PROVISIONING.md`, sections 1, 3, 4 and 8: offline rehearsal only; no live role writer, authoritative role revision, command receipt or approved packet-to-audit mapping. Historical installed0021/pending0030 statements are historical, not current environment evidence. Verified migration head0043 is unchanged; installed helpers do not supply missing authority.
- `backend/alembic/versions/0001_identity_profiles.py`: staff-role history, partial unique active role index, Auth foreign keys, RLS and restricted grants. An index alone is not a reviewed concurrent command protocol.
- `backend/app/api/auth.py`: genuine verified email, signed/provider MFA, exact current role checks. `backend/app/db/provision_runtime.py` provisions database runtime infrastructure, not staff identities or application roles. Staff directory readers are not writers.
- `frontend/lib/auth/mfa-flow.ts`: supported provider TOTP enrollment/challenge/verification; existing staff MFA entry requires staff security authorization. A new no-role subject needs an explicitly approved pre-grant official Auth interaction; no temporary staff grant.

**Implementation stop:** the user expressly requires stopping a writer if its existing approved contract does not authorize it. That condition applies. No SQL writer, migration, new grants, role-management API, pretend authority verifier or unsigned-packet execution switch is supplied. The existing synthetic rehearsal is not a one-account provisioner.

## Controlled external change packet

Keep the completed packet in an access-controlled, non-public evidence archive, not application case notes, source control or chat. The local preparation JSON is an unsigned checklist only. Move a completed packet to the approved archive before relying on it. Limit archive access to the named subject, owner, reviewer and separately authorized executor as needed. Archive retention and destruction rules require explicit approval; no arbitrary retention duration is invented.

Required content:

| Field | Required evidence / present state |
|---|---|
| Unique request ID and revision | Generated local preparation ID; approval must bind exact packet bytes and revision. |
| Environment | Only development project fhux…kzvq; pin the complete expected project identity in the private operational packet before execution. |
| Target | Approved email in the private packet; exactly one independently verified provider UUID, currently absent. Email alone never assigns a role. |
| Role and scope | support only; own assigned cases and redacted unassigned intake. History current-assignee-only; no extra queue membership or automatic assignments. No finance, operations, credential, case mutation or QR authority. |
| People | Owner/requester; owner-controlled subject; proposed owner executor **REJECTED for self-grant**; Ahmad proposed independent reviewer. Actual verified executor remains unresolved. |
| Creation/review times | Timezone-aware timestamps from the controlled process; a typed timestamp is not recent-auth evidence. |
| Email evidence | Official Auth confirmation verified against the exact provider subject by the approved evidence verifier. Currently missing. No mailbox credentials or confirmation links in packet. |
| MFA evidence | Real successful provider factor challenge plus validated signed AAL2/live-session assurance, tied to subject and time. Currently missing. Store only non-secret verification references/results; not JWTs, OTPs, seeds or recovery codes. Screenshots/checkboxes alone are insufficient. |
| Executor authority | Signed appointment to the precise one-account operation, independently verified human/account binding, current eligible session/email/AAL2 and signed recognized AMR no older than300 seconds at execution. Currently absent. |
| Ahmad's decision | Explicit APPROVE or REJECT over exact project, subject UUID/email, role/scope, executor, packet hash/revision and expiration. His actual signature, identity verification and trusted verification key/channel are absent. |
| Expiration/revocation | Proposed one execution within24 hours of signing, subject to approval of that window; live authentication must still be current. Any identity, executor, scope, evidence, packet or authority change invalidates approval. Ahmad/owner can withdraw through the authenticated archive/channel; missing revocation availability fails closed. |
| Outcome/cleanup | Pre-commit rollback; post-commit revocation is a separate authorized historical change, never deleting role/audit history or automatically deleting Auth identity/factors. Unknown commit outcome requires same-key reconciliation, never blind new-key retry. |

**Proposed verifiable channel:** a controlled PDF/document with a detached digital signature, held in a restricted revisioned archive. Independently establish Ahmad's signing-key fingerprint through a separate live identity-confirmation channel before accepting a signature. Bind the executor's appointment and packet digest to that same controlled process. Keep private signing keys with their real holders. Select the actual archive, signature verifier, authority holder and revocation registry before implementation; none is assumed to exist. An authenticated team channel is an alternative only if its real identities, immutable approval/version export and verification controls are explicitly approved. A name typed into JSON is never a signature. Ahmad must verify genuine evidence without receiving passwords or MFA secrets.

## Exact contract decision required before writer coding

Approve a bounded addendum to BTR-01 / the controlled runbook, resolving **all** of the following; this proposal itself does not amend them:

1. Resolve the subject/executor conflict: nominate a different human as executor with explicit authority (not automatically Ahmad), and decide whether the separate owner-controlled test subject is allowed; alternatively choose a different-human test subject and approve its email. Never authorize an owner self-grant under the current rule.
2. Define one CLI/runbook operation, no public endpoint or generic role editor, pinned to the exact development project, approved email plus genuine immutable Auth UUID, support only and one expected absent active Support grant. Define collision handling without changing an existing account or adopting existing privileges.
3. Name the privileged writer principal, approved existing credential retrieval mechanism and exact narrowly scoped permissions. Do not use runtime credentials, a broad key or project ownership as proof of human authority. If schema/grant changes are necessary, review them separately; no RLS or broad-grant exception.
4. Approve the external archive, signature format/verifier, registered human/key bindings, executor appointment, approval TTL, evidence verification and revocation checks. Human identity must prevent aliases/second accounts defeating self-grant or independent review. Require genuine provider evidence; never authorize using caller-supplied assurance booleans.
5. Define authoritative expected-state and transaction protocol against installed0043: existing custody/lifecycle global and ordered principal locks, coordination with other privileged writers, fresh under-lock authority/state checks, active grant uniqueness and custody continuity. No invented role revision column, synthetic counter or count-as-version. Specify contention/stale/replay/revocation behavior and least-privilege metadata/provider reads.
6. Define exact actor/operation/subject idempotency scope and canonical command, encrypted receipt format/key custody/retention, unknown-outcome reconciliation, and atomic grant/audit/receipt commit. Existing generic idempotency storage is not automatic authorization for a new operation. Review its exact storage mapping before coding.
7. Define approved audit action/target/actor and external packet reference mapping using allowed fields only; server-derived actor/state/outcome, no client-forged audit fields. Existing JSON allowlist is from_status,to_status,reason_code,version,event_id,outcome. Do not invent a role version or add JSON fields. If current fields cannot satisfy linkage, approve a separately reviewed migration rather than improvising.
8. Define role-revocation/regrant/session/job fencing and retained-history cleanup; no automatic factor/user deletion or role restoration. Require disposable PostgreSQL concurrency, atomic rollback, RLS/ACL and human recovery rehearsal before any cloud grant.

The shortest compliant next action is the **governance/addendum decision**, not a Dashboard INSERT or another TLS investigation. Live execution remains a separate later authorization.

## Safe rehearsal and required future tests

Inspected the entire existing `backend/tests/test_staff_provisioning_policy.py` and pytest configuration: standard-library/pytest-only in-memory fixture, no conftest files found, no application/provider/database imports, no remote setup/teardown. Ran `backend/.venv/Scripts/python.exe -B -m pytest backend/tests/test_staff_provisioning_policy.py -q -p no:cacheprovider`: **34 passed**. No cloud writes or reads occurred.

| Requested check | Actual evidence |
|---|---|
| Missing approval, missing signed/provider MFA, unverified email, missing current authority | Existing synthetic rejection tests passed; not genuine evidence verification. |
| Self-grant, reviewer independence, invalid role, stale state | Existing synthetic rejection tests passed. Current real proposed arrangement is blocked by human identity, not executed. |
| Replay/conflicting command, simulated failed state/audit/receipt/commit rollback | Existing in-memory tests passed; no duplicate synthetic grant on replay. |
| Concurrency | Existing concurrent last-custodian-removal model passed; Python lock only, not PostgreSQL proof. |
| Exact intended email/UUID and wrong named executor | **NOT EXECUTED:** no approved writer/authority binding; generic synthetic labels are not an exact-account verifier. |
| Unforgeable audit provenance and independent cryptographic approval | **NOT EXECUTED:** model audit is internally generated, but not a production audit or signature verifier. |
| Real idempotency/encryption/transaction rollback/RLS concurrency | **BLOCKED:** requires approved contract, implementation and separately authorized disposable database rehearsal. |

Do not inflate these34 tests into live onboarding/MFA or a successfully implemented restricted grant mechanism.

## Later narrowly scoped cloud authorization (not requested for execution now)

After the addendum, compliant identities and offline implementation/rehearsal are approved, request separate authorization to: (1) create only the exact dedicated subject through official Supabase signup, send its verification email and complete genuine subject-held email/MFA flows, after reviewing hooks/email side effects and existing-account collision handling; (2) inspect only that subject's approved identity/session/security evidence without collecting secrets; (3) execute exactly one approved Support grant with minimal atomic audit/encrypted receipt through the reviewed restricted writer; (4) verify only that grant and approved authentication/permission results. Do not manually insert into auth.users or enroll/remove factors as administrator shortcuts.

Separate fixture and acceptance authorization is still necessary. No safe case fixture is presently verified; retention-trigger QR dependency blocks improvised case creation. Actual metadata GETs create minimal access audit events, so genuine API acceptance requires that write scope too. Upstream transport/SSL-enforcement evidence remains an infrastructure acceptance blocker where required, without further investigation here. Genuine Auth/MFA, queue/assignment, abuse fail-closed, PostgreSQL/RLS and real UI tests remain outstanding. All three metadata endpoints **NOT ADMITTED**; frontend live gate **DISABLED**. No Phase10.


## Pending development exception amendment — 2026-10-24

The owner has explicitly requested a development-only self-grant exception. The separate [BTR-01 development Support exception v1.0 DRAFT](BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.0_DRAFT.md) proposes the narrow change to the self-grant and owner-test-subject exclusions. It preserves the original BTR-01 and this procedure as history. **Preparation authority is not ratification or live execution authority.** The original prohibition continues to govern until the bounded amendment is ratified and all implementation/execution gates are met; owner control is now an explicit proposed exception, rather than a requirement to nominate a different executor if that amendment is approved.

The draft pins the exact project and email, proposes Ahmad's actual independently verified signed approval, a24-hour maximum grant and hard sunset2026-11-07 23:59:59 Asia/Karachi, and identifies enforced expiry, one-use consumption, atomic audit/encrypted receipt, exact authority/locking and metadata-only access prerequisites. A normal support row has no expiry or metadata-only route boundary. These are required reviewed implementation changes, not capabilities supplied by an unsigned packet. No writer or migration is implemented and no cloud action is authorized. All earlier test results remain synthetic/historical. The next action is review and explicit ratification of the separately versioned draft, followed by exact implementation-design approval and later distinct account/grant execution authorization.
