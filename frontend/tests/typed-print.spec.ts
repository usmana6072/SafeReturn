import {test,expect} from "@playwright/test";
const bundle=require("./qa-browser-bundle.cjs");
const oid="00000000-0000-4000-8000-000000000010",jid="00000000-0000-4000-8000-000000000020",iid="00000000-0000-4000-8000-000000000030",sid="00000000-0000-4000-8000-000000000040";
async function mount(page:any,component:string,props:any){
 await page.route("https://typed-print.test/**",(r:any)=>r.request().resourceType()!=="document"?r.fallback():r.fulfill({contentType:"text/html",body:'<!doctype html><html><head><style>*{box-sizing:border-box}body{margin:0;padding:16px;font:16px sans-serif}label{display:block;margin:8px 0}input,select,textarea{max-width:100%}</style></head><body><div id="root"></div></body></html>'}));
 await page.goto("https://typed-print.test/");await page.evaluate((props:any)=>{(window as any).qaProps=props;},props);
 await page.addScriptTag({content:bundle({componentPath:"../components/"+component+".tsx",exportName:component==="printing-admin"?"PrintingAdmin":"FulfillmentAdmin"})});
}
test("typed physical QA explicitly inspects items and preserves failed request keys",async({page})=>{
 const requests:any[]=[];let denied=false;
 await page.route("**/admin/print-jobs/api**",r=>{
  if(r.request().method()==="GET")return r.fulfill({json:{id:jid,order_id:oid,job_revision:1,status:"ready",artifacts:[{id:sid,sha256_hex:"a".repeat(64),size_bytes:123,deleted_at:null}],inspection_items:[{id:iid,product_name_snapshot:"Synthetic lost labels",qr_type_snapshot:"lost"}]}});
  requests.push(r.request().postDataJSON());return r.fulfill({status:denied?403:requests.length===1?503:200,json:denied?{error:{code:"PRIVATE_CANARY"}}:{}});
 });
 await mount(page,"printing-admin",{language:"en",initialJobId:jid});
 await expect(page.getByRole("heading",{name:"Print status: ready"})).toBeVisible();
 expect(await page.locator('input[type="checkbox"]:checked').count()).toBe(0);
 await page.getByLabel(/Physically scanned and matched/).check();
 await page.getByLabel("Measured QR size (mm)",{exact:true}).fill("35");await page.getByLabel("Printed copies counted",{exact:true}).fill("7");
 for(const name of ["Every allocated QR identity scanned","Logo and quiet zone checked","English and Urdu labels checked","Cutting and packaging checked","Actual printed dimensions measured","Approve this physical print"])await page.getByLabel(name,{exact:true}).check();
 await page.getByLabel("QA reason",{exact:true}).fill("Synthetic physical inspection");
 await page.getByRole("button",{name:"Record physical QA"}).click();await expect(page.getByRole("status")).toHaveText("Request unavailable.");
 await page.getByRole("button",{name:"Record physical QA"}).click();await expect(page.getByRole("status")).toHaveText("Physical observations recorded.");
 expect(requests[0].key).toBe(requests[1].key);expect(requests[0].body.inspected_item_ids).toEqual([iid]);expect(requests[0].body.observed).toEqual([{tag_type:"lost",symbol_mm:"35",copies:7}]);
 denied=true;await page.getByRole("button",{name:"Record physical QA"}).click();await expect(page.getByRole("heading",{name:"Print status: ready"})).toHaveCount(0);expect(await page.locator("body").innerText()).not.toContain("PRIVATE_CANARY");expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
});
test("typed packing submits item membership and requires packing confirmation",async({page})=>{
 const requests:any[]=[];let shipment:any=null;
 await page.route("**/admin/shipments/api**",r=>{
  if(r.request().method()==="GET")return r.fulfill({json:{items:[{id:oid,order_number:"SYNTHETIC-ORDER",commerce_model:"single_qr",city:"Synthetic",shipping_address_id:sid,pair_units:[],items:[],qr_uses:[],logical_items:[{id:iid,product_name_snapshot:"Synthetic labels",quantity:7,sizes:[{id:jid,size_mm_snapshot:"35",copies:7}]}],shipments:shipment?[shipment]:[]}],next_cursor:null}});
  const input=r.request().postDataJSON();requests.push(input);shipment={id:sid,status:input.body.status??"preparing"};return r.fulfill({json:{status:shipment.status}});
 });
 await mount(page,"fulfillment-admin",{ur:false});await page.getByRole("button",{name:"Load ready orders"}).click();await expect(page.getByText("Distinct identities: 1")).toBeVisible();
 await page.getByLabel("Carrier",{exact:true}).fill("Synthetic carrier");await page.getByLabel("Reason",{exact:true}).fill("Synthetic package preparation");await page.getByRole("button",{name:"Create shipment",exact:true}).click();
 await expect(page.getByRole("combobox",{name:"Next status",exact:true})).toBeVisible();expect(requests[0].body.logical_item_ids).toEqual([iid]);expect(requests[0].body).not.toHaveProperty("pair_ids");
 await page.getByLabel(/I physically checked and packed/).check();await page.getByLabel("Reason",{exact:true}).fill("Synthetic packing inspection");await page.getByRole("button",{name:"Save shipment status"}).click();await expect(page.getByRole("combobox",{name:"Next status",exact:true})).toHaveValue("dispatched");expect(requests[1].body.packing_confirmed).toBe(true);
});
test("Urdu typed QA fits mobile and never preapproves physical checks",async({page},info)=>{
 await page.setViewportSize({width:375,height:900});await page.route("**/admin/print-jobs/api**",r=>r.fulfill({json:{id:jid,order_id:oid,job_revision:1,status:"ready",artifacts:[],inspection_items:[{id:iid,product_name_snapshot:"مصنوعی لیبل",qr_type_snapshot:"lost"}]}}));
 await mount(page,"printing-admin",{language:"ur",initialJobId:jid});await expect(page.locator('input[name="inspected_item_id"]')).toBeVisible();expect(await page.locator('input[type="checkbox"]:checked').count()).toBe(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath("typed-qa-ur-mobile.png"),fullPage:true});
});
