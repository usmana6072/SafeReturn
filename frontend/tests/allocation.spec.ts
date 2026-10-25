import {test,expect} from "@playwright/test";
const bundle=require("./qa-browser-bundle.cjs");
const oid="00000000-0000-4000-8000-000000000010",aid="00000000-0000-4000-8000-000000000020";
const pending={state:"reconciliation_pending",reason_code:"stock_shortage",requested_count:2,allocated_count:0};
const allocated={state:"allocated",reason_code:null,requested_count:2,allocated_count:2};
async function mount(page:any,exportName:string,props:any){
 await page.route("https://allocation.test/**",(r:any)=>r.request().resourceType()!=="document"?r.fallback():r.fulfill({contentType:"text/html",body:'<!doctype html><html><head><style>*{box-sizing:border-box}body{margin:0;padding:16px;font:16px sans-serif}label{display:block;margin:8px 0}input,select,textarea{max-width:100%}section{overflow-wrap:anywhere}</style></head><body><div id="root"></div></body></html>'}));
 await page.goto("https://allocation.test/");await page.evaluate((props:any)=>{(window as any).qaProps=props;},props);
 await page.addScriptTag({content:bundle({componentPath:exportName==="FinanceForm"?"../components/payments.tsx":"../components/allocation.tsx",exportName})});
}
test("verified shortage is held whole; authorized retry allocates exact item count",async({page},info)=>{
 let current=pending;const requests:any[]=[];
 await page.route("**/payments/api**",r=>{if(r.request().method()==="GET")return r.fulfill({json:current});requests.push(r.request().postDataJSON());current=allocated as any;return r.fulfill({json:{allocation:allocated,payment_status:"verified",fulfillment_eligible:false}});});
 await mount(page,"AllocationControls",{orderId:oid,ur:false});await expect(page.getByText(/whole order is held for reconciliation/)).toBeVisible();await expect(page.getByRole("button",{name:"Retry allocation",exact:true})).toBeDisabled();await page.getByLabel("Retry allocation for the whole verified order",{exact:true}).check();await page.getByRole("button",{name:"Retry allocation",exact:true}).click();await expect(page.getByText(/One QR is allocated to each item/)).toBeVisible();expect(requests).toHaveLength(1);expect(requests[0].body).toEqual({confirmed:true});expect(requests[0].path).toBe(`/admin/orders/${oid}/qr-allocation/retry`);expect(JSON.stringify(requests)).not.toMatch(/public_token|qr_id|copies|price/);await expect(page.getByRole("button",{name:"Retry allocation",exact:true})).toHaveCount(0);await page.screenshot({path:info.outputPath("allocated-en.png"),fullPage:true});
});
test("uncertain retry keeps key and denied refresh clears privileged data",async({page})=>{
 const requests:any[]=[];let denied=false;
 await page.route("**/payments/api**",r=>{if(r.request().method()==="GET")return r.fulfill({status:denied?403:200,json:denied?{error:{code:"FORBIDDEN",message:"PRIVATE_CANARY"}}:pending});requests.push(r.request().postDataJSON());return r.fulfill({status:requests.length===1?503:200,json:requests.length===1?{error:{code:"UNAVAILABLE",message:"PRIVATE_CANARY"}}:{allocation:pending}});});
 await mount(page,"AllocationControls",{orderId:oid,ur:false});await page.getByLabel("Retry allocation for the whole verified order",{exact:true}).check();await page.getByRole("button",{name:"Retry allocation",exact:true}).click();await expect(page.getByRole("status")).toContainText("Refresh allocation status");await page.getByRole("button",{name:"Retry allocation",exact:true}).click();await expect(page.getByRole("status")).toHaveText("");expect(requests[0].key).toBe(requests[1].key);denied=true;await page.getByRole("button",{name:"Refresh allocation status",exact:true}).click();await expect(page.getByRole("status")).toContainText("unavailable");await expect(page.getByText(/whole order is held/)).toHaveCount(0);expect(await page.locator("body").innerText()).not.toContain("PRIVATE_CANARY");
});
test("finance verification describes shortage separately from verified money",async({page})=>{
 const requests:any[]=[];
 await page.route("**/payments/api**",r=>{requests.push(r.request().postDataJSON());return r.fulfill({json:{state:"verified",allocation:pending,fulfillment_eligible:false}});});
 await mount(page,"FinanceForm",{language:"en"});await page.getByLabel("Attempt ID",{exact:true}).fill(aid);await page.getByLabel("Decision",{exact:true}).selectOption("verify");await page.getByLabel("Bank match reference",{exact:true}).fill("SYNTHETIC-BANK-REFERENCE");await page.getByLabel("Settled amount",{exact:true}).fill("123.00");await page.getByLabel("Reason",{exact:true}).fill("Synthetic independent bank review");await page.getByLabel("I independently verified bank settlement.",{exact:true}).check();await page.getByRole("button",{name:"Record review",exact:true}).click();await expect(page.getByRole("status")).toContainText("Payment verified. The whole order is held for reconciliation");expect(requests[0].body.bank_verified).toBe(true);expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
});
test("Urdu mobile reconciliation never promises partial allocation or automatic refund",async({page},info)=>{
 await page.setViewportSize({width:375,height:900});await mount(page,"AllocationSummary",{value:pending,ur:true});await expect(page.getByText(/پورا آرڈر/)).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath("reconciliation-ur-mobile.png"),fullPage:true});
});
