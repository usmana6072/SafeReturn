# SafeReturn — Document 12: Branded QR Wrapper & Print Template Amendment

**Document ID:** SR-AMD-PRINT-012  
**Version:** 1.3 proposed | **Date:** 12 October 2026 | **Scope:** Incremental amendment to SafeReturn Documents 01–11 v1.2  
**Status:** Implementation contract proposed for founder, print-operations, and security approval; not a deployed feature  
**Market:** Pakistan / Lahore pilot | **Release:** P0 two pre-approved sticker designs; P1 full admin template design tooling

> **Priority rule:** Approved founder decisions and safety/privacy rules remain controlling. This amendment supersedes v1.2 **only** for requirements explicitly identified below regarding branded wrapper artwork, messages, print-template selection, snapshots, and management. All other v1.2 requirements remain in force. Never treat the archived v1.1 sections appended to earlier documents as newly authoritative. This document is an additive specification, not a complete rewrite or executed database migration.

## 0. Executive decision and non-negotiables

SafeReturn's printed product is a **composite printable label**, not simply a bare QR code. Each label consists of an encoded canonical URL, QR modules, a small centered SafeReturn logo, a **non-interfering outer wrapper**, and appropriate purpose-specific English/Urdu text. The wrapper may resemble the user's visual example (contrasting QR block with bottom message band), but must use original SafeReturn branding and must **not copy LifeTag's trademarks, artwork, or contact details**.

**Core invariant:** One Pair ID owns exactly two current QR identities—`lost` and `ice`—and one concealed activation credential. For an order of **3 Lost + 2 ICE physical stickers**, the production manifest contains **five label occurrences**, but **only two unique QR URLs** and **one pair**. The three Lost occurrences reproduce the same Lost QR identity; their printed wrapper may vary by approved size/template, but their scanner destination and editable profile do not vary. Printed copies are not additional accounts or additional activated QR identities.

**Other immutable rules:**
- QR URLs must point only to SafeReturn's verified production domain, `/q/{token}`; no activation secrets, patient information, owner contact fields, or customer identifiers encoded into the QR.
- The centered logo and wrapper are *visual branding*, not a security/ownership credential. QR claim still requires authenticated purchase entitlement or concealed activation secret under the existing rules.
- Keep the required **4-module white quiet zone fully outside QR data modules**. Neither wrapper borders, colored backgrounds, captions, cut guides, nor logo may damage it.
- Prior baseline: minimum complete QR symbol, **including quiet zone**, 30×30 mm indoor and 35×35 mm outdoor, unless a stricter approved product/variant specification applies. The **outer label is larger** than the QR symbol and must have room for readable text, trim and bleed. Don't advertise 30×30 mm *total wrapper* as equivalent to a 30×30 mm QR plus captions.
- PDF: Lost labels first, ICE labels second; within each type, group by variant/size per approved order snapshot. Preserve exact counts. Generate vector-first, compressed, private files in Supabase Storage. Cloudinary is approved for **public catalog media**, not customer-specific private print artifacts or payment evidence.
- P0: two approved locked templates (`lost` and `ice`), with safe parameterized size variants. P1: admin draft/edit/preview/version/publish and additional physical product templates, behind feature flags and QA approval.
- Prior v1.2 payment, checkout, ownership, QR management, finance, privacy, retention, shipping and future-product rules are unaffected.

## 1. Scope and terminology

| Term | Meaning | Example |
|---|---|---|
| QR identity | One current database QR/tag ID and canonical public token/URL | Lost QR belonging to Pair A |
| QR symbol | Encoded module matrix + quiet zone + approved center-logo overlay | 35 mm scan region |
| Wrapper / label | Complete die-cut print area, including QR symbol, header/footer, message, trim/bleed | 50×70 mm sticker |
| Template | Versioned layout specification for placing QR and text | `sr-lost-sticker` v1 |
| Template revision | Immutable published layout & copy used for production | Template version 2 |
| Product variant | Purchasable size/material/color/SKU and fulfillment method | Waterproof large sticker |
| Message set | Human-reviewed English/Urdu copy assigned to a template revision and tag type | Lost return instructions |
| Print occurrence | One physical label instance of a QR identity at an approved size | 3 repeats of one Lost QR |
| Print manifest | Frozen order/QR/template/size/quantity list required for a print job | Order SR-10025 |
| Artwork preview | Authorized preview without unprotected activation secrets or private customer details | Admin preview for template |

**Not in scope for P0:** a browser-based drag-and-drop canvas, arbitrary HTML/CSS or SVG from customers, customer-uploaded wrapper code, new `child`/`elder` database tag types, new solo-tag ownership model, independently activated children, automatic medical/legal claims, payment-processing changes, public downloading of print files, or arbitrary artwork dimensions. Future child/elder/keychain products use the existing `lost`/`ice` identity types unless an approved architecture change explicitly introduces new tag types.

## 2. Functional requirements (additive)

