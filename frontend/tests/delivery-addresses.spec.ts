import {test,expect} from "@playwright/test";
import fs from "node:fs";
import {addressErrors,addressOnly,parseAddressBook} from "../lib/shipping-addresses";
const bundle=require("./qa-browser-bundle.cjs"),id=(n:number)=>"00000000-0000-4000-8000-"+String(n).padStart(12,"0");
const address=(n=1)=>({id:id(n),version:1,is_default:n===1,recipient_name:n===1?"Amina Khan":"Usman Ahmed",phone:"+923001234567",address:"House 24, Street 6\nGarden Town",city:"Lahore",province:"Punjab",postal_code:"00540"});
async function mount(page:any,component="ShippingAddresses"){
 await page.route("https://addresses.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://addresses.test/account/shipping-addresses");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/delivery-addresses.css","utf8")});
 await page.evaluate((component:string)=>{(window as any).qaProps=component==="ShippingAddresses"?{ur:false}:{ur:false,disabled:false,onSelect:(value:any)=>{(window as any).selections??=[];(window as any).selections.push(value);}};},component);
 await page.addScriptTag({content:bundle({componentPath:"../components/shipping-addresses.tsx",exportName:component,wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
}
async function fill(page:any,city="Karachi"){
 for(const [label,value]of [["Full Name","New Customer"],["Phone Number","+447700900123"],["House / Street Address","12 Example Street"],["City",city],["Postal Code","SW1A 0AA"]])await page.getByLabel(label,{exact:false}).fill(value);
}
test("schema validation keeps international phone and postal text without adding fields",()=>{
 const a=address();expect(addressErrors({...a,phone:"+447700900123",postal_code:"SW1A 0AA"},false)).toEqual({});
 expect(addressErrors({...a,phone:"03001234567",city:" "},false)).toMatchObject({city:expect.any(String),phone:expect.any(String)});
 expect(Object.keys(addressOnly(a)).sort()).toEqual(["recipient_name","phone","address","city","province","postal_code"].sort());
 expect(()=>parseAddressBook({book_version:1,items:[a,{...address(2),is_default:true}]})).toThrow();
});
test("create, edit and default preserve IDs and both revisions",async({page})=>{
 let book={book_version:1,items:[address(),address(2)]};const writes:any[]=[];
 await page.route("**/account/shipping-addresses/api",async r=>{
  if(r.request().method()==="GET")return r.fulfill({json:book});
  const data=r.request().postDataJSON();writes.push({method:r.request().method(),data});book.book_version++;
  if(r.request().method()==="POST")book.items.push({...data,id:id(3),version:1});
  else{const target=book.items.find(a=>a.id===data.id)!;Object.assign(target,data.body.address,{version:target.version+1,is_default:data.body.is_default});if(data.body.is_default)book.items.forEach(a=>{if(a.id!==target.id&&a.is_default){a.is_default=false;a.version++;}});}
  return r.fulfill({json:{book_version:book.book_version,item:book.items.at(-1)}});
 });
 await mount(page);await expect(page.locator(".address-card")).toHaveCount(2);await expect(page.locator(".address-form")).toHaveCount(0);
 await page.getByRole("button",{name:"Add New Address",exact:true}).click();await page.getByRole("button",{name:"Save Address",exact:true}).click();
 await expect(page.getByText("Please enter your full name.",{exact:true})).toBeVisible();expect(writes).toHaveLength(0);
 await fill(page);await page.getByRole("button",{name:"Save Address",exact:true}).dblclick();await expect(page.getByRole("dialog")).toHaveCount(0);expect(writes).toHaveLength(1);
 expect(writes[0].data).toMatchObject({expected_book_version:1,phone:"+447700900123",postal_code:"SW1A 0AA",is_default:false});
 expect(writes[0].data).not.toHaveProperty("country");await expect(page.locator(".address-card")).toHaveCount(3);
 const card=page.locator(".address-card").filter({has:page.getByRole("heading",{name:"Usman Ahmed",exact:true})});
 await card.getByRole("button",{name:"Edit Address"}).click();await expect(page.getByLabel("City",{exact:false})).toHaveValue("Lahore");
 await page.getByLabel("City",{exact:false}).fill("Islamabad");await page.getByRole("button",{name:"Save Changes",exact:true}).click();await expect(page.getByRole("dialog")).toHaveCount(0);
 expect(writes[1].data).toMatchObject({id:id(2),body:{expected_version:1,expected_book_version:2,is_default:false}});
 await card.getByRole("button",{name:"Set as Default"}).click();await expect(card.locator(".address-badge")).toHaveText("Default Address");
 expect(writes[2].data).toMatchObject({id:id(2),body:{expected_version:2,expected_book_version:3,is_default:true}});
 expect(book.items.filter(a=>a.is_default)).toHaveLength(1);
});
test("conflict preserves draft and requires explicit review of changed server data",async({page})=>{
 let item=address(),bookVersion=1,writes=0;
 await page.route("**/account/shipping-addresses/api",r=>{
  if(r.request().method()==="GET")return r.fulfill({json:{book_version:bookVersion,items:[item]}});
  writes++;item={...item,city:"Updated Elsewhere",version:2};bookVersion=2;return r.fulfill({status:409,json:{error:{code:"PRIVATE_CANARY"}}});
 });
 await mount(page);await page.getByRole("button",{name:"Edit Address"}).click();await page.getByLabel("City",{exact:false}).fill("My draft city");
 await page.getByRole("button",{name:"Save Changes",exact:true}).click();await expect(page.getByLabel("City",{exact:false})).toHaveValue("My draft city");
 await expect(page.getByRole("button",{name:"Save Changes",exact:true})).toBeDisabled();expect(writes).toBe(1);await expect(page.locator("body")).not.toContainText("PRIVATE_CANARY");
 await page.getByRole("dialog").getByRole("button",{name:"Refresh Addresses",exact:true}).click();await expect(page.getByRole("button",{name:"Load Latest Address"})).toBeVisible();
 await page.getByRole("button",{name:"Load Latest Address"}).click();await page.getByRole("button",{name:"Keep Editing"}).click();await expect(page.getByLabel("City",{exact:false})).toHaveValue("My draft city");
 await page.getByRole("button",{name:"Load Latest Address"}).click();await page.getByRole("button",{name:"Discard Changes"}).click();await expect(page.getByLabel("City",{exact:false})).toHaveValue("Updated Elsewhere");
});
test("delete confirmation cancels safely and default deletion has no automatic replacement",async({page})=>{
 let book={book_version:3,items:[address(),address(2)]};let deleted:any=null;
 await page.route("**/account/shipping-addresses/api",r=>{
  if(r.request().method()==="GET")return r.fulfill({json:book});
  deleted=r.request().postDataJSON();book={book_version:4,items:book.items.filter(a=>a.id!==deleted.id)};return r.fulfill({status:204});
 });
 await mount(page);const button=page.getByRole("button",{name:"Delete address for Amina Khan"});await button.click();await page.getByRole("button",{name:"Keep Address"}).click();await expect(button).toBeFocused();expect(deleted).toBeNull();
 await button.click();await expect(page.getByText("You’ll have no default address until you choose another.")).toBeVisible();await page.getByRole("button",{name:"Delete Address",exact:true}).click();await expect(page.locator(".address-card")).toHaveCount(1);
 expect(deleted).toEqual({id:id(1),expected_version:1,expected_book_version:3});await expect(page.locator(".address-badge")).toHaveCount(0);
});
test("modified sheet protects Cancel, Escape and browser Back",async({page})=>{
 await page.route("**/account/shipping-addresses/api",r=>r.fulfill({json:{book_version:0,items:[]}}));await mount(page);
 await page.getByRole("button",{name:"Add New Address"}).click();await page.getByLabel("Full Name",{exact:false}).fill("Unsaved");
 await page.getByRole("button",{name:"Cancel",exact:true}).click();await expect(page.getByRole("heading",{name:"Discard Your Changes?"})).toBeVisible();await page.getByRole("button",{name:"Keep Editing"}).click();
 await page.keyboard.press("Escape");await expect(page.getByRole("heading",{name:"Discard Your Changes?"})).toBeVisible();await page.getByRole("button",{name:"Keep Editing"}).click();
 await page.goBack();await expect(page.getByRole("heading",{name:"Discard Your Changes?"})).toBeVisible();await page.getByRole("button",{name:"Discard Changes"}).click();await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("checkout refresh preserves unrelated selection and clears a deleted selection",async({page})=>{
 let items=[address(),address(2)],requests=0;
 await page.route("**/account/shipping-addresses/api",r=>{requests++;return r.fulfill({json:{book_version:requests,items}});});
 await mount(page,"SavedAddressSelector");await expect(page.getByLabel("Choose shipping address")).toHaveValue(id(1));
 await page.getByLabel("Choose shipping address").selectOption(id(2));
 items=[{...address(),version:2},address(2)];await page.evaluate(()=>window.dispatchEvent(new Event("focus")));
 await expect.poll(()=>requests).toBe(2);await expect(page.getByLabel("Choose shipping address")).toHaveValue(id(2));
 expect(await page.evaluate(()=>(window as any).selections.length)).toBe(2);
 items=[address()];await page.evaluate(()=>window.dispatchEvent(new Event("focus")));await expect(page.getByLabel("Choose shipping address")).toHaveValue("");
 expect(await page.evaluate(()=>(window as any).selections.at(-1))).toBeNull();
});

