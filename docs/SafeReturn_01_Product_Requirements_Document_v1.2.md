# SafeReturn — Product Requirements Document (PRD) v1.2

**Document ID:** SR-PRD-001  
**Revision:** 1.2 — founder-directed implementation baseline  
**Date:** 12 October 2026  
**Market:** Lahore, Pakistan pilot  
**Status:** v1.2 product requirements proposed for implementation review; production/security approvals still required  
**Supersedes:** Specific conflicting clauses of the v1.1 amendment reproduced in Part B below. All unaffected v1.1 requirements remain operative.  
**Next documents:** Technical Design v1.2, then Database Design v1.2, API Contract v1.2, AI Agent Instructions v1.2, Implementation Plan v1.2, Security v1.2, Tests v1.2, Deployment v1.2, Physical SOP v1.2, UI/UX v1.2.

> **Document-control rule:** Part A (this v1.2 amendment) governs over any conflicting language in the archived Part B (v1.1). It is not acceptable to implement both a superseded rule and its replacement. Part B is retained intact for traceability. Document 01 is the product-level contract; detailed schema, endpoint names, job scheduling and vendor adapters will be specified in subsequent v1.2 documents.

---

# PART A — v1.2 APPROVED PRODUCT DIRECTION AND REQUIREMENT AMENDMENT

## A1. Executive product decision summary

SafeReturn is a bilingual (English/Urdu) QR-enabled lost-item recovery and emergency information service. A **single sellable, ownable and activatable QR pair** always has **one Pair ID**, **two unique public QR tokens**, **one Lost Item identity (Tag A)**, **one Emergency/ICE identity (Tag B)** and **one protected pair-level activation entitlement/credential**. Customers may purchase **different physical print sizes and different numbers of printed copies** of those two existing QR identities, without creating extra Pair IDs. A print file contains all ordered copies, arranged for cutting, so fulfillment never has to manually duplicate labels.

An unactivated QR scan should display a clear **Activate QR** action. After sign-in, the originally scanned QR is remembered, the purchaser's entitlement is verified, and the same pair is activated without a second scan. A scan token alone is never proof of ownership.

Checkout uses an explicit payment-provider abstraction. In the Lahore pilot, the customer supplies manual bank/Raast sender details and optional payment screenshot; a finance admin independently verifies settlement. The provider design must permit a future automated verification integration *without changing customer order IDs, inventory ownership, QR allocation, or fulfillment contracts*. Google Sheets is reporting/synchronization only; Supabase PostgreSQL remains authoritative. Private payment evidence and optimized printable PDFs use Supabase private object storage; Cloudinary remains available for public marketing and product media. All temporary objects have controlled deletion after approved retention periods; essential transactional records survive.

### A1.1 Explicit decisions versus still-unset commercial values

| Area | v1.2 direction | Commercial/security value still to finalize |
|---|---|---|
| QR identity | 1 pair = exactly 2 distinct public QR tokens | None; core invariant |
| Copies | Quantities are per tag type × size; repeated copies reuse same URL | Final allowed sizes and per-size pricing |
| Minimum | Each new pair order contains >=1 Lost and >=1 ICE physical copy | Special replacement/add-on sales deferred |
| Reservation | Time-limited, atomic reservation at checkout; final allocation after confirmed payment | Hold duration, delayed-transfer exception window |
| Activation | Scan→activate prompt→auth→verified entitlement→activate same remembered pair | Auth/session security configuration; gift-handling policy |
| Screenshot | Temporary manual-payment evidence only, never automatic verification | Retention/legal dispute policy |
| Future payments | Replaceable provider adapter with normalized states/webhook idempotency | Provider and integration date undecided |
| Files | Supabase private PDFs/evidence; Cloudinary for public visuals | Provider limits and storage cost validation |
| Deletion | Print PDF after delivery + approved short grace; proof after dispute window | Candidate PDF grace 7 days, pending approval; evidence period undecided |
| Printing | Logo center subject to printed scan QA and QR integrity | Approved logo artwork, QR dimensions, substrate/printer |
| Google Sheets | Finance audit/report mirror, asynchronously synchronized | Spreadsheet ID, service-account permissions, column access |

**Important:** Price figures and sample sizes in earlier design discussions were illustrations, not approved rates or SKU specifications. Future implementation must read active server-configured catalog data, not hard-code illustrative examples.

## A2. Product entities and terminology

- **Pair / kit identity:** The unique account-managed digital asset; `pair_id` and `pair_reference` designate the kit, not physical copy count.
- **Tag A — Lost:** One permanent public URL per current Lost QR identity.
- **Tag B — ICE:** One different permanent public URL per current Emergency QR identity.
- **Printed copy:** A physical repetition of the corresponding tag's same public URL and graphic. Printed copies have *no independent online identity or activation* in P0.
- **Print variant:** A defined paper/adhesive/substrate/size option, with permitted minimum dimensions and price.
- **Order pair unit:** One new pair allocated to a single customer order; print lines for that pair may have several tag×size quantities.
- **Reservation:** Time-limited, exclusive lock/claim on an available qualified unsold pair before confirmed payment.
- **Allocation:** Permanent connection between paid order and its pair. No other active order may own it.
- **Payment attempt/submission:** Provider-independent record of an attempted payment; manual proof is not confirmation.
- **Print job/artifact:** Versioned, reproducible order-specific production layout and temporary private file, with secure access and lifecycle.

Example: An order for **3 Lost copies and 2 ICE copies**, even across different sizes, allocates **one Pair ID** and contains **two unique QR destinations**, but **five printed stickers**. The five labels may be spread across one or more PDF pages. If the customer independently buys two distinct kits, there are two Pair IDs; each kit has its own two QR tokens.

## A3. Requirements: QR generation, centered branding and inventory

| ID | Priority | Requirement |
|---|---|---|
| FR-118 | P0 | Admin can request creation of N *complete* new QR pairs (not N unrelated single tags); validate N, permissions and batch limits. |
| FR-119 | P0 | Generation creates one secure Pair ID/reference and distinct high-entropy public URL tokens for Lost and ICE, with secure activation verifier and batch traceability. |
| FR-120 | P0 | Public artwork of each QR includes the approved SafeReturn logo centered over a deliberately bounded backing area without obscuring quiet zone or breaking scan reliability. |
| FR-121 | P0 | Branded QR art uses the verified final SafeReturn domain and never embeds raw activation secrets, user data or payment data. |
| FR-122 | P0 | Logo, ECC level, symbol density, printed size, contrast, laminating/substrate, and device scan tests must be validated together; failure means print QA hold. |
| FR-123 | P0 | Inventory is tracked at the complete-pair level with explicit availability, reserved, allocated, QA/revoked/exception eligibility; never treat extra copies as extra inventory pairs. |
| FR-124 | P0 | Admin inventory screen shows available, reserved, sold/allocated, held, revoked and batch counts and supports authorized Create New QRs. |
| FR-125 | P0 | A pair cannot be reserved or allocated twice, including with parallel checkouts, retries, failed background jobs or admin actions. |
| FR-126 | P0 | The system must support a low-stock alert based on an admin-configured threshold; generation remains an explicit authorized admin action for P0. |
| FR-127 | P0 | Replacement/revoked QR identities maintain historical audit links; printing uses only eligible current tokens. |

**Print branding guidance:** Preserve the existing PHY-005/006 minimum printed QR dimensions and four-module quiet zone. The v1.1 default ECC M/Q is a starting policy, *not permission to place a logo at any size without testing*. A QR/logo combination unable to pass scan QA is rejected or artwork adjusted; physically usable ECC and size are set in the future Technical/Physical specifications. Logo imagery is not cryptographic provenance: validation relies on canonical domain, token and authoritative server record.

### A3.1 Inventory status acceptance

AC-071: Creating N pairs yields exactly N parent pairs, N current Lost tags and N current ICE tags, without token collisions or partial batches.  
AC-072: Buyer adding 3 Lost plus 2 ICE copies to *one kit* does not create five QR records or five pairs.  
AC-073: Two simultaneous orders cannot receive the same reserved/allocated pair.  
AC-074: Admin low-stock warning and creation do not expose tokens or activation credentials to an unauthorized operator.  
AC-075: Logo-bearing artwork meets agreed physical QA on selected sizes before release.

## A4. Requirements: Scan-led activation, without a second scan

| ID | Priority | Requirement |
|---|---|---|
| FR-128 | P0 | Scanning a valid current **unactivated** Lost or ICE URL renders a friendly bilingual preactivation page, not an opaque error. |
| FR-129 | P0 | Page shows the tag's unactivated state and **Activate QR** CTA; it must not expose private owner, purchaser, or activation information. |
| FR-130 | P0 | Clicking Activate QR when unauthenticated routes to login/sign-up while preserving **only a safe, opaque pending scan reference** (server-side short-lived state or signed, bounded return intent). |
| FR-131 | P0 | After authenticated, verified login, show the remembered kit identity and a final **Activate QR Pair** confirmation action—no rescan and no manual retyping of its public token. |
| FR-132 | P0 | The backend verifies order entitlement for purchased pairs; for gifts/independent distribution, the concealed single-use pair activation credential or approved claim mechanism remains required. |
| FR-133 | P0 | Possession of a public QR URL, Pair ID, logo, or pending scan reference alone never authorizes claiming a pair. |
| FR-134 | P0 | One successful activation atomically assigns and activates both current tags under the same verified owner; activation of one tag alone is impossible. |
| FR-135 | P0 | After activation, the original Lost and ICE URLs route to their respective intended public experiences, subject to separately configured privacy/publication controls. |
| FR-136 | P0 | Invalid/revoked/disputed/already-owned scanned tokens show safe, context-appropriate states without leaking order or owner information; authenticated rightful owner can open their management screen. |
| FR-137 | P0 | Activation intent is time-limited, CSRF/state-protected and consumed/rotated on successful claim; support expiry and a clear recovery flow without creating unauthorized entitlement. |

**Journey:** `Scan /q/{token}` → valid unactivated page → **Activate QR** → authenticated session (login/register/email verification as required) → resolve signed pending scan intent → entitlement check → confirmation → atomic pair activation → pair setup dashboard. Authentication must not append private secrets into query strings, analytics or logs.

**Compatibility/supersession:** v1.1 §12.2's requirement that *every purchaser* manually enters Pair ID and activation secret is superseded **only for verified first-party purchased orders**. The original concealed activation credential remains available as the separate secure proof for gift/offline claims or recovery, under approved rules. Other atomicity, lockout, revocation, audit and single-use security clauses remain effective.

AC-076: Unactivated valid QR shows activation CTA in English/Urdu.  
AC-077: Login/sign-up and redirects return to same pair context even if scanning ICE rather than Lost.  
AC-078: Purchased eligible pair activates without another scan or exposed activation secret.  
AC-079: An unrelated logged-in user scanning the public URL cannot claim the pair.  
AC-080: Failed or concurrent activation never results in separate Lost/ICE owners; idempotent repeat is safe.

## A5. Requirements: product customization, quotes and checkout

