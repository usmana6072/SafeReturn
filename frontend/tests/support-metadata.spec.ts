import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';import path from 'node:path';
const bundle=require('./qa-browser-bundle.cjs'),{createHarness,id}=require('./support-metadata-fixture.cjs');
async function setup(page:Page,{h=createHarness(),caseId,admitted=true,roles=['support'],delay=0}:{h?:ReturnType<typeof createHarness>;caseId?:string;admitted?:boolean;roles?:string[];delay?:number}={}) {
 const unexpected:string[]=[],errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const css=require('./compiled-admin-css.cjs')()+'\n'+['admin-support-cases','admin-shell'].map(f=>fs.readFileSync(path.resolve('components/'+f+'.module.css'),'utf8').replace(/\.screen/g,'.qa-screen')).join('\n');
 await page.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());
  if(u.origin==='https://support.test'&&u.pathname.startsWith('/admin/support/metadata-api')) {
   if(delay)await new Promise(resolve=>setTimeout(resolve,delay));
   const r=await h.dispatch(req.url(),{method:req.method(),body:req.postData()??undefined});
   return route.fulfill({status:r.status,headers:Object.fromEntries(r.headers),body:await r.text()});
  }
  if(u.origin==='https://support.test'&&req.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><style>'+css+'</style></head><body><div id="root"></div></body></html>'});
  unexpected.push(req.url());await route.abort();
 });
 await page.goto('https://support.test/admin/support'+(caseId?'/'+caseId:''));
 await page.evaluate(({roles,caseId,admitted})=>Object.assign(window,{qaSecurity:{roles,mfa_verified:true,capabilities:['support.manage']},qaProps:{caseId,admitted}}),{roles,caseId,admitted});
 await page.addScriptTag({content:bundle({componentPath:'../components/admin-support-cases.tsx',exportName:'AdminSupportCases',wrapperPath:'../components/admin-shell.tsx',hydrate:!admitted})});
 return {h,check:()=>{expect(errors).toEqual([]);expect(unexpected).toEqual([]);for(const c of h.state.calls){expect(new URL(c.url).pathname).toMatch(/^\/api\/v1\/admin\/support-case-metadata(?:\/[a-f0-9-]{36}(?:\/history)?)?$/);expect(c.options.method).toBe('GET');}}};
}
test('list metadata, pagination, filters and refresh',async({page})=>{
 const s=await setup(page);await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
 await expect(page.getByText(/not the complete case directory/)).toBeVisible();await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('cell',{name:id(3),exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Previous',exact:true}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
 await page.getByLabel('Queue',{exact:true}).selectOption('unassigned');await page.getByRole('button',{name:'Apply filters'}).click();await expect(page.getByRole('cell',{name:id(2),exact:true})).toBeVisible();
 expect(new URL(s.h.state.calls.at(-1).url).searchParams.get('queue')).toBe('unassigned');
 await page.getByLabel('Status',{exact:true}).selectOption('closed');await page.getByRole('button',{name:'Apply filters'}).click();await expect(page.getByText('No cases found',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters'}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Refresh cases'}).click();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Previous',exact:true})).toBeDisabled();s.check();
});
test('details project no content, lazy history preserves revision gaps',async({page})=>{
 const s=await setup(page,{caseId:id(1)});await expect(page.getByText('Case content is unavailable.',{exact:false})).toBeVisible();expect(s.h.state.calls).toHaveLength(1);
 await page.getByRole('button',{name:'Load history'}).click();await expect(page.getByText('updated · Revision 4',{exact:true})).toBeVisible();await expect(page.getByText('updated · Revision 2',{exact:true})).toBeVisible();await expect(page.getByText('updated · Revision 3',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Older history'}).click();await expect(page.getByText('updated · Revision 1',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Older history'})).toBeDisabled();
 for(const name of ['Create Case','Claim Case','Add Internal Note','Change Priority','Change Status','Financial Decision','QR-pair support operations'])await expect(page.getByRole('button',{name,exact:true})).toBeDisabled();s.check();
});
test('unassigned details cannot fetch history',async({page})=>{const s=await setup(page,{caseId:id(2)});await expect(page.getByText('History is available only for cases assigned to you.')).toBeVisible();expect(s.h.state.calls).toHaveLength(1);await expect(page.getByRole('button',{name:'Load history'})).toHaveCount(0);s.check();});
test('loading state',async({page})=>{const s=await setup(page,{delay:1000});await expect(page.getByText('Loading case metadata…')).toBeVisible();await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();s.check();});
test('empty history has no fabricated events',async({page})=>{const h=createHarness();h.state.history=[];const s=await setup(page,{h,caseId:id(1)});await page.getByRole('button',{name:'Load history'}).click();await expect(page.getByText('No recorded history on this page.')).toBeVisible();s.check();});
for(const status of [401,403,404,409,422,503])test('redacted failure '+status,async({page})=>{const h=createHarness();h.state.status=status;const s=await setup(page,{h,caseId:id(1)});await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('NEVER_RENDER')).toHaveCount(0);await expect(page.getByRole('button',{name:'Load history'})).toHaveCount(0);s.check();});
test('missing MFA is denied',async({page})=>{const h=createHarness();h.state.mfa=false;const s=await setup(page,{h});await expect(page.getByRole('alert')).toContainText('MFA');expect(h.state.calls).toHaveLength(0);s.check();});
test('forbidden preview roles do not send requests',async({page})=>{const s=await setup(page,{roles:['finance']});await expect(page.getByText('Access denied',{exact:true})).toBeVisible();expect(s.h.state.calls).toHaveLength(0);s.check();});
for(const detail of [false,true])test('unsupported content rejected '+detail,async({page})=>{const h=createHarness();h.state.malformed=true;const s=await setup(page,{h,caseId:detail?id(1):undefined});await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('NEVER_RENDER')).toHaveCount(0);s.check();});
test('malformed history rejected',async({page})=>{const h=createHarness();const s=await setup(page,{h,caseId:id(1)});await expect(page.getByRole('button',{name:'Load history'})).toBeVisible();h.state.malformed=true;await page.getByRole('button',{name:'Load history'}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('NEVER_RENDER')).toHaveCount(0);s.check();});
test('invalid exact filter fails without a request',async({page})=>{const s=await setup(page);await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();const n=s.h.state.calls.length;await page.getByLabel('Exact case ID').fill('invalid');await page.getByRole('button',{name:'Apply filters'}).click();await expect(page.getByRole('alert')).toContainText('Invalid filters');expect(s.h.state.calls).toHaveLength(n);s.check();});
for(const caseId of [undefined,id(1)])test('disabled gate prevents rendering/effect/prefetch requests '+!!caseId,async({page})=>{const h=createHarness({admitted:false});const s=await setup(page,{h,caseId,admitted:false});await expect(page.getByText('Live Support integration disabled',{exact:true})).toBeVisible();if(caseId)await page.getByRole('link',{name:'Back to Support Cases'}).hover();await page.waitForTimeout(200);expect(h.state.calls).toHaveLength(0);expect(h.state.authCalls).toBe(0);expect(h.state.staffCalls).toBe(0);expect(await page.evaluate(()=>(window as unknown as {qaHydrationErrors:string[]}).qaHydrationErrors)).toEqual([]);s.check();});
test('details link never prefetches',async({page})=>{const s=await setup(page);const link=page.getByRole('link',{name:'View details',exact:true});await expect(link).toBeVisible();const n=s.h.state.calls.length;await link.hover();await page.waitForTimeout(200);expect(s.h.state.calls).toHaveLength(n);s.check();});
for(const [width,height]of [[1366,768],[768,1024],[375,667]])test('responsive read-only layout '+width,async({page})=>{await page.setViewportSize({width,height});const s=await setup(page);await expect(page.getByRole('cell',{name:id(1),exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.getByLabel('Exact case ID').focus();await page.keyboard.press('Tab');await expect(page.getByLabel('Case type',{exact:true})).toBeFocused();await page.screenshot({path:'../test-results/support-metadata/support-'+width+'.png',fullPage:true});s.check();});
