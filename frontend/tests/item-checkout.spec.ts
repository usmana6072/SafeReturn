import {test,expect} from "@playwright/test";
const bundle=require("./qa-browser-bundle.cjs");
const pid="00000000-0000-4000-8000-000000000010",v1="00000000-0000-4000-8000-000000000001",v2="00000000-0000-4000-8000-000000000002",qid="00000000-0000-4000-8000-000000000030",oid="00000000-0000-4000-8000-000000000040",aid="00000000-0000-4000-8000-000000000050";
const key="safereturn-item-cart-v2";
const product={product_id:pid,name:"Lost sticker",commerce_model:"single_qr",checkout_available:true,qr_type:"lost",price_per_copy:"12.30",max_order_copies:10,variants:[{variant_id:v1,name:"35 mm"},{variant_id:v2,name:"45 mm"}]};
const cart=[{product_id:pid,identity_group:null,sizes:[{variant_id:v1,copies:2},{variant_id:v2,copies:3}]}];
const instructions={version:"synthetic-v1",bank_name:"Synthetic Bank",account_title:"Synthetic payee",account_number:"SYNTHETIC-ACCOUNT",raast_id:"SYNTHETIC-RAAST",instructions_en:"Synthetic official instructions",instructions_ur:"منظور شدہ آزمائشی ہدایات",currency_code:"PKR"};
async function mount(page:any,exportName:string,props:any,storage:any=cart,addresses:any={items:[],book_version:0}){
 await page.route("https://item-checkout.test/**",(r:any)=>r.request().resourceType()!=="document"?r.fallback():r.fulfill({contentType:"text/html",body:'<!doctype html><html><head><style>*{box-sizing:border-box}body{margin:0;padding:16px;font:16px sans-serif}label{display:block;margin:8px 0}input{max-width:100%}fieldset{min-width:0;margin:12px 0}dd{margin:0;overflow-wrap:anywhere}</style></head><body><div id="root"></div></body></html>'}));
 await page.route("**/account/shipping-addresses/api",(r:any)=>r.fulfill({json:addresses}));
 await page.goto("https://item-checkout.test/");
 await page.evaluate(({props,key,storage}:any)=>{(window as any).qaProps=props;localStorage.setItem(key,JSON.stringify(storage));localStorage.setItem("safereturn-cart-v1","legacy-cart-canary");},{props,key,storage});
 await page.addScriptTag({content:bundle({componentPath:exportName==="KitConfigurator"?"../components/checkout.tsx":exportName==="PaymentForm"?"../components/payments.tsx":"../components/item-checkout.tsx",exportName})});
}
async function fillAddress(page:any){for(const [label,value] of [["Recipient name","Synthetic"],["Phone","+923001234567"],["Street address","Synthetic street"],["City","Lahore"]])await page.getByLabel(label,{exact:true}).fill(value);await page.getByLabel("I confirm the shipping phone and address.",{exact:true}).check();}

test('saved address quotes use its ID and version; deleted selections require a new confirmed address',async({page})=>{
 const saved={id:aid,version:4,is_default:true,recipient_name:"Saved customer",phone:"+923001234567",address:"Private saved street",city:"Lahore",province:null,postal_code:"00123"};
 const commands:any[]=[];
 await page.route('**/checkout/api',r=>{commands.push(r.request().postDataJSON());return r.fulfill({status:503,json:{error:{code:'PROVIDER_UNAVAILABLE'}}});});
 await mount(page,'ItemCheckoutCart',{products:[product],language:'en',checkout:true},cart,{book_version:8,items:[saved]});
 await expect(page.getByLabel('Choose shipping address')).toHaveValue(aid);
 await expect(page.getByLabel('Recipient name',{exact:true})).toHaveCount(0);
 await page.getByLabel('I confirm the shipping phone and address.',{exact:true}).check();
 await page.getByRole('button',{name:'Get final quote',exact:true}).click();
 expect(commands[0].body).toMatchObject({shipping_address_id:aid,shipping_address_version:4,contact_phone_confirmation:true});
 expect(commands[0].body).not.toHaveProperty('address');
 await page.route('**/account/shipping-addresses/api',r=>r.fulfill({json:{book_version:9,items:[]}}));
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(page.getByLabel('Choose shipping address')).toHaveValue('');
 await expect(page.getByLabel('I confirm the shipping phone and address.',{exact:true})).not.toBeChecked();
 await fillAddress(page);await page.getByRole('button',{name:'Get final quote',exact:true}).click();
 expect(commands[1].body).toHaveProperty('address');expect(commands[1].body).not.toHaveProperty('shipping_address_id');
});