| ID | Priority | Requirement |
|---|---|---|
| FR-138 | P0 | Customer can select an allowed size and independent integer copy quantities for **both** Lost and ICE tags for a newly purchased pair. |
| FR-139 | P0 | Customer can mix available sizes within the same tag type and select different Lost and ICE quantities. |
| FR-140 | P0 | Every new-pair order requires >=1 Lost copy and >=1 ICE copy; quantities cannot be negative, fractional, or above active per-order limits. |
| FR-141 | P0 | Copy quantities are print fulfillment units. They do not generate extra public QR IDs or activation entitlements. |
| FR-142 | P0 | Pricing is determined server-side from SKU/variant, print quantity, approved promotions/taxes, delivery charges and optional base-pair fee; return itemized quote with expiry and currency PKR. |
| FR-143 | P0 | Review screen clearly shows Lost by size/count, ICE by size/count, subtotal, fees, total, destination address and saved contact information, with an opportunity to edit. |
| FR-144 | P0 | Address/contact details and final quoted pricing are snapshotted into the order on confirmation so later account changes do not silently alter the historical order. |
| FR-145 | P0 | Customer must be authenticated/verified before creating a binding order; abandoned selections can persist safely as a non-binding cart. |
| FR-146 | P0 | The order is linked to exactly the required number of unique pairs; the default product is one pair with its chosen sticker copies. |
| FR-147 | P0 | Checkout confirmation must use idempotency to prevent double orders or duplicate payment submissions. |
| FR-148 | P0 | Customer order history shows order ID, copy specifications, address/contact snapshot (restricted to owner), payment state, fulfillment state, and safe administrative updates. |

**Supersedes:** FR-113 and §16.1's example "quantity three allocates three Pair IDs and six QR tags" **when quantity means sticker copies**. Quantity now has two explicit axes: `pair_quantity` (number of separately managed kits, default 1) and `copy_quantity` (physical stickers per tag/variant, any allowed positive integer). There is no silent conversion from copies to pairs. P0 shopping UX centers on one kit; an explicit future multi-kit UI is not required to launch.

### A5.1 Example order

| Type | Size variant | Copies | Unique token used |
|---|---|---:|---|
| Lost | Small | 2 | Pair P, Lost token L |
| Lost | Large | 1 | Pair P, Lost token L |
| Emergency | Medium | 2 | Pair P, ICE token I |
| **Total** | | **5 physical copies** | **2 unique tokens; 1 pair** |

**Commercial configuration:** There must be an explicit product/catalog policy for whether the unit pricing includes a pair base fee, adhesives, cut sheets or packing. All prices in production are sourced from catalog/price configuration. No client-calculated grand total is authoritative.

AC-081: Mixed-size order has exact correct itemization and totals on review and order history.  
AC-082: Changes to account address after purchase do not change the saved historical shipping destination.  
AC-083: Duplicate submit/retry cannot create or allocate duplicate kits.  
AC-084: Checkout rejects zero ICE, zero Lost or prohibited sizes, and respects printer minimum physical sizes.

## A6. Requirements: inventory reservation and payment-safe fulfillment

| ID | Priority | Requirement |
|---|---|---|
| FR-149 | P0 | At order confirmation, backend reserves an eligible complete, QA-qualified unsold pair atomically, with expiration and a pointer to the order. |
| FR-150 | P0 | Reserved pairs cannot be given to another live order. Hold expires or is canceled only through controlled state transitions with payment reconciliation. |
| FR-151 | P0 | If a customer has reported a transfer, a short initial reservation timer alone must not release the pair while payment is actively under review; use explicit review/timeout/exception policy. |
| FR-152 | P0 | Finance-approved settlement finalizes pair allocation; unsuccessful/rejected/expired unpaid orders release eligible pair stock only after documented checks and audit. |
| FR-153 | P0 | Allocated, shipped, activated, revoked and disputed pairs are never returned to available inventory merely because an order or file was deleted. |
| FR-154 | P0 | Print generation and release to fulfillment are prohibited until independent payment confirmation, valid allocation and required QA checks exist. |
| FR-155 | P0 | Reserve/allocate operations must be transaction-safe under concurrent requests, retries, process crashes and delayed verification callbacks. |

**Operational clarification:** An admin may generate inventory in advance as digital pairs. The corresponding physical stickers are printed *on demand* from the order's size/quantity instructions after payment confirmation. Existing print-QA requirements apply to both digital artwork and final physical printed labels, with separate statuses if needed.

AC-085: Double checkout cannot allocate same pair.  
AC-086: Pending-review payment cannot silently lose its claimed identity due to an unreviewed TTL expiry.  
AC-087: Declined/abandoned order releases pair once, and a later verified payment for it triggers finance exception/reconciliation rather than allocating someone else's inventory.  
AC-088: No print PDF is released merely because evidence was uploaded.

## A7. Requirements: payment workflow today and safe replacement tomorrow

### A7.1 Provider-independent payment model

| ID | Priority | Requirement |
|---|---|---|
| FR-156 | P0 | Create provider-agnostic `payment_intent/payment_attempt` domain concepts linked to immutable order ID, payable amount/currency, payment method/provider and normalized lifecycle. |
| FR-157 | P0 | Supported payment phases include created/awaiting, customer-submitted/under-review, verified/paid, rejected/failed, expired/canceled and disputed/refund where approved; fulfillment gates check canonical verified settlement, not uploaded files. |
| FR-158 | P0 | A dedicated payment service/interface abstracts manual-transfer verification today and a future trusted payment gateway/API later. |
| FR-159 | P0 | Future adapter changes must not change the customer's order ID, allocated Pair ID, QR public URLs, order-line sizes/copies, or core fulfillment state machine. |
| FR-160 | P0 | Payment verification records reviewer/provider actor, verification source, amount/currency, timestamp, audit ID, and unique external transaction reference where available. |
| FR-161 | P0 | Repeated admin submissions, provider callbacks and webhook retries must be authenticated, signature/timestamp checked where relevant, deduplicated and idempotent; stale conflicting transitions are rejected/escalated. |
| FR-162 | P0 | Price/amount/currency/order correlation and trusted settlement proof are required before marking a payment verified; screenshot OCR, AI, or customer-entered reference is insufficient. |

**Upgrade contract:** Manual payment and future automatic providers must produce the same **internal `PaymentVerified` business event/state transition**, with the same authorization, inventory finalization, print-job enqueue and notifications. The current manual adapter calls it only after authorized finance personnel verify a trusted bank record. The future adapter calls it only after trusted provider settlement verification. An operator fallback/reconciliation mechanism remains available; *do not equate a client redirect or success screen with bank settlement.* The event dispatch and DB status update should be reliable and retryable.

### A7.2 Current bank/Raast manual UX

| ID | Priority | Requirement |
|---|---|---|
| FR-163 | P0 | Review and checkout show official SafeReturn receiver payment details, exact order amount and a unique order reference where supported. |
| FR-164 | P0 | Customer enters **sender account number or Raast identifier**, **sender account-holder name**, transfer reference if available, payment time if known, and optional evidence screenshot according to live policy. The UI explicitly distinguishes sender from SafeReturn receiver details. |
| FR-165 | P0 | Forms validate and limit length, format and supported evidence MIME/size. Sensitive sender details are encrypted/restricted; masked display by default. |
| FR-166 | P0 | Confirm Order/Submit Payment creates a pending-review payment submission and shows honest receipt; it does not mark the order paid. |
| FR-167 | P0 | My Orders displays payment awaiting, under review, verified, rejected/needs more information and fulfillment statuses separately, with a helpful next step. |
| FR-168 | P0 | Finance admin independently checks trusted bank/Raast records and records verification or rejection; permissions and audit are mandatory. |
| FR-169 | P0 | Customer can view submitted masked account details, payment reference and status; untrusted uploaded screenshots are not publicly accessible. |
| FR-170 | P0 | Provide safe re-submission/appeal handling without losing order audit history or creating a new QR pair unnecessarily. |

### A7.3 Google Sheets finance mirror

| ID | Priority | Requirement |
|---|---|---|
| FR-171 | P0 | Google Sheets is a **read/reporting mirror**, not transaction authority. Supabase PostgreSQL remains the source of truth. |
| FR-172 | P0 | Sync stable order/payment identifiers, amount, date, masked sender account, holder as permitted, reference, payment state, verification time and reviewer identifier to a controlled sheet row. |
| FR-173 | P0 | Sheet may contain a **restricted reference/short-lived authorized view flow** for payment evidence, never a public screenshot URL or blindly embedded PII-rich image. |
| FR-174 | P0 | Updates to verified/rejected state must sync after DB commit through a durable, retried, idempotent integration job; Google API outage never reverses bank/payment truth. |
| FR-175 | P0 | Service account access is limited to approved spreadsheet(s), with least-privilege sharing, redaction, syncing status, errors and operator reconciliation. |

**Integration preparedness:** The existing Google Sheet is not attached to this document. Spreadsheet ID, columns, permissions and mapping will be defined in Technical/API/Deployment v1.2 and validated with the actual connected sheet. Do not invent its existing contents or imply live integration currently exists.

AC-089: Screenshot alone never confirms payment.  
AC-090: Admin confirmation updates database and shows paid in customer order; pending sheet sync retries safely.  
AC-091: Switching to mock future gateway adapter keeps order/fulfillment APIs compatible.  
AC-092: Duplicate verified provider notification creates at most one paid transition, allocation and print job.  
AC-093: Unauthorized staff cannot view raw evidence or approve payment.

## A8. Requirements: production PDF, storage and Ready to Ship

| ID | Priority | Requirement |
|---|---|---|
| FR-176 | P0 | After payment verified and allocation final, system creates an idempotent print job per order/print revision and generates a **print-ready PDF** without requiring admin to duplicate any QR image manually. |
| FR-177 | P0 | Printed QR art is grouped **Lost first, then ICE**, and within type by variant/size, repeated exactly as per order. Labels have adequate crop/cut separation and are never stretched or blurred. |
| FR-178 | P0 | Every repeated sticker of one tag uses the exact *same* public token/link and associated pair; any label-specific serial, if required, is non-activating print metadata only. |
| FR-179 | P0 | PDF uses vector QR and logo where feasible, embeds or subsets necessary fonts, compresses safe raster assets and excludes redundant per-sticker full-page images; QA ensures print quality and compact storage. |
| FR-180 | P0 | Format is print-standard with explicit physical units, page dimensions, margins, cutter guides, bilingual tag identification, quiet zones and compatible printer output. |
| FR-181 | P0 | Private activation insert/credential is printed in a separate protected area/page or controlled document, concealed in packaging; it must not appear on public QR stickers. |
| FR-182 | P0 | Generated files and any private manifests are placed in a private Supabase Storage bucket with stable DB references, checksum, generation revision, created time, access controls and retention metadata. |
| FR-183 | P0 | Cloudinary may hold public marketing/product images and an optimized brand asset; sensitive print PDFs/payment proofs are **not** stored in publicly accessible Cloudinary URLs in P0. |
| FR-184 | P0 | Admin **Ready to Ship / Print Queue** lists verified and allocated orders, file generation/QA state, order summary, authorized PDF download, print/pack/ship actions and any recovery/retry error. |
| FR-185 | P0 | Only authorized fulfillment users can request short-lived, access-controlled PDF downloads; prevent public indexing/cache and log access metadata without sensitive contents. |
| FR-186 | P0 | Print/physical QA must scan printed Lost and ICE samples across supported devices, verify correct URL, logo, size, labeling, quantity, cut margins, adhesion and concealed activation credential before shipment. |
| FR-187 | P0 | Admin may regenerate a failed/corrupt layout idempotently or create a versioned authorized reprint; previous released production revision is never silently overwritten. |
| FR-188 | P0 | Delivered orders may trigger automatic cleanup of transient PDFs only after confirmed shipment-delivery evidence, approved grace period and no active dispute/reprint hold; authorized admin may request early deletion under retention/legal policy. |
| FR-189 | P0 | Deleting print files never deletes QR pair/tokens, ownership, customer order, size-by-type quantities, allocation, payment status, shipment history or legally required audit metadata. |
| FR-190 | P0 | Payment evidence uses a separate restricted Supabase bucket and independent retention lifecycle; auto-delete after founder/legal-approved dispute period, not simply at bank approval. |
| FR-191 | P0 | Cleanup is retryable and auditable with orphan reconciliation, object existence checks and safe handling of provider outages; deletion of temporary storage does not create an inconsistent order status. |
| FR-192 | P0 | Reprint after deletion recreates artwork from **persisted immutable order spec and current authorized source data**, only via approval and QR-validity check; never generate a new token as a side effect of reprint. |

