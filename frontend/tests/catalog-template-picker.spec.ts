import { test, expect } from '@playwright/test';
import { parseTemplateChoices } from '../lib/catalog-template-choices';

test('strict template response parser excludes ambiguous and private projections',()=>{
 const valid={as_of:'2026-10-19T17:00:00Z',items:[{template_key:'alpha',template_version:1}]};
 expect(parseTemplateChoices(valid)).toEqual(valid);
 for(const data of [{...valid,as_of:'2026-02-30T17:00:00Z'}, {...valid,private:'PRIVATE_CANARY'}, {...valid,items:[{template_key:'alpha',template_version:'1'}]}, {...valid,items:[...valid.items,...valid.items]}, {...valid,items:[{template_key:'x/y',template_version:1}]}, {...valid,items:[{...valid.items[0],path:'PRIVATE_CANARY'}]}]) expect(()=>parseTemplateChoices(data)).toThrow('unavailable');
});

test('template picker loading, empty, outage, stale, removed and draft-safe bindings',async({page,context},testInfo)=>{
 test.setTimeout(120000);page.setDefaultTimeout(15000);
 await page.clock.install();
 const pid='00000000-0000-0000-0000-000000000101',vid='00000000-0000-0000-0000-000000000102';
 const variant={id:vid,catalog_version:1,sku:'LEGACY',name:'Legacy variant',unit_price:'100.00',template_key:'legacy-only',template_version:7,is_active:true,fulfillment_method:'pdf_label',size_mm:'30',currency_code:'PKR'};
 const product={id:pid,catalog_version:4,name:'Synthetic draft',slug:'synthetic-draft',description:'Synthetic description',category_id:null,lifecycle_status:'draft',is_featured:false,featured_sort_order:0,variants:[variant],images:[]};
 let mode:'empty'|'valid'|'down'|'removed'='empty',calls=0,saveStatus=201;
 let release: (()=>void)|null=null,hold=false;
 const saves: any[]=[];
 await page.route('**/admin/catalog-api**',async route=>{
  const request=route.request();
  if(request.method()==='GET'){
   if(request.url().includes('approved-templates')){
    calls++;
    if(hold) await new Promise<void>(resolve=>{release=resolve;});
    if(mode==='down')return route.fulfill({status:503,json:{error:{code:'PROVIDER_UNAVAILABLE',message:'PRIVATE_CANARY'}}});
    const items=mode==='empty'?[]:mode==='removed'?[{template_key:'beta',template_version:2}]:[{template_key:'alpha',template_version:1},{template_key:'beta',template_version:2}];
    return route.fulfill({json:{as_of:new Date().toISOString(),items}});
   }
   return route.fulfill({json:{items:request.url().includes('categories')?[]:[product]}});
  }
  saves.push(request.postDataJSON());
  return route.fulfill({status:saveStatus,json:saveStatus===201?{id:vid}:{error:{code:'PHYSICAL_CATALOG_APPROVAL_REQUIRED',message:'PRIVATE_CANARY'}}});
 });
 await page.goto('/admin/products');await expect(page).toHaveURL(/login/);
 const relay='/admin/catalog-api?path=/admin/catalog/approved-templates';
 expect((await page.request.get(relay)).status()).toBe(401);
 await page.goto('/login');await page.getByLabel('Email address').fill('catalog@synthetic.invalid');await page.locator('input[name=password]').fill('synthetic-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).not.toHaveURL(/\/login/);
 await page.goto('/admin/products');
 const section=page.locator('section').filter({has:page.getByRole('heading',{name:'Synthetic draft',exact:true})});
 const picker=page.getByRole('region',{name:'Catalog template selection'});
 const choice=page.getByLabel('Catalog template',{exact:true});
 const notice=page.locator('#main > p[role="status"]');
 hold=true;await section.getByRole('button',{name:'Add variant',exact:true}).click();
 await expect(picker.getByRole('status')).toContainText('Loading');await expect(choice).toBeDisabled();
 hold=false;await expect.poll(()=>release!==null).toBe(true);release!();
 await expect(picker.getByRole('status')).toHaveText('No published or configured templates are available.');
 await page.getByLabel('sku',{exact:true}).fill('SYNTHETIC');await page.getByLabel('name',{exact:true}).fill('Keep draft values');await page.getByLabel('unit price',{exact:true}).fill('100.00');
 await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toHaveText('Saved.');expect(saves[0].body.template_key).toBeNull();expect(saves[0].body.template_version).toBe(1);
 mode='valid';await page.getByRole('button',{name:'Refresh templates',exact:true}).click();await expect(choice).toBeEnabled();await choice.focus();await expect(choice).toBeFocused();await choice.selectOption('alpha@1');
 await page.getByLabel('name',{exact:true}).fill('Preserved');await page.getByLabel('sku',{exact:true}).fill('NEW-SYNTHETIC');await page.getByLabel('unit price',{exact:true}).fill('125.00');
 mode='down';const before=saves.length;await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toContainText('Selected template is unavailable');expect(saves.length).toBe(before);await expect(page.getByLabel('name',{exact:true})).toHaveValue('Preserved');await expect(picker).toContainText('alpha@1');
 mode='valid';saveStatus=422;await page.getByRole('button',{name:'Refresh templates',exact:true}).click();await expect(choice).toBeEnabled();await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toContainText('reviewed template');expect(saves.at(-1).body.template_key).toBe('alpha');expect(saves.at(-1).body.template_version).toBe(1);
 mode='removed';const removedBefore=saves.length;await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toContainText('Selected template is unavailable');expect(saves.length).toBe(removedBefore);await expect(picker).toContainText('alpha@1');
 await choice.selectOption('beta@2');await page.clock.fastForward(60001);await expect(picker.getByRole('status')).toContainText('stale');await expect(choice).toBeDisabled();
 const count=calls;await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));await expect.poll(()=>calls).toBeGreaterThan(count);await expect(choice).toBeEnabled();
 mode='empty';await section.getByRole('button',{name:'Edit variant',exact:true}).click();await expect(picker.getByRole('status')).toHaveText('No published or configured templates are available.');await expect(picker).toContainText('legacy-only@7');
 await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toContainText('reviewed template');expect(saves.at(-1).body.template_key).toBe('legacy-only');expect(saves.at(-1).body.template_version).toBe(7);
 await page.getByRole('button',{name:'Clear draft template',exact:true}).click();await page.getByRole('button',{name:'Save',exact:true}).click();await expect(notice).toContainText('reviewed template');expect(saves.at(-1).body.template_key).toBeNull();expect(saves.at(-1).body.template_version).toBe(7);
 expect(await page.locator('body').innerText()).not.toContain('PRIVATE_CANARY');expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
 // APIRequest bypasses the browser's in-memory catalog mocks.
 for(const path of [relay+'&x=1',relay+'&path=/admin/products']){const r=await page.request.get(path);expect(r.status()).toBe(422);expect(r.headers()['cache-control']).toBe('private, no-store');}
 for(const method of ['POST','PUT','PATCH','DELETE','OPTIONS']) {const r=await page.request.fetch(relay,{method});expect(r.status()).toBe(405);expect(r.headers()['allow']).toBe('GET');expect(r.headers()['x-content-type-options']).toBe('nosniff');}
 const override=await page.request.post('/admin/catalog-api',{headers:{Origin:'http://127.0.0.1:3100'},data:{path:'/admin/catalog/approved-templates',method:'GET'}});expect(override.status()).toBe(405);
 const unavailable=await page.request.get(relay);expect(unavailable.status()).toBe(503);expect(await unavailable.text()).not.toContain('PRIVATE_CANARY');
 await context.addCookies([{name:'safereturn-language',value:'ur',url:'http://127.0.0.1:3100'}]);await page.setViewportSize({width:375,height:900});await page.goto('/admin/products');await page.locator('section').filter({has:page.getByRole('heading',{name:'Synthetic draft',exact:true})}).getByRole('button',{name:'نیا ویریئنٹ',exact:true}).click();await expect(page.locator('html')).toHaveAttribute('dir','rtl');await expect(page.getByLabel('کیٹلاگ ٹیمپلیٹ',{exact:true})).toBeDisabled();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:testInfo.outputPath('template-picker-rtl.png'),fullPage:true});
});
