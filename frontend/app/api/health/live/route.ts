import { getServerApiClient } from "../../../../lib/api/server";

export const dynamic = "force-dynamic";

// Public operational check for the web-to-API connection; readiness remains private.
export async function GET() {
  const headers = { "Cache-Control": "no-store" };
  try {
    const liveness = await getServerApiClient().getLiveness();
    return Response.json(liveness, { headers });
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503, headers });
  }
}
