# Phase 4: logical item checkout

This document records the Phase 4 handoff. Migration `0040_item_checkout` is authored but unapplied, and its admission row defaults to disabled. Current Phase 5 source progress and superseding allocation behavior are recorded in `VERIFIED_QR_ALLOCATION_PHASE5.md`; this is not a rollout.

## Contract and customer behavior

`POST /api/v1/me/checkout/item-quotes` accepts `commerce_model: "single_qr"`, delivery/contact confirmation and `items`. Each item has `product_id`, optional `identity_group`, and `sizes: [{variant_id, copies}]`. Price, totals, QR type, QR IDs and public tokens are not accepted. Both quote and confirm require the existing authenticated verified-account transaction dependency and an idempotency key.

The server groups by `(product_id, identity_group)`, where absent/null group means one default item for that product. Repeated variants have their copies summed. A nonempty group is an explicit request for another QR identity. Copy limits apply across every size of each logical item. The backend resolves the selected product/type, active sizes and matching reviewed template specifications; computes `sum(copies) * product.price_per_copy` using Decimal; and returns server totals. Shipping/tax continue using the existing configured PKR policy. There is no stock reservation at this stage.

`POST /api/v1/me/checkout/item-quotes/{quote_id}/confirm` accepts only `accept_total` and `accept_currency`. It locks the actor's quote, checks status/expiry/total/model and revalidates product/variant versions, price/cap/type, exact template specifications and official instructions. Any difference invalidates the quote. It writes one logical item with separate size snapshots, encrypted purchase delivery details, immutable totals and official instruction snapshots; places the order; confirms the quote; and checks deferred constraints before returning. The shared transaction/receipt/audit wrapper commits before HTTP success. No QR is assigned and no legacy pair is reserved. Replays use the existing actor/operation/key receipt; a different confirmation key must still pass the locked quote's open-state check.

The live product configurator chooses the new UI only for explicit `single_qr` products. It supports multiple sizes and copy counts, default merging and an explicit separate-identity checkbox. New cart storage contains only product/group/variant/copy choices under `safereturn-item-cart-v2`; it never stores quoted prices, addresses, payment grants or tokens. Legacy `safereturn-cart-v1` is preserved. Mixed models are presented as separate checkouts/orders. Each successful checkout clears only its own cart. Failed/uncertain requests preserve choices; confirmation retries retain their key. Stale/expired quotes obtain a fresh quote key. Cart/contact changes invalidate the displayed quote and total acceptance.

Customer order detail displays the logical item's selected type, size/copy breakdown and immutable unit price/total. Staff order detail can validate the new model and report identity/item/copy counts while continuing to strip private snapshot details from the browser projection. Existing legacy response shapes remain unchanged.

## Bank/Raast instructions and private evidence

No approved destination values exist in the repository, so none are invented. The new protected, empty `checkout_payment_instructions` table stores versioned approved bank name, account title/number, Raast ID, English/Urdu instructions and approval attribution. Runtime roles cannot edit or directly read it. A narrow helper returns only the active official instruction fields. A new quote fails with `PAYMENT_INSTRUCTIONS_UNAVAILABLE` until a reviewed record exists. Quotes and orders snapshot the instruction values; changed instructions invalidate confirmation.

`GET /api/v1/me/orders/{order_id}/payment-instructions` uses verified-account and order-owner authorization and returns the order's frozen instructions. The existing payment page displays them and retains its private signed upload/finalize flow. Missing instructions are explicitly unavailable. Evidence is not verification: uploading/finalizing a screenshot leaves payment under review. The browser scenario exercises upload/finalize retry without uploading again or changing that claim.

Approving actual values and deciding who may edit/activate instruction records remain owner decisions for rollout. There is no new editor or runtime grant for those records in this phase.

## Additive schema and coexistence

Migration `0040_item_checkout` follows `0039_single_qr_catalog`:

