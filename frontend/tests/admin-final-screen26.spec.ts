import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs'; import path from 'node:path';
import { ALL_ADMIN_MODULES, DEMO_ROLES, DEMO_PERMISSIONS } from '../lib/admin-navigation';
import { capabilities, staffRoles } from '../lib/auth/staff-contract';
import { INITIAL_SEED_DATA } from '../lib/admin-mock-data';
const bundle = require('./qa-browser-bundle.cjs');
const screens = [
 ['2','/admin','admin-overview','OverviewDashboard',{}],
 ['3','/admin/products','admin-products-list','ProductsList',{}],
 ['4','/admin/products/new','admin-add-product','AddProductForm',{}],
 ['5','/admin/products/PROD-101','admin-product-details','AdminProductDetails',{productId:'PROD-101'}],
 ['6','/admin/templates','admin-templates-list','PrintTemplatesList',{}],
 ['7','/admin/templates/new','admin-create-template-key','CreatePrintTemplatePage',{}],
 ['8','/admin/templates/TP-WRIST-V2','admin-template-details','AdminTemplateDetails',{keyParam:'TP-WRIST-V2'}],
 ['9','/admin/inventory','admin-inventory','AdminInventoryManagement',{}],
 ['10','/admin/batches','admin-batches','AdminQRBatchesList',{}],
 ['11','/admin/qa','admin-qa','AdminQA',{}],
 ['12','/admin/orders','admin-orders','AdminOrders',{}],
 ['13','/admin/payments','admin-payments','AdminPayments',{}],
 ['14','/admin/print-jobs','admin-print-jobs','AdminPrintJobs',{}],
 ['15b','/admin/ready-to-ship','admin-shipments','AdminShipments',{initialTab:'ready'}],
 ['15','/admin/shipments','admin-shipments','AdminShipments',{}],
 ['16','/admin/users','admin-users','AdminUsers',{}],
 ['17','/admin/users/USR-8821','admin-users','AdminUsers',{userId:'USR-8821'}],
 ['18','/admin/support','admin-support-cases','AdminSupportCases',{}],
 ['19','/admin/notifications','admin-notifications','AdminNotifications',{}],
 ['20','/admin/privacy/exports','admin-privacy-requests','AdminPrivacyRequests',{}],
 ['21','/admin/finance/sheet-sync','admin-finance-sync','AdminFinanceSync',{}],
 ['22','/admin/storage','admin-storage-retention','AdminStorageRetention',{}],
 ['23','/admin/audit','admin-audit-logs','AdminAuditLogs',{}],
 ['24','/admin/staff-permissions','admin-staff-permissions','AdminStaffPermissions',{}],
 ['25','/admin/system','admin-system-monitoring','AdminSystemMonitoring',{}],
] as const;
const cache = new Map<string,string>();
async function setup(page: Page, roles: readonly string[] = staffRoles) {
 const css = fs.readFileSync('components/admin-workspace.module.css','utf8')+'\n'+fs.readdirSync('.next/static/chunks').filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.join('.next/static/chunks',f),'utf8')).join('\n');
 await page.route('http://final-demo.test/**',route=>{
  const url = new URL(route.request().url()); const screen = screens.find(entry=>entry[1]===url.pathname) ?? screens[0];
  const component=screen[2]; if(!cache.has(component))cache.set(component,bundle({componentPath:'../components/'+component+'.tsx',exportName:screen[3],wrapperPath:'../components/admin-shell.tsx',cssClass:'review-screen'}));
  const source = fs.readFileSync('components/'+component+'.tsx','utf8');
  const styles = [...source.matchAll(/\.\/([\w-]+\.module\.css)/g)].map(match=>fs.readFileSync('components/'+match[1],'utf8').replaceAll('.screen','.review-screen')).join('\n');
  return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'\n'+styles+'</style></head><body><div id="root"></div><script>window.qaSecurity='+JSON.stringify({roles,mfa_verified:true,capabilities})+';window.qaProps='+JSON.stringify({...screen[4],relatedCapabilities:capabilities,auditAvailable:true})+';'+cache.get(component)+'</script></body></html>'});
 });
}
for(const [width,height] of [[1366,768],[1440,900],[1920,1080],[768,1024],[390,844],[375,667]])test('full shared shell and 24 content screens at '+width+'x'+height,async({page})=>{
 test.setTimeout(300000);await page.setViewportSize({width,height});const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await setup(page);
 for(const [number,url] of screens){await page.goto('http://final-demo.test'+url);await expect(page.locator('#staff-content').getByRole('heading').first(), 'Screen '+number).toBeVisible();await expect(page.getByRole('combobox',{name:'Demo Role Preview',exact:true})).toBeVisible();expect(await page.locator('header h1').evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeLessThanOrEqual(16);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Screen '+number+' full-page overflow').toBe(true);
 if(width<768){await page.getByRole('button',{name:'Menu',exact:true}).click();await expect(page.getByRole('dialog',{name:'Staff menu',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Collapse sidebar',exact:true})).toHaveCount(0);await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeFocused();}
 if(number==='25')await page.screenshot({path:`test-results/final-shell-${width}.png`,fullPage:true});
 }
 expect(errors).toEqual([]);
});
test('every preview sidebar link resolves with correct highlight and preview cannot grant demo editing',async({page})=>{
 test.setTimeout(300000);await page.setViewportSize({width:1366,height:768});await setup(page,['security_admin']);
 for(const role of DEMO_ROLES){await page.goto('http://final-demo.test/admin');await page.getByRole('combobox',{name:'Demo Role Preview'}).selectOption(role);const nav=page.getByRole('navigation',{name:'Staff navigation'}).first();
  for(const id of DEMO_PERMISSIONS[role].pages){const item=ALL_ADMIN_MODULES.find(entry=>entry.id===id)!;await page.getByRole('combobox',{name:'Demo Role Preview'}).selectOption(role);const link=nav.getByRole('link',{name:item.labelEn,exact:true});await expect(link).toHaveAttribute('href',item.path);await link.click();await expect(page.locator('#staff-content').getByRole('heading').first()).toBeVisible();await expect(page.getByRole('navigation',{name:'Staff navigation'}).first().getByRole('link',{name:item.labelEn,exact:true})).toHaveAttribute('aria-current','page');}
 }
 await page.goto('http://final-demo.test/admin/products');await page.getByRole('combobox',{name:'Demo Role Preview'}).selectOption('Operations');await expect(page.getByRole('link',{name:/Add Product/i})).toHaveCount(0);
});
test('shared reset cancellation, focus trap, persistence and protected non-demo storage',async({page})=>{
 await page.setViewportSize({width:1440,height:900});await setup(page);await page.goto('http://final-demo.test/admin');await page.evaluate(()=>{localStorage.setItem('safereturn_demo_db',JSON.stringify({...((window as any).unused||{}),products:[]}));localStorage.setItem('unrelated-session','preserve');});await page.reload();
 await page.getByRole('button',{name:'Reset Demo Data',exact:true}).first().click();const dialog=page.getByRole('dialog',{name:'Reset Demo Data?',exact:true});await expect(dialog).toBeVisible();await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();await page.keyboard.press('Shift+Tab');await expect(dialog.getByRole('button',{name:'Reset Data',exact:true})).toBeFocused();await page.keyboard.press('Tab');await expect(dialog.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!).products)).toEqual([]);
 await page.getByRole('button',{name:'Reset Demo Data',exact:true}).first().click();await page.getByRole('button',{name:'Reset Data',exact:true}).click();expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!).products.length)).toBe(INITIAL_SEED_DATA.products.length);expect(await page.evaluate(()=>localStorage.getItem('unrelated-session'))).toBe('preserve');await page.reload();expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!).products.length)).toBe(3);
});



