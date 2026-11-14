# SafeReturn Customer Portal — Prototype gap analysis

## Evidence and confidence

**Directly inspected:** uploaded Gemini single-file HTML prototype, including its mock state and handlers. **Historical context:** project PRD, API, technical, security and UX v1.2 search results explicitly describe themselves as proposed and primarily assume QR pairs. These are *not* evidence that an independent-QR backend route exists. **Newer independent-QR phases:** referenced in project conversation, but their complete schemas, implementation handoff reports and live OpenAPI were not available in this audit. Therefore no precise independent-QR DTO, requiredness or endpoint implementation is claimed verified. All standalone changes are mock UX behavior, not a replacement backend contract.

## Feature traceability and gaps

| Page / feature | Original prototype | Documented/latest project direction | Issue | Correction in deliverable | Evidence | Priority |
|---|---|---|---|---|---|---|
| Checkout payment | Automatically `Verified (Demo)` | Independent settlement verification before allocation | Fabricated approval | New order starts unpaid; payment submission becomes under review | Original `submitSimulatedOrder`; project architecture | Critical |
| QR allocation | Automatically allocated after order | One QR per logical order item, after verified payment | Premature allocation | New orders have no allocated QR | Original order submission; founder single-QR decision | Critical |
| Activation | Immediate toggle; claimed 5-minute window | Purchaser entitlement, delivered item, expiring intent, final confirmation | No intent check | Simulated five-minute intent; blocks ineligible fixtures; explicit disclaimer | Original `startActivationFlow`, `executeActivation`; Phase 7 summary | Critical |
| Emergency privacy | Medical toggle only | Separate publication and disclosure consent | Missing safeguards | Explicit medical and contact consent, private defaults | Original emergency editor; security principles | Critical |
| Emergency contact | Remove only | Manage name, relationship, phone and display order | Missing create/edit | Add/remove/edit draft contacts, order assigned | Original `removeEmergencyContact` | High |
| Blood group | Only A+, B+, O+, AB+ | Support all standard ABO/Rh choices | Incomplete selection | Eight choices plus unspecified | Original emergency editor | High |
| Lost WhatsApp | Toggle without phone editor or consent | Opt-in disclosure | Consent/data gap | Number and explicit disclosure consent | Original lost editor | High |
| Sizes / copies | Only 1, 2, 5 copies | Per-size quantities, combined maximum, price per copy | Incomplete selection | Quantity per synthetic size, combined cap, computed subtotal | Original order modal; product copy pricing v1.4 | High |
| Product type | Every new order saved as Lost | Product-specific QR type | Incorrect data | Cart/order preserve product type | Original order submission | Critical |
| Inbox | Archive deletes array element | Archive should preserve record | Destructive simulation | Archive/restore and read status | Original `archiveMessage` | Medium |
| Address book | Add only; phone silently taken from account | Manage saved shipping addresses | Missing controls | Create/edit/default/delete and phone field | Original address view | High |
| Account | Read-only name; toast-only privacy actions | Account management, authenticated privacy requests | Nonfunctional/misleading | Editable synthetic display name; no fake server export/deletion | Original account view | High |
| Mobile | Wide table and crowded nav | Mobile-first usability | Overflow/hierarchy | Responsive cards and scrollable compact nav | Original CSS | Medium |
| Urdu | Only some nav strings | Bilingual customer portal | Partial translation | RTL and Urdu nav; detailed forms explicitly remain untranslated | Original dictionary | High |
| QR history | Data exists but no visible history | QR history visibility | Hidden capability | History modal | Original QR data | Medium |
| Live backend contract | Not included | Implemented vs documented separation | Cannot verify routes/DTOs | Marked as acceptance gate, no invented API | v1.2 docs marked proposed | Critical |

## Out of scope and intentionally not simulated as completed

Real MFA, payment settlement, real allocation, printing QA, courier integration, public finder scanning, token generation, ownership transfer, medical responder reveal, privacy export/deletion, QR-pair management, and live Supabase access. Existing delivered/verified order is **synthetic fixture only**. The prototype does not grant QR identities to unpaid orders.
