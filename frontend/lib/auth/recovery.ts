import { createHash, createHmac, timingSafeEqual } from "node:crypto";

function key() {
  const value = process.env.SAFERETURN_SESSION_SIGNING_KEY ?? "";
  if (!/^[a-f0-9]{64}$/.test(value)) throw new Error("Recovery unavailable");
  return Buffer.from(value, "hex");
}

export function recoveryTicket(token: string, now = Date.now()) {
  const payload = Buffer.from(JSON.stringify({ until: now + 600000,
    binding: createHash("sha256").update(token).digest("hex") })).toString("base64url");
  return payload + "." + createHmac("sha256", key()).update(payload).digest("base64url");
}

export function recoveryAllowed(ticket: string, token: string, now = Date.now()) {
  try {
    if (ticket.length > 512) return false;
    const parts = ticket.split(".");
    if (parts.length !== 2) return false;
    const signature = Buffer.from(parts[1], "base64url");
    const expected = createHmac("sha256", key()).update(parts[0]).digest();
    if (signature.length !== expected.length || !timingSafeEqual(signature, expected)) return false;
    const payload = JSON.parse(Buffer.from(parts[0], "base64url").toString());
    return typeof payload.until === "number" && payload.until > now && payload.until <= now + 600000
      && payload.binding === createHash("sha256").update(token).digest("hex");
  } catch { return false; }
}
