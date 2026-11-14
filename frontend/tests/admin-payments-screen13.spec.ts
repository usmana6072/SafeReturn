import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import ts from 'typescript';
import { INITIAL_SEED_DATA, loadAdminMockData, resetAdminMockData, recordDemoPaymentFollowUp } from '../lib/admin-mock-data';
import { canReviewDemoPayments } from '../lib/admin-payment-access';
const bundle = require('./qa-browser-bundle.cjs');
const options={componentPath:'../components/admin-payments.tsx',exportName:'AdminPayments',cssClass:'payments-screen'};
async function open(page:Page, role='finance', preview='authenticated', orders?:unknown[]) {
 const css=fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n')+fs.readFileSync('components/admin-payments.module.css','utf8').replaceAll('.screen','.payments-screen')+fs.readFileSync('components/admin-orders.module.css','utf8').replaceAll('.screen','.payments-screen');
 await page.route('http://payments-demo.test/**',route=>route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:'+JSON.stringify(preview)+',effectiveRole:'+JSON.stringify(role)+'};'+bundle(options)+'</script></body></html>'}));
 if(orders) await page.addInitScript(({orders})=>{if(!sessionStorage.getItem('seeded')){localStorage.setItem('safereturn_demo_db',JSON.stringify({orders}));sessionStorage.setItem('seeded','1');}},{orders});
 await page.goto('http://payments-demo.test/admin/payments');
}
const input={orderId:'ORD-9022',note:'Synthetic evidence follow-up',confirmed:true,authenticatedRoles:['finance'],previewRole:'authenticated'};

test('follow-up service enforces permissions, confirmation, duplicates and immutable order/payment states',()=>{
 resetAdminMockData();const before=loadAdminMockData();
 for(const role of ['operations','support','security_admin']) expect(recordDemoPaymentFollowUp({...input,authenticatedRoles:[role]}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,previewRole:'Superadmin'}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,confirmed:false}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,note:' '}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,note:'x'.repeat(501)}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,orderId:'unknown'}).success).toBe(false);
 expect(recordDemoPaymentFollowUp({...input,orderId:'ORD-9021'}).success).toBe(false);
 expect(recordDemoPaymentFollowUp(input).success).toBe(true);
 expect(recordDemoPaymentFollowUp(input).success).toBe(false);
 const after=loadAdminMockData();const order=after.orders.find(o=>o.id===input.orderId)!;
 const {demoPaymentReviews,...unchanged}=order;
 expect(unchanged).toEqual(before.orders.find(o=>o.id===input.orderId));expect(demoPaymentReviews).toHaveLength(1);
 expect(after.products).toEqual(before.products);expect(after.qrBatches).toEqual(before.qrBatches);
 expect(after.auditLogs[0].action).toBe('Demo payment follow-up recorded');
 resetAdminMockData();expect(loadAdminMockData().orders.find(o=>o.id===input.orderId)?.demoPaymentReviews).toBeUndefined();
 expect(canReviewDemoPayments(['superadmin'])).toBe(true);
});