**Candidate retention defaults (NOT final policy):** PDF cleanup no sooner than confirmed delivery + 7 days and absent dispute/reprint hold; payment-evidence expiry after a separately approved finance/dispute policy. Retain the fact, timestamp, hash/reference if legally appropriate, reason and actor of deletion, but not expired evidence files. Backups/provider caches may have separate documented expiry windows. Do not label deletion as irreversible if copies still exist in backups.

**PDF storage efficiency:** Create the QR symbol as reusable vector paths per token and size; place references at multiple positions, rather than embedding repeated large PNG files. Reuse logo artwork, avoid unnecessary photographs/backgrounds, apply compression, and reject wildly oversized job output. Define and test maximum PDF bytes/page at implementation once printer/catalog values are known; do not invent universal limits.

AC-094: Order for 3 Lost + 2 ICE yields one pair/two URLs/five print labels; all exact and correctly sized.  
AC-095: Lost section precedes ICE; no cut line/center logo intersects QR quiet zone.  
AC-096: A paid order appears once in Ready to Ship after print job succeeds; failed PDF jobs are retriable.  
AC-097: Unpaid order never releases printable production file; unauthorized users cannot download.  
AC-098: Confirmed delivery + elapsed retention triggers deletion of temporary object but leaves order and QR ownership data intact.  
AC-099: Deleting screenshot after retention never changes payment-verified audit state.  
AC-100: Repeated identical copies produce a compact PDF while staying legible/scannable on the smallest approved label.

## A9. Requirements: customer and admin UX routing

### A9.1 Customer-facing states/screens

1. Public unactivated QR page (`/q/{token}`) shows **Activate QR** and English/Urdu affordances; no raw system error for a legitimate inventory token.
2. Auth forms accept a protected, single-use pending activation intent; after successful login/verified email go directly to **Confirm activation**.
3. Activation result shows linked Lost and ICE tag identities and setup actions; finder/emergency flows require no login once activated.
4. Shop configurator: per-tag type and size stepper with current cart summary and min-pair validation.
5. Order review: address, contact, every line and backend final quote.
6. Payment instructions: SafeReturn recipient details plus sender account-holder/account/transaction reference and optional upload; manual flow branded **Under Review**.
7. My Orders detail: unique order reference, delivery info, print copy summary, masked payment metadata, separate payment and delivery progress.

### A9.2 Admin-facing screens

1. Inventory dashboard and **Create New QR Pairs** dialog (N) plus low-stock indicator, batch outcomes and QA holds.
2. Finance review queue: restricted sender info, payment evidence, bank verification reference, approve/reject and audit.
3. Ready to Ship / print queue: generated PDF indicator, download, actual QA result, print/reprint, dispatch and delivery proof.
4. File retention/cleanup/audit view with permitted deletion and exception status; role-appropriate, no raw medical/emergency profile access for warehouse staff.
5. Sync-monitor view for failed Google Sheets/report updates (could be an admin subsection rather than separate screen).

All user-visible payment status labels must distinguish **customer-submitted**, **bank-verified** and **shipped/delivered**. No confirmation label may misrepresent an unverified transfer as paid. The final exhaustive route/screens matrix belongs in Document 11 v1.2; new routes are proposal-level here.

## A10. Security, privacy and fraud invariants

| ID | Mandatory rule |
|---|---|
| SEC-062 | Public QR token/logo/Pair ID never acts as activation proof or login bypass. |
| SEC-063 | Protected scan intent is bound to specific token, short-lived, safe across auth redirects, no open redirect or secret disclosure. |
| SEC-064 | Owner entitlement derives from verified user/order records, never from user-submitted `owner_user_id`. |
| SEC-065 | Admin/finance/fulfillment roles have server-side separate permissions and MFA per existing policy. |
| SEC-066 | Payment confirmation only from verified bank settlement or a trusted gateway adapter; no screenshot-driven approval. |
| SEC-067 | Payment identifiers and evidence are restricted/encrypted where appropriate, masked in UI and Sheets, absent ordinary logs. |
| SEC-068 | Print URLs and payment proofs use private object storage, approved short-lived access, not globally shareable public links. |
| SEC-069 | File deletion respects disputes, fraud investigations, approved legal retention and current reprint needs. |
| SEC-070 | Google Sheets reports follow least privilege and cannot mutate verified payment/order state. |
| SEC-071 | Generated QR and PDF never contain ICE medical details, private numbers, customer addresses or private activation secrets on public facing labels. |
| SEC-072 | All jobs, webhooks, reservations and payment attempts must be idempotent and audit critical state changes. |

Preserve **all** v1.1 controls for anonymous finder forms, anti-harvesting of ICE contact numbers, WhatsApp opt-in, consent-based geolocation, encrypted precise locations, rate limits, RLS/privilege restrictions, bilingual warning text, and durable notification outbox.

## A11. Data and integration contract (conceptual, not DDL)

The subsequent Database Design document must express the following entities with constraints, not unstructured JSON substitutes:

| Existing/new conceptual record | Purpose and immutable facts |
|---|---|
| `qr_batches`, `tag_pairs`, `qr_codes`, pair activation credential | Retain existing pair model and historical tag replacements |
| `catalog_variants` or equivalent | Permitted type/size/substrate, print limits and approved money configuration |
| `orders`, `order_items`, size/type copy lines | Historical product, price, shipping/contact snapshot; copies are integers |
| `pair_reservations` / allocation fields | One-to-one exclusive temporary claim and permanent verified allocation |
| `payment_attempts` / `payment_events` | Provider identifier, normalized status, validated bank evidence, reviewer and deduplication |
| `payment_evidence` | Private file path/metadata, owner permissions, expiry, deletion record |
| `print_jobs` / `print_artifacts` | Exact order revision, format, generation status, private object key, bytes/checksum and retention |
| `fulfillment_events` / `shipments` | Print-QA, label counts, packed, dispatched, delivered, exceptions |
| `integration_outbox` / `sheet_sync` | DB-after-commit durable Sheets updates with retries, stable row mapping |
| `audit_events` | Authorized actor/source, change, timestamp and non-sensitive identifiers |

The next Technical/API documents must define explicit transactional boundaries for `reserve_pair`, `confirm_payment`, `finalize_allocation`, `create_print_job` and `activate_pair`, with recovery for stale locks and async jobs. **Do not implement QR copies as additional qr_codes rows.**

## A12. External services, cost and deployment controls

- **Supabase:** PostgreSQL/Auth, storage buckets for private payment evidence, private production PDF and optional public product assets; storage metadata is not the order ledger.
- **Cloudinary:** Approved logo/media, product photos and optimized public marketing imagery in P0. Avoid redundant duplication of confidential PDFs across providers; any future Cloudinary private PDF storage requires separate ADR.
- **Google Sheets:** Optional reporting integration enabled with dedicated service account; database continues to operate if Sheets is down.
- **Resend:** Existing outbox-driven transactional messages; never claim email deliverability guaranteed.
- **Manual bank/Raast:** Pilot adapter and human verification; replaceable by a future trusted gateway adapter.
- **Jobs/workers:** A minimal durable asynchronous jobs/outbox approach is sufficient; do not introduce microservices, Kafka or expensive infrastructure solely for PDF generation or synchronization.
- **Cloud object retention:** Keep generated PDFs compact and short-lived; harden access controls, verify quotas and vendor terms before deployment. Price/free tier assumptions are **not verified** in this PRD.

## A13. Release plan changes and test gates

**Suggested revised dependency order:** (1) lock founder commercial/security decisions and ADRs → (2) catalog sizes + pair schema/reservations and migration → (3) scan-led activation → (4) payment service abstraction and manual workflow → (5) copy-aware checkout/order persistence → (6) admin pair generation/branding and QR QA → (7) PDF worker/storage/private downloads → (8) payment verification→allocation→Ready to Ship → (9) Google Sheets mirror → (10) cleanup jobs and dispute/reprint safety → (11) bilingual UI/regression/security/physical pilot checks.

**Mandatory end-to-end acceptance demonstration:**

1. Authorized admin generates 10 valid pairs, inventory reports 10 pair units and 20 distinct public tags.
2. Customer configures one pair with 3 Lost and 2 ICE physical copies, including at least two permitted size variants.
3. Review screen itemizes each copy count, shipping/contact snapshot and server total.
4. Order reserves precisely one eligible pair; concurrent buyer cannot reserve it.
5. Customer submits sender details + optional screenshot; My Orders displays Under Review; print queue does not release production files.
6. Finance confirms transfer using trusted bank record; payment service marks verified, records audit and finalized allocation exactly once.
7. Google Sheets mirror receives non-public restricted row/status (or retry remains pending if provider unavailable).
8. PDF worker creates a compact private file with exactly five labels, Lost first, ICE second, center logo, correct tokens/sizes, concealed activation insert and cutting margins.
9. Authorized admin retrieves PDF, verifies physical output, packs correct pair, ships and records confirmed delivery.
10. Customer scans either unactivated tag, chooses Activate, signs in, returns to same pair context and activates both once without rescan.
11. Another random account scanning the same tag cannot claim ownership; active Lost and ICE routes behave correctly and preserve privacy.
12. After retention triggers, sensitive temporary files are deleted, but order ID, print copy breakdown, pair ownership and payment/fulfillment audit remain accessible.
13. Swap the manual payment adapter with a simulated automatic-provider adapter; the same order and allocation workflows still pass with idempotent duplicate events.

**Release blockers:** unauthorized activation; duplicate pair allocation; screenshot-only payment verification; raw payment evidence/public PDF link leakage; QR not scannable at approved smallest size; printable public activation secret; failure to maintain order after file cleanup; unverifiable delivered state; non-idempotent payment callbacks; medical/ICE privacy regression.

## A14. Decision register for completion in downstream documents

| ID | Decision | Proposed safe baseline | Status |
|---|---|---|---|
| PRD12-DEC-01 | Exact sellable sizes, material and price table | Admin-configured validated catalog | Needs founder configuration |
| PRD12-DEC-02 | Minimum 1 of each printed tag | Enforced per new pair | Founder direction accepted |
| PRD12-DEC-03 | Reservation hold & pending-review grace | Configurable policy; no premature payment-review release | Needs policy value |
| PRD12-DEC-04 | Gift/third-party activation | Concealed one-time credential only | Security review required |
| PRD12-DEC-05 | Evidence retention | Delete after finance/dispute window | Needs legal/finance approval |
| PRD12-DEC-06 | PDF retention | Delivery + proposed 7 day grace, legal/reprint exceptions | Needs founder approval |
| PRD12-DEC-07 | Payment provider | Manual now; automatic verified gateway later | Gateway undecided |
| PRD12-DEC-08 | Google Sheet schema and sharing | Restricted mirror, masked sender account | Real sheet mapping pending |
| PRD12-DEC-09 | QR center logo artwork and scanning | Measured approved art, no quiet zone overlap | Physical QA pending |
| PRD12-DEC-10 | Shipping/carrier delivery evidence | Authorized verification and audit | Carrier policy pending |
| PRD12-DEC-11 | Cloudinary scope | Public media only, confidential files in Supabase | Proposed v1.2 architecture |
| PRD12-DEC-12 | Payment screenshot optionality | Optional when manual reference details sufficient | Finance review pending |

## A15. v1.1 compatibility index and change precedence

