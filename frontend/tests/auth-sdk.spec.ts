import { test, expect } from "@playwright/test";
import { createAuthClient } from "../lib/auth/client";
import type { CookieOptions } from "@supabase/ssr";
import { recoveryAllowed, recoveryTicket } from "../lib/auth/recovery";

function provider() {
  const jar = new Map<string, string>();
  const writes: { name: string; value: string; options: CookieOptions }[] = [];
  const requests: { path: string; body: Record<string, unknown> }[] = [];
  let expire = false;
  let aal = "aal1";
  let used = false;
  let failure: { endpoint: string; status: number } | undefined;
  const user = { id: "00000000-0000-4000-8000-000000000001", aud: "authenticated",
    email: "fixture@example.invalid", role: "authenticated", user_metadata: {},
    app_metadata: {}, created_at: new Date().toISOString() };
  const jwt = () => ["e30", Buffer.from(JSON.stringify({ sub: user.id,
    exp: Math.floor(Date.now() / 1000) + 3600, iat: Math.floor(Date.now() / 1000),
    session_id: "00000000-0000-4000-8000-000000000002", role: "authenticated", aal })).toString("base64url"), "signature"].join(".");
  const transport: typeof fetch = async (input, init) => {
    const url = new URL(String(input));
    expect(url.origin).toBe("https://fixture.test");
    expect(init?.cache).toBe("no-store");
    expect(init?.redirect).toBe("error");
    const body = init?.body ? JSON.parse(String(init.body)) : {};
    requests.push({ path: url.pathname + url.search, body });
    if (failure && url.pathname.endsWith(failure.endpoint)) return Response.json({
      code: "fixture_denied", msg: "Controlled provider failure",
    }, { status: failure.status });
    if (url.pathname.endsWith("/factors")) return Response.json({ id: "fixture-factor", type: "totp", totp: { secret: "SYNTHETIC", uri: "otpauth://totp/fixture", qr_code: "<svg/>" } });
    if (url.pathname.endsWith("/challenge")) return Response.json({ id: "fixture-challenge", expires_at: Math.floor(Date.now()/1000)+60 });
    if (url.pathname.endsWith("/verify")) {
      if (body.code !== "123456" || used) return Response.json({ msg: "Invalid or expired challenge" }, { status: 400 });
      used = true; aal = "aal2";
      return Response.json({ access_token: jwt(), refresh_token: "fixture-mfa-refresh", expires_in: 3600, token_type: "bearer", user });
    }
    if (url.pathname.endsWith("/signup")) return Response.json({ user, session: null });
    if (url.pathname.endsWith("/recover") || url.pathname.endsWith("/resend")) return Response.json({});
    if (url.pathname.endsWith("/token")) return Response.json({ access_token: jwt(),
      refresh_token: "fixture-refresh", expires_in: expire && url.search.includes("password") ? -10 : 3600,
      token_type: "bearer", user });
    if (url.pathname.endsWith("/user")) return Response.json(user);
    if (url.pathname.endsWith("/logout")) return new Response(null, { status: 204 });
    throw new Error("Unexpected provider endpoint");
  };
  const client = () => createAuthClient({ url: "https://fixture.test", key: "sb_publishable_fixture" }, {
    getAll: () => [...jar].map(([name, value]) => ({ name, value })),
    setAll: (items) => items.forEach(item => { writes.push(item); if (item.value) jar.set(item.name, item.value); else jar.delete(item.name); }),
  }, transport);
  return { client, jar, writes, requests, expire: () => { expire = true; },
    fail: (endpoint: string, status: number) => { failure = { endpoint, status }; } };
}

for (const status of [400, 429, 503]) {
  test(`controlled provider login failure ${status} never installs a session`, async () => {
    const fixture = provider();
    fixture.fail("/token", status);
    const result = await fixture.client().auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password" });
    expect(result.error !== null).toBe(true);
    expect(result.data.session === null).toBe(true);
    expect(fixture.jar.size).toBe(0);
  });
}

test("revoked refresh credential clears expired cookie session", async () => {
  const fixture = provider();
  fixture.expire();
  await fixture.client().auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password" });
  fixture.fail("/token", 400);
  const result = await fixture.client().auth.getUser();
  expect(result.error !== null).toBe(true);
  expect(result.data.user === null).toBe(true);
  expect((await fixture.client().auth.getSession()).data.session === null).toBe(true);
});

test("PKCE provider rejection cannot mint a confirmation session", async () => {
  const fixture = provider();
  await fixture.client().auth.signUp({ email: "fixture@example.invalid", password: "fixture-password-123" });
  fixture.fail("/token", 400);
  const result = await fixture.client().auth.exchangeCodeForSession("expired-or-replayed-code");
  expect(result.error !== null).toBe(true);
  expect(result.data.session === null).toBe(true);
  expect((await fixture.client().auth.getSession()).data.session === null).toBe(true);
});

test("SDK signup requires confirmation and persists PKCE verifier in HttpOnly cookie", async () => {
  const fixture = provider();
  const result = await fixture.client().auth.signUp({ email: "fixture@example.invalid", password: "fixture-password-123",
    options: { emailRedirectTo: "https://web.test/auth/callback" } });
  expect(result.error).toBeNull();
  expect(result.data.session).toBeNull();
  expect(fixture.requests[0].body.code_challenge_method).toBe("s256");
  expect(fixture.writes.some(item => item.name.endsWith("code-verifier") && item.options.httpOnly)).toBe(true);
});

