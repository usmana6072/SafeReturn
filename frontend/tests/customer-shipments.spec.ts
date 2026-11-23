import {test,expect} from "@playwright/test";
import fs from "node:fs";
const bundle=require("./qa-browser-bundle.cjs");
const id=(n:number)=>"00000000-0000-4000-8000-"+String(n).padStart(12,"0");
const shipment=(n:number,status:string)=>({id:id(n),order_id:id(10),order_number:"SR-2026-100",status,carrier:"Example Courier",tracking_reference:n===2?null:"TRACK-"+n,
 created_at:"2026-11-01T10:00:00Z",packed_at:n===1?null:"2026-11-02T10:00:00Z",dispatched_at:status==="preparing"?null:"2026-11-03T10:00:00Z",
 delivered_at:status==="delivered"?"2026-11-04T10:00:00Z":null,currency_code:"PKR",total_pkr:"1200.00",order_items:[{product_name_snapshot:"Canvas Bag Tag",quantity:3}]});
const items=[shipment(1,"preparing"),shipment(2,"dispatched"),shipment(3,"delivered")];
async function mount(page:any,component:string,props:any){
 await page.route("https://customer-shipments.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://customer-shipments.test/shipments");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/customer-shipments.css","utf8")});
 await page.evaluate((props:any)=>{(window as any).qaProps=props;},props);
 await page.addScriptTag({content:bundle({componentPath:"../components/customer-shipments.tsx",exportName:component,wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
}
test("shipment filters use shipment states and missing tracking has no copy action",async({page})=>{
 await mount(page,"ShipmentsList",{items,next:null,ur:false});
 await page.getByRole("button",{name:"Dispatched",exact:true}).click();
 await expect(page.locator(".ship-card")).toHaveCount(1);await expect(page.getByText("Tracking number not available yet.")).toBeVisible();
 await expect(page.getByRole("button",{name:"Copy Tracking Number"})).toHaveCount(0);
 await expect(page.locator('.portal-nav > a[href="/orders"]')).not.toHaveAttribute("aria-current","page");
 await page.getByRole("button",{name:"Delivered",exact:true}).click();await expect(page.locator(".ship-card")).toContainText("Delivered");
});
test("copy preserves the entire reference and reports clipboard failure",async({page})=>{
 const value="LONG-TRACKING-"+ "0123456789".repeat(12);
 await mount(page,"TrackingNumber",{value,ur:false});
 await page.evaluate(()=>Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async(value:string)=>{(window as any).copiedTracking=value;}}}));
 await page.getByRole("button",{name:"Copy Tracking Number"}).click();await expect(page.getByRole("status")).toHaveText("Tracking number copied.");
 expect(await page.evaluate(()=>(window as any).copiedTracking)).toBe(value);
 await page.evaluate(()=>Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async()=>{throw Error("denied");}}}));
 await page.getByRole("button",{name:"Copy Tracking Number"}).click();await expect(page.getByRole("status")).toContainText("Select the tracking number");
});
test("detail timeline uses only recorded milestones and keeps order totals separate",async({page},info)=>{
 await page.setViewportSize({width:390,height:844});
 const data=shipment(2,"dispatched");
 await mount(page,"ShipmentDetails",{shipment:data,summary:data,orderId:id(10),address:null,backHref:"/shipments",ur:false});
 await expect(page.locator(".ship-timeline")).toContainText("Shipment Created");await expect(page.locator(".ship-timeline")).toContainText("Dispatched");
 await expect(page.locator(".ship-timeline")).not.toContainText("Delivery Recorded");
 await expect(page.locator(".ship-order-total")).toContainText("Order Total");await expect(page.locator(".ship-order-total")).toContainText("PKR 1200.00");
 await expect(page.getByRole("link",{name:"Track Shipment",exact:true})).toHaveCount(0);
 await expect(page.getByRole("link",{name:"View Order Details"})).toHaveAttribute("href","/orders/"+id(10));
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath("shipment-details-390.png"),fullPage:true});
});
