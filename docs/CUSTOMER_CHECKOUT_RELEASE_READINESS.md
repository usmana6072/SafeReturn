# Customer checkout readiness — 2026-10-26

## Runtime admission and percentage pricing follow-up

After database admission was enabled, actual quote requests returned 503 because the API runtime checkout switch defaulted off and shipping/tax settings were absent. Earlier catalog availability checks missed these runtime dependencies. The independent catalog now includes runtime blockers; quote/confirm return specific safe error codes instead of a generic configuration failure.

The user explicitly specified PKR 100 delivery and 5% tax after adding delivery. Added server-only `single_qr_checkout_enabled` and `single_qr_checkout_tax_percent` settings. The ignored development `.env` now enables independent checkout, sets delivery to `100.00` and percentage tax to `5`. The shared legacy checkout flag remains false and its fixed-tax behavior is unchanged. Independent percentage tax takes precedence over the existing fixed-tax option when configured; otherwise existing fixed-tax behavior remains supported. Decimal calculations round tax half-up to two places. Confirmation recalculates current charges and rejects a stale quote before writing an order. No schema, migration or quarantine changes were needed.

Verification: 112 scoped backend tests and 13 checkout browser tests passed, as did the production build/typecheck and local relay/FastAPI integration check. An actual development SELECT-only catalog/template probe (always rolled back; SELECT FOR SHARE prevents PostgreSQL READ ONLY mode) and in-memory encryption roundtrip passed. Three PKR 60 copies with no separate identity produce one identity, subtotal 180.00, delivery 100.00, tax 14.00 and total 294.00. No quote/order/payment fixture was inserted. Local API 8031 and web 3032 were restarted. An authenticated end-to-end order submission has not been executed by the agent.

## Approved development checkout enablement

On 2026-10-26, after the preparation and tests recorded below, the user explicitly approved publication and checkout enablement and supplied their approver account. The existing verified account has active finance and operations roles. A guarded transaction in development project `fhuxryfkfrvycsojkzvq` committed at 17:46:15 UTC (22:46:15 Asia/Karachi):

- Inserted approved, active payment instruction version `checkout-20261026-v1` using the exact reviewed draft. `approved_by` references the supplied existing user; `approved_at` records the application of this approval.
- Changed only the singleton `single_checkout_release.enabled` from false to true.

The transaction verified the target project/TLS, approver, draft SHA-256, absence of active/conflicting instruction versions, disabled prior release state and published product eligibility. It locked both configuration tables, applied both writes atomically, and checked catalog availability before commit. The local execution receipt is `tmp/checkout-release-receipt.json`; the original reviewed draft remains preserved. No separate database audit event is claimed.

Post-commit live browser verification passed: public API reports `checkout_available=true` and no blockers, public catalog does not contain payment destination details, and shop Order now → product size selection → Add to cart → cart checkout link works. No real order or payment was created for this check.

This is **development checkout admission only**, not full lifecycle release. Activation remains disabled, the 70-operation quarantine and finance/fulfillment restrictions remain intact, and no production settings, migrations, auth roles, settlement authority, allocation rules or legacy behavior changed. End-to-end authenticated purchase/payment/fulfillment acceptance remains outstanding.

The following sections preserve the pre-approval findings and preparation history; statements describing an unpublished draft or disabled checkout refer to that earlier state.

## Exact blockers and authority

- Development target: Supabase project `fhuxryfkfrvycsojkzvq`. The pinned read-only audit in `backend/scripts/check_customer_flow_readiness.py` reported revision `0050_public_catalog_browsing`, `single_checkout_release.enabled=false`, zero active payment instructions, and `standalone_owner_release.enabled=false`.
- Published `mobile qr` / SKU `mobile1`: one eligible active size, product price PKR 60.00, maximum combined copies 10. Catalog visibility is not purchase authorization. Migration 0050 intentionally permits browsing while purchase admission stays closed.
- `backend/alembic/versions/0040_item_checkout.sql` defines the singleton release row and `checkout_payment_instructions`. Runtime API, worker, anon and authenticated roles cannot edit either table. `sr_single_checkout_enabled()` and `sr_checkout_payment_instructions()` are narrow read helpers. Quote/confirmation also enforce admission in `backend/app/api/v1/item_checkout.py`.
- No existing administrative instruction-management API or settings editor was found. `docs/ITEM_CHECKOUT_PHASE4.md` explicitly leaves approval values and who may edit/activate them to rollout decisions. An admin frontend cannot safely implement this absent a backend management contract. No new grants, endpoint, migration, or privileged browser access were added.
- The frontend 70-operation quarantine still blocks finance reviews (`POST /admin/payment-attempts/{attempt_id}/reviews`), allocation retry, print job creation/QA and other protected operations. Enabling customer checkout alone would not establish an operational settlement-to-fulfillment workflow. Resolving quarantine is outside this task's authority.

## Safe code changes

The existing public catalog routes now return `checkout_unavailable_reasons` for independent products, using only the two existing read helpers. Only booleans/reason codes are exposed, not payment details or approval identity. The additional check can restrict availability but cannot make an ineligible catalog product purchasable. Legacy products retain their existing behavior. Responses remain uncached.