test('phone requires country code; three copies do not require a separate identity',async({page})=>{
 const commands:any[]=[];
 await page.route('**/checkout/api',r=>{commands.push(r.request().postDataJSON());return r.fulfill({status:503,json:{error:{code:'PROVIDER_UNAVAILABLE'}}});});
 const threeCopies=[{product_id:pid,identity_group:null,sizes:[{variant_id:v1,copies:3}]}];
 await mount(page,'ItemCheckoutCart',{products:[product],language:'en',checkout:true},threeCopies);
 await fillAddress(page);
 const phone=page.getByLabel('Phone',{exact:true});
 await phone.fill('3001234567');
 await page.getByLabel('I confirm the shipping phone and address.',{exact:true}).check();
 await page.getByRole('button',{name:'Get final quote',exact:true}).click();
 expect(await phone.evaluate((el:HTMLInputElement)=>el.validity.patternMismatch)).toBe(true);
 await expect(phone).toBeFocused();
 expect(commands).toHaveLength(0);
 await expect(page.locator('#checkout-phone-help')).toContainText('Country code required');
 await phone.fill('+923001234567');
 await page.getByLabel('I confirm the shipping phone and address.',{exact:true}).check();
 await page.getByRole('button',{name:'Get final quote',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('preserved');
 expect(commands).toHaveLength(1);
 expect(commands[0].body.items).toEqual(threeCopies);
 expect(commands[0].body.address.phone).toBe('+923001234567');
});

test("single-type multi-size quote and submit retain legacy cart and server totals",async({page},info)=>{
 const commands:any[]=[];let uncertain=true;
 await page.route("**/checkout/api",async r=>{const command=r.request().postDataJSON();commands.push(command);if(command.path.endsWith("/confirm")){if(uncertain){uncertain=false;return r.fulfill({status:503,json:{error:{code:"UNAVAILABLE",message:"PRIVATE_CANARY"}}});}return r.fulfill({status:201,json:{order_id:oid}});}return r.fulfill({status:201,json:{quote_id:qid,expires_at:new Date(Date.now()+60000).toISOString(),currency_code:"PKR",subtotal_pkr:"61.50",shipping_pkr:"50.00",tax_pkr:"2.50",total_pkr:"114.00",identity_count:1,payment_instructions:instructions,items:[{product_name:"Lost sticker",qr_type:"lost",quantity:5,unit_price:"12.30",line_total:"61.50",sizes:[{name:"35 mm",copies:2},{name:"45 mm",copies:3}]}]}});});
 await mount(page,"ItemCheckoutCart",{products:[product],language:"en",checkout:true});await fillAddress(page);await page.getByRole("button",{name:"Get final quote",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Review order"})).toBeVisible();await expect(page.getByText("5 × PKR 12.30 = PKR 61.50",{exact:true})).toBeVisible();await expect(page.getByText("Payment evidence is not verified payment.",{exact:true})).toBeVisible();
 await page.screenshot({path:info.outputPath("quote-en.png"),fullPage:true});expect(commands[0].body).toMatchObject({commerce_model:"single_qr",items:cart});expect(JSON.stringify(commands[0].body)).not.toMatch(/price|qr_uses|public_token/);
 await page.getByLabel("I accept the total and shipping details.",{exact:true}).check();await page.getByRole("button",{name:"Submit order",exact:true}).click();await expect(page.getByRole("status")).toContainText("preserved");expect(await page.evaluate(key=>localStorage.getItem(key),key)).not.toBeNull();
 await page.getByRole("button",{name:"Submit order",exact:true}).click();await expect(page.getByRole("heading",{name:"Order submitted."})).toBeVisible();expect(commands[1].key).toBe(commands[2].key);expect(await page.evaluate(key=>localStorage.getItem(key),key)).toBeNull();expect(await page.evaluate(()=>localStorage.getItem("safereturn-cart-v1"))).toBe("legacy-cart-canary");expect(await page.locator("body").innerText()).not.toContain("PRIVATE_CANARY");await page.screenshot({path:info.outputPath("submitted-en.png"),fullPage:true});
});

test("default product lines merge and explicit identity groups stay separate",async({page})=>{
 await page.route("https://item-checkout.test/cart",r=>r.fulfill({contentType:"text/html",body:"saved"}));
 await mount(page,"ItemConfigurator",{product,language:"en"},cart);
 await page.getByLabel("35 mm",{exact:true}).fill("1");await page.getByRole("button",{name:"Add to cart",exact:true}).click();await page.waitForURL("**/cart");let stored=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key);expect(stored).toHaveLength(1);expect(stored[0].sizes[0].copies).toBe(3);
 await page.unroute("https://item-checkout.test/**");await mount(page,"ItemConfigurator",{product,language:"en"},cart);await page.getByLabel("45 mm",{exact:true}).fill("2");await page.getByLabel("Create a separate QR identity for this product",{exact:true}).check();await page.getByRole("button",{name:"Add to cart",exact:true}).click();await page.waitForURL("**/cart");stored=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key);expect(stored).toHaveLength(2);expect(stored[1].identity_group).toMatch(/^[a-f0-9-]{36}$/);
});

test("stale quotes and denial preserve cart and hide private errors",async({page})=>{
 const commands:any[]=[];
 await page.route("**/checkout/api",r=>{const c=r.request().postDataJSON();commands.push(c);return c.path.endsWith("/confirm")?r.fulfill({status:409,json:{error:{code:"QUOTE_STALE",message:"PRIVATE_CANARY"}}}):r.fulfill({json:{quote_id:qid,expires_at:new Date(Date.now()+60000).toISOString(),items:[],payment_instructions:instructions,subtotal_pkr:"61.50",shipping_pkr:"50.00",tax_pkr:"2.50",total_pkr:"114.00",currency_code:"PKR"}});});
 await mount(page,"ItemCheckoutCart",{products:[product],language:"en",checkout:true});await fillAddress(page);await page.getByRole("button",{name:"Get final quote",exact:true}).click();await page.getByLabel("I accept the total and shipping details.",{exact:true}).check();await page.getByRole("button",{name:"Submit order",exact:true}).click();await expect(page.getByRole("status")).toContainText("fresh quote");expect(await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key)).toEqual(cart);expect(await page.locator("body").innerText()).not.toContain("PRIVATE_CANARY");await page.getByRole("button",{name:"Get final quote",exact:true}).click();await expect(page.getByRole("heading",{name:"Review order"})).toBeVisible();expect(commands[0].key).not.toBe(commands[2].key);
});

test("private evidence retry never declares verified payment",async({page})=>{
 let uploaded=0,finalized=0;const commands:any[]=[];
 await page.route("**/payments/api**",async r=>{if(r.request().method()==="GET")return r.fulfill({json:r.request().url().includes("payment-instructions")?instructions:{items:[]}});const c=r.request().postDataJSON();commands.push(c);if(c.path.endsWith("/payment-attempts"))return r.fulfill({json:{attempt_id:aid,state:"under_review"}});if(c.path.endsWith("/evidence-uploads"))return r.fulfill({json:{upload_url:"https://private-storage.synthetic.invalid/evidence",upload_token:"synthetic-private-grant"}});finalized++;return r.fulfill({status:finalized===1?503:200,json:finalized===1?{error:{code:"UNAVAILABLE"}}:{received:true}});});
 await page.route("https://private-storage.synthetic.invalid/**",r=>{uploaded++;return r.fulfill({status:200,headers:{"Access-Control-Allow-Origin":"*"},body:""});});
 await mount(page,"PaymentForm",{orderId:oid,language:"en"});await expect(page.getByText("Synthetic Bank",{exact:true})).toBeVisible();await page.getByLabel("Sender holder name",{exact:true}).fill("Synthetic holder");await page.getByLabel("Sender account",{exact:true}).fill("SYNTHETIC");await page.getByRole("button",{name:"Submit for review",exact:true}).click();await page.getByLabel("Optional private evidence",{exact:true}).setInputFiles({name:"proof.png",mimeType:"image/png",buffer:Buffer.from("synthetic-proof")});await page.getByRole("button",{name:"Upload evidence",exact:true}).click();await expect(page.getByRole("status")).toContainText("Request not confirmed");await page.getByRole("button",{name:"Upload evidence",exact:true}).click();await expect(page.getByRole("status")).toHaveText("Evidence received. Payment remains under review.");expect(uploaded).toBe(1);const final=commands.filter(c=>c.path.endsWith("evidence-finalize"));expect(final[0].key).toBe(final[1].key);expect(await page.evaluate(()=>localStorage.getItem("safereturn-item-cart-v2"))).not.toContain("synthetic-private-grant");
});

test("Urdu single-QR cart fits mobile and unavailable size blocks quote",async({page},info)=>{
 await page.setViewportSize({width:375,height:900});await mount(page,"ItemCheckoutCart",{products:[],language:"ur",checkout:true});await expect(page.getByRole("alert")).toBeVisible();await expect(page.getByRole("button",{name:"حتمی قیمت حاصل کریں",exact:true})).toBeDisabled();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath("cart-ur-mobile.png"),fullPage:true});
});

