# SafeReturn — blocked-task contract review and decision record

Date: 2026-10-19 (Asia/Karachi). Decision record: **BTR-20261019**, revision 1.

## Authority, scope and approval meaning

The project owner explicitly asked the agent to review every blocked task, correct contracts and approve the corrected decisions after review. This record exercises that delegated **product/engineering design approval** for the thirteen task cards listed below. It is not a claim that an independent security/legal reviewer signed, a provider accepted a configuration, a physical test passed, or any implementation exists.

The approved decisions may guide subsequent, individually scoped implementation tasks with synthetic identities/providers. No real role/credential/MFA change, suspension, export, erasure, payment/refund, dispatch, email, Sheets/storage write, stored-object deletion, restore, migration application, deployment, commit or push is authorized by this review. Existing owner operations AND finance roles remain unchanged. Installed migration 0021 and the running authentication/3031 runtime remain untouched. Tasks 5.7G/H/I remain IMPLEMENTED with their existing gates.

The requesting project owner is the product decision authority. Execution authority is a separately identified, authorized operator with the explicit role stated below; this record does not grant that role. Independent approval means a different human/actor, not two roles on one account. Missing personnel or provider evidence is a release/execution gate, not something an agent may simulate as accepted.

## Sources and concrete findings

Reviewed current task cards and Docs 01–12 sections on staff permissions, public challenge/notifications, cancellation/settlement, replacement and manufacturing custody, Sheets/retention, privacy and recovery. Cross-checked actual guards and AMR parsing in `backend/app/api/auth.py` and `core/auth.py`; migration 0005 account/session projection; inventory sealed-insert generation; payment locking/settlement guards; notification template/provider/idempotency; finance Sheet columns/projection; 0019 retention admission/recovery; and 0021 case scope/history.

| Finding | Correction approved in this record |
| --- | --- |
| Doc 12 proposed API-245–255 collides with implemented API-245 cleanup retry and API-246/247 shipment reads | Keep all implemented IDs/routes unchanged. Reassign only unimplemented template proposals to API-300–310; reserve additional future contracts below |
| Cancel/refund descriptions risk equating a request with financial settlement or stock release | Cancellation request is review-only; separate independently reconciled decision/release; refund execution disabled |
| Account restoration could accidentally revive old sessions or revoked staff powers | App-level suspension plus session invalidation epoch; fresh authentication required after restoration; no staff-role restoration |
| Replacement can copy ciphertext bound to the retired QR, or leave stale printable tokens usable | Re-encrypt approved copied fields under the new resource context, or start private/unpublished; fence all old artifacts and preserve old-recipient history |
| Later batch exports could imply recovery of hashed activation secrets | Export only the original printer-encrypted sealed manifest; no reconstruction, plaintext browser delivery or silent credential regeneration |
| A worksheet tab can be mistaken for an access-control boundary | Dedicated workbook/service account; retain the actual eleven-column safe mirror; no assertion of per-tab OAuth isolation |
| Privacy export/erasure approval could broaden support access or erase accounting/QR history | Separate request authority/projection; preserve assigned-agent notes and legacy reasons; explicit allowlists, held/partial outcomes and retained-history dispositions |
| DB backup can be mistaken for private-object/key recovery evidence | Separate DB, Storage, key and configuration custody; no restore/send/replay until reconciliation gates pass |

## Common contract rules

All paths below are relative to `/api/v1`. New IDs reserve future contracts only; they are **not registered runtime routes**. Existing API-023/065/089/093 keep their IDs. Unknown JSON fields are rejected. UUIDs, aware UTC timestamps, positive integer `expected_revision`, fixed reason codes plus encrypted optional explanations, and explicit `confirmed=true` apply to sensitive decisions. Reason text is not copied into audit metadata.

Use existing signed JWT/provider identity, live session, verified email, explicit role and verified AAL2 guards. High-risk execution additionally requires signed AMR authentication within 300 seconds; a refreshed token's `iat` alone is insufficient. Customer request creation may use the existing customer guard where specifically stated; granting/retrieving an export requires recent authentication. No implicit superadmin inheritance.

Mutations use actor/operation/resource-scoped idempotency keys and encrypted receipts, with transactionally committed minimal audit and append-only decisions. Same key/body returns the original receipt; changed body returns 409. Versions fence stale actions (412). Foreign/missing scoped objects both return 404; missing auth 401; wrong role/AAL/reauth 403; invalid input 422; missing key 400; domain conflicts 409; expired/used grants 410; rate limit 429; unavailable crypto/provider/database 503. Failures must not echo submitted private fields. Reads are private/no-store, bounded to 1–100 rows (20 default), with stable cursor ties; provider/storage locators are never list fields.

No common rule silently changes existing endpoint responses. Compatibility changes must be documented in the implementing task. One-use download consumption is the explicit exception to receipt replay: duplicate consumption returns 410 and requires a new authorized grant; no plaintext archive in a receipt.

<a id="btr-01"></a>

## BTR-01 — 2.3B staff authority and controlled provisioning

**APPROVED for development; task becomes TODO.** Use a controlled provisioning runbook, not a web role editor or new role-management endpoint.