| ID | Priority | Requirement / acceptance |
|---|---|---|
| WRAP-FR-001 | P0 | Every approved sticker print uses a configured, versioned outer wrapper and approved bilingual purpose message, not just a loose QR bitmap. |
| WRAP-FR-002 | P0 | SafeReturn logo is centered *inside* QR module matrix in approved bounded style; the exterior wrapper is independently designed. |
| WRAP-FR-003 | P0 | `lost` and `ice` each have distinct title/message and clear icon/visual identification without using color alone. |
| WRAP-FR-004 | P0 | Render messages **outside** the QR symbol/quiet zone; no line of text may touch scan modules or be clipped. |
| WRAP-FR-005 | P0 | Preserve exact QR URLs and profile semantics across multiple copies, colors and sizes. |
| WRAP-FR-006 | P0 | Use approved mapping of product variant + tag type + template key/version; no silent fallback to an unrelated label template. |
| WRAP-FR-007 | P0 | Freeze template revision, rendered copy, dimensions, artwork/assets fingerprints, relevant renderer parameters, and QR binding into the print job so reprints are reproducible. |
| WRAP-FR-008 | P0 | If template invalid/unpublished/incompatible with size or material: block production job, show actionable admin error, never ship a guessed layout. |
| WRAP-FR-009 | P0 | Support exact physical units (mm), printing margins, quiet zones, safe zones, trim/cut guides, and printer QA. |
| WRAP-FR-010 | P0 | Generated PDF remains small using vector QR paths, PDF form/object reuse when possible, subset licensed approved fonts, compressed images, bounded metadata and deduplicated logo assets. |
| WRAP-FR-011 | P0 | Main production PDF contains **no plaintext concealed activation credential**; authorized insert generation uses existing restricted workflow. |
| WRAP-FR-012 | P0 | All printable public-facing message content is bilingual English/Urdu, rendered with reviewed fonts, correct shaping/direction and scan-safe spacing. |
| WRAP-FR-013 | P0 | Private production artwork download requires verified staff role and short-lived authorized access; audit preview/download/regenerate actions. |
| WRAP-FR-014 | P0 | Published templates never change in place; editing creates a new draft revision. Existing order/reprint uses frozen revision unless an audited replacement is explicitly approved. |
| WRAP-FR-015 | P1 | Admin can create, preview, revise, approve, publish, retire and map approved templates, with restricted design controls and audit trail. |
| WRAP-FR-016 | P1 | Additional physical products (keychains, bag tags, children/elder badges) can have purpose-specific wrapper, copy, artboard dimensions and material rules without new QR identities unless customer purchases a new pair. |
| WRAP-FR-017 | P1 | Product-specific templates may choose Lost, ICE or both as print placements, but no component permits claim/access to an unauthorized existing QR. |
| WRAP-FR-018 | P0 | Changes to a QR owner's profile change the **linked public web page**, not previously printed wrapper copy; wrappers must avoid mutable profile-specific fields. |

## 3. Initial approved-template candidates (not final print artwork)

### 3.1 SafeReturn Lost Sticker (`sr-lost-sticker`, revision 1)

- Visual: deep teal/ink header or left marker, scan-safe high-contrast QR region, optional warm pale message/footer band; clear English/Urdu labels; original SafeReturn logo centered within QR.
- Header: `FOUND THIS ITEM?` / reviewed Urdu equivalent.
- Short English message: **“Found this item? Scan to contact its owner.”**
- Urdu candidate: **“اگر یہ چیز آپ کو ملی ہے تو مالک سے رابطے کے لیے اسکین کریں۔”** This must be reviewed by a native Urdu copy reviewer before publishing.
- Scope: lost-item recovery only; no claim that direct owner phone or WhatsApp is always available. Actual public page respects owner's WhatsApp opt-in, optional finder location, and message access.

### 3.2 SafeReturn Emergency Sticker (`sr-ice-sticker`, revision 1)

- Visual: same brand family, visibly distinct `EMERGENCY` purpose label and icon, calm warning/attention accent, no inaccurate rescue guarantee.
- Header: `EMERGENCY INFORMATION` / reviewed Urdu equivalent.
- Short English message: **“In an emergency, scan to view shared information and contact options.”**
- Urdu candidate: **“ایمرجنسی میں شیئر کی گئی معلومات اور رابطے کے طریقے دیکھنے کے لیے اسکین کریں۔”** Human linguistic and safety review required.
- No statement that all private medical details or phone numbers are immediately public; ICE reveal remains protected on the web.

### 3.3 Future optional templates, feature-gated

| Product | Template example | QR binding | Additional approval |
|---|---|---|---|
| Acrylic keychain | `sr-keychain-return` | Existing authorized Lost QR or new pair's Lost QR | engraving/material/scan testing |
| School bag tag | `sr-bag-tag` | Authorized Lost QR | child-data minimization if identifying minor |
| Child wearable badge | `sr-child-guardian` | Paired Lost or ICE identity per approved product purpose | guardian consent, published info review, policy/legal approval |
| Elder identification badge | `sr-elder-assist` | Paired ICE identity or approved Lost use | privacy/health wording, physical QA |

**Do not** add new literal `tag_type` values (`child`, `elder`, `keychain`) without an explicit database/API/activation ADR. These are physical product labels and profiles/purpose choices, not automatically new QR types.

## 4. Geometry and print layout contract

For each approved variant, specify in millimeters:

- `label_width_mm`, `label_height_mm`: full finished outer label; independently set; not necessarily square.
- `bleed_mm`, `safe_inset_mm`, `cut_clearance_mm`: substrate/print-house approved values.
- `qr_box_x_mm`, `qr_box_y_mm`, `qr_symbol_size_mm`: region enclosing the entire QR including 4-module quiet zone.
- `header_rect`, `caption_rect`, `logo_geometry`: normalized or mm geometry from approved restricted layout schema.
- `qr_module_count` determined at render time by URL length / QR version; module size `p = qr_symbol_size_mm / (m + 8)` for an `m × m` matrix and 4 quiet modules each side. Reject if the resulting module pitch falls below independently validated printer/media/scanner limits.
- Wrapper decoration must never overlap the `qr_symbol_size_mm` bounding box, including the quiet zone. If a template places a colored border around QR, there must be a scan-safe buffer beyond the quiet zone and sufficient contrast.
- Center overlay may cover QR modules only within an approved, empirically validated logo footprint. Error correction (v1.2 M/Q baseline; Q candidate for logo artwork) does **not** guarantee scan success; confirm longest URL, worst-case module density, actual production prints, paper/material, laminate/gloss, blur, distance, low light and multiple phone scanners.
- Fixed template layouts must be tested in both languages and every offered size. If text cannot fit, use short reviewed copy or disallow that variant/template mapping—never shrink fonts to unreadable sizes or truncate Urdu.
- Bleed and cutting lines must be outside QR quiet zone. PDF page scaling must be actual size (100%); QA verifies printed dimensions with physical ruler/caliper.