test('persisted product data hydrates safely and no preview grants mutations',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await page.route('http://hydrate-demo.test/**',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><div id="root"></div><script>window.qaRole={authenticatedRoles:["security_admin"],effectiveRole:"Operations",selectedRole:"Operations"};'+bundle({componentPath:'../components/admin-products-list.tsx',exportName:'ProductsList',hydrate:true})+'</script></body></html>'}));
 await page.addInitScript(()=>localStorage.setItem('safereturn_demo_db',JSON.stringify({products:[]})));await page.goto('http://hydrate-demo.test');await expect(page.getByRole('heading',{name:'Products',exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Add Product',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Add Product',exact:true})).toBeDisabled();expect(await page.evaluate(()=>(window as any).qaHydrationErrors)).toEqual([]);expect(errors).toEqual([]);
});

test('mock add product validates PKR price and preserves historical order snapshots across navigation',async({page})=>{
 await setup(page);await page.goto('http://final-demo.test/admin/products');await page.getByRole('link',{name:'Add Product',exact:true}).click();await expect(page.getByRole('heading',{name:'Add New Product',exact:true})).toBeVisible();await page.getByRole('button',{name:'Save Draft',exact:true}).click();await expect(page.getByText('Product title is required.',{exact:true})).toBeVisible();await expect(page.getByText('Price is required.',{exact:true})).toBeVisible();
 const snapshots = INITIAL_SEED_DATA.orders;await page.getByLabel('Product Title *',{exact:true}).fill('Screen 26 review product');await page.locator('input[name="price_per_copy"]').fill('17.125');await page.getByRole('button',{name:'Save Draft',exact:true}).click();expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();await page.locator('input[name="price_per_copy"]').fill('17.25');await page.getByRole('button',{name:'Save Draft',exact:true}).click();await expect(page).toHaveURL('http://final-demo.test/admin/products');await expect(page.getByText('Screen 26 review product',{exact:true})).toBeVisible();const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));expect(stored.orders).toEqual(snapshots);expect(stored.products.find((entry:any)=>entry.name==='Screen 26 review product')).toMatchObject({price:17.25,status:'draft'});await page.reload();await expect(page.getByText('Screen 26 review product',{exact:true})).toBeVisible();
});


