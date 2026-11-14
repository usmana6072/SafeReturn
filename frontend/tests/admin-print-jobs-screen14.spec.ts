import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import ts from 'typescript';
import {INITIAL_PRINT_JOBS,loadAdminMockData,resetAdminMockData,recordDemoPrintInspection,demoPrintCopies,demoPrintReviewAvailable} from '../lib/admin-mock-data';
import {canInspectDemoPrintJobs} from '../lib/admin-print-policy';import {id} from '../lib/printing-contract';
const bundle=require('./qa-browser-bundle.cjs');
const options={componentPath:'../components/admin-print-jobs.tsx',exportName:'AdminPrintJobs',cssClass:'print-screen'};
async function open(page:Page,role='operations',preview='authenticated',printJobs?:unknown[]) {
 const css=fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n')+fs.readFileSync('components/admin-print-jobs.module.css','utf8').replaceAll('.screen','.print-screen');
 await page.route('http://print-demo.test/**',route=>{
  const pathname=new URL(route.request().url()).pathname;const jobId=pathname.startsWith('/admin/print-jobs/')?decodeURIComponent(pathname.slice('/admin/print-jobs/'.length)):undefined;
  return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:'+JSON.stringify(preview)+',effectiveRole:'+JSON.stringify(role)+'};window.qaProps='+JSON.stringify({jobId})+';'+bundle(options)+'</script></body></html>'});
 });
 if(printJobs)await page.addInitScript(({printJobs})=>{if(!sessionStorage.getItem('seeded')){localStorage.setItem('safereturn_demo_db',JSON.stringify({printJobs}));sessionStorage.setItem('seeded','1');}},{printJobs});
 await page.goto('http://print-demo.test/admin/print-jobs');
}
const input={jobId:'DEMO-PRINT-002',outcome:'Passed' as const,confirmed:true,authenticatedRoles:['operations'],previewRole:'authenticated'};

test('print mock model validates quantity, authority, prerequisites, history, reset and isolation',()=>{
 resetAdminMockData();const before=loadAdminMockData();
 expect(demoPrintCopies(INITIAL_PRINT_JOBS[1])).toBe(3);expect(demoPrintCopies(INITIAL_PRINT_JOBS[0])).toBeUndefined();
 expect(INITIAL_PRINT_JOBS[1].sampleItem?.id).not.toBe(INITIAL_PRINT_JOBS[2].sampleItem?.id);
 expect(demoPrintCopies({...INITIAL_PRINT_JOBS[1],sampleItem:{...INITIAL_PRINT_JOBS[1].sampleItem!,sizes:[{label:'bad',copies:1.5}]}})).toBeUndefined();
 for(const role of ['finance','support','security_admin'])expect(recordDemoPrintInspection({...input,authenticatedRoles:[role]}).success).toBe(false);
 expect(canInspectDemoPrintJobs(['superadmin'])).toBe(true);
 expect(recordDemoPrintInspection({...input,previewRole:'Superadmin'}).success).toBe(false);
 expect(recordDemoPrintInspection({...input,confirmed:false}).success).toBe(false);
 expect(recordDemoPrintInspection({...input,jobId:'unknown'}).success).toBe(false);
 expect(recordDemoPrintInspection({...input,jobId:'DEMO-PRINT-001'}).success).toBe(false);
 expect(recordDemoPrintInspection({...input,outcome:'Rejected'}).success).toBe(false);
 expect(recordDemoPrintInspection(input).success).toBe(true);expect(recordDemoPrintInspection(input).success).toBe(false);
 const after=loadAdminMockData();expect(after.orders).toEqual(before.orders);expect(after.products).toEqual(before.products);expect(after.qrBatches).toEqual(before.qrBatches);expect(after.qaPairs).toEqual(before.qaPairs);expect(after.qaInspections).toEqual(before.qaInspections);
 expect(after.printJobs[1].status).toBe('ready');expect(after.printJobs[1].qaStatus).toBe('Passed');expect(after.printJobs[1].inspections).toHaveLength(1);
 expect(demoPrintReviewAvailable(after.printJobs[1])).toBe(false);expect(after.auditLogs[0].action).toBe('Mock print QA Passed');
 expect(recordDemoPrintInspection({...input,jobId:'DEMO-PRINT-003',outcome:'Rejected',reason:'Physical damage',note:'Synthetic sample damage'}).success).toBe(true);
 resetAdminMockData();expect(loadAdminMockData().printJobs).toEqual(INITIAL_PRINT_JOBS);
});