- `orders.commerce_model` and `checkout_quotes.commerce_model` default to `legacy_pair`; order model is immutable. Existing rows are not converted.
- `orders.payment_instructions_snapshot` is nullable for legacy rows and immutable once set.
- `order_logical_items` records product/type/name, explicit group, combined quantity/cap, PKR unit price/total and product version. An expression unique index allows exactly one default item per order/product and one per explicit group.
- `order_item_sizes` records variant/name/SKU/mm/material/copies/version and the full reviewed print specification. Unique item/variant and item/mm constraints prevent duplicate size selections after normalization. Generated revision/approval IDs have RESTRICT foreign keys to SQL-managed registry records.
- Snapshot tables use RLS, owner-only draft inserts and owner/authorized staff reads. Runtime UPDATE/DELETE and worker table access are absent. Triggers reject snapshot rewriting, product/type/size/specification mismatch, mixed models and incomplete placed-order totals/copies/shipping.
- The original legacy completion function's body is retained with an explicit single-model dispatch. The old quote/confirm contract and legacy catalog helper remain pair-specific. New tables contain no historical backfill.
- Public catalog includes typed products only through the disabled `single_checkout_release` gate and physical/type approval filters; includes explicit model/type fields; and retains legacy listing rules. Neither the API nor worker can change this release row.
- Legacy payment verification cannot settle a typed order: both the reviewer and new DB guards reject typed verification/allocation. Phase 5 must replace those guards with atomic verified allocation. This gate is independent of customer checkout admission.

Existing pairs, profiles, token URLs, legacy purchase rows and print snapshots are not rewritten. Public scans and ownership are still legacy-only until their later phase. No public token is used for checkout authorization or entitlement.

## Validation and remaining gates

Scoped backend result: **347 passed, 6 opt-in PostgreSQL cases skipped, 2 older integrated browser cases deselected**. This includes 51 new Phase 4 contract/orchestration checks plus legacy checkout input, pricing, inventory, order-console, catalog, template, storage, staff and transaction-boundary checks. New cases cover multi-product/type/size arithmetic, default merge and explicit separation, limits, strict quantities, tampering, address-source validation, unavailable approvals, stale price, closed/expired/cross-owner quotes, snapshots without allocation, receipts/replay/key conflict, missing official instructions, auth denial and typed verification blocking.

Frontend: **5 current-component browser scenarios passed**. They exercise single-type multi-size checkout and server totals; confirmation uncertainty/retry; stale-confirmation refresh with a new quote key; default merge/intentional separation; unavailable size gating; official instructions; private evidence retry; cart preservation and mobile Urdu layout. English quote/submission and mobile Urdu screenshots were inspected. The dedicated actual-code VM checks for cart sanitization, typed staff summaries and checkout relay authorization/origin/targets/key transport passed. TypeScript and scoped Ruff/whitespace checks passed.

The older `node scripts/test-orders.cjs` passed 72 contract/navigation assertions and its relay checks, then failed in the existing page-mock harness on the `next/link` import from an unchanged admin page. That older full script is not reported as passing. Its page mocks and older integrated technical-editor fixtures still need reconciliation.

These results are synthetic/offline acceptance, not proof of PostgreSQL execution, RLS/MVCC, real Auth/Next SSR or provider behavior. Six opt-in checks are provided in `backend/tests/integration/test_item_checkout_postgres.py` for upgrade preservation, closed admission, ACL/RLS, immutable model, and incomplete placement rollback. They were not run. Before rollout, the isolated rehearsal must also exercise complete approved positive checkout, different-key confirmation races, same-key replay, audit/commit failures, snapshot/quote tampering and cross-owner runtime access on PostgreSQL; then run integrated browser/Auth/private-storage acceptance. Template authority holds and typed privacy export/readers must be extended in their affected later phases before admission.

Reproducible frontend commands from `frontend`: `npm run test:item-checkout`, `npm run test:item-contracts`, `npm run typecheck`.

Next is Phase 5: atomically verified payment and one permanent distinct QR claim per logical item, including stock exhaustion policy, concurrency and rollback acceptance. Printing, shipment membership, ownership/activation and public standalone scans remain later work. No migrations were applied, environment variables changed or deployment performed.
