"use server";

import { createHash } from "node:crypto";
import { headers, cookies } from "next/headers";
import { redirect } from "next/navigation";
import { authClient, verifiedSession, accountRequest } from "../../lib/auth/server";
import { authConfig } from "../../lib/auth/config";
import { recoveryAllowed } from "../../lib/auth/recovery";
import { readTicket, ScanTicket, ActivationTicket } from "../../lib/scan-ticket";

export type FormState = { status: "idle" | "error" | "confirmation" | "saved";
  reason?: "invalid" | "denied" | "unavailable" | "limited" | "email_limited" | "stale" };
const attempts = new Map<string, { count: number; until: number }>();

async function sameOrigin() {
  const origin = (await headers()).get("origin");
  const matches = origin === authConfig().origin;
  if (!matches && process.env.NODE_ENV === "development") {
    console.info("Auth local request rejected: origin mismatch");
  }
  return matches;
}

function limited(email: string) {
  const now = Date.now();
  for (const [key, value] of attempts) if (value.until <= now) attempts.delete(key);
  const key = createHash("sha256").update(email.toLowerCase()).digest("hex");
  const value = attempts.get(key) ?? { count: 0, until: now + 60000 };
  value.count += 1;
  if (attempts.size >= 1000 || value.count > 5) return true;
  attempts.set(key, value);
  return false;
}

export async function submitIdentity(mode: "login" | "signup", _previous: FormState,
  form: FormData): Promise<FormState> {
  let signedIn = false;
  try {
    if (!(await sameOrigin())) return { status: "error", reason: "denied" };
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const name = String(form.get("display_name") ?? "").trim();
    if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
      || password.length < (mode === "signup" ? 12 : 1) || password.length > 128
      || (mode === "signup" && (!name || name.length > 120 || /[\x00-\x1f\x7f]/.test(name)))) {
      return { status: "error", reason: "invalid" };
    }
    if (limited(email)) return { status: "error", reason: "limited" };
    const client = await authClient();
    const result = mode === "signup"
      ? await client.auth.signUp({ email, password,
        options: { data: { display_name: name },
          emailRedirectTo: `${authConfig().origin}/auth/callback` } })
      : await client.auth.signInWithPassword({ email, password });
    if (result.error) return { status: "error", reason: result.error.code === "over_email_send_rate_limit"
      ? "email_limited" : result.error.status === 429 ? "limited"
        : (result.error.status ?? 400) >= 500 ? "unavailable" : "denied" };
    signedIn = !!result.data.session;
    if (!signedIn) return { status: "confirmation" };
  } catch { return { status: "error", reason: "unavailable" }; }
  if (signedIn) {
    const scan = readTicket<ScanTicket>((await cookies()).get("sr-scan")?.value, "scan");
    const activation = readTicket<ActivationTicket>((await cookies()).get("sr-activation")?.value, "activation");
    redirect(scan || activation ? "/activate" : "/auth/continue");
  }
  return { status: "error", reason: "unavailable" };
}

export async function logout() {
  try {
    if (!(await sameOrigin())) return;
    const client = await authClient();
    // Global scope invalidates provider refresh sessions; API session guard denies deleted sessions.
    const { error } = await client.auth.signOut({ scope: "global" });
    if (error) redirect("/account?logout=failed");
  } catch { redirect("/account?logout=failed"); }
  redirect("/login");
}

export async function saveAccount(_previous: FormState, form: FormData): Promise<FormState> {
  try {
    if (!(await sameOrigin())) return { status: "error", reason: "denied" };
    const session = await verifiedSession();
    if (!session) return { status: "error", reason: "denied" };
    const name = String(form.get("display_name") ?? "").trim();
    const locale = String(form.get("preferred_locale") ?? "");
    const version = String(form.get("version") ?? "");
    if (!name || name.length > 120 || !["en", "ur"].includes(locale)
      || !/^(0|[0-9]{1,12}\.[0-9]{1,6})$/.test(version)) {
      return { status: "error", reason: "invalid" };
    }
    await accountRequest(session.token, { display_name: name, preferred_locale: locale, version });
    (await cookies()).set("safereturn-language", locale, {
      sameSite: "lax", path: "/", secure: process.env.NODE_ENV === "production", maxAge: 31536000,
    });
    // Reload to obtain the new version, preventing accidental stale resubmission.
  } catch (error) {
    return { status: "error", reason: error instanceof Error && error.message === "stale"
      ? "stale" : "unavailable" };
  }
  redirect("/account?saved=1");
}

export async function requestEmail(mode: "resend" | "recovery", _previous: FormState,
  form: FormData): Promise<FormState> {
  try {
    if (!(await sameOrigin())) return { status: "error", reason: "denied" };
    const email = String(form.get("email") ?? "").trim();
    if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { status: "error", reason: "invalid" };
    if (limited(email)) return { status: "error", reason: "limited" };
    const client = await authClient();
    const callback = `${authConfig().origin}/auth/callback`;
    const result = mode === "recovery"
      ? await client.auth.resetPasswordForEmail(email, { redirectTo: callback })
      : await client.auth.resend({ type: "signup", email, options: { emailRedirectTo: callback } });
    if (result.error?.status === 429) return { status: "error", reason: "limited" };
    if (result.error && (result.error.status ?? 500) >= 500) return { status: "error", reason: "unavailable" };
    return { status: "confirmation" };
  } catch { return { status: "error", reason: "unavailable" }; }
}

export async function resetPassword(_previous: FormState, form: FormData): Promise<FormState> {
  try {
    if (!(await sameOrigin())) return { status: "error", reason: "denied" };
    const session = await verifiedSession();
    const jar = await cookies();
    if (!session || !recoveryAllowed(jar.get("sr-recovery")?.value ?? "", session.token)) {
      return { status: "error", reason: "denied" };
    }
    const password = String(form.get("password") ?? "");
    if (password.length < 12 || password.length > 128) return { status: "error", reason: "invalid" };
    const result = await session.client.auth.updateUser({ password });
    if (result.error) return { status: "error", reason: "denied" };
    jar.delete("sr-recovery");
    const signedOut = await session.client.auth.signOut({ scope: "global" });
    if (signedOut.error) return { status: "error", reason: "unavailable" };
  } catch { return { status: "error", reason: "unavailable" }; }
  redirect("/auth/sign-in?reset=done");
}
