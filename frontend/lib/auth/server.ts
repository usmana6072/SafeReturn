import "server-only";
import { createAuthClient } from "./client";
import { cookies } from "next/headers";
import { authConfig } from "./config";
import { validateOrigin } from "../api/transport";

export async function authClient() {
  const config = authConfig();
  const jar = await cookies();
  return createAuthClient(config, {
      getAll: () => jar.getAll(),
      setAll: (items) => {
        // Proxy owns refresh on Server Component reads; actions/routes can write.
        try { items.forEach(({ name, value, options }) => jar.set(name, value, options)); }
        catch { /* Server Component cookie writes are handled by the proxy. */ }
      },
  });
}

export type Account = { user_id: string; display_name: string | null;
  preferred_locale: "en" | "ur"; email_verified: boolean;
  masked_contact: { phone: string | null }; version: string };

export async function accountRequest(token: string, edit?: {
  display_name: string; preferred_locale: string; version: string;
}): Promise<Account> {
  const origin = validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "");
  const response = await fetch(`${origin}/api/v1/me`, {
    method: edit ? "PATCH" : "GET", cache: "no-store", redirect: "error",
    signal: AbortSignal.timeout(8000),
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json",
      ...(edit ? { "Content-Type": "application/json", "If-Match": `"${edit.version}"` } : {}) },
    body: edit ? JSON.stringify({ display_name: edit.display_name,
      preferred_locale: edit.preferred_locale }) : undefined,
  });
  if (!response.ok) throw new Error(response.status === 412 ? "stale" : "unavailable");
  const data = await response.json();
  if (!data || typeof data.user_id !== "string" || typeof data.version !== "string"
    || !["en", "ur"].includes(data.preferred_locale)
    || typeof data.email_verified !== "boolean"
    || (data.display_name !== null && typeof data.display_name !== "string")) {
    throw new Error("unavailable");
  }
  return data;
}

export async function verifiedSession() {
  const client = await authClient();
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) return null;
  // getSession is only token transport AFTER provider verification; API verifies again.
  const { data: { session } } = await client.auth.getSession();
  if (!session) return null;
  return { client, user: data.user, token: session.access_token };
}