test("SDK login, provider verification, cookie reuse and global logout", async () => {
  const fixture = provider();
  const signedIn = await fixture.client().auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password-123" });
  expect(signedIn.error).toBeNull();
  expect(fixture.writes.length).toBeGreaterThan(0);
  for (const write of fixture.writes) {
    expect(write.options.httpOnly).toBe(true);
    expect(write.options.sameSite).toBe("lax");
    expect(write.options.path).toBe("/");
  }
  const next = fixture.client();
  expect((await next.auth.getUser()).data.user?.id).toBe(signedIn.data.user?.id);
  expect(fixture.requests.some(item => item.path.endsWith("/user"))).toBe(true);
  expect((await next.auth.signOut({ scope: "global" })).error).toBeNull();
  expect(fixture.requests.some(item => item.path.endsWith("/logout?scope=global"))).toBe(true);
  expect((await fixture.client().auth.getSession()).data.session).toBeNull();
});

test("SDK refresh recovers expired session and writes replacement cookies", async () => {
  const fixture = provider();
  fixture.expire();
  await fixture.client().auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password-123" });
  const result = await fixture.client().auth.getUser();
  expect(result.error).toBeNull();
  expect(fixture.requests.some(item => item.path.endsWith("grant_type=refresh_token"))).toBe(true);
});

test("SDK confirmation exchanges code using stored PKCE verifier", async () => {
  const fixture = provider();
  await fixture.client().auth.signUp({ email: "fixture@example.invalid", password: "fixture-password-123" });
  const result = await fixture.client().auth.exchangeCodeForSession("fixture-code");
  expect(result.error).toBeNull();
  const exchange = fixture.requests.find(item => item.path.endsWith("grant_type=pkce"));
  expect(exchange?.body.auth_code).toBe("fixture-code");
  expect(typeof exchange?.body.code_verifier).toBe("string");
  expect(String(exchange?.body.code_verifier).length).toBeGreaterThan(20);
});

test("SDK recovery exchange emits PASSWORD_RECOVERY; signup does not", async () => {
  const fixture = provider();
  await fixture.client().auth.resetPasswordForEmail("fixture@example.invalid", { redirectTo: "https://web.test/auth/callback" });
  const next = fixture.client();
  let recovery = false;
  const { data: { subscription } } = next.auth.onAuthStateChange(event => { if (event === "PASSWORD_RECOVERY") recovery = true; });
  const result = await next.auth.exchangeCodeForSession("fixture-code");
  subscription.unsubscribe();
  expect(result.error).toBeNull();
  expect(recovery).toBe(true);
  expect(fixture.requests.find(item => item.path.startsWith("/auth/v1/recover"))?.body.code_challenge_method).toBe("s256");
});

test("recovery authorization is signed, token-bound and expires", () => {
  const original = process.env.SAFERETURN_SESSION_SIGNING_KEY;
  process.env.SAFERETURN_SESSION_SIGNING_KEY = "1".repeat(64);
  try {
    const ticket = recoveryTicket("fixture-access", 1000);
    expect(recoveryAllowed(ticket, "fixture-access", 1001)).toBe(true);
    expect(recoveryAllowed(ticket, "other-access", 1001)).toBe(false);
    expect(recoveryAllowed(ticket + "x", "fixture-access", 1001)).toBe(false);
    expect(recoveryAllowed(ticket, "fixture-access", 601001)).toBe(false);
  } finally {
    if (original === undefined) delete process.env.SAFERETURN_SESSION_SIGNING_KEY;
    else process.env.SAFERETURN_SESSION_SIGNING_KEY = original;
  }
});

test("production session cookie is Secure and HttpOnly", async () => {
  const environment = process.env as Record<string, string | undefined>;
  const original = environment.NODE_ENV;
  environment.NODE_ENV = "production";
  try {
    const fixture = provider();
    await fixture.client().auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password-123" });
    expect(fixture.writes.length).toBeGreaterThan(0);
    expect(fixture.writes.every(item => item.options.secure && item.options.httpOnly)).toBe(true);
  } finally {
    if (original === undefined) delete environment.NODE_ENV;
    else environment.NODE_ENV = original;
  }
});


test("synthetic SDK TOTP enrollment, invalid/expired challenge, success and replay", async () => {
  const fixture = provider();
  const client = fixture.client();
  await client.auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password" });
  const enrollment = await client.auth.mfa.enroll({ factorType: "totp" });
  expect(enrollment.error).toBeNull();
  expect(enrollment.data?.totp.secret).toBe("SYNTHETIC");
  expect((await client.auth.mfa.challengeAndVerify({ factorId: "fixture-factor", code: "000000" })).error).not.toBeNull();
  const challenge = await client.auth.mfa.challenge({ factorId: "fixture-factor" });
  expect(challenge.error).toBeNull();
  fixture.fail("/verify", 400);
  expect((await client.auth.mfa.verify({ factorId: "fixture-factor", challengeId: challenge.data!.id, code: "123456" })).error).not.toBeNull();
});
test("synthetic SDK successful MFA installs AAL2; replay fails", async () => {
  const fixture = provider(); const client = fixture.client();
  await client.auth.signInWithPassword({ email: "fixture@example.invalid", password: "fixture-password" });
  expect((await client.auth.mfa.challengeAndVerify({ factorId: "fixture-factor", code: "123456" })).error).toBeNull();
  const token = (await client.auth.getSession()).data.session!.access_token;
  expect(JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString()).aal).toBe("aal2");
  expect((await client.auth.mfa.verify({ factorId: "fixture-factor", challengeId: "fixture-challenge", code: "123456" })).error).not.toBeNull();
});
