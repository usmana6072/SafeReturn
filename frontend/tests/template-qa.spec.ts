import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';import path from 'node:path';
const bundle=require('./qa-browser-bundle.cjs'),{createHarness,content,tid,rid}=require('./templates-fixture.cjs');
function withDraft(h=createHarness()){h.state.revisions=[{revision_id:rid,template_id:tid,version:1,status:'draft',row_version:1,content:content(),fingerprint_sha256:null,created_at:'2026-10-23T00:00:00Z',published_at:null}];return h;}
async function setup(page:Page,component='list',h=createHarness()){
 const unexpected:string[]=[],errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const css=fs.readdirSync(path.resolve('.next/static/chunks')).filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.resolve('.next/static/chunks',f),'utf8')).join('\n')+'\n'+fs.readFileSync(path.resolve('components/admin-templates.module.css'),'utf8').replace(/\.screen/g,'.qa-screen');
 await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url());if(url.origin==='https://templates.test'&&url.pathname==='/admin/templates/api'){const response=await h.dispatch(req.url(),{method:req.method(),headers:{'Content-Type':'application/json'},body:req.postData()??undefined});return route.fulfill({status:response.status,headers:Object.fromEntries(response.headers),body:Buffer.from(await response.arrayBuffer())});}if(url.origin==='https://templates.test'&&req.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><style>'+css+'</style></head><body><div id="root"></div></body></html>'});unexpected.push(req.method()+' '+req.url());await route.abort();});
 await page.goto('https://templates.test/admin/templates'+(component==='new'?'/new':component==='detail'?'/'+tid:''));
 await page.evaluate(({component,tid})=>Object.assign(window,{qaSecurity:{roles:['operations'],mfa_verified:true,capabilities:['printing.manage']},qaProps:component==='detail'?{keyParam:tid}:{}}),{component,tid});
 await page.addScriptTag({content:bundle({componentPath:'../components/admin-template-qa.tsx',exportName:'TemplateQA',wrapperPath:'../components/admin-shell.tsx'})});

 return {h,check:()=>{expect(unexpected).toEqual([]);expect(errors).toEqual([]);for(const c of h.state.calls)expect(c.path).not.toMatch(/qr-inventory|qr-pairs|qr-batches|qr-allocation|independent-qr|credential|reservation|assignment|export|\/publish/);}};
}

test('pending revision details and unavailable decisions',async({page})=>{
 const h=withDraft();h.state.revisions[0].status='pending_qa';h.state.revisions[0].fingerprint_sha256='a'.repeat(64);
 const s=await setup(page,'list',h);
 await page.getByRole('button',{name:'Synthetic design · Revision 1 · Pending'}).click();
 await expect(page.getByRole('button',{name:'Approve QA',exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:'Reject QA',exact:true})).toBeDisabled();
 await page.getByLabel('Short review note').fill('Manual review draft');
 await expect(page.getByText('Notes cannot be submitted',{exact:false})).toBeVisible();
 expect(h.state.calls.every((c:any)=>c.method==='GET')).toBeTruthy();s.check();
});
test('empty pending queue',async({page})=>{const s=await setup(page);await expect(page.getByText('No revisions pending QA.')).toBeVisible();s.check();});
for(const status of [401,403,503])test('QA backend error '+status,async({page})=>{const h=createHarness();h.state.status=status;const s=await setup(page,'list',h);await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('No revisions pending QA.')).toHaveCount(0);s.check();});
