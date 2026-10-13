# SafeReturn — Physical Product & Fulfillment Standard Operating Procedure (SOP)

**Document:** SR-SOP-009 · **Version:** 1.2 draft · **Revision:** 12 October 2026  
**Market:** Lahore/Pakistan controlled pilot · **Repository target:** `docs/10-physical-product-sop.md`  
**Owner:** Operations lead / founder · **Reviewers:** Print/QA, finance, engineering, security/privacy  
**Status:** Proposed operating specification; not evidence of an operational production facility or of executed tests.

> **Reading rule.** Part A is the controlling **v1.2** amendment. Part B reproduces the uploaded original **v1.1 SOP** without removing its unaffected operational detail. Wherever Part B assumes a fixed paired sticker quantity, outdated checkout allocation timing, unbranded QR, or differently stored file, **Part A overrides Part B**. No production configuration, vendor suitability, legal retention schedule, printer calibration, actual price, or final dimension beyond existing minimums is claimed verified.

## Part A — v1.2 production and fulfillment contract

### A0. Authority, terminology, and boundaries

Source hierarchy: Product Requirements 01 v1.2 → approved founder ADRs → Technical Design 02 v1.2 → Database Design 03 v1.2 → API Contract 04 v1.2 → Agent Rules 05 v1.2 → Plan 06 v1.2 → Security 07 v1.2 → Test Plan 08 v1.2 → Operations Runbook 09 v1.2 → this physical operating procedure. Any unresolved naming conflict must be recorded in an ADR and reconciled before implementation; prose or illustrative code here is not permission to create unreviewed routes or tables.

**Terms.** A *pair* is one sellable/ownable identity unit with one Pair ID, two current distinct QR identities (`lost` and `ice`), and one independent activation secret or verified entitlement. A *QR identity* is its immutable public URL while current. A *physical copy* is a label, sticker, keychain print, or badge artwork showing an existing identity; repeated copies share its destination/profile. A *product* is the sellable catalog item; a *variant* fixes material, size and production constraints; an *order line* snapshots its purchased identity, name, variant, quantity, price and QR use. *Ready to Ship* means confirmed payment, final allocation, successful print artifact generation, and required pre-shipping controls—**not** permission to dispatch without physical QA. The *original v1.1 SOP* is retained for unchanged supplier, packing, fraud and incident controls.

**Launch scope:** Stickers are the P0 physical product; the catalog and fulfillment model accommodate future QR keychains, bag tags, children's badges and wearable/elderly ID badges, but these cannot be sold/printed until relevant template, manufacturing, safety, privacy, QA and shipping procedures have been approved. A reusable QR on a future product creates no new QR token, and a new identity requires a complete new pair. Each owner can have many pairs with independently editable Lost and ICE public profiles; printed copies of the *same* tag share its profile.

### A1. Non-negotiable physical invariants

| ID | Requirement | Production proof |
|---|---|---|
| SOP12-01 | Exactly two distinct current public QR tokens per newly issued pair: Lost and ICE | Pair manifest + DB identity check |
| SOP12-02 | 3 Lost + 2 ICE means five print occurrences, **two** URL/token identities, **one** pair, not five identities | Manifest count + PDF render extraction + physical scan |
| SOP12-03 | All printed copies of a QR point to the same independent, editable per-tag profile | Scan same URL from each copy; check profile resolution |
| SOP12-04 | Centered approved SafeReturn logo may not reduce scan reliability or corrupt code | Print-size/device/material scan matrix |
| SOP12-05 | Four-module white quiet zone, full symbol minimum 30×30 mm indoors and 35×35 mm outdoors until a reviewed, tested variation is approved | Dimension/contrast measurements |
| SOP12-06 | Private print artifacts and payment evidence reside in separate **private Supabase Storage** buckets; Cloudinary is for **public product photos/marketing imagery only** in P0 | Bucket permission/URL review |
| SOP12-07 | A QR public URL / centered logo does **not** prove ownership or authorize activation | Activation test; concealed credential custody |
| SOP12-08 | No printing/shipping on submitted screenshot alone; independent payment settlement required | Finance approval evidence |
| SOP12-09 | Allocation and shipping prevent double-sold pairs and cross-owner QR reuse | Order/pair matching check + DB transaction tests |
| SOP12-10 | Artwork orders Lost first, ICE second, within each using size/template grouping; quantities are exact | Render manifest audit and visual verification |
| SOP12-11 | No health/private ICE notes, finder details, payment data or full emergency phones embedded into visible QR artwork | QR payload/print-text inspection |
| SOP12-12 | Credential is concealed separately; never exposed as an ordinary printed label, in browser response, in logs or in a publicly accessible artifact | Packaging inspection and secret access audit |
| SOP12-13 | Actual printed shipment requires independent/approved per-pair QA and traceable packaging | `pair_print_qa` and fulfillment record |
| SOP12-14 | Temporary files are deleted only under approved retention/hold rules; permanent order/identity/copy-count/audit records remain | Storage deletion job and database reconciliation |
| SOP12-15 | New products remain behind approved feature flags and supplier/template qualification | Published catalog state and release record |

### A2. Responsibilities and separation of duties

| Role | Permitted actions | Forbidden without additional authorization |
|---|---|---|
| Admin inventor/operations | Generate *N* pairs, view counts, reserve/allocate only through approved workflow, release stock after QA | Forging settlement, reusing sold pair, exposing secrets |
| Finance reviewer (MFA) | Verify actual bank/Raast settlement using independent channel, reject/freeze suspicious transactions, audit | Approve based on screenshot alone; edit printed URL |
| Renderer/worker (service identity) | Read frozen print manifest, render deterministic PDF, upload private artifact, record checksum | Invent URL/extra pair; write payment status; publish object |
| Authorized print operator | Obtain short-lived authorized download, print at actual size, cut, label, reconcile physical copies | Modify token/Pair ID, use public PDF links, print stale superseded versions |
| QA inspector | Inspect layout, scan, adhesion/durability, make accept/reject record | Approve unexplained mismatched child identity or credential exposure |
| Packing/dispatch | Match manifest, assemble correct pair/copies, conceal insert, update carrier state | Mark delivered without evidence; print over unverified payment |
| Support/security | Handle returns, reprint/dispute holds, approve exceptional revocation | Quietly transfer a child QR apart from its pair |
| Customer | Select product/size/number of Lost and ICE physical copies, manage owned per-tag profiles | Claim another account's QR from a public URL |

For pilot-scale staff overlap, document a compensating second-person spot check and audit; do not claim independent verification where there is none. All sensitive admin actions require authorized role and recorded actor/time/reason.

### A3. Product, variant, and order snapshot rules

1. P0 public catalog offers **approved sticker variants only** (sizes, substrate, indoor/outdoor suitability, price). A variant must have a stable SKU and approved `print_template_version` and cut/bleed/margin configuration; unqualified variants are unpublished.
2. For a new pair, order configuration specifies Lost copy lines by approved size and ICE copy lines by approved size. A mixed-size checkout is allowed; copy counts are nonnegative bounded integers, with at least one of each required for newly sold paired kit unless a separately approved exception exists.
3. Backend quote establishes shipping and final PKR total. On confirmation, immutable order line snapshots retain product/variant IDs and purchased names, SKUs, sizes/materials, currency, unit/final prices, counts, tag-role mapping, QR reuse/new-pair selection and template revision. Later catalog edits must not mutate past orders.
4. A repeat purchase may **reuse an existing authorized tag identity** on a new physical item only if user owns the pair at order submission **and again immediately before printing**. Existing-QR reuse has no new inventory-pair reservation; it still has an order, line and physical production job.
5. Choosing a new QR identity on any future item creates a **complete new Lost+ICE pair**. Physical packaging must explain both identities and their activation entitlement even if a particular item displays only one of the pair's two URLs; any exception to bundled physical delivery requires founder/security approval and must not silently break the paired model.
6. An admin product-create form must not bypass manufacturing qualification: `draft → tested/approved → published` with separate product photos in Cloudinary and immutable print-template versioning. Disabling the product should preserve prior orders and reprint reproducibility.

**Worked example (illustrative, not commercial prices):** An order for 3 Lost small stickers and 2 ICE medium stickers contains a single new Pair ID and two current QR URLs. The PDF must have exactly 3 prints of the Lost URL followed by exactly 2 prints of the ICE URL, with their specified sizes. A copy counts as printed artwork, *not* as a new `qr_codes` record. The system should never require a staff member to manually copy and paste a QR multiple times.

### A4. Pair batch generation and available stock

**Trigger:** Inventory dashboard warns low stock using configured threshold. Admin selects **Create New QRs** and enters number **N** of complete pairs, not number of single tags or copies. Check input max/authorization/capacity and record an idempotent batch request. Generate N Pair IDs, two high-entropy current public QR tokens and one separately protected activation credential verifier per pair. Each visible symbol encodes the exact approved canonical-domain `/q/{token}` URL. For each batch, record staff actor, generation time, secure batch reference, token/artwork/template revisions, quantity created, exceptions and QA/release status.

**Stock states:** generated → pending QA → QA approved and available → reserved (exclusive temporary order) → allocated (paid/owned) → printed/packed/shipped as separate fulfillment states; quarantine/revoked/reissued are controlled exceptional branches. A pair may not simultaneously be reserved for competing orders, and a payment-under-review order must not lose entitlement solely due to an unexamined short timeout. Reconcile expired holds with submitted payments prior to release, as required by Documents 02–04. Never allocate a failed-QA, revoked, already sold/activated or otherwise blocked pair.

**Batch balancing equation:** created pairs = available + currently reserved + allocated/sold + held/quarantined + revoked/retired + documented corrections, with mutually exclusive category definitions. Copy quantities do **not** enter the unique-pair stock balance. Daily reconciliation must identify orphan tags, duplicated current child types, missing activation verifiers, reservation races, unreviewed exceptions and negative inventory.

### A5. QR generation, logo placement, and geometry