test('published browse-only product cannot request checkout and preserves its cart',async({page})=>{let writes=0;await page.route('**/checkout/api',r=>{writes++;return r.fulfill({status:503,json:{error:{code:'SINGLE_QR_CHECKOUT_NOT_RELEASED'}}});});await mount(page,'ItemCheckoutCart',{products:[{...product,checkout_available:false}],language:'en',checkout:true});await fillAddress(page);await expect(page.getByRole('button',{name:'Get final quote',exact:true})).toBeDisabled();await expect(page.getByRole('alert')).toContainText('unavailable for ordering');expect(writes).toBe(0);expect(await page.evaluate(key=>localStorage.getItem(key),key)).not.toBeNull();});

test('missing availability fails closed and both backend blockers are explained',async({page})=>{
 await mount(page,'KitConfigurator',{product:{...product,checkout_available:undefined,checkout_unavailable_reasons:['SINGLE_QR_CHECKOUT_NOT_RELEASED','PAYMENT_INSTRUCTIONS_UNAVAILABLE']},language:'en'},[]);
 await expect(page.getByRole('button',{name:'Order now',exact:true})).toBeDisabled();
 await expect(page.getByRole('status')).toHaveText('Online purchasing has not been enabled, and approved Bank / Raast payment instructions are not available.');
});