test('print browser search, filters, copies, pass confirmation, history, refresh and no network',async({page})=>{
 await open(page);await expect(page.locator('tbody tr')).toHaveCount(3);
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 const search=page.getByRole('textbox',{name:'Search jobs'});await search.fill('ord-9023');await expect(search).toBeFocused();await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('combobox',{name:'Job Status',exact:true}).selectOption('ready');await expect(page.getByText('No matching print jobs',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear Filters'}).click();await search.fill('sample A');await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('combobox',{name:'QA Status',exact:true}).selectOption('Awaiting Review');
 expect(requests).toEqual([]);
 await page.getByRole('link',{name:'View Details for DEMO-PRINT-002'}).click();
 await expect(page.getByText('QR identities required: 1 for this illustrative logical item (DEMO-ITEM-A).',{exact:true})).toBeVisible();
 await expect(page.getByRole('row',{name:'Total copies 3'})).toBeVisible();
 await expect(page.getByText('Production Print File Unavailable',{exact:true})).toBeVisible();
 requests.length=0;
 await page.getByRole('button',{name:'Record Mock QA Pass',exact:true}).click();
 await page.getByRole('button',{name:'Cancel',exact:true}).click();expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
 await expect(page.getByRole('button',{name:'Record Mock QA Pass',exact:true})).toBeFocused();
 await page.getByRole('button',{name:'Record Mock QA Pass',exact:true}).click();await page.getByRole('button',{name:'Confirm Demo Pass'}).click();await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Confirm Demo Pass'}).click();
 await expect(page.getByText('Mock print QA result recorded as Passed.',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Record Mock QA Pass',exact:true})).toBeDisabled();expect(requests).toEqual([]);
 await page.reload();await expect(page.getByText('Reinspection is not available in this demo workflow.',{exact:true})).toBeVisible();
 const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));expect(stored.printJobs[1].inspections).toHaveLength(1);expect(stored.orders.find((o:any)=>o.id==='ORD-9023').status).toBe('Processing');
 await page.getByRole('link',{name:'Back to Print Jobs'}).click();await page.getByRole('combobox',{name:'QA Status',exact:true}).selectOption('Passed');await expect(page.locator('tbody tr')).toHaveCount(1);
});

test('rejection requires reason, preserves history, persists and does not alter QR batch QA',async({page})=>{
 await open(page);await page.getByRole('link',{name:'View Details for DEMO-PRINT-003'}).click();await page.getByRole('button',{name:'Reject Mock Print Job',exact:true}).click();
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Confirm Demo Rejection'}).click();await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('combobox',{name:'Demo rejection reason'}).selectOption('Copy or size mismatch');await page.getByRole('textbox',{name:'Inspection note (optional)'}).fill('Synthetic sample only');
 await page.getByRole('button',{name:'Confirm Demo Rejection'}).click();await expect(page.getByText('Mock print QA result recorded as Rejected.',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByText('Copy or size mismatch',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Record Mock QA Pass',exact:true})).toBeDisabled();
});

for(const width of [1366,1440,375])test('print responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});await open(page);await expect(page.locator('tbody tr')).toHaveCount(3);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/print-jobs-'+width+'.png',fullPage:true});
 await page.getByRole('link',{name:'View Details for DEMO-PRINT-002'}).click();await expect(page.getByRole('heading',{name:'Print Job Details',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/print-details-'+width+'.png',fullPage:true});
 await page.getByRole('button',{name:'Reject Mock Print Job',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();
 expect(await page.getByRole('dialog').evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(width);await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('legacy summary, missing IDs and restricted roles do not gain QA rights',async({page})=>{
 await open(page,'operations','Superadmin');await page.getByRole('link',{name:'View Details for DEMO-PRINT-002'}).click();await expect(page.getByRole('button',{name:'Record Mock QA Pass',exact:true})).toBeDisabled();
 await page.goto('http://print-demo.test/admin/print-jobs/DEMO-PRINT-001');await expect(page.getByText('QR Sticker Set (x2)',{exact:true})).toHaveCount(2);await expect(page.getByRole('button',{name:'Record Mock QA Pass',exact:true})).toBeDisabled();
 await page.goto('http://print-demo.test/admin/print-jobs/unknown');await expect(page.getByText('Print job not found',{exact:true})).toBeVisible();
});

test('storage failure stays visible without success or persisted QA',async({page})=>{
 await open(page);await page.getByRole('link',{name:'View Details for DEMO-PRINT-002'}).click();await page.getByRole('button',{name:'Record Mock QA Pass',exact:true}).click();await page.getByRole('checkbox').check();
 await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error('quota');};});await page.getByRole('button',{name:'Confirm Demo Pass'}).click();await expect(page.getByRole('alert')).toContainText('Unable to save mock print QA');expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
});

test('empty collection and denied Finance context are safe',async({page})=>{
 await open(page,'finance','Operations');await expect(page.getByText('Access denied',{exact:true})).toBeVisible();
});

test('empty collection preserves empty state after refresh',async({page})=>{
 await open(page,'operations','authenticated',[]);await expect(page.getByText('No demo print jobs',{exact:true})).toBeVisible();await page.reload();await expect(page.getByText('No demo print jobs',{exact:true})).toBeVisible();
});

test('print routes preserve real capability guards, old order query and UUID live detail behavior',async()=>{
 const AdminPage=()=>null,AdminNotice=()=>null,AdminPrintJobs=()=>null,PrintConsole=()=>null,PrintingAdmin=()=>null;
 function load(file:string){const result={exports:{} as any};const source=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 vm.runInNewContext(source,{exports:result.exports,require:(name:string)=>{if(name==='react/jsx-runtime')return require(name);if(name==='next/link')return ()=>null;if(name.includes('admin-page'))return {AdminPage,AdminNotice};if(name.includes('admin-print-jobs'))return {AdminPrintJobs};if(name.includes('print-console'))return {PrintConsole};if(name.includes('printing-admin'))return {PrintingAdmin};if(name.includes('admin-print-policy'))return {canInspectDemoPrintJobs};if(name.includes('printing-contract'))return {id};throw Error(name);}});return result.exports.default;}
 const list=load('app/admin/print-jobs/page.tsx');for(const role of ['operations','superadmin','finance','support','security_admin']){const page=await list({searchParams:Promise.resolve({})});expect(page.type).toBe(AdminPage);expect(page.props.capability).toBe('printing.manage');expect(page.props.children({roles:[role]},false).type).toBe(['operations','superadmin'].includes(role)?AdminPrintJobs:AdminNotice);}
 const legacy=await list({searchParams:Promise.resolve({orderId:'00000000-0000-0000-0000-000000000001'})});expect(legacy.props.children({roles:['superadmin']},false).type).toBe(AdminNotice);
 const detail=load('app/admin/print-jobs/[jobId]/page.tsx');const demo=await detail({params:Promise.resolve({jobId:'DEMO-PRINT-002'})});expect(demo.props.children({roles:['operations']},false).type).toBe(AdminPrintJobs);
 const live=await detail({params:Promise.resolve({jobId:'00000000-0000-0000-0000-000000000001'})});expect(live.props.children({roles:['finance']},false).type).toBe(AdminNotice);expect(live.props.children({roles:['operations']},false).props.children[0].type).toBe(PrintConsole);
});