1. Resolve correct immutable token and canonical HTTPS public URL; don't place raw activation secret, PII, phone, medical notes, payment reference or coordinates in QR payload. Validate that the route exists and unactivated QR displays the safe Activate QR flow, not an unexplained error.
2. Use a versioned QR matrix generator (Segno proposed). Encode with minimum supported density and documented ECC. Baseline v1.1 ECC **M or Q** applies unless centered-logo tests justify a higher validated setting (such as H), a smaller logo or redesign; do not blindly assert that ECC H guarantees readability.
3. Preserve **four complete QR modules of plain white quiet zone on every side**. The quiet zone is part of the measured full symbol size, including the 30×30 mm indoor/35×35 mm outdoor minimum. Logo backing must not enter quiet zone, erase finder/timing/alignment patterns or consume an untested fraction of modules.
4. Render small approved square SafeReturn logo centrally with transparent-safe or bounded white backing; test against long canonical URLs, multiple printers/materials, glossy reflections, lamination, dirt and actual camera devices. Logo **does not authenticate the URL**; verified domain and server records are the trust anchor.
5. Geometry formula: let QR data matrix have `m` modules per side, each printed at `p` mm. Total with mandatory 4-module quiet zone each side is `(m + 8) × p` mm. If the approved full symbol dimension is `S`, `p = S / (m + 8)`; reject layouts with insufficient physical module pitch or print resolution. Do not scale the symbol non-uniformly.
6. Use high-contrast dark modules/light ground and a solid quiet-zone ground, preferably vector paths. Use actual printer output calibration (not screen pixels) and check bilingual text legibility independently of the scannable symbol.
7. Physical variants below the current tested minimum shall remain unavailable; names such as “Small” are marketing labels and never permission to print an undersized QR. Extra outdoor durability requirements apply where exposure is expected.
8. QR visual appearance, source brand logo, generator/ECC version, URL host, target physical size, label template, and checksum must be reproducibly traceable to a versioned production manifest.

**Physical release tests:** 100% scan/identity check of produced current child tags at batch production as required by existing SOP; device/substrate/lighting sampling supplements, not replaces, the required pair match and scan tests. Any failure of a primary scan is a stop and rework signal, not a cosmetic defect.

### A6. Compact PDF generation and printable manifest

**Preconditions:** Independent verified payment; resolved stable order snapshot; final exclusive pair allocation for newly purchased pair; ownership revalidated for reused QR; approved current tokens; approved products/templates; no security/QA hold; idempotent print-job creation keyed to order and revision. Job runs asynchronously without requiring an active admin browser tab.

**Required document structure:**

- Cover/reference (optional, minimal): non-sensitive order ID, internal batch/job ID, count and size summary. No customer medical or payment account details.
- **Section 1 — LOST:** All Lost physical occurrences; group by approved size/variant while preserving their source order line and tag identity. Generate exactly `copies` occurrences of that **same** URL and place requested size label/cut guidance.
- **Section 2 — EMERGENCY/ICE:** All ICE physical occurrences, same size/count rules, distinct from Lost URL. Show English/Urdu purpose markings.
- **Concealed activation material:** Treat separately from visible tags in a restricted manufacturing workflow; do not embed raw credentials in ordinary print-job PDFs or expose through the Ready to Ship file without an independently approved encrypted/separated process.
- Page break/divider and cut registration keep physical items separable without sacrificing quiet zone. Templates use configured real page dimensions, printable region, margins, bleed, line widths and production tolerances. Do not let clip/overflow truncate any symbol.

**PDF production and storage policy:** Prefer SVG/vector QR modules, reuse identical symbol/logo objects within the PDF when renderer supports it, embed logo once or deduplicate, subset approved fonts with Urdu shaping verified, avoid full-page rasterized QR images, compress streams and omit bulky/unnecessary metadata. Optimize for small file size **without reducing print fidelity**. No hard-coded arbitrary maximum file bytes until tested; instrument byte size per copy/page/template and alert on regression. PDF is a **temporary production artifact**, never system of record. Store in dedicated private Supabase Storage bucket under opaque object key, record content type, byte count, checksum, render/template revision, timestamps, creator/authorization and retention deadline in `print_jobs` / `print_artifacts` as defined by DB/API. Browser receives no unrestricted public object URL; admin uses server-authenticated, short-lived download. Do not additionally upload sensitive print PDFs to public Cloudinary.

**Pre-download computer checks:** exact pair and child mapping, order/size snapshots, repeats and order (Lost before ICE), no collisions/quiet-zone violation, no missing bilingual glyphs, correct page/cut zones, no exposed credentials/private data, expected token host, stable PDF hash and private object ACL. Mark generation failure retriable; never create a second conflicting job on worker retries.

### A7. Physical printing, cutting, and per-copy QA

1. Staff opens **Admin → Orders Ready to Ship** with required role/MFA. Choose order and review number of pairs, product lines, sizes, Lost/ICE counts, payment confirmation, print revision, generated file checksum and approved template.
2. Download **authorized current PDF**; verify local file checksum, correct order/version and printable scale. Do not print browser-fit-to-page unless template was calibrated for it. Printer sheet/material, resolution, ink, lamination settings and labels must match the approved variant.
3. Produce one full test sheet before a run; measure at least one symbol **including** quiet zone and its physical pitch, printed logo coverage, bilingual labels, substrate strength and cut safety. Use calibrated scale references.
4. Print exactly the manifest counts. Scan every distinct token at minimum and inspect/scan each physical print according to approved per-copy sampling/risk policy; keep original v1.1 **every-pair inspection** compulsory. For very small pilot runs, 100% copies scan is recommended and should be release policy if feasible.
5. Cut along registered cut lines leaving quiet zones intact. Never trim into QR margin, scratch modules with cutters, affix stickers over edges that deform modules, or cover codes with unreadable glossy laminates.
6. Sort piles by `order_id`, `pair_id`, tag type and variant/size. Reconcile **count printed, count passed, count rejected, count reprinted, count packed** for each group. Void/destroy misprints so extra physical stock cannot circulate as authentic consumer items.
7. Quality inspector validates printed Lost URL points to Lost page and ICE to ICE page, and activation not yet claimed by unauthorized person. Unactivated pages must offer the approved activation invitation while revealing no owner private details.
8. Record printer/date/sheet lot/material lot, dimensions, scanner/device observations, inspector, pass/fail evidence, defect ID and rework disposition; do not store raw private scan URLs in ordinary logs.
9. Defects that block ship: wrong URL, incorrect tag purpose, wrong logo/domain, wrong size/copy count, clipped quiet zone, blurry/unscannable QR, exposed activation credential, stale print-job version, absent finance approval, mismatch to order, misassigned customer, or missing required packaging.

### A8. Concealed activation credential and package assembly

An order-created pair has one protected activation entitlement/verifier for both current tags. A public QR scan passes only tag/pair context across login and cannot claim the tag on its own. Purchase entitlement (verified to the authenticated buyer) or sealed valid secret is required. Any printed activation secret must be in a **separate concealed insert** or another explicitly reviewed secure procedure; public visible tags and public PDF never contain it. Only minimum-role staff may handle unsealed inserts and with audit. The insert is issued once/paired and must be matched to internal Pair ID without revealing it to unrelated staff, carrier or finder.

Packing checklist: (1) paid/authorized order, (2) exact allocated pair(s), (3) every ordered Lost/ICE occurrence, (4) correct sizes/product/variant and no damaged copies, (5) independent pair-tag URL scan evidence, (6) concealed matching credential or approved buyer-entitlement activation instructions, (7) bilingual English/Urdu handling and safety notices, (8) destination/contact confirmation, (9) tamper-evident seal and parcel ID, (10) photograph/proof metadata without readable credentials or private QR profile content. Packing must never merge stickers from different owners simply because sizes match.

Customer instructions: “Scan either tag; if not activated, choose Activate QR and sign in. SafeReturn remembers the scanned tag so you do not need to scan again. Activation requires the verified purchasing account or the concealed activation credential. Both tags in the same pair activate together, but Lost and Emergency profile details can be edited separately. All physical copies of one URL display the same profile.” Translate and human-review for English and Urdu. Never claim that scan alone provides ownership.

### A9. Ready to Ship, packing, and carrier handoff

**Workflow states (semantic; map exactly to approved DB/API values before coding):** `awaiting_payment` → `payment_under_review` → `payment_verified` → `allocated` → `print_queued` → `print_ready` → `print_qa_passed` → `packed` → `shipped` → `delivered`; exceptions include `payment_rejected`, `payment_disputed`, `print_failed`, `qa_hold`, `packing_hold`, `shipment_exception`, `return_requested`, `cancelled`. Payment, allocation, print-job and shipment are **distinct state dimensions**; do not implement one mutable all-purpose status column if DB contract separates them.

**Admin Ready to Ship view:** Show only orders eligible for production, with ID, created timestamp, verified-payment badge, product-name/variant snapshots, number of new pairs/reused QR lines, Lost count/size, ICE count/size, total physical units, artifact status/current version, permitted PDF download, QA status, packing status, destination summary and error reason. Finance proof is not exposed by default to packers. Admin can requeue failed jobs, quarantine failed artwork, request controlled reprint, record checked packing, carrier/tracking, dispatch/delivery evidence and exceptional deletion request in authorized workflows.

Dispatch: select qualified carrier; verify shipping label/contact and no exposure of emergency details; record `shipment_id`, tracking and courier handoff; communicate status to owner without sensitive content. Delivery confirmation must rely on trusted carrier signal or authorized evidence review, not guessed elapsed time. The order remains visible indefinitely as a historical order subject to approved records policy; delivery does not delete QR ownership, order lines, print counts or payment review. Track returned/damaged/lost parcels and trigger fraud/replacement holds.

### A10. Payment operations, Google Sheets and future gateway compatibility

**Today:** Checkout produces final server-calculated amount and official transfer instructions. Customer may submit sender account holder/identifier/reference and optional screenshot. The account identifier is sensitive; finance staff obtain only necessary fields. An independently verified settled bank/Raast transaction—never screenshot or customer self-attestation—changes payment status to verified. Only then are allocation/print/shipping jobs eligible. Retain failure/dispute workflow for mismatch, reversal, duplicate reference, screenshot manipulation, payment of wrong amount, no bank receipt, pending delayed settlement or suspicious payer account.

**Future:** Implement payment settlement behind provider-independent payment attempts and verified events. A new payment gateway's signed webhook/reconciliation produces the same validated `payment_verified` state as authorized manual review; its change **must not alter** immutable order IDs, product snapshots, QR identity allocations, print jobs or shipping flow. Idempotent capture/refund events must be tested; a provider switch does not retroactively approve old screenshots. Run new adapter in shadow/staging and get founder authorization before cutover.

