import { randomBytes } from "node:crypto";
import { test, expect } from "@playwright/test";
import { createAuthClient } from "../lib/auth/client";

test("authorized manual mailbox: signup confirmation and password recovery through real callbacks", async ({ page, context }) => {
  test.skip(!process.env.SAFERETURN_LIVE_EMAIL_DESTINATION, "Requires explicit --email authorization and manual mailbox access");
  test.setTimeout(600000);
  // Never capture credential-bearing screenshots, traces, URLs, or provider bodies.
  const email = process.env.SAFERETURN_LIVE_EMAIL_DESTINATION!;
  const password = randomBytes(32).toString("base64url");
  let client: ReturnType<typeof createAuthClient> | undefined;
  try {
    if (!process.env.SAFERETURN_LIVE_EMAIL_RECOVERY_ONLY) {
    await page.goto("/auth/sign-up");
    await page.evaluate(({ email, password }) => {
      document.querySelector<HTMLInputElement>('input[name="display_name"]')!.value = "Authorized auth verification";
      document.querySelector<HTMLInputElement>('input[name="email"]')!.value = email;
      document.querySelector<HTMLInputElement>('input[name="password"]')!.value = password;
    }, { email, password });
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Check your email", { timeout: 20000 });
    console.log("ACTION REQUIRED: Open the confirmation email link in this test browser tab. Do not paste the link into chat.");
    await expect.poll(() => new URL(page.url()).pathname, { timeout: 240000 }).toBe("/account");
    await expect(page.getByText("Email confirmed.", { exact: true })).toBeVisible();
    console.log("PASS: real mailbox confirmation and PKCE callback reached the account.");
    // Revoke the confirmation session before recovery creates another session.
    const confirmationJar = new Map((await context.cookies()).map(cookie => [cookie.name, cookie.value]));
    const confirmationClient = createAuthClient({ url: process.env.SAFERETURN_SUPABASE_URL!, key: process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY! }, {
      getAll: () => [...confirmationJar].map(([name, value]) => ({ name, value })),
      setAll: items => items.forEach(item => { if (item.value) confirmationJar.set(item.name, item.value); else confirmationJar.delete(item.name); }),
    });
    if ((await confirmationClient.auth.signOut({ scope: "local" })).error) throw new Error("Confirmation session cleanup requires retry");
    await context.clearCookies();
    }
    await page.goto("/auth/forgot-password");
    await page.evaluate(email => { document.querySelector<HTMLInputElement>('input[name="email"]')!.value = email; }, email);
    await page.getByRole("button", { name: "Send reset link", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("If an eligible account exists", { timeout: 20000 });
    console.log("ACTION REQUIRED: Open the recovery email link in this same test browser tab. Do not paste it into chat.");
    await expect.poll(() => new URL(page.url()).pathname, { timeout: 240000 }).toBe("/auth/reset-password");
    await expect(page.locator('input[name="password"]')).toHaveCount(1);
    // Read-only proof that the recovery session reached the guarded form. Do not
    // change a potentially pre-existing account's password or globally log it out.
    console.log("PASS: real recovery email/PKCE callback minted the guarded recovery session; password mutation not requested.");
  } finally {
    const jar = new Map((await context.cookies()).map(cookie => [cookie.name, cookie.value]));
    client = createAuthClient({ url: process.env.SAFERETURN_SUPABASE_URL!, key: process.env.SAFERETURN_SUPABASE_PUBLISHABLE_KEY! }, {
      getAll: () => [...jar].map(([name, value]) => ({ name, value })),
      setAll: items => items.forEach(item => { if (item.value) jar.set(item.name, item.value); else jar.delete(item.name); }),
    });
    const result = await client.auth.signOut({ scope: "local" });
    if (result.error) throw new Error("Manual email test session cleanup requires retry");
    await context.clearCookies();
  }
});
