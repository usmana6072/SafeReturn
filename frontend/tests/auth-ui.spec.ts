import { test, expect } from "@playwright/test";

for (const width of [390, 1440]) {
  for (const language of ["en", "ur"]) {
    test(`auth screens fit ${width}px ${language} with labels and password controls`, async ({ page, context }) => {
      await context.addCookies([{ name: "safereturn-language", value: language, url: "http://127.0.0.1:3100" }]);
      await page.setViewportSize({ width, height: 900 });
      for (const path of ["/login", "/signup"]) {
        await page.goto(path);
        await expect(page.locator("html")).toHaveAttribute("dir", language === "ur" ? "rtl" : "ltr");
        await expect(page.locator("input[name=email]")).toHaveAttribute("type", "email");
        const password = page.locator("input[name=password]");
        await expect(password).toHaveAttribute("type", "password");
        await page.getByRole("button", { name: language === "ur" ? "دکھائیں" : "Show", exact: true }).click();
        await expect(password).toHaveAttribute("type", "text");
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await page.screenshot({ path: `test-results/auth-${path.slice(1)}-${language}-${width}.png`, fullPage: true });
      }
    });
  }
}

test("unauthenticated account never renders private fields", async ({ page }) => {
  await page.goto("/account");
  // Unconfigured isolated test build safely fails closed; configured server redirects to login.
  await expect(page.locator("h1")).toHaveText(/Account unavailable|Log in to SafeReturn/);
  await expect(page.locator("input[name=version]")).toHaveCount(0);
});

test("invalid identity submission keeps safe error and never retains password", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[name=email]").fill("fixture@example.invalid");
  await page.locator("input[name=password]").fill("fixture-password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(/Service unavailable|Unable to sign in|Too many attempts/);
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator("input[name=password]")).toHaveValue("");
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("approved auth routes and invalid recovery render accessible safe states", async ({ page }) => {
  for (const route of ["/auth/sign-in", "/auth/sign-up", "/auth/verify-email", "/auth/forgot-password"]) {
    await page.goto(route);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("input[name=email]")).toHaveAttribute("type", "email");
  }
  await page.goto("/auth/reset-password");
  await expect(page.getByText("This recovery session is invalid or expired.")).toBeVisible();
  await expect(page.locator("input[name=password]")).toHaveCount(0);
});