**Reporting:** Supabase PostgreSQL remains financial system of record. Google Sheets is a **restricted, redacted, eventually consistent** finance mirror of order ID, non-sensitive payment references/amounts, review status and timestamps. A reporting outage must not block approved bank confirmation or shipping if authorized database truth is established; repair via retryable outbox and reconciliation. Never embed screenshot binaries/full account identifiers in broadly shared Sheets. The original screenshot remains only in private storage until approved retention deletion.

### A11. Storage, artifact retention, deletion and reprint

| Record/file | Location | Expected lifecycle | Must remain after object deletion? |
|---|---|---|---|
| Order and immutable product/variant/quantity snapshots | Supabase PostgreSQL | Retained under approved records policy | Yes |
| Pair ID, current/historical QR IDs and token mapping, copy use/size mapping | Supabase PostgreSQL | Durable with supported revocation/replacement history | Yes |
| Payment settlement/reviewer/provider event & audit | Supabase PostgreSQL | Retained as finance/legal policy requires | Yes |
| Payment screenshot (temporary optional evidence) | **Private Supabase Storage evidence bucket** | Retain during approved review/dispute window; legal hold blocks deletion | No raw screenshot after authorized deletion; retain approved audit/tombstone metadata |
| Production print PDF | **Private Supabase Storage print bucket** | Until verified delivery + approved grace/reprint interval (candidate 7 days; **not yet approved**) and no dispute/hold | Keep checksum, job revision, copy counts, deletion audit |
| Public catalog photographs/logo | Cloudinary (approved public media) | Product publication/asset lifecycle | Image reference/history as applicable |
| Google Sheets rows | Restricted finance mirror | Redacted reporting/reconciliation per policy | Supabase authoritative data survives any sheet purge |

**Deletion procedure:** scheduled worker identifies eligible unheld objects; verify storage key owner/order, delivery state/retention deadline, pending reprints/disputes/legal holds, and least-privilege delete authorization; delete private file; confirm provider deletion; mark DB artifact tombstone and audit idempotency/retry. If physical shipment status later changes, do not resurrect/delete financial records. Deleting the object does not mean it vanished from provider backups instantly; document backup expiry and incident legal requirements. No automatic deletion solely on payment confirmation or a customer's unverified delivery claim.

**Controlled reprint:** Authorized support/fulfillment requests reprint with reason, customer and order ownership checks, valid current QR status, freeze previous job version, regenerate from stable order/item/QR use snapshots, create new private artifact with version/checksum, apply payment/replacement exceptions policy, perform physical QA and document extra copies/charges if relevant. For revoked/replaced QR, never silently reprint obsolete tokens. If the original pair is compromised, follow approved revocation/reissue flow, not ordinary copy printing.

### A12. Exceptions, returns, replacement, privacy incidents

- **Wrong QR identity/owner on artwork:** stop printer and dispatch; quarantine all affected lots; revoke download links; freeze job; verify whether any physical tag was shipped; consider token revocation/reissue and notify security.
- **Unreadable logo-centered code:** quarantine specific template/variant/batch; inspect ECC, module pitch, quiet-zone, print process and camera matrix; correct approved template then render/version/retest.
- **Customer requests size correction after payment:** controlled amendment/requote/finance difference and snapshot revision; invalidate old PDF; no manual print substitution.
- **Duplicate reservations or wrong pair allocation:** stop fulfillment, DB transaction audit, release only after finance/ownership reconciliation and no activation/shipment.
- **Mismatched activation insert:** quarantine; destroy exposed or incorrect insert securely, reissue approved secret with audit; do not send child tags separately without recorded exception.
- **Lost or damaged parcel:** record carrier evidence, freeze disputed claims, follow return/replacement policy and credential exposure rules; do not merely print more live QR labels to unknown recipient.
- **QR copied by unauthorized party:** branded logo is not authentication. Use token and account-security response, abuse monitoring, optional approved revoke/reissue process.
- **Payment reversal or complaint:** finance block and support hold; preserve legally required evidence and prevent automatic artifact deletion until resolved.
- **Child/senior badge privacy (future):** physical outward-facing labels must not print home address, health details or contact without explicit lawful/guardian publication and risk review; public scan is governed by ICE protected reveal and Lost consent controls.

### A13. Future keychains, bag tags and wearable badges — release-gated playbooks

Future products share catalog + order + pair/QR-use machinery, not necessarily a sticker sheet template. For each additional product require an approved bill of materials; artwork safe area, scale, material, coating and engraving/UV print tests; metal/acrylic reflection testing; attachment/edge safety; age-related choking/sharpness requirements as applicable; batch/lot traceability; per-unit proof/sample; warranty/replacement and shipping packaging; customer consent/privacy notices; and a documented manufacturer file-format/hand-off contract. Keychains may need individual vector SVG/PDF cut/engrave export and supplier-specific registration; children's badges need child-safe material and minimal exposed PII; chest badges need comfort, durable attachment and protected medical-information access. None of these templates can be used in live orders until QA, tests, legal/privacy review and product feature flag approvals are recorded.

**Two different selections must be available later:** `new_pair` creates a whole new paired identity (independent profiles); `reuse_existing_qr` binds the physical new product to an already owned current QR URL (shared profile), without consuming new pair stock. The UI must explain that editing a reused tag's profile updates *all* printed products carrying that URL. Admin may offer multiple approved physical goods within one order, each with distinct SKU/name/quantity and its own QR-use mapping.

### A14. Production records, checklists and templates

#### A14.1 Batch issue record

```text
batch_reference:             [assigned]
requested_pair_count:        [N]
created_pair_count:          [N]
valid_current_lost_count:    [N]
valid_current_ice_count:     [N]
held/rejected_pair_count:    [N]
operator_id:                 [authorized staff]
canonical_domain_version:    [approved]
qr_generator/ecc_version:    [approved]
logo_and_label_version:      [approved]
QA_release_actor/time:       [record]
manifest_access_level:      restricted
```

#### A14.2 One order print/pack record

```text
order_id:                    [record]
order_snapshot_revision:     [record]
product_id/name/variant_SKU: [immutable snapshots]
new_pair_count:              [record]
reused_qr_line_count:        [record]
pair_reference(s):           [record, restricted]
lost:                        [(tag_identity, size, copies), ...]
ice:                         [(tag_identity, size, copies), ...]
expected_total_copies:       SUM(lost copies)+SUM(ice copies)
actual_passed_copies:        [record]
artifact_job/version:        [record]
PDF_bytes/checksum:          [record]
media_storage_key:           [opaque private reference]
payment_verified_by/at:      [record]
print_operator/date:         [record]
QA_actor/result/defects:     [record]
pack_actor/seal_id:          [record]
carrier/tracking:            [record]
delivery_evidence:           [record]
artifact_delete_due/hold:    [record]
```

#### A14.3 Sign-off sheet (one order)

| Checkpoint | Required sign-off |
|---|---|
| Payment verified via bank/provider, not screenshot alone | Finance |
| Order snapshot and exactly matched pair(s)/reused tag IDs | Fulfillment |
| Count, sizes, Lost-first/ICE-second PDF, current template | Print operator |
| Quiet-zone, logo, physical scanning, print readability | QA |
| Concealed activation insert correct, bilingual instructions | Packer/QA |
| Customer address and carrier handoff | Dispatch |
| Delivery independently confirmed; retention clock observed | Operations |

### A15. Security and acceptance gate matrix

| Gate | Positive and negative checks | Evidence / reference |
|---|---|---|
| Production QR batch | N pairs, 2N distinct current tags, no plaintext secrets leaked, all QA eligible before availability | DB tests + operator batch reconciliation; Doc 08 QR cases |
| Logo + print | All offered size/substrate/device combinations, quiet-zone preserved, baseline minimums and correct centered logo | Actual printed scan sheets + measured pitch; Doc 08 A4.1 and A5.1 |
| Multi-copy order | 3 Lost + 2 ICE ⇒ exactly 5 printed, 2 URL identities, 1 new pair | Print PDF checks + E2E journey SR-JOURNEY-01 |
| Independent profiles | Edit one Lost or ICE; other tags/pairs unaffected; repeated copies share profile | E2E/auth tests Doc 08 A4.3 |
| Checkout/reservation | Server quote, snapshot fields, exclusivity, delayed transfer/expiry safety, refunds | Doc 08 A4.5–A4.7 |
| Payment gate | Manual screenshot does not approve shipment; verified bank channel or valid future gateway event does | Doc 08 A4.7; Security 07 |
| Private files | No anonymous PDF/evidence access, short-lived scoped staff download, Cloudinary only public photos | Doc 08 A4.8–A4.9; Security 07 |
| Google Sheets | Failed mirror retry does not alter authoritative finance/payment decision | Doc 08 A4.10 |
| Packaging/dispatch | Exact tag/pair counts, no exposed secret, real carrier tracking and delivery evidence | Doc 08 admin/fulfillment cases + original SOP |
| Cleanup/reprint | Deletion respects hold/window, order data stays; reprint versioned, old revoked tokens excluded | Doc 08 A4.8–A4.9; Runbook 09 |
| Future product flag | Unapproved badges/keychains cannot be purchased; published approved variant yields valid product-specific print | Doc 08 A4.4; release ADR |

Stop shipment for any critical mismatch in identity, authorization, payment state, printed readability, credential security, customer destination, or required QA. Store signed test evidence before declaring the Lahore pilot ready. Tests in Document 08 are *planned* until actual execution is recorded.

### A16. Day-to-day operational schedule and troubleshooting

| Frequency/event | Operator task | Escalation |
|---|---|---|
| At admin batch creation | Verify requested count, generated pair identities, status and secure manifest | Security if duplicate/missing tags or secret mishandling |
| Daily before processing orders | Reconcile reservations vs payment review, low stock, failed jobs, available substrates | Finance for ambiguous delayed transfer |
| Each verified-paid order | Check allocation ownership, render job, output size/count, authorized download | Engineering if job failed or artifact checksum differs |
| Each print batch | Printer calibration, QR scan matrix sampling, materials/lot and reject-count reconciliation | QA hold on unreadable code or incorrect logo |
| Each parcel | Match all physical copies to pair(s) and products, seal insert and track carrier | Security if mismatched ownership/credential |
| Daily worker operation | Alert on failed print jobs, failed storage deletions, privacy export access, Sheets sync lag | Technical on-call; no silent downgrade |
| On verified delivery + approved window | Evaluate artifact cleanup with hold checks and audit | Privacy/legal for disputed/legal hold |
| Periodic review | Test reprint recovery, backup artifact metadata, supplier/label longevity, future product sample qualification | Founder release review |