**Sizing caveat:** v1.2's 30×30 / 35×35 mm requirement applies to the QR symbol including quiet zone, not the entire branded label. A small 30×30 mm *wrapper with bilingual footer* would make the symbol smaller than baseline; do not offer this as a valid print size unless a specific physical standard is re-approved after measured QA. Catalog size values should distinguish `qr_symbol_size_mm` from outer label dimensions rather than overload `product_variants.size_mm` without a documented definition.

### 4.1 Layout schematic, not to scale

```text
┌───────────────────────────────┐  outer label/cut size
│ SafeReturn  •  LOST ITEM      │  header outside QR symbol
│   ┌───────────────────────┐   │
│   │  white QUIET ZONE     │   │
│   │  ▣ QR DATA + logo ▣   │   │  QR region is scanner-safe
│   │  white QUIET ZONE     │   │
│   └───────────────────────┘   │
│ Found this item? Scan to      │
│ contact its owner.            │  footer outside QR symbol
│ [reviewed Urdu message]       │
└───────────────────────────────┘
```

## 5. Source-data mapping and migration design (Document 03)

**Existing compatible v1.2 schema:** `product_variants(template_key, template_version, fulfillment_method, size_mm)`, immutable order snapshots (`order_items.template_key_snapshot`, `template_version_snapshot`, `size_mm_snapshot`), `order_item_qr_uses`, `tag_pairs`, `qr_codes`, `print_jobs(template_fingerprint, render_config, job_revision)`, and `print_artifacts`. **Reuse these; do not introduce a second source of truth for pair identity or printing quantity.**

**New approved migration proposal:** create `print_templates` and `print_template_revisions`, and map eligibility via `print_template_variant_bindings`. Each revision owns its bilingual immutable message snapshots; use a separate `print_template_translations` table only if multilingual message sets evolve beyond two languages. Below is a target proposal; apply with reviewed numbered migrations, not at application startup.

```sql
-- Proposed next revision. Review against real Supabase schema before execution.
CREATE TABLE print_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    template_key text NOT NULL UNIQUE,
    name text NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('lost','ice','mixed')),
    lifecycle_status text NOT NULL DEFAULT 'draft'
        CHECK (lifecycle_status IN ('draft','active','retired')),
    created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT print_template_key_nonempty CHECK (char_length(trim(template_key)) > 0)
);

CREATE TABLE print_template_revisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id uuid NOT NULL REFERENCES print_templates(id) ON DELETE RESTRICT,
    version integer NOT NULL CHECK (version >= 1),
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','pending_qa','published','retired')),
    layout_json jsonb NOT NULL,
    label_width_mm numeric(7,2) NOT NULL CHECK (label_width_mm > 0),
    label_height_mm numeric(7,2) NOT NULL CHECK (label_height_mm > 0),
    qr_symbol_size_mm numeric(7,2) NOT NULL CHECK (qr_symbol_size_mm > 0),
    message_en text NOT NULL CHECK (char_length(trim(message_en)) > 0),
    message_ur text NOT NULL CHECK (char_length(trim(message_ur)) > 0),
    assets_manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
    fingerprint_sha256 char(64),
    qa_report_ref text,
    published_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(template_id, version),
    CONSTRAINT revision_published_has_fingerprint CHECK
      (status <> 'published' OR (fingerprint_sha256 IS NOT NULL AND published_at IS NOT NULL))
);
CREATE INDEX idx_print_revision_template ON print_template_revisions(template_id,version DESC);

CREATE TABLE print_template_variant_bindings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id uuid NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
    tag_type text NOT NULL CHECK (tag_type IN ('lost','ice')),
    template_revision_id uuid NOT NULL REFERENCES print_template_revisions(id) ON DELETE RESTRICT,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_active_variant_tag_template
    ON print_template_variant_bindings(variant_id,tag_type)
    WHERE is_active = true;
```

**DDL vs application invariants:** a SQL `CHECK` cannot ensure that `layout_json` geometry fits physically, that a published revision is immutable, that bindings match tag purpose and variant size, or that all public templates are QA-approved. Enforce these via transactional service validation, least-privilege permissions, and database triggers/privileges as appropriate. Restrict direct table DML. Allow only a reviewed approved transition `draft → pending_qa → published → retired`; publication cannot be reversed to draft or updated in place. Fingerprint SHA-256 must cover *canonicalized* layout JSON, text, logo/font asset checksums, renderer contract version and printing geometry; exclude volatile timestamps.

**Optional locale scaling:** If a new language is approved, add `print_template_messages(template_revision_id, locale, header, instruction, ...)` with `(template_revision_id, locale)` uniqueness; **do not simultaneously make both normalized table and old `message_en`/`message_ur` independently authoritative.** For v1.3 P0 the two fixed columns suffice.

### 5.1 Precedence and compatibility rules for existing columns

