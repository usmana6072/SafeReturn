import { test, expect } from "@playwright/test";
import fs from "node:fs";
const bundle = require("./qa-browser-bundle.cjs");
const id = (n:number) => "00000000-0000-4000-8000-" + String(n).padStart(12,"0");
const key = "safereturn-item-cart-v2", oldKey = "safereturn-cart-v1";
const product = {product_id:id(1),name:"Canvas QR Tag",slug:"canvas",description:null,commerce_model:"single_qr",qr_type:"lost",checkout_available:true,featured:false,catalog_version:1,
 price_per_copy:"12.30",max_order_copies:5,category:{id:id(9),slug:"tags",name:"Tags"},images:[],variants:[{variant_id:id(2),sku:"CANVAS",name:"Small",currency_code:"PKR",unit_price_pkr:"12.30"},{variant_id:id(3),sku:"CANVAS-L",name:"Large",currency_code:"PKR",unit_price_pkr:"12.30"}]};
const items = [{product_id:id(1),identity_group:null,sizes:[{variant_id:id(2),copies:2},{variant_id:id(3),copies:1}]},{product_id:id(1),identity_group:"separate",sizes:[{variant_id:id(2),copies:1}]}];
async function mount(page:any, props:any={catalog:{products:[product],unavailable:false},ur:false}, saved=items, pairs:any[]=[]) {
 await page.route("https://cart.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://cart.test/cart");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/shopping-cart.css","utf8")});
 await page.evaluate(({props,saved,pairs,key,oldKey}:any)=>{(window as any).qaProps=props;localStorage.setItem(key,JSON.stringify(saved));localStorage.setItem(oldKey,JSON.stringify(pairs));},{props,saved,pairs,key,oldKey});
 await page.addScriptTag({content:bundle({componentPath:"../components/shopping-cart.tsx",exportName:"ShoppingCart",wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
 await expect(page.locator(".cart-card")).toHaveCount(saved.length+pairs.length);
}
test("cart edits preserve separate QR batches, enforce combined limits and undo only the removal",async({page})=>{
 await page.setViewportSize({width:320,height:900});await mount(page);
 const first=page.locator(".cart-card").first();
 await expect(page.locator(".cart-total")).toContainText("PKR 49.20");
 await first.getByRole("button",{name:"Increase quantity, Small",exact:true}).click();
 await expect(page.locator(".cart-total")).toContainText("PKR 61.50");
 await first.getByRole("button",{name:"Increase quantity, Small",exact:true}).click();
 await expect(first.getByRole("button",{name:"Increase quantity, Large",exact:true})).toBeDisabled();
 await first.getByRole("button",{name:"Remove Option, Large",exact:true}).click();
 await expect(first.locator(".cart-option")).toHaveCount(1);
 await page.getByRole("button",{name:"Undo",exact:true}).click();await expect(first.locator(".cart-option")).toHaveCount(2);
 const stored=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)!),key);
 expect(stored[1]).toEqual(items[1]);expect(stored[0].sizes[0].copies).toBe(4);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test("failed storage leaves visible quantities and persisted selections intact",async({page})=>{
 await mount(page);await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error("denied")};});
 await page.locator(".cart-card").first().getByRole("button",{name:"Increase quantity, Small",exact:true}).click();
 await expect(page.getByRole("alert")).toContainText("couldn’t be saved");
 await expect(page.locator(".cart-card").first().getByLabel("Small",{exact:true})).toHaveValue("2");
});
test("legacy pairs retain both tag types and use actual product prices",async({page})=>{
 const legacy={...product,commerce_model:"legacy_pair"};
 await mount(page,{catalog:{products:[legacy],unavailable:false},ur:false},[],[{variant_id:id(2),lost:2,ice:1}]);
 await expect(page.locator(".cart-total")).toContainText("PKR 36.90");
 await page.getByRole("button",{name:"Decrease quantity, Small · Emergency",exact:true}).click();
 await expect(page.getByRole("alert")).toContainText("at least one Lost");
 await expect(page.locator(".cart-checkout-dock button")).toBeDisabled();
});
