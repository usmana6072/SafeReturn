import { expect, test } from "@playwright/test";
import { ApiError, createApiClient, validateOrigin } from "../lib/api/transport";

function stub(response: Response): typeof fetch {
  return async () => response;
}

test("typed client uses the approved endpoint and safe request options", async () => {
  let requestedUrl = "";
  let options: RequestInit | undefined;
  const fetchImpl: typeof fetch = async (url, init) => {
    requestedUrl = String(url);
    options = init;
    return Response.json({ status: "ok" });
  };
  const client = createApiClient({ origin: "http://127.0.0.1:8000", fetchImpl });
  expect(await client.getLiveness()).toEqual({ status: "ok" });
  expect(requestedUrl).toBe("http://127.0.0.1:8000/api/v1/health/live");
  expect(options?.cache).toBe("no-store");
  expect(options?.redirect).toBe("error");
  expect(options?.headers).toEqual({ Accept: "application/json" });
});

test("configuration rejects credentials, unsafe protocols, paths and query strings", () => {
  for (const origin of ["invalid", "ftp://example.com", "http://example.com", "https://user:secret@example.com", "https://example.com/path", "https://example.com?key=secret", "https://example.com#secret"]) {
    expect(() => validateOrigin(origin)).toThrow("API request failed: configuration");
  }
  expect(validateOrigin("https://api.example.com/")).toBe("https://api.example.com");
  expect(validateOrigin("http://[::1]:8000")).toBe("http://[::1]:8000");
  expect(() => createApiClient({ origin: "https://api.example.com", timeoutMs: 0 })).toThrow(ApiError);
});

test("malformed and overexposing successful responses fail contract validation", async () => {
  for (const payload of [null, [], {}, { status: "ready" }, { status: "ok", secret: "private" }]) {
    const client = createApiClient({ origin: "https://api.example.com", fetchImpl: stub(Response.json(payload)) });
    await expect(client.getLiveness()).rejects.toMatchObject({ kind: "contract" });
  }
  for (const response of [new Response("not json"), new Response("{", { headers: { "content-type": "application/json" } })]) {
    const client = createApiClient({ origin: "https://api.example.com", fetchImpl: stub(response) });
    await expect(client.getLiveness()).rejects.toMatchObject({ kind: "contract" });
  }
});

test("HTTP and network failures omit upstream private details", async () => {
  const client = createApiClient({ origin: "https://api.example.com", fetchImpl: stub(new Response("private-provider-detail", { status: 503 })) });
  await expect(client.getLiveness()).rejects.toMatchObject({ kind: "http", status: 503, message: "API request failed: http" });
  const offline = createApiClient({ origin: "https://api.example.com", fetchImpl: async () => { throw new Error("private-provider-detail"); } });
  await expect(offline.getLiveness()).rejects.toMatchObject({ kind: "network", message: "API request failed: network" });
});

test("slow requests are aborted and reported as timeouts", async () => {
  const fetchImpl: typeof fetch = async (_url, options) => new Promise((_resolve, reject) => {
    options?.signal?.addEventListener("abort", () => reject(new Error("upstream timeout")), { once: true });
  });
  const client = createApiClient({ origin: "https://api.example.com", timeoutMs: 20, fetchImpl });
  await expect(client.getLiveness()).rejects.toMatchObject({ kind: "timeout" });
});
