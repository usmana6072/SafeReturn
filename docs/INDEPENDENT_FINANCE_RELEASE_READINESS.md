# Independent-QR finance implementation and controlled release proposal

Status: implementation prepared; NOT released, NOT PostgreSQL-accepted. Development target remains `fhuxryfkfrvycsojkzvq`. No database, provider, role, MFA, migration or protected release change was performed in this task.

## Dependency findings

The earlier explanation that finance was entirely pair-only was incomplete. Phase 5 migration 0041 already adds `sr_typed_settle`, typed settlement ledgers and one permanent claim per logical item. It also updates reconciliation to understand typed ledgers. However, the original Python review endpoint and SQL reconciliation function still contain legacy branches. The 70-operation frontend quarantine intentionally blocks those shared paths. This task does not bypass or remove that boundary.

- API-241 `POST /admin/payment-attempts/{attempt_id}/reviews`: existing mixed-model writer; typed branch already uses the verified allocator; legacy branch locks/updates `order_pair_units` and can enqueue `allocation.finalize`.
- API-342/343 `GET /admin/finance/reconciliation` and `/counts`: shared global SQL still contains `order_pair_units` queries for legacy orders.
- `GET /admin/orders/{order_id}/qr-allocation` and `POST .../retry`: quarantined allocation reads/recovery. Replacement exact-order snapshot subsumes the read; retry delegates to the existing typed helper.
- Order detail/cancellation/financial-review and print/fulfillment paths remain quarantined separately. Releasing finance alone cannot release the whole downstream lifecycle.
- Safe existing reads: exact order metadata lookup, finance payment attempts and private evidence. They remain unchanged.
- Actual privileged freshness requirement is 300 seconds (`privacy_exports.recent`, also used by financial disputes). Replacement uses the existing Python helper and repeats the same check in SQL after lock waits and before return.

## Implementation

Prepared additive `0051_independent_finance` follows 0050 without rewriting any historical migration. It adds four functions only, creates no tables and seeds no rows:

1. `sr_independent_finance_snapshot`: finance/session-authorized exact independent order, immutable amount due, current states, typed allocation status, bounded 100-review history and stored-state discrepancy signals. Records a safe read audit event. No legacy order scan or pair relation is referenced.
2. `sr_independent_finance_authorize`: verified live finance/MFA session, 300-second freshness and exclusion of the purchasing account. Internal only.
3. `sr_independent_finance_review`: order-before-attempt locks, authorization rechecks and independent-only model. Verify delegates exclusively to `sr_typed_settle`; reject/request-more-info append existing review records and preserve another open attempt's pending order state. No second allocator. Freshness expiration after writes raises, so the outer transaction rolls back.
4. `sr_independent_finance_retry`: calls the existing whole-order typed retry with independent finance/self-review/freshness checks before and after it.

All four functions revoke PUBLIC, anon, authenticated, API and worker access. There are deliberately **no runtime grants**. Migration installation by itself cannot release these entry points.

`app/services/independent_finance.py` reuses existing encrypted receipts, idempotency, audit/transaction wrapper, HMAC bank-reference scheme and safe private evidence metadata read. Settlement input is never inferred from screenshots/customer references. Authorization and origin checks run before receipt replay; SQL rechecks authority inside the mutation. No raw bank reference or HMAC is returned. Existing global reference uniqueness, order/attempt locks, ledger/item/QR uniqueness and deferred completeness constraints remain authoritative. Existing shortage policy is preserved: verified money, whole-order reconciliation hold, zero partial allocations, no automatic refund.

The replacement router reuses original quarantined URLs; it is **not imported/mounted by app.main**, and its admission function unconditionally returns `INDEPENDENT_FINANCE_NOT_RELEASED` after finance authorization. The original API-241 review route and the typed allocation status/retry routes are also closed at the FastAPI boundary after staff authorization: they return 503 before entering their old handlers. This closes direct-backend access that the frontend quarantine alone could not stop. Their paths remain in OpenAPI for the later in-place replacement; the frontend 70-operation registry remains unchanged.