1. For new orders, resolved binding `(variant_id, tag_type)` supplies the **published** `template_revision_id`, while `product_variants.template_key`/`template_version` remain compatible human-readable/default catalog references. If both populated, they must resolve to the same published revision or checkout/print must reject with configuration error. No competing independent selection path.
2. `order_items.template_key_snapshot` and `.template_version_snapshot` remain immutable purchase-time fields, but an order line containing both Lost and ICE usages may need **per-usage** revision snapshots. **Never assume one order-item-level template applies equally to both tags.** Implement a reviewed extension, either columns on `order_item_qr_uses` (`template_revision_id_snapshot`, `template_fingerprint_snapshot`) or a one-to-one `order_item_print_occurrence_specs` table keyed by `(order_item_qr_use_id, size/variant grouping)`. Do **not** invent a new `qr_codes` row per occurrence.
3. The `print_jobs.render_config` stores an immutable **render manifest** with per-usage QR id, expected copies, physical size, selected template key/revision/fingerprint, asset/font checksums, output group order, and renderer version. Store only server-accessible bindings; raw public token is not copied into routine logs.
4. Existing v1.2 orders/jobs keep their historical template association. Backfill legacy template references by validated mapping when possible; do **not** rewrite historical QR URLs or fabricate a revision for an unknown template. Mark uncertain jobs `legacy_review_required` in a separate migration audit/report; don't mutate existing status enums without explicit migration.
5. Existing v1.2 `print_artifacts` continue to hold private PDF hash/bytes/object key/expiry; no need for one artifact per physical sticker. Reprints use same QR tokens and frozen revision.
6. A `print_template_variant_bindings` row must not be deleted if referenced by history; retire binding (`is_active=false`) and make a fresh binding for future orders.

### 5.2 Migration execution (non-destructive expand/backfill/contract)

- Inspect live schema and migration head (do not trust illustrative `CREATE TABLE IF NOT EXISTS`). Generate schema diff.
- **Expand:** add new tables, indexes and optional nullable per-usage snapshot fields. Add RLS, least-privilege grants and audit triggers.
- **Seed:** create two candidate templates and revisions in `draft`, validate both physically, record review, publish and bind to eligible sticker variants.
- **Backfill:** map any existing variant key/version carefully, log unresolved legacy mappings, do not force bad assumptions.
- **Application rollout:** write new print-manifest fields on new orders while reading old and new formats; feature-gate production renderer switch.
- **Contract:** make new references required only once all affected active variants/orders use approved mapping. Require tested rollback that restores old renderer for legacy jobs without deleting printed identity/history.
- Store actual SQL migration IDs/versions in repository after schema inspection; example SQL above is a proposal, not safe to run blindly.

## 6. API amendment (Document 04)

**Do not change existing API IDs `API-090`, `API-232`–`API-237`, `API-242`–`API-244`, or payments/catalog routes.** Extend new `API-245` onwards only after verifying Doc 04 registry for clashes; these are **proposed reserved identifiers**, not automatically implemented endpoints. All routes are under `/api/v1` and require RBAC/MFA as appropriate. Sensitive mutations require request tracing, audit and idempotency.

| ID | Method and proposed path | Access | Contract |
|---|---|---|---|
| API-245 | `GET /admin/print-templates` | Ops/catalog staff | Filter by purpose/status, pagination, label sizes, published revision |
| API-246 | `POST /admin/print-templates` | Print-design admin + MFA | Create draft template key/purpose; reject duplicate key |
| API-247 | `GET /admin/print-templates/{template_id}` | Authorized staff | Metadata + revision list, publication state; no confidential customer data |
| API-248 | `POST /admin/print-templates/{template_id}/revisions` | Print-design admin + MFA | Create a NEW draft revision from approved base, never modify published revision |
| API-249 | `PATCH /admin/print-templates/{template_id}/revisions/{revision_id}` | Print-design admin + MFA | Optimistic version (`If-Match`), permitted draft fields only |
| API-250 | `POST /admin/print-templates/{template_id}/revisions/{revision_id}/preview` | Authorized designer/QA | Validated synthetic data only; short-lived staff-only preview, no public URL |
| API-251 | `POST /admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa` | Designer/QA roles | Validate geometry, locale text, scan report and material matrix |
| API-252 | `POST /admin/print-templates/{template_id}/revisions/{revision_id}/publish` | Approver + MFA | QA-approved revision becomes immutable published revision; audit |
| API-253 | `POST /admin/print-template-bindings` | Ops/catalog admin + MFA | Bind approved revision to `(variant_id, tag_type)` with conflict protection |
| API-254 | `GET /admin/print-template-bindings` | Ops/catalog staff | Effective bindings, variants, types, sizes, invalid mapping alerts |
| API-255 | `POST /admin/print-templates/{template_id}/revisions/{revision_id}/retire` | Approver + MFA | Prevent future usage; existing order snapshots retained; verify replacement mapping |

### 6.1 Endpoint examples

**Create a draft revision** (synthetic example; template ID resolved server side):

```json
{
  "version_note": "Improve Urdu instruction spacing",
  "label_dimensions_mm": {"width":"55.00","height":"75.00"},
  "qr_symbol_size_mm": "35.00",
  "layout": {
    "schema_version": 1,
    "layout_mode": "fixed-footer",
    "qr_placement": "centered",
    "header_style": "lost",
    "footer_alignment": "center",
    "bleed_mm": "2.00",
    "safe_inset_mm": "2.50"
  },
  "messages": {
    "en": "Found this item? Scan to contact its owner.",
    "ur": "اگر یہ چیز آپ کو ملی ہے تو مالک سے رابطے کے لیے اسکین کریں۔"
  }
}
```

Use strict Pydantic models with `extra=forbid`, decimal strings for geometry, whitelisted styling only (no HTML, scripts, remote SVG fetches or arbitrary fonts), bounded text length, validated locale content, and stable response envelope. The frontend only previews; the authoritative geometry/publishing validator runs server side.