test('fractional copies are rejected without saving or rounding',async({page})=>{
 await mount(page,'ItemConfigurator',{product,language:'en'},[]);
 await page.getByLabel('35 mm',{exact:true}).fill('1.5');
 await page.getByRole('button',{name:'Add to cart',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('Enter whole copy counts within the product limit.');
 expect(await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key)).toEqual([]);
});

for(const [code,message] of [['SINGLE_QR_CHECKOUT_NOT_RELEASED','Online purchasing has not been enabled.'],['PAYMENT_INSTRUCTIONS_UNAVAILABLE','Approved Bank / Raast payment instructions are unavailable.'],['AUTH_REQUIRED','Please sign in again.']]){
 test(`quote failure explains ${code} and preserves cart`,async({page})=>{
  await page.route('**/checkout/api',r=>r.fulfill({status:503,json:{error:{code}}}));
  await mount(page,'ItemCheckoutCart',{products:[product],language:'en',checkout:true});await fillAddress(page);
  await page.getByRole('button',{name:'Get final quote',exact:true}).click();
  await expect(page.getByRole('status')).toContainText(message);
  expect(await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key)).toEqual(cart);
 });
}

test('browse-only published product shows order availability instead of an Add to cart button',async({page})=>{await mount(page,'KitConfigurator',{product:{...product,checkout_available:false},language:'en'},[]);await expect(page.getByText('Online ordering is not available yet.')).toBeVisible();await expect(page.getByRole('button',{name:'Order now',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Add to cart',exact:true})).toHaveCount(0);await expect(page.getByRole('link',{name:'Back to Shop'})).toHaveAttribute('href','/shop');});

test("shop configuration keeps QR options readable and validates whole copy counts", async ({ page }) => {
 await page.setViewportSize({width:320,height:844});
 await mount(page,"ItemConfigurator",{product,language:"en",premium:true},[]);
 const fs=require("node:fs");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/shop.css","utf8")});
 await page.evaluate(()=>{document.body.classList.add("customer-portal");document.getElementById("root")!.classList.add("shop-screen");});
 await expect(page.getByLabel("35 mm",{exact:true})).toHaveValue("1");
 await expect(page.getByRole("button",{name:"Decrease copies for 35 mm"})).toBeDisabled();
 await expect(page.locator(".shop-identity input").first()).toHaveCSS("width","20px");
 expect((await page.locator(".shop-identity label > span").first().boundingBox())!.width).toBeGreaterThan(100);
 await page.getByLabel("45 mm",{exact:true}).fill("2");
 await expect(page.locator(".shop-price-summary")).toContainText("PKR 36.90");
 await page.getByLabel("35 mm",{exact:true}).fill("1.5");
 await expect(page.getByRole("button",{name:"Add to Cart",exact:true})).toBeDisabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