**Troubleshooting:** If no PDF appears, inspect print-job status and safe error code, storage write permissions, renderer font/logo/template version and retry idempotency—not the public customer link. If PDF size grows unexpectedly, look for rasterized full-page QR copies or repeated oversized logo/font embeddings, compare per-page byte metrics, fix renderer and rerun scan QA. If QR scans to wrong page, halt and verify token-to-tag role mapping, canonical URL and manifest, not manual sticker relabeling. If a Sheets row is missing, requeue reporting sync; never re-approve payment solely to refresh the sheet. If private PDFs are exposed, revoke access and follow security incident procedure immediately.

### A17. Founder approvals and ADRs required before first real shipment

1. Final product sizes, substrates, prices, shipping rates, SKU variants, quantity limits and warehouse/print vendor selection.
2. Final controlled production host, QR logo geometry, ECC selection, physical scan pass criteria, Urdu label typography and printer resolution.
3. Payment review SLA and delayed-transfer reservation policy; manual evidence fields; eventual gateway provider and cutover acceptance.
4. Printed activation secret manufacture/containment, ownership-entitlement fallback and what packaging insert is included for a verified order.
5. Finance screenshot and PDF retention periods (including any proposed delivery-plus-7-day reprint grace), legal holds and backup-expiry expectations.
6. Catalog admin permissions, featured-product governance and future product-specific manufacturing/spec safety gates.
7. Whether per-copy 100% scan QA is mandatory pilot policy (recommended) in addition to original required per-pair 100% check.
8. Shipping provider, delivery evidence reliability, return/refund/recall policy, staff separation and facility safety.

Record a versioned ADR for each material decision before generating production print templates. Draft assumptions are not approved production settings.

### A18. Cross-document traceability and change handoff

| v1.2 requirement | Upstream references | This SOP implementation area |
|---|---|---|
| One pair, two identities, many prints | PRD 01 A2–A5; TDD 02 §§3–6; DB 03 §§5–7; API 04 §§A7–A8 | A1, A3–A6 |
| Multiple per-account independently editable QR profiles | PRD 01 extensibility; DB 03 §6; API 04 A7 | A0, A3, A8, A15 |
| Branded QR and size QA | PRD 01 A3; TDD 02 §4; Security 07; Test 08 A4.1 | A5, A7, A15 |
| Inventory/verified payment/print | PRD 01 A6–A8; DB 03 §§7–9; API 04 A8–A11; Plan 06 | A4, A6, A9–A10 |
| Storage and cleanup | DB 03 §9; Security 07; Runbook 09 §§6–7, 13–14 | A6, A11 |
| Future products / reuse | PRD 01 extensibility; TDD 02 amendment; DB 03 §§4–6; API 04 A6–A8 | A3, A13 |
| QA and launch | Test Plan 08; Runbook 09 §§19–21; original SOP Part B | A7, A14–A17 |

**Implementation boundary:** This file is a production/operations SOP and does not replace authoritative SQL migration scripts, backend OpenAPI, billing agreements, validated manufacturer artwork or the separate final UI/UX screen inventory (Document 11). Do not start Document 11 in this delivery.

---

## Part B — Archived original v1.1 Physical Product & Fulfillment SOP

The following is the complete text of the supplied v1.1 physical SOP retained for traceability and unaffected procedures. **If a statement conflicts with Part A, Part A wins.** References to fixed printed kits, original one-pair-per-quantity calculation, unchanged logo rules or former allocation/storage flows are historical, not alternative v1.2 requirements.

---

# SafeReturn — Physical Product & Fulfillment Standard Operating Procedure

**Document 9 of 10** · **Version:** v1.1-draft · **Date:** 11 October 2026  
**Proposed repository path:** `docs/10-physical-product-sop.md`  
**Market:** Lahore, Pakistan (controlled pilot)  
**Owner:** Operations lead / founder · **Reviewers:** Engineering, Security/Privacy, Finance, Print QA  
**Status:** Proposed for approval; not a claim that manufacturing, QA, or shipment has occurred.

> **Core invariant:** One sellable SafeReturn kit = **one Pair ID + two different current QR tags** (Tag A `lost`, Tag B `ice`) + **one concealed activation credential**. Never ship a partial, mismatched, already activated, unverified, or unconcealed kit.

This document operationalizes PRD v1.1 and Documents 1–8. It covers print engineering, supplier management, production manifests, batch traceability, QA, payment review, order allocation, packing, shipping, replacement, return, fraud, and Lahore pilot execution. It intentionally **does not define the complete software screen/route/navigation inventory**; that is reserved for **Document 10, the final UI/UX specification**.

## 1. Authority and document mapping

| Source | What it governs |
|---|---|
| PRD v1.1 | Paired product, English/Urdu labels, optional finder location, WhatsApp and ICE privacy, physical constraints |
| Doc 1 Technical Design §§7,11,15 | Pair generation/activation, order flow, 30/35 mm QR and ECC/quiet zone |
| Doc 2 Database Design §§5,10–11,15–16 | `qr_batches`, `tag_pairs`, `qr_codes`, `pair_activation_credentials`, `pair_print_qa`, order allocation, shipments |
| Doc 3 API Contract | Authorized batch/print/QA, payment, inventory, order, shipping, replacement endpoints |
| Doc 4 AI Agent Instructions | Scoped implementation, no production actions without permission, secrets handling |
| Doc 5 Implementation Plan | Workstream sequencing, QA and release gates |
| Doc 6 Security & Privacy | Physical token/secret custody, consent, fraud and audit requirements |
| Doc 7 Test Plan | Physical QR test cases and release evidence |
| Doc 8 Deployment Runbook | Verified production domain, secrets, backups, provider readiness and go-live |

**Conflict resolution:** The DB design's selected final child uniqueness is `(pair_id, tag_type) WHERE is_current=true`, retaining revoked historical tags. Its earlier unconditional uniqueness line is superseded. Do not create separate tag ownership or transfer a single child. If any operational step conflicts with an approved ADR, stop and obtain founder approval.

### 1.1 Defined terms

- **Pair ID / `pair_reference`:** Non-secret human-readable identity of the two-tag kit.
- **Tag A:** Lost-item recovery QR (`tag_type=lost`).
- **Tag B:** Emergency information/ICE QR (`tag_type=ice`).
- **Public token:** High-entropy URL token on a visible tag; **not** an activation credential.
- **Activation credential:** Secret issued once per pair, concealed in the packaging; one credential activates both tags atomically.
- **Artwork QR size:** Full QR symbol **including** four-module quiet zone on all sides.
- **Batch:** Group of generated pairs under `qr_batches`, with controlled manifest and QA records.
- **QA hold:** No allocation, packing, or shipment until disposition is approved.
- **Rework:** Authorized reprint/repackage with audit and new QA; never silently modify a printed QR token.
- **Release:** Human-approved inventory transition to `qa_passed` after documented acceptance.


## 2. Responsibilities, access and separation of duties

| Role | Allowed duties | Must not do |
|---|---|---|
| Founder / operations lead | Approve supplier, BOM, pilot quantity, exception policy, shipment release | Override security/privacy without decision record |
| Backend service | Generate pair IDs/tokens, create credential verifier, maintain DB transactions | Expose raw credential to public endpoints or ordinary logs |
| Print operator | Print controlled artwork and serials from authorized manifest | Edit token, domain, Pair ID or tag mode by hand |
| QA inspector | Independently scan, measure, inspect and record each pair | Approve their own undocumented exception |
| Finance reviewer | Verify settled bank/Raast transaction using trusted bank channel | Treat screenshot or AI classification as settlement proof |
| Inventory allocator | Allocate QA-approved pairs to verified orders under DB lock | Allocate unverified, reserved, rejected or active pair |
| Packer | Match physical pair, sealed insert and order; seal parcel | Open/reveal customer activation credential unnecessarily |
| Dispatch coordinator | Carrier handoff, proof of dispatch and tracking | Expose private addresses on public QR or logs |
| Support/security | Investigate disputes, revoke/reissue under approved policy | Transfer Tag A independently from Tag B |

**Least privilege:** Finance cannot silently create inventory; fulfillment cannot approve bank settlement; print staff should not receive live owner medical data, account credentials or plaintext payment proofs. Admin actions require authenticated roles and audit.

### 2.1 Two-person controls

For pilot-scale operations, separate generation/print from final QA where practical. Require two-person review for payment anomalies, manual inventory overrides, activation-secret exposure, batch reissue and disputed ownership. If one founder must perform both steps, record a documented compensating review and evidence rather than claiming independent review occurred.


## 3. Product specification and bill of materials (BOM)

### 3.1 One kit contents

| Item | Quantity | Requirement |
|---|---:|---|
| Tag A — lost item | 1 | Unique visible QR, Tag A identity, bilingual purpose text |
| Tag B — ICE | 1 | Different unique visible QR, Tag B identity, bilingual purpose text |
| Concealed activation insert | 1 | One secret bound to the Pair ID, tamper-evident and unreadable before opening |
| Pair identification on packaging | 1 | Human-readable non-secret Pair ID, matching both tags |
| English/Urdu instructions | 1 | Scan/activate, safety/privacy notes, support contact, no raw secrets in visible copy |
| Protective packaging | 1 | Protects print/adhesive/credential during transport |
| Order/packing record | 1 | Internal record; does not reveal private owner/medical data |

**Packaging can contain multiple kits**, but each kit must remain individually identifiable and securely sealed. Quantity 3 means 3 Pair IDs, 6 visible QR tags and 3 concealed credentials.

### 3.2 Materials by intended placement

| Candidate | Appropriate use | Benefits | Risks / required validation |
|---|---|---|---|
| Laminated polyester/PET | Keys, indoor belongings, luggage | Abrasion resistance, stable print | Adhesion and flexibility on curved items |
| Outdoor-grade vinyl + UV laminate | Helmets, bikes, exposed surfaces | Weather resistance and conformability | Sunlight fade, edge lifting, solvent compatibility |
| Rigid PVC/PET card or key tag | Bags/keyrings | Physical durability | Hole placement, scratches, QR bending |
| Reflective substrate | Optional specialized outdoor placement | Visibility | Glare can reduce QR readability; require separate scan QA |
| Ordinary unlaminated paper | **Prototype only** | Cheap iteration | Poor moisture/abrasion durability |

