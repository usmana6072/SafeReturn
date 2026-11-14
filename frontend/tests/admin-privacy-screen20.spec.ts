import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const bundle=require('./qa-browser-bundle.cjs');
const {createHarness,id,cursor}=require('./privacy-metadata-fixture.cjs');
async function setup(page:Page,{h=createHarness(),requestId,admitted=true,roles=['security_admin'],delay=0,search='',ur=false}:{h?:ReturnType<typeof createHarness>;requestId?:string;admitted?:boolean;roles?:string[];delay?:number;search?:string;ur?:boolean}={}){
  const unexpected:string[]=[],errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  const chunks=path.resolve('.next/static/chunks');
  const css=require('./compiled-admin-css.cjs')()+'\n'+fs.readFileSync('components/admin-privacy-requests.module.css','utf8').replaceAll('.screen','.privacy-screen');
  await page.route('**/*',async route=>{
    const req=route.request(),u=new URL(req.url());
    if(u.origin==='https://privacy.test'&&u.pathname==='/admin/privacy/exports/api'){
      if(delay)await new Promise(resolve=>setTimeout(resolve,delay));
      const response=await h.dispatch(req.url(),{method:req.method()});
      return route.fulfill({status:response.status,headers:Object.fromEntries(response.headers),body:await response.text()});
    }
    if(u.origin==='https://privacy.test'&&req.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{box-sizing:border-box}body{margin:0;font:14px system-ui}main{padding:16px;max-width:1200px;margin:auto}'+css+'</style></head><body><main><div id="root"></div></main></body></html>'});
    unexpected.push(req.url());await route.abort();
  });
  await page.goto('https://privacy.test/admin/privacy/exports'+(requestId?'/'+requestId:'')+search);
  await page.evaluate(props=>Object.assign(window,{qaRole:{authenticatedRoles:props.roles,selectedRole:'authenticated'},qaProps:props}),{requestId,admitted,roles,ur});
  await page.addScriptTag({content:bundle({componentPath:'../components/admin-privacy-requests.tsx',exportName:'AdminPrivacyRequests',cssClass:'privacy-screen',hydrate:!admitted})});
  return {h,check:()=>{expect(unexpected).toEqual([]);expect(errors).toEqual([]);for(const call of h.state.calls){expect(new URL(call.url).pathname).toBe('/api/v1/admin/privacy/exports');expect(call.options.method).toBe('GET');}}};
}
test('authorized list, local filters, cursor pagination and refresh',async({page})=>{
  const s=await setup(page);await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();const initial=s.h.state.calls.length;
  await page.getByLabel('Status (this page)',{exact:true}).selectOption('ready');await expect(page.locator('tbody tr')).toHaveCount(1);expect(s.h.state.calls).toHaveLength(initial);
  await page.getByRole('button',{name:'Clear filters'}).click();await page.getByLabel('Request reference (this page)').fill(id(1));await expect(page.locator('tbody tr')).toHaveCount(1);expect(s.h.state.calls).toHaveLength(initial);
  await page.getByRole('button',{name:'Clear filters'}).click();await page.getByRole('button',{name:'Next page'}).click();await expect(page.getByRole('cell',{name:id(3),exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Refresh requests'}).click();await expect(page.getByRole('cell',{name:id(3),exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Previous page'}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
  await page.getByLabel('Page size',{exact:true}).selectOption('50');await page.getByRole('button',{name:'Refresh requests'}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();expect(new URL(s.h.state.calls.at(-1).url).searchParams.get('limit')).toBe('50');
  for(const call of s.h.state.calls){expect(new URL(call.url).searchParams.has('status')).toBe(false);expect(new URL(call.url).searchParams.has('id')).toBe(false);}s.check();
});
test('local empty filter does not claim directory absence',async({page})=>{const s=await setup(page);await expect(page.locator('tbody tr')).toHaveCount(2);await page.getByLabel('Status (this page)',{exact:true}).selectOption('held');await expect(page.getByText('No export requests on this page',{exact:true})).toBeVisible();await expect(page.getByText('Other pages may contain different statuses.',{exact:false})).toBeVisible();s.check();});
test('empty list has no mock fallback',async({page})=>{const h=createHarness();h.state.rows=[];const s=await setup(page,{h});await expect(page.getByText('No export requests on this page',{exact:true})).toBeVisible();await expect(page.locator('tbody tr')).toHaveCount(0);s.check();});
test('loading state',async({page})=>{const s=await setup(page,{delay:1000});await expect(page.getByText('Loading privacy request metadata…')).toBeVisible();await expect(page.locator('tbody tr')).toHaveCount(2);s.check();});
test('details only use authorized list; no action or payload disclosure',async({page})=>{
  const s=await setup(page,{requestId:id(1)});await expect(page.getByText('Authorized request metadata',{exact:true})).toBeVisible();
  await expect(page.getByText('An updated timestamp is not supplied by this API.',{exact:false})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Actions unavailable'})).toBeVisible();
  for(const label of ['Approve','Reject','Escalate','Download','Delete','Add note'])await expect(page.getByRole('button',{name:label,exact:true})).toHaveCount(0);
  await expect(page.locator('body')).not.toContainText('NEVER_RENDER');await expect(page.locator('body')).not.toContainText('999');await expect(page.locator('body')).not.toContainText(id(201));
  expect(s.h.state.calls).toHaveLength(1);expect(new URL(s.h.state.calls[0].url).searchParams.has('id')).toBe(false);s.check();
});
test('details preserve source page cursor',async({page})=>{const s=await setup(page,{requestId:id(3),search:'?cursor='+cursor});await expect(page.getByText('Authorized request metadata',{exact:true})).toBeVisible();expect(new URL(s.h.state.calls[0].url).searchParams.get('cursor')).toBe(cursor);s.check();});
test('missing request is only absent on the loaded authorized page',async({page})=>{const s=await setup(page,{requestId:id(999)});await expect(page.getByText('Request not present on this authorized page',{exact:true})).toBeVisible();await expect(page.getByText('This does not prove the request is absent globally.',{exact:false})).toBeVisible();expect(s.h.state.calls).toHaveLength(1);s.check();});
test('invalid synthetic request ID performs no request',async({page})=>{const s=await setup(page,{requestId:'DEMO-PRIV-001'});await expect(page.getByRole('alert')).toContainText('Invalid request reference');expect(s.h.state.calls).toHaveLength(0);s.check();});
test('unsupported query cannot enable legacy console',async({page})=>{const s=await setup(page,{search:'?view=live'});await expect(page.getByRole('alert')).toContainText('Invalid request reference or page query');expect(s.h.state.calls).toHaveLength(0);s.check();});
for(const status of [401,403,404,412,422,503])test('redacted backend error '+status,async({page})=>{const h=createHarness();h.state.status=status;const s=await setup(page,{h});await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('body')).not.toContainText('NEVER_RENDER');await expect(page.locator('tbody tr')).toHaveCount(0);s.check();});
test('authorization loss clears earlier page rows',async({page})=>{const s=await setup(page);await expect(page.locator('tbody tr')).toHaveCount(2);s.h.state.status=403;await page.getByRole('button',{name:'Refresh requests'}).click();await expect(page.getByRole('alert')).toContainText('Access denied');await expect(page.locator('tbody tr')).toHaveCount(0);s.check();});
test('unexpected private fields fail closed',async({page})=>{const h=createHarness();h.state.malformed=true;const s=await setup(page,{h});await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('body')).not.toContainText('NEVER_RENDER');s.check();});
for(const role of ['operations','support','finance','superadmin'])test('forbidden role '+role,async({page})=>{const s=await setup(page,{roles:[role]});await expect(page.getByText('Access denied',{exact:true})).toBeVisible();expect(s.h.state.calls).toHaveLength(0);s.check();});
test('missing MFA is denied by actual relay without upstream call',async({page})=>{const h=createHarness();h.state.mfa=false;const s=await setup(page,{h});await expect(page.getByRole('alert')).toContainText('MFA');expect(s.h.state.calls).toHaveLength(0);s.check();});
for(const detail of [false,true])test('disabled gate suppresses SSR hydration/effects '+detail,async({page})=>{const h=createHarness({admitted:false});const s=await setup(page,{h,requestId:detail?id(1):undefined,admitted:false,search:'?view=live&enabled=true'});await expect(page.getByText('Live Privacy integration disabled',{exact:true})).toBeVisible();expect(h.state.authCalls).toBe(0);expect(h.state.staffCalls).toBe(0);expect(h.state.calls).toHaveLength(0);expect(await page.evaluate(()=>(window as unknown as {qaHydrationErrors:string[]}).qaHydrationErrors)).toEqual([]);s.check();});
for(const width of [1366,768,375])test('responsive metadata details '+width,async({page})=>{await page.setViewportSize({width,height:850});const s=await setup(page,{requestId:id(1)});await expect(page.getByText('Authorized request metadata',{exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);fs.mkdirSync(path.resolve('../tmp/phase11-privacy'),{recursive:true});await page.screenshot({path:path.resolve('../tmp/phase11-privacy/privacy-'+width+'.png'),fullPage:true});s.check();});
test('RTL layout keeps request references and metadata bounded',async({page})=>{await page.setViewportSize({width:375,height:850});const s=await setup(page,{requestId:id(1),ur:true});await expect(page.locator('.privacy-screen')).toHaveAttribute('dir','rtl');await expect(page.getByText('Authorized request metadata',{exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);s.check();});