Homepage/shop cards, product details and the independent cart share availability logic and English/Urdu explanations. Independent products require explicit `checkout_available=true`; missing availability fails closed. Existing real quote/confirm APIs and payment flow remain in use. Fractional configurator quantities are rejected rather than silently rounded. Checkout errors distinguish release, instructions, session, permission and input failures. Approved payment instruction line breaks are preserved for readable payment options.

## Payment configuration prepared, not published

The user supplied Easypaisa account details and confirmed the same phone number is a registered Raast ID linked to ABL, with the same recipient title. These are two alternative routes, not a claim that Raast settles into Easypaisa. The bilingual draft explicitly labels the destinations, requires checking the recipient name and exact server order total, says to pay only once, suggests including the order number where the payment app supports notes, and explains that evidence submission does not verify settlement.

Real values are stored only in ignored local `tmp/payment-instructions.draft.json`, not application source or a public page. `bank_name` describes the account-number route; the existing bilingual instruction fields explain the ABL Raast route. There are no invented database fields for payment method, IBAN, Raast bank or payment reference.

Actual schema requirements:

| Field | Constraint |
| --- | --- |
| version | 1–80 characters, primary key |
| bank_name / account_title | 1–160 characters each |
| account_number / raast_id | 4–80 characters each; both required |
| instructions_en / instructions_ur | 1–2000 characters each |
| approved_by | genuine existing `auth.users.id`, required foreign key |
| approved_at | genuine approval timestamp, required |
| active | boolean; at most one active record |

Draft string lengths were checked against these constraints. Proposed version is `checkout-20261026-v1`; uniqueness must be checked before use. `active=false`, `approved_by=null`, `approved_at=null` deliberately make this an unapproved draft, not an insert-ready record. No user UUID or approval time was fabricated. PKR is supplied by the existing helper, not a configurable table column.

## Proposed release sequence for later review

1. Complete isolated PostgreSQL and real Auth/private-storage acceptance with separately authorized fixture writes. Offline test results do not establish live transaction, settlement, RLS, stock, provider or audit readiness.
2. Establish a usable authorized finance verification/fulfillment path without bypassing the quarantine; verify typed inventory availability, print policy/origin/QA, shipment delivery eligibility and separately approved activation readiness. The observed manual render policy origin is `http://127.0.0.1:3100`; its suitability for intended scan/print use must be reviewed. Quotes do not reserve stock.
3. Review the exact local draft text and destination values. Obtain explicit approval, the genuine approving user's UUID and recorded approval timestamp, and an authorized operator/change-record procedure. The schema records attribution but supplies no configuration mutation API or automatic configuration audit writer; do not claim an audit event exists.
4. Before any privileged operation, repeat pinned read-only checks, show exact old/new rows, environment, operator, tests, rollback and effects. Proposed configuration is one versioned approved payment instruction record, active only upon explicit authorization. Any existing active record must be accounted for atomically. Do not silently overwrite it. Existing orders retain frozen instructions; changed instructions invalidate open quotes.
5. Only after lifecycle prerequisites are satisfied, seek separate explicit authorization to change `public.single_checkout_release.enabled` from false to true for the singleton row in the development project. This enables quote/confirmation admission, not settlement, allocation or activation authorization. Turning it off later blocks new admissions; it does not undo existing orders or obligations.

No executable release SQL is provided while approval attribution and lifecycle readiness remain unresolved. No production changes, real payment, database fixture creation, migration or release write was performed.

## Validation

- 267 scoped backend tests passed: catalog availability, item checkout, catalog DTOs, pricing, verified allocation, typed fulfillment, payment storage/reads, authentication, release gates and standalone ownership. These use isolated mocks, not live database writes.
- Frontend typecheck, catalog rendering and checkout relay/cart contract checks passed.
- Production build and final TypeScript check passed. No lint command is configured in the frontend package.
- 34 browser tests passed after the build completed (47.8 seconds), covering English/Urdu at 320, 375, 390, 430, 768, 1024 and 1440 pixels, checkout, payment evidence retry, address operations, activation and error states. An earlier concurrent build/browser run had 32 passes and two missing-generated-CSS failures; the complete sequential rerun passed.
- `node scripts/test-customer-backend.cjs` passed: real Next relay to local FastAPI HTTP with synthetic Auth/SQL; no live database writes. Catalog renders (six cases) and item-cart/checkout-relay contract checks passed.
- Restarted local API on 8031 and customer web on 3032. Read-only Playwright smoke verified the actual development catalog returns both blockers and both `/shop` and `/shop/mobile1` display them with disabled order buttons. No purchase request was submitted.
- `git diff --check` passed; existing CRLF normalization notices only.
- Live positive checkout, bank settlement, private storage and complete delivered-order activation remain manual acceptance prerequisites. Passing mocked tests is not release approval.

## Files changed in this readiness task

`backend/app/api/v1/catalog.py`; `backend/tests/test_catalog_checkout_availability.py`; `frontend/lib/catalog.ts`; new `frontend/lib/checkout-availability.ts`; `frontend/components/catalog.tsx`, `checkout.tsx`, `item-checkout.tsx`; `frontend/scripts/test-catalog-page-render.cjs`; `frontend/tests/item-checkout.spec.ts`; this report; ignored local `tmp/payment-instructions.draft.json`. Earlier customer-portal changes and unrelated pre-existing edits remain separate in the working tree. No migration or quarantine file was modified.
