import {guardedBackendFetch} from '../../../lib/api/quarantine';
import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";
const headers = { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" };
export async function POST(request: NextRequest) {
  try {
    const session = await verifiedSession();
    if (!session) return NextResponse.json({ error: { code: "AUTH_REQUIRED" } }, { status: 401, headers });
    const origin = authConfig().origin;
    if (request.headers.get("origin") !== origin) return NextResponse.json({ error: { code: "FORBIDDEN" } }, { status: 403, headers });
    const { order_id, body, key } = await request.json();
    if (typeof order_id !== "string" || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(order_id) || typeof key !== "string" || !/^[A-Za-z0-9._:-]{8,160}$/.test(key)) return NextResponse.json({ error: { code: "VALIDATION_ERROR" } }, { status: 400, headers });
    const r = await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "")}/api/v1/me/orders/${order_id}/cancel`, { method: "POST", cache: "no-store", redirect: "error", signal: AbortSignal.timeout(20000), headers: { Authorization: `Bearer ${session.token}`, Origin: origin, "Content-Type": "application/json", "Idempotency-Key": key }, body: JSON.stringify(body) });
    if (!r.ok) return NextResponse.json({ error: { code: r.status === 409 ? "CONFLICT" : "UNAVAILABLE" } }, { status: r.status, headers });
    return NextResponse.json(await r.json(), { status: r.status, headers });
  } catch { return NextResponse.json({ error: { code: "UNAVAILABLE" } }, { status: 503, headers }); }
}
