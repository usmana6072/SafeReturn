# Phase 6 — typed printing and fulfillment

Source implementation only. Migration `0042_typed_print_fulfillment` is authored, **not applied**. The customer checkout release gate stays disabled. No environment variables changed, no deployment occurred, and Phase 7 ownership/activation/public scan admission remains closed.

## Implemented behavior

- A private worker-only handoff consumes one `allocation.ready` event per iteration. A permanent unique event receipt, the existing `allocation.finalize` print request and audit event commit together. Reconciliation events never start production. Retries never allocate another QR.
- `sr_print_occurrences` branches by the order's immutable commerce model. A typed occurrence is a purchase size selection joined to its logical item's permanent claim. All requested sizes and copies repeat that same identity. Legacy pair occurrence SQL remains in place.
- Registry specifications come from immutable `order_item_sizes.print_spec_snapshot`, including the original approval/revision/assets. Reprints reuse the previous encrypted manifest, rather than resolving today's catalog. Both enqueue and worker checks compare occurrence ID, QR ID, type, size, quantity and token. The worker repeats the comparison after provider upload and before recording an artifact. A superseded typed job cannot publish a later `ready` state.
- The renderer's bounded total is 5,000 copies, matching the existing checkout maximum of 50 selections × 100 copies. Product combined-copy limits remain unchanged. QA accepts up to 50 observed type/size groups and 5,000 copies per aggregate observation.
- Existing operations/MFA/private download grants and checksum-checked downloads remain the transport. Typed allocation, payment, financial fences, cancellation requests and template holds are rechecked before releasing bytes. No public artifact URL or ownership credential is introduced.
- Typed QA requires every logical item ID to be explicitly inspected, all existing scan/scale/quiet-zone/bilingual/cutting checks, exact size/type/copy totals and the retained artifact checksum. The SQL guard also enforces these requirements for direct runtime writes. This records staff attestations; automated PDF tests do not prove physical approval.
- `shipment_items` records every logical item against the inspected print job. Membership is permanent, belongs to the order's permanent allocation and cannot coexist with pair membership. A complete order is shipped together. Packing must be explicitly confirmed before outbound states; the newest retained artifact must have physical QA approval. Deferred checks reject incomplete memberships and order status changes without a matching shipment.
- Template withdrawal holds now include typed purchase specifications. Order summaries report actual print status. The operations print detail page exposes the existing guarded print/download/QA controls; the packing queue submits typed item IDs. Shipment detail has a separate safe item-membership read endpoint.

## API changes

Existing paths continue to serve both order models:

| API | Change |
|---|---|
| `POST /admin/orders/{id}/print-jobs` | Typed frozen manifests; existing revision/idempotency checks retained. |
| `GET /admin/print-jobs/{id}` | Adds safe `inspection_items` metadata, without QR tokens. Metadata console validates and strips this before forwarding its smaller projection. |
| `POST /admin/print-jobs/{id}/qa` | Adds `inspected_item_ids`; required as an exact set for approved typed jobs. Legacy pair QA remains separate and unchanged. |
| Existing artifact grant/download APIs | Typed live production guards apply through the occurrence projection. |
| `POST /admin/shipments` | Exactly one of `pair_ids` or `logical_item_ids`; the server verifies the order model and exact complete membership. |
| `PATCH /admin/shipments/{id}` | Typed packing attestations alongside the existing guarded status transitions. |
| `GET /admin/shipments/{id}/items` | Operations/MFA-only typed membership and frozen print job IDs; empty for legacy shipments. |
| Existing ready queue, owner order detail and print summary | Typed eligibility, actual print state and requested copy totals. |

Frontend: `app/admin/print-jobs/[jobId]/page.tsx`, `components/printing-admin.tsx`, `components/fulfillment-admin.tsx`, `components/shipment-discovery.tsx`, their existing relays, and `lib/printing-contract.ts`.

## Migration and coexistence

New tables: protected append-only `typed_print_handoffs`, and operations-scoped `shipment_items`, with RESTRICT foreign keys. Models are in `backend/app/db/commerce.py`. New helpers default to no runtime access; only the bounded handoff and live-lease order-lock helper receive worker execute grants.

The migration extends installed legacy function definitions in place and aborts if expected definitions are absent. In particular it retains the registry wrapper installed by migration 0034, rather than replacing the earlier fulfillment predicate. No legacy row, pair constraint, token, profile, historical print manifest, grant or order snapshot is converted or deleted. New typed order status validation allows packed/dispatched/delivered, with independent deferred shipment checks. Refund admission remains closed.

## Validation and remaining acceptance gates

Final scoped results: **337 backend tests passed, 6 opt-in PostgreSQL tests skipped; 3 current-component browser scenarios passed; TypeScript, scoped Ruff and whitespace checks passed.** The print metadata harness also passed 61 contract/navigation assertions plus relay and ten simulated page-role branches. Alembic read-only head discovery reports `0042_typed_print_fulfillment`; the installed database revision was not queried or changed.

Focused offline tests cover real PDF decoding, repeated tokens across different sizes, distinct item identities, deterministic renders, binding tampering, the post-upload worker recheck, request boundaries and existing printing/payment/catalog/inventory regressions. Browser tests mount the actual React controls with synthetic transport responses; they cover typed QA, retry keys, denied-action clearing, typed packing and Urdu mobile layout. They do not prove integrated Auth/Next/storage behavior.

Opt-in `backend/tests/integration/test_typed_print_fulfillment_postgres.py` authors isolated rehearsal cases for migration compatibility, rollback/replay, shortage suppression, token/ACL denial, permanent claim projection, complete shipment membership/packing and stale revision rejection. **These PostgreSQL tests were not executed.** Do not run the repository's shared database harness or load credentials implicitly. A separately approved disposable target and actual full-chain rehearsal are required before applying migrations.

Remaining rollout gates:

- Real PostgreSQL function compilation, deferred triggers, RLS/grants, lock races, populated upgrade preservation and failure/commit rollback.
- Integrated worker lease expiry/crash recovery, storage upload/download retention, one-time grants and disputes/cancellation/template withdrawal races during provider I/O.
- Approved physical artwork, actual paper scans/dimensions and owner agreement on single-QR packing/custody procedures. New labels do not contain an ownership proof.
- Typed reprints after a shipment exists are rejected atomically, preserving the existing job and shipment. Reprints before shipment creation reuse the immutable manifest. No automatic relabeling, membership rewrite, QR recycling or refund occurs. Post-shipment replacement/repacking needs an explicitly reviewed append-only workflow before enabling that operation. Legacy historical reprints keep their existing path. Template withdrawal after dispatch similarly requires operational reconciliation; it must not be bypassed merely to advance tracking.
- Phase 5's typed cancellation-completion/refund gap remains. Phase 7 must extend activated standalone reprint authorization using authenticated entitlement; Phase 6 only admits unclaimed allocated standalone identities.
- Admission must remain disabled until these gates and Phase 7/8 acceptance are complete.

Stop here before Phase 7. Safe cleanup remains deferred.