**Preview response** (illustrative, restricted):

```json
{
  "revision_id":"<uuid>",
  "validation_status":"needs_physical_scan_qa",
  "warnings":["Urdu text requires human approval"],
  "preview":{"kind":"short_lived_staff_asset","expires_at":"2026-10-12T15:30:00Z"},
  "fingerprint":"<sha256>"
}
```

**Publishing:** `409 TEMPLATE_QA_REQUIRED` if no approved scanner/material review; `409 TEMPLATE_REVISION_IMMUTABLE` if an edit targets published revision; `422 TEMPLATE_GEOMETRY_INVALID` if QR/text overlap or size incompatible; `409 TEMPLATE_BINDING_CONFLICT` for conflicting active assignments; `403 PRINT_TEMPLATE_ROLE_REQUIRED` for insufficient authorization; `410 TEMPLATE_PREVIEW_EXPIRED` for expired preview. Ensure standard Doc 04 error schema matches these proposed codes.

### 6.2 Extensions to existing endpoints

- Catalog APIs (`API-220`–`API-229`): admin product variant editor can select only eligible published bindings; do not let public catalog enumerate internal template drafts/secret assets. Public pages show customer-safe wrapper visuals only.
- Quote/checkout endpoints (`API-203/204`, `API-060`–`API-062`): check active published template eligibility for every physical usage and size. Freeze the correct per-usage revision. Fail configuration before charging/placing order; do not recalculate from mutable template settings after checkout.
- Existing batch `API-090`: generation remains one pair per requested pair count, not per sticker/wrapper. Batch logo config is a QR symbol/logo resource, **not** the outer wrapper template.
- Existing print `API-232`–`API-237`: job responses include frozen template references/fingerprints, locale coverage, QA requirements, byte counts, and safe validation warnings; restricted download still uses API-236. `POST .../print-jobs` never mints new QR identities on reprint.
- Existing art/storage APIs stay private; never publish raw PDF via Cloudinary or unprotected signed URL.
- Add documented API contract tests and produce/validate actual FastAPI OpenAPI 3.1 during implementation. This Markdown does not claim a full runnable OpenAPI file exists.

## 7. Backend module and worker changes (Document 02)

Keep FastAPI modular monolith, Supabase Postgres, Next.js, private Supabase Storage, Cloudinary public-media model, and existing durable print-worker pattern. Introduce these **functions/services**, not new microservices:

```text
backend/
  app/
    services/
      print_templates.py     # lookup, lifecycle, binding, validation, fingerprints
      print_geometry.py      # exact physical units, bounds, quiet-zone validation
      qr_artwork.py          # existing QR symbol + approved centered SafeReturn logo
      print_renderer.py      # compose wrapper + instructions + QR into vector PDF
      print_manifest.py      # immutable order usage, copies, sizes, frozen revision
    routers/
      admin_print_templates.py  # proposed API-245..255
    workers/
      print_jobs.py         # existing durable job handler, no separate service mandated
    db/
      migrations/          # match actual repo migration system (Alembic baseline)
```

This is a suggested separation, not a demand to duplicate modules already present. Respect existing project structure and Doc 05 coding standards.

### 7.1 Deterministic render algorithm

1. Receive `PrintJobQueued(order_id, job_revision)` only after payment is **verified**, pair(s) **allocated**, and snapshot/eligibility checks pass.
2. Query immutable order-item QR usages, canonical QR identity URLs and template revision snapshots using server-only data access. Assert exact Lost/ICE counts and pair association.
3. Validate all order usages have compatible published or historically frozen template versions, usable font/logo assets, output dimensions and scanner QA policy.
4. Assemble occurrences sorted by `tag_type` order **Lost then ICE**, then approved variant grouping/order; ensure 3 Lost copies all decode to the same Lost URL and 2 ICE copies decode to same ICE URL.
5. Build QR module geometry from canonical URL; apply bounded center logo after selected approved ECC/scanner test contract; reserve 4-module white quiet zone.
6. Compose branded header/footer/wrapper outside symbol region using fixed safe layout and embedded Unicode/Urdu shaping-capable fonts. Language direction independent per text block.
7. Render vector-first PDF at exact millimeter coordinates, add cutting guides outside quiet zone, deduplicate QR and logo/font objects, compress and calculate SHA-256 + byte size.
8. Produce server-side render validation evidence and require physical scan/print QA before marking QA-passed; retryable rendering failures must leave order/payment truth untouched.
9. Store one private versioned PDF artifact and minimal print-job metadata in Supabase Storage/Postgres; admin download only through existing restricted flow.
10. On confirmed delivery plus approved grace/holds, delete private PDF via existing retention worker; retain frozen manifest/template revision, QR binding, order/item details and audit.

### 7.2 Idempotency / consistency

- Stable key `(order_id, job_revision, template_manifest_fingerprint)`; retries must not produce two different 'current' ready artifacts or duplicate pair allocation.
- Never fetch *latest published template* during an old-job retry or reprint: use frozen revision/fingerprint; an explicit authorized rework is a new job revision with a reason/audit and approved new artifact only when policy allows.
- If fonts or referenced assets disappear, fail safely and alert operator; don't silently substitute materially different artwork. Keep protected immutable asset versions/checksums or reproducible bundled assets.
- Use minimal metadata and structured logging without QR raw tokens, owner names, medical notes, payment screenshots or plaintext secrets.
- Do not delete shared template assets while historical snapshots need them for authorized reprints; asset retention differs from short-lived order PDF retention.

## 8. UI/UX amendment (Document 11)

### P0 screens (existing, no new public route)

