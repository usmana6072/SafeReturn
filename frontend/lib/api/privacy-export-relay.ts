import {guardedBackendFetch} from './quarantine';
import {quarantineResponse} from './quarantine-response';
import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../auth/server";
import { authConfig } from "../auth/config";
import { validateOrigin } from "./transport";

const headers = { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" };
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export async function privacyRelay(request: NextRequest, admin: boolean) {
  // Admin metadata uses the independently gated adapter. Never revive decisions
  // through this obsolete admin branch or bypass its metadata gate.
  if(admin)return quarantineResponse();
  try {
    const session = await verifiedSession();
    if (!session) return NextResponse.json({ error: { code: "AUTH_REQUIRED" } }, { status: 401, headers });
    let path = admin ? "/admin/privacy/exports" : "/me/privacy/exports";
    let body, key, grant;
    if (request.method === "GET") {
      const allowed = admin ? ["limit", "cursor"] : ["id"];
      if ([...request.nextUrl.searchParams.keys()].some(k => !allowed.includes(k) || request.nextUrl.searchParams.getAll(k).length !== 1)) return NextResponse.json({ error: { code: "INVALID_QUERY" } }, { status: 400, headers });
      if (admin) path += "?" + request.nextUrl.searchParams.toString();
      else {
        const id = request.nextUrl.searchParams.get("id") ?? "";
        if (!uuid.test(id)) return NextResponse.json({ error: { code: "INVALID_REQUEST" } }, { status: 400, headers });
        path += "/" + id;
      }
    } else {
      if (request.headers.get("origin") !== authConfig().origin) return NextResponse.json({ error: { code: "FORBIDDEN" } }, { status: 403, headers });
      if (Number(request.headers.get("content-length") || 0) > 8192) return new NextResponse(null, { status: 413, headers });
      const input = await request.json();
      const actions = admin ? ["decisions"] : ["request", "download-grants", "download"];
      if (!actions.includes(input.action) || input.action !== "request" && !uuid.test(input.id ?? "")) return NextResponse.json({ error: { code: "INVALID_REQUEST" } }, { status: 400, headers });
      if (input.action !== "request") path += "/" + input.id + "/" + input.action;
      body = input.body;
      if (input.action === "download") grant = request.headers.get("x-privacy-grant");
      else {
        if (typeof input.key !== "string" || !/^[A-Za-z0-9._:-]{8,160}$/.test(input.key)) return NextResponse.json({ error: { code: "INVALID_REQUEST" } }, { status: 400, headers });
        key = input.key;
      }
    }
    const response = await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "") + "/api/v1" + path, {
      method: request.method, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${session.token}`, Origin: authConfig().origin,
        ...(request.method === "POST" ? { "Content-Type": "application/json" } : {}),
        ...(key ? { "Idempotency-Key": key } : {}), ...(grant ? { "X-Privacy-Grant": grant } : {}) },
      ...(request.method === "POST" ? { body: JSON.stringify(body ?? {}) } : {}),
    });
    if (response.ok && response.headers.has("content-disposition")) return new NextResponse(response.body, { status: response.status, headers: { ...headers, "Content-Type": "application/json", "Content-Disposition": 'attachment; filename="safereturn-basic-v1.json"' } });
    return NextResponse.json(await response.json(), { status: response.status, headers });
  } catch { return NextResponse.json({ error: { code: "EXPORT_SERVICE_UNAVAILABLE" } }, { status: 503, headers }); }
}