1. Owner approves the named person's role, business purpose, case/change reference and scope. A separately identified security custodian validates identity and MFA evidence using a privileged operations channel outside the app. No shared identities, self-grants or email-derived roles.
2. Explicit role matrix remains: support = own assigned cases/redacted unassigned intake; finance = financial review/reporting; operations = inventory/printing/packing/dispatch; security_admin = explicitly authorized security/hold/privacy decisions; superadmin = only endpoints that explicitly name it. Multiple roles do not bypass independent-actor approval.
3. Serialize staff changes and last-authorized-security-custodian checks in one transaction. Preserve at least one active, non-suspended, independently recoverable authorized custodian; separately test concurrent removals. Revocation appends history/sets revoked_at, never deletes original grants or silently grants a replacement role.
4. Recheck current role on the next protected command; fence jobs/grants whose authorization was revoked. Record request/approver/executor, previous/new role state and outcome without private identity evidence. No new audit JSON keys until the existing audit allowlist is reviewed in a separate migration.
5. Document independent break-glass custody and signed offline recovery evidence. A real last-custodian action requires a separately approved recovery plan; routine customer signup never provisions staff.

Release gate: actual named custodian/independent approver, controlled channel and a human synthetic onboarding/revocation/recovery drill. The owner account is not a test subject.

<a id="btr-02"></a>

## BTR-02 — 2.3D suspension, restoration and recovery

**APPROVED for development; task becomes TODO.** Choose an application account-security state, not direct managed `auth.users` edits or a broad runtime Auth administration key.

- Additive model, if implemented: `account_security_state` with user FK, active/suspended, revision, invalidate-before epoch and case reference; append-only security events. Existing external Auth bans/deletion remain independently authoritative.
- API-320 suspend and API-321 restore accept `{case_id, expected_revision, reason_code, confirmed}`. Explicit security_admin only, AAL2 and recent AMR. Target must have case-scoped action authority. Block self-action, last-custodian lockout and stale/duplicate changes; never mutate ownership, payment or staff roles.
- Suspension rejects protected API requests and revokes application grants/jobs that require the subject's active authorization. It does not by itself revoke printed public QR availability: that uses existing separately authorized API-088 after emergency-access impact review. In-flight mutation must serialize/recheck account state before commit.
- Advance invalidation on suspension AND restoration. A pre-restoration session cannot become valid again through token refresh or stale AMR. Inspect actual Auth session metadata before the future migration; extend only the narrow session-state projection or use an explicit application session registration mechanism. No direct runtime SELECT grant on Auth tables. Do not substitute `authentication_time` alone if an old session can acquire fresh MFA without a new authenticated session.
- API-322 opens a case-linked recovery escalation with no credential/factor/email change. AAL2 security role can record the referral; actual lost-factor recovery is an authorized provider procedure with separate identity evidence and independent approval. Never transmit passwords, OTPs or recovery secrets in cases.

Release gate: synthetic session-invalidation/concurrent-action drill and approved custody playbook; real account actions remain separately authorized.

<a id="btr-03"></a>

## BTR-03 — 3.5C controlled replacement

**APPROVED for development; task becomes TODO.** Existing API-089 is a case-approved replacement of exactly one current child on the same pair/type/owner.

Request: `{case_id, expected_revision, expected_current_qr_id, tag_type, replacement_batch_id, replacement_serial, qa_reference, reason_code, confirmed}`. New token is server-generated. Caller is explicit operations + AAL2/recent AMR; an unexpired, unused approval by a different security_admin is bound to case/pair/old child/type. Approval is a scoped authority record, not a client boolean or arbitrary QA string.

Use a documented common lock order for related orders, pair, old child, approval and affected jobs. Recheck entitlement, holds, physical QA evidence and current-child uniqueness under lock. Commit retiring/revoking old token, creating new current child, consuming approval, artifact/grant invalidation and append-only audit atomically. Existing deferred exactly-two-current-child constraints must still pass; exactly one concurrent replacement succeeds. Same idempotency receipt does not mint a second child.

Sibling identity and pair owner stay unchanged. No automatic paid-order occurrence rebinding, duplicate package, free stock release, dispatch or physical QA approval. New production uses an explicit new/replacement job with original order linkage and current QR-source validation; stale worker/artifact/download authorization must fail. Historical orders/old tokens/messages remain auditable, and finder messages keep their original recipient.

A new child starts private/unpublished unless the owner explicitly approves an allowlisted profile migration. Encrypted values bound to the old QR UUID cannot be byte-copied: decrypt/re-encrypt inside the trusted service under the new AAD, without staff/browser plaintext. Third-party contacts and consent cannot be invented.

No automatic fee, refund or balance adjustment. A separately case-approved complimentary replacement may proceed; chargeable replacements require an ordinary separately approved quote/order. Compromised pair activation credentials require a separate security response; replacing a printed public token is not proof that the concealed pair secret is safe. Missing approval/custody/entitlement returns 409 and stops release.

<a id="btr-04"></a>

## BTR-04 — 4.4A challenge and proxy policy

**Design APPROVED; task remains BLOCKED for live acceptance.** Keep challenge-protected private contact reveal and finder submission fail-closed during provider failure. Already approved public minimal scan/emergency content remains available; never expose additional private contact/medical data as an outage fallback. Accessible English/Urdu retry/help copy must distinguish challenge unavailable from saved-message success. Optional geolocation remains optional.

Validate provider success, exact configured hostname, action/resource binding, freshness and single use server-side. Reject forged forwarded headers. Default rate-limit peer is the direct ASGI peer; enable proxy headers only after the exact trusted proxy network/hop topology is documented and spoof-tested. Do not invent production CIDRs from a hosting product name or change the running launcher in this review. No raw token/IP/location in telemetry.