| Older v1.1 provision | v1.2 handling |
|---|---|
| §7 FR-065–071 paired kit identity | **Retained**, now distinguishes one pair from copies |
| §12.2 mandatory Pair ID + secret entry on every purchase | **Qualified** for verified online purchasers via signed scan intent/order entitlement; gift/offline secret retained |
| §16.1 FR-113 quantity examples | **Superseded for print copy count**; pair quantity remains an explicit distinct field |
| §16.1 FR-114–117 complete-pair allocation, QA and concealed insert | **Retained**, adapted to print-on-demand |
| §19 parent/child schema and §20 activation API | **Retained conceptually**; downstream v1.2 DB/API to extend without duplicate child rows |
| §21 privacy/security and §23 physical standards | **Retained** and strengthened for logo/pdfs/payments |
| Manual bank transfer verification | **Retained as an adapter**, not permanently hard-wired into order service |
| Supabase and Cloudinary | Supabase authoritative/private, Cloudinary approved public media |
| Google Sheets in v1.1 | New v1.2 mirror requirement, not source of truth |
| v1.1 accepted FR/AC wording not named here | Remains applicable unless directly conflicting; flag unresolved conflicts for ADR |

---

## A11. Founder-approved extensibility amendment — October 12, 2026

**Overrides any v1.2 wording limiting a customer to one pair across their account, or permanently limiting checkout to stickers.** Only QR stickers are sold at pilot launch, but the catalog and ownership model must support future keychains, bag tags, children’s badges, and emergency badges.

| ID | Priority | Requirement |
|---|---|---|
| FR-201 | P0 architectural foundation | One authenticated account may own many distinct `tag_pairs`; each pair continues to contain exactly one current Lost tag and one current ICE tag. |
| FR-202 | P0 | Each current Lost QR has its own editable recovery profile, and each current ICE QR has its own independently editable emergency profile; editing one cannot modify another unless an explicit shared-profile feature is approved later. |
| FR-203 | P0 | Multiple printed copies of the *same* QR identity share its URL and profile; they do not have independently editable pages. |
| FR-204 | P0 catalog foundation | Store products and purchasable variants (SKU, name, optional size/material/color, price, images, fulfillment template, sale/publication status) separately from QR identities. QR stickers are the only published launch product. |
| FR-205 | P0 order history | Every line item persists `product_id`, `variant_id`, purchased product name/SKU/variant/price snapshots, quantity, and tag-specific print instructions; past orders must remain truthful if the catalog later changes. |
| FR-206 | P1 when additional products launch | Authorized admins can create, update, publish, archive and feature products/variants, upload Cloudinary public assets, and select print/manufacturing templates; archived products remain visible in historical orders. |
| FR-207 | P1 when additional products launch | A purchased physical item can either print an eligible already-owned QR identity (same page/profile) or request a **new complete QR pair** (two tags, separate editable profiles). Never create an unpaired freely-owned one-sided QR implicitly. |
| FR-208 | P1 when additional products launch | One order may contain multiple product/variant line items and zero or more **new pair units**, subject to each product’s eligibility/entitlement rules; standalone reprints using already-owned pairs do not consume new inventory. |
| FR-209 | P1 | Homepage and shop fetch `published`/`featured` catalog entries through authorized public read endpoints; horizontal scroll/swipe carousel with accessible buttons and a full catalog page; no hardcoded product cards. |
| FR-210 | P0 security foundation | All QR profile reads/writes and existing-pair reuse must be authorized against pair ownership; children’s/minors’ content and emergency publication need explicit privacy/guardian protections. |
| FR-211 | P0 | Printed-artifact metadata binds every printed occurrence to order item, pair, QR tag, variant and quantity, without treating print-copy rows as new QR identities. |

**Launch-versus-future distinction:** P0 must establish a forward-compatible normalized schema and independent tag profile management. Enable admin multi-product publishing and existing-QR reuse at P1 after API/UI/security/fulfillment verification. A shopper is not promised a new-product screen in the Lahore P0 unless separately approved. Product photos are Cloudinary-public; payment evidence and print PDFs stay in private Supabase Storage.


# PART B — ARCHIVED v1.1 AMENDMENT (TRACEABILITY ONLY)

> The following is the original uploaded v1.1 PRD amendment retained for reference. **Where Part B conflicts with Part A, Part A is authoritative.** It is not a separately implementable specification. The v1.0 base PRD was not supplied among the 11 uploads; earlier v1.0 requirements referenced by v1.1 must be verified against the actual original before claiming a complete merged v1.0–v1.2 baseline.

# SafeReturn — PRD v1.1 Amendment

Revision date: 11 October 2026 · Lahore Pilot · Supersedes affected sections of PRD v1.0

Change status: Proposed for founder approval, with security-sensitive refinements.

This amendment updates Sections 7, 9–15, 17–21, 23–27, 29, and 33, while leaving unaffected requirements from v1.0 in force.

## Critical architecture decisions

The paired-tag kit is now the unit of sale, ownership, and activation, while each tag retains its own permanent public URL and independently configurable public profile.

One important security distinction: a direct WhatsApp link necessarily discloses the owner's WhatsApp number to the finder. It cannot simultaneously guarantee that number's privacy. Therefore the feature must be disabled by default, require explicit owner consent, and clearly warn that anyone accessing the QR page may obtain the number.

Similarly, making emergency phone numbers available only after Turnstile verification can delay legitimate emergency access. The revised design uses a lightweight reveal mechanism with a risk-adaptive bot check, rather than making an external CAPTCHA service an absolute prerequisite to emergency calling. This is a deliberate safety exception to the proposed mandatory bot check, requiring founder approval.

The six changes are classified as follows:

| Change                                  | Priority     | Architectural impact                                    |
| --------------------------------------- | ------------ | ------------------------------------------------------- |
| Bilingual Urdu/English public interface | P0           | Localization, print artwork, accessibility and QA       |
| Direct WhatsApp click-to-chat           | P0, opt-in   | Public phone disclosure, preferences, audit             |
| Paired lost-item and ICE tags           | P0           | Inventory, activation, schema, commerce                 |
| Finder-initiated geolocation            | P0, optional | Consent, precise location storage, email payload        |
| ICE number reveal protection            | P0           | Public contact API, bot checks, emergency accessibility |
| Physical QR print specifications        | P0           | Dimensions, encoding, packaging and QA                  |

# Revised Section 7 — Product Scope

## 7.1 Physical product definition

FR-065 — Paired kit product model

Each SafeReturn retail kit contains exactly two distinct physical QR tags:

| Tag   | Designation              | Primary purpose                              |
| ----- | ------------------------ | -------------------------------------------- |
| Tag A | Lost-Object Recovery Tag | Bags, keys, luggage, and personal belongings |
| Tag B | Emergency / ICE Tag      | Wallets, helmets, motorcycles, vehicles      |

Each tag has its own immutable, cryptographically unpredictable public URL:

- Tag A: `https://safereturn.pk/q/{lost_token}`
- Tag B: `https://safereturn.pk/q/{ice_token}`

Both tags belong to one internal Pair ID, share one activation credential, and are activated atomically under the same owner.

The Pair ID must be a non-secret, unique identifier. It must not grant activation rights.

FR-066: A paired kit is purchased and allocated as one inventory unit.

FR-067: Both tags must be activated together, but can subsequently have separate item assignments and public operational states.

FR-068: Tag A defaults to lost-item mode; Tag B defaults to emergency mode. The public URL for either tag remains stable.

FR-069: A kit owner may configure the two tags independently after activation, within the supported tag-purpose rules.

FR-070: For P0, the recommended configuration is to preserve Tag A as lost-item recovery and Tag B as emergency identification. A future combined mode may be offered independently for either tag, subject to explicit publication consent.

FR-071: The owner dashboard must display the paired kit and its two child tags clearly, rather than presenting them as two unrelated purchases.

### Acceptance criteria

AC-025: A single valid activation credential activates both QR tags in one database transaction.

AC-026: Each physical tag resolves to its own correct public page.

AC-027: A failure activating either child tag rolls back activation of the entire pair.

AC-028: The dashboard identifies both tags as belonging to the same kit.

# Revised Section 9 — Functional Requirements

| ID     | Priority | Requirement                                                                                 |
| ------ | -------- | ------------------------------------------------------------------------------------------- |
| FR-072 | P0       | Public QR pages must support English and Urdu                                               |
| FR-073 | P0       | All printed QR labels and retail packaging must contain bilingual instructions              |
| FR-074 | P0       | Finder forms must offer a visible English/Urdu language switch                              |
| FR-075 | P0       | Owners may explicitly enable direct WhatsApp contact per lost-item tag                      |
| FR-076 | P0       | WhatsApp contact is disabled by default                                                     |
| FR-077 | P0       | Finders may optionally share their current browser location                                 |
| FR-078 | P0       | Geolocation is requested only after a finder action                                         |
| FR-079 | P0       | Public ICE phone numbers require an explicit reveal action                                  |
| FR-080 | P0       | Automated harvesting controls must protect contact-reveal endpoints                         |
| FR-081 | P0       | A pair must have one activation credential and two unique public tokens                     |
| FR-082 | P0       | Physical production must enforce the revised dimensions, quiet zone, and encoding standards |

Existing FR-001 through FR-064 remain applicable unless superseded by these requirements.

# Revised Section 11 — Website and UI Requirements

## 11.1 Bilingual public interface

FR-083: Every public QR landing page must include visible Urdu and English instructions, regardless of the selected interface language.

Examples:

| English                     | Urdu                                    |
| --------------------------- | --------------------------------------- |
| Scan to Return              | واپس کرنے کے لیے اسکین کریں             |
| Found this item?            | کیا آپ کو یہ چیز ملی ہے؟                |
| Contact the Owner           | مالک سے رابطہ کریں                      |
| Send Message                | پیغام بھیجیں                            |
| Share Location              | اپنا مقام شیئر کریں                     |
| Emergency Contact           | ہنگامی رابطہ                            |
| Tap to Reveal / Call        | نمبر دیکھنے یا کال کرنے کے لیے ٹیپ کریں |
| Chat with Owner on WhatsApp | واٹس ایپ پر مالک سے رابطہ کریں          |

Translations are proposed and must be reviewed by a fluent Urdu speaker before printing or launch.

## 11.2 Language behavior

- Default to a supported language based on the user's browser preference, falling back to English.
- Always provide a visible language toggle.
- Use `lang="ur"` and right-to-left layout for Urdu content.
- Preserve left-to-right formatting for phone numbers, URLs, and email addresses.
- Translate field labels, validation errors, confirmation messages, privacy notices, and unavailable-QR states.
- Do not rely on automatic browser translation for essential workflows.
- Maintain consistent language selection across the public scan and finder form.

## 11.3 Revised public page components

SafeReturn

English | اردو

## Found this item?

کیا آپ کو یہ چیز ملی ہے؟

Help return this item to its owner. No account is needed.

Your message / آپ کا پیغام

Enter a message for the owner...

Your contact / آپ کا رابطہ

Phone or email

Share Location / اپنا مقام شیئر کریں

Chat with Owner on WhatsApp

Only when enabled by the owner

Send Message / پیغام بھیجیں

Illustrative layout; the production form includes validation, consent, and functional controls.

## 11.4 Updated UI acceptance criteria

AC-029: A finder can complete the lost-item form entirely in Urdu.

AC-030: Urdu content renders right-to-left without reversing telephone numbers or URLs.

AC-031: A language switch does not discard already entered form data.

AC-032: Every public QR status page has a bilingual explanation.

AC-033: Public finder workflows are tested with Urdu-speaking participants who are not instructed by the development team.

AC-034: WhatsApp, location sharing, and phone reveal actions are labeled accessibly in both languages.

# Revised Section 12 — QR Lifecycle and State Machine

## 12.1 Paired kit architecture

The new entity hierarchy is:

