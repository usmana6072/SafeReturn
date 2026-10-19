import { test, expect } from "@playwright/test";
import { ticket, readTicket, type ScanTicket } from "../lib/scan-ticket";
import { qrClient } from "../lib/qr-contract";

test("scan tickets reject tampering, wrong purpose and expiry", () => {
  process.env.SAFERETURN_SESSION_SIGNING_KEY = "ab".repeat(32);
  const now = Date.now(), value = { token: "synthetic_public_token", until: now + 900000 };
  const signed = ticket(value, "scan");
  expect(readTicket<ScanTicket>(signed, "scan", now)).toEqual(value);
  expect(readTicket(signed, "activation", now)).toBeNull();
  expect(readTicket(signed, "scan", now + 900001)).toBeNull();
  expect(readTicket(signed + "x", "scan", now)).toBeNull();
  expect(readTicket("forged", "scan", now)).toBeNull();
  expect(signed).not.toContain("https://");
});
test("QR transport carries conditional versions and idempotency without logging errors", async () => {
  const calls: RequestInit[] = [];
  const transport: typeof fetch = async (_input, init) => { calls.push(init!); return new Response(null, { status: 204 }); };
  const request = qrClient("http://127.0.0.1:8115", "synthetic-token", transport);
  await request("/me/qr/synthetic/ice-contacts/synthetic", "DELETE", undefined, 4);
  expect(calls[0].headers).toMatchObject({ "If-Match": '"4"', Authorization: "Bearer synthetic-token" });
  await request("/me/tag-pairs/activations", "POST", { confirm: true }, undefined, "synthetic-idempotency");
  expect(calls[1].headers).toMatchObject({ "Idempotency-Key": "synthetic-idempotency" });
  expect(calls.every(c => c.cache === "no-store" && c.redirect === "error")).toBe(true);
  const denied = qrClient("http://127.0.0.1:8115", undefined, async () => Response.json({ secret: "must-not-echo" }, { status: 412 }));
  await expect(denied("/me/qr")).rejects.toThrow("API request failed: http");
});
