# SafeReturn frontend

Node.js 24 was used for local verification. From this folder:

```powershell
npm ci
$env:NEXT_TELEMETRY_DISABLED="1"
npm run dev
```

Production verification: `npm run build`, `npm run typecheck`, then `npm test`.
Install test Chromium once with `npx playwright install chromium`.
Alternatively set `PLAYWRIGHT_CHANNEL=msedge` to use installed Microsoft Edge.
In restricted Windows environments, start the production server on port 3100,
set `PLAYWRIGHT_EXTERNAL_SERVER=1`, and run the tests against that server; stop
the server afterwards. This avoids blocked process-tree cleanup by the runner.

The homepage uses the approved teal mock layout, system font fallbacks, and
English/Urdu dictionaries. Language changes persist in a server-managed cookie
and set document language/direction before rendering. No font CDN is required.
Catalog shows an empty state pending Phase 5 live catalog implementation; no sample prices,
fake QR tokens, or future products are offered. Authentication and checkout
belong to later tasks. Native mobile navigation and FAQ disclosure work without
client JavaScript. Final fonts, brand artwork and Urdu copy require release QA.

## Local API integration

Start FastAPI on localhost:8000 using the backend README, then run `npm run dev`.
Development defaults the server-only API origin to `http://127.0.0.1:8000`.
Set `SAFERETURN_API_ORIGIN` explicitly for a production build/server; it accepts
an HTTPS origin, or HTTP on loopback for local development. Set it in the process
environment; the root `.env.example` lists names only and is not loaded automatically.

`GET /api/health/live` on Next.js checks FastAPI's `/api/v1/health/live`.
It returns `{ "status": "ok" }` on success, or a generic 503 unavailable response
on configuration, timeout, network, HTTP or response-contract failures.
Responses are not cached. The API origin is server-only; readiness tokens are
never forwarded. The browser calls its own origin, so CORS changes are unnecessary.

After `npm run build`, run `npm run test:integration:local` to start the actual
backend/frontend, execute tests, stop the backend and verify the web's outage
response, then stop the remaining process. The script uses ports 8100/3100 and
refuses occupied ports. Set `PLAYWRIGHT_CHANNEL=msedge` to use installed Edge.
Unit transport tests use explicit mocked HTTP responses; integration tests use
real local servers and are skipped in ordinary browser runs without an explicit
`SAFERETURN_TEST_API_ORIGIN`. No Supabase or provider credentials are required.