**Supplier must supply:** material data sheet, adhesive details, ink/print process, laminate/UV performance claims, dimensions/tolerance, sample lead time, reprint policy, batch traceability and quotation. Do not invent a guaranteed waterproof or UV lifetime without a test or supplier evidence.

### 3.3 Placement rules

- Do not place QR across a seam, hinge, extreme curve or textured area that distorts modules.
- Keep the four-module white quiet zone clear after cutting and mounting.
- Ensure tag cannot be easily mistaken for a government-issued ID or certified medical device.
- Never place activation secret on the visible tag.
- If placement is outdoors/helmet, apply the **outdoor 35×35 mm minimum** regardless of whether the tag is A or B.
- Keep bilingual descriptive text outside the QR quiet zone.
- Avoid holes or trimming within the QR artwork/quiet zone.


## 4. QR generation and print engineering

### 4.1 Mandatory parameters

| Parameter | Acceptance rule |
|---|---|
| Payload | Verified production canonical HTTPS URL + opaque public token |
| Token entropy | At least 128 bits, generated by CSPRNG; unique in DB |
| QR generator | Segno or validated equivalent approved in architecture |
| Error correction | **Q preferred** (~25% recovery); **M allowed** (~15%) only after real substrate/device QA |
| Quiet zone | **4 modules of white/clear high-contrast space** on every side |
| Indoor QR artwork | **≥30×30 mm**, including quiet zone |
| Outdoor/helmet QR artwork | **≥35×35 mm**, including quiet zone |
| Colors | Dark foreground on light background, high contrast; no inverted experimental palette without QA |
| Decoration | No logos, icons, text or graphic overlays on modules/quiet zone |
| Format | Vector SVG/PDF or verified high-resolution raster; no lossy JPEG QR master |
| Bilingual text | Both English and Urdu on tags and retail packaging |
| Modes | A resolves lost mode; B resolves ICE mode; tokens distinct |

**Do not print before production domain ownership and HTTPS are verified.** Printed URLs are costly to change and cannot depend on a temporary Vercel/Railway domain.

### 4.2 Module-size calculation

For a QR symbol with `N` data modules on each side, total modules including quiet zone = `N + 8`. Thus:

`module_pitch_mm = artwork_width_mm / (N + 8)`.

Example for QR Version 3 (`N=29`): at 30 mm artwork, pitch ≈ `30/37 = 0.811 mm`; at 35 mm, pitch ≈ `35/37 = 0.946 mm`. **This is illustrative only**; the actual QR version depends on URL length, ECC and encoding. The supplier must measure the rendered output, not rely on the example.

### 4.3 Generate artwork procedure

1. Confirm production URL template and HTTPS certificate.
2. Authorize batch creation through admin backend with a staff actor.
3. Generate Pair ID, two distinct high-entropy public tokens and one high-entropy activation secret.
4. Store pair/QR metadata and **only** an activation-secret verifier in DB; plaintext secret should exist only in tightly controlled print/export handling.
5. Render two QR symbols with the selected ECC and full quiet zone.
6. Validate decoded payload for both symbols **before** print export.
7. Render bilingual Tag A/Tag B copy and non-secret serials outside quiet zone.
8. Export vector master, controlled print layout, QA manifest and separate restricted activation-insert job.
9. Compute SHA-256 checksum of approved manifest and record `print_manifest_checksum`.
10. Record actual `qr_version`, `ecc_level`, `printed_size_mm`, batch and serial metadata.
11. Restrict, expire and securely delete plaintext credential export after reconciliation; record custody.

**Important:** The API/DB contract may require exact names different from illustrative scripts; use approved Document 3 endpoints and Document 2 schema. Do not invent operational API paths.

### 4.4 Print-file validation

- File has explicit physical dimensions in mm and correct bleed/cut marks.
- Barcode payload has no accidental newline, whitespace or wrong environment host.
- Font supports Urdu shaping; text remains legible at actual size.
- No raster resampling blurs module edges.
- White quiet zone survives trimming and lamination.
- Each Tag A and B has a distinct serial and token.
- Activation secret appears **only** on its controlled concealed insert, never in public artwork.
- Manifest row count equals two QR files per Pair ID.
- QA prints from the actual vendor process and actual material, not merely a desktop proof.


## 5. Supplier qualification and pilot purchasing

### 5.1 Request-for-quotation checklist

- [ ] Supplier location/contact, production method and traceability.
- [ ] Minimum order quantity, prototype pricing, lead time and reprint terms.
- [ ] Material/adhesive/laminate specification and intended indoor/outdoor life claims.
- [ ] Supported QR ECC, vector artwork, color and print resolution.
- [ ] Ability to preserve four-module quiet zone and mm-scale tolerance.
- [ ] Capability for bilingual Urdu/English typography.
- [ ] Ability to print concealed inserts separately under restricted access.
- [ ] Confidentiality and secure disposal of print files/waste.
- [ ] Delivery/reject policy and defect replacement time.
- [ ] Agreement not to reuse URLs, serials, art files or customer details.

### 5.2 Supplier qualification steps

1. Shortlist local Lahore printers for fast prototype feedback; do not select solely on cheapest sticker price.
2. Request samples on **final intended substrate**.
3. Test indoor and outdoor QR samples on representative phones.
4. Test adhesion and wear (see §8).
5. Evaluate print confidentiality and insert concealment capability.
6. Approve supplier with signed specification, QA tolerance and reprint terms.
7. Record supplier and material in `qr_batches`.
8. Begin with a limited pilot batch; increase quantity only after field evidence.

### 5.3 Pricing and unit economics

Compute cost per **paired kit**, including two printed tags, one secret insert, protective packaging, bilingual leaflet, QA/reject allowance, payment review labor, shipping, returns/reprints and provider/platform costs. The pricing model and margin require founder approval; no fixed local vendor price is asserted.


## 6. Batch lifecycle and controlled manifests

### 6.1 Database status mapping

| Entity | Valid states (Document 2) | Operational interpretation |
|---|---|---|
| `qr_batches.status` | `draft`, `generated`, `printed`, `qa_passed`, `rejected`, `closed` | Batch-level custody and release |
| `tag_pairs.inventory_status` | `generated`, `printed`, `qa_passed`, `reserved`, `packed`, `shipped`, `delivered`, `rejected` | Physical inventory progression |
| `tag_pairs.ownership_status` | `unclaimed`, `active`, `transfer_pending`, `disputed`, `revoked` | Independent ownership lifecycle |
| `qr_codes.public_status` | `unactivated`, `active`, `owner_disabled`, `admin_suspended`, `revoked` | Public scan behavior |
| `pair_activation_credentials.status` | `unused`, `locked`, `consumed`, `revoked` | Secret usability |

**Do not conflate inventory and ownership.** A shipped pair may still be `unclaimed` until activated; an activated pair may be physically delivered. A rejected physical print must not be made allocatable.

### 6.2 Batch manifest fields (restricted)

Batch code; Pair ID; Tag A serial and token hash/fingerprint; Tag B serial and token hash/fingerprint; artwork file checksums; QR version/ECC; print dimensions; substrate; print date; supplier; operator; QA outcome; packaging method; defect reason; custody events. Use exact token only inside restricted print process; do not distribute full token exports as ordinary CSV attachments.

**Separate activation-insert manifest:** Pair ID, controlled insert ID, sealed envelope/label reference and short checksum; plaintext secret accessible only during authorized secure print step. Never include plaintext activation secrets in normal QA reports, packing slips, shipping labels or staff chat.

### 6.3 Batch workflow

`draft → generated → printed → qa_passed → closed`, with `rejected` branch at any failed quality stage. `qa_passed` requires passing per-pair QA records; batch release cannot hide defective pairs.

1. Create batch with unique code and material/ECC parameters.
2. Generate pairs and both child QR records atomically.
3. Freeze and checksum approved artwork/manifest.
4. Release print files to approved operator with custody record.
5. Print, count, reconcile rejects and destroyed waste.
6. QA every kit's identity/concealment; perform batch-level durability sample tests.
7. Release passing pairs; quarantine failures.
8. Close batch after count reconciliation and archive redacted evidence.

### 6.4 Batch reconciliation equation

`generated_pairs = passed_pairs + rejected_pairs + quarantined_pairs + unaccounted_pairs`.

**Release requires `unaccounted_pairs = 0`**. Any unexplained missing print/insert triggers security hold and investigation, because missing credentials or tags can enable fraud.


## 7. Concealed activation credential manufacturing

### 7.1 Approved candidate methods

| Method | When to use | Mandatory QA |
|---|---|---|
| Scratch-off | Only after scratch/abrasion/moisture test on final supplier material | Secret fully hidden before scratching, readable after, no bleed-through |
| Opaque tamper-evident sealed sleeve | Preferred fallback if scratch-off fails local QA | Opaque under bright light, visible tamper evidence, unique sealed insert |
| Peel-and-seal pouch | Alternative with approved adhesive | Tamper evidence, legibility, adhesive does not destroy print |

**Never:** put secret on either QR tag, expose through packaging window, photograph secrets for QA, email plain secret files, or use public token/Pair ID as secret.

### 7.2 Secure print procedure

1. Authorized backend creates high-entropy secret and stores verifier, not plaintext.
2. A restricted single-use export job sends plaintext secret only to approved insert printer.
3. Operator matches Pair ID to insert under dual-control or logged compensating review.
4. Conceal immediately; reject any readable-through, misprinted, or unsealed insert.
5. Reconcile generated/printed/sealed/destroyed inserts against batch manifest.
6. Securely destroy printer spool/cache, temporary files and rejected secret-bearing paper as far as technically possible; document limitations.
7. Restrict reprint: lost/misprinted secret requires revocation/rotation workflow, not casual re-use.
8. Do not let packer expose insert; inspect exterior seal and Pair ID only.

### 7.3 Lost or exposed secret

Immediately quarantine pair, lock/revoke credential, determine whether tag public tokens were exposed, record incident, and authorize new credential/insert or replacement pair according to approved backend capability. **Do not assume secret rotation is implemented**; if not, reject pair and issue a newly generated one. Keep full audit trail.


## 8. Print quality assurance (QA) and acceptance sampling

### 8.1 Every-pair inspection — 100% required

For **every** pair, QA inspector must verify:

