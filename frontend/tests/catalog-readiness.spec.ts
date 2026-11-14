import { test, expect } from '@playwright/test';
test('synthetic catalog publication guidance, preserved failures and mobile RTL', async ({page,context},testInfo) => {
 test.setTimeout(120000); page.setDefaultTimeout(20000);
 const pid='00000000-0000-0000-0000-000000000101';
 const product={id:pid,catalog_version:4,name:'Synthetic draft',price_per_copy:'100.00',max_order_copies:100,slug:'synthetic-draft',description:'Synthetic description',category_id:null,lifecycle_status:'draft',is_featured:false,featured_sort_order:0,variants:[],images:[]};
 let code='FUTURE_PRODUCT_DISABLED', status=422;
 const saves:Record<string,unknown>[]=[];
 await page.route('**/admin/catalog-api**', async route=>{
   if(route.request().method()==='GET') return route.fulfill({json:route.request().url().includes('approved-templates')?{as_of:new Date().toISOString(),items:[]}:{items:route.request().url().includes('categories')?[]:[product]}});
   saves.push(route.request().postDataJSON());
   return route.fulfill({status,json:{error:{code,message:'PRIVATE_CANARY_PROVIDER',details:{secret:'PRIVATE_CANARY_TOKEN'}}}});
 });
 await page.goto('/admin/products');await expect(page).toHaveURL(/login/);
 expect((await page.request.get('/admin/catalog-api?path=/admin/products')).status()).toBe(401);
 await page.goto('/login');await page.getByLabel('Email address').fill('catalog@synthetic.invalid');await page.locator('input[name=password]').fill('synthetic-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).not.toHaveURL(/\/login/);
 await page.goto('/admin/products');await expect(page.getByRole('heading',{name:'Catalog management'})).toBeVisible();
 const section=page.locator('section').filter({has:page.getByRole('heading',{name:'Synthetic draft',exact:true})});
 await section.getByRole('button',{name:'Edit product',exact:true}).click();
 await page.getByLabel('name',{exact:true}).fill('Keep my unsaved edit');
 await page.getByLabel('lifecycle status',{exact:true}).selectOption('published');
 await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.locator('#main > p[role="status"]')).toContainText('active QR Stickers');
 await expect(page.getByLabel('name',{exact:true})).toHaveValue('Keep my unsaved edit');await expect(page.getByLabel('lifecycle status',{exact:true})).toHaveValue('published');
 const firstKey=saves[0].key;
 await page.getByRole('button',{name:'Save',exact:true}).click();expect(saves[1].key).toBe(firstKey);
 for(const [next,expected] of [['PHYSICAL_CATALOG_APPROVAL_REQUIRED','reviewed template key/version'],['VERIFIED_PUBLIC_IMAGE_REQUIRED','server verification'],['VERSION_MISMATCH','entries remain']] as const){code=next;status=next==='VERSION_MISMATCH'?412:422;await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.locator('#main > p[role="status"]')).toContainText(expected);await expect(page.getByLabel('name',{exact:true})).toHaveValue('Keep my unsaved edit');}
 expect(await page.locator('body').innerText()).not.toContain('PRIVATE_CANARY');
 await section.getByRole('button',{name:'Add variant',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'Template guidance'})).toContainText('not the SKU');
 await expect(page.getByRole('complementary',{name:'Template guidance'})).toContainText('cannot create or approve');
 await expect(page.getByLabel('Catalog template',{exact:true})).toBeDisabled();
 await page.getByLabel('sku',{exact:true}).fill('SYNTHETIC-SKU');await page.getByLabel('name',{exact:true}).fill('Synthetic variant');await expect(page.getByLabel('unit price',{exact:true})).toHaveCount(0);
 code='VALIDATION_ERROR';status=422;await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.locator('#main > p[role="status"]')).toContainText('required fields');await expect(page.getByLabel('sku',{exact:true})).toHaveValue('SYNTHETIC-SKU');
 expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);
 // These requests bypass browser mocks and exercise the existing relay boundaries.
 expect((await page.request.post('/admin/catalog-api',{headers:{Origin:'https://untrusted.invalid'},data:{path:'/admin/products',method:'PATCH'}})).status()).toBe(403);
 expect((await page.request.get('/admin/catalog-api?path=/admin/catalog/approved-templates&extra=1')).status()).toBe(422);
 await context.addCookies([{name:'safereturn-language',value:'ur',url:'http://127.0.0.1:3100'}]);await page.setViewportSize({width:375,height:900});await page.goto('/admin/products');
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await page.locator('section').filter({has:page.getByRole('heading',{name:'Synthetic draft',exact:true})}).getByRole('button',{name:'نیا ویریئنٹ',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'ٹیمپلیٹ کی رہنمائی'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:testInfo.outputPath('catalog-rtl.png'),fullPage:true});
});