\#chatgpt-mermaid-\_r_1vd\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_1vd\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_1vd\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_1vd\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_1vd\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_1vd\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_1vd\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_1vd\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_1vd\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_1vd\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vd\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vd\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_1vd\_ p{margin:0;}#chatgpt-mermaid-\_r_1vd\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_1vd\_ .label text,#chatgpt-mermaid-\_r_1vd\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .node rect,#chatgpt-mermaid-\_r_1vd\_ .node circle,#chatgpt-mermaid-\_r_1vd\_ .node ellipse,#chatgpt-mermaid-\_r_1vd\_ .node polygon,#chatgpt-mermaid-\_r_1vd\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .rough-node .label text,#chatgpt-mermaid-\_r_1vd\_ .node .label text,#chatgpt-mermaid-\_r_1vd\_ .image-shape .label,#chatgpt-mermaid-\_r_1vd\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_1vd\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .rough-node .label,#chatgpt-mermaid-\_r_1vd\_ .node .label,#chatgpt-mermaid-\_r_1vd\_ .image-shape .label,#chatgpt-mermaid-\_r_1vd\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_1vd\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_1vd\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vd\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vd\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_1vd\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_1vd\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vd\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vd\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_1vd\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_1vd\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vd\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_1vd\_ .icon-shape,#chatgpt-mermaid-\_r_1vd\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_1vd\_ .icon-shape p,#chatgpt-mermaid-\_r_1vd\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_1vd\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_1vd\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vd\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_1vd\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_1vd\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_1vd\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_1vd\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_1vd\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_1vd\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vd\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_1vd\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vd\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_1vd\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_1vd\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_1vd\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_1vd\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .node rect,#chatgpt-mermaid-\_r_1vd\_ .node circle,#chatgpt-mermaid-\_r_1vd\_ .node ellipse,#chatgpt-mermaid-\_r_1vd\_ .node polygon,#chatgpt-mermaid-\_r_1vd\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_1vd\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_1vd\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_1vd\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_1vd\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vd\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}QR Production BatchTag Pair / KitTag A: Lost-Object QRTag B: Emergency ICE QROne Activation CredentialOne OwnerLost Item ProfileEmergency Profile

FR-084: Each `tag_pair` must reference exactly one Tag A and one Tag B.

FR-085: The two child tags must have distinct public tokens and distinct QR serial numbers.

FR-086: A child tag cannot belong to more than one pair.

FR-087: A pair cannot be activated if either child tag is already activated, revoked, disputed, or assigned to another owner.

FR-088: The activation credential must be associated with the pair, not duplicated for each tag.

## 12.2 Pair activation workflow

1. Customer logs in and verifies their email.
2. Customer enters the Pair ID and private activation secret.
3. Backend verifies entitlement to the purchased kit.
4. Backend checks rate limits and credential lockout.
5. Backend starts a database transaction.
6. Backend locks the pair, credential, and both QR rows in a deterministic order.
7. Backend verifies that the pair and both tags are eligible.
8. Backend assigns one owner to the pair and both tags.
9. Backend activates both tags.
10. Backend consumes the shared activation credential.
11. Backend creates an audit event and activation notification.
12. Transaction commits.
13. Dashboard opens a two-tag setup wizard.

If any database operation fails, the entire transaction rolls back.

AC-035: A concurrent activation race cannot produce different owners for Tag A and Tag B.

AC-036: Repeating an already successful activation with the same idempotency key returns the existing result without reassigning ownership.

AC-037: A partial pair activation is impossible under normal database constraints and transactional logic.

## 12.3 Revised lifecycle dimensions

| Entity            | Lifecycle                                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| Pair              | `generated`, `printed`, `qa_passed`, `reserved`, `shipped`, `delivered`, `activated`, `disputed`, `revoked` |
| Child tag         | `unactivated`, `active`, `owner_disabled`, `admin_suspended`, `revoked`                                     |
| Shared credential | `unused`, `locked`, `consumed`, `revoked`                                                                   |

Physical inventory status should remain separate from ownership and public operational status, as established in v1.0. The pair-level lifecycle above is a summary, not a replacement for the orthogonal state dimensions.

## 12.4 Deactivation and replacement

An owner may disable one tag independently without disabling the other.

For example, a damaged lost-item tag may be disabled while the emergency tag remains active.

Replacement policy: A replacement child tag receives a new public token. The Pair ID remains stable, and the replacement is attached to the existing pair through an audited replacement operation.

The replaced token is revoked permanently.

A pair may retain one activation credential that is already consumed; replacement does not re-enable that credential.

## 12.5 Ownership transfer

A pair is the unit of ownership transfer.

Transferring the kit transfers both tags together. Independent transfer of Tag A or Tag B is not supported in P0 or P1 unless a future product decision explicitly introduces pair splitting.

After transfer, former owner emergency details, finder-message history, and private preferences must not become accessible to the recipient.

# Revised Section 13 — Emergency Identification

## 13.1 Phone number harvesting protection

The requirement is to reduce automated harvesting of published emergency phone numbers while preserving rapid emergency access.

SEC-041: Initial HTML and server-rendered public page data must not contain full emergency contact numbers.

SEC-042: Initial page metadata, structured data, analytics events, and embedded scripts must not contain full phone numbers.

SEC-043: Phone numbers must be fetched from a separate, protected public contact-reveal endpoint after a deliberate user action.

SEC-044: Contact reveal endpoints must apply IP-based and QR-based rate limits, automated abuse detection, and Turnstile verification when required.

SEC-045: Successfully revealed numbers must not be stored in persistent browser storage.

SEC-046: Contact reveal responses must use `Cache-Control: no-store`.

SEC-047: The interface must not claim that click-to-reveal makes public numbers impossible to scrape. A number revealed to an anonymous visitor remains obtainable by that visitor.

## 13.2 Recommended emergency UX

SafeReturn · ICE

## Emergency Contacts

ہنگامی رابطے

Emergency information provided by the owner. Not medically verified.

Primary Contact · Father

Number hidden until requested

Tap to Reveal / Call

نمبر دیکھنے یا کال کرنے کے لیے ٹیپ کریں

Illustrative design. A production control performs the protected reveal request.

## 13.3 Reveal workflow

\#chatgpt-mermaid-\_r_1vr\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_1vr\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_1vr\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_1vr\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_1vr\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_1vr\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_1vr\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_1vr\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_1vr\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_1vr\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vr\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vr\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_1vr\_ p{margin:0;}#chatgpt-mermaid-\_r_1vr\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_1vr\_ .label text,#chatgpt-mermaid-\_r_1vr\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .node rect,#chatgpt-mermaid-\_r_1vr\_ .node circle,#chatgpt-mermaid-\_r_1vr\_ .node ellipse,#chatgpt-mermaid-\_r_1vr\_ .node polygon,#chatgpt-mermaid-\_r_1vr\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .rough-node .label text,#chatgpt-mermaid-\_r_1vr\_ .node .label text,#chatgpt-mermaid-\_r_1vr\_ .image-shape .label,#chatgpt-mermaid-\_r_1vr\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_1vr\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .rough-node .label,#chatgpt-mermaid-\_r_1vr\_ .node .label,#chatgpt-mermaid-\_r_1vr\_ .image-shape .label,#chatgpt-mermaid-\_r_1vr\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_1vr\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_1vr\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vr\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vr\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_1vr\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_1vr\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vr\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vr\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_1vr\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_1vr\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_1vr\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_1vr\_ .icon-shape,#chatgpt-mermaid-\_r_1vr\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_1vr\_ .icon-shape p,#chatgpt-mermaid-\_r_1vr\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_1vr\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_1vr\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_1vr\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_1vr\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_1vr\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_1vr\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_1vr\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_1vr\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_1vr\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vr\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_1vr\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_1vr\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_1vr\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_1vr\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_1vr\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_1vr\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .node rect,#chatgpt-mermaid-\_r_1vr\_ .node circle,#chatgpt-mermaid-\_r_1vr\_ .node ellipse,#chatgpt-mermaid-\_r_1vr\_ .node polygon,#chatgpt-mermaid-\_r_1vr\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_1vr\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_1vr\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_1vr\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_1vr\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_1vr\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Open emergency QRShow public profile withoutphoneTap Reveal / CallAbuse riskApply rate limitsRun Turnstile verificationAllowed?Fetch phone over HTTPSSafe retry / alternate guidanceDisplay number and Call actionLowElevatedYesNo

The first reveal must work without registration or account creation.

Safety exception: If Turnstile is unavailable, the backend may allow a tightly rate-limited emergency contact reveal where the request is otherwise low risk. The system must not make legitimate emergency information entirely dependent on a third-party challenge service.

This is recommended over mandatory Turnstile verification on every call.

## 13.4 Additional acceptance criteria

AC-038: Initial HTML does not contain full contact numbers.

AC-039: An ordinary user can reveal and call an emergency contact using a mobile browser.

AC-040: Automated repeated contact-reveal requests trigger abuse controls.

AC-041: Contact reveal does not require login, registration, or installation.

AC-042: A Turnstile outage does not automatically make every emergency contact unreachable.

# Revised Section 14 — Lost-Item Recovery

## 14.1 Finder form — updated fields

| Field                  | Required    | Validation / behavior                      |
| ---------------------- | ----------- | ------------------------------------------ |
| Message                | Yes         | 10–1,000 characters                        |
| Finder name            | No          | Maximum 80 characters                      |
| Email                  | Conditional | Valid email; at least one contact method   |
| Phone                  | Conditional | Valid phone; at least one contact method   |
| Contact preference     | No          | Email or phone                             |
| Share Location         | No          | Explicit opt-in                            |
| Latitude               | No          | Generated by browser only after permission |
| Longitude              | No          | Generated by browser only after permission |
| Location accuracy      | No          | Browser-reported accuracy in meters        |
| Location consent       | Conditional | Required if coordinates are submitted      |
| Turnstile              | Risk-based  | Server-side verification                   |
| Finder contact consent | Yes         | Required for submission                    |

## 14.2 Direct WhatsApp communication

FR-089: Owners must have a per-tag toggle named “Allow direct WhatsApp contact.”

FR-090: The toggle is disabled by default.

FR-091: Enabling the feature requires the owner to verify or confirm the WhatsApp-enabled number and explicitly acknowledge that the number becomes available to the public.

FR-092: When enabled, the finder page displays a prominent green bilingual WhatsApp contact button.

FR-093: The button opens a WhatsApp click-to-chat URL using the international phone number format without the leading `+`.

Example format:

`https://wa.me/923001234567?text=Hello%2C%20I%20found%20your%20item`

FR-094: The prefilled message must not include medical details, private account identifiers, activation secrets, or precise finder location.

FR-095: The finder may still submit the SafeReturn form. WhatsApp does not replace the durable finder-message workflow.

FR-096: SafeReturn must not claim to have delivered, recorded, or received a WhatsApp message merely because the link was opened.

FR-097: Disabling the toggle must remove the contact button from subsequent page loads.

FR-098: The owner must be warned that the WhatsApp number is disclosed to anyone who opens the chat link and may be collected or misused.

### Important clarification

Resend remains the transactional notification provider for messages submitted through SafeReturn. However, WhatsApp-only conversations are not stored or audited by SafeReturn.

Opening `wa.me` does not generate a finder message or guaranteed email notification. If a durable record is required, the finder must submit the SafeReturn form.

The owner must understand this distinction.

## 14.3 WhatsApp privacy and UX

Recommended owner settings:

| Setting                               | Default                         |
| ------------------------------------- | ------------------------------- |
| Allow direct WhatsApp contact         | Off                             |
| WhatsApp phone number                 | Empty                           |
| Use account phone number              | No automatic selection          |
| Display WhatsApp contact on Tag A     | Off                             |
| Display WhatsApp contact on ICE Tag B | Off unless separately supported |

The owner should be encouraged to use a dedicated contact number rather than a private personal number.

The backend should return a validated click-to-chat destination only when the feature is enabled. It must never expose the number through an unrelated private profile endpoint.