1. Exactly one physical Tag A and one Tag B; different tokens.
2. Printed Pair ID matches controlled manifest and concealed insert reference.
3. Tag A scan opens lost mode; Tag B opens ICE mode; neither exposes activation secret.
4. Both QR codes decode correctly on a representative phone.
5. Indoor QR ≥30×30 mm and outdoor/helmet QR ≥35×35 mm for the applicable product; both include quiet zone.
6. Four-module white quiet zone on all sides after cutting/lamination.
7. Correct ECC Q, or M with documented approved QA exception.
8. Both English and Urdu text present and legible.
9. No smearing, missing modules, overprint, trimming intrusion, delamination or distortion.
10. Concealed credential cannot be read without opening and seal shows tamper evidence.
11. Serial/token mapping and inventory status are correct.
12. QA record includes inspector, date, `qa_round`, flags, and approval result.

**A failed individual kit is rejected/quarantined.** Sampling cannot replace the 100% identity/mismatch/secret-concealment checks.

### 8.2 Batch durability sampling — proposed pilot plan

For the first supplier/material/print process, test **at least 10 finished pairs or all pairs if the pilot batch is smaller**, selected across beginning/middle/end of print run. This is a **proposed pilot screening plan**, not an ISO/ANSI acceptance-sampling claim or a statistically proven reliability level. After initial evidence, founder/QA lead should approve sample size and acceptance thresholds for each production volume/material.

Sample tests: indoor normal light, dim light, glare, outdoor sunlight, moisture/water splash, gentle abrasion, adhesion peel/edge lifting, curvature, thermal exposure representative of Lahore use, repeated scanning and laminate wear. Test final adhesive/substrate after curing. Record exact conditions and pass/fail, not vague “waterproof” claims.

### 8.3 Device matrix

- At least two representative Android phones (including a budget/older model).
- At least one iPhone if available; if unavailable, mark test **not performed** and do not claim iOS compatibility verified.
- Native camera scan and a second QR scanning app where feasible.
- Different distances/angles/lighting and mobile connectivity conditions.
- Test both Tag A and Tag B, initial/unactivated and active safe states.

### 8.4 Defect classification

| Class | Examples | Disposition |
|---|---|---|
| Critical | Wrong QR token/owner mode; secret visible; duplicate Pair ID; malicious domain; mispaired A/B | Stop batch, quarantine, investigate security |
| Major | QR fails scan, quiet zone cut, below size, Urdu absent, laminate/adhesive fails intended use | Reject pair; reprint/rework and full retest |
| Minor | Cosmetic defect outside QR/quiet zone with no readability/privacy impact | QA lead documented disposition; never hide from evidence |

**Proposed release threshold:** zero Critical and zero Major defects in **released units**; 100% identity/concealment checks passed. For batch-level destructive sample tests, **any** Critical/Major failure triggers hold and investigation, not silent acceptance. Statistical acceptance criteria for larger production require a separate approved QA plan.

### 8.5 Record in `pair_print_qa`

`pair_id`, `qa_round`, `lost_scan_passed`, `ice_scan_passed`, `pair_match_passed`, `credential_concealed`, `bilingual_label_passed`, `quiet_zone_passed`, `indoor_size_passed`, `outdoor_size_passed`, `packaging_method`, `tamper_evidence_passed`, `approved`, `inspected_by`, `inspected_at`, and documented defect/notes according to final schema. Do not put plaintext secrets in notes or photographs.


## 9. QA rework, quarantine and secure destruction

1. Mark affected pair/batch on QA hold; physically isolate in labeled locked bin.
2. Record defect code, inspector, sample evidence (redacted), time and supplier.
3. For cosmetic defect: QA lead determines if rework is possible without changing printed token/secret.
4. For QR damage: do **not** manually change token; reprint same authorized artwork only if custody and token validity are intact, or perform audited replacement with new token.
5. For exposed credential: revoke/rotate under supported secure process or reject and regenerate pair.
6. For pair mismatch: hold **both** tags and insert; investigate full batch reconciliation.
7. Repeat **all** per-pair QA checks after rework; increment `qa_round`.
8. Securely destroy rejected secret-bearing inserts and defective QR prints after authorization, with count/witness evidence.
9. Keep historical DB records; do not delete revoked QR children to “clean up” inventory.

**No silent QA override.** An override requires role permission, reason, audit and independent review; it cannot override critical security requirements.


## 10. Inventory storage, stock counts and reservation

### 10.1 Storage rules

- Store passed, uninspected, rejected and returned kits separately.
- Keep concealed inserts with matching physical pair in tamper-evident sealed packaging.
- Limit storage access to authorized staff; keep custody log.
- Protect adhesive/laminate from moisture, heat and direct sunlight per supplier instructions.
- Avoid labels with full public token/secret in open inventory spreadsheets.
- Use Pair ID as internal lookup, not secret.

### 10.2 Cycle counts

Daily during active pilot packing, reconcile physical passed kits against `tag_pairs.inventory_status` and active `order_pair_allocations`. Weekly reconcile entire stock and returned/quarantined kits. Every mismatch gets incident/ticket, not manual silent status edit.

### 10.3 Eligibility for allocation

A pair is allocatable only if:
- `inventory_status = qa_passed`;
- ownership is `unclaimed`, not disputed/revoked;
- both **current** QR children exist with expected tag types and safe states;
- activation credential exists and is `unused` (not locked/revoked/consumed);
- per-pair QA approved, including concealment;
- pair has no other active allocation;
- batch is QA-approved and not under recall;
- order payment is independently verified.

Backend must enforce these checks transactionally, not trust a staff spreadsheet.


## 11. Catalog, orders and manual bank/Raast verification

### 11.1 Customer order flow

1. Customer selects product/quantity **in pairs**.
2. Backend calculates price, shipping and total using fixed-precision money (`Decimal`/integer minor units), not client totals or floats.
3. Create order and order items; no inventory allocation yet unless explicitly designed as a time-limited unpaid reservation with safeguards.
4. Show approved bank/Raast payment instructions, official recipient name, reference and amount.
5. Customer transfers externally and submits payment reference/proof if required.
6. Store proof in private Supabase Storage; order remains **unverified**.
7. Finance independently checks actual bank/Raast settlement and records review.
8. Only verified payment advances to allocation.

### 11.2 Payment states and audit

Document 2 proposes `orders.payment_status`: `awaiting_transfer`, `proof_submitted`, `under_review`, `verified`, `rejected`, `refunded`; `payment_submissions.status`: `submitted`, `under_review`, `approved`, `rejected`. Do not confuse submission approval with automatic financial settlement. The payment reviewer records actor, bank reference, settled amount/date, match result, decision and sanitized reason.

### 11.3 Independent bank verification checklist

- [ ] Correct official receiving account/bank verified.
- [ ] Settled credit exists in trusted bank channel, not merely screenshot/SMS.
- [ ] Amount matches approved order total or approved exception.
- [ ] Transaction reference/date is plausible and not previously used.
- [ ] Customer/order association independently established.
- [ ] Duplicate payment proof/reference checked.
- [ ] Discrepancies escalated, not auto-approved.
- [ ] Review outcome recorded with authenticated finance actor.
- [ ] No allocation until `verified` status committed.

**Do not ask AI to approve payment based on an image.** AI may help flag inconsistencies but final confirmation is a human bank-ledger action.

### 11.4 Fraud cases

| Case | Response |
|---|---|
| Fake screenshot | Reject/hold; request verifiable transaction reference |
| Same proof used twice | Flag duplicate, hold both orders, investigate |
| Partial payment | Hold, document difference and approved adjustment process |
| Wrong beneficiary | Do not mark verified; customer support investigation |
| Bank credit later reversed | Freeze unshipped allocation, review risk/exception |
| Staff approves own order | Second reviewer or documented exception control |
| Chargeback/refund after dispatch | Case-specific fraud/return workflow; preserve audit |


## 12. Atomic pair allocation and reservation

### 12.1 Allocation preconditions

Order payment `verified`; order not cancelled/refunded; order item quantity `quantity_pairs`; candidate pairs QA-passed and not active/allocated; staff authorized; shipping/fulfillment policy approved.

### 12.2 Transaction pseudocode

```text
BEGIN
  Lock verified order and order item rows
  Confirm requested quantity_pairs and no duplicate allocation
  Select eligible pairs with deterministic locking order
  Lock selected pair rows FOR UPDATE
  Check batch, pair QA, both current children, credential unused
  Insert order_pair_allocations with active status
  Update tag_pairs.inventory_status = reserved
  Update order fulfillment_status = allocated
  Insert audit event with staff actor, order, pair references
COMMIT
```

- Enforce one active allocation per pair with database constraint/index.
- Reject partial allocation unless product policy explicitly permits split fulfillment; if permitted, track quantities precisely.
- On conflict, retry boundedly; never double-sell pair.
- If order is cancelled before dispatch, release allocation transactionally and return eligible pair to QA-approved inventory **only after integrity check**.
- Pair allocation does not activate tags; customer activation remains separate.

### 12.3 Example

Order quantity = **3 kits** → allocate **3 Pair IDs**, each with **2 QR codes**, for **6 physical tags** and **3 concealed secrets**. Shipping one Pair ID for an order quantity of 3 is an under-fulfillment defect.


## 13. Packing station SOP

### 13.1 Prepare station

- Clean, dry table; no uncontrolled cameras or visitors.
- Access to authorized order list and allocated Pair IDs only.
- Separate passed kits, returns and rejects.
- Scanning device connected to trusted admin QA workflow.
- Packaging and tamper-evident supplies ready.

### 13.2 Pack one order

1. Confirm order status: payment verified, allocation active, correct recipient/address access.
2. Read expected **number of pairs**, not number of tags.
3. Retrieve allocated pairs by Pair ID from QA-passed stock.
4. For each pair, inspect Tag A, Tag B and sealed credential insert **without opening secret**.
5. Scan both public QR labels, verify roles and Pair ID via authorized QA view; do not activate.
6. Confirm printed dimensions/quiet zone previously QA-approved and no new damage.
7. Confirm bilingual instructions and privacy disclosure insert.
8. Check concealed credential seal intact and Pair ID matches.
9. Place each complete pair into its own protective inner sleeve.
10. Count pairs again against order item quantity.
11. Add packing slip with order ID, Pair IDs/serials as permitted, product count and support instructions — **never activation secrets, medical notes or finder locations**.
12. Seal parcel, add shipping label, photograph exterior only if needed (redact address in shared evidence).
13. Record `shipment_pairs.packed_qa_confirmed`, packer, timestamp; transition statuses transactionally.
14. Move parcel to dispatch queue, not delivered status.

