import {test,expect} from "@playwright/test";
import fs from "node:fs";
const bundle=require("./qa-browser-bundle.cjs");
const id=(n:number)=>"00000000-0000-4000-8000-"+String(n).padStart(12,"0");
const order=(n:number,payment="verified",fulfillment="preparing")=>({id:id(n),order_number:"SR-240"+n,order_status:n===4?"cancelled":"placed",payment_status:payment,fulfillment_status:fulfillment,currency_code:"PKR",total_pkr:"1230.00",created_at:"2026-11-01T12:00:00Z"});
const items=[order(1,"under_review","unallocated"),order(2,"verified","dispatched"),order(3,"verified","delivered"),order(4,"refunded","returned")];
async function mount(page:any,component:string,props:any) {
 await page.route("https://orders.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://orders.test/orders");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/customer-orders.css","utf8")});
 await page.evaluate((props:any)=>{(window as any).qaProps=props;},props);
 await page.addScriptTag({content:bundle({componentPath:component==="OrdersList"?"../components/customer-orders.tsx":"../components/customer-order-details.tsx",exportName:component,wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
}
test("order filters distinguish payment from delivery and search references",async({page})=>{
 await mount(page,"OrdersList",{items,next:null,older:false,ur:false});
 await page.getByRole("button",{name:"Shipped",exact:true}).click();await expect(page.locator(".orders-card")).toHaveCount(1);
 await expect(page.locator(".orders-card")).toContainText("SR-2402");
 await page.getByRole("button",{name:"Cancelled",exact:true}).click();await expect(page.locator(".orders-card")).toContainText("Refunded");
 await page.getByRole("button",{name:"Clear Filters",exact:true}).click();await page.getByRole("searchbox").fill("SR-2401");
 await expect(page.locator(".orders-card")).toHaveCount(1);await expect(page.locator(".orders-card")).toContainText("Payment Under Review");
 await expect(page.locator(".orders-card")).not.toContainText("Paid");
});
test("paginated history retains paging and avoids partial-history searches",async({page})=>{
 await mount(page,"OrdersList",{items,next:"opaque-next",older:false,ur:false});
 await expect(page.getByRole("searchbox")).toHaveCount(0);
 await expect(page.getByRole("link",{name:"Older Orders"})).toHaveAttribute("href","/orders?cursor=opaque-next");
 await expect(page.locator(".orders-note")).toContainText("page of your order history");
});
test("full detail presents purchase snapshots, actual prices and independent shipment errors",async({page},info)=>{
 await page.setViewportSize({width:390,height:844});
 const detail={...items[0],payment_status:"verified",fulfillment_status:"allocated",commerce_model:"single_qr",identity_count:1,pair_count:0,print_status:"rendering",
 subtotal_pkr:"1200.00",shipping_pkr:"20.00",tax_pkr:"10.00",discount_pkr:"0.00",items:[],qr_uses:[],
 logical_items:[{id:id(11),product_name_snapshot:"Canvas Bag Tag",qr_type_snapshot:"lost",quantity:3,unit_price_snapshot:"400.00",line_total:"1200.00",sizes:[{id:id(12),variant_name_snapshot:"Large",size_mm_snapshot:"45",copies:3}]}],
 shipping_snapshot:{recipient_name:"Example Buyer",phone:"+923000000000",address:"Example Street",city:"Lahore",province:null,postal_code:null}};
 await mount(page,"CustomerOrderDetails",{id:id(1),summary:null,detail,shipments:null,restricted:false,ur:false});
 await expect(page.getByRole("heading",{name:"Canvas Bag Tag"})).toBeVisible();
 await expect(page.locator(".orders-price-summary")).toContainText("PKR 1230.00");
 await expect(page.locator(".orders-price-summary")).toContainText("PKR 20.00");
 await expect(page.getByText("Shipping information couldn’t be loaded.",{exact:true})).toBeVisible();
 await expect(page.locator(".orders-timeline")).toContainText("Payment Confirmed");
 await expect(page.locator(".orders-timeline")).not.toContainText("Shipped");
 await expect(page.getByRole("link",{name:"View Payment Details"})).toHaveAttribute("href","/checkout?orderId="+id(1));
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath("full-order-details-390.png"),fullPage:true});
});