External gate: approved staging hostname, actual proxy topology and separately authorized real widget/mobile/timeout acceptance. Provider documentation confirms five-minute, single-use tokens; test keys do not establish production acceptance.

<a id="btr-05"></a>

## BTR-05 — 4.4C notification copy/version policy

**Current English copy and design APPROVED; task remains BLOCKED for deliverability/native-copy acceptance.** Review approves the current privacy-preserving subject/body in `workers/notifications.py` as the English generic finder-message notification: it announces a message and asks the user to sign in, without asserting return/delivery. No finder text, contacts, location, medical details, credentials, evidence/export links or activation tokens. No arbitrary HTML editor or bulk-send feature. Approved current English content SHA-256 (`SUBJECT + "\n" + HTML`, matching API-101 metadata): `1980434b84ea5cd7e5db1533ffe67d323a2bb157f3fa7d3eef9d2848da47b863`; a content change requires a new recorded review, not inherited approval.

Future template versioning must freeze identifier + content fingerprint at enqueue and freeze the exact provider request before its first send. Existing rows have historical version `not_recorded`, never fabricated approval timestamps. Once an attempt might have reached Resend, retries use identical recipient/body/original key even after template edits. A new template is for new events only. Retain current 23-hour ambiguous-send cutoff and fenced attempt history; provider acceptance is not inbox delivery.

External gate: actual approved sender domain and SPF/DKIM/DMARC review, independently reviewed Urdu copy where used, authorized disposable recipient and received-message evidence. No live send/replay or DNS edit is authorized here.

<a id="btr-06"></a>

## BTR-06 — 5.3A cancellation request and release policy

**APPROVED for development; task becomes TODO.** API-065 creates/returns an owner-scoped review request, not an instant refund, stock release or payment reversal.

Closed JSON `{expected_revision, reason_code, confirmed}`; verified owner, idempotency key. Here the revision fences the core order, not merely a new cancellation record: implementation must expose/maintain an authoritative order revision across all relevant writers in a rehearsed additive change if none exists; an old request revision cannot authorize changed order/payment state. Return 202 `{request_id, order_id, request_status, revision, next_action:'await_review'}`; repeat active request returns its stable receipt. Foreign order is 404. Request lifecycle: requested → investigating → approved/rejected/escalated → completed; versioned append-only decisions. The core order/payment/fulfillment states stay independent.

Every final release needs a finance reconciliation record proving no accepted/pending/ambiguous settlement and a distinct operations executor. No client clock, screenshot, elapsed reservation TTL or request alone authorizes release. Lock order → attempts in stable ID order → reservations/units, then decision/job rows; recheck concurrent settlement, allocation, activation, printing and shipment under lock. A verified/under-review/disputed/ambiguous transfer, paid allocation, active production or dispatched/activated unit requires escalation, not automatic release. Finance attestation has a bounded 300-second action validity and rechecks current revision; waiting reopens review.

Completed eligible cancellation changes only allowed order/reservation states through the existing verified writer or a rehearsed guarded extension. Retain purchase/address/QR-use/payment/audit history; do not free an activated pair or silently allocate another pair after late settlement. A late transfer after cancellation goes to reconciliation, never auto-fulfillment. Rejecting the request leaves the underlying order unchanged. No numerical refund SLA or money movement is promised.

<a id="btr-07"></a>

## BTR-07 — 5.3B financial disputes/refunds

**Explicit 2026-10-20 owner amendment:** The owner approved the four precise Task 5.3B additions in PHASE_IMPLEMENTATION.md. Doc 04 API-323/324 now supplies normative authority/DTO/version/reference/fence/package semantics; Doc 03 records additive 0025 after pending 0024. Refund execution/O-06 and fence removal/restoration remain disabled. This approval changes no installed migration, runtime origin/flag, real case authority, staff role or provider.

**Controlled authority provisioning runbook (future separately authorized operation):** First approve the exact environment, case/order/attempt binding, target finance identity, read/decision capabilities and independent security_admin provisioner in a trusted audit record. Verify current security role and identity/MFA through existing controls; original settlement reviewer and grant beneficiary cannot self-provision/decide. Under reviewed restricted administrative access, lock the order then its attempts/units/pairs/case; verify payment case linkage/optional pair and the attempt belongs to that order. Use bound SQL parameters and the provisioner's current actor context to insert the immutable binding and a distinct-person authority (can_decide implies can_review); generated minimal audit/authority events must commit with it. Do not grant runtime writes to these tables or change staff_roles. Verify positive/negative case boundaries and provenance readback; do not retry an ambiguous write without reconciliation. Revoke by one-way revoked_at update with version/audit under the same locks; do not delete history or clear revocation. Regrant needs separate recorded approval. No numerical expiry/retention invented. This runbook is **not** permission to provision any real case/user in the current synthetic-only task; no runtime grant API/editor or credential is added.

**APPROVED for development; task becomes TODO. Refund execution is explicitly DISABLED.** Optional O-06 remains unapproved. Customer case closure, request cancellation, a screenshot or a finance Sheet row never settles/refunds a payment.