No Meta Cloud API is needed for a simple `wa.me` deep link, and no automated WhatsApp messages are sent by SafeReturn.

## 14.4 Optional browser geolocation

FR-099: The finder form must include an optional “Share Location” action.

FR-100: Browser geolocation permission must be requested only after the finder clicks that action.

FR-101: Location permission denial must not prevent message submission.

FR-102: The interface must explain that the current location may be shared with the owner and may not be the exact location of the found item.

FR-103: Store coordinates only when the finder explicitly agrees to share them.

FR-104: Location data must not appear on the public QR page.

FR-105: Location must be available only to the authorized owner and narrowly authorized support personnel.

FR-106: The finder must be able to clear the selected location before submitting.

FR-107: Geolocation failures must produce a bilingual, non-blocking message.

FR-108: The owner notification must include a clickable Google Maps link when valid coordinates were voluntarily submitted.

Example:

`https://www.google.com/maps?q=31.5204,74.3587`

The example coordinates are illustrative, not a real finder location.

## 14.5 Geolocation processing rules

- Browser geolocation requires a secure context, normally HTTPS.
- The frontend requests permission after explicit interaction.
- The frontend may request a reasonably accurate position with a short timeout.
- The backend validates latitude between −90 and +90.
- The backend validates longitude between −180 and +180.
- The backend validates accuracy as a non-negative finite value when supplied.
- The backend must not trust coordinates as proof of physical presence.
- No background or continuous location tracking is permitted.
- Location sharing is one-time and associated only with the finder submission.
- Coordinates should be retained no longer than the associated finder message unless a documented legal or security exception applies.
- Emailing a Google Maps link discloses the submitted coordinates to the email provider and to Google when the link is opened. This must be reflected in the privacy notice.

## 14.6 Revised finder workflow

\#chatgpt-mermaid-\_r_207\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_207\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_207\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_207\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_207\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_207\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_207\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_207\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_207\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_207\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_207\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_207\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_207\_ p{margin:0;}#chatgpt-mermaid-\_r_207\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_207\_ .label text,#chatgpt-mermaid-\_r_207\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .node rect,#chatgpt-mermaid-\_r_207\_ .node circle,#chatgpt-mermaid-\_r_207\_ .node ellipse,#chatgpt-mermaid-\_r_207\_ .node polygon,#chatgpt-mermaid-\_r_207\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .rough-node .label text,#chatgpt-mermaid-\_r_207\_ .node .label text,#chatgpt-mermaid-\_r_207\_ .image-shape .label,#chatgpt-mermaid-\_r_207\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_207\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .rough-node .label,#chatgpt-mermaid-\_r_207\_ .node .label,#chatgpt-mermaid-\_r_207\_ .image-shape .label,#chatgpt-mermaid-\_r_207\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_207\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_207\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_207\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_207\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_207\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_207\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_207\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_207\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_207\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_207\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_207\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_207\_ .icon-shape,#chatgpt-mermaid-\_r_207\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_207\_ .icon-shape p,#chatgpt-mermaid-\_r_207\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_207\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_207\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_207\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_207\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_207\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_207\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_207\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_207\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_207\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_207\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_207\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_207\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_207\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_207\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_207\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_207\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_207\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .node rect,#chatgpt-mermaid-\_r_207\_ .node circle,#chatgpt-mermaid-\_r_207\_ .node ellipse,#chatgpt-mermaid-\_r_207\_ .node polygon,#chatgpt-mermaid-\_r_207\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_207\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_207\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_207\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_207\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_207\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Finder scans Tag ABilingual lost-item pageChoose contact methodEnter message and contactOpen wa.meShare location?Request browser permissionValidate submissionAttach coordinatesCommit message and outboxShow accepted confirmationWorker sends Resend emailFinder chats externallySafeReturn formWhatsApp enabledYesNoGrantedDenied

## 14.7 Updated acceptance criteria

AC-043: WhatsApp is absent when disabled.

AC-044: Enabling WhatsApp requires explicit disclosure consent.

AC-045: WhatsApp button uses a valid, encoded `wa.me` URL.

AC-046: Clicking WhatsApp does not falsely create a “message delivered” status.

AC-047: Finder can submit without sharing location.

AC-048: Denied geolocation permission does not block submission.

AC-049: Valid shared coordinates appear only in the authorized owner message and notification.

AC-050: Invalid coordinates are rejected or omitted according to the documented validation policy, without silently changing them.

AC-051: Location can be removed before submission.

AC-052: Both WhatsApp and geolocation controls work in the bilingual mobile interface.

# Revised Section 15 — Email Notification Architecture

## 15.1 Finder email payload

The existing database-backed outbox and Resend architecture remain mandatory.

When a finder submits a message, the notification payload may include:

| Field                     | Condition                         |
| ------------------------- | --------------------------------- |
| Tag serial and item label | Always                            |
| Finder name               | If supplied                       |
| Finder contact method     | Always                            |
| Finder message            | Always                            |
| Submitted location        | Only with explicit consent        |
| Google Maps link          | Only when valid coordinates exist |
| Dashboard message link    | Always                            |
| Submission timestamp      | Always                            |

The email must not include unrelated medical information, activation secrets, or the owner's account credentials.

FR-109: Location-containing notifications must be marked as sensitive and excluded from verbose application logs.

FR-110: A Google Maps link must be constructed only from validated numeric coordinates, never from arbitrary finder-provided URLs.

FR-111: Resend delivery attempts must remain independent of WhatsApp link usage.

FR-112: Email failures must not cause accepted finder messages or their shared location to be lost.

AC-053: A location-enabled finder message produces one durable notification event containing the authorized location reference.

AC-054: A message without location does not generate a location link.

AC-055: A WhatsApp-only interaction does not appear as a successfully delivered SafeReturn email.

# Revised Section 16 — E-Commerce and Fulfillment

## 16.1 Product and inventory adjustments

FR-113: Product quantities represent paired kits, not individual child tags.

For example, purchasing quantity three allocates three Pair IDs and six physical QR tags.

FR-114: Each order allocation must reference a complete pair.

FR-115: A kit cannot be marked as print-QA-passed unless both tags have passed scan tests and their activation insert matches the Pair ID.

FR-116: Packaging must clearly distinguish Tag A and Tag B.

FR-117: Order fulfillment must not ship a kit with a missing child tag or exposed activation credential.

## 16.2 Packaging labels

Recommended package labeling:

Tag A — Lost Item / گمشدہ چیز

Tag B — Emergency / ہنگامی رابطہ

One activation code activates both tags / ایک ایکٹیویشن کوڈ دونوں ٹیگز فعال کرتا ہے

The packaging must explain that the two tags have different purposes and must not be confused with two separately purchased accounts.

# Revised Section 17 — Technology Stack

The original technology stack remains approved provisionally.

Two additions are necessary:

| Technology                            | Role                                                            | Cost consideration                          |
| ------------------------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| Next.js internationalization approach | English/Urdu dictionaries, locale routing or state, RTL support | No additional paid SaaS required            |
| Browser Geolocation API               | Finder-initiated, optional location sharing                     | Browser-native API; no GPS-tracking service |

WhatsApp click-to-chat uses a standard HTTPS deep link, not Meta's messaging API.

No geocoding service is required in P0 because the platform stores numeric coordinates and constructs a Google Maps link.

# Revised Section 18 — System Architecture

\#chatgpt-mermaid-\_r_20g\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_20g\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_20g\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_20g\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_20g\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_20g\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_20g\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_20g\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_20g\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_20g\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20g\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20g\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_20g\_ p{margin:0;}#chatgpt-mermaid-\_r_20g\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_20g\_ .label text,#chatgpt-mermaid-\_r_20g\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .node rect,#chatgpt-mermaid-\_r_20g\_ .node circle,#chatgpt-mermaid-\_r_20g\_ .node ellipse,#chatgpt-mermaid-\_r_20g\_ .node polygon,#chatgpt-mermaid-\_r_20g\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .rough-node .label text,#chatgpt-mermaid-\_r_20g\_ .node .label text,#chatgpt-mermaid-\_r_20g\_ .image-shape .label,#chatgpt-mermaid-\_r_20g\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_20g\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .rough-node .label,#chatgpt-mermaid-\_r_20g\_ .node .label,#chatgpt-mermaid-\_r_20g\_ .image-shape .label,#chatgpt-mermaid-\_r_20g\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_20g\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_20g\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20g\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20g\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_20g\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_20g\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_20g\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_20g\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_20g\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_20g\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20g\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_20g\_ .icon-shape,#chatgpt-mermaid-\_r_20g\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_20g\_ .icon-shape p,#chatgpt-mermaid-\_r_20g\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_20g\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_20g\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_20g\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_20g\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_20g\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_20g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_20g\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_20g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_20g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20g\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_20g\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20g\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_20g\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_20g\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_20g\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_20g\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .node rect,#chatgpt-mermaid-\_r_20g\_ .node circle,#chatgpt-mermaid-\_r_20g\_ .node ellipse,#chatgpt-mermaid-\_r_20g\_ .node polygon,#chatgpt-mermaid-\_r_20g\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_20g\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_20g\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_20g\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_20g\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20g\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Physical paired kitTag A Lost QRTag B ICE QRBilingual public lost-item pageBilingual emergency pageFinder form + optionalgeolocationOpt-in WhatsApp deep linkProtected contact reveal APIFastAPISupabase PostgreSQLNotification outbox workerResendExternal WhatsAppconversation

The WhatsApp conversation occurs outside SafeReturn's application boundary.

The browser's location permission and the external Google Maps destination are also explicit privacy boundaries.

# Revised Section 19 — Database Schema and ERD

## 19.1 Schema migration strategy

The paired kit introduces a parent entity (`tag_pairs`) above individual QR tags. This changes the ownership, activation, and inventory model.

For a new deployment, create the revised schema directly through Alembic migrations. If a v1.0 database already exists, perform a controlled data migration rather than deleting or recreating existing QR records.

DB-001: `tag_pairs` is the authoritative owner and activation entity.

DB-002: `qr_codes` remains the authoritative public token and per-tag state entity.

DB-003: The activation credential belongs to `tag_pairs`, not to individual QR records.

DB-004: Both child tags must reference the same pair and batch.

DB-005: Pair-level ownership changes must update both child tags atomically, or preferably derive child ownership from the pair to avoid duplicated owner state.

DB-006: Existing `qr_activation_credentials.qr_id` must be replaced by `pair_id`.

## 19.2 New `tag_pairs` table

| Column             | PostgreSQL type | Constraints / meaning       |
| ------------------ | --------------- | --------------------------- |
| `id`               | uuid            | PK                          |
| `pair_reference`   | varchar(40)     | NN, UQ, printed Pair ID     |
| `batch_id`         | uuid            | NN, FK → qr_batches.id      |
| `tag_id_lost`      | uuid            | NN, FK → qr_codes.id, UQ    |
| `tag_id_ice`       | uuid            | NN, FK → qr_codes.id, UQ    |
| `owner_user_id`    | uuid            | Nullable FK → auth.users.id |
| `inventory_status` | varchar(25)     | NN                          |
| `ownership_status` | varchar(25)     | NN                          |
| `activated_at`     | timestamptz     | Nullable                    |
| `revoked_at`       | timestamptz     | Nullable                    |
| `created_at`       | timestamptz     | NN                          |
| `updated_at`       | timestamptz     | NN                          |

Required checks:

- `tag_id_lost <> tag_id_ice`.
- Both tags must be unique across all pairs, including cross-role use.
- Both child tags must belong to the same batch.
- The lost tag must have `tag_type = 'lost'`.
- The ICE tag must have `tag_type = 'ice'`.
- An activated pair must have an owner.
- A revoked pair cannot be reactivated.

