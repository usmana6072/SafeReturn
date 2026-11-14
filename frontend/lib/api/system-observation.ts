import { ApiError, createApiClient } from "./transport";
export type Observation = { state: "responded" | "unavailable" | "unconfigured" | "unknown"; checked_at: string };
export async function observeLiveness(origin: string, fetchImpl: typeof fetch = fetch): Promise<Observation> {
  let state: Observation["state"] = "unknown";
  try { await createApiClient({ origin, timeoutMs: 5000, fetchImpl }).getLiveness(); state = "responded"; }
  catch (error) {
    if (error instanceof ApiError) state = error.kind === "configuration" ? "unconfigured" : error.kind === "contract" ? "unknown" : "unavailable";
  }
  // The timestamp is a completed transport observation, never a heartbeat,
  // readiness result, provider acceptance or backup verification timestamp.
  return { state, checked_at: new Date().toISOString() };
}