API-324 supplies only a case-authorized finance review projection: case ID/type/status/revision, linked order/attempt IDs, exact Decimal amounts/currency, canonical settlement state, prior non-sensitive decisions and exception metadata. Exclude support notes/legacy reasons, address, medical/finder content and private URLs. Access requires explicit finance, AAL2 and a separately provisioned case-specific review authority; finance alone cannot list/read arbitrary support cases. API-323 records `{expected_revision, decision:'investigate'|'confirm_dispute'|'resolve_no_change'|'escalate', settlement_review_reference, reason_code, confirmed}` with recent AMR and independent decision authority.

Append decisions; never overwrite the original bank verification or manufacture a refund reference. Confirmed disputes must fence current allocation/print/reprint/download/packing/dispatch/delivery eligibility through the common eligibility service before any screen enables decisions. Preserve already-created packages in safe exception/returned paths. If the current model cannot represent that fence, implementation requires an additive migration first; a UI-only dispute marker is insufficient. Resolution does not re-verify payment or resume shipment automatically: reuse the verified finance reconciliation/eligibility writer with new independent evidence. Already-dispatched cases are escalated; no automatic carrier call, ownership revocation or refund.

<a id="btr-08"></a>

## BTR-08 — 5.4A manufacturing custody/export

**APPROVED for synthetic development; task becomes TODO.** Choose generation-time sealing to the authorized printer public key, consistent with existing API-090 `safereturn-sealed-insert-v1`. Ordinary metadata/list/detail/UI never contains plaintext credentials. Private-key custody is outside the application.

API-093 request: `{expected_revision, printer_key_fingerprint, production_approval_id, reason_code, confirmed}`; explicit operations + AAL2/recent AMR and independent case/batch-scoped security approval. Return 202 `{job_id, batch_id, revision, status, manifest_sha256}`. Read job metadata through API-336, issue a session-bound one-use grant through API-338 POST `{expected_revision,confirmed}` only for a ready job, and retrieve only encrypted bytes through API-337 with `X-Print-Grant` (same-origin authenticated consumption, max 300 seconds, 256-bit random verifier stored as digest); never a public signed URL or a plaintext browser manifest. Missing/used/expired grants fail closed; duplicate consumption is 410. Grant issuance rechecks production authority/recipient fingerprint and supersedes any active grant for that job/session.

Bind immutable batch/pair count, exactly two child identities per pair, encrypted manifest hash and recipient-key fingerprint to the durable job. Idempotent retries transport the SAME sealed bytes to the SAME approved recipient, not a new key/credential. A missing original sealed payload, unknown handoff acknowledgment, wrong/rotated fingerprint, already released batch or stale approval produces a reconciliation conflict; no hash reversal, raw-secret reconstruction, silent re-mint or new recipient. A successful HTTP response alone is not printer receipt or physical QA. Printer acceptance is a signed/checksummed handoff record under dual control.

No real printer connection, copy/native-font approval, physical packaging/scan pass or plaintext purge is certified here. Physical release remains 6.4. Encrypted transport retries and encrypted receipt replay do not authorize a second physical run. Document custodian destruction/receipt separately; no plaintext archive.

<a id="btr-09"></a>

## BTR-09 — 5.6A actual masked Sheets mirror

**Schema/sharing design APPROVED; task remains BLOCKED for actual configuration/write acceptance.** PostgreSQL is authoritative. Use a dedicated workbook shared only with the dedicated least-privilege service account and named finance reviewers; never public-link sharing, a mixed personal workbook, a bank import or bidirectional status sync. A tab/protected range is not a confidentiality boundary.

Approve the actual `SHEET_COLUMNS`, in this exact order:

`order_id, order_number, payment_status, fulfillment_status, currency, amount, payment_method, sender_account, evidence, export_version, reconciliation_time`.

`sender_account` remains literal `masked`; `evidence` remains literal `private`. No bank/name suffix is added merely because an older prose proposal allowed one. Decimal amounts serialized as decimal strings, stable order_id key, monotonic export version, RAW writes and UTC reconciliation time. Reject header drift, duplicate keys and stale worker completion rather than overwriting an unrelated row. A real mapping must name workbook ID, numeric sheet ID, exact tab/range, key column and exclusive writer; IDs/credentials stay out of public reports.

External gate: operator supplies/validates that concrete mapping, actual service-account sharing and separately authorizes a dedicated synthetic worksheet upsert/lost-ack/retry drill. Keep `SAFERETURN_GOOGLE_SHEETS_APPROVED=false` until that evidence is accepted; this review edits no environment or provider flag.

<a id="btr-10"></a>

## BTR-10 — 5.6B retention and orphan reconciliation

**PDF design and safety protocol APPROVED; task remains BLOCKED for evidence/legal/provider activation.** Approve the proposed PDF business grace as seven days after the later of confirmed delivery or the latest completed authorized reprint, subject to current verified settlement, completed work/reconciliation and no active grant/hold/dispute/reprint request. This is a future versioned policy, not a bulk deadline backfill or activation. Existing artifact deadlines are not rewritten by this review.

Payment-evidence retention remains unset pending actual finance/legal record-class requirements. Message/account/medical and backup periods are separate and also unset. No guessed legal duration, universal seven-day evidence purge or silent interpretation of a configured string as legal approval. Activation needs a record containing resource class, policy version, approving authority, effective date, duration/trigger, exception mapping and evidence reference. Missing policy fails closed.

