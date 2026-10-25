import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import ts from 'typescript';
import {INITIAL_SHIPMENTS,INITIAL_SEED_DATA,loadAdminMockData,saveAdminMockData,resetAdminMockData,recordDemoShipmentTracking} from '../lib/admin-mock-data';
import {canManageDemoShipments,demoShipmentTransitions} from '../lib/admin-shipment-policy';
import {demoShipmentReadiness,demoOrderPrintQA} from '../lib/admin-shipment-readiness';
const bundle=require('./qa-browser-bundle.cjs');const options={componentPath:'../components/admin-shipments.tsx',exportName:'AdminShipments',cssClass:'ship-screen'};
async function open(page:Page,role='operations',preview='authenticated',seed?:Record<string,unknown>) {
 const css=fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n')+fs.readFileSync('components/admin-shipments.module.css','utf8').replaceAll('.screen','.ship-screen');
 await page.route('http://ship-demo.test/**',route=>{
  const pathname=new URL(route.request().url()).pathname;const shipmentId=pathname.startsWith('/admin/shipments/')?decodeURIComponent(pathname.slice('/admin/shipments/'.length)):undefined;
  return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="p-4 max-w-7xl mx-auto"><div id="root"></div></main><script>window.qaRole={authenticatedRoles:['+JSON.stringify(role)+'],selectedRole:'+JSON.stringify(preview)+',effectiveRole:'+JSON.stringify(role)+'};window.qaProps='+JSON.stringify({shipmentId,initialTab:pathname.includes('ready-to-ship')?'ready':'shipments'})+';'+bundle(options)+'</script></body></html>'});
 });
 if(seed)await page.addInitScript(({seed})=>{if(!sessionStorage.getItem('seeded')){localStorage.setItem('safereturn_demo_db',JSON.stringify(seed));sessionStorage.setItem('seeded','1');}},{seed});
 await page.goto('http://ship-demo.test/admin/shipments');
}
const input={shipmentId:'DEMO-SHIP-001',expectedStatus:'dispatched',status:'exception',confirmed:true,note:'Synthetic tracking exception',authenticatedRoles:['operations'],previewRole:'authenticated'};

test('tracking service enforces roles, confirmation, transitions, stale state, history, reset and isolation',()=>{
 resetAdminMockData();const before=loadAdminMockData();
 expect(before.shipments.every(s=>before.orders.some(o=>o.id===s.orderId))).toBe(true);
 for(const role of ['finance','support','security_admin'])expect(recordDemoShipmentTracking({...input,authenticatedRoles:[role]}).success).toBe(false);
 expect(canManageDemoShipments(['superadmin'])).toBe(true);
 expect(recordDemoShipmentTracking({...input,previewRole:'Superadmin'}).success).toBe(false);
 expect(recordDemoShipmentTracking({...input,confirmed:false}).success).toBe(false);
 expect(recordDemoShipmentTracking({...input,status:'packed'}).success).toBe(false);
 expect(recordDemoShipmentTracking({...input,note:'x'.repeat(501)}).success).toBe(false);
 expect(recordDemoShipmentTracking({...input,shipmentId:'unknown'}).success).toBe(false);
 expect(recordDemoShipmentTracking(input).success).toBe(true);expect(recordDemoShipmentTracking(input).success).toBe(false);
 const after=loadAdminMockData();expect(after.shipments[0].events).toHaveLength(2);expect(after.shipments[0].events[0]).toEqual(before.shipments[0].events[0]);expect(after.shipments[0].status).toBe('exception');
 for(const key of ['orders','printJobs','products','qrBatches','qaPairs','qaInspections'] as const)expect(after[key]).toEqual(before[key]);
 expect(after.auditLogs[0].action).toBe('Demo tracking update');
 expect(recordDemoShipmentTracking({...input,expectedStatus:'exception',status:'returned'}).success).toBe(true);
 expect(recordDemoShipmentTracking({...input,expectedStatus:'returned',status:'delivered'}).success).toBe(false);
 resetAdminMockData();expect(loadAdminMockData().shipments).toEqual(INITIAL_SHIPMENTS);
 const orphan=loadAdminMockData();orphan.orders=[];saveAdminMockData(orphan);expect(recordDemoShipmentTracking(input).success).toBe(false);resetAdminMockData();
});

test('payment labels and mock print QA never manufacture shipment readiness',()=>{
 for(const order of INITIAL_SEED_DATA.orders)expect(['Unknown','Blocked']).toContain(demoShipmentReadiness(order));
 expect(demoShipmentReadiness({...INITIAL_SEED_DATA.orders[0],payment:'Verified',lineItems:[{id:'sample',title:'Snapshot',quantity:3}]})).toBe('Unknown');
 const passed=INITIAL_SEED_DATA.printJobs.map(job=>({...job,orderId:'ORD-9021',qaStatus:'Passed' as const}));
 expect(demoOrderPrintQA('ORD-9021',passed)).toContain('Not verified');
});