Closed backend snapshot DTOs and frontend parsing cover order, attempts, customer-submitted reference, private evidence metadata, verification history, discrepancy signals and separate allocation state. The existing ledger stores an HMAC, not a retrievable raw bank settlement reference. Returned verified settlement amount/currency are the immutable attempt values whose equality is required by settlement verification. Bank-ledger feed comparison and raw settlement-reference retrieval are explicitly unavailable; no bank feed is invented.

The staged admin panel supports server reads, manual independent settlement entry, verify/reject/request-more-info, verification notes, retry-key retention after uncertainty, clear-on-failed-refresh, bounded review history and confirmed whole-order allocation retry. Production mounts it with release=false, and the new relay independently returns 503 without any upstream request. A prepared authenticated same-origin typed transport still calls `guardedBackendFetch`, so original quarantine rules block it even if someone directly invokes that transport. Reconciliation's original protected page remains `AdminQuarantined`.

## Scope limits and security gates

This implements exact-order reconciliation, not a global financial queue/counts dashboard. It does not enable API-343 or fabricate global counts. Evidence remains accessible only through the existing finance/MFA private byte-stream relay. No public URLs are added. No new bank ledger integration or automated settlement verification exists.

Static function/service inspection shows no direct pair-allocation calls in replacement code. This is **not proof of zero nested legacy relation execution**: existing allocator/registry policies, triggers, RLS and security-definer dependencies must be traced in the authorized PostgreSQL rehearsal. The source-level test and old allocator tests do not substitute for that proof.

New SQL has not been applied or executed. Genuine provider Auth/MFA/recent-session acceptance, real PostgreSQL constraints/locking, concurrent verification, duplicate reference collisions, failure-at-commit/audit/encryption rollback, read query plans and durable handoff tests remain approval-gated. Mock tests cannot establish those properties. The new code is not represented as release-ready merely because unit/browser tests pass.

## Minimal approval proposal

Do not enable finance now. First approve a separately isolated development rehearsal of migration 0051 and synthetic fixture writes. Exact fixture design must be reviewed: separate customer and finance identities, two logical items with multiple sizes/copies, typed stock and approved template snapshots, payment attempts/reviews, and cleanup/rollback boundaries. No real customer's order, bank approval or QR allocation may be used. Rehearsal must prove actual no-auth/no-MFA/wrong-role/stale/self-review denial, amount/reference matching, same/different-key concurrent replay, duplicate reference rollback, stock shortage/no partial claims, allocation retry, audit/receipt/commit failure rollback and unchanged legacy/quarantine behavior. Genuine MFA tests require genuine disposable provider identities; synthetic AAL2 claims are not acceptance evidence.

After those results and separate explicit release approval, the smallest release is:

- Apply the reviewed additive migration to the pinned development project.
- Grant only snapshot/review/retry entry functions to the runtime API role; keep the internal authorize function non-executable directly and all tables closed.
- Install the replacement **in place of**, never alongside, exactly the three existing route operations: GET reconciliation (exact-order contract), POST payment review and POST allocation retry. Do not re-enable legacy handlers or introduce alternate URLs. Add separately reviewed admission configuration and origin/key readiness; preserve finance/MFA/freshness checks.
- Make a separately reviewed narrow quarantine/admission change for only those three operations, and wire the closed frontend route to the prepared guarded transport. Keep the other 67 operations, including global reconciliation counts and general order detail, blocked.
- Enable the panel only from backend-confirmed capability/release state, then run genuine authenticated browser acceptance. Review every supported direct backend client; the historical quarantine is a frontend transport boundary, not a blanket FastAPI middleware.

Rollback: return panel/relay to closed mode, remove replacement route admission and revoke its three entry grants; never delete financial history, change verified payment truth, reassign QR claims or undo existing customer obligations.

