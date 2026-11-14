# Phase 5: verified settlement and permanent QR allocation

Source implementation is complete. Migration `0041_verified_qr_allocation` follows `0040_item_checkout` and is authored, not applied. Customer admission stays disabled. Phase 6 printing/fulfillment has not been started.

## Approved shortage policy

The owner explicitly selected this policy in the current implementation chat: **record independently verified payment as verified, hold the whole order for reconciliation, allocate nothing partially, and perform no automatic refund**. This is represented separately from payment status. It is not an unpaid/rejected payment or an automatic backorder/refund promise.

An authorized finance/operations retry can satisfy the entire order after restocking or clearing a hold. Existing allocations never change on retry. Refund execution and standalone activation remain separate future workflows.

## Live contracts and screens

- Existing `POST /api/v1/admin/payment-attempts/{attempt_id}/reviews` retains the finance/MFA guard, encrypted idempotency receipt and transaction dependency. Legacy pair review still uses its original reservation/allocation writer. `single_qr` verification dispatches to a narrow SQL settlement helper after order/attempt locks, independent bank confirmation and exact amount/currency validation. Screenshots do not invoke this helper.
- New `GET /api/v1/admin/orders/{order_id}/qr-allocation` returns safe allocation state/reason and requested/allocated identity counts to authorized finance/operations staff.
- New `POST /api/v1/admin/orders/{order_id}/qr-allocation/retry` accepts only `{confirmed: true}` with an idempotency key. It accepts no QR ID, token, price or substitute payment assertion. The SQL helper rechecks the live session and exact allowed staff roles after lock waits and before success.
- Owner and staff order detail add an `allocation` projection for typed orders. State is `awaiting_verified_payment`, `reconciliation_pending` or `allocated`; pending has zero claims and allocated has exactly the requested number. It contains no token, purchaser identity or private bank/evidence fields. Existing legacy detail shapes remain unchanged.
- The live UUID staff order console exposes whole-order retry only for pending typed allocations. It clears privileged allocation data on denied/failed refresh and preserves retry keys after uncertain responses. Refresh establishes a fresh deliberate retry attempt. Customer order detail distinguishes verified money, requested identities and allocated identities.
- `/admin/payments/review` connects the existing bank review form to an actual finance/MFA guarded route, linked from the payment queue and individual attempts. Optional order/attempt IDs are validated; a supplied attempt ID is read-only in the form. The exact route is added to the MFA return allowlist. Review results distinguish verified-but-held from verified-and-allocated; neither claims print/dispatch completion. Private evidence downloads remain behind the existing finance-authorized relay.

The relay retains server-held bearer transport, same-origin mutation checks, no redirects and no-store responses. Existing legacy payment/evidence/instruction targets remain allowed. Error text does not expose upstream private details in the new allocation controls.

## Transaction and concurrency design

`sr_typed_settle` runs inside the existing payment receipt/audit transaction. It rechecks finance role, verified live session and MFA; locks order before attempt; rejects a closed attempt/order; validates independent bank confirmation and exact PKR settlement; and writes the verified review/attempt/order and typed settlement ledger together. The bank reference is normalized and HMACed by the existing stable reference-key scheme, with the existing global verified-reference unique index spanning both legacy and typed orders. Raw bank references and fingerprints are not added to allocation status, audit details or event payloads.

Allocation counts **logical items**, never sizes or copies. Required QR types are locked in deterministic order. Candidates must be current, unactivated standalone identities from matching generated typed batches, available/unclaimed with no owner or existing permanent claim. Ordered QR/state row locks use `SKIP LOCKED`. The allocator selects enough candidates for every required type **before writing any claim or inventory transition**. An unavailable or temporarily locked identity may produce reconciliation; payment truth is still retained and retry remains possible.

If stock is short, ledger state is `reconciliation_pending` with `stock_shortage`; payment stays verified and fulfillment stays unallocated. Existing financial fences, active cancellation requests or withdrawn template approvals also hold a verified order, with distinct safe reason codes. Registry shared locking protects historical approval checks against concurrent withdrawal. Historical approved snapshots are used; changing current catalog prices or bindings does not rewrite a submitted purchase.

If all stock is present, each item gets one distinct permanent claim and its standalone inventory state becomes allocated. Purchaser entitlement is recorded on the claim; standalone ownership/activation fields are not activated. Inventory cannot be reused after a dispute/cancellation or on a repeat request. Whole-order completeness is a deferred invariant, checked before the endpoint returns and again at commit.

The same transaction writes safe audit events, immutable durable allocation handoff events and the existing finance sync job. A failure in claim/state transition, handoff enqueue, audit, receipt encryption or final commit rolls the whole transaction back. The API does not commit inside the helper. Different review keys and attempts still contend on the order lock; the first verified settlement closes later review writers. Receipt replays cannot mint a replacement QR. Retry of an already allocated ledger returns its existing allocation state.

## Additive schema and legacy coexistence

`backend/alembic/versions/0041_verified_qr_allocation.sql` adds:

