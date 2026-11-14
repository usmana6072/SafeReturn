# Phase 3 — real product administration

## Source implementation

The production `/admin/products`, `/admin/products/new` and `/admin/products/[productId]` routes now use `frontend/components/product-admin-live.tsx`. They load and mutate backend catalog records through the existing authenticated same-origin relay. They do not read demo product data or claim success from browser storage. Older demo components remain as reference/test assets; this phase does not clean them up or convert other admin modules.

New products are created as drafts with an explicit Lost (`lost`) or Emergency (`ice`) type, one decimal PKR `price_per_copy`, title, description and combined-copy limit. After the draft exists, the editor manages available sizes and public images. Every size displays and uses the product price; there is no size-price input. Each operation reports its own confirmed save; the form does not claim that partially completed product setup is fully published.

Drafts can remain incomplete. Publication requires an active QR Stickers category, at least one active physical size, unique active sizes, matching-type approved template bindings and exactly one verified main image. The API, immutable purchase pricing and existing physical/privacy approval rules remain authoritative. A configured template reference alone does not establish type-specific approval. Reviewed binding/QA authority uses the existing print-template backend workflow; this editor does not manufacture approval or bypass its feature/authority gates.

Image upload uses the existing scoped Cloudinary grant and backend asset verification. Main and additional images are server records. Main-image changes use a versioned metadata endpoint; removal unlinks metadata and does not delete remote objects. A completed upload is retained for attachment retry after a verification/service failure. Failed, stale or denied operations preserve form entries and do not display private provider messages. Reload is explicit and asks before discarding changed product details.

## Backend and API changes

- Product request adds `qr_type`; new creation requires it. Legacy edits may retain null and cannot silently change the legacy identity model.
- New `GET /api/v1/admin/products/{product_id}` returns the exact record, variants and images; it does not reconstruct detail from a capped list.
- New `PATCH /api/v1/admin/products/{product_id}/images/{image_id}` changes alt text, ordering and main designation under the product's `If-Match` revision. It cannot rebind image storage or move an image to another product.
- Existing create/update/variant/upload/unlink endpoints retain authenticated role, MFA, idempotency, audit and version checks. The relay forwards validated list pagination and retains same-origin mutation checks, server-held bearer transport and no-store responses.

## Additive migration 0039

`0039_single_qr_catalog` follows `0038_typed_inventory`; it is authored, not applied.

`products.commerce_model` defaults to `legacy_pair`, preserving all existing products. New product creation explicitly uses `single_qr` and disables the legacy `allows_new_pair` path. The model is immutable. A typed product requires a selected type; legacy products are not converted or inferred. Published/referenced type changes are rejected. Phase 4 must extend reference checks to its new logical item tables.

New deferred publication guards cover product, size and image mutations. No direct table privileges are added. A type-specific registry eligibility helper reuses reviewed template/authority checks. Existing order/profile/token rows and frozen purchase snapshots are not rewritten.

Legacy public catalog and quote helpers explicitly select `legacy_pair` products. Consequently, existing customer shopping and checkout retain their original product model, while new typed products cannot accidentally be sold as Lost+Emergency pairs. **New-model customer catalog/checkout admission is deliberately deferred to Phase 4**, including products whose admin lifecycle is published. Publishing in this phase is not an assertion that the new checkout is released.

## Verification boundaries

Backend tests cover selected-type creation, no legacy conversion, matching-type approval, main image, duplicate sizes, stale versions, scoped image updates and missing detail. Browser tests mount the current React components against intercepted synthetic endpoints, exercising server-record reload, price/type payloads, stale edits, image upload/attachment retry, denial and Urdu/mobile layout. A separate VM test executes the actual relay with controlled session/upstream modules, checking authentication, origin, paths, pagination, revision headers and safe failures.

These checks do not prove real PostgreSQL deferred triggers/RLS/MVCC, actual Auth/Next SSR integration, provider uploads or physical print approval. Opt-in isolated migration cases are provided in `backend/tests/integration/test_single_qr_catalog_postgres.py`; no database rehearsal or migration application is performed in this phase. The older integrated catalog browser fixtures target the replaced technical editor and require reconciliation before claiming a fresh full-stack suite pass. Native Urdu/manual accessibility and physical QA remain separate acceptance gates.

Final scoped results: **223 backend checks passed**, 4 PostgreSQL checks skipped and 2 older integrated browser cases deselected. **4 current-component browser scenarios passed**, along with the relay VM checks, TypeScript, scoped Ruff and whitespace checks. English and mobile Urdu screenshots were inspected. Reproducible frontend commands: `npm run test:catalog-admin`, `npm run test:catalog-relay`, `npm run typecheck` from `frontend`.

No environment variables changed, no deployment occurred, and Phase 4 was not started.
