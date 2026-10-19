import { test, expect } from "@playwright/test";
test("bounded synthetic staff console, MFA, roles, direct URL/RSC and responsive RTL flow", async ({ page, context, request }) => {
  test.setTimeout(180000);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/login$/);
  let loginNumber = 0;
  async function login() {
    await context.clearCookies();
    await page.goto("/login");
    await page.locator('input[name="email"]').fill(`staff-${++loginNumber}@example.invalid`);
    await page.locator('input[name="password"]').fill("synthetic-password");
    await page.getByRole("button", { name: "Log in", exact: true }).click();
  }
  await login();
  await expect(page).toHaveURL(/\/admin\/security\/mfa\?returnTo=%2Fadmin/);
  await page.locator('input[name="code"]').fill("000000");
  await page.getByRole("button", { name: "Verify authenticator" }).click();
  await expect(page.getByText("Code invalid or expired. Try a new code.", { exact: true })).toBeVisible();
  await page.locator('input[name="code"]').fill("123456");
  await page.getByRole("button", { name: "Verify authenticator" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Your staff workspace" })).toBeVisible();
  const sidebar = page.getByRole("navigation", { name: "Staff navigation" }).first();
  await expect(sidebar.getByRole("link", { name: "Products", exact: true })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Payments", exact: true })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Shipments", exact: true })).toBeVisible();
  for (const path of ["/admin/products", "/admin/payments", "/admin/shipments", "/admin/ready-to-ship"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).not.toContainText(/denied|unavailable/);
    await expect(page.getByRole("navigation", { name: "Staff navigation" }).first().locator('[aria-current="page"]')).toHaveAttribute("href", path);
  }
  await page.goto("/admin");
  for (const language of ["en", "ur"]) {
    await context.addCookies([{ name: "safereturn-language", value: language, url: "http://127.0.0.1:3100" }]);
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("dir", language === "ur" ? "rtl" : "ltr");
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (width < 768) {
        await page.getByRole("button", { name: language === "ur" ? "مینو" : "Menu", exact: true }).click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(page.getByRole("dialog")).not.toBeVisible();
        await expect(page.getByRole("button", { name: language === "ur" ? "مینو" : "Menu", exact: true })).toBeFocused();
      }
    }
    await page.screenshot({ path: `test-results/staff-console-${language}.png`, fullPage: true });
  }
  for (const [role, allowed, forbidden] of [
    ["finance", "Payments", "/admin/shipments"],
    ["operations", "Shipments", "/admin/payments"],
    ["security_admin", "Products", "/admin/payments"],
    ["a", "Products", "/admin/shipments"],
    ["support", "", "/admin/products"],
  ]) {
    expect((await request.post(`http://127.0.0.1:8115/fixture/staff/${role}`)).ok()).toBe(true);
    await login();
    await expect(page).toHaveURL(/\/admin$/);
    if (allowed) await expect(page.getByRole("navigation", { name: "Staff navigation" }).first().getByRole("link", { name: allowed, exact: true })).toBeVisible();
    else await expect(page.getByRole("heading", { name: "No modules available" })).toBeVisible();
    const allowedPaths: Record<string, string[]> = {
      finance: ["/admin/payments"], operations: ["/admin/products", "/admin/ready-to-ship", "/admin/shipments", "/admin/print-jobs/00000000-0000-4000-8000-000000000098"],
      security_admin: ["/admin/products"], a: ["/admin/products"], support: [],
    };
    for (const path of ["/admin/products", "/admin/payments", "/admin/ready-to-ship", "/admin/shipments", "/admin/print-jobs/00000000-0000-4000-8000-000000000098"]) {
      const rsc = await page.request.get(path, { headers: { RSC: "1" } });
      const body = await rsc.text();
      if (allowedPaths[role].includes(path)) {
        expect(body).not.toContain("Access denied");
        expect(body).toMatch(/"(?:FinanceForm|FulfillmentAdmin|CatalogAdmin|PrintingAdmin)"/);
      } else {
        expect(body).toContain("Access denied");
        expect(body).not.toMatch(/"(?:FinanceForm|FulfillmentAdmin|CatalogAdmin|PrintingAdmin)"/);
      }
    }
    await page.goto(forbidden);
    await expect(page.getByRole("heading", { name: "Access denied" })).toBeVisible();
  }
  await request.post("http://127.0.0.1:8115/fixture/staff/revoked");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Access denied" })).toBeVisible();
  await request.post("http://127.0.0.1:8115/fixture/staff/customer");
  await login();
  await expect(page).toHaveURL(/\/account$/);
  await page.goto("/admin/payments");
  await expect(page.getByRole("heading", { name: "Access denied" })).toBeVisible();
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});
