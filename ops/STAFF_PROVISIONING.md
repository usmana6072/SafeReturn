# Controlled staff onboarding and revocation — Task 2.3B

**Scoped development amendment, 2026-10-24:** the owner approved [BTR-01 development exception v1.1](../docs/BTR_01_DEVELOPMENT_SUPPORT_EXCEPTION_v1.1.md) for one fixed development project/email, permitting owner-controlled provisioning without Ahmad/another independent reviewer. Its [restricted command runbook](SUPPORT_DEVELOPMENT_EXCEPTION.md) governs only that exception. General BTR-01, production prohibitions, custody/recovery rules and the historical rehearsal below remain unchanged. Restricted source implementation is not a live grant authorization; no migration or command credential has been applied/provisioned.

Status: implemented offline runbook/rehearsal; **not a live execution authorization**.
Normative authority: [BTR-01](../docs/SafeReturn_13_Blocked_Task_Contract_Review_2026-10-19.md#btr-01), its common security rules, Doc04 endpoint role lists and Doc03 database contracts. Named people, independent custody and actual PostgreSQL/provider/manual execution remain gates. The owner's existing operations AND finance grants are not test subjects.

## 1. What exists and what does not

- `staff_roles` records grant identifiers/user/role/grantor/time, nullable `revoked_at`, reason and a partial unique active `(user_id,role)` index. Revocation sets `revoked_at`; retain the original row. A later separately authorized grant requires a new row, never clearing old revocation history. Preserving grant fields/history is a runbook requirement; this does not assert a database immutability trigger. No role revision column or role-change command/receipt exists.
- `require_staff` checks verified email, current signed/provider MFA and exact active roles on every protected call. Bootstrap capabilities and hidden buttons confer no authority. A valid customer session does not become a staff session through signup/email matching.
- Runtime `safereturn_api` has narrow SELECT on its own role rows, not a role-provisioning writer. A technical DB login/service key, `superadmin` label, or an operations/finance grant is not human change approval.
- Pending0030 defines account-state epochs, `security_custodians`, the `account-lifecycle-custody` transaction advisory lock and principal lock keys. It is **unapplied**. Its custody helper additionally checks independently verified, unexpired/unrevoked evidence, active security_admin and current account eligibility. Row counts alone are not independent recoverability. Pending0031 is a read helper, not a role writer.
- Existing audit JSON allows only scalar `from_status`, `to_status`, `reason_code`, `version`, `event_id`, `outcome`. No requester/approver/executor/evidence document or new JSON field may be inserted without a separately reviewed migration. Identity evidence/secrets stay outside application cases/logs/chat.

## 2. Explicit role matrix

| Role | Approved scope summary | Additional limits |
| --- | --- | --- |
| support | Own assigned cases and redacted unassigned intake | No general customer directory, finance or credential recovery authority |
| finance | Explicit financial review and reporting endpoints | MFA, independent trusted settlement/decision authority where required; no stock/fulfillment authority |
| operations | Explicit inventory, printing, packing and dispatch endpoints | No implicit finance/security/hold/role authority; physical/custody gates still apply |
| security_admin | Explicit security, hold, privacy and directory endpoints | Case/action/independent-custody/recent-AMR requirements remain; no automatic role-management power |
| superadmin | Only endpoints that explicitly name superadmin | No inherited operations, finance, directory, printing or lifecycle authority |

Multiple grants form only the explicitly permitted endpoint union. One person with multiple roles never supplies two independent people. This summary is not a new permission policy: exact Doc04 lists and live guards remain authoritative; broader archived security-matrix shorthand does not create exceptions.

## 3. Prepare a change packet outside the application

1. Record a change reference, requested named subject, exact role/action, business purpose and bounded scope. The owner explicitly approves the person and purpose. Customer signup and email/domain membership cannot provision staff.
2. A separately identified security custodian validates identity, account eligibility and genuine MFA through a controlled privileged channel. Never copy TOTP seeds, OTPs, passwords, bearer tokens, recovery keys or private identity evidence into the packet's application-facing metadata.
3. Record requester, owner approver, independent custodian/reviewer and executor separately. Resolve each named person's authority outside the app; do not fill names from owner account metadata or grant a placeholder identity. No self-grant/shared identity. Changes involving authority principals, self-revocation, bootstrap or last-custodian recovery need separately reviewed handling; this runbook does not manufacture an exception.
4. Verify a distinct remaining active, non-suspended, independently recoverable authorized security custodian where a change can affect security continuity. Check provider bans/deletion, verified/nonanonymous identity, current grant and unexpired custody evidence. A second nominal role or expired/suspended custodian is insufficient.
5. Obtain verified live identity/session/email/current AAL2 and signed recognized AMR within300 seconds for high-risk execution. Refreshing `iat`, ticking a box, a screenshot or a typed timestamp is not recent authentication evidence. Independent review and current authority must be rechecked immediately before execution/replay.

**Current gate:** no actual named owner delegate, independent custodian, executor/channel, signed recovery drill or new role-change writer is identified/authorized here. The packet remains a proposal. No live execution command is supplied.

## 4. Controlled transaction review sequence — not executable SQL

Only after a separately authorized implementation and disposable PostgreSQL rehearsal:

1. Inspect installed revision and current role/account/custody/session state through separately authorized least-privilege mechanisms. Do not apply pending0022–0031 or query general Auth tables from runtime to satisfy this runbook.
2. Review the exact privileged executor, grants, operation/resource-scoped idempotency record, encrypted receipt and authoritative concurrency token contract. `staff_roles` has no version column; a UI value, count, current timestamp or the synthetic rehearsal counter cannot substitute.
3. Serialize the approved staff change and last-custodian check in a single transaction. When0030 is actually installed, use its same global custody/lifecycle lock and principal locking protocol; review actor/approver/subject lock order, try-lock contention and concurrent readers with that implementation. The present installed0021 environment cannot be claimed to supply pending helpers. Do not use session GUCs to forge real identity/MFA.
4. Under those locks, revalidate the entire packet, current roles/account/MFA/recent AMR, independent people/evidence, expected state and remaining recoverable custodian. Staleness or contention means refresh and independent review, not auto-adjusted expected versions or new keys.
5. Apply one exact approved role change. Grant inserts a new historical row; revoke stamps only the chosen active grant's revocation. Preserve all other roles, especially the owner's operations AND finance. Never delete original grants, clear revocation, silently assign replacement roles or edit customer/ownership/financial records.
6. Atomically record the approved metadata-only audit and encrypted command receipt with the role change. Request/approver/executor and previous/new state need an approved reference mapping to the controlled packet. Existing audit fields alone do not define that missing storage/authority contract. Any state/audit/receipt/commit failure rolls back together.
7. Same key/same canonical command returns the original authorized receipt only under current authority; changed same-key input conflicts. Do not blindly retry an unknown outcome with a new key. Reconcile through the controlled channel if the original key/outcome is lost. Exact live role-command error/version/receipt behavior still requires its own approved contract; BTR common rules do not implement it.

## 5. Revocation, sessions, grants and jobs

After an authorized removal, test the next protected API request with the revoked role: it must deny even if a browser still displays old navigation. Clear privileged browser data and pending commands on denial using existing console behavior. Test both roles separately on mixed-role identities; revoking one must not remove the other or confer independent-actor approval.

Role revocation is **not** provider logout, account suspension, factor removal, credential rotation or customer-account deletion. It does not inherently revoke the underlying identity token. Regrant may let an old still-valid session regain access unless separately approved session/epoch fencing prevents it. Do not piggyback API320 suspension, alter Auth sessions, or change account epochs as an invented role-revocation mechanism.

Review each actor-bound grant/job against its current canonical authority checks. Print grant redemption rechecks operations/MFA; case-scoped and manufacturing authority have their own live/independence/epoch rules. A business print/fulfillment/outbox job is not automatically an enqueueing employee's personal grant. Do not cancel business history, settled orders, ownership or physical work because a staff role changed. Exact role-revocation/regrant fencing and in-flight effect mapping remain execution gates; existing account-suspension fences do not prove every role-change race is covered. External effects already in flight cannot be recalled by a database flag.

## 6. Break-glass and rollback

Maintain independently held, signed offline identity/custody/recovery evidence through the separately approved channel. No secret values or identity attachments in this repo. A named independent human must demonstrate recovery using disposable synthetic accounts before live last-custodian operations are considered. If no recoverable authorized custodian remains, stop and escalate under a separately approved recovery plan; do not self-grant or nominate a custodian from a role count.

Before commit, any failed check rolls back all role/audit/receipt changes. After commit, correction requires a new explicitly reviewed change with new historical evidence. Never erase revocation/audit/receipts, restore old sessions, or downgrade installed0030 epochs to undo a change. Do not attempt automatic compensation for an uncertain provider/commit outcome.

## 7. Reproducible offline evidence

From repository root, PowerShell:

```powershell
New-Item -ItemType Directory -Force output/task23b,tmp/task23b-web | Out-Null
$env:PYTHONUTF8='1'
$env:PYTHONPYCACHEPREFIX='E:\Projects\SafeReturn\tmp\task23b-web\pycache'
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_staff_provisioning_policy.py -q -p no:cacheprovider --junitxml=output/task23b/policy.xml
```

The fixture-only reference model lives inside that test file. It has synthetic labels, in-memory grants/receipts/audit and a Python lock only; no DB/Auth/storage/network/CLI executor, no import into the app and no real evidence validation. Its counters, tuple records, error labels, memory receipts and authority booleans are deliberately **not** a proposed production schema/transport/encryption/signature/authority contract. They illustrate BTR-01 invariants: independent evidence, no self-grant/inheritance, preserved grant history, last-custodian checks, simultaneous removals, next-command denial, stale review, replay/conflicting-key and atomic rollback. Passing it grants no authority to anyone. Actual cryptographic/session/role guards are tested separately with synthetic mocked provider transport.

## 8. Remaining approval and acceptance gates

- Named owner authority/delegate, independent custodian/approver/executor, trusted channel and genuine identity/MFA/signed recovery evidence. No invented identities or acceptance attestations.
- Exact privileged role-change executor/permissions, authoritative version/expected-state semantics, controlled packet mapping, receipt retention/encryption/idempotency and audit linkage; separately approved design before affected coding. No runtime endpoint, SQL function, migration or general Auth grant was introduced here.
- Installed-revision-aware global/principal/role/custody lock protocol; real concurrent last-admin removal, direct privileged writer coordination, RLS/ACL, query plans/timeouts, MVCC, atomic audit/receipt/commit rollback and replay-versus-revocation/regrant races on disposable PostgreSQL.
- Current-role grant/job and provider session invalidation/regrant behavior, provider new-session/recovery handling and integrated browser/API denial. No claim that pending0030 is applied or provider logout occurred.
- Human synthetic onboarding/revocation/rollback/break-glass drill, security-owner sign-off and reviewed minimal evidence retention. Genuine execution remains separately authorized.

No frontend change: no new staff-management page, role editor, build or browser acceptance claim. Existing2.3A MFA and2.3D lifecycle implementations/gates remain unchanged. Installed0021, pending0022–0031, disabled flags, services3031/API8030, configured Auth/ignored environments and protected mobile tooling are preserved.
