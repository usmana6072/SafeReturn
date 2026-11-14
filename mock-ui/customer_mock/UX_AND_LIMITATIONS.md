# UX improvement summary and acceptance limitations

- Replaced large desktop tables with responsive cards and compact navigation; touch targets are at least 44 px tall.
- Teal/navy design, focus outlines, readable labels, dialog headings, feedback and explicit private/public states.
- Independent item identity and per-size copy calculations are visible during purchase.
- Payment submission explicitly stays under review, and new orders cannot activate or claim allocated stock.
- Consent-dependent WhatsApp and emergency publication now require separate acknowledgement.
- Added address editing/default/removal, inbox archive/restore, QR history and display-name editing.

## Not ready for final production design approval

1. Compare each field and status with the **actual current independent-QR OpenAPI and migrations**; the v1.2 retrieved documents describe a superseded pair architecture and are proposed, not deployment evidence.
2. Verify Phase 3–7 endpoints, product size lists, copy caps, required address/payment fields, activation intent lifetime and publication semantics.
3. Complete Urdu translations for all dynamic form content; only navigation and RTL are implemented.
4. Real MFA, payment verification, shipping, QR provisioning, activation, privacy requests, public emergency reveal and authenticated ownership cannot be tested in this offline prototype.
5. Independent real-device accessibility and visual QA remains necessary, including screen readers and full keyboard dialog focus trapping.
6. This is an in-memory prototype: refreshing resets data. File input is never uploaded; real browser storage and network are intentionally unused.
