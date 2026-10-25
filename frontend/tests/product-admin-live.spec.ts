import {test,expect} from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const bundle=require("./qa-browser-bundle.cjs");

const pid="00000000-0000-4000-8000-000000000101",cid="00000000-0000-4000-8000-000000000102";
function product(){return {id:pid,name:"Server sticker",slug:"server-sticker",description:"",category_id:cid,qr_type:"lost",commerce_model:"single_qr",price_per_copy:"12.30",max_order_copies:20,lifecycle_status:"draft",is_featured:false,featured_sort_order:0,catalog_version:1,variants:[] as any[],images:[] as any[]};}
async function open(page:any,options:{ur?:boolean;existing?:boolean;denied?:boolean;list?:boolean}={}){
 const state={product:product(),saved:[] as any[],conflict:false,providerFailure:false,attachFailure:false,uploads:0};
 let css="*{box-sizing:border-box}body{margin:0;padding:16px;width:auto}input,select,textarea{max-width:100%}";
 const dir=path.resolve(".next/static/chunks");if(fs.existsSync(dir))css+=fs.readdirSync(dir).filter(f=>f.endsWith(".css")).map(f=>fs.readFileSync(path.join(dir,f),"utf8")).join("\n");
 await page.route("https://catalog-live.test/**",(r:any)=>r.fulfill({contentType:"text/html",body:`<!doctype html><html dir="${options.ur?"rtl":"ltr"}"><head><style>${css}</style></head><body><div id="root"></div></body></html>`}));
 await page.route("**/admin/catalog-api**",async(r:any)=>{
  const request=r.request();const url=new URL(request.url());
  if(options.denied)return r.fulfill({status:403,json:{error:{code:"FORBIDDEN",message:"PRIVATE_CANARY"}}});
  if(request.method()==="GET"){
   const target=url.searchParams.get("path");
   if(target?.includes("approved-templates"))return r.fulfill({json:{as_of:new Date().toISOString(),items:[]}});
   if(target?.includes("categories"))return r.fulfill({json:[{id:cid,name:"QR Stickers",slug:"qr-stickers",is_active:true}]});
   return r.fulfill({json:target==="/admin/products"?{items:[state.product],next_cursor:null}:state.product});
  }
  const command=request.postDataJSON();state.saved.push(command);
  if(state.conflict)return r.fulfill({status:412,json:{error:{code:"VERSION_MISMATCH",message:"PRIVATE_CANARY"}}});
  if(command.authorize_upload)return r.fulfill({json:{upload_url:"https://api.cloudinary.com/v1_1/synthetic/image/upload",upload_params:{signature:"synthetic-signature"},public_id:"safereturn/catalog/synthetic-photo"}});
  if(command.path.endsWith("/images")){
   if(state.attachFailure){state.attachFailure=false;return r.fulfill({status:503,json:{error:{code:"PROVIDER_UNAVAILABLE"}}});}
   if(command.body.is_primary)state.product.images.forEach(i=>i.is_primary=false);
   state.product.images.push({id:"00000000-0000-4000-8000-000000000301",...command.body,verified_public_url:"https://res.cloudinary.com/synthetic/image/upload/v1/photo.png"});state.product.catalog_version++;return r.fulfill({json:state.product.images.at(-1)});
  }
  if(command.path.endsWith("/variants")){state.product.variants.push({id:"00000000-0000-4000-8000-000000000201",...command.body,catalog_version:1,unit_price:state.product.price_per_copy,currency_code:"PKR"});state.product.catalog_version++;return r.fulfill({json:state.product.variants.at(-1)});}
  if(command.body.lifecycle_status==="published"&&!state.product.images.some(i=>i.is_primary))return r.fulfill({status:422,json:{error:{code:"VERIFIED_PUBLIC_IMAGE_REQUIRED"}}});
  state.product={...state.product,...command.body,catalog_version:state.product.catalog_version+1};return r.fulfill({json:state.product});
 });
 await page.route("https://api.cloudinary.com/**",(r:any)=>{state.uploads++;return r.fulfill({status:state.providerFailure?503:200,headers:{"Access-Control-Allow-Origin":"*"},json:{public_id:"safereturn/catalog/synthetic-photo"}});});
 await page.route("https://res.cloudinary.com/**",(r:any)=>r.fulfill({status:200,contentType:"image/png",body:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDTsAAAAASUVORK5CYII=","base64")}));
 await page.goto("https://catalog-live.test/");
 await page.evaluate((props:any)=>{(window as any).qaProps=props;},{ur:options.ur??false,...(options.existing?{productId:pid}:{})});
 await page.addScriptTag({content:bundle({componentPath:"../components/product-admin-live.tsx",exportName:options.list?"ProductAdminList":"ProductAdminEditor"})});
 return state;
}

test("real editor sends product price and type, reloads server state, and never uses demo storage",async({page},testInfo)=>{
 const state=await open(page);
 await page.getByLabel("Title",{exact:true}).fill("New typed sticker");await page.getByLabel("Slug",{exact:true}).fill("new-typed-sticker");
 await page.getByLabel("QR type",{exact:true}).selectOption("ice");await page.getByLabel("Price per copy (PKR)",{exact:true}).fill("18.75");
 await page.getByLabel("Maximum combined copies across sizes",{exact:true}).fill("15");await page.getByRole("button",{name:"Save product",exact:true}).click();
 await expect(page.getByRole("status").first()).toHaveText("Product saved to the server.");await expect(page).toHaveURL(/admin\/products\/.*edit=true/);
 expect(state.saved[0].body).toMatchObject({qr_type:"ice",price_per_copy:"18.75",max_order_copies:15,lifecycle_status:"draft"});
 await page.getByRole("button",{name:"Reload from server",exact:true}).click();await expect(page.getByLabel("Title",{exact:true})).toHaveValue("New typed sticker");
 expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
 await page.screenshot({path:testInfo.outputPath("editor-en.png"),fullPage:true});
});

test("size price stays on product and stale edits remain visible",async({page})=>{
 const state=await open(page,{existing:true});await expect(page.getByLabel("Title",{exact:true})).toHaveValue("Server sticker");
 await page.getByLabel("SKU",{exact:true}).fill("SIZE-35");await page.getByLabel("Size name",{exact:true}).fill("35 mm");await page.getByRole("button",{name:"Save size",exact:true}).click();
 await expect(page.getByText("35 mm · 35.00 mm · PKR 12.30 per copy")).toBeVisible();
 expect(state.saved[0].body).not.toHaveProperty("unit_price");
 state.conflict=true;await page.getByLabel("Title",{exact:true}).fill("Unsaved title");await page.getByRole("button",{name:"Save product",exact:true}).click();
 await expect(page.getByRole("status").first()).toContainText("entries remain");await expect(page.getByLabel("Title",{exact:true})).toHaveValue("Unsaved title");expect(await page.locator("body").innerText()).not.toContain("PRIVATE_CANARY");
});

test("image verification retry reuses uploaded asset and failed publication is explicit",async({page})=>{
 const state=await open(page,{existing:true});await expect(page.getByLabel("Title",{exact:true})).toHaveValue("Server sticker");
 await page.getByLabel("Status",{exact:true}).selectOption("published");await page.getByRole("button",{name:"Save product",exact:true}).click();await expect(page.getByRole("status").first()).toContainText("image");
 await page.getByLabel("Status",{exact:true}).selectOption("draft");
 await page.getByLabel("Image file",{exact:true}).setInputFiles({name:"photo.png",mimeType:"image/png",buffer:Buffer.from("synthetic-public-image")});await page.getByLabel("Image description",{exact:true}).fill("Public sticker photo");state.attachFailure=true;
 await page.getByRole("button",{name:"Upload and save image",exact:true}).click();await expect(page.getByRole("status").first()).toContainText("unavailable");expect(state.uploads).toBe(1);
 await page.getByRole("button",{name:"Upload and save image",exact:true}).click();await expect(page.getByRole("status").first()).toHaveText("Image verified and saved to the server.");expect(state.uploads).toBe(1);
 const attachments=state.saved.filter(c=>c.path.endsWith("/images")&&!c.authorize_upload);expect(attachments[0].key).toBe(attachments[1].key);
});

test("denied list cannot fall back to demo records; Urdu editor fits mobile",async({page},testInfo)=>{
 await open(page,{denied:true,list:true});await expect(page.getByRole("status")).toContainText("MFA");await expect(page.getByRole("heading",{name:"Server sticker"})).toHaveCount(0);
 await page.unrouteAll();await page.setViewportSize({width:375,height:900});await open(page,{existing:true,ur:true});await expect(page.getByLabel("عنوان",{exact:true})).toHaveValue("Server sticker");expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const heading=await page.getByRole("heading",{level:1}).boundingBox();expect(heading!.x).toBeGreaterThanOrEqual(0);expect(heading!.x+heading!.width).toBeLessThanOrEqual(375);await page.screenshot({path:testInfo.outputPath("editor-ur-mobile.png"),fullPage:true});
});