- **Public product detail:** show approved visual example of Lost and Emergency label, realistic physical wrapper/QR dimension depiction, bilingual text sample, distinct scan area; no false claim that the image equals an actual customer's token.
- **Customer cart/checkout/orders:** show sticker copy type, size, quantities and branded wrapper thumbnail; QR identity count remains paired; final costs still server sourced.
- **Admin Ready to Ship (`/admin/ready-to-ship`) and Print Job (`/admin/print-jobs/[jobId]`):** add `Template / Revision`, message language review status, per-size printable label proof, count/QA checklist, private PDF download, reprint reason, and proper failure/hold states. Printed proofs are restricted, not public.
- **Admin Products / Variants:** select from published approved template binding for that variant/QR type; prevent incompatible sizes or missing English/Urdu text.

### P1 new staff screens (proposed frontend routes; must align with API IDs)

| Screen ID | Proposed route | Design specification |
|---|---|---|
| ADM-30 | `/admin/print-templates` | Library cards/table by name, purpose, status, version, compatible variants, language readiness; create template CTA |
| ADM-31 | `/admin/print-templates/new` | Restricted predefined-template wizard, fixed layout presets, purpose and product mapping |
| ADM-32 | `/admin/print-templates/[templateId]` | Revision history, draft/published badges, currently mapped products, audit and retirement |
| ADM-33 | `/admin/print-templates/[templateId]/revisions/[revisionId]` | Form-based header/footer color, safe regions, English/Urdu text, symbol size, live two-locale proof (staff synthetic), validation, submit for QA |
| ADM-34 | `/admin/print-templates/[templateId]/revisions/[revisionId]/qa` | Measured sample and scanner/device/material test matrix, approval sign-off, publish gate |

Do not create unbounded WYSIWYG/drag-drop rendering as P0. Use **preset layouts + constrained fields**. Screens must use SafeReturn teal/white/ink UI tokens and highly readable Inter / approved Urdu fonts. Mobile admin behavior must be practical, though production geometry proof should advise desktop for detailed QA.

**UI labels:** `Template`, `QR purpose`, `Printed size`, `QR scan area`, `English message`, `Urdu message`, `Preview`, `Submit for QA`, `Publish revision`, `Mapped variants`, `Regenerate PDF`. Use realistic demo/synthetic QR only; never print live credentials in generic design mocks. Empty, loading, validation, expired preview, conflicting binding, unsuccessful physical QA, publish success, and permission-denied states required.

## 9. Security, privacy and abuse cases (Document 07)

1. Template creation/publishing restricted to staff print-design/QA roles with MFA, separation of duties for high-risk edits where feasible, and immutable audit logs. Production staff can download approved jobs but not upload arbitrary executable template code.
2. **No arbitrary HTML, CSS, JavaScript, remote image/SVG URLs, shell commands or user-controlled code** is accepted as a render template. Strict whitelist of geometry/layout properties. SVG/font/logo sources must be vetted, size-bounded, MIME/content-validated, malware-checked where appropriate, and safely embedded. Prevent SSRF, XML external entities, path traversal and PDF active content.
3. Synthetic/preview labels use synthetic QR links. No private customer data, finder messages, medical notes, full contact numbers, payment details, QR activation secret or real order manifests in unrestricted previews.
4. Logo is not proof of authorized issuance; do not claim that copied branding prevents QR spoofing. Verified domain and server-side validation underpin trust. Consider printed anti-tamper measures only as distinct physical controls.
5. Download grant short lifetime, private bucket, role and order authorization, no public CDN cache for private PDF. Signatures/URLs treated as bearer credentials; redact from logs and analytics.
6. Image and font licenses must authorize commercial reproduction. Urdu copy must receive language, accessibility, and privacy/safety review; no unsupported medical claims.
7. Preserve legal holds and retention: deleting generated PDFs after policy does not delete shared template revisions/assets, immutable order specs or audit. Payment screenshot retention remains separate and unchanged.
8. Reject unauthorized template-to-variant cross-reference, cross-tenant QR printing, revoked token printing, and draft/unapproved template deployment. Require audit for template retirement and reprints.
9. Ensure secure processing resource ceilings for renderer: maximum image/font size, max copies/pages, memory/time limits, and retries with backoff. Avoid accidentally exhausting worker/storage with malicious drafts.
10. Protect future child/elder templates with separate guardian/medical-content review; printed text should not expose sensitive identifiers.

## 10. Testing and acceptance (Document 08)

Implement these additional tests with synthetic data. They supplement, not replace, Document 08 v1.2 cases.

