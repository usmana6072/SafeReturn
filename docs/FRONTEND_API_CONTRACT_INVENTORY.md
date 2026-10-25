# Generated integration contract inventory

Generated from the current app without loading credentials. Empty response schemas require source/test review; security declarations do not prove live authorization.

| Method | Path | Operation | Bearer declared | JSON body | Success / error statuses |
|---|---|---|---|---|---|
| GET | `/api/v1/health/live` | API-001 | no | {} | 200 |
| GET | `/api/v1/health/ready` | API-002 | yes | {} | 200, 401, 404, 503 |
| GET | `/api/v1/me/staff-security` | staffSecurity | yes | {} | 200 |
| GET | `/api/v1/me` | API-020 | yes | {} | 200 |
| PATCH | `/api/v1/me` | API-021 | yes | {"additionalProperties": false, "properties": {"display_name": {"anyOf": [{"maxLength": 120, "type": "string"}, {"type": "null"}], "title": "Display Name"}, "preferred_locale": {"anyOf": [{"enum": ["en", "ur"], "type": "string"}, {"type": "null"}], "title": "Preferred Locale"}}, "title": "ProfileEdit", "type": "object"} | 200, 422 |
| GET | `/api/v1/me/privacy-consents` | API-022 | yes | {} | 200 |
| POST | `/api/v1/me/account-deletion-requests` | API-023 | yes | {"properties": {"confirm": {"type": "boolean", "const": true, "title": "Confirm"}, "reason": {"anyOf": [{"type": "string", "maxLength": 1000}, {"type": "null"}], "title": "Reason"}}, "additionalProperties": false, "type": "object", "required": ["confirm"], "title": "DeletionRequest"} | 202 |
| GET | `/api/v1/admin/audit-events` | API-100 | yes | {} | 200, 422 |
| GET | `/api/v1/public/products` | API-003 | no | {} | 200, 422 |
| GET | `/api/v1/public/products/{sku}` | API-004 | no | {} | 200, 422 |
| GET | `/api/v1/public/catalog/featured` | API-201 | no | {} | 200 |
| GET | `/api/v1/public/catalog/categories` | API-200 | no | {} | 200 |
| GET | `/api/v1/public/catalog/products/{product_id}/variants` | API-202 | no | {} | 200, 422 |
| POST | `/api/v1/me/checkout/quotes` | API-203 | yes | {"$ref": "#/components/schemas/QuoteRequest"} | 201, 422 |
| POST | `/api/v1/me/checkout/quotes/{quote_id}/confirm` | API-204 | yes | {"$ref": "#/components/schemas/ConfirmRequest"} | 201, 422 |
| POST | `/api/v1/me/orders` | API-060 | yes | {} | 409 |
| GET | `/api/v1/me/orders` | API-061 | yes | {} | 200, 422 |
| GET | `/api/v1/me/shipping-addresses` | API-068 | yes | {} | 200 |
| POST | `/api/v1/me/shipping-addresses` | API-067 | yes | {"$ref": "#/components/schemas/CreateAddress"} | 201, 422 |
| PATCH | `/api/v1/me/shipping-addresses/{address_id}` | API-069 | yes | {"$ref": "#/components/schemas/UpdateAddress"} | 200, 422 |
| DELETE | `/api/v1/me/shipping-addresses/{address_id}` | API-070 | yes | {} | 204, 422 |
| GET | `/api/v1/admin/products` | API-220 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/products` | API-221 | yes | {"$ref": "#/components/schemas/ProductRequest"} | 201, 422 |
| GET | `/api/v1/admin/catalog/categories` | API-227 | yes | {} | 200 |
| POST | `/api/v1/admin/catalog/categories` | API-228 | yes | {"$ref": "#/components/schemas/CategoryRequest"} | 201, 422 |
| PATCH | `/api/v1/admin/catalog/categories/{category_id}` | API-229 | yes | {"$ref": "#/components/schemas/CategoryRequest"} | 200, 422 |
| PATCH | `/api/v1/admin/products/{product_id}` | API-222 | yes | {"$ref": "#/components/schemas/ProductRequest"} | 200, 422 |
| POST | `/api/v1/admin/products/{product_id}/variants` | API-223 | yes | {"$ref": "#/components/schemas/VariantRequest"} | 201, 422 |
| PATCH | `/api/v1/admin/product-variants/{variant_id}` | API-224 | yes | {"$ref": "#/components/schemas/VariantRequest"} | 200, 422 |
| POST | `/api/v1/admin/products/{product_id}/images` | API-225 | yes | {"$ref": "#/components/schemas/ImageRequest"} | 201, 422 |
| DELETE | `/api/v1/admin/products/{product_id}/images/{image_id}` | API-226 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/qr-batches` | API-090 | yes | {"$ref": "#/components/schemas/BatchRequest"} | 201, 400, 403, 409, 503, 422 |
| GET | `/api/v1/admin/qr-batches` | API-091 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/tag-pairs` | API-084 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/tag-pairs/{pair_id}` | API-085 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/qr-batches/{batch_id}` | API-092 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/inventory/summary` | API-230 | yes | {} | 200 |
| GET | `/api/v1/public/qr/{token}/activation-context` | API-207 | no | {} | 200, 422 |
| POST | `/api/v1/me/tag-pairs/activation-intents` | API-208 | yes | {"$ref": "#/components/schemas/IntentRequest"} | 201, 422 |
| POST | `/api/v1/me/tag-pairs/activations` | API-032 | yes | {"$ref": "#/components/schemas/ConfirmationRequest"} | 201, 422 |
| GET | `/api/v1/me/qr/{qr_id}/lost-profile` | API-040 | yes | {} | 200, 422 |
| PUT | `/api/v1/me/qr/{qr_id}/lost-profile` | API-041 | yes | {"$ref": "#/components/schemas/LostEdit"} | 200, 422 |
| GET | `/api/v1/me/qr/{qr_id}/ice-profile` | API-042 | yes | {} | 200, 422 |
| PUT | `/api/v1/me/qr/{qr_id}/ice-profile` | API-043 | yes | {"$ref": "#/components/schemas/ICEEdit"} | 200, 422 |
| GET | `/api/v1/me/qr/{qr_id}/ice-contacts` | API-044 | yes | {} | 200, 422 |
| POST | `/api/v1/me/qr/{qr_id}/ice-contacts` | API-045 | yes | {"$ref": "#/components/schemas/ContactEdit"} | 201, 422 |
| PATCH | `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | API-046 | yes | {"$ref": "#/components/schemas/ContactEdit"} | 200, 422 |
| DELETE | `/api/v1/me/qr/{qr_id}/ice-contacts/{contact_id}` | API-047 | yes | {} | 204, 422 |
| GET | `/api/v1/me/qr/{qr_id}/contact-preferences` | API-048 | yes | {} | 200, 422 |
| PUT | `/api/v1/me/qr/{qr_id}/contact-preferences` | API-049 | yes | {"$ref": "#/components/schemas/PreferenceEdit"} | 200, 422 |
| GET | `/api/v1/me/tag-pairs` | API-030 | yes | {} | 200, 422 |
| GET | `/api/v1/me/tag-pairs/{pair_id}` | API-031 | yes | {} | 200, 422 |
| GET | `/api/v1/me/qr` | API-205 | yes | {} | 200, 422 |
| GET | `/api/v1/me/qr/{qr_id}` | API-206 | yes | {} | 200, 422 |
| GET | `/api/v1/public/qr/{token}` | API-010 | no | {} | 200, 422 |
| POST | `/api/v1/me/orders/{order_id}/payment-attempts` | API-210 | yes | {"$ref": "#/components/schemas/PaymentRequest"} | 201, 422 |
| GET | `/api/v1/me/orders/{order_id}/payment-attempts` | API-209 | yes | {} | 200, 422 |
| POST | `/api/v1/me/payment-attempts/{attempt_id}/evidence-uploads` | API-211 | yes | {"$ref": "#/components/schemas/UploadRequest"} | 200, 422 |
| POST | `/api/v1/me/payment-attempts/{attempt_id}/evidence-finalize` | API-212 | yes | {"$ref": "#/components/schemas/EvidenceRequest"} | 200, 422 |
| POST | `/api/v1/admin/payment-attempts/{attempt_id}/reviews` | API-241 | yes | {"$ref": "#/components/schemas/ReviewRequest"} | 200, 422 |
| GET | `/api/v1/admin/payment-evidence/{evidence_id}` | payment-evidence-read | yes | {} | 200, 422 |
| GET | `/api/v1/admin/orders/{order_id}/payment-attempts` | API-240 | yes | {} | 200, 422 |
| GET | `/api/v1/me/tag-pairs/{pair_id}/activation-history` | API-034 | yes | {} | 200, 422 |
| PATCH | `/api/v1/me/qr/{qr_id}/public-status` | API-035 | yes | {"$ref": "#/components/schemas/Command"} | 200, 422 |
| GET | `/api/v1/admin/print-jobs/counts` | API-350 | yes | {} | 200 |
| GET | `/api/v1/admin/print-jobs` | API-349 | yes | {} | 200 |
| POST | `/api/v1/admin/orders/{order_id}/print-jobs` | API-234 | yes | {"$ref": "#/components/schemas/PrintJobRequest"} | 202, 422 |
| GET | `/api/v1/admin/orders/{order_id}/print-jobs` | API-233 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/print-jobs/{job_id}` | API-235 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/print-artifacts/{artifact_id}/download-grants` | API-236 | yes | {} | 201, 422 |
| POST | `/api/v1/admin/print-downloads` | print-download-redeem | yes | {"$ref": "#/components/schemas/DownloadRequest"} | 200, 422 |
| POST | `/api/v1/admin/print-jobs/{job_id}/qa` | API-237 | yes | {"$ref": "#/components/schemas/JobQARequest"} | 200, 422 |
| POST | `/api/v1/admin/tag-pairs/{pair_id}/print-qa` | API-094 | yes | {"$ref": "#/components/schemas/PrintQARequest"} | 201, 422 |
| GET | `/api/v1/me/orders/{order_id}/print-summary` | API-213 | yes | {} | 200, 422 |
| GET | `/api/v1/me/orders/{order_id}` | API-062 | yes | {} | 200, 422 |
| GET | `/api/v1/me/orders/{order_id}/shipments` | API-066 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/orders/ready-to-ship` | API-232 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/shipments` | API-095 | yes | {"$ref": "#/components/schemas/ShipmentRequest"} | 201, 422 |
| GET | `/api/v1/admin/shipments` | API-246 | yes | {} | 200, 422 |
| PATCH | `/api/v1/admin/shipments/{shipment_id}` | API-096 | yes | {"$ref": "#/components/schemas/ShipmentUpdate"} | 200, 422 |
| GET | `/api/v1/admin/shipments/{shipment_id}` | API-247 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/orders/{order_id}` | API-081 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/orders` | API-080 | yes | {} | 200, 422 |
| POST | `/api/v1/public/qr/{token}/finder-messages` | API-015 | no | {"$ref": "#/components/schemas/FinderMessageRequest"} | 202, 422 |
| POST | `/api/v1/public/qr/{token}/messages` | API-011 | no | {"$ref": "#/components/schemas/FinderMessageRequest"} | 202, 422 |
| POST | `/api/v1/public/qr/{token}/contact-reveals` | API-012 | no | {"$ref": "#/components/schemas/ContactRevealRequest"} | 200, 422 |
| POST | `/api/v1/public/qr/{token}/whatsapp-link` | API-013 | no | {"$ref": "#/components/schemas/WhatsAppRequest"} | 200, 422 |
| GET | `/api/v1/public/config` | API-005 | no | {} | 200, 422, 503 |
| POST | `/api/v1/public/abuse-reports` | API-014 | no | {"$ref": "#/components/schemas/Report"} | 202, 4XX, 400, 405, 409, 413, 415, 429, 503 |
| GET | `/api/v1/admin/notification-outbox` | API-101 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/notification-outbox/{id}/retry` | API-102 | yes | {"$ref": "#/components/schemas/Retry"} | 202, 422 |
| GET | `/api/v1/me/finder-messages` | API-050 | yes | {} | 200, 422 |
| GET | `/api/v1/me/finder-messages/{message_id}` | API-051 | yes | {} | 200, 422 |
| PATCH | `/api/v1/me/finder-messages/{message_id}` | API-052 | yes | {"$ref": "#/components/schemas/MessageUpdate"} | 200, 422 |
| DELETE | `/api/v1/me/finder-messages/{message_id}` | API-053 | yes | {} | 204, 422 |
| GET | `/api/v1/admin/finance/sheet-sync` | API-238 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/finance/sheet-sync/{sync_id}/retry` | API-239 | yes | {} | 202, 422 |
| GET | `/api/v1/admin/storage/artifacts` | API-242 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/storage/artifacts/{artifact_id}/cleanup-retry` | API-245 | yes | {"$ref": "#/components/schemas/RetentionHoldRequest"} | 202, 422 |
| POST | `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | API-243 | yes | {"$ref": "#/components/schemas/RetentionHoldRequest"} | 201, 422 |
| DELETE | `/api/v1/admin/storage/artifacts/{artifact_id}/retention-holds` | API-244 | yes | {} | 204, 422 |
| GET | `/api/v1/admin/support-cases` | API-097 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/support-cases` | API-098 | yes | {"$ref": "#/components/schemas/Intake"} | 201, 422 |
| PATCH | `/api/v1/admin/support-cases/{case_id}` | API-099 | yes | {"$ref": "#/components/schemas/Change"} | 200, 422 |
| POST | `/api/v1/me/privacy/exports` | API-325 | yes | {"$ref": "#/components/schemas/app__api__v1__privacy_exports__ExportRequest"} | 202, 422 |
| GET | `/api/v1/me/privacy/exports/{request_id}` | API-326 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/privacy/exports` | API-330 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/privacy/exports/{request_id}/decisions` | API-327 | yes | {"$ref": "#/components/schemas/app__api__v1__privacy_exports__Decision"} | 200, 422 |
| POST | `/api/v1/me/privacy/exports/{request_id}/download-grants` | API-328 | yes | {"$ref": "#/components/schemas/Revision"} | 200, 422 |
| POST | `/api/v1/me/privacy/exports/{request_id}/download` | API-329 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/catalog/approved-templates` | API-339 | yes | {} | 200, 401, 403, 405, 422, 503 |
| GET | `/api/v1/admin/print-templates` | API-300 | yes | {} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates` | API-301 | yes | {"$ref": "#/components/schemas/Create"} | 201, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| GET | `/api/v1/admin/print-templates/{template_id}` | API-302 | yes | {} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions` | API-303 | yes | {"$ref": "#/components/schemas/NewRevision"} | 201, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| PATCH | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}` | API-304 | yes | {"$ref": "#/components/schemas/DraftEditRequest"} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/preview` | API-305 | yes | {"$ref": "#/components/schemas/Preview"} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/submit-qa` | API-306 | yes | {"$ref": "#/components/schemas/Reason"} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/publish` | API-307 | yes | {"$ref": "#/components/schemas/Publish"} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| GET | `/api/v1/admin/print-template-bindings` | API-309 | yes | {} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-template-bindings` | API-308 | yes | {"$ref": "#/components/schemas/Bind"} | 201, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/admin/print-templates/{template_id}/revisions/{revision_id}/retire` | API-310 | yes | {"$ref": "#/components/schemas/Retire"} | 200, 400, 401, 403, 404, 405, 409, 412, 413, 422, 429, 503 |
| POST | `/api/v1/me/orders/{order_id}/cancel` | API-065 | yes | {"$ref": "#/components/schemas/CancellationRequest"} | 202, 422 |
| POST | `/api/v1/admin/orders/{order_id}/cancellation-reconciliations` | API-340 | yes | {"$ref": "#/components/schemas/Reconciliation"} | 200, 422 |
| POST | `/api/v1/admin/orders/{order_id}/cancellation-decisions` | API-341 | yes | {"$ref": "#/components/schemas/app__api__v1__cancellations__Decision"} | 200, 422 |
| POST | `/api/v1/admin/tag-pairs/{pair_id}/release-allocation` | API-087 | yes | {"$ref": "#/components/schemas/Release"} | 200, 422 |
| GET | `/api/v1/admin/support-cases/{case_id}/financial-review` | API-324 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/support-cases/{case_id}/financial-decisions` | API-323 | yes | {"$ref": "#/components/schemas/FinancialDecision"} | 200, 422 |
| GET | `/api/v1/admin/finance/reconciliation` | API-342 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/finance/reconciliation/counts` | API-343 | yes | {} | 200 |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports` | API-093 | yes | {"$ref": "#/components/schemas/app__api__v1__manufacturing_exports__ExportRequest"} | 202, 422 |
| GET | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}` | API-336 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download-grants` | API-338 | yes | {"$ref": "#/components/schemas/GrantRequest"} | 200, 422 |
| POST | `/api/v1/admin/qr-batches/{batch_id}/print-exports/{job_id}/download` | API-337 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/dashboard/summary` | API-344 | yes | {} | 200 |
| GET | `/api/v1/admin/dashboard/trends` | API-345 | yes | {} | 200, 422 |
| GET | `/api/v1/admin/users` | API-346 | yes | {} | 200 |
| GET | `/api/v1/admin/users/count` | API-348 | yes | {} | 200 |
| GET | `/api/v1/admin/users/{user_id}` | API-347 | yes | {} | 200, 422 |
| POST | `/api/v1/admin/users/{user_id}/suspensions` | API-320 | yes | {"$ref": "#/components/schemas/Suspend"} | 200, 422 |
| POST | `/api/v1/admin/users/{user_id}/restorations` | API-321 | yes | {"$ref": "#/components/schemas/Restore"} | 200, 422 |
| POST | `/api/v1/admin/users/{user_id}/recovery-escalations` | API-322 | yes | {"$ref": "#/components/schemas/Recovery"} | 202, 422 |

