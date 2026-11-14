# Customer portal implementation — 26 October 2026

Status: frontend implementation with real API wiring and isolated integration evidence; **not production end-to-end accepted**. Protected quarantine and backend release gates prevent the full requested customer workflow. No gate, migration, database, production resource, authentication configuration or payment authority was changed.

## Architecture and design

The existing application is Next.js 16 / React 19 / strict TypeScript, App Router, Tailwind plus component CSS, Supabase SSR authentication and server-held bearer requests to FastAPI. No dependencies or separate application were added. `frontend/AGENTS.md` and the installed Next CSS/client-component guidance were read.

The six files in `mock-ui/customer_mock/` were inspected. There are no accompanying asset files. The actual CSS overrides the older notes: espresso `#3D2C2E`, terracotta `#C97C5D`, hover `#B56748`, cream `#FFF1E6`, surface `#FFFDFB`, crimson `#8C1C13`. The scoped portal stylesheet preserves these values, header/shield, sidebar, responsive horizontal navigation, spacing, cards, controls, badges and dialog appearance. Native dialogs add keyboard focus containment and Escape dismissal. The offline-demo badge becomes Customer Portal; logout is real. No prototype JS or synthetic customer records are used in application code.

Visual inspection compared the original mock at 1440px with actual-component screenshots at 1440px and Urdu 390px. Automated checks cover all requested widths in both languages. This is not pixel-perfect acceptance of every screen: real statuses, UUIDs, blocked controls and required forms alter content density. No external font or artwork was introduced.

## Screens and backend mapping

Paths below are relative to `/api/v1`. Existing Supabase session verification, `ownerApi`, same-origin relays, CSRF/origin checks, private caching and idempotency are reused.

| Screen | Real contract | Current classification |
|---|---|---|
| Dashboard | GET `/me/independent-qr?limit=100`, `/me/orders?limit=5`, `/me/finder-messages?status=new&limit=5` | Implemented; independent widget failure states. QR counts explicitly cover at most the first 100 allocated identities, not a fabricated account-wide aggregate. |
| My QR / activation | GET `/me/independent-qr`; POST `/me/independent-qr/activation-intents`, `/me/independent-qr/activations`; PATCH `/{qr_id}/availability`; GET `/{qr_id}/history` under the same prefix | Implemented; backend eligibility and `activation_released` authoritative. Filter applies to the displayed page. Server expiry shown and expired confirmation disabled. One identity remains one logical item. |
| Lost / Emergency profiles | GET `/me/qr/{qr_id}`; GET/PUT `lost-profile`, `ice-profile`, `contact-preferences`; GET/POST/PATCH/DELETE `ice-contacts` | Existing typed editors retained, but these operations are in the protected quarantine. Portal explicitly reports unavailability and does not offer an enabled edit action. No bypass. |
| Catalog/product | GET `/public/products`, `/public/products/{sku}` | Existing validated catalog integrated with portal styling. Type, image, backend prices, sizes and `checkout_available` retained. |
| Cart/checkout | POST `/me/checkout/item-quotes`, `/me/checkout/item-quotes/{quote_id}/confirm`; saved-address reads | Existing single-QR integration reused. Choices only in local storage; no tokens, prices or addresses persisted. Server quote/totals and admission gate authoritative. Existing legacy code and cart storage preserved. |
| Orders | GET `/me/orders`, GET `/me/orders/{order_id}/shipments` | List and shipment integration retained. Payment accessible directly from list and detail fallback. |
| Detailed order/allocation/print/cancellation | GET `/me/orders/{order_id}`, POST `/me/orders/{order_id}/cancel` | Quarantined. No inferred allocation or print state, and no cancellation bypass. Detailed logical-item snapshots cannot be fetched through an alternative privileged endpoint. |
| Payments | GET `/me/orders/{order_id}/payment-instructions`, GET/POST `/me/orders/{order_id}/payment-attempts`, POST `/me/payment-attempts/{attempt_id}/evidence-uploads` and `/evidence-finalize`; signed private PUT | Customer component rebuilt with loading/denial/validation/conflict/rate/network states, response checks, private in-memory grants and retry keys. Evidence submission never verifies settlement. Backend/provider admission still required. |
| Finder inbox | GET list/detail `/me/finder-messages`; PATCH status; DELETE message | Existing server integration retained, pending submits added. Backend statuses `viewed`, `archived`, `flagged`; restoring an archive means `viewed`, not resetting it to `new`. No replies. |
| Addresses | GET/POST `/me/shipping-addresses`; PATCH/DELETE `/{id}` | Existing integration, revision checks and default address retained; deletion now uses the approved-style dialog. |
| Account/privacy | GET/PATCH `/me`; GET `/me/privacy-consents`; POST `/me/account-deletion-requests`; customer `/me/privacy/exports` request/status/grant/download routes | Existing real workflows retained. Reviewed requests are not erasure or export delivery. Provider/reviewer/feature gates remain authoritative. |

