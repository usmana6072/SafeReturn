import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const bundle=require('./qa-browser-bundle.cjs');
const {createHarness,id,cat}=require('./products-fixture.cjs');
async function setup(page:Page,component='list',h=createHarness()){
 const unexpected:string[]=[];
 const css=fs.readdirSync(path.resolve('.next/static/chunks')).filter(f=>f.endsWith('.css')).map(f=>fs.readFileSync(path.resolve('.next/static/chunks',f),'utf8')).join('\n');
 await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url());
  if(url.origin==='https://products.test'&&url.pathname==='/admin/catalog-api'){
   const response=await h.dispatch(req.url(),{method:req.method(),headers:{'Content-Type':'application/json'},body:req.postData()??undefined});return route.fulfill({status:response.status,headers:Object.fromEntries(response.headers),body:await response.text()});
  }
  if(url.origin==='https://api.cloudinary.com'&&url.pathname==='/v1_1/synthetic/image/upload')return route.fulfill({status:200,contentType:'application/json',body:'{}'});
  if(url.origin==='https://res.cloudinary.com')return route.fulfill({status:200,contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jcdkAAAAASUVORK5CYII=','base64')});
  if(url.origin==='https://products.test'&&req.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><style>'+css+'</style></head><body><div id="root"></div></body></html>'});
  unexpected.push(req.method()+' '+req.url());return route.abort();
 });
 await page.goto('https://products.test/admin/products'+(component==='new'?'/new':component==='detail'?'/'+id:''));
 await page.evaluate(({component,id})=>{Object.assign(window,{qaSecurity:{roles:['operations'],mfa_verified:true,capabilities:['catalog.manage']},qaProps:component==='detail'?{productId:id,initialEdit:true}:{},qaRole:{authenticatedRoles:['operations'],effectiveRole:'operations',selectedRole:'operations'}});}, {component,id});
 await page.addScriptTag({content:bundle({componentPath:component==='list'?'../components/admin-products-list.tsx':component==='new'?'../components/admin-add-product.tsx':'../components/admin-product-details.tsx',exportName:component==='list'?'ProductsList':component==='new'?'AddProductForm':'AdminProductDetails',wrapperPath:'../components/admin-shell.tsx'})});
 return {h,unexpected,check:()=>expect(unexpected).toEqual([])};
}
test('list uses backend data, cursor paging, refresh and real UUID links',async({page})=>{
 const s=await setup(page);await expect(page.getByText('SafeReturn Sticker',{exact:true})).toBeVisible();await expect(page.getByText('PKR 12.50',{exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'View details'})).toHaveAttribute('href','/admin/products/'+id);
 await page.getByRole('button',{name:'Next page'}).click();await expect(page.getByText('No products on this page',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Previous page'}).click();await expect(page.getByText('SafeReturn Sticker',{exact:true})).toBeVisible();s.h.state.product.name='Fresh product';await page.getByRole('button',{name:'Refresh products'}).click();await expect(page.getByText('Fresh product',{exact:true})).toBeVisible();s.check();
});
test('draft create validates input, submits once and navigates to backend ID',async({page})=>{
 const s=await setup(page,'new');await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Create draft',exact:true}).click();expect(s.h.state.calls.filter((c:any)=>c.method==='POST')).toHaveLength(0);
 await page.getByLabel('Product name',{exact:true}).fill('Created product');await page.getByLabel('Slug',{exact:true}).fill('created-product');await page.getByLabel('Price per copy (PKR)',{exact:true}).fill('17.25');await page.getByLabel('Category',{exact:true}).selectOption(cat);
 s.h.state.delay=150;await page.getByRole('button',{name:'Create draft',exact:true}).evaluate(button=>{const form=button.closest('form')!;form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));});await expect(page).toHaveURL('https://products.test/admin/products/'+id+'?edit=true');expect(s.h.state.product.name).toBe('Created product');expect(s.h.state.calls.filter((c:any)=>c.method==='POST')).toHaveLength(1);s.check();
});
test('edit preserves input on conflict and merges untouched fresh fields',async({page})=>{
 const s=await setup(page,'detail');await expect(page.getByLabel('Product name',{exact:true})).toHaveValue('SafeReturn Sticker');s.h.state.conflict=true;await page.getByLabel('Product name',{exact:true}).fill('My retained name');await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Your input is preserved');await expect(page.getByLabel('Product name',{exact:true})).toHaveValue('My retained name');await expect(page.getByRole('button',{name:'Save changes',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Load latest version (keep edits)'}).click();await expect(page.getByLabel('Description',{exact:true})).toHaveValue('Changed by another admin');await expect(page.getByLabel('Product name',{exact:true})).toHaveValue('My retained name');await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByText('Product saved by the server.',{exact:true})).toBeVisible();expect(s.h.state.product.name).toBe('My retained name');expect(s.h.state.product.description).toBe('Changed by another admin');expect(await page.evaluate(()=>localStorage.getItem('safereturn_demo_db'))).toBeNull();s.check();
});
test('category create and edit are real commands, not fixture persistence',async({page})=>{
 const s=await setup(page,'detail');await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();await page.getByText('Manage categories',{exact:true}).click();await page.getByLabel('Category name',{exact:true}).fill('Accessories');await page.getByLabel('Category slug',{exact:true}).fill('accessories');await page.getByRole('button',{name:'Create category',exact:true}).click();await expect(page.getByText('Category saved by the server.',{exact:true})).toBeVisible();await page.getByLabel('Category name',{exact:true}).fill('Updated accessories');await page.getByRole('button',{name:'Save category',exact:true}).click();await expect(page.getByRole('option',{name:'Updated accessories',exact:true}).first()).toHaveCount(1);expect(s.h.state.categories.some((c:any)=>c.name==='Updated accessories')).toBeTruthy();s.check();
});
test('variants preserve attributes and use product pricing without a size-price field',async({page})=>{
 const s=await setup(page,'detail');await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Add variant'}).click();await page.getByLabel('Variant name',{exact:true}).fill('Large sticker');await page.getByLabel('SKU',{exact:true}).fill('LARGE-1');await page.getByLabel('Approved template reference',{exact:true}).selectOption('approved-template@1');await page.getByRole('button',{name:'Save variant'}).click();await expect(page.getByText('Size saved by the server.',{exact:true})).toBeVisible();expect(s.h.state.product.variants[0].unit_price).toBe('12.50');await page.getByRole('button',{name:'Edit size',exact:true}).click();await page.getByLabel('Color',{exact:true}).fill('Blue');await page.getByRole('button',{name:'Save variant'}).click();await expect(page.getByText('vinyl / Blue',{exact:true})).toBeVisible();expect(s.h.state.product.variants[0].sku).toBe('LARGE-1');expect(s.h.state.product.variants[0].template_key).toBe('approved-template');s.check();
});
test('public image authorization, upload, verified attach, metadata and unlink',async({page})=>{
 const s=await setup(page,'detail');await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();await page.getByLabel('Public raster file',{exact:true}).setInputFiles({name:'public.png',mimeType:'image/png',buffer:Buffer.from('synthetic-public-raster')});await page.getByLabel('New image description',{exact:true}).fill('Sticker artwork');await page.getByRole('button',{name:'Upload and attach image'}).click();await expect(page.getByText('Product image verified and attached by the server.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Edit image metadata'}).click();await page.getByLabel('Image alt text',{exact:true}).fill('Updated artwork');await page.getByLabel('Image sort order',{exact:true}).fill('2');await page.getByRole('button',{name:'Save image metadata'}).click();await expect(page.getByText('Updated artwork',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Edit image metadata'}).click();page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Remove image',exact:true}).click();await expect(page.getByText('Image link removed by the server.',{exact:true})).toBeVisible();expect(s.h.state.product.images).toHaveLength(0);s.check();
});
for(const status of [401,403,404,503])test('backend '+status+' stays visible without demo fallback',async({page})=>{
 const h=createHarness();h.state.status=status;const s=await setup(page,'list',h);await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('SafeReturn Sticker',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Next page'})).toBeDisabled();s.check();
});
test('mobile form stays within viewport and supports confirmed archive',async({page})=>{
 await page.setViewportSize({width:390,height:844});const s=await setup(page,'detail');await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();await page.getByLabel('Product status',{exact:true}).selectOption('archived');await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('button',{name:'Confirm and save'}).click();await expect(page.getByText('Product saved by the server.',{exact:true})).toBeVisible();expect(s.h.state.product.lifecycle_status).toBe('archived');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.locator('main').evaluate(el=>{el.scrollTop=0;});await page.screenshot({path:'../test-results/products-integration/mobile-products.png',fullPage:true});s.check();
});

test('existing eligible category can replace an unsupported selection without changing product slug',async({page})=>{
 const h=createHarness();const other='20000000-0000-4000-8000-000000000003';h.state.categories.push({id:other,name:'Safety QR',slug:'safety-qr',sort_order:1,is_active:true,catalog_version:1});h.state.product.category_id=other;
 const s=await setup(page,'detail',h);await expect(page.getByLabel('Category',{exact:true})).toHaveValue(other);
 await expect(page.getByLabel('Category',{exact:true}).locator('option[value="'+other+'"]')).toHaveJSProperty('disabled',true);
 await page.getByRole('button',{name:'Use QR Stickers category',exact:true}).click();await expect(page.getByLabel('Category',{exact:true})).toHaveValue(cat);
 await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByText('Product saved by the server.',{exact:true})).toBeVisible();expect(h.state.product.category_id).toBe(cat);expect(h.state.product.slug).toBe('sticker');s.check();
});

