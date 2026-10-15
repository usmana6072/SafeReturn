import { test, expect } from "@playwright/test";
import { createAuthClient } from "../lib/auth/client";

test("live Supabase browser login reaches private account and local test logout revokes API access", async ({ page, context }) => {
  test.skip(!process.env.SAFERETURN_LIVE_AUTH_TEST, "Requires explicit dedicated live Auth runner");
  // No traces/screenshots or credential literals; each browser context starts empty.
  let access: string | undefined;
  let client: ReturnType<typeof createAuthClient> | undefined;
  try {
    await page.goto("/auth/sign-in");
    await page.evaluate(({ email, password }) => {
      const emailInput = document.querySelector<HTMLInputElement>('input[name="email"]')!;
      const passwordInput = document.querySelector<HTMLInputElement>('input[name="password"]')!;
      emailInput.value = email;
      passwordInput.value = password;
    }, { email: process.env.SAFERETURN_AUTH_TEST_EMAIL!, password: process.env.SAFERETURN_AUTH_TEST_PASSWORD! });
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page).toHaveURL(/\/account$/, { timeout: 20000 });
    await expect(page.getByRole("heading", { name: "Your account", exact: true })).toBeVisible();
    await expect(page.getByText("Email confirmed.", { exact: true })).toBeVisible();
    await expect(page.locator('input[name="version"]')).toHaveCount(1);
    const jar = new Map((await context.cookies()).map(item => [item.name, item.value]));
    const authCookies = (await context.cookies()).filter(item => item.name.startsWith("sb-"));
    expect(authCookies.length).toBeGreaterThan(0);
    expect(authCookies.every(item => item.httpOnly && item.secure && item.sameSite === "Lax")).toBe(true);
    expect(await page.evaluate(() => localStorage.length)).toBe(0);
    // A server SDK client using only this new context's cookies revokes only its session.
    client = createAuthClient({ url: process.env.SAFERETURN_SUPABASE_URL!, key: process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY! }, {
      getAll: () => [...jar].map(([name, value]) => ({ name, value })),
      setAll: items => items.forEach(item => { if (item.value) jar.set(item.name, item.value); else jar.delete(item.name); }),
    });
    const session = (await client.auth.getSession()).data.session;
    if (!session) throw new Error("Live test session unavailable");
    access = session.access_token;
    // Do not put response bodies/tokens into assertion output.
    const before = await fetch(`${process.env.SAFERETURN_API_ORIGIN}/api/v1/me`, { headers: { Authorization: `Bearer ${access}` } });
    expect(before.status).toBe(200);
    expect((await client.auth.signOut({ scope: "local" })).error === null).toBe(true);
    const after = await fetch(`${process.env.SAFERETURN_API_ORIGIN}/api/v1/me`, { headers: { Authorization: `Bearer ${access}` } });
    expect(after.status).toBe(401);
    await page.reload();
    await expect(page).toHaveURL(/\/login$/);
  } finally {
    // Also clean a provider session if a UI assertion failed after successful login.
    if (!client) {
      const jar = new Map((await context.cookies()).map(item => [item.name, item.value]));
      client = createAuthClient({ url: process.env.SAFERETURN_SUPABASE_URL!, key: process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY! }, {
        getAll: () => [...jar].map(([name, value]) => ({ name, value })),
        setAll: items => items.forEach(item => { if (item.value) jar.set(item.name, item.value); else jar.delete(item.name); }),
      });
    }
    const cleanup = await client.auth.signOut({ scope: "local" });
    if (cleanup.error) throw new Error("Live test session cleanup requires retry");
    await context.clearCookies();
  }
});
