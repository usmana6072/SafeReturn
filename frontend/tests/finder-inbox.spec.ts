import {test,expect} from "@playwright/test";
import fs from "node:fs";
import {findFinderSummary,finderPage} from "../lib/finder-inbox";
const bundle=require("./qa-browser-bundle.cjs");
const id=(n:number)=>"00000000-0000-4000-8000-"+String(n).padStart(12,"0");
const items=[{id:id(1),qr_id:id(11),qr_label:"Canvas Backpack",finder_name:"Ali",tag_type:"lost",status:"new",submitted_at:"2026-11-01T10:00:00Z",notification_status:"sent"},{id:id(2),qr_id:id(12),qr_label:"Family Emergency QR",finder_name:null,tag_type:"ice",status:"viewed",submitted_at:"2026-11-01T09:00:00Z",notification_status:null}];
async function mount(page:any,props:any){
 await page.route("https://finder.test/**",(route:any)=>route.request().resourceType()==="document"?route.fulfill({contentType:"text/html",body:'<!doctype html><html><body><div id="root"></div></body></html>'}):route.fallback());
 await page.goto("https://finder.test/inbox");
 await page.addStyleTag({content:require("./compiled-admin-css.cjs")()+fs.readFileSync("components/customer-portal.css","utf8")+fs.readFileSync("components/finder-inbox.css","utf8")});
 await page.evaluate((props:any)=>{(window as any).qaProps=props;},props);
 await page.addScriptTag({content:bundle({componentPath:"../components/finder-inbox.tsx",exportName:"FinderInbox",wrapperPath:"../components/customer.tsx",wrapperExport:"CustomerShell"})});
}
const props={items,next:null,context:{status:"new",qr_id:id(11)},unread:"1",failed:false,ur:false};
test("inbox search uses disclosed summary names and preserves server filters on details",async({page})=>{
 await mount(page,props);await expect(page.locator(".finder-row.unread")).toHaveCount(1);
 await expect(page.locator(".finder-row").first()).toHaveAttribute("href","/inbox/"+id(1)+"?status=new&qr_id="+id(11));
 await page.getByRole("searchbox").fill("ali");await expect(page.locator(".finder-row")).toHaveCount(1);
 await page.getByRole("button",{name:"Clear search",exact:true}).click();await expect(page.locator(".finder-row")).toHaveCount(2);
 await page.getByRole("searchbox").fill("missing");await expect(page.getByRole("heading",{name:"No Matching Messages"})).toBeVisible();
 await expect(page.getByRole("link",{name:"Read",exact:true})).toHaveAttribute("href","/inbox?status=viewed&qr_id="+id(11));
});
test("pagination never presents local page search as full inbox search",async({page})=>{
 await mount(page,{...props,next:"older",context:{}});await expect(page.getByRole("searchbox")).toHaveCount(0);
 await expect(page.getByRole("link",{name:"Older Messages"})).toHaveAttribute("href","/inbox?cursor=older");
 await expect(page.locator(".finder-note")).toContainText("page of messages");
});
test("empty filtered views and failures remain distinct",async({page})=>{
 await mount(page,{...props,items:[]});await expect(page.getByRole("heading",{name:"No Matching Messages"})).toBeVisible();
 await mount(page,{...props,items:[],context:{}});await expect(page.getByRole("heading",{name:"No Finder Messages Yet"})).toBeVisible();
 await mount(page,{...props,failed:true});await expect(page.getByRole("heading",{name:"Couldn’t Load Messages"})).toBeVisible();await expect(page.getByRole("button",{name:"Retry",exact:true})).toBeVisible();
});

test("older direct-link associations follow owner API cursors and match the exact message",async()=>{
 const calls:string[]=[];
 const target={id:items[1].id,status:"viewed" as const,submitted_at:items[1].submitted_at};
 const match=await findFinderSummary(target,async path=>{
  calls.push(path);const q=new URL(path,"https://owner.test").searchParams;
  expect(q.get("status")).toBe("viewed");expect(q.get("qr_id")).toBeNull();
  return q.has("cursor")?{items:[items[1]],next_cursor:null}:{items:[{...items[0],status:"viewed"}],next_cursor:"opaque-next"};
 });
 expect(match?.qr_id).toBe(items[1].qr_id);expect(calls).toHaveLength(2);
 expect(new URL(calls[1],"https://owner.test").searchParams.get("cursor")).toBe("opaque-next");
});
test("QR lookup stops on deleted records and rejects repeated or invalid cursors",async()=>{
 const target={id:id(99),status:"viewed" as const,submitted_at:items[0].submitted_at};
 let calls=0;
 expect(await findFinderSummary(target,async()=>{calls++;return {items:[items[1]],next_cursor:"older"};})).toBeNull();
 expect(calls).toBe(1);
 const newer={...items[0],status:"viewed",submitted_at:"2026-11-02T10:00:00Z"};
 await expect(findFinderSummary(target,async()=>({items:[newer],next_cursor:"repeated"}))).rejects.toThrow("Unavailable");
 expect(()=>finderPage({items:[],next_cursor:"x".repeat(257)})).toThrow("Unavailable");
});
