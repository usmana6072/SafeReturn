import {guardedBackendFetch} from '../../../../lib/api/quarantine';
import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../../lib/auth/server";
import { authConfig } from "../../../../lib/auth/config";
import { validateOrigin } from "../../../../lib/api/transport";

const headers = { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" };
async function relay(request: NextRequest) {
  try {
    const session = await verifiedSession();
    if (!session) return NextResponse.json({ error: { code: "AUTH_REQUIRED" } }, { status: 401, headers });
    const origin = authConfig().origin;
    if (request.method !== "GET" && request.headers.get("origin") !== origin)
      return NextResponse.json({ error: { code: "FORBIDDEN" } }, { status: 403, headers });
    let suffix = "", body;
    if (request.method !== "GET") {
      const data = await request.json();
      if (request.method !== "POST") {
        if (typeof data.id !== "string" || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(data.id))
          return NextResponse.json({ error: { code: "VALIDATION_ERROR" } }, { status: 400, headers });
        suffix = "/" + data.id;
      }
      if (request.method === "DELETE") {
        if (!Number.isInteger(data.expected_version) || data.expected_version < 1 || !Number.isInteger(data.expected_book_version) || data.expected_book_version < 0)
          return NextResponse.json({ error: { code: "VALIDATION_ERROR" } }, { status: 400, headers });
        suffix += `?expected_version=${data.expected_version}&expected_book_version=${data.expected_book_version}`;
      } else body = JSON.stringify(request.method === "POST" ? data : data.body);
    }
    const response = await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "")}/api/v1/me/shipping-addresses${suffix}`, {
      method: request.method, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(20000),
      headers: { Authorization: `Bearer ${session.token}`, Origin: origin, "Content-Type": "application/json" }, body,
    });
    if (response.status === 204) return new NextResponse(null, { status: 204, headers });
    if (!response.ok) return NextResponse.json({ error: { code: response.status === 409 ? "CONFLICT" : response.status === 401 ? "AUTH_REQUIRED" : response.status === 403 ? "FORBIDDEN" : "UNAVAILABLE" } }, { status: response.status, headers });
    return NextResponse.json(await response.json(), { headers, status: response.status });
  } catch { return NextResponse.json({ error: { code: "UNAVAILABLE" } }, { status: 503, headers }); }
}
export const GET = relay;
export const POST = relay;
export const PATCH = relay;
export const DELETE = relay;
