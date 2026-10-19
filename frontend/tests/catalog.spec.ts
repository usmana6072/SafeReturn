import { test, expect as baseExpect } from "@playwright/test";
const expect=baseExpect.configure({timeout:15000});
test.setTimeout(90000);
test.use({actionTimeout:15000});
const api="http://127.0.0.1:8115";
test.beforeEach(async({page})=>{await page.route("https://res.cloudinary.com/**",route=>route.fulfill({status:200,contentType:"image/png",body:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDTsAAAAASUVORK5CYII=","base64")}));});
test("featured data, exact money, details and no draft leakage",async({page})=>{
 await page.goto("/"); const cards=page.locator(".featured-scroll .catalog-card");await expect(cards).toHaveCount(2);
 await expect(cards.first()).toContainText("Synthetic card 1");await expect(cards.first()).toContainText("PKR 150.25");
 await expect(page.locator("body")).not.toContainText("Synthetic card 3");
 await cards.first().getByRole("link",{name:"View details"}).click();await expect(page).toHaveURL(/shop\/PROJECTION-1/);await expect(page.getByRole("heading",{level:1})).toHaveText("Synthetic card 1");
});
test("shop search and category URLs",async({page})=>{
 await page.goto("/shop?q=absent-catalog-item");await expect(page.locator(".catalog-card")).toHaveCount(0);
 await page.getByRole("link",{name:"Reset filters"}).click();await expect(page.locator(".catalog-card")).toHaveCount(2);
 await page.getByRole("link",{name:"QR Stickers",exact:true}).click();await expect(page).toHaveURL(/category=qr-stickers/);
});
for(const width of [320,1440]) test(`featured keyboard, RTL and overflow ${width}`,async({page})=>{
 await page.setViewportSize({width,height:900});await page.goto("/");
 await page.getByRole("button",{name:"Next products",exact:true}).focus();await expect(page.locator(":focus")).toBeVisible();await page.keyboard.press("Enter");
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.getByRole("button",{name:"اردو",exact:true}).click();await expect(page.locator("html")).toHaveAttribute("dir","rtl");
 await expect(page.locator(".featured-scroll .catalog-card")).toHaveCount(2);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`test-results/task51-ur-${width}.png`,fullPage:true});
});
test("feature changes appear on next request; empty fallback",async({page,request})=>{
 await request.post(`${api}/fixture/catalog/off`);try {await page.goto("/");await expect(page.locator(".featured-scroll")).toHaveCount(0);await expect(page.getByRole("status")).toContainText("No featured products");}finally {await request.post(`${api}/fixture/catalog/on`);}
 await page.reload();await expect(page.locator(".featured-scroll .catalog-card")).toHaveCount(2);
});
test("anonymous admin denial and CSRF boundary",async({page,request})=>{
 await page.goto("/admin/products");await expect(page).toHaveURL(/login/);await expect(page.getByRole("heading",{name:"Catalog management"})).toHaveCount(0);
 expect((await request.get("/admin/catalog-api?path=/admin/products")).status()).toBe(401);
});
test("admin browser draft creation and versioned edit",async({page})=>{
 await page.goto("/login");await page.getByLabel("Email address").fill("catalog-fixture@example.invalid");await page.locator('input[name="password"]').fill("synthetic-password");await page.getByRole("button",{name:"Log in",exact:true}).click();await expect(page).toHaveURL(/account/);
 await page.goto("/admin/products");await expect(page.getByRole("heading",{name:"Catalog management"})).toBeVisible();
 const forged=await page.request.post("/admin/catalog-api",{headers:{Origin:"https://untrusted.invalid"},data:{path:"/admin/products",method:"POST",body:{name:"Forged",slug:"forged-change"}}});expect(forged.status()).toBe(403);
 await page.getByRole("button",{name:"New product",exact:true}).click();await page.getByLabel("slug",{exact:true}).fill("browser-synthetic-draft");await page.getByLabel("name",{exact:true}).fill("Browser synthetic draft");
 await page.getByRole("button",{name:"Save",exact:true}).click();await expect(page.getByRole("status")).toHaveText("Saved.");
 const section=page.locator("section").filter({has:page.getByRole("heading",{name:"Browser synthetic draft",exact:true})});await section.getByRole("button",{name:"Edit product",exact:true}).click();await page.getByLabel("name",{exact:true}).fill("Browser edited draft");await page.getByRole("button",{name:"Save",exact:true}).click();await expect(page.getByRole("heading",{name:"Browser edited draft",exact:true})).toBeVisible();
 await page.goto("/shop");await expect(page.locator("body")).not.toContainText("Browser edited draft");
});

test("provider outage has a recoverable bilingual fallback",async({page,request})=>{
 await request.post(`${api}/fixture/catalog/unavailable`);try {await page.goto("/");await expect(page.getByRole("status")).toContainText("Products could not be loaded");await page.goto("/shop/PROJECTION-1");await expect(page.getByRole("heading",{level:1})).toContainText("Product could not be loaded");await page.goto("/");await page.getByRole("button",{name:"اردو",exact:true}).click();await expect(page.getByRole("status")).toContainText("مصنوعات ابھی لوڈ نہیں ہو سکیں");}finally{await request.post(`${api}/fixture/catalog/on`);}
});

test("admin signed upload finalizes only the verified public asset",async({page})=>{
 await page.route("https://api.cloudinary.com/v1_1/synthetic/image/upload",async route=>{expect(route.request().postData()).toContain("signature");await route.fulfill({status:200,headers:{"Access-Control-Allow-Origin":"http://127.0.0.1:3100"},contentType:"application/json",body:JSON.stringify({public_id:"synthetic"})});});
 await page.goto("/login");await page.getByLabel("Email address").fill("catalog-upload@example.invalid");await page.locator('input[name="password"]').fill("synthetic-password");await page.getByRole("button",{name:"Log in",exact:true}).click();await expect(page).toHaveURL(/account/);
 await page.goto("/admin/products");const section=page.locator("section").filter({has:page.getByRole("heading",{name:"Browser edited draft",exact:true})});await section.getByRole("button",{name:"Attach public image"}).click();
 await page.getByLabel("alt text",{exact:true}).fill("Browser marketing product photo");await page.getByLabel("Upload public product image").setInputFiles({name:"public-product.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDTsAAAAASUVORK5CYII=","base64")});
 await page.getByRole("button",{name:"Save",exact:true}).click();await expect(page.getByRole("status")).toHaveText("Saved.");await expect(section).toContainText("Browser marketing product photo");
});