Orphan discovery initially produces metadata-only inventory/quarantine. Never infer ownership from filename, age or absent DB row alone. Prove exact bucket/key, creator/issuance record, immutable checksum and upload attempt/fence, exclude in-flight or ambiguous completions, and require human reconciliation before cleanup eligibility. Unknown ownership is never deleted automatically. Quarantine is a logical state, not a provider move/delete. Reuse 0019 order-first admission, lease fencing, deletion-intent, fresh provider absence confirmation and durable tombstones. No retry can create a late legal hold over already authorized deletion or pretend the object was recovered.

External gate: evidence/legal schedule, separate policy references, provider/cache/backup handling and explicit disposable-object live-delete authorization. No real object is touched in this review.

<a id="btr-11"></a>

## BTR-11 — 5.7J access/export

**Narrow `basic_v1` contract APPROVED for development; task becomes TODO.** This is a documented scoped self-service export, not a claim that every statutory data-access request is legally complete. Broader requests are escalated with explicit omissions, never silently treated as satisfied.

- API-325 POST `/me/privacy/exports`: `{scope:'basic_v1', case_id?, confirmed:true}`; verified subject + recent authentication; case must be the actor's privacy request if supplied, otherwise create a scoped request/case atomically. Return 202 `{request_id,status:'requested',revision}`. Subject always derives from verified identity, never a supplied user ID/email/recipient.
- API-326 GET `/me/privacy/exports/{request_id}`: own status, revision, manifest/scope version, category counts and safe exclusion reasons, ready/expiry timestamps; no object key/URL, notes or third-party identifiers. Other subject 404.
- API-330 GET `/admin/privacy/exports`: explicit security_admin + AAL2, bounded metadata only for specifically authorized requests/cases. No blanket support-case private read.
- API-327 POST `/admin/privacy/exports/{request_id}/decisions`: `{case_id,expected_revision,decision:'approve'|'reject'|'escalate',scope_version,reason_code,confirmed}`; explicit security_admin + recent AMR, case-specific authority, independent approver, immutable manifest approval bound to subject/scope/policy. Support may triage its assigned case but gets no export bytes, new high-risk resolution power or access to other agents' notes.
- API-328 POST `/me/privacy/exports/{request_id}/download-grants`: `{expected_revision,confirmed}`; subject + recent authentication, ready/nonexpired artifact, active session and current approval. Return a memory-only opaque one-use grant (256-bit random verifier, stored only as digest), max 300-second TTL; one active grant per request/session; never email or URL query parameter.
- API-329 POST `/me/privacy/exports/{request_id}/download`: grant in `X-Privacy-Grant`, same session/subject/Origin and current authorization, atomic consumption. Stream attachment through authenticated app transport with no-store and nosniff; no redirect to storage. Duplicate/expired grant 410; a failed/partial stream requires a new authorized grant, not a receipt containing private bytes.

Request lifecycle: requested → reviewing → approved → building → ready → expired; rejected/escalated/held/retry are explicit alternatives. At most one active request per subject/scope; bounded automatic worker retries use fenced leases and stable request/manifest identity, without notifications. The approval record expires after 24 hours if generation has not begun; completed artifact retrieval also expires after 24 hours. These are technical access TTLs, not legal retention/SLA claims; expired ciphertext cleanup remains a separately approved policy operation.

`basic_v1` allowlist: own supplied display name/locale; currently and historically owned pair metadata without tokens/activation secrets; own Lost item text where it does not disclose another subject; own order/item/QR occurrence metadata and Decimal totals; normalized own payment outcomes without sender/evidence/bank fields; own submitted privacy request status. Incoming finder messages export only own-recipient receipt counts/status/time; omit message/contact/location bodies and finder identifiers. Omit ICE medical/contact fields and guardian/third-party data until individually authorized. Omit shipping names/phones/addresses, Auth tables/tokens/factors/sessions, private notes/legacy deletion reasons, staff audit internals, storage locators and provider credentials. Do not call this a full account dump.

Every category has included/omitted/held/not-supported disposition, reason code, schema version and source watermark/count. Build bounded UTF-8 JSON plus manifest, encrypted at rest under the existing keyring with resource-bound AAD and checksum; deterministic snapshot scope with reauthorization at approval, generation and grant. Default cap 10,000 records / 10 MiB plaintext; exceeding a cap escalates instead of silently truncating a successful export. Use bounded streaming/paging; no arbitrary SQL, user-selected columns, cross-owner joins or formula-bearing spreadsheet output. Changes after the watermark are disclosed, not falsely snapshot-complete. Holds preserve records; any disclosure restriction requires explicit classification/review rather than interpreting every retention hold as permission to deny all access.

Release gate: human security/privacy review of the actual allowlist/manifest and identity evidence, independent operator/custody and synthetic grant/expiry/provider-failure drill. Real customer export and real storage writes remain separately authorized.

<a id="btr-12"></a>

## BTR-12 — 5.7K erasure and backup-aware execution

**Plan/status contract APPROVED; destructive execution remains BLOCKED.** Reuse API-023 request/case and API-053 message-hide semantics; no duplicate instant-delete endpoint. Existing API-023 returns its case UUID as request_id, which API-334 uses; no managed Auth deletion or incompatible API-023 response change. A request or case closure is never proof of erasure.

