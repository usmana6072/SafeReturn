# Phase 7 — independent ownership and activation

Source implementation only. Additive migration **0043_standalone_activation is authored, not applied**. Read-only Alembic graph discovery reports this revision as the source head; the installed database revision was not inspected. Customer checkout release remains disabled. The new protected `standalone_owner_release` row defaults to false and has no API/worker write grants. No environment variables changed or deployment occurred. Stop before Phase 8.

## Owner decision recorded

The purchaser must sign in with a verified account and activate only after confirmed delivery. Gifting/transfers and concealed activation credentials are deferred. A public QR token, QR ID or caller-supplied owner ID is never ownership proof. The existing legacy pair activation and concealed-credential contracts remain unchanged.

## Implemented source

- The permanent `order_item_qr_allocations` claim supplies entitlement. Both intent creation and confirmation check the purchaser, live account/session, paid settlement, exact verified amount/currency, delivered order, delivered shipment with packed item membership, QR/state validity, financial fences, cancellation requests and template holds/withdrawals.
- An intent belongs to one logical item, purchaser and authenticated session. It expires after five minutes and freezes the standalone state revision. Confirmation locks the order, QR, state and intent; it rechecks entitlement and consumes only that intent. No sibling type is activated. Default Lost/Emergency profiles are unpublished, with existing consent requirements retained for later publication.
- Permanent actor-scoped request receipts enforce idempotency and reject changed requests under the same key. Ownership/public status, intent consumption, history, audit and receipt commit together. A unique index permits only one activation event per QR. Tables have RLS and no direct API/worker access; helpers expose only the required operations.
- Independent owner disable/resume uses an explicit confirmation, state revision and idempotency key. It cannot restore an admin-suspended or revoked QR. Disable does not mutate its sibling or clear existing profile consent. Resume rechecks the release and financial fence. History is independently scoped and bounded by revision.
- Existing QR-owner/profile guards now recognize active standalone ownership alongside legacy pair ownership. `/me/qr` includes owned standalone identities with null pair fields; the existing profile editor returns to the independent collection for these identities. Purchase size/copy links come from frozen logical items and sizes, never a new allocation.
- Public projection preserves the installed consent/field allowlist and legacy URLs. Standalone reads/actions remain behind the owner release gate; restricted owner accounts expose no profile/contact details. The existing ICE/contact and Lost finder-message paths gain standalone checks. Finder messages resolve the standalone owner and use the existing encrypted message/location, idempotency, recipient and notification-outbox machinery.
- Privacy exports add safe own-record categories for standalone identities/history and logical item/size snapshots. Existing export lease/reviewer checks and third-party/medical/contact omissions remain. No public token, session ID or activation credential enters the export. Protected financial/ownership/history records are preserved; deletion/cleanup remains deferred.
- Assigned support staff with a live MFA session can look up safe standalone status metadata for an assigned case's linked order. They receive no public token, owner contact data, claim credential or ownership-changing action. Reads are audited.
- Printing/fulfillment predicates now recognize an activated standalone owner matching the permanent purchaser, so activation does not itself invalidate historical shipment eligibility. Phase 6's post-shipment reprint restriction remains.

## APIs and screens

| API | Purpose |
|---|---|
| `GET /me/independent-qr?limit=&after=` | Purchaser's allocated identities, safe state/revision, server-calculated eligibility; UUID keyset pagination. |
| `POST /me/independent-qr/activation-intents` | Closed body `{logical_item_id}`. No token or credential field. |
| `POST /me/independent-qr/activations` | `{intent_id, confirmed:true}` and `Idempotency-Key`. |
| `GET /me/independent-qr/{qr_id}/history` | Owner history with `limit` and `after_revision`. |
| `PATCH /me/independent-qr/{qr_id}/availability` | `{public_status, expected_revision, confirmed:true}` and idempotency key. |
| `GET /admin/support-cases/{case_id}/independent-qr` | Assigned support/MFA-only safe status discovery for the case's order. |

Mutation request bodies are bounded to 4 KiB. Validation does not echo submitted input. Existing `/me/qr`, profile, public scan, reveal/contact and finder endpoints keep their paths; legacy pair endpoints keep their original shape.

Frontend: the authenticated `/independent-qr` page, guarded same-origin `/independent-qr/api` relay, and `components/independent-qr.tsx`. The relay restricts targets, bounds upstream bodies, validates closed representations and strips upstream errors. Intent and retry keys stay in component memory. UI supports explicit per-identity activation/availability review, history pagination, denied-refresh clearing, English and Urdu/RTL. Existing My QR, account navigation, activation guidance and profile return links connect to the new screen.

## Validation and limits

- The scoped regression run passed **400 backend tests**, with **9 opt-in PostgreSQL cases skipped**. After the final request-size guard, all **22 focused owner tests** passed, including three added HTTP authorization/size/non-echo checks; these overlap the earlier regression run.
- Three actual-component Phase 7 browser scenarios passed: one identity/sibling isolation and uncertain retry, explicit availability review/denial clearing, and unreleased Urdu mobile layout. All three Phase 6 print/packing scenarios also passed after the shared browser harness was corrected to transpile `.ts` and `.tsx` using their actual filenames.
- Actual-code contract/relay VM checks, TypeScript, scoped Ruff and whitespace checks passed. The Urdu mobile screenshot was inspected. Browser responses/Auth are synthetic, not integrated provider or Next SSR evidence.
- Authored opt-in PostgreSQL cases cover delivered eligibility, sibling independence, replay, competing intents, changed fulfillment, different-account denial, receipt/audit rollback, expired intents, account restrictions, table ACL denial and restricted public projection. **None was executed.** No PostgreSQL function compilation, RLS, locking/MVCC, upgrade preservation or real race result is claimed.

Phase 8 must rehearse the entire pending chain on a separately approved disposable populated target, including legacy activation/profiles/public URLs/orders and frozen reprints. It must exercise real account invalidation, financial/cancellation/template races, consent and contact reveal, finder notifications, privacy export paging, lease/provider behavior and integrated browser/Auth flows. Source-level in-place function extensions deliberately abort if installed definitions differ and need particular migration review.

Before release, review physical custody/packing acceptance and the remaining typed cancellation/refund and post-shipment replacement/repacking gaps recorded in Phases 5–6. No customer admission or standalone owner/public gate may be enabled on the strength of these offline checks. Gifting, transfers, concealed credentials, replacement QR identities and destructive cleanup remain out of scope.