test('activating the canonical category selects it but waits for explicit product save',async({page})=>{
 const h=createHarness();h.state.categories[0].is_active=false;h.state.product.category_id=null;
 const s=await setup(page,'detail',h);await expect(page.getByText('No active qr-stickers category is available.',{exact:false})).toBeVisible();
 await page.getByText('Manage categories',{exact:true}).click();await page.getByLabel('Category to edit',{exact:true}).selectOption(cat);await page.getByLabel('Active category',{exact:true}).check();await page.getByRole('button',{name:'Save category',exact:true}).click();
 await expect(page.getByLabel('Category',{exact:true})).toHaveValue(cat);expect(h.state.product.category_id).toBeNull();
 await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByText('Product saved by the server.',{exact:true})).toBeVisible();expect(h.state.product.category_id).toBe(cat);s.check();
});

test('creating the canonical category selects its returned ID and invalid publication never forwards',async({page})=>{
 const h=createHarness();h.state.categories=[];h.state.product.category_id=null;
 const s=await setup(page,'detail',h);await expect(page.getByLabel('Product name',{exact:true})).toBeVisible();
 await page.getByLabel('Product status',{exact:true}).selectOption('published');await page.getByRole('button',{name:'Save changes',exact:true}).click();await page.getByRole('button',{name:'Confirm and save',exact:true}).click();await expect(page.getByRole('alert')).toContainText('category slug qr-stickers');expect(h.state.calls.filter((c:any)=>c.method!=='GET')).toHaveLength(0);
 await page.getByText('Manage categories',{exact:true}).click();await page.getByLabel('Category name',{exact:true}).fill('QR Stickers');await page.getByLabel('Category slug',{exact:true}).fill('qr-stickers');await page.getByRole('button',{name:'Create category',exact:true}).click();
 await expect(page.getByLabel('Category',{exact:true})).toHaveValue(h.state.categories[0].id);
 await page.getByRole('button',{name:'Save changes',exact:true}).click();await page.getByRole('button',{name:'Confirm and save',exact:true}).click();await expect(page.getByText('Product saved by the server.',{exact:true})).toBeVisible();expect(h.state.product.category_id).toBe(h.state.categories[0].id);expect(h.state.product.lifecycle_status).toBe('published');s.check();
});

