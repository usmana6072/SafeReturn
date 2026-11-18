import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const bundle=require('./qa-browser-bundle.cjs');
const compiledCss=require('./compiled-admin-css.cjs');
const id=(n:number)=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const identity={logical_item_id:id(1),qr_id:id(2),order_id:id(3),product_name_snapshot:'Everyday belongings',tag_type:'lost',ownership_status:'unclaimed',public_status:'unactivated',revision:1,activated_at:null,can_activate:false};
async function mount(page:any,ur=false,props?:object,component='IndependentQRs') {
  const errors:string[]=[];
  page.on('pageerror',(error:Error)=>errors.push(error.message));
  await page.route('https://portal.test/**',(route:any)=>route.request().resourceType()==='document'?route.fulfill({contentType:'text/html',body:'<!doctype html><html><head></head><body><div id="root"></div></body></html>'}):route.fallback());
  await page.goto('https://portal.test/my-qr');
  await page.addStyleTag({content:compiledCss()+'\n'+fs.readFileSync('components/customer-portal.css','utf8')});
  await page.evaluate(({ur,props}:any)=>{(window as any).qaUr=ur;(window as any).qaProps=props??{ur};document.documentElement.dir=ur?'rtl':'ltr';},{ur,props});
  await page.addScriptTag({content:bundle({componentPath:component==='ShippingAddresses'?'../components/shipping-addresses.tsx':'../components/independent-qr.tsx',exportName:component,wrapperPath:'../components/customer.tsx',wrapperExport:'CustomerShell'})});
  await expect(page.locator('.customer-portal'),errors.join('\n')).toBeVisible({timeout:15000});
  expect(errors).toEqual([]);
}
for(const width of [320,375,390,430,768,1024,1440])for(const ur of [false,true]) {
  test(`approved palette and responsive navigation ${width}px ${ur?'Urdu':'English'}`,async({page},info)=>{
    await page.setViewportSize({width,height:950});
    await page.route('**/independent-qr/api**',r=>r.fulfill({json:{items:[identity,{...identity,logical_item_id:id(4),qr_id:id(5),tag_type:'ice',product_name_snapshot:'Emergency contact'}],next_cursor:null,activation_released:false}}));
    await mount(page,ur);
    await expect(page.locator('.identity-card')).toHaveCount(2);
    await expect(page.locator('.portal-nav [aria-current=page]')).toHaveAttribute('href','/my-qr');
    expect(await page.locator('.portal-header').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(61, 44, 46)');
    expect(await page.locator('.customer-portal').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(255, 241, 230)');
    expect(await page.locator('.portal-nav .active').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(201, 124, 93)');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await expect(page.getByRole('button',{name:ur?'فعال کرنا شروع کریں':'Begin activation'}).first()).toBeDisabled();
    await page.screenshot({path:info.outputPath(`portal-${width}-${ur?'ur':'en'}.png`),fullPage:true});
  });
}
test('expired server intent cannot confirm; native dialog restores navigation',async({page})=>{
  let confirmations=0;
  await page.route('**/independent-qr/api**',r=>{
    if(r.request().method()==='GET')return r.fulfill({json:{items:[{...identity,can_activate:true}],next_cursor:null,activation_released:true}});
    const command=r.request().postDataJSON();
    if(command.action==='confirm')confirmations++;
    return r.fulfill({json:{intent_id:id(8),logical_item_id:identity.logical_item_id,qr_id:identity.qr_id,expires_at:new Date(Date.now()-1000).toISOString(),method:'delivered_purchaser'}});
  });
  await mount(page);await page.getByRole('button',{name:'Begin activation'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByLabel('I am the purchaser and want to activate this QR.').check();
  await expect(page.getByRole('button',{name:'Confirm activation',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('expired');
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect(confirmations).toBe(0);
});
test('active QR opens its profile and filtering preserves identity allocation',async({page})=>{
  await page.route('**/independent-qr/api**',r=>r.fulfill({json:{items:[{...identity,ownership_status:'active',public_status:'active'},{...identity,logical_item_id:id(4),qr_id:id(5),tag_type:'ice'}],next_cursor:null,activation_released:false}}));
  await mount(page);
  await expect(page.getByRole('link',{name:'Edit this profile'})).toHaveAttribute('href','/my-qr/'+identity.qr_id);
  await page.getByLabel('Filter this page').selectOption('ice');await expect(page.locator('.identity-card')).toHaveCount(1);await expect(page.getByRole('heading',{name:'Emergency QR',exact:true})).toBeVisible();
});
test('saved address create, edit, conflict and delete use server revisions',async({page})=>{
  let version=0,items:any[]=[],conflict=false;const writes:any[]=[];
  await page.route('**/account/shipping-addresses/api',r=>{
    if(r.request().method()==='GET')return r.fulfill({json:{book_version:version,items}});
    const data=r.request().postDataJSON();writes.push({method:r.request().method(),data});
    if(conflict)return r.fulfill({status:409,json:{error:{message:'PRIVATE_CANARY'}}});
    version++;
    if(r.request().method()==='POST')items=[{...data,id:id(9),version:1}];
    if(r.request().method()==='PATCH')items=[{...items[0],...data.body.address,is_default:data.body.is_default,version:2}];
    if(r.request().method()==='DELETE'){items=[];return r.fulfill({status:204});}
    return r.fulfill({json:{book_version:version,item:items[0]}});
  });
  await mount(page,false,{ur:false},'ShippingAddresses');
  for(const [label,value] of [['Recipient name','Example customer'],['Phone (+923…)','+923001234567'],['Street address','Test street'],['City','Lahore']])await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByRole('button',{name:'Save address',exact:true}).click();await expect(page.getByRole('status')).toContainText('Changes saved');
  expect(writes[0].data.expected_book_version).toBe(0);
  await page.getByRole('button',{name:'Edit',exact:true}).click();await page.getByLabel('City',{exact:true}).fill('Karachi');
  await page.getByRole('button',{name:'Save address',exact:true}).click();await expect(page.getByRole('status')).toContainText('Changes saved');
  expect(writes[1].data.body.expected_version).toBe(1);
  await expect(page.locator('.portal-main')).toContainText('Karachi');
  conflict=true;await page.getByRole('button',{name:'Edit',exact:true}).click();await page.getByRole('button',{name:'Save address',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Change not confirmed');await expect(page.locator('body')).not.toContainText('PRIVATE_CANARY');
  conflict=false;await page.getByRole('button',{name:'Reload list',exact:true}).click();
  await page.getByRole('button',{name:'Delete',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button',{name:'Confirm deletion',exact:true}).click();await expect(page.getByText('No saved addresses.')).toBeVisible();
  expect(writes.at(-1)).toMatchObject({method:'DELETE',data:{id:id(9),expected_version:2,expected_book_version:2}});
});
