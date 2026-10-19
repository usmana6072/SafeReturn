import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";
export async function GET(request: NextRequest) { return relay(request); }
export async function POST(request: NextRequest) { return relay(request); }
async function relay(request: NextRequest) {
 const session = await verifiedSession();
 if (!session) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
 if (request.method === "POST" && request.headers.get("origin") !== authConfig().origin) return NextResponse.json({ error: "Access denied" }, { status: 403 });
 try {
 const payload = request.method === "POST" ? await request.json() : null;
 const path = payload?.path ?? request.nextUrl.searchParams.get("path");
 if (typeof path !== "string" || !/^\/admin\/(products(?:\/[a-f0-9-]{36}(?:\/(?:variants|images)(?:\/[a-f0-9-]{36})?)?)?|product-variants\/[a-f0-9-]{36}|catalog\/categories(?:\/[a-f0-9-]{36})?)$/.test(path)) return NextResponse.json({ error: "Invalid request" }, { status: 400 });
 const method = payload?.method ?? "GET";
 if (!["GET","POST","PATCH","DELETE"].includes(method)) return NextResponse.json({ error: "Invalid request" }, { status: 400 });
 const origin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "");
 const response = await fetch(`${origin}/api/v1${path}${payload?.authorize_upload === true ? "?authorize_upload=true" : ""}`, { method, cache:"no-store", redirect:"error", signal:AbortSignal.timeout(15000), headers:{ Authorization:`Bearer ${session.token}`, "Content-Type":"application/json", ...(payload?.key ? {"Idempotency-Key":String(payload.key)} : {}), ...(payload?.version ? {"If-Match":`"${payload.version}"`} : {}) }, body:payload?.body === undefined ? undefined : JSON.stringify(payload.body) });
 return NextResponse.json(await response.json(), { status:response.status, headers:{"Cache-Control":"no-store"} });
 } catch { return NextResponse.json({ error:"Catalog unavailable" }, { status:503 }); }
}
