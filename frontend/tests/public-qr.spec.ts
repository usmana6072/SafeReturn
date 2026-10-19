import { test, expect } from "@playwright/test";
const token = (kind: string) => {
  const value = process.env[`PUBLIC_QR_${kind.toUpperCase()}`];
  if (!value) throw new Error("Run through the isolated PostgreSQL browser controller");
  return value;
};
const forbidden = ["+923001234567", "PRIVATE-PHONE-CIPHERTEXT", "HIDDEN-LABEL", "HIDDEN-NAME", "medical_notes_ciphertext", "phone_ciphertext", "owner_user_id", "activation_secret"];

test("anonymous Lost HTML/API/RSC are allowlisted and published text is escaped", async ({ page, request }) => {
  const path = `/q/${token("lost")}`;
  const response = await page.goto(path);
  await expect(page.getByRole("heading", {name:"Found this item?"})).toBeVisible();
  await expect(page.getByText("Public bag", {exact:true})).toBeVisible();
  await expect(page.getByText("<script>window.scanInjected=true</script>",{exact:true})).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as {scanInjected?:boolean}).scanInjected)).toBeUndefined();
  expect(response?.headers()["cache-control"]).toContain("no-store");
  for (const value of forbidden) expect(await response!.text()).not.toContain(value);
  const rsc = await request.get(path,{headers:{RSC:"1"}});
  for (const value of forbidden) expect(await rsc.text()).not.toContain(value);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content",/noindex/);
  await expect(page.locator('meta[name="referrer"]')).toHaveAttribute("content","no-referrer");
  await expect(page.locator('p[lang="en"]')).toBeVisible();
  await expect(page.locator('p[lang="ur"]')).toBeVisible();
  await page.screenshot({path:"test-results/public-lost-desktop.png",fullPage:true});
});

test("ICE contacts render without profile name and disclose no phone on any initial response", async ({page, request}) => {
  const path=`/q/${token("ice")}`;
  await page.goto(path);
  await expect(page.getByRole("heading",{name:"Emergency information"})).toBeVisible();
  await expect(page.getByText(/Parent/)).toBeVisible();
  await expect(page.getByRole("button",{name:/reveal/i})).toBeVisible();
  expect(await page.locator('a[href^="tel:"]').count()).toBe(0);
  const rsc=await request.get(path,{headers:{RSC:"1"}});
  const document=await request.get(path);
  const texts=[await page.content(),await rsc.text(),await document.text()];
  for(const text of texts)for(const value of forbidden)expect(text).not.toContain(value);
  await expect(page.getByText("Owner-provided information is not medically verified.",{exact:true})).toBeVisible();
});

test("language switch preserves scan, provides Urdu RTL and fits a small screen",async({page})=>{
  await page.setViewportSize({width:320,height:740});
  const path=`/q/${token("ice")}`;
  await page.goto(path);
  await page.getByRole("button",{name:"اردو",exact:true}).click();
  await expect(page).toHaveURL(path);
  await expect(page.locator('html')).toHaveAttribute('lang','ur');
  await expect(page.locator('html')).toHaveAttribute('dir','rtl');
  await expect(page.getByRole('heading',{name:'ہنگامی معلومات',exact:true})).toBeVisible();
  await expect(page.locator('p[lang="en"]')).toBeVisible();
  await expect(page.locator('p[lang="ur"]')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  const button=page.getByRole('button',{name:'English',exact:true});
  await button.focus();await expect(button).toBeFocused();
  await page.screenshot({path:'test-results/public-ice-urdu-mobile.png',fullPage:true});
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(path);
  await expect(page.locator('html')).toHaveAttribute('lang','en');
});

for(const [state,title]of Object.entries({unactivated:'This tag is not active yet.',owner_disabled:'This tag is currently unavailable.',admin_suspended:'This tag is temporarily unavailable.',revoked:'This QR code is no longer valid.'})){
  test(`safe ${state} screen retains scan context`,async({page})=>{
    await page.goto(`/q/${token(state)}`);
    await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
    await expect(page.getByText('Public bag',{exact:true})).toHaveCount(0);
    await expect(page.getByRole('button',{name:'Activate QR',exact:true})).toHaveCount(state==='unactivated'?1:0);
    for(const value of forbidden)expect(await page.content()).not.toContain(value);
  });
}
test('unknown scan is a generic bilingual unavailable page without login',async({page})=>{
  await page.goto('/q/'+'unknown'.repeat(5));
  await expect(page.getByRole('heading',{name:'We could not verify this QR code.'})).toBeVisible();
  await expect(page.locator('p[lang="ur"]')).toBeVisible();
  expect(new URL(page.url()).pathname).toContain('/q/');
});
