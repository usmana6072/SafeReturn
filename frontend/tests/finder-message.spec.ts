import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit", route => route.fulfill({
    contentType: "application/javascript",
    body: "window.turnstile={render:(el,o)=>{setTimeout(()=>o.callback(o.action+':'+o.cData+':'+crypto.randomUUID()),20);return 'fixture';},remove:()=>{}};",
  }));
});

test("finder can submit without location after explicit contact consent", async ({ page }) => {
  await page.goto(`/q/${process.env.PUBLIC_QR_LOST}`);
  const form = page.locator("form[data-finder-message]");
  await form.getByLabel("Email", { exact: true }).fill("finder@example.test");
  await form.getByLabel("Message", { exact: true }).fill("I found your keys near the shop.");
  await form.getByRole("checkbox", { name: /I consent/ }).check();
  await form.getByRole("button", { name: "Send secure message", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Your message is saved" })).toBeVisible();
});

test("revoking location consent discards a delayed browser response", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "geolocation", { value: {
      getCurrentPosition: (success: (position: unknown) => void) => {
        setTimeout(() => success({ coords: { latitude: 31.5, longitude: 74.3, accuracy: 10 } }), 200);
      },
    } });
  });
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto(`/q/${process.env.PUBLIC_QR_LOST}`);
  const form = page.locator("form[data-finder-message]");
  const consent = form.getByRole("checkbox", { name: /Share my one-time location/ });
  await consent.check();
  await consent.uncheck();
  await expect(form.locator('[name="latitude"]')).toHaveValue("");
  await page.waitForTimeout(300);
  await expect(form.locator('[name="latitude"]')).toHaveValue("");
  await expect(consent).not.toBeChecked();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: "test-results/finder-message-mobile.png", fullPage: true });
});

test("Urdu finder form stays readable on a narrow screen", async ({ page, context }) => {
  await context.addCookies([{ name: "safereturn-language", value: "ur", domain: "127.0.0.1", path: "/" }]);
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto(`/q/${process.env.PUBLIC_QR_LOST}`);
  const form = page.locator("form[data-finder-message]");
  await expect(form.locator('[name="message"]')).toBeVisible();
  await expect(form.getByRole("checkbox", { name: /میں اپنی رابطے کی معلومات/ })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: "test-results/finder-message-ur-mobile.png", fullPage: true });
});
