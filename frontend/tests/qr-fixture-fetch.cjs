// Loaded only by the isolated PostgreSQL/browser controller, never by app scripts.
const originalFetch = globalThis.fetch;
globalThis.fetch = function(input, init) {
  const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url);
  if (url.origin === "https://fixture.test") {
    url.protocol = "http:"; url.hostname = "127.0.0.1"; url.port = "8115";
    return originalFetch(url, init);
  }
  if (!["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)) throw new Error("External network disabled in QR fixture");
  return originalFetch(input, init);
};