test('payments browser filters, evidence, cancel, confirmed follow-up, refresh, duplicates and no network',async({page})=>{
 await open(page);
 await expect(page.locator('tbody tr')).toHaveCount(3);
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 const search=page.getByRole('textbox',{name:'Search payments'});
 await search.fill('tArIq');await expect(search).toBeFocused();
 await page.keyboard.press('Tab');await expect(page.getByRole('combobox',{name:'Payment Status',exact:true})).toBeFocused();
 await page.getByRole('combobox',{name:'Payment Status',exact:true}).selectOption('Verified');
 await expect(page.getByText('No matching payment records',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear Filters'}).click();
 await search.fill('9022');await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 const panel=page.getByRole('region',{name:'Selected payment details'});
 await expect(panel.getByText('Payment evidence not available in this demo record.',{exact:true})).toBeVisible();
 await expect(panel.getByText('29.00 · Currency not specified',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Approve Settlement — unavailable'})).toBeDisabled();
 await page.getByRole('button',{name:'Record Demo Review Decision',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('textbox',{name:'Review note'}).fill('Cancelled note');
 await page.getByRole('button',{name:'Cancel',exact:true}).click();
 expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
 await expect(page.getByRole('button',{name:'Record Demo Review Decision',exact:true})).toBeFocused();
 await page.getByRole('button',{name:'Record Demo Review Decision',exact:true}).click();
 await page.getByRole('button',{name:'Confirm Demo Follow-up'}).click();await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByRole('textbox',{name:'Review note'}).fill('Synthetic follow-up: evidence unavailable');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Confirm Demo Follow-up'}).click();
 await expect(page.getByText('Demo follow-up recorded. Payment and fulfillment status unchanged.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Record Demo Review Decision',exact:true})).toBeDisabled();
 expect(requests).toEqual([]);
 const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));
 const order=stored.orders.find((o:any)=>o.id==='ORD-9022');
 expect(order.payment).toBe('Under Review');expect(order.status).toBe('Pending Review');expect(order.total).toBe(29);
 expect(order.demoPaymentReviews).toHaveLength(1);
 await page.reload();await expect(page.getByText('Synthetic follow-up: evidence unavailable',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 await expect(page.getByRole('link',{name:'View Order'})).toHaveAttribute('href','/admin/orders/ORD-9022');
});

for(const width of [1366,1440,375])test('payments responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});await open(page);
 await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/payments-'+width+'.png',fullPage:true});
 await page.getByRole('button',{name:'Record Demo Review Decision',exact:true}).click();
 const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
 expect(await dialog.evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(width);
 await page.screenshot({path:'test-results/payment-review-'+width+'.png',fullPage:true});
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
});

test('preview cannot grant review rights and storage failure does not claim success',async({page})=>{
 await open(page,'finance','Superadmin');await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 await expect(page.getByRole('button',{name:'Record Demo Review Decision',exact:true})).toBeDisabled();
 await page.evaluate(()=>{(window as any).qaRole.selectedRole='authenticated';});
 await page.getByRole('button',{name:'View payment details for ORD-9021'}).click();await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 await page.getByRole('button',{name:'Record Demo Review Decision',exact:true}).click();
 await page.getByRole('textbox',{name:'Review note'}).fill('Failure check');await page.getByRole('checkbox').check();
 await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error('quota');};});
 await page.getByRole('button',{name:'Confirm Demo Follow-up'}).click();
 await expect(page.getByRole('alert')).toContainText('Unable to save demo review');
 expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
});

test('restricted authenticated role cannot gain access through preview',async({page})=>{
 await open(page,'support','Superadmin');await expect(page.getByText('Access denied',{exact:true})).toBeVisible();
});

test('no pending payments, unavailable storage and empty lists',async({page})=>{
 await open(page,'finance','authenticated',[]);await expect(page.getByText('No demo payment records',{exact:true})).toBeVisible();
 await page.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('blocked');};});await page.reload();
 await expect(page.getByRole('alert')).toContainText('Browser demo storage could not be read');
 await page.getByRole('button',{name:'View payment details for ORD-9022'}).click();
 await expect(page.getByRole('button',{name:'Record Demo Review Decision',exact:true})).toBeDisabled();
});

test('unknown statuses and missing currency have neutral display without invented history',async({page})=>{
 await open(page,'superadmin','authenticated',[{...INITIAL_SEED_DATA.orders[0],payment:'Unrecognized',currencyCode:'invalid'}]);
 await expect(page.getByRole('region',{name:'Payment records'}).getByText('Unrecognized',{exact:true})).toBeVisible();
 await expect(page.getByText('29.99 · Currency not specified',{exact:true})).toBeVisible();
 await expect(page.getByRole('status')).toContainText('No pending payments');
});

test('payment route keeps real capability guard and finance-only live tools',async()=>{
 const AdminPage=()=>null,AdminNotice=()=>null,AdminPayments=()=>null,OrdersConsole=()=>null;
 const result={exports:{} as any};
 const source=ts.transpileModule(fs.readFileSync('app/admin/payments/page.tsx','utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 vm.runInNewContext(source,{exports:result.exports,require:(name:string)=>{
  if(name==='react/jsx-runtime')return require(name);if(name==='next/link')return ()=>null;
  if(name.includes('admin-page'))return {AdminPage,AdminNotice};if(name.includes('admin-payments'))return {AdminPayments};
  if(name.includes('orders-console'))return {OrdersConsole};if(name.includes('admin-payment-access'))return {canReviewDemoPayments};throw Error(name);
 }});
 for(const role of ['finance','superadmin','operations','support','security_admin']) {
  const page=await result.exports.default({searchParams:Promise.resolve({})});expect(page.type).toBe(AdminPage);expect(page.props.capability).toBe('payments.review');
  expect(page.props.children({roles:[role]},false).type).toBe(['finance','superadmin'].includes(role)?AdminPayments:AdminNotice);
 }
 const live=await result.exports.default({searchParams:Promise.resolve({view:'live'})});expect(live.props.children({roles:['superadmin']},false).type).toBe(AdminNotice);
});