Reserve API-331 GET `/admin/privacy/erasures` for authorized case-scoped security metadata; API-332 POST `/admin/privacy/erasures/{case_id}/plans`; API-333 POST `/admin/privacy/erasures/{case_id}/decisions`; API-334 GET `/me/privacy/erasures/{case_id}` for verified requester-safe status; API-335 POST `/admin/privacy/erasures/{case_id}/execute` only after the blocked execution gates are resolved. Plan/decision/execute use common revision/idempotency/recent-AMR rules, explicit security_admin and independent case authority. A plan binds subject, source revisions/watermark, per-class policy versions, holds, scope hash and approvers. Changing any bound fact invalidates approval.

Plan dispositions: unpublish/hide, erase under approved class policy, retain with reason/deadline, blocked by hold, provider pending and backup pending. No `auth.users` cascade-delete, automatic pair ownership transfer, payment reset, destruction of essential order/QR/audit history or unsupported key-wide crypto-erasure. Shared key rotation does not prove one subject's data was erased. Active export/print/delivery work, immutable original-recipient data and financial disputes must be reconciled under common order/pair/object locks before any execution admission. Cancellation of pending notifications is a fenced state transition, not a real replay/send.

Execution states: requested → planning → awaiting_approval → approved → executing → completed_with_retentions; held, partial_retry, rejected and backup_pending are explicit. Checkpoints record per-class outcome without plaintext, survive worker crashes and require fresh absence confirmation for provider objects. `completed` cannot be returned while a required provider/key/backup disposition is unknown. Unpublication may take effect through separately approved existing owner controls; it is not physical erasure.

Remaining critical inputs: actual jurisdiction/record-class obligations and response timelines, approver identity/evidence rules for guardians or compromised accounts, financial/message/medical retention mapping, provider/cache/backup expiry and legal exceptions. The project owner's delegated technical review cannot certify those facts. No physical purge writer or live erasure is activated until those inputs and separately scoped migration/application approvals exist.

<a id="btr-13"></a>

## BTR-13 — 6.3B disaster recovery

**Recovery design and engineering rehearsal targets APPROVED; task remains BLOCKED for actual custody/restore evidence.** Use provisional engineering acceptance targets RPO ≤1 hour and RTO ≤4 hours for the pilot drill. They are future test targets, not measured guarantees or assertions about the configured plan. If actual provider/cost capability cannot meet them, return an explicit target/capability decision before release, never silently lower the target.

Maintain separate versioned inventories for PostgreSQL/Auth linkage, private Storage objects, all required encryption key versions, deployment/configuration and DNS custody. Database backups include object metadata, not the Storage bytes; missing bytes cannot be reported recovered by restoring metadata. Preserve erasure tombstones/hold policy in a separately protected recovery journal so an older DB restore cannot republish erased/revoked data.

Restore only a separately authorized isolated target with no public DNS, real outbound workers, provider credentials or ordinary-user access. Fence/invalidate pre-restore leases and download grants, reconcile payment/order/ownership/current-child uniqueness and every tombstone/hold/object checksum, then reconcile ambiguous provider sends using original keys; never replay notifications or payments automatically. Escrow retrieval is independently controlled and audited; keys never enter source, ordinary backup reports or this document. Reprint requires current settlement/QR/physical rules and is not an automatic replacement for missing artifacts.

Measure recovery point age, full elapsed recovery time, missing object/key counts and unresolved provider outcomes. No cutover until independent security/database approval of reconciliation. Synthetic in-memory object/key fixtures prove protocol only, not actual hosted backup restoration or key custody. No real backup download, restore, credential rotation or cutover is authorized here.

## Canonical future API reservation ledger

| ID | Method | Path | Task / status |
| --- | --- | --- | --- |
| API-300–310 | As Doc 12 corrected table | Existing proposed print-template paths | O-05 / future; P1 disabled; role names still require an explicit existing-role mapping, not new granted roles |
| API-320 | POST | `/admin/users/{user_id}/suspensions` | 2.3D design approved |
| API-321 | POST | `/admin/users/{user_id}/restorations` | 2.3D design approved |
| API-322 | POST | `/admin/users/{user_id}/recovery-escalations` | 2.3D design approved |
| API-323 | POST | `/admin/support-cases/{case_id}/financial-decisions` | 5.3B design approved |
| API-324 | GET | `/admin/support-cases/{case_id}/financial-review` | 5.3B design approved |
| API-325 | POST | `/me/privacy/exports` | 5.7J design approved |
| API-326 | GET | `/me/privacy/exports/{request_id}` | 5.7J design approved |
| API-327 | POST | `/admin/privacy/exports/{request_id}/decisions` | 5.7J design approved |
| API-328 | POST | `/me/privacy/exports/{request_id}/download-grants` | 5.7J design approved |
| API-329 | POST | `/me/privacy/exports/{request_id}/download` | 5.7J design approved |
| API-330 | GET | `/admin/privacy/exports` | 5.7J design approved |
| API-331 | GET | `/admin/privacy/erasures` | 5.7K plan/status design approved |
| API-332 | POST | `/admin/privacy/erasures/{case_id}/plans` | 5.7K plan/status design approved |
| API-333 | POST | `/admin/privacy/erasures/{case_id}/decisions` | 5.7K plan/status design approved |
| API-334 | GET | `/me/privacy/erasures/{case_id}` | 5.7K requester status design approved |
| API-335 | POST | `/admin/privacy/erasures/{case_id}/execute` | 5.7K execution blocked / not enabled |
| API-336 | GET | `/admin/qr-batches/{batch_id}/print-exports/{job_id}` | 5.4A approved metadata only |
| API-337 | POST | `/admin/qr-batches/{batch_id}/print-exports/{job_id}/download` | 5.4A approved encrypted bytes only; one-use session-bound grant, never plaintext |
| API-338 | POST | `/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants` | 5.4A approved ready-job grant issuance; current role/authority/recipient checks |
| API-340 | POST | `/admin/orders/{order_id}/cancellation-reconciliations` | 5.3A explicit owner approval 2026-10-20; finance/MFA, Doc 04 exact contract |
| API-341 | POST | `/admin/orders/{order_id}/cancellation-decisions` | 5.3A explicit owner approval 2026-10-20; operations/MFA, Doc 04 exact contract |