| Test ID | Test | Expected |
|---|---|---|
| WRAP-T001 | 3 Lost + 2 ICE same pair, sizes vary | Exactly 5 physical occurrences, 2 unique valid URLs, correct grouping/order |
| WRAP-T002 | 3 copies of Lost QR | All three decode to exactly the same Lost URL and profile |
| WRAP-T003 | One user, several pairs | Correct per-pair QR, no accidental cross-pair reuse |
| WRAP-T004 | ICE vs Lost label | Correct distinct approved bilingual purpose copy/templates |
| WRAP-T005 | Wrapper/cut line intersects QR quiet zone | Template rejected, job not released |
| WRAP-T006 | QR symbol smaller than approved minimum | Variant/binding rejected unless approved override with QA evidence |
| WRAP-T007 | Longest permitted URL and centered logo on real sticker | Decodes across approved device/material/lighting matrix |
| WRAP-T008 | Urdu shaping on every approved label size | Proper glyph formation, RTL order, not clipped, readable |
| WRAP-T009 | Admin edits published template | Rejected; new draft revision required |
| WRAP-T010 | New revision published during old order reprint | Reprint uses old frozen revision or audited explicit approved override |
| WRAP-T011 | New checkout with incompatible variant binding | Fails before order acceptance/payment rather than substituting template |
| WRAP-T012 | Printer retries same job | Idempotent; no duplicate pair, QR token, or conflicting current artifact |
| WRAP-T013 | Payment unverified | No printable ready job/download grant |
| WRAP-T014 | Unauthorized staff preview/download | 403 and audited denial, no object leak |
| WRAP-T015 | Malicious SVG/URL/HTML in template fields | Strict validation, no SSRF/script/external resource loads |
| WRAP-T016 | PDF size vs equivalent raster labels | Vector PDF remains bounded, records byte size; no unsupported hard-coded limit claim |
| WRAP-T017 | Completed shipment and retention time | File deleted on schedule unless hold; immutable order/QR/template history retained |
| WRAP-T018 | Missing historical template logo/font | Safe failure and operator recovery; no silent style change |
| WRAP-T019 | Cloudinary marketing asset removed | Private historical print job reproducibility not broken if protected asset is retained |
| WRAP-T020 | Feature flag off for future template editor | P0 fixed templates still work; P1 routes/actions unavailable |
| WRAP-T021 | QR logo mimicked on fake wrapper | No special activation rights; security depends on entitlement and verified host |
| WRAP-T022 | Multiple print copies attached to same QR | Customer dashboard shows one QR card with shared profile; no duplicate QR identities |
| WRAP-T023 | Child/elder products not approved | No purchasable catalog variant or usable production template |
| WRAP-T024 | Product variant changed after order | Historical order and reprint use snapshot SKU/size/message/template |
| WRAP-T025 | Manual payment switch to future gateway | Template selection/print eligibility still triggered only by canonical `verified` payment status |

**Physical QA minimum:** record real scanner/device types, URL density, printed dimensions, material and lamination, normal/poor lighting, one-handed angled scans, center logo variants, small and large sizes, Urdu legibility, cutting and wear. PASS criteria must be measured/agreed before launch rather than invented here. Release blocked by any cross-owner leak, unsafe print, incorrect URLs, unreadable mandatory label, credential exposure, or unapproved payment.

## 11. Implementation backlog (Document 06)

| Ticket | Priority | Task / dependency | Done when |
|---|---|---|---|
| WRAP-01 | P0 | Approve label geometry/copy/logo assets and print-house test matrix | Founder + print QA + native Urdu review sign off |
| WRAP-02 | P0 | Inspect v1.2 schema; design additive revision/binding migration | Reviewer approves no-breaking migration; tests run on PostgreSQL |
| WRAP-03 | P0 | Seed two fixed Lost/ICE published template revisions and safe asset manifest | Validated, versioned and mapped to sticker variants |
| WRAP-04 | P0 | Build strict binding resolver and geometry/purpose validator | Mismatch/invalid/unknown templates refused safely |
| WRAP-05 | P0 | Extend immutable per-usage print manifest/snapshots | Correct frozen revisions for both tag types and all sizes |
| WRAP-06 | P0 | Compose vector wrapper, bilingual text and approved center QR logo | Render test suite, font embedding and dimension checks |
| WRAP-07 | P0 | Integrate with existing durable PDF worker/private Supabase Storage | Authenticated ready-job download, retries and hash/size records |
| WRAP-08 | P0 | Update print QA, packaging and SOP procedures | Physical scan matrix and ordered copies pass |
| WRAP-09 | P0 | Extend storefront preview and ops print-job screen | Clearly distinguishes full label from QR symbol and reflects snapshots |
| WRAP-10 | P0 | Security, test and rollout/rollback rehearsals | ST/WRAP tests pass, launch approvals recorded |
| WRAP-11 | P1 | Build admin templates API CRUD/revision/preview/publish routes | Role/MFA, optimistic locking, audit, OpenAPI contract pass |
| WRAP-12 | P1 | Build Admin Print Templates screen set | Designs navigable, validation/QA/publish flows functional |
| WRAP-13 | P1 | Gate future product templates by QA and policy | Keychains/badges only publish after approved release gates |

**Build order:** WRAP-01 → WRAP-02/03 → WRAP-04/05 → WRAP-06 → WRAP-07/08/09 → WRAP-10. P1 follows successful P0 pilot. Do not allocate whole QR pairs per copy.

## 12. Operations and rollout amendment (Document 09 / 10)

- Confirm canonical production domain and SafeReturn logo ownership before manufacturing. Test printed scan to that exact domain and correct Lost/ICE public routes.
- Keep fixed published template revisions in source-controlled configuration or DB (DB authoritative revision), versioned with asset checksums; private immutable assets need separate lifecycle from short-lived per-order PDFs.
- Create staging sample orders for each size/material; verify real print scaling and color. Compare full outer label, QR symbol, cut lines, actual ruler measurement and bilingual message legibility.
- Deploy schema expand and seeded drafts first; production renderer behind `print_wrappers_v13_enabled=false`, turn on only after QA and authorized release. Rollback disables new rendering; it does not revoke already-shipped printed public tokens.
- Keep v1.2 legacy render path temporarily for historical orders; publish compatibility mapping report and review exceptions.
- Monitor `render_failed`, `binding_missing`, `geometry_invalid`, `qa_failed`, PDF output bytes, render duration, signed download denials, retry storms and private-bucket growth. No raw QR URLs in log events.
- Private PDF retention/deletion grace remains policy driven; e.g. prior seven-day proposal is not a final mandate. Automatic deletion must respect dispute, refund and reprint holds and preserve DB snapshots.
- P1 changes to templates require draft → review → physical QA → published workflow; live published revisions remain immutable.

