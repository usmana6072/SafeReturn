export type ApiFailureKind = "configuration" | "network" | "timeout" | "http" | "contract";

export class ApiError extends Error {
  constructor(public readonly kind: ApiFailureKind, public readonly status?: number) {
    // Response bodies, URLs, credentials and provider exception text stay private.
    super(`API request failed: ${kind}`);
    this.name = "ApiError";
  }
}

export type Liveness = { status: "ok" };

export function parseLiveness(value: unknown): Liveness {
  if (typeof value !== "object" || value === null || Array.isArray(value)
    || Object.keys(value).length !== 1 || !("status" in value) || value.status !== "ok") {
    throw new ApiError("contract");
  }
  return { status: "ok" };
}

export function validateOrigin(value: string): string {
  let url: URL;
  try { url = new URL(value); } catch { throw new ApiError("configuration"); }
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if ((url.protocol !== "https:" && !(url.protocol === "http:" && loopback))
    || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new ApiError("configuration");
  }
  return url.origin;
}

export function createApiClient(options: {
  origin: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}) {
  const origin = validateOrigin(options.origin);
  const timeoutMs = options.timeoutMs ?? 5000;
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 30000) {
    throw new ApiError("configuration");
  }
  const fetchImpl = options.fetchImpl ?? fetch;

  async function getJson<T>(path: string, parse: (value: unknown) => T): Promise<T> {
    const signal = AbortSignal.timeout(timeoutMs);
    let response: Response;
    try {
      response = await fetchImpl(`${origin}${path}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        redirect: "error",
        signal,
      });
    } catch {
      throw new ApiError(signal.aborted ? "timeout" : "network");
    }
    if (!response.ok) throw new ApiError("http", response.status);
    if (response.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
      throw new ApiError("contract");
    }
    let value: unknown;
    try { value = await response.json(); } catch {
      throw new ApiError(signal.aborted ? "timeout" : "contract");
    }
    return parse(value);
  }

  return {
    getLiveness: () => getJson("/api/v1/health/live", parseLiveness),
  };
}
