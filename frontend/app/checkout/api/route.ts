import { guardedBackendFetch } from "../../../lib/api/quarantine";
import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";

function isAllowedOrigin(originHeader: string | null): boolean {
  const configOrigin = authConfig().origin;
  if (originHeader === configOrigin) return true;
  if (process.env.NODE_ENV === "development" && originHeader) {
    try {
      const oUrl = new URL(originHeader);
      const cUrl = new URL(configOrigin);
      const loopbacks = ["localhost", "127.0.0.1", "[::1]"];
      if (
        loopbacks.includes(oUrl.hostname) &&
        loopbacks.includes(cUrl.hostname) &&
        oUrl.port === cUrl.port
      ) {
        return true;
      }
    } catch {
      // ignore
    }
  }
  return false;
}

export async function POST(request: NextRequest) {
  try {
    const session = await verifiedSession();
    if (!session) {
      return NextResponse.json({ error: { code: "AUTH_REQUIRED" } }, { status: 401 });
    }

    const origin = request.headers.get("origin");
    if (!isAllowedOrigin(origin)) {
      return NextResponse.json({ error: { code: "FORBIDDEN" } }, { status: 403 });
    }

    const bodyData = await request.json().catch(() => ({}));
    const { path, body, key } = bodyData;

    if (
      typeof path !== "string" ||
      !/^\/me\/checkout\/(?:quotes|item-quotes)(?:\/[a-f0-9-]{36}\/confirm)?$/.test(path) ||
      typeof key !== "string" ||
      !/^[A-Za-z0-9._:-]{8,160}$/.test(key)
    ) {
      return NextResponse.json({ error: { code: "VALIDATION_ERROR" } }, { status: 400 });
    }

    const response = await guardedBackendFetch(
      `${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "")}/api/v1${path}`,
      {
        method: "POST",
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(20000),
        headers: {
          Authorization: `Bearer ${session.token}`,
          Origin: authConfig().origin,
          "Content-Type": "application/json",
          "Idempotency-Key": key,
        },
        body: JSON.stringify(body),
      }
    );

    const data = await response.json().catch(() => ({}));
    console.log(`[checkout-api] path=${path} backend_status=${response.status} response_body=`, JSON.stringify(data));
    return NextResponse.json(data, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    console.error("[checkout-api] error:", err);
    return NextResponse.json(
      { error: { code: "PROVIDER_UNAVAILABLE" } },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
