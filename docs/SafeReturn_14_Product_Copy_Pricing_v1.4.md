# SafeReturn architecture amendment v1.4: product copy pricing

Approved pricing contract:

- Each product has one required `price_per_copy`, expressed as a decimal PKR amount.
- Every available size uses that same price. Variant-specific prices are legacy metadata, not checkout authority.
- Product subtotal is the sum of selected copy quantities multiplied by the product price.
- `max_order_copies` applies to the combined quantity across selected sizes. The existing 100-copy request ceiling is retained.
- Checkout accepts size/variant IDs and quantities, never customer-supplied prices or totals as pricing authority. Total acceptance is a confirmation of the server quote.
- Order item `unit_price_snapshot` and `line_total`, and order aggregate snapshots, retain the verified quote values. Later product edits do not rewrite them.
- The previously approved target of exactly one distinct QR identity per logical order item remains unchanged, irrespective of sizes or copies.

## Implementation boundary

Migration `0036_product_copy_pricing` is additive and has not been applied by this change. It follows repository head `0035_public_abuse_intake`; the installed database revision must be verified separately.

Existing products retain a nullable price until an admin explicitly configures one. No price is inferred from historical size prices. New inserts require an explicit price; the public catalog excludes unconfigured products and checkout rejects them. Historical order and quote rows are not backfilled or rewritten.

The API-backed catalog editor and the separate demo Add/Edit forms expose copy pricing. The redesigned Add/Edit forms still use their existing local demo store; this change does not turn them into backend persistence. Their displayed success is demo persistence only.

The repository still uses `new_pair`, pair reservations and pair allocation/activation. Independent single-QR allocation requires the separate cross-domain schema and workflow migration identified in the architecture audit. This pricing change neither implements nor proves that requirement.

Validation covers product price contracts, multi-size arithmetic, combined-copy limits, client price rejection and demo product edits. PostgreSQL migration/RLS/commit behavior and a fresh integrated browser build remain separate verification gates. The old catalog browser harness starts a prebuilt `tmp/task51a-web` artifact and cannot validate current frontend source without rebuilding that artifact.
