import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const bundle=require('./qa-browser-bundle.cjs');
const compiledCss=require('./compiled-admin-css.cjs');
const id=(n:number)=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const identity={logical_item_id:id(1),qr_id:id(2),order_id:id(3),product_name_snapshot:'Everyday belongings',tag_type:'lost',ownership_status:'unclaimed',public_status:'unactivated',revision:1,activated_at:null,can_activate:false};
async function mount(page:any,ur=false,props?:object,component='IndependentQRs',routePath='/my-qr') {
  const errors:string[]=[];
  page.on('pageerror',(error:Error)=>errors.push(error.message));
  await page.route('https://portal.test/**',(route:any)=>route.request().resourceType()==='document'?route.fulfill({contentType:'text/html',body:'<!doctype html><html><head></head><body><div id="root"></div></body></html>'}):route.fallback());
  await page.goto('https://portal.test'+routePath);
  await page.addStyleTag({content:compiledCss()+'\n'+fs.readFileSync('components/customer-portal.css','utf8')+(component==='ShopCatalog'?fs.readFileSync('components/shop.css','utf8'):'')});
  await page.evaluate(({ur,props}:any)=>{(window as any).qaUr=ur;(window as any).qaProps=props??{ur};document.documentElement.dir=ur?'rtl':'ltr';},{ur,props});
  const componentPath=component==='ShippingAddresses'?'../components/shipping-addresses.tsx':component==='ShopCatalog'?'../components/shop-catalog.tsx':'../components/independent-qr.tsx';
  await page.addScriptTag({content:bundle({componentPath,exportName:component,wrapperPath:'../components/customer.tsx',wrapperExport:'CustomerShell'})});
  await expect(page.locator('.customer-portal'),errors.join('\n')).toBeVisible({timeout:15000});
  expect(errors).toEqual([]);
}
test('portal shop keeps the customer navigation on mobile and desktop',async({page})=>{
  for(const width of [430,1024]){
    await page.setViewportSize({width,height:900});
    await mount(page,false,{ur:false,catalog:{products:[],unavailable:false},shopPath:'/portal/shop'},'ShopCatalog','/portal/shop');
    const nav=page.getByRole('navigation',{name:'Customer navigation'});
    await expect(nav.getByRole('link',{name:'Shop',exact:true})).toHaveAttribute('href','/portal/shop');
    await expect(nav.getByRole('link',{name:'Shop',exact:true})).toHaveAttribute('aria-current','page');
    await expect(nav.getByRole('link',{name:'Home',exact:true})).toHaveAttribute('href','/dashboard');
    if(width<800){
      await expect(nav.getByRole('link')).toHaveCount(4);
      await nav.getByRole('button',{name:'More'}).click();
      await expect(page.getByRole('dialog',{name:'More'}).getByRole('link',{name:'Support'})).toHaveAttribute('href','/help');
    }else{
      await expect(nav.getByRole('link',{name:'Support'})).toHaveAttribute('href','/help');
      await expect(nav.getByRole('link',{name:'Account Settings'})).toHaveAttribute('href','/account');
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
});
for(const width of [320,360,375,390,412,430,768,1024,1440])for(const ur of [false,true]) {
  test(`approved palette and responsive navigation ${width}px ${ur?'Urdu':'English'}`,async({page},info)=>{
    await page.setViewportSize({width,height:950});
    await page.route('**/independent-qr/api**',r=>r.fulfill({json:{items:[identity,{...identity,logical_item_id:id(4),qr_id:id(5),tag_type:'ice',product_name_snapshot:'Emergency contact'}],next_cursor:null,activation_released:false}}));
    await mount(page,ur);
    await expect(page.locator('.lib-card')).toHaveCount(2);
    await expect(page.locator('.portal-nav [aria-current=page]')).toHaveAttribute('href','/my-qr');
    expect(await page.locator('.portal-header').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(61, 44, 46)');
    expect(await page.locator('.customer-portal').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(248, 242, 236)');
    expect(await page.locator('.portal-nav .active').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe(width < 800 ? 'rgb(89, 72, 66)' : 'rgb(201, 124, 93)');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await expect(page.getByRole('button',{name:ur?'فعال ہونے کی حالت دیکھیں':'View Activation Status'})).toHaveCount(2);
    await page.screenshot({path:info.outputPath(`portal-${width}-${ur?'ur':'en'}.png`),fullPage:true});
  });
}
test('mobile More exposes the secondary routes and returns keyboard focus', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.route('**/independent-qr/api**', route => route.fulfill({ json: { items: [], next_cursor: null, activation_released: false } }));
  await mount(page);
  const nav = page.getByRole('navigation', { name: 'Customer navigation' });
  await expect(nav.getByRole('link')).toHaveCount(4);
  await expect(nav.getByRole('link', { name: 'Shop' })).toHaveAttribute('href', '/portal/shop');
  const trigger = nav.getByRole('button', { name: 'More' });
  await trigger.focus();
  await page.keyboard.press('Enter');
  const sheet = page.getByRole('dialog', { name: 'More' });
  await expect(sheet.getByRole('link')).toHaveCount(6);
  await expect(sheet.getByRole('link', { name: 'Shopping Cart' })).toHaveAttribute('href', '/cart');
  await expect(sheet.getByRole('button', { name: 'Log out' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  const avatar = await page.locator('.header-avatar').boundingBox();
  expect(avatar!.x + avatar!.width).toBeLessThanOrEqual(320);
});

test('expired server intent cannot confirm; native dialog restores navigation',async({page})=>{
  let confirmations=0;
  await page.route('**/independent-qr/api**',r=>{
    if(r.request().method()==='GET')return r.fulfill({json:{items:[{...identity,can_activate:true}],next_cursor:null,activation_released:true}});
    const command=r.request().postDataJSON();
    if(command.action==='confirm')confirmations++;
    return r.fulfill({json:{intent_id:id(8),logical_item_id:identity.logical_item_id,qr_id:identity.qr_id,expires_at:new Date(Date.now()-1000).toISOString(),method:'delivered_purchaser'}});
  });
  await mount(page);await page.getByRole('button',{name:'Activate QR'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByLabel('I am the purchaser and want to activate this QR.')).toBeDisabled();
  await expect(page.getByRole('button',{name:'Confirm Activation',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('expired');
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect(confirmations).toBe(0);
});
test('active QR opens its profile and filtering preserves identity allocation',async({page})=>{
  await page.route('**/independent-qr/api**',r=>r.fulfill({json:{items:[{...identity,ownership_status:'active',public_status:'active'},{...identity,logical_item_id:id(4),qr_id:id(5),tag_type:'ice'}],next_cursor:null,activation_released:false}}));
  await mount(page);
  await expect(page.getByRole('link',{name:'Manage QR'})).toHaveAttribute('href','/my-qr/'+identity.qr_id);
  await page.getByRole('button',{name:'Filter',exact:true}).click();await page.getByLabel('Tag type').selectOption('ice');await page.getByRole('button',{name:'Done',exact:true}).click();await expect(page.locator('.lib-card')).toHaveCount(1);await expect(page.getByRole('heading',{name:'Everyday belongings',exact:true})).toBeVisible();
});
