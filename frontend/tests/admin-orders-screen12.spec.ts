import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import ts from 'typescript';
import { id as parseLiveId } from '../lib/orders-contract';
import { INITIAL_SEED_DATA, type MockOrder } from '../lib/admin-mock-data';
import { canReadDemoOrders, filterDemoOrders, orderAmount } from '../lib/admin-orders';
const bundle = require('./qa-browser-bundle.cjs');
const options = {componentPath:'../components/admin-orders.tsx',exportName:'AdminOrders',cssClass:'orders-screen'};

async function harness(page: Page, orders?: MockOrder[], role = 'operations') {
  const css = fs.readdirSync('.next/static/chunks').filter(file => file.endsWith('.css')).map(file => fs.readFileSync(path.join('.next/static/chunks',file),'utf8')).join('\n') + fs.readFileSync('components/admin-orders.module.css','utf8').replaceAll('.screen','.orders-screen');
  const script = bundle(options);
  await page.route('http://orders-demo.test/**', route => {
    const pathname = new URL(route.request().url()).pathname;
    const orderId = pathname.startsWith('/admin/orders/') ? decodeURIComponent(pathname.slice('/admin/orders/'.length)) : undefined;
    return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:"authenticated",effectiveRole:"'+role+'"};window.qaProps='+JSON.stringify({orderId})+';'+script+'</script></body></html>'});
  });
  await page.addInitScript(({orders}) => {
    if (orders && !sessionStorage.getItem('seeded')) {
      localStorage.setItem('safereturn_demo_db',JSON.stringify({orders}));
      sessionStorage.setItem('seeded','1');
    }
  }, {orders});
  await page.goto('http://orders-demo.test/admin/orders');
}

test('order filters combine, preserve fixtures and roles never derive from preview',()=>{
 const orders = INITIAL_SEED_DATA.orders;
 expect(filterDemoOrders(orders,'9022','all','all').map(o=>o.id)).toEqual(['ORD-9022']);
 expect(filterDemoOrders(orders,' AMINA ','Dispatched','Verified')).toHaveLength(1);
 expect(filterDemoOrders(orders,'amina','Processing','Verified')).toHaveLength(0);
 for(const role of ['operations','finance','support','superadmin']) expect(canReadDemoOrders([role])).toBe(true);
 expect(canReadDemoOrders(['security_admin'])).toBe(false);
 expect(canReadDemoOrders([])).toBe(false);
 expect(orderAmount(29.99)).toBe('29.99 · Currency not specified');
 expect(orderAmount('250.00','PKR')).toBe('PKR 250.00');
 expect(orderAmount(29.99,'USD')).toBe('USD 29.99');
 expect(orderAmount(undefined,'PKR')).toBe('Not available');
});