1. `typed_order_settlements`: one permanent ledger per order and unique attempt, immutable financial identity, revisioned reconciliation state and terminal allocation state.
2. `order_item_qr_allocations`: primary key on logical item and unique QR ID, with RESTRICT FKs to the item, QR, ledger and purchaser/allocator accounts. Claims cannot be moved, updated, deleted or recycled.
3. `typed_allocation_events`: immutable `(order, settlement_revision)` handoff, either `allocation.ready` or `allocation.reconciliation`. It is durable work storage for a later consumer, not a print success or a live worker lease.

All three tables use RLS without direct runtime table grants. Only status, settlement and retry helpers are executable by the API role; internal allocator/check functions and the tables have no API/worker access. Runtime helpers enforce role/session admission independently of the Python guard. Deferred checks bind verified attempts/reviews to the ledger and require either zero assignments or every logical item assigned with matching QR type and allocated inventory state. Unique constraints/FKs protect relational identity; claim guards also reject cross-order/type assignments. An unpaid order cannot claim allocated fulfillment.

The migration refuses to silently adopt pre-existing standalone allocated fixtures without claims; such fixtures require explicit reconciliation before upgrade. No legacy product, order, pair, profile, public token URL or frozen print row is backfilled or rewritten. Existing pair review and legacy finance change-trigger behavior are retained. Typed finance change events use their own once-per-ledger-revision enqueue. Existing financial reconciliation signals now recognize typed allocations: allocated typed orders do not appear falsely pair-less, while pending verified orders remain actionable under `VERIFIED_ALLOCATION_MISMATCH`.

Typed production stays closed through explicit DB guards on new print jobs, shipments and old pair print/render jobs. No `allocation.finalize` legacy job is enqueued for a typed order, even when printing is enabled. `fulfillment_eligible` remains false in typed review/retry responses until Phase 6 supplies the complete production path. Checkout release remains the disabled Phase 4 gate. Public scans and standalone ownership remain closed until their own phase.

## Validation and limits

Final scoped backend regression: **449 passed, 17 opt-in PostgreSQL tests skipped**. The 36 new Phase 5 unit/model checks exercise authoritative finance/MFA denial, amount/currency/bank confirmation, closed/cancelled review, strict retry payloads, safe errors, helper dispatch, no legacy writer on typed verification, preserved legacy pair verification, non-verifying reviews, unique item/QR/attempt constraints, reconciliation consistency and preserved legacy finance trigger source. SQLite model checks do not prove PostgreSQL locks, triggers, cross-schema Auth FKs or RLS.

Four new current-component browser scenarios passed, plus all five Phase 4 cart/checkout/private-evidence browser scenarios. They cover whole-order hold wording, exact identity counts, explicit retry, uncertain retry keys, denied refresh clearing data, finance result wording, no browser storage of review data, and mobile Urdu layout. Allocated/requested counts use an isolated LTR number span in RTL text. English and Urdu screenshots were inspected. Actual-code VM checks passed for allocation invariants, finance page role/ID guards, the MFA return allowlist, payment relay session/origin/path/header behavior and existing item-cart/order-summary contracts. TypeScript, scoped Ruff and whitespace checks passed.

A legacy financial-fence worker test used a stale mock signature. Its mock now accepts and asserts the existing `admit=False` failure-bookkeeping call. Production worker code was not changed. The older orders page-mock script/older full-stack fixtures noted in Phase 4 remain separate unreconciled harness gaps; this phase does not claim the entire repository test suite passes.

`backend/tests/integration/test_verified_qr_allocation_postgres.py` contains **17 unrun opt-in cases** for disposable PostgreSQL namespaces. They cover competing review transactions, different attempts on one order, a shared reference across orders, the last typed QR, shortage followed by complete allocation, repeat settlement/retry preserving QR IDs, cancellation ordering/races, live role/MFA/session denial, ACLs and injected claim/state/audit/outbox/finance-enqueue rollback. Fixtures use synthetic privileged catalog/approval records without disabling guards; they do not establish real publication evidence or physical QA. The fixture verifies preservation of a legacy order across the upgrade and confirms release defaults to disabled before enabling only its isolated test namespace.

Real PostgreSQL execution, migration/ACL/MVCC correctness, API receipt/commit crash rehearsal, real Auth/Next SSR and provider/worker acceptance remain required before rollout. None was performed here. Native Urdu/manual accessibility and physical QA remain acceptance work. No database migration was applied, environment variable changed, service deployed or external message sent.

Cancellation requests can pause typed allocation; a new pair-less cancellation completion/refund workflow is not introduced here. The legacy completion helper still requires pair units. That new-model workflow needs policy/implementation acceptance before customer rollout, while existing legacy cancellation remains intact.

Reproducible frontend commands from `frontend`: `npm run test:allocation`, `npm run test:allocation-contracts`, `npm run test:item-checkout`, `npm run test:item-contracts`, `npm run typecheck`.

## Phase 6 handoff

Add the typed durable-event consumer and print/fulfillment support, using the item's single permanent claim and each immutable size/copy specification. Recheck financial/cancellation/template holds before production and artifact release. Extend manifests, print workers, QA, private download grants and shipment membership without changing legacy frozen reprints. Add real PDF decode/count/dimension and full rollback/concurrency acceptance. Standalone customer entitlement/activation/public reads remain Phase 7. Safe cleanup stays deferred.
