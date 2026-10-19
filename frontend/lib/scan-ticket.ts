import { createHmac, timingSafeEqual } from "node:crypto";

export type ScanTicket = { token: string; until: number };
export type ActivationTicket = { actor: string; intent: string; pair: string; key: string; until: number };
function sign(value: string, purpose: string) {
  const key = process.env.SAFERETURN_SESSION_SIGNING_KEY ?? "";
  if (!/^[a-f0-9]{64}$/.test(key)) throw new Error("Session configuration unavailable");
  return createHmac("sha256", Buffer.from(key, "hex")).update(`SafeReturn:${purpose}:v1:${value}`).digest();
}
export function ticket(value: ScanTicket | ActivationTicket, purpose: "scan" | "activation") {
  const payload = Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${payload}.${sign(payload, purpose).toString("base64url")}`;
}
export function readTicket<T extends ScanTicket | ActivationTicket>(value: string | undefined, purpose: "scan" | "activation", now = Date.now()): T | null {
  try {
    if (!value || value.length > 1400) return null;
    const [payload, signature, extra] = value.split(".");
    if (extra !== undefined || !signature) return null;
    const actual = Buffer.from(signature, "base64url"), expected = sign(payload, purpose);
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) return null;
    const data = JSON.parse(Buffer.from(payload, "base64url").toString());
    if (!Number.isSafeInteger(data.until) || data.until <= now || data.until > now + 900000) return null;
    if (purpose === "scan" && !/^[A-Za-z0-9_-]{1,80}$/.test(data.token)) return null;
    if (purpose === "activation" && (![data.actor, data.intent, data.pair].every(v => typeof v === "string" && /^[a-f0-9-]{36}$/i.test(v)) || !/^[a-f0-9-]{36}$/i.test(data.key))) return null;
    return data;
  } catch { return null; }
}