No approval is requested to skip prerequisites. The next approval is for the reviewed isolated rehearsal, not live finance enablement.

## Executed validation (2026-10-27)

- Backend: **199 passed** in 25.88 seconds across `test_independent_finance.py`, `test_verified_qr_allocation.py`, `test_finance_reconciliation.py`, `test_payment_reads_safe.py`, `test_payment_storage.py`, `test_auth.py`, `test_release_gates.py`. These are isolated unit/model/HTTP checks. A new authenticated HTTP regression check confirms that API-241 and both allocation routes return 503 before settlement/allocation SQL. Existing allocator tests cover logical item/copy invariants and simulated transaction boundaries; they do not establish new SQL concurrency behavior.
- Browser: **20 passed** in 44.2 seconds using `playwright.independent-finance.config.ts`, including the closed production panel, synthetic approved-state workflow/retry behavior, denied refresh, private evidence transport and responsive existing payment reads. An initial test selector failed; it was corrected to select the actual named combobox and the complete suite passed.
- Quarantine: **131 passed**, all original 70 operations remain denied. An initial protected-page assertion failed after a proposed page change; that page was restored and all checks passed without changing the quarantine test or rules.
- Existing payment read relay: **37 checks passed**, 19 allowlisted GET calls, zero excluded requests. New closed relay/prepared transport test passed authentication, role, DTO, closed-route and actual quarantine checks with **zero upstream requests**.
- Scoped Ruff checks passed. Final production build and its TypeScript check passed after order-change stale-state hardening (52-second compilation; 33.4-second TypeScript stage). The three new browser scenarios passed again after that change. No frontend lint script exists.
- No live bank settlement, payment review, allocation, database fixture write or migration application was performed. No claim of PostgreSQL execution of 0051 is made.

## Files in this task

- New backend: `app/services/independent_finance.py`, `app/api/v1/independent_finance.py`, `app/api/v1/independent_finance_contract.py`, `tests/test_independent_finance.py`.
- Prepared migration: `backend/alembic/versions/0051_independent_finance.py` and `.sql`.
- Frontend: modified `components/admin-payments.tsx`; new `components/independent-finance.tsx`, `lib/independent-finance.ts`, `lib/api/independent-finance-relay.ts`, closed `app/admin/payments/finance-api/route.ts`, `tests/independent-finance.spec.ts`, `playwright.independent-finance.config.ts`, `scripts/test-independent-finance.cjs`.
- This report. The original reconciliation page was restored unchanged. Earlier customer checkout work and unrelated edits remain separate.

## Quarantine inventory