test('tabs, search, status filters, readiness panel, keyboard and no network',async({page})=>{
 await open(page);await expect(page.locator('tbody tr')).toHaveCount(2);
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 const search=page.getByRole('textbox',{name:'Search logistics'});await search.fill('track-001');await expect(search).toBeFocused();await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('combobox',{name:'Shipment Status',exact:true}).selectOption('exception');await expect(page.getByText('No matching shipments',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear Filters'}).click();await search.fill('amina');await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('tab',{name:'Ready to Ship',exact:true}).click();await expect(page.getByRole('tab',{name:'Ready to Ship',exact:true})).toHaveAttribute('aria-selected','true');await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByRole('button',{name:'View Readiness for ORD-9021'}).click();await expect(page.getByRole('region',{name:'Readiness for ORD-9021'})).toContainText('Shipment release authority');
 await expect(page.getByRole('region',{name:'Readiness for ORD-9021'})).toContainText('Not verified');
 await page.getByRole('tab',{name:'Ready to Ship',exact:true}).focus();await page.keyboard.press('ArrowRight');await expect(page.getByRole('tab',{name:'All Shipments',exact:true})).toBeFocused();
 await expect(page.getByRole('textbox',{name:'Search logistics'})).toHaveValue('amina');expect(requests).toEqual([]);expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
});

test('detail navigation, cancel, confirmed synthetic delivery, preserved history, refresh and terminal status',async({page})=>{
 await open(page);await page.getByRole('link',{name:'View Details for DEMO-SHIP-001'}).click();await expect(page.getByRole('heading',{name:'Shipment Details',exact:true})).toBeVisible();
 await expect(page.getByText('Delivery address not available in this demo record.',{exact:true})).toBeVisible();await expect(page.getByText('Medical Wristband (x1)',{exact:true})).toBeVisible();
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 await page.getByRole('button',{name:'Record Demo Tracking Update',exact:true}).click();await page.getByRole('button',{name:'Cancel',exact:true}).click();expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
 await expect(page.getByRole('button',{name:'Record Demo Tracking Update',exact:true})).toBeFocused();await page.getByRole('button',{name:'Record Demo Tracking Update',exact:true}).click();
 await page.getByRole('button',{name:'Confirm Demo Tracking Update'}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('combobox',{name:'Demonstration status'}).selectOption('delivered');await page.getByRole('textbox',{name:'Tracking note (optional)'}).fill('Synthetic delivered scenario only');await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Confirm Demo Tracking Update'}).click();await expect(page.getByText('Demo tracking update recorded. No real delivery or fulfillment action performed.',{exact:true})).toBeVisible();expect(requests).toEqual([]);
 const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));expect(stored.shipments[0].events).toHaveLength(2);expect(stored.orders).toEqual(INITIAL_SEED_DATA.orders);expect(stored.printJobs).toEqual(INITIAL_SEED_DATA.printJobs);
 await page.reload();await expect(page.getByText('Synthetic delivered scenario only',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Record Demo Tracking Update',exact:true})).toBeDisabled();
 await expect(page.getByRole('link',{name:'View Order'})).toHaveAttribute('href','/admin/orders/ORD-9021');
 await page.goto('http://ship-demo.test/admin/shipments/not-found');await expect(page.getByText('Shipment not found',{exact:true})).toBeVisible();
});

for(const width of [1366,1440,375])test('logistics responsive '+width,async({page})=>{
 await page.setViewportSize({width,height:width===1440?900:768});await open(page);await expect(page.locator('tbody tr')).toHaveCount(2);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/shipments-'+width+'.png',fullPage:true});
 await page.getByRole('tab',{name:'Ready to Ship',exact:true}).click();await page.getByRole('button',{name:'View Readiness for ORD-9023'}).click();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/readiness-'+width+'.png',fullPage:true});
 await page.goto('http://ship-demo.test/admin/shipments/DEMO-SHIP-001');await expect(page.getByRole('heading',{name:'Shipment Details',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/shipment-details-'+width+'.png',fullPage:true});
 await page.getByRole('button',{name:'Record Demo Tracking Update',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();expect(await page.getByRole('dialog').evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(width);await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('preview is read-only and stale tracking submissions cannot overwrite changes',async({page})=>{
 await open(page,'operations','Superadmin');await page.goto('http://ship-demo.test/admin/shipments/DEMO-SHIP-001');await expect(page.getByRole('button',{name:'Record Demo Tracking Update',exact:true})).toBeDisabled();
 await page.evaluate(()=>{(window as any).qaRole.selectedRole='authenticated';});await page.getByRole('link',{name:'Back to Shipments'}).click();
 // Navigation rebuilds the preview context, so use a fresh authenticated harness for the write check.
 await page.unrouteAll();await open(page);await page.goto('http://ship-demo.test/admin/shipments/DEMO-SHIP-001');await page.getByRole('button',{name:'Record Demo Tracking Update',exact:true}).click();
 await page.getByRole('combobox',{name:'Demonstration status'}).selectOption('delivered');await page.getByRole('checkbox').check();
 await page.evaluate((seed)=>{localStorage.setItem('safereturn_demo_db',JSON.stringify({...seed,shipments:seed.shipments.map((s:any)=>s.id==='DEMO-SHIP-001'?{...s,status:'exception'}:s)}));window.dispatchEvent(new Event('storage'));},INITIAL_SEED_DATA);
 await page.getByRole('button',{name:'Confirm Demo Tracking Update'}).click();await expect(page.getByRole('alert')).toContainText('Shipment status changed');
});

test('write failure reports an error without recording a tracking event',async({page})=>{
 await open(page);await page.goto('http://ship-demo.test/admin/shipments/DEMO-SHIP-001');await page.getByRole('button',{name:'Record Demo Tracking Update',exact:true}).click();await page.getByRole('combobox',{name:'Demonstration status'}).selectOption('exception');await page.getByRole('checkbox').check();
 await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error('quota');};});await page.getByRole('button',{name:'Confirm Demo Tracking Update'}).click();await expect(page.getByRole('alert')).toContainText('Unable to save demo tracking');expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();
});

test('restricted roles, empty collections and unavailable storage are safe',async({page})=>{
 await open(page,'finance','Superadmin');await expect(page.getByText('Access denied',{exact:true})).toBeVisible();
 await page.unrouteAll();await open(page,'operations','authenticated',{shipments:[],orders:[]});await expect(page.getByText('No demo shipments',{exact:true})).toBeVisible();await page.getByRole('tab',{name:'Ready to Ship',exact:true}).click();await expect(page.getByText('No readiness candidates',{exact:true})).toBeVisible();
 await page.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('unavailable');};});await page.reload();await expect(page.getByRole('alert')).toContainText('Browser demo storage could not be read');
});

test('stored snapshots and unknown states display honestly without catalog-derived quantities',async({page})=>{
 await open(page,'superadmin','authenticated',{orders:[{...INITIAL_SEED_DATA.orders[0],lineItems:[{id:'historical',title:'Historical purchased title',quantity:3}]}],shipments:[{...INITIAL_SHIPMENTS[0],status:'unrecognized',events:[]}]});
 await expect(page.getByRole('region',{name:'Shipments table'}).getByText('Unknown (unrecognized)',{exact:true})).toBeVisible();await page.getByRole('link',{name:'View Details for DEMO-SHIP-001'}).click();await expect(page.getByText('Historical purchased title · Stored quantity: 3',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Record Demo Tracking Update',exact:true})).toBeDisabled();
 await expect(page.getByText('No synthetic tracking events recorded. History is not inferred from the current status.',{exact:true})).toBeVisible();
});

test('real shipment routes keep capability guard, Operations-only live tools and UUID details',async()=>{
 const AdminPage=()=>null,AdminNotice=()=>null,AdminShipments=()=>null,ShipmentDiscovery=()=>null,FulfillmentAdmin=()=>null;
 function load(file:string){const result={exports:{} as any};const source=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;vm.runInNewContext(source,{exports:result.exports,require:(name:string)=>{if(name==='react/jsx-runtime')return require(name);if(name==='next/link')return ()=>null;if(name.includes('admin-page'))return {AdminPage,AdminNotice};if(name.includes('admin-shipments'))return {AdminShipments};if(name.includes('shipment-discovery'))return {ShipmentDiscovery};if(name.includes('fulfillment-admin'))return {FulfillmentAdmin};if(name.includes('admin-shipment-policy'))return {canManageDemoShipments};throw Error(name);}});return result.exports.default;}
 for(const file of ['app/admin/shipments/page.tsx','app/admin/ready-to-ship/page.tsx']){const list=load(file);for(const role of ['operations','superadmin','finance','support','security_admin']){const page=await list({searchParams:Promise.resolve({})});expect(page.type).toBe(AdminPage);expect(page.props.capability).toBe('fulfillment.manage');expect(page.props.children({roles:[role]},false).type).toBe(['operations','superadmin'].includes(role)?AdminShipments:AdminNotice);}const live=await list({searchParams:Promise.resolve({view:'live'})});expect(live.props.children({roles:['superadmin']},false).type).toBe(AdminNotice);}
 const detail=load('app/admin/shipments/[shipmentId]/page.tsx');const demo=await detail({params:Promise.resolve({shipmentId:'DEMO-SHIP-001'})});expect(demo.props.children({roles:['operations']},false).type).toBe(AdminShipments);const live=await detail({params:Promise.resolve({shipmentId:'00000000-0000-0000-0000-000000000001'})});expect(live.props.children({roles:['operations']},false).type).toBe(ShipmentDiscovery);
});
