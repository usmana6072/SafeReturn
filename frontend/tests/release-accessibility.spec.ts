import { test, expect } from "@playwright/test";

const customerRoutes = ["/dashboard", "/kits", "/my-qr", "/orders", "/inbox", "/settings", "/help"];

for (const width of [320, 390, 768, 1440]) {
  test(`release layout has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: "اردو", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("public and auth surfaces expose labeled landmarks and keyboard focus", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("navigation").first()).toHaveAttribute("aria-label", /.+/);
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  await page.goto("/login");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByLabel(/Email address|ای میل/)).toHaveAttribute("autocomplete", "email");
  await expect(page.getByLabel(/Password|پاس ورڈ/)).toHaveAttribute("autocomplete", "current-password");
});

test("unauthenticated customer routes do not render private content", async ({ page }) => {
  for (const route of customerRoutes) {
    await page.goto(route);
    await expect(page.locator("input[name=version]")).toHaveCount(0);
    await expect(page.locator("textarea")).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(/finder@example|private medical|sender account/i);
  }
});

test("mobile navigation remains keyboard operable without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    viewport: { width: 320, height: 844 },
  });
  const page = await context.newPage();
  await page.goto("/");
  const summary = page.locator(".mobile-menu summary");
  await summary.focus();
  await expect(summary).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator(".mobile-menu nav")).toBeVisible();
  await context.close();
});