1. `POST /api/v1/me/checkout/quotes`
2. `POST /api/v1/me/checkout/quotes/{quote_id}/confirm`
3. `POST /api/v1/admin/qr-batches`
4. `GET /api/v1/admin/tag-pairs`
5. `GET /api/v1/admin/tag-pairs/{pair_id}`
6. `GET /api/v1/admin/qr-batches`
7. `GET /api/v1/admin/qr-batches/{batch_id}`
8. `GET /api/v1/admin/inventory/summary`
9. `POST /api/v1/admin/qr-inventory/batches`
10. `GET /api/v1/admin/qr-inventory/batches`
11. `GET /api/v1/admin/qr-inventory/batches/{batch_id}`
12. `GET /api/v1/admin/qr-inventory/summary`
13. `GET /api/v1/admin/qr-inventory/codes`
14. `GET /api/v1/admin/qr-inventory/codes/{qr_id}`
15. `GET /api/v1/public/qr/{token}/activation-context`
16. `POST /api/v1/me/tag-pairs/activation-intents`
17. `POST /api/v1/me/tag-pairs/activations`
18. `GET /api/v1/me/qr/{qr_id}/lost-profile`
19. `PUT /api/v1/me/qr/{qr_id}/lost-profile`
20. `GET /api/v1/me/qr/{qr_id}/ice-profile`
21. `PUT /api/v1/me/qr/{qr_id}/ice-profile`
22. `GET /api/v1/me/qr/{qr_id}/ice-contacts`
23. `POST /api/v1/me/qr/{qr_id}/ice-contacts`
24. `PATCH /api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}`
25. `DELETE /api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}`
26. `GET /api/v1/me/qr/{qr_id}/contact-preferences`
27. `PUT /api/v1/me/qr/{qr_id}/contact-preferences`
28. `GET /api/v1/me/tag-pairs`
29. `GET /api/v1/me/tag-pairs/{pair_id}`
30. `GET /api/v1/me/qr`
31. `GET /api/v1/me/qr/{qr_id}`
32. `GET /api/v1/admin/support-cases/{case_id}/independent-qr`
33. `POST /api/v1/admin/payment-attempts/{attempt_id}/reviews`
34. `GET /api/v1/admin/orders/{order_id}/qr-allocation`
35. `POST /api/v1/admin/orders/{order_id}/qr-allocation/retry`
36. `GET /api/v1/me/tag-pairs/{pair_id}/activation-history`
37. `PATCH /api/v1/me/qr/{qr_id}/public-status`
38. `POST /api/v1/admin/orders/{order_id}/print-jobs`
39. `POST /api/v1/admin/print-artifacts/{artifact_id}/download-grants`
40. `POST /api/v1/admin/print-downloads`
41. `POST /api/v1/admin/print-jobs/{job_id}/qa`
42. `POST /api/v1/admin/tag-pairs/{pair_id}/print-qa`
43. `GET /api/v1/me/orders/{order_id}`
44. `GET /api/v1/admin/orders/ready-to-ship`
45. `POST /api/v1/admin/shipments`
46. `PATCH /api/v1/admin/shipments/{shipment_id}`
47. `GET /api/v1/admin/orders/{order_id}`
48. `GET /api/v1/admin/orders`
49. `GET /api/v1/admin/shipments`
50. `GET /api/v1/admin/shipments/{shipment_id}`
51. `POST /api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry`
52. `POST /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds`
53. `DELETE /api/v1/admin/storage/artifacts/{artifact_id}/retention-holds`
54. `GET /api/v1/admin/support-cases`
55. `POST /api/v1/admin/support-cases`
56. `PATCH /api/v1/admin/support-cases/{case_id}`
57. `POST /api/v1/admin/privacy/exports/{request_id}/decisions`
58. `POST /api/v1/me/orders/{order_id}/cancel`
59. `POST /api/v1/admin/orders/{order_id}/cancellation-reconciliations`
60. `POST /api/v1/admin/orders/{order_id}/cancellation-decisions`
61. `POST /api/v1/admin/tag-pairs/{pair_id}/release-allocation`
62. `GET /api/v1/admin/support-cases/{case_id}/financial-review`
63. `POST /api/v1/admin/support-cases/{case_id}/financial-decisions`
64. `GET /api/v1/admin/finance/reconciliation`
65. `GET /api/v1/admin/finance/reconciliation/counts`
66. `POST /api/v1/admin/qr-batches/{batch_id}/print-exports`
67. `GET /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}`
68. `POST /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants`
69. `POST /api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download`
70. `GET /api/v1/admin/dashboard/summary`

## Protected file integrity

- `frontend/lib/api/quarantine-operations.ts` matches HEAD (line-ending normalized); SHA-256 `7d72feed4169af8914eebc5f07c76590e1d1d684652d37c0d1fc78432068b9d9`.
- `frontend/lib/api/quarantine.ts` matches HEAD (line-ending normalized); SHA-256 `149aac46c79198d1b19c707d32e792bbda5fa11762b331b2679c307ebdd9004a`.
- `backend/alembic/versions/0044_support_dev_exception.py` matches HEAD (line-ending normalized); SHA-256 `67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30`.
- `backend/alembic/versions/0044_support_dev_exception.sql` matches HEAD (line-ending normalized); SHA-256 `17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d`.