## Reconciliation with the mock

- Dashboard no longer requests legacy tag pairs. Navigation leads to independent QR identities. Legacy URLs, activation code and behavior remain unchanged.
- No mock prices, sizes, copy cap, transfer date, reference or fabricated verification. Payment uses `sender_holder_name` (160), `sender_account` (4–80) and private evidence grants.
- Shipping uses `recipient_name` (160), `phone` (16), `address` (500), `city`/`province` (100), `postal_code` (20), defaults and version fields. No invented address label or split address lines.
- Existing Lost editor contract: `item_label` 120, `description` 1000, `reward_text` 200, `return_instructions` 1000, `published`; preferences use E.164 and `wa-public-v1` consent. These are currently quarantined.
- Existing Emergency contract: `display_name` 120, eight ABO/Rh groups, `emergency_instructions` 1000, `medical_notes` 1000 (not mock 2000), `show_medical_notes`, `published`, `ice-public-v1` consent. No separate private identity-label field exists. Contact relationship 60, optional name 120, phone 8–16/E.164, order 0–100, per-contact publication/`ice-contact-v1`; maximum three contacts. These are currently quarantined.
- No analytics, scan counts, invented tracking, ownership transfer, customer payment approval, forced allocation/printing/delivery, instant account deletion or client-generated activation credential.
- New portal, payment, dialog and dashboard strings have English/Urdu coverage. Existing bilingual forms remain; backend product names and opaque IDs are not machine-translated. Full native-language review and legacy export metadata-label translation remain manual acceptance items.

## Exact blockers and limits

1. The unchanged 70-operation list in `lib/api/quarantine-operations.ts` blocks customer profile/detail operations and order detail/cancellation. Completing those positive journeys would require a separately approved security-contract change, expressly outside this task.
2. `activation_released`, catalog `checkout_available`, SQL single-checkout/standalone-owner admission and official bank instruction records remain authoritative. Phase 8 records both SQL gates closed; this task did not inspect or change live gate state. Do not treat an isolated fixture with an open gate as rollout evidence.
3. No global independent-QR count endpoint exists; the dashboard labels bounded counts. Collection DTO lacks profile publication/label fields; the UI does not invent them. Independent history describes lifecycle events, not an invented profile-edit audit.
4. No independent Emergency private label field, finder replies, mark-unread operation, gifting/transfer or instant export/erasure contract is supplied. No replacement was fabricated.
5. The named Single-QR Customer Dashboard Research document was not found in the checked-in file listing. Phase 3–7 handoffs, Phase 8 amendments, backend routes/DTOs and quarantine were used instead; old v1.2 pair requirements were not reintroduced.
6. Genuine authenticated Supabase/PostgreSQL, private storage, settlement, shipment and consent acceptance has not been executed. Only isolated synthetic-auth/SQL tests and read-only source review are claimed. Test-only fixtures are under `tests/`, never application routes.

## Changed files

New application files: `components/customer-dashboard.tsx`, `customer-navigation.tsx`, `customer-dialog.tsx`, `customer-payment.tsx`, `customer-submit.tsx`, `customer-portal.css`; `lib/customer-capabilities.ts`; `app/customer-actions.ts`; `app/(customer)/loading.tsx`; layouts under `app/shop`, `cart`, `checkout`, `payments`.

