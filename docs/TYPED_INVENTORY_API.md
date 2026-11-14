# Phase 2: typed QR inventory API

This source implementation follows migration `0037_independent_qr_foundation` with additive `0038_typed_inventory`. No migrations have been applied by this work. Customer checkout, ownership, activation, public scanning and printing continue using their legacy contracts. Standalone identities are inventory only until the later plan phases are implemented.

## Authorization and transport

All endpoints below have `/api/v1` prefix. They require an authenticated, email-verified account with verified MFA and an explicit active **operations** role. Finance, support, security_admin and superadmin alone do not inherit this authority. The PostgreSQL helpers recheck the live account/session and role, including replay after a lock wait. Tables receive no new runtime write grants; only two narrow security-definer entrypoints are executable by `safereturn_api`.

The backend uses bearer authentication. Phase 3 will connect the redesigned screens through existing same-origin server relays; no new browser token transport or cookie-authenticated backend endpoint is introduced here. Responses use `private, no-store`.

## Generation

`POST /admin/qr-inventory/batches`

Header: `Idempotency-Key` — exactly one ASCII key, 8–160 characters (`A-Z a-z 0-9 . _ : -`). Unknown request fields and query parameters are rejected.

```json
{
  "batch_label": "LOST-2026-001",
  "qr_type": "lost",
  "quantity": 100,
  "ecc_level": "Q"
}
```

- `qr_type` is `lost` or `ice`. Emergency is the UI label for stored `ice`.
- `quantity` is a strict integer from 1 to 1000, excluding booleans and strings.
- Batch label is 3–40 ASCII letters/digits/dots/underscores/hyphens, starting with a letter or digit; it is globally unique across legacy and standalone batches.
- ECC is `M` or `Q`, default `Q`. Physical size/material/template is determined during later product/print work, not identity generation.

The 201 receipt contains `batch_id`, `batch_label`, `qr_type`, `generated_quantity`, `status: generated` and `created_at`. It contains no public tokens, ownership credentials, printer artifacts, private profile data or owner IDs.

Generation creates exactly N QR rows and N standalone state rows, without pairs, sibling identities, profiles or activation credentials. Public tokens use the existing cryptographic generator; serials and tokens retain global uniqueness. Public standalone scan admission remains closed by Phase 1.

The transaction includes batch, identities, state, immutable receipt and audit. Same actor/key and normalized body replays the original receipt without generating additional stock. Changed body returns `409 IDEMPOTENCY_KEY_REUSED`; duplicate label returns `409 BATCH_LABEL_CONFLICT`. A uniqueness collision returns `409 GENERATION_CONFLICT`, after savepoint rollback. Replaying after a role/session/MFA loss is denied. Database commit failure rolls back the transaction before the protected response is sent.

## Metadata queries

| Method/path | Filters/result |
|---|---|
| `GET /admin/qr-inventory/batches` | Optional `qr_type`, exact `batch_label`, batch `status`, `limit` (1–100, default 20), `cursor`. |
| `GET /admin/qr-inventory/batches/{batch_id}` | Standalone batch metadata and requested/actual generated quantities; unknown or legacy ID returns 404. |
| `GET /admin/qr-inventory/codes` | Optional `qr_type`, `batch_id`, `inventory_status`, `ownership_status`, `limit`, `cursor`. |
| `GET /admin/qr-inventory/codes/{qr_id}` | Standalone QR metadata; unknown or legacy ID returns 404. |
| `GET /admin/qr-inventory/summary` | Optional `qr_type`; separate type counters, including zeros for empty stock. |

Pages include `as_of`, `items`, and `next_cursor`. Ordering is descending creation time and UUID, with bounded keyset pagination and one internal lookahead row. Cursors are positions, not authorization or a frozen snapshot; changing stock may change subsequent results. Unknown list/summary query fields are rejected.

QR metadata: `qr_id`, `batch_id`, `batch_label`, `qr_type`, `serial_number`, `public_status`, `inventory_status`, `ownership_status`, `row_version`, `created_at`, `allocatable`. No token or owner ID is projected.

Summary counters: `total`, raw-state `available`, `allocated`, `retired`, and `allocatable`, separately for Lost and Emergency. `allocatable` currently means an inventory candidate: available/unclaimed/unowned/current/unactivated QR in a generated standalone batch. It is **not** verified payment, ownership entitlement, physical QA, print readiness or shipment authorization. Actual paid allocation and last-identity contention tests belong to Phase 5.

Existing `/admin/qr-batches`, pair detail and pair stock contracts remain available. Legacy batch list/detail/last-batch projections exclude standalone batches using a JSON row predicate that also works before the new columns exist. No legacy customer router or historical snapshot is rewritten by Phase 2.

## Verification and remaining gates

Synthetic tests exercise HTTP validation, authorization boundaries, secret-free response shapes, helper arguments, metadata filters, pagination, conflict mapping, savepoint rollback and the existing pair inventory paths. They do not execute PL/pgSQL or prove PostgreSQL locks/RLS/commit behavior.

Opt-in PostgreSQL tests live in `backend/tests/integration/test_typed_inventory_postgres.py`. They cover actual concurrent same-key generation, label contention, changed-body replay, global token/state counts, no sibling pairs, cross-type/legacy isolation, direct-table denial, live authority, audit failure rollback, commit-time quantity checks and legacy token preservation. They are skipped unless an owner explicitly configures an isolated rehearsal target and enables the test. The existing harness first verifies the installed baseline (historical default 0021) and uses UUID-isolated schemas/NOLOGIN roles. Later installed revisions require reconciling its older table-count assumptions; do not bypass that guard.

No PostgreSQL rehearsal, environment change, migration application, deployment, or Phase 3 frontend integration is performed in this step.