API-311–319 and API-344 onwards remain unallocated after the explicit 2026-10-20 API-340/341 and API-342/343 approvals. Subsequent explicit owner approval allocated API-339 to the read-only configured catalog template discovery contract in Doc 04 / Task 5.1A; this does not activate O-05 template creation/approval or change this blocked-task review’s dispositions. Runtime API-245/246/247 and all existing canonical routes/operation IDs remain unchanged. The ledger does not authorize implementation of optional template management or new staff-role grants. A future task must implement actual schema/DTO/OpenAPI tests and rehearse any migration before requesting application.

## Task disposition and exact remaining gates

| Task | Before → after | Approval removed | Remaining acceptance/execution gate |
| --- | --- | --- | --- |
| 2.3B | BLOCKED → TODO | Role/dual-control/runbook design | Named independent custodian/approver and synthetic human drill; no real grants |
| 2.3D | BLOCKED → TODO | App-state/session/recovery contract | Implementation/migration/session reconciliation and human security drill |
| 3.5C | BLOCKED → TODO | Case approval, identity/profile/artifact consequences | Implementation, independent authority and actual physical release |
| 4.4A | BLOCKED → BLOCKED | Fail-closed fallback/proxy trust design | Concrete staging topology/hostname and live widget authorization/evidence |
| 4.4C | BLOCKED → BLOCKED | Generic English copy/version/retry design | Domain, deliverability authorization/receipt and native copy evidence |
| 5.3A | BLOCKED → TODO | Request/reconciliation/release boundary | Implementation and synthetic finance/operations decisions |
| 5.3B | BLOCKED → TODO | Finance case scope/dispute fence/refunds-disabled | Implementation and human finance review; O-06 remains disabled |
| 5.4A | BLOCKED → TODO | Generation-time sealed transport/custody protocol | Implementation, printer fingerprint/custodians and physical acceptance |
| 5.6A | BLOCKED → BLOCKED | Actual code-aligned schema/workbook sharing design | Concrete workbook/tab/service-account mapping and live-write authorization/evidence |
| 5.6B | BLOCKED → BLOCKED | PDF seven-day design/orphan/hold protocol | Evidence/legal schedule, policy records and live disposable-object authorization |
| 5.7J | BLOCKED → TODO | `basic_v1` authority/manifest/redaction/delivery contract | Implementation, human scope/identity review and synthetic delivery/expiry drill |
| 5.7K | BLOCKED → BLOCKED | Plan/status/checkpoint/recovery design | Actual legal/financial/guardian/class/backup policy before purge execution |
| 6.3B | BLOCKED → BLOCKED | Recovery protocol and target objectives | Actual backup/key custody, target capability, restore authorization and measured drill |

No task is marked IMPLEMENTED or VERIFIED by this document. New roadmap totals: **70 tasks: 26 VERIFIED, 12 IMPLEMENTED, 26 TODO, 6 BLOCKED**. Next newly unblocked feature after 5.7I is **5.7J**, with the `basic_v1` scope above; it does not authorize 5.7K erasure or real exports. Existing earlier TODO tasks retain their dependency order.

## Verification required in each implementation task

Rehearse additive DDL and rollback before requesting application. Verify actual canonical OpenAPI against this ledger, including absent/unimplemented reserved endpoints. Use isolated synthetic accounts/providers and dedicated artifact directories. Cover forbidden roles and current session/AMR, authority/IDOR/guardian boundaries, stale and concurrent decisions, one-use grants, encrypted AAD/key failure, original-recipient redaction, case closure side effects, active holds versus workers, exactly-two identities, stale QR/artifact sources, duplicate settlement/release, provider ambiguity and backup resurrection. Test denied paths as well as allowed paths. Run only focused tests/lint/typecheck and a bounded browser flow for the selected implementation; no full-suite, provider, physical or legal acceptance is claimed by this documentation review.

## Provider facts checked during review