Modified application files: `components/customer.tsx`, `independent-qr.tsx`, `payments.tsx`, `shipping-addresses.tsx`, `catalog.tsx`, `item-checkout.tsx`; customer dashboard, QR list/detail, order list/detail, inbox detail and settings pages; account, address, export, catalog/product, cart and checkout pages.

Test additions/updates: customer portal Playwright config/spec; customer backend Python fixture and Node relay/HTTP runner; dashboard and order server-render tests; real quarantine loader; existing independent QR, checkout, address and browser bundling harnesses. Old harnesses were corrected to execute the unchanged quarantine and complete existing response fixtures.

Pre-existing edits to `backend/scripts/run_admin_read_acceptance.py`, `frontend/scripts/configure-development-auth.py`, `frontend/scripts/staff-login-acceptance.cjs` and the untracked mock directory were preserved.

## Validation and remaining acceptance

Executed evidence is recorded below after the final checks. No lint command/configuration is provided by the existing package.

| Check | Actual result |
|---|---|
| `npm run typecheck` | Passed, including final changed source. |
| `npm run build` | Passed after cleaning only generated `.next`. The interrupted earlier build left invalid null-byte JSON; clean rebuild succeeded. Existing multiple-lockfile/root warning remains. |
| `npx playwright test --config playwright.customer-portal.config.ts` | Final run: **29 passed**, 40.0s. Includes all seven requested widths in English/Urdu, expired intent, disabled release, quarantine, address CRUD/conflicts, multi-size single identity, checkout retries, server totals and evidence retry. Actual components with intercepted browser responses. |
| Focused backend pytest regression | **270 passed**, 111.57s: standalone owner, item checkout, shipping addresses, messages, checkout validation, copy pricing, verified allocation, release gates, privacy navigation and account lifecycle. Offline/isolated tests; no live database writes. |
| `node scripts/test-customer-backend.cjs` | Passed: real Next relay → loopback HTTP → actual FastAPI ownership routes and checkout DTO validation. Synthetic auth and SQL dependencies, not PostgreSQL or provider acceptance. |
| `node scripts/test-customer-dashboard.cjs` | Passed: server component endpoint/token forwarding, independent counts, payment state, partial failure isolation. |
| `node scripts/test-customer-orders-render.cjs` | Passed: three server render cases, pagination, quarantined detail and safe fallback. |
| `node scripts/test-independent-qr.cjs` | Passed: closed payloads, denied auth/origin, bounds, idempotency transport, canary rejection. |
| `node scripts/test-item-checkout.cjs` | Passed: merge/separation, stripped client price fields, item/copy counts, auth/origin, retry key; legacy quote quarantine remains enforced. |
| `node scripts/test-shipping-address-relay.cjs` | Passed: auth/origin/validation, revisions, errors, 204 and private headers. |
| `node scripts/test-shipping-addresses.cjs` | Passed: synthetic CRUD/conflict/default address/reset/private-storage/Urdu checks. Its legacy checkout portion is a component fixture, not authorization to use the quarantined legacy endpoint. |
| `git diff --check` | Passed; only Git line-ending notices. Protected backend and quarantine files have no diff. |

An earlier browser run passed 29/29. A subsequent run passed 27/29 with two blank Urdu harness mounts; both passed on targeted rerun. Render-error capture and an explicit shell mount wait were added; final full-run outcome is recorded below. These intermittent harness failures are disclosed, not counted as product acceptance. Initial outdated relay harness import failures were repaired by loading the real quarantine policy; an incomplete old quote fixture and obsolete native-confirm expectation were corrected.

Manual release acceptance still needs: approved signed-in customer environment; real session expiry and cross-owner denial; all released positive journeys with PostgreSQL guards; private upload/finalize and export delivery; payment settlement → allocation → print → shipment → activation; exact-copy identity invariants under concurrency; consent publication/revocation when quarantine is legitimately lifted; screen reader/native Urdu review; all screens at every requested width; real-device dialog/focus/back-navigation and reload recovery. No production writes were attempted.
