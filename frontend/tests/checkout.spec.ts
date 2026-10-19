import {test,expect as baseExpect,type Page} from "@playwright/test";
const expect=baseExpect.configure({timeout:15000}),api="http://127.0.0.1:8115";
const variants=process.env.CHECKOUT_TEST_VARIANTS!.split(",");
test.setTimeout(90000);test.use({actionTimeout:15000});
async function seed(page:Page){await page.goto("/cart");await page.evaluate(({variants})=>localStorage.setItem("safereturn-cart-v1",JSON.stringify([{variant_id:variants[0],lost:3,ice:0},{variant_id:variants[1],lost:0,ice:2}])),{variants});}
async function login(page:Page){await page.goto("/login");await page.getByLabel("Email address").fill(`checkout+${test.info().testId}@example.invalid`);await page.locator('input[name="password"]').fill("synthetic-password");await page.getByRole("button",{name:"Log in",exact:true}).click();await expect(page).toHaveURL(/account/);}
async function address(page:Page){await page.getByLabel("Recipient name",{exact:true}).fill("Synthetic browser recipient");await page.getByLabel("Phone",{exact:true}).fill("+923001234567");await page.getByLabel("Street address",{exact:true}).fill("Synthetic private browser street");await page.getByLabel("City",{exact:true}).fill("Lahore");await page.getByLabel("I confirm the shipping phone and address.").check();}
async function prepare(page:Page){await seed(page);await login(page);await page.goto("/checkout");await address(page);}

test("independent counts create one cart kit and survive guest sign-in redirect",async({page})=>{
 await page.goto("/shop/SYNTHETIC-0");await page.getByLabel("Lost copies — Synthetic size 0",{exact:true}).fill("3");await page.getByLabel("ICE copies — Synthetic size 1",{exact:true}).fill("2");await page.getByRole("button",{name:"Add to cart",exact:true}).click();await expect(page).toHaveURL(/cart/);await expect(page.getByText("Total copies: 5",{exact:false})).toBeVisible();
 await page.getByRole("link",{name:"Continue to checkout"}).click();await expect(page).toHaveURL(/login/);expect(await page.evaluate(()=>JSON.parse(localStorage.getItem("safereturn-cart-v1")!).length)).toBe(2);
});
test("quote review and confirmation commit an awaiting-payment order",async({page})=>{
 await prepare(page);const quoteResponse=page.waitForResponse(r=>r.url().endsWith("/checkout/api")&&r.status()===201);await page.getByRole("button",{name:"Get final quote"}).click();const q=await(await quoteResponse).json();expect(q.new_pair_count).toBe(1);expect(q.total_pkr).toBe("11.00");expect(JSON.stringify(q)).not.toContain("Synthetic private browser street");
 await expect(page.getByRole("region",{name:"Final quote"})).toContainText("PKR 11.00");await expect(page.getByRole("button",{name:"Confirm order"})).toBeDisabled();
 expect((await page.request.post("/checkout/api",{headers:{Origin:"https://untrusted.invalid"},data:{path:"/me/checkout/quotes",body:{},key:"synthetic-csrf-key"}})).status()).toBe(403);
 await page.getByLabel("I accept the total and shipping details.").check();await page.getByRole("button",{name:"Confirm order"}).click();await expect(page.getByRole("heading",{name:"Order placed."})).toBeVisible();await expect(page.getByText("Payment verification is still pending.")).toBeVisible();expect(await page.evaluate(()=>localStorage.getItem("safereturn-cart-v1"))).toBeNull();
});
test("expired quote requires refresh and preserves address and cart",async({page,request})=>{
 await prepare(page);const response=page.waitForResponse(r=>r.url().endsWith("/checkout/api")&&r.status()===201);await page.getByRole("button",{name:"Get final quote"}).click();const q=await(await response).json();await request.post(`${api}/fixture/checkout/expire/${q.quote_id}`);
 await page.getByLabel("I accept the total and shipping details.").check();await page.getByRole("button",{name:"Confirm order"}).click();await expect(page.getByRole("status")).toContainText("Quote expired or already used");await expect(page.getByLabel("Street address",{exact:true})).toHaveValue("Synthetic private browser street");
 await page.getByRole("button",{name:"Refresh quote"}).click();await expect(page.getByLabel("I accept the total and shipping details.")).not.toBeChecked();
});
test("stock shortage does not discard private form fields or cart",async({page,request})=>{
 await prepare(page);await request.post(`${api}/fixture/checkout/stock/off`);try{await page.getByRole("button",{name:"Get final quote"}).click();await expect(page.getByRole("status")).toContainText("Pair stock is unavailable");await expect(page.getByLabel("Street address",{exact:true})).toHaveValue("Synthetic private browser street");expect(await page.evaluate(()=>localStorage.getItem("safereturn-cart-v1"))).not.toBeNull();}finally{await request.post(`${api}/fixture/checkout/stock/on`);}
});
test("lost quote response retries the same idempotency key",async({page})=>{
 await prepare(page);let savedId="",firstKey="";
 await page.route("**/checkout/api",async route=>{firstKey=route.request().postDataJSON().key;const response=await route.fetch();savedId=(await response.json()).quote_id;await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({error:{code:"PROVIDER_UNAVAILABLE"}})});});await page.getByRole("button",{name:"Get final quote"}).click();await expect(page.getByRole("status")).toContainText("Request could not be completed");await page.unroute("**/checkout/api");
 const request=page.waitForRequest(r=>r.url().endsWith("/checkout/api"));const response=page.waitForResponse(r=>r.url().endsWith("/checkout/api")&&r.status()===201);await page.getByRole("button",{name:"Get final quote"}).click();expect((await request).postDataJSON().key).toBe(firstKey);expect((await(await response).json()).quote_id).toBe(savedId);
});
for(const width of [320,1440])test(`Urdu cart keyboard and layout ${width}`,async({page})=>{
 await seed(page);await page.goto("/");await page.getByRole("button",{name:"اردو",exact:true}).click();await expect(page.locator("html")).toHaveAttribute("dir","rtl");await page.goto("/cart");await page.setViewportSize({width,height:900});await expect(page.locator("html")).toHaveAttribute("dir","rtl");await page.locator('input[type="number"]').first().focus();await expect(page.locator(":focus")).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`test-results/task52-cart-ur-${width}.png`,fullPage:true});
});