test('orders browser search, combined filters, clear, navigation, refresh and read-only storage',async({page})=>{
 await harness(page);
 const requests:string[]=[];page.on('request',request=>requests.push(request.url()));
 await expect(page.getByRole('heading',{name:'Orders & Sales',exact:true})).toBeVisible();
 await expect(page.locator('tbody tr')).toHaveCount(3);
 const search=page.getByRole('textbox',{name:'Search orders',exact:true});
 await search.focus();await page.keyboard.press('Tab');
 await expect(page.getByRole('combobox',{name:'Order Status',exact:true})).toBeFocused();
 await search.fill('tArIq');await expect(search).toBeFocused();
 await page.getByRole('combobox',{name:'Order Status',exact:true}).selectOption('Pending Review');
 await page.getByRole('combobox',{name:'Payment Status',exact:true}).selectOption('Under Review');
 await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('combobox',{name:'Payment Status',exact:true}).selectOption('Verified');
 await expect(page.getByText('No matching orders', {exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear Filters'}).click();
 await expect(page.locator('tbody tr')).toHaveCount(3);
 expect(requests).toEqual([]);
 await page.getByRole('link',{name:'View Details for ORD-9022'}).click();
 await expect(page.getByRole('heading',{name:'Order Details',exact:true})).toBeVisible();
 await expect(page.getByText('Kids Backpack Tag (x2)',{exact:true})).toBeVisible();
 await expect(page.getByText('29.00 · Currency not specified',{exact:true})).toBeVisible();
 await expect(page.getByText('Detailed order activity is not available in this mock record.')).toBeVisible();
 await page.reload();await expect(page.getByText('Tariq Mahmood',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
 await page.getByRole('link',{name:'Back to Orders'}).click();
 await expect(page.locator('tbody tr')).toHaveCount(3);
 await page.goto('http://orders-demo.test/admin/orders/does-not-exist');
 await expect(page.getByText('Order not found',{exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Back to Orders'}).first()).toHaveAttribute('href','/admin/orders');
});

test('stored snapshots, explicit currency, actual activity, unknown statuses and shared updates',async({page})=>{
 const orders:MockOrder[]=[{...INITIAL_SEED_DATA.orders[0],currencyCode:'PKR',lineItems:[{id:'snapshot',title:'Purchased title',quantity:2,unitPrice:'100.00',lineTotal:'200.00'}],total:225,subtotal:200,shippingAmount:25,activity:[{id:'evt-demo',type:'Synthetic order note',timestamp:'2026-10-22T08:00:00Z',actor:'Demo Support',description:'Stored event only.'}]}];
 await harness(page,orders);
 await page.getByRole('link',{name:'View Details for ORD-9021'}).click();
 await expect(page.getByText('Purchased title',{exact:true})).toBeVisible();
 await expect(page.getByText('PKR 225.00',{exact:true})).toBeVisible();
 await expect(page.getByText('Stored event only.',{exact:true})).toBeVisible();
 const before=await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'));
 await page.evaluate(()=>{const db=JSON.parse(localStorage.getItem('safereturn_demo_db')!);db.products=[{name:'Current renamed product',price:999}];localStorage.setItem('safereturn_demo_db',JSON.stringify(db));window.dispatchEvent(new Event('storage'));});
 await expect(page.getByText('Purchased title',{exact:true})).toBeVisible();
 await expect(page.getByText('PKR 100.00',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByText('Purchased title',{exact:true})).toBeVisible();
 await page.evaluate(()=>{const db=JSON.parse(localStorage.getItem('safereturn_demo_db')!);db.orders[0].payment='Unrecognized demo state';localStorage.setItem('safereturn_demo_db',JSON.stringify(db));window.dispatchEvent(new Event('storage'));});
 await expect(page.getByText('Unrecognized demo state',{exact:true})).toBeVisible();
 expect(before).toBeTruthy();
});

for (const width of [1366,1440,375]) test('orders responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});
 await harness(page);
 await expect(page.locator('tbody tr')).toHaveCount(3);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/orders-list-'+width+'.png',fullPage:true});
 await page.getByRole('link',{name:'View Details for ORD-9021'}).click();
 await expect(page.getByRole('heading',{name:'Order Details',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/order-details-'+width+'.png',fullPage:true});
});

test('restricted authenticated role cannot gain demo access through role preview',async({page})=>{
 await harness(page,undefined,'security_admin');
 await expect(page.getByText('Access denied',{exact:true})).toBeVisible();
 await expect(page.locator('table')).toHaveCount(0);
});

test('empty records and blocked browser storage are handled',async({page})=>{
 await harness(page,[]);
 await expect(page.getByText('No demo orders',{exact:true})).toBeVisible();
 await page.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('unavailable');};});
 await page.reload();
 await expect(page.getByRole('alert')).toContainText('Browser demo storage could not be read');
 await expect(page.locator('tbody tr')).toHaveCount(3);
});


test('server page composition retains capability guards and separates live from demo routes', async()=>{
 const AdminPage=()=>null,AdminNotice=()=>null,AdminOrders=()=>null,OrdersConsole=()=>null;
 function load(file:string) {
  const result:{exports:any}={exports:{}};
  const compiled=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  vm.runInNewContext(compiled,{exports:result.exports,require:(name:string)=>{
   if(name==='react/jsx-runtime')return require('react/jsx-runtime');
   if(name==='next/link')return ()=>null;
   if(name.includes('admin-page'))return {AdminPage,AdminNotice};
   if(name.includes('components/admin-orders'))return {AdminOrders};
   if(name.includes('orders-console'))return {OrdersConsole};
   if(name.includes('lib/admin-orders'))return {canReadDemoOrders};
   if(name.includes('orders-contract'))return {id:parseLiveId};
   throw Error('Unexpected dependency: '+name);
  }});
  return result.exports.default;
 }
 const list=load('app/admin/orders/page.tsx');
 for(const role of ['operations','finance','support','superadmin','security_admin']) {
  const element=await list({searchParams:Promise.resolve({})});
  expect(element.type).toBe(AdminPage);expect(element.props.capability).toBe('orders.read');
  const content=element.props.children({roles:[role]},false);
  expect(content.type).toBe(role==='security_admin'?AdminNotice:AdminOrders);
 }
 const deniedLive=await list({searchParams:Promise.resolve({view:'live'})});
 expect(deniedLive.props.children({roles:['support']},false).type).toBe(AdminNotice);
 const detail=load('app/admin/orders/[orderId]/page.tsx');
 const mock=await detail({params:Promise.resolve({orderId:'ORD-9021'})});
 expect(mock.props.capability).toBe('orders.read');
 expect(mock.props.children({roles:['operations']},false).type).toBe(AdminOrders);
 const live=await detail({params:Promise.resolve({orderId:'00000000-0000-0000-0000-000000000001'})});
 expect(live.props.children({roles:['operations']},false).type).toBe(OrdersConsole);
 expect(live.props.children({roles:['support']},false).type).toBe(AdminNotice);
});
