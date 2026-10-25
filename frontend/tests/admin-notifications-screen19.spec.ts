import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const bundle=require('./qa-browser-bundle.cjs');
const {createHarness,id}=require('./notification-fixture.cjs');
async function setup(page:Page,{h=createHarness(),notificationId,admitted=true,retryAdmitted=false,roles=['operations'],delay=0}:{h?:ReturnType<typeof createHarness>;notificationId?:string;admitted?:boolean;retryAdmitted?:boolean;roles?:string[];delay?:number}={}){
  const unexpected:string[]=[],errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  const chunks=path.resolve('.next/static/chunks');
  const compiled=require('./compiled-admin-css.cjs')();
  const css=compiled+'\n'+fs.readFileSync('components/admin-notifications.module.css','utf8').replaceAll('.screen','.notifications-screen');
  await page.route('**/*',async route=>{
    const req=route.request(),u=new URL(req.url());
    if(u.origin==='https://notifications.test'&&u.pathname==='/admin/notifications/api'){
      if(delay)await new Promise(resolve=>setTimeout(resolve,delay));
      const r=await h.dispatch(req.url(),{method:req.method(),headers:{'Content-Type':'application/json',...(req.method()==='POST'?{Origin:'https://notifications.test'}:{})},body:req.postData()??undefined});
      return route.fulfill({status:r.status,headers:Object.fromEntries(r.headers),body:await r.text()});
    }
    if(u.origin==='https://notifications.test'&&req.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{box-sizing:border-box}body{margin:0;font:14px system-ui}main{padding:16px;max-width:1200px;margin:auto}h1{font-size:22px}'+css+'</style></head><body><main><div id="root"></div></main></body></html>'});
    unexpected.push(req.url());await route.abort();
  });
  await page.goto('https://notifications.test/admin/notifications'+(notificationId?'/'+notificationId:''));
  await page.evaluate(props=>Object.assign(window,{qaRole:{authenticatedRoles:props.roles,selectedRole:'authenticated'},qaProps:props}),{notificationId,admitted,retryAdmitted,roles});
  await page.addScriptTag({content:bundle({componentPath:'../components/admin-notifications.tsx',exportName:'AdminNotifications',cssClass:'notifications-screen',hydrate:!admitted})});
  return {h,check:()=>{expect(unexpected).toEqual([]);expect(errors).toEqual([]);for(const c of h.state.calls)expect(new URL(c.url).pathname).toMatch(/^\/api\/v1\/admin\/notification-outbox(?:\/[a-f0-9-]{36}\/retry)?$/);}};
}
test('outbox, status filters, page-local channel, pagination and refresh',async({page})=>{
  const s=await setup(page);await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
  await expect(page.getByText('2 shown on this page; not an outbox total.')).toBeVisible();
  await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('cell',{name:id(3),exact:true})).toBeVisible();
  await page.getByLabel('Channel (this page)',{exact:true}).selectOption('email');await expect(page.getByText('No notifications found',{exact:true})).toBeVisible();
  await page.getByLabel('Channel (this page)',{exact:true}).selectOption('unavailable');await expect(page.getByRole('cell',{name:id(3),exact:true})).toBeVisible();
  await page.getByLabel('Channel (this page)',{exact:true}).selectOption('all');await page.getByRole('button',{name:'Previous',exact:true}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
  await page.getByLabel('Status',{exact:true}).selectOption('dead');await page.getByRole('button',{name:'Apply filters'}).click();await expect(page.getByRole('cell',{name:id(2),exact:true})).toHaveCount(0);
  expect(new URL(s.h.state.calls.at(-1).url).searchParams.get('status')).toBe('dead');
  await page.getByRole('button',{name:'Clear filters'}).click();await expect(page.getByRole('cell',{name:id(2),exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Refresh notifications'}).click();await expect(page.getByRole('button',{name:'Previous',exact:true})).toBeDisabled();
  for(const call of s.h.state.calls)expect(new URL(call.url).searchParams.has('channel')).toBe(false);s.check();
});
test('empty list has no synthetic fallback',async({page})=>{const h=createHarness();h.state.rows=[];const s=await setup(page,{h});await expect(page.getByText('No notifications found',{exact:true})).toBeVisible();await expect(page.locator('tbody tr')).toHaveCount(0);s.check();});
test('loading state',async({page})=>{const s=await setup(page,{delay:1000});await expect(page.getByText('Loading notifications…')).toBeVisible();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();s.check();});
test('detail uses list-by-id, bounded history and disabled retry',async({page})=>{
  const s=await setup(page,{notificationId:id(1)});await expect(page.getByText('Attempt 3 · transient_failure',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Older attempts'}).click();await expect(page.getByText('Attempt 1 · transient_failure',{exact:true})).toBeVisible();
  await expect(page.getByText('Attempt 3 · transient_failure',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Review single-event retry'})).toBeDisabled();
  await expect(page.getByText('Recipients, message content and provider identifiers are not exposed.',{exact:false})).toBeVisible();
  expect(new URL(s.h.state.calls[0].url).searchParams.get('id')).toBe(id(1));
  await page.getByText('Template metadata',{exact:true}).click();await expect(page.getByText('Historical template versions were not recorded.',{exact:false})).toBeVisible();s.check();
});
test('invalid detail ID and filters never call backend',async({page})=>{const s=await setup(page,{notificationId:'DEMO-NTF-001'});await expect(page.getByRole('alert')).toContainText('Notification not found');expect(s.h.state.calls).toHaveLength(0);s.check();});
test('invalid exact filter clears old rows without new request',async({page})=>{const s=await setup(page);await expect(page.locator('tbody tr')).toHaveCount(2);const n=s.h.state.calls.length;await page.getByLabel('Exact notification ID').fill('invalid');await page.getByRole('button',{name:'Apply filters'}).click();await expect(page.getByRole('alert')).toContainText('Invalid filters');await expect(page.locator('tbody tr')).toHaveCount(0);expect(s.h.state.calls).toHaveLength(n);s.check();});
for(const status of [401,403,404,412,422,503])test('redacted backend error '+status,async({page})=>{const h=createHarness();h.state.status=status;const s=await setup(page,{h});await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('body')).not.toContainText('NEVER_RENDER');await expect(page.locator('tbody tr')).toHaveCount(0);s.check();});
test('unexpected sensitive data rejected',async({page})=>{const h=createHarness();h.state.malformed=true;const s=await setup(page,{h});await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('body')).not.toContainText('NEVER_RENDER');s.check();});
for(const role of ['support','finance','superadmin'])test('forbidden role does not load '+role,async({page})=>{const s=await setup(page,{roles:[role]});await expect(page.getByText('Access denied',{exact:true})).toBeVisible();expect(s.h.state.calls).toHaveLength(0);s.check();});
for(const detail of [false,true])test('disabled admission blocks rendering and effect '+detail,async({page})=>{const h=createHarness({admitted:false});const s=await setup(page,{h,notificationId:detail?id(1):undefined,admitted:false});await expect(page.getByText('Live Notifications integration disabled',{exact:true})).toBeVisible();expect(h.state.calls).toHaveLength(0);expect(h.state.authCalls).toBe(0);expect(h.state.staffCalls).toBe(0);expect(await page.evaluate(()=>(window as unknown as {qaHydrationErrors:string[]}).qaHydrationErrors)).toEqual([]);s.check();});
test('missing MFA is denied by relay without upstream call',async({page})=>{const h=createHarness();h.state.mfa=false;const s=await setup(page,{h});await expect(page.getByRole('alert')).toContainText('MFA');expect(h.state.calls).toHaveLength(0);s.check();});
test('controlled retry requires confirmation; queues without delivery claim',async({page})=>{
  const s=await setup(page,{notificationId:id(1),retryAdmitted:true});await page.getByRole('button',{name:'Review single-event retry'}).click();
  const dialog=page.getByRole('dialog');await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();await expect(dialog.getByRole('button',{name:'Queue reviewed retry'})).toBeDisabled();
  await dialog.getByRole('checkbox').check();await dialog.getByRole('button',{name:'Queue reviewed retry'}).click();
  await expect(page.getByText('Retry queued. This receipt does not confirm email delivery.',{exact:true})).toBeVisible();
  expect(s.h.state.calls.filter((c:{options:{method:string}})=>c.options.method==='POST')).toHaveLength(1);s.check();
});
test('stale expected attempt count forces refreshed review',async({page})=>{
  const s=await setup(page,{notificationId:id(1),retryAdmitted:true});await page.getByRole('button',{name:'Review single-event retry'}).click();s.h.state.rows[0].attempt_count=4;
  await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Queue reviewed retry'}).click();await expect(page.getByText('Retry refused: attempt count changed. Review the refreshed notification.')).toBeVisible();
  expect(s.h.state.receipts.size).toBe(0);s.check();
});
test('unknown committed outcome freezes body and reuses key only on explicit reconciliation',async({page})=>{
  const s=await setup(page,{notificationId:id(1),retryAdmitted:true});await page.getByRole('button',{name:'Review single-event retry'}).click();s.h.state.commitThenFailOnce=true;
  await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Queue reviewed retry'}).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('outcome is unknown');await expect(page.getByLabel('Reviewed reason')).toBeDisabled();
  expect(s.h.state.calls.filter((c:{options:{method:string}})=>c.options.method==='POST')).toHaveLength(1);
  await page.getByRole('button',{name:'Reconcile identical request'}).click();await expect(page.getByText('Retry queued. This receipt does not confirm email delivery.',{exact:true})).toBeVisible();
  const calls=s.h.state.calls.filter((c:{options:{method:string}})=>c.options.method==='POST');expect(calls[0].options.body).toEqual(calls[1].options.body);expect(calls[0].options.headers['Idempotency-Key']).toEqual(calls[1].options.headers['Idempotency-Key']);expect(s.h.state.receipts.size).toBe(1);s.check();
});
for(const width of [1366,768,375])test('responsive metadata layout '+width,async({page})=>{
  await page.setViewportSize({width,height:850});const s=await setup(page,{notificationId:id(1)});await expect(page.getByText('Delivery activity',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
  fs.mkdirSync(path.resolve('../tmp/phase10-notifications'),{recursive:true});await page.screenshot({path:path.resolve('../tmp/phase10-notifications/notifications-'+width+'.png'),fullPage:true});s.check();
});
