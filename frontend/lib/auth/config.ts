import { validateOrigin } from "../api/transport";

const productionOrigin = "https://www.safereturnqr.me";
const previousOrigins = new Set(["https://safe-return-frontend.vercel.app", "https://safereturnqr.me"]);

export function webOrigin() {
  const configured = validateOrigin(process.env.SAFERETURN_WEB_ORIGIN
    ?? (process.env.NODE_ENV === "development" ? "http://localhost:3000" : productionOrigin));
  return previousOrigins.has(configured) ? productionOrigin : configured;
}

export function authConfig() {
  const origin = webOrigin();
  const url = validateOrigin(process.env.SAFERETURN_SUPABASE_URL ?? "");
  const key = process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY ?? "";
  if (!url.startsWith("https://") || !key.startsWith("sb_publishable_")) {
    throw new Error("Authentication configuration unavailable");
  }
  return { origin, url, key };
}
