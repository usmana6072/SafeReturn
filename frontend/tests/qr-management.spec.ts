import { test, expect as baseExpect, type Page, type APIRequestContext } from "@playwright/test";
const expect = baseExpect.configure({ timeout: 15000 });

const id = (name: string) => process.env[`QR_TEST_${name}`]!;
const api = "http://127.0.0.1:8115";
test.skip(!process.env.QR_TEST_LOST, "Run through the isolated backend PostgreSQL/browser controller.");
test.setTimeout(90000);
test.use({ actionTimeout: 15000 });
async function login(page: Page) {
  await page.goto("/login");
  // The simulated provider maps these per-case aliases to the same synthetic
  // owner. Keep application login throttling intact across a fast test suite.
  await page.getByLabel("Email address").fill(`fixture+${test.info().testId}@example.invalid`);
  await page.locator('input[name="password"]').fill("synthetic-password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);
}
async function profile(request: APIRequestContext, qr: string, kind: "lost" | "ice", edit?: object) {
  const url = `${api}/api/v1/me/qr/${qr}/${kind}-profile`;
  const auth = await request.post(`${api}/auth/v1/token`);
  const headers = { Authorization: `Bearer ${(await auth.json()).access_token}` };
  const current = await request.get(url, { headers });
  expect(current.status()).toBe(200);
  if (!edit) return current.json();
  const result = await request.put(url, { headers: { ...headers, "If-Match": `"${(await current.json()).version}"` }, data: edit });
  expect(result.status()).toBe(200);
  return result.json();
}

test("multiple kits show distinct Lost/ICE links without private medical or phones", async ({ page }) => {
  await login(page); await page.goto("/dashboard");
  await expect(page.locator(".pair-card")).toHaveCount(2);
  for (const name of ["LOST", "ICE", "OTHER_LOST", "OTHER_ICE"]) {
    await expect(page.locator(`a[href="/my-qr/${id(name)}"]`)).toBeVisible();
  }
  await expect(page.getByText("Every printed copy of the same QR shares its profile.", { exact: false })).toBeVisible();
  await expect(page.locator("input[type=tel]")).toHaveCount(0);
  await page.screenshot({ path: "test-results/task34-dashboard-en.png", fullPage: true });
});

test("Lost save and draft preview affect only the selected QR", async ({ page, request }) => {
  await login(page); await page.goto(`/my-qr/${id("LOST")}`);
  await page.getByLabel("Item label", { exact: true }).fill("Synthetic school bag");
  await page.getByLabel("Description", { exact: true }).fill("Blue bag");
  await expect(page.getByLabel("Draft preview")).toContainText("Synthetic school bag");
  await page.locator(".qr-editor").first().getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status")).toHaveText("Changes saved.");
  expect((await profile(request, id("LOST"), "lost")).item_label).toBe("Synthetic school bag");
  expect((await profile(request, id("OTHER_LOST"), "lost")).item_label).toBeNull();
  expect((await profile(request, id("ICE"), "ice")).display_name).toBeNull();
});

test("a concurrent save shows a conflict and preserves newer data", async ({ page, request }) => {
  await login(page); await page.goto(`/my-qr/${id("LOST")}`);
  await profile(request, id("LOST"), "lost", { item_label: "Newer synthetic label" });
  await page.getByLabel("Item label", { exact: true }).fill("Stale browser label");
  await page.locator(".qr-editor").first().getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator(".form-notice[role=alert]")).toContainText("Your changes were not saved", { timeout: 15000 });
  expect((await profile(request, id("LOST"), "lost")).item_label).toBe("Newer synthetic label");
});

test("QR list searches all owned labels and filters by purpose", async ({ page }) => {
  await login(page); await page.goto("/my-qr");
  await page.getByLabel("Search by label").fill("Newer synthetic");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.locator(".qr-card")).toHaveCount(1);
  await expect(page.locator(`a[href="/my-qr/${id("LOST")}"]`)).toBeVisible();
  await page.getByLabel("Search by label").fill("");
  await page.getByRole("combobox", { name: "Filter", exact: true }).selectOption("ice");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.locator(".qr-card")).toHaveCount(2);
});

test("WhatsApp preference requires consent, masks the number and can be disabled", async ({ page }) => {
  await login(page); await page.goto(`/my-qr/${id("LOST")}`);
  let form = page.locator("form").filter({ has: page.getByRole("heading", { name: "WhatsApp preference" }) });
  await form.locator('input[name="whatsapp_phone"]').fill("+923001234567");
  await form.locator('input[name="whatsapp_enabled"]').check();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(form.getByRole("alert")).toBeVisible();
  await expect(form.locator('input[name="whatsapp_phone"]')).toHaveValue("+923001234567");
  await expect(form.locator('input[name="whatsapp_enabled"]')).toBeChecked();
  await form.locator('input[name="consent"]').check();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("••••4567", { exact: true })).toBeVisible();
  await expect(page.locator('input[name="whatsapp_phone"]')).toHaveValue("");
  expect(await page.content()).not.toContain("+923001234567");
  form = page.locator("form").filter({ has: page.getByRole("heading", { name: "WhatsApp preference" }) });
  await form.locator('input[name="whatsapp_enabled"]').uncheck();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator('input[name="whatsapp_enabled"]')).not.toBeChecked();
});