test('published revision appears and saves its key/version without configured enrollment',async({page})=>{
 const h=createHarness(),{content,tid,rid}=require('./templates-fixture.cjs');
 const template={template_id:tid,key:'physically-reviewed',name:'Printed design',purpose:'lost',lifecycle_status:'active',row_version:3,created_at:'2026-10-25T12:00:00Z'};
 h.state.publishedTemplates=[template];h.state.publishedDetails[tid]={template,revisions:[{revision_id:rid,template_id:tid,version:3,status:'published',row_version:4,content:content(),fingerprint_sha256:'a'.repeat(64),created_at:'2026-10-25T12:00:00Z',published_at:'2026-10-25T13:00:00Z'}],next_cursor:null};
 const s=await setup(page,'detail',h);await page.getByRole('button',{name:'Add variant'}).click();
 await expect(page.getByRole('option',{name:'physically-reviewed@3',exact:true})).toHaveCount(1);
 await page.getByLabel('Variant name',{exact:true}).fill('Physical template variant');await page.getByLabel('SKU',{exact:true}).fill('PHYSICAL-3');await page.getByLabel('Approved template reference',{exact:true}).selectOption('physically-reviewed@3');await page.getByRole('button',{name:'Save variant'}).click();await expect(page.getByText('Size saved by the server.',{exact:true})).toBeVisible();expect(h.state.product.variants[0].template_key).toBe('physically-reviewed');expect(h.state.product.variants[0].template_version).toBe(3);s.check();
});
test('draft and retired revisions are excluded while refresh finds a new publication',async({page})=>{
 const h=createHarness(),{content,tid,rid}=require('./templates-fixture.cjs');const template={template_id:tid,key:'newly-published',name:'New design',purpose:'lost',lifecycle_status:'active',row_version:3,created_at:'2026-10-25T12:00:00Z'};h.state.publishedTemplates=[template];h.state.publishedDetails[tid]={template,revisions:[{revision_id:rid,template_id:tid,version:2,status:'retired',row_version:4,content:content(),fingerprint_sha256:'a'.repeat(64),created_at:'2026-10-25T12:00:00Z',published_at:'2026-10-25T13:00:00Z'}],next_cursor:null};const s=await setup(page,'detail',h);await page.getByRole('button',{name:'Add variant'}).click();await expect(page.getByRole('option',{name:'approved-template@1',exact:true})).toHaveCount(1);await expect(page.getByRole('option',{name:'newly-published@2',exact:true})).toHaveCount(0);h.state.publishedDetails[tid].revisions[0].status='published';await page.getByRole('button',{name:'Refresh templates',exact:true}).click();await expect(page.getByRole('option',{name:'newly-published@2',exact:true})).toHaveCount(1);s.check();
});
test('registry failure reports unavailable rather than an empty dropdown',async({page})=>{const h=createHarness();h.state.templateStatus=503;const s=await setup(page,'detail',h);await page.getByRole('button',{name:'Add variant'}).click();await expect(page.getByText('Template choices unavailable. The current reference is preserved.')).toBeVisible();await expect(page.getByLabel('Approved template reference',{exact:true})).toBeDisabled();s.check();});
test('legacy QR pair product explains why independent QR setup needs a new product',async({page})=>{const h=createHarness();h.state.product.commerce_model='legacy_pair';h.state.product.qr_type=null;const s=await setup(page,'detail',h);await expect(page.getByText('This is a legacy QR-pair product.',{exact:false})).toBeVisible();await expect(page.getByLabel('QR type',{exact:true})).toBeDisabled();s.check();});
