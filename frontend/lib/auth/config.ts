import { validateOrigin } from "../api/transport";

export function authConfig() {
  const origin = validateOrigin(process.env.SAFERETURN_WEB_ORIGIN
    ?? (process.env.NODE_ENV === "development" ? "http://localhost:3000" : ""));
  const url = validateOrigin(process.env.SAFERETURN_SUPABASE_URL ?? "");
  const key = process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY ?? "";
  if (!url.startsWith("https://") || !key.startsWith("sb_publishable_")) {
    throw new Error("Authentication configuration unavailable");
  }
  return { origin, url, key };
}