### 13.3 Packing rejection

Stop packing if any pair is missing a tag, wrong role, broken seal, mismatched ID, unreadable, previously activated, or flagged disputed/revoked. Quarantine and replace allocation through authorized workflow; do not swap individual tags across pairs.

### 13.4 Two-person spot check

For initial pilot, a second person should spot-check the first few packed orders and all exceptions. Record who checked and what was verified; if unavailable, founder documents risk and performs pre-dispatch reconciliation.


## 14. Shipping and delivery in Lahore pilot

### 14.1 Carrier selection

Select a carrier based on service area, parcel tracking, delivery proof, loss/damage handling, cost, and ability to protect private recipient data. Confirm actual rates and coverage; no carrier performance claims are made here.

### 14.2 Dispatch SOP

1. Verify packed shipment belongs to order and contains only its allocated pairs.
2. Confirm shipping address/phone from authorized encrypted record.
3. Generate carrier label with only necessary delivery information.
4. Handoff sealed parcel; capture tracking reference and carrier receipt.
5. Update shipment to `dispatched` and pairs to `shipped` in authorized transaction.
6. Notify customer through approved channel without exposing activation secret.
7. Monitor exception/delivery status; mark delivered only with evidence or approved customer confirmation.
8. Handle failed delivery/return-to-sender via controlled return workflow.

### 14.3 Delivery evidence

Order ID, shipment ID, carrier, tracking reference, dispatch timestamp, handoff proof, delivery/failed attempt evidence, exception code and operator. Keep recipient phone/address private; no public QR link to customer shipping record.

### 14.4 Lost parcel

Immediately mark shipment exception, contact carrier, freeze any affected unactivated credentials if compromise is plausible, assess whether public QR tokens/insert were exposed, and determine secure replacement. Never issue another live secret for same pair without approved credential rotation/revocation.


## 15. Customer activation and handoff safety

- Customer must authenticate with verified account/entitlement as approved in API contract.
- Customer enters **one concealed credential** to activate both tags atomically.
- Physical Pair ID alone is not sufficient proof of ownership.
- Activation UI must not allow Tag A-only or Tag B-only activation.
- Failed activation attempts are throttled; support must not ask customers to send full secret in chat.
- Successful activation sets pair owner and both current child public states in one DB transaction.
- If secret appears compromised, pause and escalate; do not override without audit.
- Provide bilingual instructions on packaging; detailed screen and navigation behavior belongs to final UI/UX spec.

### 15.1 Safe customer-facing instruction draft (human review)

**English:** “This pack contains two QR tags. Keep the activation code private. Sign in to SafeReturn and activate both tags together using the concealed code. Do not share the code with anyone. For emergencies, follow local emergency services guidance; SafeReturn is not an emergency dispatch service.”

**Urdu draft:** “اس پیک میں دو QR ٹیگز ہیں۔ ایکٹیویشن کوڈ کو خفیہ رکھیں۔ SafeReturn میں سائن اِن کریں اور چھپے ہوئے کوڈ سے دونوں ٹیگز ایک ساتھ فعال کریں۔ یہ کوڈ کسی کے ساتھ شیئر نہ کریں۔ ہنگامی صورتحال میں مقامی ایمرجنسی سروسز سے رابطہ کریں؛ SafeReturn خود ایمرجنسی سروس نہیں ہے۔”

Native-speaker and legal/privacy review required before printing.


## 16. Returns, refunds, exchanges and cancellations

### 16.1 Return intake

1. Verify order and requester identity without demanding activation secret.
2. Record reason: damaged, wrong kit, undelivered, changed mind, compromised secret, wrong address, duplicate order.
3. Check shipment status and physical custody; create support case.
4. Quarantine returned kit; do not put directly back into sellable stock.
5. Scan both tags and inspect seal, physical wear, current ownership and credential status.
6. If **activated, secret exposed, missing tag or ownership disputed**, never resell as an unused kit.
7. Determine refund/exchange under founder-approved published policy and applicable legal obligations.
8. If safe and unused, perform full re-QA and security review before any return to inventory.
9. Record refund and payment review separately; do not erase original order/audit.

### 16.2 Cancellation timing

| Stage | Default operational response |
|---|---|
| Before payment | Cancel order; no allocation |
| Proof submitted, not verified | Finance checks bank state before refund decision |
| Verified, not allocated | Cancel with authorized finance reversal process |
| Allocated, not packed | Release allocation transactionally after QA/secret integrity check |
| Packed, not dispatched | Unpack under controlled procedure; quarantine until QA |
| Dispatched | Carrier intercept if possible; return intake and refund review |
| Delivered, not activated | Return only under approved seal/identity policy |
| Activated | Cannot be treated as unused inventory; ownership/security case |

**Do not invent a legal return window or guaranteed refund entitlement.** Publish approved policy after local review.


## 17. Replacements, lost tags and ownership disputes

### 17.1 Tag-only replacement

1. Authenticate requester and verify pair ownership/authorization.
2. Identify damaged/missing Tag A or B and reason.
3. Lock pair, mark old child `is_current=false` and `public_status=revoked` with timestamp.
4. Generate new public token and serial for **same tag type** and **same pair**.
5. Maintain partial unique current-child invariant and exactly-two-current check at transaction boundary.
6. Generate new physical QR, run full print QA, dispatch to verified owner.
7. Preserve old QR row and replacement chain; scanning old token must show safe revoked state.
8. Do not transfer old finder messages or public medical data to an unrelated person.

**Important:** Replacing one physical tag does not imply new pair activation secret or new owner. If credential compromise/ownership dispute is involved, use a separate approved security workflow.

### 17.2 Full pair replacement

Use when both tags, credential or physical mapping are compromised. Revoke/quarantine old pair as required, create a new pair with two new tokens and new concealed secret, QA and reallocate under authorized customer-support process. Avoid accidentally granting two active kits for one entitlement.

### 17.3 Ownership dispute

Suspend risky transfers/activation as approved, gather non-secret proof of purchase/receipt, verify identity, log staff access and decision, avoid disclosing current owner PII to claimant. Only authorized support/security can resolve. Never split A/B ownership.

### 17.4 Lost/stolen parcel or exposed insert

Treat as possible credential compromise, even if public QR is unactivated. Freeze, investigate, revoke/reissue under documented procedure. Do not ask customers to reveal secrets over WhatsApp or email.


## 18. Fraud prevention, custody and insider controls

| Risk | Prevention | Detection | Response |
|---|---|---|---|
| Printer copies public QR | Contract, restricted manifests, watermark/custody | Duplicate print/scan anomalies | Investigate, revoke affected batch |
| Printer copies secret insert | Controlled one-time print, opaque packaging, access logs | Reconciliation gap, exposed seal | Freeze credentials, incident response |
| Mismatched A/B tags | Pair-ID manifest and 100% dual scan | QA pair mismatch | Quarantine whole pair |
| Fake payment screenshot | Independent bank settlement check | Duplicate reference or no credit | Reject/hold, audit |
| Double inventory sale | DB unique active allocation + row locks | Allocation conflict | Roll back and investigate |
| Staff steals sealed kits | Restricted stock, cycle count, dispatch custody | Missing stock | Quarantine batch, incident |
| Owner impersonation | Auth/entitlement/secret and support proof | Suspicious activation failures | Throttle/lock/review |
| Replacement abuse | Limit and verify replacement reasons | Repeat requests, unusual loss | Escalate with case history |
| Counterfeit SafeReturn tag | Canonical domain, serial validation, QA | Wrong URL/branding reports | Public warning, investigate |
| Public token used as secret | Separate CSPRNG values, tests | Activation attempt with QR token | Reject and audit |
| Exposed private delivery address | Access control and redacted evidence | Log/export review | Contain, privacy incident |

### 18.1 Custody record

For each transfer: timestamp, batch/pair range, from/to actor, physical count, manifest checksum or reference, seal state, reason and signatures/approvals. No plaintext activation secret in custody records.


## 19. Lahore pilot production and fulfillment plan

### 19.1 Suggested controlled stages (not fixed quantities)

**Stage P0 — prototype:** Generate synthetic/test tokens on non-production environment; sample several substrates and dimensions; verify bilingual print and scan. Do not hand out test tags as live products.

**Stage P1 — limited real batch:** After production domain, provider, privacy and bank SOP approval, print a small numbered batch. 100% pair/secret QA and documented sample durability checks. Choose batch size based on budget, printer MOQ and ability to support each user; do not assume a universal number.

**Stage P2 — supervised customer pilot:** Enroll consenting Lahore users; independently verify payment; allocate/pack/ship complete kits; observe activation and scan success without seeing or recording secrets.

**Stage P3 — expand cautiously:** Review print rejection, delivery loss, support burden, activation problems and security incidents. Approve larger production only after no unresolved Critical/High issues.

### 19.2 Pilot launch prerequisites

- [ ] Approved PRD/architecture/security decisions and human-reviewed consent copy.
- [ ] Production domain/DNS/HTTPS stable; Resend sender verified.
- [ ] Secure pair generator, DB constraints and activation concurrency tests pass.
- [ ] QR artwork size/ECC/quiet zone and bilingual copy approved.
- [ ] Supplier final-material samples pass physical tests.
- [ ] Concealed insert method tested and batch custody defined.
- [ ] Finance has independent bank verification access and SOP.
- [ ] Private proof storage and admin permissions tested.
- [ ] Inventory/shipments and exception workflows tested.
- [ ] Backup/restore and incident contact readiness.
- [ ] No Critical/High privacy or security defects.

### 19.3 Pilot metrics

Measure: first-scan success by tag/material/phone, QA reject rate, batch reconciliation accuracy, activation completion, support tickets per kit, payment review time, allocation conflict rate, packing accuracy, shipping exception rate, replacement/return rate, privacy/security incidents. Define numerical thresholds after baseline and founder approval; do not fabricate acceptance percentages.


## 20. Operational records and forms

### 20.1 Batch release form

```text
Batch code:
Supplier / substrate / adhesive / laminate:
Print date / operator:
Approved canonical domain:
ECC: Q / M (exception approval if M)
Pair count generated / printed / passed / rejected / quarantined:
Unaccounted pairs (must be zero):
Manifest SHA-256:
100% per-pair QA complete? Y/N
Durability sample count and conditions:
Critical/Major defects found:
Secure secret-insert reconciliation:
QA inspector / timestamp:
Operations approval / timestamp:
Decision: RELEASE / HOLD / REJECT
Exception ticket(s):
```