Implementation detail: Two individually unique columns do not, by themselves, prevent the same QR ID appearing as Tag A in one pair and Tag B in another. Enforce global child membership with a single `qr_codes.pair_id` relationship and a unique `(pair_id, tag_type)` constraint, or a dedicated membership table.

Recommended canonical model: Store `pair_id` and `tag_type` in `qr_codes`. Treat `tag_id_lost` and `tag_id_ice` as pair-level references maintained by deferred integrity checks or a database view. This avoids contradictory membership data.

## 19.3 Revised `qr_codes`

Add:

| Column          | Type        | Constraint                             |
| --------------- | ----------- | -------------------------------------- |
| `pair_id`       | uuid        | NN, FK → tag_pairs.id                  |
| `tag_type`      | varchar(10) | NN, `lost` or `ice`                    |
| `public_status` | varchar(25) | Existing, independently configurable   |
| `mode`          | varchar(20) | Existing, subject to tag-purpose rules |

Add `UNIQUE(pair_id, tag_type)`.

Remove `owner_user_id` as the authoritative ownership source. Owner authorization is resolved through `tag_pairs.owner_user_id`.

Keep `public_token` and `serial_number` individually unique.

### Circular foreign key consideration

Because `tag_pairs` references two `qr_codes` rows while those rows also reference the pair, creation requires a controlled transaction with deferred constraints.

A simpler alternative is to avoid storing the two child IDs directly and derive them through `(pair_id, tag_type)`. This is the recommended implementation for the solo-developer MVP. A database view can expose `tag_id_lost` and `tag_id_ice` to administration and reporting.

## 19.4 Revised `qr_activation_credentials`

| Column                 | Type        | Constraint            |
| ---------------------- | ----------- | --------------------- |
| `pair_id`              | uuid        | PK, FK → tag_pairs.id |
| `secret_verifier`      | bytea       | NN                    |
| `verifier_key_version` | smallint    | NN                    |
| `credential_status`    | varchar(20) | NN                    |
| `failed_attempts`      | integer     | NN, default 0         |
| `locked_until`         | timestamptz | Nullable              |
| `consumed_at`          | timestamptz | Nullable              |
| `rotated_at`           | timestamptz | Nullable              |

The activation secret must never be duplicated into the two QR records.

## 19.5 Revised finder messages

Add the following fields to `finder_messages`:

| Column                | PostgreSQL type | Constraint                      |
| --------------------- | --------------- | ------------------------------- |
| `location_latitude`   | numeric(9,6)    | Nullable, −90 to 90             |
| `location_longitude`  | numeric(9,6)    | Nullable, −180 to 180           |
| `location_accuracy_m` | numeric(10,2)   | Nullable, non-negative          |
| `location_consent_at` | timestamptz     | Nullable                        |
| `location_source`     | varchar(20)     | Nullable, `browser_geolocation` |

The two coordinate fields must be present together or both null.

If coordinates are present, `location_consent_at` must also be present.

Because precise location is sensitive, the stronger production recommendation is to store coordinates as an encrypted structured payload, with the numeric types above representing the validated logical schema. This avoids leaving plaintext coordinates in database snapshots while preserving validation in the application layer.

## 19.6 New `tag_contact_preferences`

| Column                      | PostgreSQL type | Constraints          |
| --------------------------- | --------------- | -------------------- |
| `qr_id`                     | uuid            | PK, FK → qr_codes.id |
| `whatsapp_enabled`          | boolean         | NN, default false    |
| `whatsapp_phone_ciphertext` | bytea           | Nullable             |
| `whatsapp_consent_at`       | timestamptz     | Nullable             |
| `whatsapp_consent_version`  | varchar(30)     | Nullable             |
| `updated_at`                | timestamptz     | NN                   |

When `whatsapp_enabled = true`, a valid number and recorded disclosure consent must exist.

Phone numbers are stored encrypted, although the number is intentionally disclosed when the owner enables public WhatsApp contact.

## 19.7 Revised order allocations

Replace the QR-level allocation target:

Previous: `order_qr_allocations.qr_id`

New: `order_tag_pair_allocations.pair_id`

| Column              | Type        | Constraint              |
| ------------------- | ----------- | ----------------------- |
| `id`                | uuid        | PK                      |
| `order_item_id`     | uuid        | NN, FK → order_items.id |
| `pair_id`           | uuid        | NN, FK → tag_pairs.id   |
| `allocation_status` | varchar(20) | NN                      |
| `allocated_at`      | timestamptz | NN                      |
| `released_at`       | timestamptz | Nullable                |

Enforce no more than one active allocation per pair with a partial unique index.

## 19.8 Revised ERD

\#chatgpt-mermaid-\_r_20p\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_20p\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_20p\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_20p\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_20p\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20p\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_20p\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_20p\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_20p\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_20p\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_20p\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_20p\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20p\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_20p\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_20p\_ p{margin:0;}#chatgpt-mermaid-\_r_20p\_ .entityBox{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_20p\_ .relationshipLabelBox{fill:rgb(48, 48, 48);opacity:0.7;background-color:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_20p\_ .relationshipLabelBox rect{opacity:0.5;}#chatgpt-mermaid-\_r_20p\_ .labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-\_r_20p\_ .edgeLabel{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_20p\_ .edgeLabel .label rect{fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_20p\_ .edgeLabel .label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20p\_ .edgeLabel .label{fill:rgb(31, 78, 148);font-size:14px;}#chatgpt-mermaid-\_r_20p\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_20p\_ .edge-pattern-dashed{stroke-dasharray:8,8;}#chatgpt-mermaid-\_r_20p\_ .node rect,#chatgpt-mermaid-\_r_20p\_ .node circle,#chatgpt-mermaid-\_r_20p\_ .node ellipse,#chatgpt-mermaid-\_r_20p\_ .node polygon{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_20p\_ .relationshipLine{stroke:rgb(175, 175, 175);stroke-width:1px;fill:none;}#chatgpt-mermaid-\_r_20p\_ .marker{fill:none!important;stroke:rgb(175, 175, 175)!important;stroke-width:1;}#chatgpt-mermaid-\_r_20p\_ [data-look=neo].labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-\_r_20p\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_20p\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_20p\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_20p\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_20p\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20p\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_20p\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_20p\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}AUTH_USERSTAG_PAIRSuuididPKstringpair_referenceUKuuidbatch_idFKuuidowner_user_idFKstringownership_statusQR_BATCHESQR_CODESuuididPKuuidpair_idFKstringtag_typestringpublic_tokenUKstringpublic_statusQR_ACTIVATION_CREDENTIALSuuidpair_idPKbyteasecret_verifierstringcredential_statusORDER_TAG_PAIR_ALLOCATIONSORDER_ITEMSITEMSPUBLIC_EMERGENCY_INFOEMERGENCY_CONTACTSTAG_CONTACT_PREFERENCESuuidqr_idPKbooleanwhatsapp_enabledbyteawhatsapp_phone_ciphertextFINDER_MESSAGESuuididPKuuidqr_idFKdecimallocation_latitudedecimallocation_longitudetimestamplocation_consent_atNOTIFICATION_OUTBOXownsproducescontainssecuresallocatedcontainsidentifiespublisheslistsconfiguresreceivestriggers

The relationship `TAG_PAIRS ||--|{ QR_CODES` represents two child records, with exactly one of each tag type enforced through database constraints and activation validation.

## 19.9 Data retention

- Finder location: delete with the corresponding finder message, proposed maximum 180 days.
- WhatsApp number: retain while configured; erase when removed or when the account deletion workflow completes.
- Pair ownership audit: retain according to the approved security policy.
- Consumed activation secret: remove its verifier when no longer needed for legitimate security or recovery purposes.
- Former owner emergency information: remove or unpublish during transfer before the recipient gains access.

# Revised Section 20 — REST API Contract

All existing v1.0 API conventions remain applicable.

## 20.1 Paired activation

Replace:

`POST /api/v1/me/qr/activations`

with:

`POST /api/v1/me/tag-pairs/activations`

Request schema:

```
{
  "pair_reference": "SR-P-00001234",
  "activation_secret": "PRIVATE-ACTIVATION-SECRET",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
}
```

Successful response: `201 Created`.

```
{
  "pair_id": "7a9e6c3d-0000-4000-8000-000000000001",
  "status": "activated",
  "tags": [
    {
      "tag_type": "lost",
      "qr_id": "7a9e6c3d-0000-4000-8000-000000000002",
      "status": "active"
    },
    {
      "tag_type": "ice",
      "qr_id": "7a9e6c3d-0000-4000-8000-000000000003",
      "status": "active"
    }
  ]
}
```

Authorization: verified customer JWT and valid purchase entitlement.

Errors: 401, 403, 409, 422, 429, 503.

Idempotency: mandatory.

## 20.2 Additional API endpoints

| Method | Route                                | Auth           | Purpose                              | Success |
| ------ | ------------------------------------ | -------------- | ------------------------------------ | ------- |
| GET    | `/me/tag-pairs`                      | Customer       | List owned kits                      | 200     |
| GET    | `/me/tag-pairs/{id}`                 | Owner          | Pair and child details               | 200     |
| POST   | `/me/tag-pairs/activations`          | Verified owner | Activate both tags                   | 201     |
| GET    | `/me/qr/{id}/contact-preferences`    | Owner          | WhatsApp settings                    | 200     |
| PUT    | `/me/qr/{id}/contact-preferences`    | Owner          | Set WhatsApp consent and number      | 200     |
| POST   | `/public/qr/{token}/contact-reveals` | Anonymous      | Reveal an ICE contact                | 200     |
| POST   | `/public/qr/{token}/messages`        | Anonymous      | Finder submission, optional location | 202     |
| GET    | `/admin/tag-pairs`                   | Admin          | Search paired inventory              | 200     |
| GET    | `/admin/tag-pairs/{id}`              | Admin          | Pair inventory details               | 200     |
| POST   | `/admin/tag-pairs/{id}/suspend`      | Admin          | Suspend pair after review            | 200     |

## 20.3 WhatsApp preference request

`PUT /api/v1/me/qr/{id}/contact-preferences`

```
{
  "whatsapp_enabled": true,
  "whatsapp_phone": "+923001234567",
  "public_disclosure_consent": true
}
```

Rules:

- Owner authorization required.
- QR must be eligible for lost-item messaging.
- Consent must be true when enabling.
- A number must normalize to a valid international WhatsApp-compatible format.
- Disabling does not require resubmitting the number.
- The backend must never interpret enabling WhatsApp as consent to publish other account contact details.

## 20.4 Emergency contact reveal request

`POST /api/v1/public/qr/{token}/contact-reveals`

Request:

```
{
  "contact_id": "550e8400-e29b-41d4-a716-446655440000",
  "turnstile_token": null
}
```

Response:

```
{
  "phone": "+923001234567",
  "tel_uri": "tel:+923001234567"
}
```

The endpoint must return only contacts explicitly published on the active QR. It must not permit arbitrary contact-ID enumeration across QR profiles.

Rate limiting: per QR, per IP, and risk-based challenge.

No authenticated account required.

## 20.5 Finder submission with location

The existing finder submission schema gains:

```
{
  "location": {
    "latitude": 31.5204,
    "longitude": 74.3587,
    "accuracy_m": 25,
    "consent_accepted": true
  }
}
```

The `location` object is optional. If provided, both coordinates and explicit consent are required.

No separate server endpoint is required for obtaining browser location; the browser obtains it locally after permission and sends it only with the finder submission.

## 20.6 Public WhatsApp link contract

The public profile response may include a `whatsapp_contact` object only when the owner enables it.

For better control over automated harvesting, do not include the full WhatsApp URL in the initial server-rendered HTML. A user-initiated protected endpoint may provide the destination.

This reduces casual scraping but cannot conceal the number from a finder who legitimately opens the link.