## 13. Per-document change index and precedence mapping

| v1.2 document | Additive amendment | Unchanged |
|---|---|---|
| 01 PRD | WRAP-FR-001..018 + size/wrapper distinction + bilingual purpose copy | Paired kit, activation, payments, ownership, commerce |
| 02 Technical Design | Constrained template resolver, geometry/layout and render pipeline | FastAPI monolith, worker, Supabase/Cloudinary assignments |
| 03 Database | `print_templates`, revision/bindings, per-usage snapshot extension | Existing pairs, QR IDs, order lines, print jobs and artifacts |
| 04 API Contract | Proposed API-245..255, preview/publish, existing route extensions | Auth, checkout/payment, API-090, API-232..244 |
| 05 Agent Instructions | Read this amendment and never silently change published template/QR security rules | Existing agent review and production boundaries |
| 06 Implementation Plan | WRAP-01..13 tasks, dependency and release gates | Other v1.2 milestones/tickets |
| 07 Security & Privacy | Template injection/upload threat, access and immutable revision audit | Existing ICE, payment, ownership, evidence rules |
| 08 Test Plan | WRAP-T001..025 + physical sample QA | All v1.2 cases and stop-ship rules |
| 09 Deployment | Versioned asset rollout, flags, monitoring, rollback | Vercel/Railway/Supabase topology, retention providers |
| 10 Fulfillment SOP | Wrapper dimensions, messages, trim/bleed, font/scan checks | QA custody, allocation, packaging, ship/reprints |
| 11 UI/UX | P0 proof updates + P1 ADM-30..34 print template screens | All  existing public/customer/admin screen IDs and shells |

## 14. Founder / engineering decisions to record before release

| Decision | Proposed default | Blocking? |
|---|---|---|
| WRAP-DEC-01: Logo source/style | Official vector SafeReturn symbol with approved bounded white backing | Yes for physical print |
| WRAP-DEC-02: Initial sticker outer sizes | Choose sizes accommodating minimum QR and two languages; test printer | Yes |
| WRAP-DEC-03: English/Urdu text | Two short purpose messages above, edited/approved by local reviewer | Yes |
| WRAP-DEC-04: Minimum module pitch/logo coverage | Derived from real devices/production test matrix | Yes |
| WRAP-DEC-05: Product variant `size_mm` meaning | Explicitly distinguish `label_*` and `qr_symbol_size_mm` | Yes before catalog launch |
| WRAP-DEC-06: Template management scope | P0 locked presets, P1 constrained admin editor | Recommended |
| WRAP-DEC-07: Historical jobs/template backfill | Allow audited legacy render for unknown old templates | Yes for migration if historic jobs exist |
| WRAP-DEC-08: Font licensing and Urdu typography | Commercial-use license, embedded/subset shaping validated | Yes |
| WRAP-DEC-09: QA reviewer / publish role separation | Founder-approved privileged print QA workflow | Yes for P1 |
| WRAP-DEC-10: PDF size soft budgets | Measure and set alerts per variant/page counts; no universal invented cap | Before scale-up |

## 15. Exact instructions for Codex / Antigravity

> Implement SafeReturn according to Documents 01–11 v1.2 plus Document 12 v1.3. Treat the amendment as authoritative only for branded QR wrapper, bilingual print-message, template versioning/mapping and related PDF/QA/UI requirements; preserve all unrelated v1.2 invariants. First inspect repository, actual Supabase schema, migration head, API contract and current renderer. Report conflicts, especially per-tag usage template snapshots and what `product_variants.size_mm` means, before writing migrations. Work one WRAP ticket per branch. Never invent extra QR identities for copies, make private PDFs public, permit public-token activation, or mutate a published template in place. Run SQL/Postgres integration, API, render, physical scan QA and permission tests. State test evidence truthfully. No production migrations, bank actions, mass file deletion or live shipping without explicit founder approval.

### Agent task prompt example — WRAP-04

```text
Read AGENTS.md, SafeReturn Documents 01–05 v1.2, Document 12 v1.3 §§3–7.
Implement only WRAP-04: versioned template binding resolution and validation.
Inspect actual migrations; do not guess table names.
Inputs: product variant ID, tag type (lost/ice), immutable order usage snapshot.
Output: one approved revision ID + fingerprint or explicit contract error.
Enforce size/type/locale and immutable published-revision rules.
Do not build a drag-and-drop editor, change checkout/payment state, or modify QR ownership.
Add and run PostgreSQL integration and API tests; report files/commands/results.
```

## 16. Traceability and completion checklist

- [ ] Product owner approves print-template scope and bilingual copy.
- [ ] QR and wrapper have separate, calibrated real-world dimensions.
- [ ] Two fixed templates are versioned and physically scan-tested.
- [ ] Live QR data remains distinct from centered brand image and wrappers.
- [ ] Lost and ICE message types are correct, independent and bilingual.
- [ ] All five occurrences for 3 Lost + 2 ICE use exactly two unique QR URLs.
- [ ] Order-item/usage snapshot contains historical template revision/fingerprint.
- [ ] Print PDF is compact, private, repeatable, and contains no plaintext activation secret.
- [ ] Admin preview and download permissions protect customer and print data.
- [ ] New P1 template revisions cannot overwrite published/history.
- [ ] Product variant bindings fail safely and do not alter existing order prices.
- [ ] CI/security/API/physical QA evidence is recorded; no untested launch claims.
- [ ] Deployment, retention and rollback have founder approval.

**End of Document 12 (v1.3 amendment).** The eleven v1.2 documents remain the baseline; this file is the narrowly scoped authoritative change overlay.
