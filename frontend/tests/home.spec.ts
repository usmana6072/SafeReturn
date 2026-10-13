import { test, expect } from "@playwright/test";
import en from "../messages/en.json";
import ur from "../messages/ur.json";

test("homepage renders honest catalog state and expandable FAQ", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(en.title);
  await expect(page.getByText(en.catalogEmpty)).toBeVisible();
  await page.getByText(en.faqs[0][0], { exact: true }).click();
  await expect(page.getByText(en.faqs[0][1], { exact: true })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
});

test("language switch changes server-rendered direction and persists", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "اردو", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ur");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(ur.title);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ur");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
});

test("translations retain identical keys and list lengths", () => {
  expect(Object.keys(ur).sort()).toEqual(Object.keys(en).sort());
  for (const key of ["chips", "steps", "faqs"] as const) expect(ur[key]).toHaveLength(en[key].length);
});

for (const width of [320, 390, 768, 1440]) {
  test(`layout fits ${width}px in English and Urdu`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    for (const language of ["en", "ur"]) {
      if (language === "ur") await page.getByRole("button", { name: "اردو", exact: true }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", language);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if (width < 640) {
        await page.locator(".mobile-menu summary").click();
        await expect(page.locator(".mobile-menu nav")).toBeVisible();
        await page.locator(".mobile-menu summary").click();
      }
      if (width === 390 || width === 1440) {
        await page.screenshot({ path: `test-results/home-${language}-${width}.png`, fullPage: true });
      }
    }
  });
}

test("keyboard skip link reaches main content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: en.skip })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("mobile navigation and FAQ work without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:3100/");
  await page.locator(".mobile-menu summary").click();
  await expect(page.locator(".mobile-menu nav")).toBeVisible();
  await page.getByText(en.faqs[0][0], { exact: true }).click();
  await expect(page.getByText(en.faqs[0][1], { exact: true })).toBeVisible();
  await context.close();
});