# Revised Section 21 — Security and Privacy

## 21.1 Additional security requirements

| ID      | Requirement                                                                                         |
| ------- | --------------------------------------------------------------------------------------------------- |
| SEC-048 | Pair activation must be atomic and enforce common ownership                                         |
| SEC-049 | The activation secret must be independent of both public QR tokens                                  |
| SEC-050 | Public WhatsApp contact requires explicit, recorded disclosure consent                              |
| SEC-051 | WhatsApp phone numbers must not be returned when the feature is disabled                            |
| SEC-052 | Browser geolocation must be optional and explicitly initiated                                       |
| SEC-053 | Precise finder coordinates must be encrypted or equivalently protected at rest                      |
| SEC-054 | Location must not be sent to analytics or ordinary application logs                                 |
| SEC-055 | Public ICE contact numbers must be absent from initial HTML and metadata                            |
| SEC-056 | Contact reveal endpoints require rate limiting and adaptive bot protection                          |
| SEC-057 | Emergency contact availability must have a documented Turnstile-failure policy                      |
| SEC-058 | Pair and child-tag membership must be protected by database integrity constraints                   |
| SEC-059 | Pair ownership transfers must not expose previous owner data                                        |
| SEC-060 | Activation print exports must be restricted, encrypted, and audited                                 |
| SEC-061 | QR print QA must verify that public QR URLs and private activation credentials are correctly paired |
| SEC-062 | Bilingual security notices must convey equivalent meaning in Urdu and English                       |

## 21.2 New privacy disclosures

The Privacy Policy must explicitly explain:

WhatsApp: Enabling direct chat makes the selected WhatsApp number available to people accessing the tag's contact feature. SafeReturn does not control external WhatsApp conversations.

Geolocation: The finder voluntarily shares a one-time browser location. It is not continuous tracking and may be inaccurate.

Google Maps: Opening the location link transfers the submitted coordinates to Google.

Emergency contacts: Published numbers are intentionally available to people who scan the ICE tag. Anti-harvesting controls reduce automated collection but cannot guarantee secrecy.

Bilingual consent: Consent text must be understandable in both languages, with no materially weaker explanation in Urdu.

# Revised Section 23 — Physical QR Product Requirements

## 23.1 Updated specifications

The following supersede PHY-005 and PHY-006 from v1.0.

| ID      | Mandatory specification                                                                                |
| ------- | ------------------------------------------------------------------------------------------------------ |
| PHY-005 | Indoor QR artwork must measure at least 30 × 30 mm, including the quiet zone                           |
| PHY-006 | Outdoor and helmet QR artwork must measure at least 35 × 35 mm, including the quiet zone               |
| PHY-016 | QR encoding must use Error Correction Level Q (approximately 25%) or M (approximately 15%)             |
| PHY-017 | Every QR must have an unobstructed white quiet zone at least four modules wide on all sides            |
| PHY-018 | QR foreground/background contrast must remain sufficient after printing and lamination                 |
| PHY-019 | Each kit must contain both distinct tags and one matching private activation credential                |
| PHY-020 | Both tags and packaging must include bilingual Urdu/English labeling                                   |
| PHY-021 | Printed public URLs must contain no activation secrets or personal information                         |
| PHY-022 | Scratch-off activation concealment must pass local durability QA before use                            |
| PHY-023 | If scratch-off concealment fails QA, use an opaque tamper-evident sealed sleeve or peel-and-seal pouch |
| PHY-024 | A package with a visibly exposed or compromised activation secret must not be sold                     |
| PHY-025 | The two QR tags must be individually scanned and verified before packing                               |
| PHY-026 | Physical labels must visibly distinguish lost-item and ICE functions                                   |

## 23.2 Module density and scan quality

QR module size is determined by the encoded URL length, error correction level, and QR version.

A 35 mm sticker does not automatically guarantee readability if the encoded URL is excessively long.

Therefore:

- Keep the public domain and token representation as short as practical without sacrificing token entropy.
- Generate QR codes using Segno.
- Calculate the selected QR version and physical module size before approving print artwork.
- Include the four-module quiet zone within the specified overall dimensions.
- Test the exact production artwork rather than relying on QR generator previews.
- Prefer Q for additional damage tolerance where print density remains acceptable; use M where readability and module size testing justify it.

The 15% and 25% figures describe approximate codeword recovery capacity, not a guarantee that an equivalent percentage of sticker surface may be damaged.

## 23.3 Bilingual sticker labeling

TAG A · LOST ITEM

گمشدہ چیز

Scan to Return

واپس کرنے کے لیے اسکین کریں

TAG B · ICE

ہنگامی رابطہ

Scan for Emergency Contact

ہنگامی رابطے کے لیے اسکین کریں

Conceptual labeling mockups only. The square patterns are decorative placeholders, not functioning QR codes or print-ready artwork.

Bilingual text must not encroach on the QR quiet zone. If the minimum sticker dimensions cannot accommodate legible bilingual labeling and the required QR artwork, increase the overall label dimensions.

## 23.4 Packaging quality assurance

A kit passes packaging QA only when:

1. Tag A scans to its designated lost-item URL.
2. Tag B scans to its designated ICE URL.
3. Both tags resolve to the correct Pair ID internally.
4. The private activation credential matches the pair.
5. The activation credential is not visible through the packaging.
6. Tamper-evident sealing is intact.
7. Urdu and English instructions are legible.
8. The printed official domain is correct.
9. Both QR codes pass the scan test matrix.
10. Batch and QA results are recorded.

# Revised Section 25 — Testing and Acceptance Criteria

The following tests are added to the v1.0 testing strategy.

| Test ID | Test                       | Pass condition                                         |
| ------- | -------------------------- | ------------------------------------------------------ |
| AC-056  | Pair integrity             | Exactly one lost tag and one ICE tag per pair          |
| AC-057  | Pair activation rollback   | Neither tag activates if either fails validation       |
| AC-058  | Cross-role tag duplication | Database rejects duplicate membership                  |
| AC-059  | Bilingual physical label   | Both languages legible on production sample            |
| AC-060  | Urdu finder form           | Urdu-speaking participant completes without assistance |
| AC-061  | WhatsApp disabled          | No public WhatsApp number or button exposed            |
| AC-062  | WhatsApp enabled           | Valid click-to-chat destination after consent          |
| AC-063  | Location permission denied | Finder can submit normally                             |
| AC-064  | Location consent withdrawn | No coordinates stored                                  |
| AC-065  | ICE initial DOM inspection | No published phone number in HTML or hydration data    |
| AC-066  | ICE protected reveal       | Legitimate visitor can reveal and call                 |
| AC-067  | Turnstile unavailable      | Documented emergency fallback works                    |
| AC-068  | Indoor physical scan       | 30 mm QR meets pilot scan criteria                     |
| AC-069  | Outdoor physical scan      | 35 mm QR meets pilot scan criteria                     |
| AC-070  | Packaging seal test        | Credential concealed and tamper evidence intact        |

# Revised Section 26 — MVP Prioritization

## Updated P0 scope

The six requested features are included in P0, with these boundaries:

- Bilingual Urdu/English is mandatory for physical labels, packaging, public QR pages, finder forms, emergency pages, and their validation messages. Full bilingual administration remains P1.
- WhatsApp is an opt-in click-to-chat link, not automated WhatsApp messaging.
- A paired kit is the mandatory physical product structure.
- Geolocation is optional and one-time, not continuous tracking.
- ICE number reveal protection is mandatory, with emergency availability safeguards.
- Revised print and packaging specifications are mandatory.

Impact: The new requirements increase implementation and QA complexity. The 14–18-week v1.0 estimate should be revised to approximately 17–21 part-time weeks, subject to supplier testing and developer availability.

# Revised Section 27 — Development Roadmap

| Week  | Revised milestone                                           |
| ----- | ----------------------------------------------------------- |
| 1–2   | Approve paired-kit rules, bilingual UX, privacy disclosures |
| 3–4   | Schema, Pair ID design, activation transaction              |
| 5–6   | Authentication, order entitlement, QR generation            |
| 7–8   | Paired inventory, print exports, activation                 |
| 9–10  | Bilingual public pages and emergency contact reveal         |
| 11–12 | Finder form, geolocation, WhatsApp preference               |
| 13–14 | Resend outbox, customer dashboard, admin operations         |
| 15–16 | Checkout, manual payment reconciliation, fulfillment        |
| 17–18 | Security, accessibility, localization, integration tests    |
| 19    | Physical printing, packaging and QA                         |
| 20    | Controlled Lahore pilot                                     |
| 21    | Defect correction and stabilization                         |

Critical dependencies include finishing the paired schema before activation development and finalizing bilingual print layouts before placing a production order.

# Revised Section 29 — Lahore Pilot Validation

The pilot must now validate not only purchase intent but also whether the paired product makes sense to customers.

Additional hypotheses:

- Customers understand why two distinct QR tags are included.
- Urdu instructions increase comprehension for finders.
- Customers are willing to enable WhatsApp after understanding number disclosure.
- Finders understand that location sharing is optional.
- ICE phone reveal does not introduce unacceptable emergency delays.
- Both physical QR formats remain scannable after local outdoor use.

Recommended pilot tests include Urdu-speaking finders, motorcycle owners, helmet users, and customers unfamiliar with QR-based identification.

The paired-kit manufacturing cost must replace the single-sticker assumption in Section 28. The previous PKR 350 price and PKR 90 variable-cost scenario are no longer reliable planning defaults until two-tag printing, activation inserts, packaging, and QA costs are estimated.

# Revised Section 33 — Decision Register

## Proposed founder approvals

## PRD v1.1 approval register

Select your decisions to prepare the implementation baseline.

DEC-009 — Paired kit as the only P0 product

Approve: one kit, two tags

Request alternative packaging model

DEC-010 — Tag purpose and modes

Tag A lost, Tag B ICE; fixed P0 roles

Allow combined mode on both tags at launch

DEC-011 — WhatsApp number disclosure

Approve explicit opt-in with warning

Postpone WhatsApp to P1

DEC-012 — Emergency phone reveal protection

Approve adaptive Turnstile with emergency fallback

Require Turnstile on every reveal, accepting outage risk

DEC-013 — Finder location retention

Delete with message at 180 days

Use shorter 30-day retention

DEC-014 — Bilingual scope

Public pages + physical products in P0

Entire website including admin in P0

DEC-015 — Activation packaging

Scratch-off only if QA passes; otherwise sealed pouch

Use sealed pouch from the beginning

DEC-016 — QR print error correction

Q preferred, M permitted after scan QA

Q only

Submit founder decisions&#x20;

## Updated MVP build checklist

PRD v1.1 change implementation

0/16

Finalize paired-kit data model and migration

Implement atomic two-tag activation

Update order allocation to use Pair IDs

Create Urdu/English translation dictionaries

Implement bilingual public QR and finder pages

Design bilingual physical sticker and packaging artwork

Implement opt-in WhatsApp contact preferences

Implement optional finder geolocation and consent

Update finder schema and email location links

Implement protected ICE contact reveal endpoint

Test Turnstile outage fallback for emergency contacts

Implement 30 mm and 35 mm print QA

Test scratch-off or tamper-evident packaging

Run pair ownership, privacy, and concurrency tests

Recalculate paired-kit unit economics

Conduct Lahore bilingual pilot

&#x20;Copy updated checklist

PRD v1.1 conclusion: SafeReturn is now specified around a paired physical kit, bilingual public access, optional direct WhatsApp communication, consent-based finder geolocation, protected ICE contact disclosure, and stricter print QA.

The most important remaining approvals are the exact tag-mode policy, acceptable emergency phone-reveal friction, and the paired-kit selling price. Once those are settled, this amendment can be consolidated with the unchanged v1.0 requirements into a single version-controlled implementation baseline.