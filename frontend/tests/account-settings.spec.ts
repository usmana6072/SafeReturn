import {test,expect} from "@playwright/test";
import fs from "node:fs";
import {accountInitials} from "../lib/account-copy";
const bundle=require("./qa-browser-bundle.cjs"),id="00000000-0000-4000-8000-000000000001";
const account={user_id:id,display_name:"Amina Khan",preferred_locale:"en",email_verified:true,masked_contact:{phone:null},version:"0"};
async function mount(page:any,component="AccountSettings",props:any={}){
 await page.route("https://settings.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://settings.test/account");await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/account-settings.css","utf8")});
 await page.evaluate(({account,props}:any)=>{(window as any).qaProps={account,email:"amina@example.test",initialName:"",ur:false,saved:false,logoutFailed:false,...props,saveAction:async(_:any,form:FormData)=>{(window as any).writes??=[];(window as any).writes.push(Object.fromEntries(form));await new Promise(r=>setTimeout(r,200));return {status:"error",reason:(window as any).stale?"stale":"unavailable"};},languageAction:async(_:any,form:FormData)=>{(window as any).languageWrite=Object.fromEntries(form);return {status:"error",reason:"unavailable"};},logoutAction:async()=>{(window as any).loggedOut=true;}};},{account,props});
 await page.addScriptTag({content:bundle({componentPath:component==="PrivacyExports"?"../components/privacy-exports.tsx":"../components/account-settings.tsx",exportName:component,wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
}
test("account shows real verification and customer-only settings with safe initials",async({page})=>{
 expect(accountInitials("Amina Khan")).toBe("AK");expect(accountInitials("")).toBe("SR");
 await mount(page);await expect(page.getByText("Email Verified",{exact:true})).toBeVisible();
 await expect(page.locator('a[href^="/admin"]')).toHaveCount(0);await expect(page.getByRole("link",{name:"Change Password",exact:false})).toHaveAttribute("href","/auth/forgot-password");
 await expect(page.locator('.settings-card').getByRole("link",{name:"Delivery Addresses",exact:false})).toHaveAttribute("href","/account/shipping-addresses");
 await expect(page.locator(".settings-form")).toHaveCount(0);
});
test("profile validation and failed save retain edits and submit only supported fields",async({page})=>{
 await mount(page);await page.getByRole("button",{name:"Edit Profile",exact:true}).click();await page.getByLabel("Your Name",{exact:true}).fill(" ");
 await page.getByRole("button",{name:"Save Changes",exact:true}).click();await expect(page.getByText("Please enter your name.",{exact:true})).toBeVisible();
 await page.getByLabel("Your Name",{exact:true}).fill("Updated Name");await page.getByRole("button",{name:"Save Changes",exact:true}).dblclick();
 await expect(page.locator(".settings-feedback[role=alert]")).toContainText("couldn’t be saved");await expect(page.getByLabel("Your Name",{exact:true})).toHaveValue("Updated Name");
 const writes=await page.evaluate(()=>(window as any).writes);expect(writes).toHaveLength(1);expect(writes[0]).toEqual({version:"0",display_name:"Updated Name",preferred_locale:"en"});
 await expect(page.locator('input[name=email],input[name=phone]')).toHaveCount(0);
});
test("stale profile blocks blind retries and preserves the draft",async({page})=>{
 await mount(page);await page.evaluate(()=>(window as any).stale=true);await page.getByRole("button",{name:"Edit Profile",exact:true}).click();await page.getByLabel("Your Name",{exact:true}).fill("My draft");
 await page.getByRole("button",{name:"Save Changes",exact:true}).click();await expect(page.getByRole("button",{name:"Refresh Profile"})).toBeVisible();await expect(page.getByRole("button",{name:"Save Changes",exact:true})).toBeDisabled();await expect(page.getByLabel("Your Name")).toHaveValue("My draft");
});
test("language preference submits a locale-only revision and preserves the selected language on error",async({page})=>{
 await mount(page);await page.getByRole("button",{name:/App Language/}).click();await page.getByRole("radio",{name:"اردو",exact:true}).check();await page.getByRole("button",{name:"Save Changes",exact:true}).click();
 await expect(page.locator(".settings-feedback[role=alert]")).toBeVisible();expect(await page.evaluate(()=>(window as any).languageWrite)).toEqual({version:"0",preferred_locale:"ur"});await expect(page.getByRole("radio",{name:"اردو",exact:true})).toBeChecked();
});
test("profile sheet protects unsaved changes on cancel and browser back",async({page})=>{
 await mount(page);await page.getByRole("button",{name:"Edit Profile",exact:true}).click();await page.getByLabel("Your Name").fill("Unsaved");
 await page.getByRole("button",{name:"Cancel",exact:true}).click();await expect(page.getByRole("heading",{name:"Discard Your Changes?"})).toBeVisible();await page.getByRole("button",{name:"Keep Editing"}).click();
 await page.goBack();await expect(page.getByRole("heading",{name:"Discard Your Changes?"})).toBeVisible();await page.getByRole("button",{name:"Discard Changes"}).click();await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("export uses the existing request, status and one-use grant download flow",async({page})=>{
 let stage="requested";const calls:any[]=[];
 await page.route("**/account/privacy/exports/api**",async r=>{
  if(r.request().method()==="GET")return r.fulfill({json:{request_id:id,case_id:id,status:stage,revision:1}});
  const body=r.request().postDataJSON();calls.push({...body,grant:r.request().headers()["x-privacy-grant"]});
  if(body.action==="download")return r.fulfill({contentType:"application/json",body:'{"account":"synthetic"}'});
  return r.fulfill({json:body.action==="request"?{request_id:id}:{grant:"SYNTHETIC-ONE-USE"}});
 });
 await mount(page,"PrivacyExports");await page.getByRole("button",{name:"Check Request Status",exact:true}).click();await expect(page.getByText("Enter a valid request reference.")).toBeVisible();expect(calls).toHaveLength(0);
 await expect(page.getByRole("button",{name:"Request My Data",exact:true})).toBeDisabled();await page.getByRole("checkbox").check();await page.getByRole("button",{name:"Request My Data",exact:true}).click();
 await expect(page.locator(".settings-export-result")).toContainText("Requested");await expect(page.getByRole("button",{name:"Download Reviewed Data"})).toHaveCount(0);
 stage="ready";await page.getByRole("button",{name:"Check Request Status",exact:true}).click();await page.getByRole("checkbox").check();const download=page.waitForEvent("download");await page.getByRole("button",{name:"Download Reviewed Data"}).click();await download;
 expect(calls.map(c=>c.action)).toEqual(["request","download-grants","download"]);expect(calls[0].body).toEqual({scope:"basic_v1",confirmed:true});expect(calls[2].grant).toBe("SYNTHETIC-ONE-USE");
 expect(await page.evaluate(()=>localStorage.length+sessionStorage.length)).toBe(0);expect(page.url()).not.toContain("SYNTHETIC");await expect(page.locator("body")).not.toContainText("SYNTHETIC-ONE-USE");
});

