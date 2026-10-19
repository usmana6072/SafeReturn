import { test, expect } from "@playwright/test";
import { mfaReturn } from "../lib/auth/mfa-return";
for (const value of ["https://evil.test", "//evil.test", "/admin/payments?x=1", "/admin/payments/../products", "%2fadmin/payments", ["/admin/payments"], undefined]) {
  test(`unsafe return ${JSON.stringify(value)}`, () => expect(mfaReturn(value)).toBe("/account"));
}
test("fixed return", () => expect(mfaReturn("/admin/payments")).toBe("/admin/payments"));
test("anonymous staff security bounded browser flow", async ({ page }) => {
  await page.goto("/admin/security/mfa?returnTo=https://evil.test");
  await expect(page.getByRole("heading", { name: "Staff security unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Set up authenticator" })).toHaveCount(0);
});