### 20.2 Per-pair QA card

```text
Pair ID:                     Batch:
Tag A serial:               Tag B serial:
A scanned lost mode:        PASS/FAIL
B scanned ICE mode:         PASS/FAIL
Two tokens distinct:        PASS/FAIL
Pair and insert match:      PASS/FAIL
ECC and QR size:            PASS/FAIL
Four-module quiet zone:     PASS/FAIL
English and Urdu copy:      PASS/FAIL
Material/adhesion/print:    PASS/FAIL
Secret fully concealed:     PASS/FAIL
Tamper evidence intact:     PASS/FAIL
QA round:                   Inspector:
Disposition: PASS / HOLD / REJECT
Defect code / evidence ref (no secret):
```

### 20.3 Bank verification form

```text
Order ID:                   Customer ID (internal):
Expected total:             Payment reference:
Proof received?             Bank statement/portal verified? Y/N
Actual settled amount:      Settlement date/time:
Reference previously used?  Y/N
Mismatch or exception:
Reviewer ID / timestamp:
Decision: VERIFIED / REJECTED / INVESTIGATE
Second approval (if required):
Audit event ID:
```

### 20.4 Packing and dispatch form

```text
Order ID:                    Shipment ID:
Payment verified?            Y/N
Quantity ordered (pairs):
Pair IDs allocated:
Pair IDs physically packed:
Each contains Tag A + Tag B + sealed insert? Y/N
All QA-passed?               Y/N
Bilingual leaflet included? Y/N
No activation secrets on packing slip? Y/N
Packer / time:               QA checker / time:
Carrier / tracking:          Handoff proof ref:
Dispatch status / time:
```

### 20.5 Return/replacement case

```text
Case ID:                     Original order/shipment:
Requester verification method:
Pair ID / affected tag type:
Issue and physical condition:
Activation/ownership status:
Secret seal intact?          Y/N/UNKNOWN
Security quarantine required? Y/N
Old token revoked?           Y/N/NOT APPLICABLE
Replacement pair/tag ID:
Finance/refund decision:
Customer communication:
Approver / audit reference:
Closure and QA evidence:
```


## 21. Quality tests and release gates

| Test ID | Procedure | Pass criteria | Owner |
|---|---|---|---|
| PHY-01 | Measure indoor QR including quiet zone | ≥30×30 mm | QA |
| PHY-02 | Measure outdoor QR including quiet zone | ≥35×35 mm | QA |
| PHY-03 | Inspect quiet zone | Four clear white modules each side | QA |
| PHY-04 | Inspect ECC | Q or approved M exception | QA |
| PHY-05 | Scan Tag A on representative devices | Correct lost mode and token | QA |
| PHY-06 | Scan Tag B on representative devices | Correct ICE mode and token | QA |
| PHY-07 | Cross-check Pair ID and serials | A/B/insert all match | QA |
| PHY-08 | Inspect bilingual copy | English and Urdu present/legible | QA |
| PHY-09 | Inspect credential concealment | No readable secret without opening | QA/security |
| PHY-10 | Inspect tamper evidence | Tamper visible; seal intact | QA |
| PHY-11 | Abrasion/moisture/adhesion samples | Remain scanable, fit for intended use | QA |
| PHY-12 | Batch count reconciliation | Zero unaccounted pairs/inserts | Ops/security |
| PHY-13 | Attempt allocate unverified order | Rejected, no stock change | Backend/finance |
| PHY-14 | Race two orders for same pair | Only one active allocation | Backend |
| PHY-15 | Pack quantity 3 | 3 pairs, 6 tags, 3 secrets | Fulfillment |
| PHY-16 | Simulate wrong A/B pairing | Quarantine, cannot ship | QA |
| PHY-17 | Return activated kit | Cannot restock as new | Support/ops |
| PHY-18 | Replace one tag | Old QR revoked; new current; history kept | Backend/ops |
| PHY-19 | Lost parcel with secret exposure | Hold/revoke/reissue incident path | Ops/security |
| PHY-20 | Audit payment approval | Bank verified by authorized staff | Finance |
| PHY-21 | Check packing slip and shipping label | No secrets/medical notes/location | QA/privacy |
| PHY-22 | Scan after trimming/lamination | Quiet zone and scan still pass | QA |
| PHY-23 | Check production QR host | Owned verified HTTPS domain | Engineering |
| PHY-24 | Validate QR token not activation secret | Distinct and cannot activate with token | Security |

Map these to physical, DB, API and E2E cases in Document 7; do not claim tests passed before recording evidence. Release gate requires all applicable P0 tests passed, no unresolved Critical/Major physical defects in released units, and human sign-off.


## 22. Incident and recall procedures

### 22.1 Stop-production triggers

- Incorrect or unowned QR domain; print token collision or wrong mode.
- Any exposed activation secret or missing controlled insert.
- Mismatched A/B tags, missing pair inventory or unauthorized manifest copy.
- Supplier print process changes material/ECC/quiet zone without approval.
- Fraudulent payment approvals, double allocation or unauthorized shipment.
- Public privacy incident involving ICE phone, finder location or customer details.

### 22.2 Recall/containment workflow

1. Stop print, allocation and dispatch for affected batch.
2. Mark batch/pairs under hold/rejected or revoked according to safe supported transitions.
3. Reconcile physical stock, shipped parcels and activated pairs.
4. Identify affected customers by internal order mapping; do not publish owner data.
5. Revoke unsafe public QR tokens/credentials as needed, preserving emergency safety communication.
6. Notify operations/security and privacy/legal owner; evaluate customer notification.
7. Reprint/replace under new QA and approved financial policy.
8. Record root cause, affected range, custody, decisions and corrective actions.
9. Resume only after technical and operational release sign-off.

### 22.3 Resend or service outage during shipping

Do not lose physical order status or finder messages because email fails. Outbox retries independently. Hold shipments only if customers cannot safely activate or obtain essential information; define exception owner. Do not send activation secrets in email as workaround.


## 23. Audit, metrics, security and privacy

**Record:** generation, print export, checksum, QA, override, payment review, allocation, packing, dispatch, return, revocation, replacement, destruction and batch recall. Each event includes authenticated actor, time, affected IDs and sanitized reason.

**Never record in ordinary audit/log:** plaintext activation secret, full ICE contact phone, private medical notes, finder text, precise coordinates, full bank credentials or customer shipping address. Store shipping address encrypted and reveal only to authorized fulfillment processes. Payment proof files remain private with time-limited access.

**Retention:** Use approved privacy policy and applicable financial obligations. The proposed finder/location retention from Document 6 does not automatically apply to physical inventory, orders, payment or shipping records. Founder/legal review must set appropriate retention and disposal schedules.

**Daily operations checks:** QA hold count, stock reconciliation, verified-but-unallocated orders, packed-not-dispatched parcels, shipment exceptions, payment review backlog, duplicate references, print waste, missing credentials, support incidents and provider alerts.


## 24. Training, supplier and change control

Before staff or supplier begins live work:

1. Explain Pair ID vs public token vs activation secret.
2. Demonstrate two-tag matching and 100% QA.
3. Demonstrate proper QR size measurement and quiet zone inspection.
4. Demonstrate safe concealed insert handling and secure disposal.
5. Demonstrate payment verification **against bank records**.
6. Demonstrate stock reservation and packing against approved order.
7. Demonstrate quarantine/incident reporting without revealing customer data.
8. Have operator perform a supervised practice run with synthetic kits.
9. Record training date, trainer, operator and competency check.

**Change control:** A new supplier, material, QR version/ECC, URL format, credential packaging, printer workflow or packing method requires documented impact analysis, test samples and approval. Do not silently modify print master files after manifest checksum is approved.


## 25. Open decisions and approval register

| ID | Decision | Proposed direction | Must approve before |
|---|---|---|---|
| SOP-D01 | Production canonical domain | Owned verified SafeReturn HTTPS domain | Printing live labels |
| SOP-D02 | QR ECC default | Q, M only with approved QA | Print master |
| SOP-D03 | Final indoor/outdoor materials | Supplier samples with wear tests | Purchasing |
| SOP-D04 | Insert concealment | Sealed opaque/tamper-evident if scratch-off fails | Secret print |
| SOP-D05 | Pilot batch size and sample plan | Small controlled batch; 100% identity QA | Production |
| SOP-D06 | Print confidentiality and disposal | Signed supplier controls | External print handoff |
| SOP-D07 | Price, shipping, refund/return policy | Pair-based unit economics, local review | Checkout |
| SOP-D08 | Bank verification evidence | Independent finance reviewer | Payment acceptance |
| SOP-D09 | Shipping carrier and proof policy | Verified Lahore coverage and tracking | Dispatch |
| SOP-D10 | Activated-kit returns/replacements | Security-first exception workflow | Support |
| SOP-D11 | Ownership dispute and lost secret | Quarantine/revoke/reissue policy | Pilot |
| SOP-D12 | QA sampling at larger scale | Statistical plan after pilot evidence | Scale-up |
| SOP-D13 | Bilingual label and medical disclaimer | Native-speaker/legal review | Print approval |
| SOP-D14 | QR replacements and secret rotation capability | Verify backend implementation | Rework/replacement |

### 25.1 Sign-off

| Role | Approval | Date | Notes |
|---|---|---|---|
| Founder / product owner | Pending | — | Business policy and pilot budget |
| Technical owner | Pending | — | Pair, QR, API and DB behavior |
| Security/privacy reviewer | Pending | — | Credential custody and disclosures |
| QA lead / supplier owner | Pending | — | Print material and acceptance |
| Finance reviewer | Pending | — | Manual payment SOP |
| Fulfillment lead | Pending | — | Packing, shipping, returns |

**Do not use “approved” or “production ready” until signed evidence exists.**

---

## 26. Final document boundary

**This is Document 9 only.** The next and **final** document is **Document 10 — SafeReturn UI/UX Design Specification**: exhaustive page/screen inventory, route map, navigation journeys, components, responsive states, English/Urdu RTL, accessibility, loading/error/empty/offline states, and implementation-ready frontend guidance aligned with Documents 1–9.

No separate UI/UX artifact has been created in this step.

**End of Document 9.**

