import { test, expect } from "@playwright/test";

async function challenge(page: import("@playwright/test").Page, proof = "success") {
  await page.route("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit", route => route.fulfill({
    contentType: "application/javascript",
    body: `window.turnstile={render:(el,o)=>{setTimeout(()=>o.callback(${JSON.stringify(proof)}==='success'?o.action+':'+o.cData+':'+crypto.randomUUID():${JSON.stringify(proof)}),20);return 'fixture';},remove:()=>{}};`,
  }));
}

test("denied location leaves a keyboard-submittable form and truthful receipt", async ({ page }) => {
  await challenge(page);
  await page.addInitScript(() => {
    let requests = 0;
    Object.defineProperty(window, "fixtureLocationRequests", { get: () => requests });
    Object.defineProperty(navigator, "geolocation", { value: {
      getCurrentPosition: (_success: unknown, failure: (error: unknown) => void) => { requests++; failure({ code: 1 }); },
    } });
  });
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto(`/q/${process.env.PUBLIC_QR_LOST}`);
  const form = page.locator("form[data-finder-message]");
  await expect(form).toBeVisible();
  expect(await page.evaluate(() => Reflect.get(window, "fixtureLocationRequests"))).toBe(0);
  const location = form.getByRole("checkbox", { name: /Share my one-time location/ });
  await expect(location).toHaveAccessibleDescription(/shared once with this item's owner/);
  await location.focus();
  await page.keyboard.press("Space");
  await expect(location).not.toBeChecked();
  await expect(form.getByRole("status")).toContainText("Location is unavailable");
  await expect(form.locator('[name="latitude"]')).toHaveValue("");
  await form.getByRole("textbox", { name: "Email", exact: true }).fill("finder@example.test");
  await form.getByRole("textbox", { name: "Message", exact: true }).fill("I found your keys near the entrance.");
  await form.getByRole("checkbox", { name: /I consent/ }).focus();
  await page.keyboard.press("Space");
  const submit = form.getByRole("button", { name: "Send secure message", exact: true });
  await expect(submit).toBeEnabled();
  await submit.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Your message is saved. Email notification is not guaranteed.");
});

test("challenge outage preserves typed data and never claims email delivery", async ({ page }) => {
  await challenge(page, "outage");
  await page.goto(`/q/${process.env.PUBLIC_QR_LOST}`);
  const form = page.locator("form[data-finder-message]");
  await form.getByRole("textbox", { name: "Email", exact: true }).fill("finder@example.test");
  await form.getByRole("textbox", { name: "Message", exact: true }).fill("I found your bag near the reception.");
  await form.getByRole("checkbox", { name: /I consent/ }).check();
  const submit = form.getByRole("button", { name: "Send secure message", exact: true });
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect(form.getByRole("alert")).toContainText("could not be submitted");
  await expect(form.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("I found your bag near the reception.");
  await expect(form.getByRole("textbox", { name: "Email", exact: true })).toHaveValue("finder@example.test");
  await expect(form.getByRole("checkbox", { name: /I consent/ })).toBeChecked();
  await expect(page.getByRole("status").filter({ hasText: "Your message is saved" })).toHaveCount(0);
});

test("public form has labels, touch targets and no private notification payload", async ({ page, request }) => {
  await challenge(page);
  await page.setViewportSize({ width: 320, height: 740 });
  const path = `/q/${process.env.PUBLIC_QR_LOST}`;
  await page.goto(path);
  const form = page.locator("form[data-finder-message]");
  await expect(form.getByRole("textbox", { name: "Message", exact: true })).toBeVisible();
  for (const locator of [form.getByRole("textbox", { name: "Email", exact: true }), form.getByRole("combobox", { name: "Preferred contact", exact: true }), form.locator('label:has(input[name="contact_consent_accepted"])')]) {
    expect((await locator.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  }
  await form.getByRole("textbox", { name: "Email", exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(form.getByRole("textbox", { name: "Phone", exact: true })).toBeFocused();
  for (const response of [await request.get(path), await request.get(path, { headers: { RSC: "1" } })]) {
    const html = await response.text();
    for (const privateValue of ["PRIVATE-FINDER-MESSAGE", "original-owner@example.test", "recipient_email_snapshot_ciphertext", "provider_message_id"]) expect(html).not.toContain(privateValue);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
