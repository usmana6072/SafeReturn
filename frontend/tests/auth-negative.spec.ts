import { test, expect } from "@playwright/test";

// Real Next requests; these cases never request signup, resend or recovery email.
for (const query of ["", "?code=one&code=two", "?code=%3Cunsafe%3E", "?next=https://attacker.invalid&return_to=//attacker.invalid"]) {
  test(`invalid callback cannot redirect externally or mint recovery authority: ${query}`, async ({ request }) => {
    const response = await request.get(`/auth/callback${query}`, { maxRedirects: 0 });
    expect([307, 503]).toContain(response.status());
    expect(response.headers()["cache-control"]).toBe("no-store");
    expect(response.headers()["referrer-policy"]).toBe("no-referrer");
    const location = response.headers().location;
    if (location) {
      const destination = new URL(location);
      expect(destination.origin).toBe("http://127.0.0.1:3100");
      expect(destination.pathname).toBe("/login");
      expect(destination.search).toBe("?confirmation=failed");
    }
    expect(response.headers()["set-cookie"] ?? "").not.toContain("sr-recovery=");
  });
}

test("forged session and recovery cookies cannot expose account or password form", async ({ page, context }) => {
  await context.addCookies([
    { name: "sr-recovery", value: "forged-ticket", url: "http://127.0.0.1:3100" },
    { name: "sb-fixture-auth-token", value: "forged-session", url: "http://127.0.0.1:3100" },
  ]);
  await page.goto("/account");
  await expect(page.locator('input[name="version"]')).toHaveCount(0);
  await page.goto("/auth/reset-password");
  await expect(page.locator('input[name="password"]')).toHaveCount(0);
  await expect(page.getByText("This recovery session is invalid or expired.")).toBeVisible();
});

test("actual login Server Action rejects an untrusted Origin before authentication", async ({ page, context }) => {
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("csrf-fixture@example.invalid");
  await page.locator('input[name="password"]').fill("fixture-password");
  await page.route("**/login", async route => {
    if (route.request().method() === "POST") {
      // API forwarding preserves the hostile Origin; browser networking may rewrite it.
      const rejected = await route.fetch({ headers: { ...route.request().headers(), origin: "https://attacker.invalid" } });
      await route.fulfill({ response: rejected });
    } else await route.continue();
  });
  const rejected = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === "/login");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  const response = await rejected;
  expect(response.status()).toBe(500);
  expect((await context.cookies()).filter(cookie => cookie.name.startsWith("sb-"))).toHaveLength(0);
  expect(new URL(page.url()).pathname).toBe("/login");
});
