# Field-level and backend-contract mapping

**Support key:** `Architecture` = described in newer project decisions or legacy proposed specifications, **not confirmed deployed**. `Unknown` = exact independent-QR API field name, enum, length or optionality requires live OpenAPI/service/schema verification. `Demo` = synthetic UI-only property.

| Form | Field | Prototype required? | Input | Validation in prototype | Backend support | Prototype status |
|---|---|---|---|---|---|---|
| Account | display name | Yes on edit | text | max 120 | Unknown exact DTO | Editable demo |
| Account | email | Read-only | text | Fixture verified flag | Auth concept, actual status unknown | Display only |
| Account | preferred language | Optional | switch | en / ur | Architecture; exact storage unknown | Session-only |
| Lost QR | item label | Yes | text | max 120 | Architecture; exact limits unknown | Editable |
| Lost QR | description | No | textarea | max 1000 | Architecture; exact limits unknown | Editable |
| Lost QR | reward text | No | text | max 200 | Architecture; exact limits unknown | Editable |
| Lost QR | enabled | No | checkbox | boolean | Unknown exact state contract | Editable demo |
| Lost QR | profile published | No | checkbox | boolean | Architecture | Editable demo |
| Lost QR | WhatsApp enabled | No | checkbox | requires number + consent | Architecture | Editable demo |
| Lost QR | WhatsApp number | Conditional | tel | 10–15 digits, optional leading + | Exact format unknown | Editable demo |
| Lost QR | disclosure consent | Conditional | checkbox | required when WA enabled | Architecture | Editable demo |
| Emergency | identity label | Yes | text | max 120 | Unknown exact DTO | Editable demo |
| Emergency | display name | Yes | text | max 120 | Architecture | Editable demo |
| Emergency | blood group | No | select | ABO/Rh or unspecified | Enum unknown | Editable demo |
| Emergency | medical notes | No | textarea | max 2000 | Architecture | Editable demo |
| Emergency | medical publication | No | checkbox | requires medical consent | Architecture | Off by default |
| Emergency | medical consent | Conditional | checkbox | required when published | Architecture | Editable demo |
| Emergency | contacts publication | No | checkbox | consent + >=1 valid contact | Architecture | Off by default |
| Emergency | contact consent | Conditional | checkbox | required when contacts published | Architecture | Editable demo |
| Emergency contact | name | Yes | text | max 120 | Architecture | Add/edit/remove |
| Emergency contact | relationship | Yes | text | max 80 | Architecture; enum unknown | Add/edit/remove |
| Emergency contact | phone | Yes | tel | 9–20 characters with digits/spaces/hyphens | Exact format unknown | Add/edit/remove |
| Emergency contact | display order | Auto | integer | sequential from 1 | Architecture | Assigned by list order |
| Catalog | product identity / QR type | Server-defined | read-only | catalog fixture | Architecture | No client override |
| Catalog | sizes | Catalog-defined | numeric per size | integer >=0 | Architecture | Synthetic choices |
| Catalog | copies per size | At least one | number | combined 1–20 in fixture | Architecture; real max unknown | Calculated |
| Catalog | price per copy | Server-defined | read-only | PKR unit price fixture | Product Copy Pricing v1.4 | Immutable cart snapshot |
| Checkout | address | Yes | select | saved address exists | Architecture; exact DTO unknown | Functional |
| Payment | sender name | Yes in demo | text | max 120 | Proposed manual payment flow; exact DTO unknown | Submitted for review |
| Payment | bank/Raast reference | Yes in demo | text | max 120 | Proposed manual payment flow; exact DTO unknown | Submitted for review |
| Payment | transfer date | Yes in demo | date | browser date control | Proposed; exact DTO unknown | Submitted for review |
| Payment | evidence | No | file | png/jpeg/pdf accept; **not uploaded** | Proposed private evidence | Filename only |
| Activation | order item entitlement | No user-entered secret | selected fixture | eligible delivered/verified/allocated | Architecture; backend enforcement unverified | Simulated gate |
| Activation | intent expiry | Automatic | timestamp | 5 min local demo | Actual lifetime needs verification | Simulated |
| Address | label | Yes | text | max 60 | Exact DTO unknown | CRUD |
| Address | recipient | Yes | text | max 120 | Exact DTO unknown | CRUD |
| Address | phone | Yes | tel | 9–20 characters | Exact DTO unknown | CRUD |
| Address | street | Yes | text | max 240 | Exact DTO unknown | CRUD |
| Address | city | Yes | text | max 100 | Exact DTO unknown | CRUD |
| Inbox | read / archived | Action | boolean | in-memory state | Actual API actions unknown | Functional demo |

**Important:** Numeric lengths, 20-copy fixture cap, price amounts, size lists, payment requiredness and local intent duration are **prototype choices**, not verified backend limits. Do not use them as implementation contract. No real cancellation request is exposed because support was not verified.
