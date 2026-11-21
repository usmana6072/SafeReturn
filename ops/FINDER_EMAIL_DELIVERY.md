# Finder inbox and domain email

Finder submission commits the encrypted message and its notification event in one
transaction. The customer sees the message at `/inbox` independently of email
delivery. The form confirms success only after an accepted API receipt; validation
and API failures retain the form for retry with the same idempotency key.

Apply migration `0058_finder_email_details` after
`0057_downloaded_print_shipping`, preserving any other installed Alembic branch.
The migration adds one lease-scoped function for the notification worker; it
does not grant general access to message/contact/location tables. Deploy the
backend and frontend changes together after the migration.

On 2026-11-20, migration `0058_finder_email_details` was rehearsed with rollback,
then committed to the configured Supabase project and independently verified.
The existing `0044_support_dev_exception` branch, existing function definitions
and permissions, and message/outbox counts were preserved. The restricted worker
login was verified against the new function; requests without a matching lease
return no finder information. No live email was sent during migration.

For an environment still on `0057`, run the scoped release script from the repo
root with `PYTHONPATH=backend`: `python backend/scripts/release_finder_email.py`
rehearses and rolls back; add `--apply` to commit after checks. It uses the
configured migration URL without printing credentials and preserves other heads.

The API now processes finder notifications automatically when
`SAFERETURN_WORKER_DATABASE_URL`, `SAFERETURN_RESEND_API_KEY` and
`SAFERETURN_NOTIFICATION_FROM_EMAIL` are configured. The worker must have the same
`SAFERETURN_PROFILE_DATA_KEYS` keyring as the API. The sender must be an address
on the domain verified in Resend. The original customer's verified account email
is the recipient, never the finder email. Secrets stay on the backend.

For a separately operated notification service, set
`SAFERETURN_NOTIFICATION_WORKER_ENABLED=false` on the API and run
`python -m app.workers.notifications`. Both modes use the existing durable
leases, attempt fencing, provider idempotency and capped retries. API shutdown
stops new claims and drains its admitted iteration before closing the worker pool.
No other job is started by this change.

Email contains finder name, email, phone, preferred contact, submission time,
message, QR reference, consented location (when present), and an inbox link.
Finder input is HTML-escaped. Email status `sent` means Resend accepted the
request, not proof of inbox placement. Failed messages remain in the customer
portal; terminal email failures remain available to the existing operations
retry workflow.

Local verification (no hosted database or actual provider email):

```powershell
cd backend
./.venv/Scripts/python.exe -m pytest tests/test_notifications.py tests/test_finder_email_details.py tests/test_notification_service.py tests/test_finder_validation.py tests/test_messages.py -q
$env:SAFERETURN_FINDER_REHEARSAL='1'
$env:SAFERETURN_INDEPENDENT_FINANCE_REHEARSAL='1'
./.venv/Scripts/python.exe -m pytest tests/integration/test_finder_delivery_local.py -q
cd ../frontend
node scripts/test-finder-message.cjs
npm run typecheck
```

## Shipment delivery confirmations

Shipment creation now completes packing and dispatch in one transaction, preserving
the existing payment, allocation and print checks. The saved shipment starts as
`dispatched`; tracking is optional and can be saved later without changing the
status. The only next status exposed by the order shipment form is `delivered`.
Existing preparing/packed shipments can also be completed through that form;
their internal packing/dispatch checks run before delivery is recorded.

The form labels the former required Reason field **Delivery note (optional)**.
It is an internal audit note; a useful example is “Courier confirmed delivery”.
Blank notes use that default. **Received by (optional)** is a separate field and
is included in the customer email only when provided.

Marking delivered atomically saves the status and an encrypted, durable
`shipment.delivered` email event. The existing notification worker sends it from
`SafeReturn <services@safereturnqr.me>` to the customer's verified account email.
It includes the order, courier, tracking when available, delivered timestamp,
ordered items, optional receiver name and an order link. Finder emails retain
their configured sender. The existing retry and lease fencing also cover delivery
emails; repeated delivery submissions cannot enqueue another event.

Apply migration `0059_shipment_delivery_email` before deploying these changes.
This migration was rehearsed with rollback, then applied and independently
verified on the configured Supabase project on 2026-11-21. Existing shipment
statuses and records were left unchanged.
From the repository root with `PYTHONPATH=backend`, run
`python backend/scripts/release_shipment_delivery.py` for a rollback rehearsal,
then add `--apply` to commit after checks. This preserves the independent support
branch, unrelated functions, outbox guard permissions and existing message rows.
It sends no email and changes no existing shipment status.

Validation includes unit checks, a full disposable PostgreSQL order → printing →
shipment → customer email flow with a controlled provider, and the browser flow
in `frontend/tests/fulfillment-workflow.spec.ts`. The database flow checks missing
tracking, later tracking edits, optional notes, encrypted receiver details,
delivery receipt replay, duplicate suppression and rollback when queue encryption
fails. Actual Resend delivery is verified after deployment.