- [Cloudflare server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/): server verification is required; tokens are single-use and valid for 300 seconds. This supports the binding/expiry design, not acceptance of the actual hostname or proxy.
- [Resend idempotency](https://resend.com/changelog/idempotency-keys): retained provider keys have a 24-hour window and require the same payload. This supports retaining the existing stricter 23-hour ambiguity cutoff, not claiming exactly-once inbox delivery.
- [Google Sheets authorization scopes](https://developers.google.com/workspace/sheets/api/scopes): scope applies to a workbook file, not one tab. Dedicated-workbook isolation remains necessary.
- [Supabase database backups](https://supabase.com/docs/guides/platform/backups): Storage object bytes are outside database backups. Hosted plan entitlements, object backup and key recovery require their own evidence.

These are provider contract checks on the review date, not legal advice, legal sign-off, live configuration inspection or provider actions.

## Review evidence and limitations

Documentation/source consistency check PASS on 2026-10-19: all 13 review sections and explicit anchors; exactly seven BLOCKED→TODO card changes, six remaining blockers, unchanged 5.7G/H/I statuses and reconciled phase/roadmap arithmetic; all twelve specification links and task-decision links; eleven template ID remaps preserving method/path; nineteen unique future route reservations consistent with Doc 04; actual source-generated OpenAPI keeps API-245/246/247 unchanged and contains none of the thirty future reserved IDs; Sheet column list matches the actual worker. Evidence artifact: `output/blocked-review/review-checks.json` (local ignored artifact, no credentials).

The initial link-check script incorrectly assumed every review link had an anchor; it stopped with ValueError before completion. Corrected to support plain-document and anchored links, then the complete consistency check passed. This is a documentation checker correction, not a product test failure. Git diff whitespace validation and post-review runtime health are recorded in the phase handoff. No feature tests, full suite, migration rehearsal/application, live provider acceptance, legal/physical certification or production readiness is claimed for this review. No new implementation task was started.

### BTR-08 implementation follow-up (2026-10-20)

Owner explicitly approved the four Task 5.4A pre-implementation directions recorded in PHASE_IMPLEMENTATION.md. Exact API-093/336–338, original-source enrollment/provenance, distinct executor/security custody, encrypted database spool, bounded durable job, session/revision grants and signed accepted/not_received reconciliation contracts are now in Doc 04/03 and the Doc 09 controlled procedure. No new endpoint, role grant/editor, retention period, credential-recovery policy or physical-release writer. No real provisioning, export, printer delivery, signature import, migration application or runtime activation authorized/performed. Implementation evidence/remaining gates belong to the Task 5.4A handoff; original decision/disposition history and Task 6.4 physical release remain unchanged.

### Task 5.7B contract approval follow-up (2026-10-20)

Owner explicitly approved the four A–D dashboard proposals recorded in PHASE_IMPLEMENTATION.md. Doc04 now allocates API-344/345 to role-scoped count/trend reads; future unallocated IDs346+. Doc03/09 define pending0028 count-only helpers and observation/rollback boundaries. No registered-user/Auth helper, metric-role inheritance, financial accounting/recovery/retention/alert policy, new writer or other task is implemented by that approval. Unimplemented matching drill-downs and2.3C remain explicit dependencies, not fabricated aggregate values. Actual DB/runtime/manual acceptance remains separate; preserve all prior BTR decisions and statuses.


## Owner approval — Task 2.3C A–E (2026-10-20)

Owner replied “approve” to the explicit A–E directory review in PHASE_IMPLEMENTATION.md. This separately approves API346–348 metadata-only reads, security_admin-only authority, exact UUID/filter/keyset contract, retained-nonanonymous Auth population and1000+ count cap, default-disabled flag and narrow pending0029 helper/offline rehearsal. Support account-state lookup is explicitly excluded until a distinct case-subject/fields/purpose contract is approved; superadmin inheritance is not approved. Doc04 defines the final closed DTOs/errors. No2.3D/5.7C implementation, new role, broad Auth read grant, live Auth action, migration application, configuration activation or service restart is authorized. Prior BTR-01/02 and all other decisions/gates remain unchanged. Future unallocated API IDs begin349; API339/344/345 stay unchanged.


## Owner approval — Task2.3D A–F (2026-10-20)

Owner replied “approve” to A–F in PHASE_IMPLEMENTATION.md after the explicit missing-contract review. This refines BTR-02 with exact API320–322 closed command/result/reason/error/Origin/idempotency contracts, case-bound single-use independent approvals, expiring controlled custodian evidence/last-custodian checks, session-created-at cutoff plus shared/exclusive transaction admission, epoch-based grant/job fences, safe encrypted replay and refusal to downgrade durable security history. Doc04 contains the exact affected-authority inventory, including safe unavailability for untimestamped privacy authorities. Pending0030 follows0029; no new IDs/roles or general Auth SELECT grant.

Only Task2.3D synthetic implementation is approved. No live authority provisioning, actual named custodian proof, provider/session metadata acceptance, real suspension/restoration/Auth/factor/credential/email write, migration application/config/runtime activation, export/delivery/provider/worker execution or2.3B/5.7C implementation. API346–348 DTOs/disabled flag and NOT_IMPLEMENTED suspension projection stay unchanged; API339/344/345 and prior decisions/gates retained. Implementation evidence cannot certify PG locking/MVCC/ACL or human custody; those remain separate gates.


## Owner approval — Task5.7C A–F (2026-10-20)

Owner replied “approve” to A–F in PHASE_IMPLEMENTATION.md. Approval covers explicit security_admin console/navigation users.manage/fixed MFA return, opt-in API347 include=account_security ready/unavailable application state/revision/configuration union with unchanged default, pending0031 narrow read helper/offline-only rehearsal, fixed same-origin bounded typed relays and safe confirmation/receipt/current-state/uncertain-idempotency interactions. No new backend API ID, role, general Auth SELECT, real approval/custody provisioning or lifecycle activation. Case discovery remains explicitly unavailable pending its own minimum-fields/subject/permission contract; support/audit links do not widen roles. Docs03/04/07/11 define exact final boundaries. Prior API339/344/345 and320–322/346–348 IDs/defaults, installed0021/pending0022–0030, owner operations AND finance, prior PG/provider/custody/manual gates retained. Synthetic console implementation is not live runtime or human acceptance authorization.