test("ICE draft, contact creation, consent renewal and confirmed removal", async ({ page }) => {
  await login(page); await page.goto(`/my-qr/${id("ICE")}`);
  await page.getByLabel("Display name or alias").fill("Synthetic ICE alias");
  await page.getByLabel("Replace medical notes (optional)").fill("Synthetic private note");
  await page.locator(".qr-editor").first().getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status")).toHaveText("Changes saved.");
  let form = page.locator("form").filter({ has: page.getByRole("heading", { name: "Add emergency contact" }) });
  await form.getByLabel("Relationship", { exact: true }).fill("Parent");
  await form.locator('input[name="phone"]').fill("+923001234567");
  await form.locator('input[name="published"]').check();
  await form.locator('input[name="consent"]').check();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("••••4567", { exact: true })).toBeVisible();
  await expect(page.locator('input[name="phone"]').first()).toHaveValue("");
  expect(await page.content()).not.toContain("+923001234567");
  form = page.locator("form").filter({ has: page.getByRole("heading", { name: "Edit contact" }) });
  await form.getByLabel("Relationship", { exact: true }).fill("Guardian");
  await form.locator('input[name="consent"]').check();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator('input[name="relationship_label"]').first()).toHaveValue("Guardian");
  form = page.locator("form").filter({ has: page.getByRole("heading", { name: "Edit contact" }) });
  await form.locator('input[name="remove"]').check(); await form.locator('input[name="confirm_remove"]').check();
  await form.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Edit contact" })).toHaveCount(0);
});

test("key outage still permits privacy disabling without clearing retained medical data", async ({ page, request }) => {
  await profile(request, id("ICE"), "ice", { published: true, show_medical_notes: true,
    medical_notes: "Synthetic private note",
    publication_consent_accepted: true, publication_consent_version: "ice-public-v1" });
  await login(page);
  await request.post(`${api}/fixture/keys/off`);
  try {
    await page.goto(`/my-qr/${id("ICE")}`);
    const form = page.locator("form").filter({ hasText: "Turn publication off while preserving saved private data." });
    await expect(form).toBeVisible();
    await form.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByRole("status")).toHaveText("Changes saved.");
  } finally { await request.post(`${api}/fixture/keys/on`); }
  const result = await profile(request, id("ICE"), "ice");
  expect(result.published).toBe(false); expect(result.medical_notes).toBe("Synthetic private note");
});

test("mobile Urdu dashboard fits the screen and keeps exact QR links", async ({ page, context }) => {
  await context.addCookies([{ name: "safereturn-language", value: "ur", url: "http://127.0.0.1:3100" }]);
  // Sign in in English, then restore the persisted Urdu preference for dashboard.
  await context.clearCookies(); await login(page);
  await context.addCookies([{ name: "safereturn-language", value: "ur", url: "http://127.0.0.1:3100" }]);
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/dashboard");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator(`a[href="/my-qr/${id("LOST")}"]`)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/task34-dashboard-ur-mobile.png", fullPage: true });
});

test("forged scan context cannot present confirmation or a credential form", async ({ page, context }) => {
  await login(page);
  await context.addCookies([{ name: "sr-scan", value: "forged", url: "http://127.0.0.1:3100" }, { name: "sr-activation", value: "forged", url: "http://127.0.0.1:3100" }]);
  await page.goto("/activate");
  await expect(page.getByText("Scan a QR on your kit to start.", { exact: false })).toBeVisible();
  await expect(page.locator('input[name="activation_secret"]')).toHaveCount(0);
  await expect(page.locator('input[name="confirm"]')).toHaveCount(0);
});

test("scan survives login and activates both tags without a second scan", async ({ page, context }) => {
  await page.goto(`/q/${id("TOKEN")}`);
  await expect(page.getByRole("heading", { name: "This QR is not activated" })).toBeVisible();
  await page.getByRole("button", { name: "Activate QR", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  const cookie = (await context.cookies()).find(c => c.name === "sr-scan");
  expect(cookie?.httpOnly).toBe(true); expect(cookie?.sameSite).toBe("Lax");
  await page.getByLabel("Email address").fill("fixture@example.invalid");
  await page.locator('input[name="password"]').fill("synthetic-password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(/\/activate$/);
  await page.locator('input[name="activation_secret"]').fill(id("ACTIVATION_SECRET"));
  await page.getByRole("button", { name: "Check eligibility" }).click();
  await expect(page.getByRole("button", { name: "Activate both QR tags" })).toBeVisible();
  expect(page.url()).not.toContain(id("ACTIVATION_SECRET"));
  await page.locator('input[name="confirm"]').check();
  await page.getByRole("button", { name: "Activate both QR tags" }).click();
  await expect(page).toHaveURL(new RegExp(`/kits/${id("ACTIVATION_PAIR")}\\?activated=1$`));
  await expect(page.getByRole("status")).toContainText("Both QR tags are active");
  await expect(page.locator(".qr-card")).toHaveCount(2);
  expect((await context.cookies()).some(c => ["sr-scan", "sr-activation"].includes(c.name))).toBe(false);
});