test('template draft creation persists without materializing revisions or modifying orders',async({page})=>{
 await setup(page);await page.goto('http://final-demo.test/admin/templates/new');await page.getByLabel('Unique key *',{exact:true}).fill('review-screen26-key');await page.getByLabel('Template name *',{exact:true}).fill('Review draft template');await page.getByRole('button',{name:'Save draft key',exact:true}).click();await expect(page).toHaveURL('http://final-demo.test/admin/templates');await expect(page.getByText('review-screen26-key',{exact:true})).toBeVisible();const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('safereturn_demo_db')!));expect(stored.printTemplates.find((entry:any)=>entry.key==='review-screen26-key')).toMatchObject({status:'draft',revision:0,revisions:[]});expect(stored.orders).toEqual(INITIAL_SEED_DATA.orders);await page.reload();await expect(page.getByText('review-screen26-key',{exact:true})).toBeVisible();
});
test('collapsed navigation persists and blocked reset reports an error instead of success',async({page})=>{
 await setup(page);await page.setViewportSize({width:1366,height:768});await page.goto('http://final-demo.test/admin');await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click();await expect(page.getByRole('button',{name:'Expand sidebar',exact:true})).toBeVisible();await page.reload();await expect(page.getByRole('button',{name:'Expand sidebar',exact:true})).toBeVisible();await page.getByRole('button',{name:'Reset Demo Data',exact:true}).click();await page.evaluate(()=>{Storage.prototype.setItem=()=>{throw Error('blocked');};});await page.getByRole('button',{name:'Reset Data',exact:true}).click();await expect(page.getByText('Failed to reset demo data',{exact:true})).toBeVisible();await expect(page.getByText('Demo data reset to initial benchmark state!',{exact:true})).toHaveCount(0);
});
test('all navigation destinations exist and repaired entry routes select existing demos without mounting API consoles',async()=>{
 const vm=require('node:vm'),ts=require('typescript');
 for(const item of ALL_ADMIN_MODULES)expect(fs.existsSync('app'+item.path+'/page.tsx'),item.path).toBe(true);
 async function routeTree(file:string,query:Record<string,string>={},params:Record<string,string>={}){
  const result={exports:{} as any};const refs:Record<string,()=>null>={};const requireMock=(name:string):any=>{if(name==='react/jsx-runtime')return require(name);if(name.includes('inventory-contract'))return {id:(value:string)=>{if(!/^[0-9a-f-]{36}$/.test(value))throw Error();return value;}};return new Proxy({},{get:(_target,key:string)=>refs[key]??(refs[key]=()=>null)});};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText,{exports:result.exports,require:requireMock});const tree=await result.exports.default({searchParams:Promise.resolve(query),params:Promise.resolve(params)});expect(tree.type).toBe(refs.AdminPage);return {tree,refs,content:tree.props.children({roles:['operations'],capabilities},false)};
 }
 for(const [file,component,live] of [['app/admin/products/page.tsx','ProductsList','ProductAdminList'],['app/admin/products/new/page.tsx','AddProductForm','ProductAdminEditor'],['app/admin/inventory/page.tsx','AdminInventoryManagement','InventoryConsole'],['app/admin/batches/page.tsx','AdminQRBatchesList','InventoryConsole']]){
  const demo=await routeTree(file);expect(demo.tree.props.capability).toBeDefined();expect(demo.content.props.children?.type??demo.content.type).toBe(demo.refs[component]);const api=await routeTree(file,{view:'live'});expect(api.content.props.children?.type??api.content.type).toBe(api.refs[live]);
 }
 const detail=await routeTree('app/admin/products/[productId]/page.tsx',{}, {productId:'PROD-101'});expect(detail.content.props.children.type).toBe(detail.refs.AdminProductDetails);
 const batch=await routeTree('app/admin/batches/[batchId]/page.tsx',{}, {batchId:'BATCH-2026-09'});expect(batch.content.type).toBe(batch.refs.AdminQRBatchDetails);
});

