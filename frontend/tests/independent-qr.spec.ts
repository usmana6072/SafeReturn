import {test,expect} from '@playwright/test';
const bundle=require('./qa-browser-bundle.cjs');
const id=(n:number)=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const first={logical_item_id:id(1),qr_id:id(2),order_id:id(3),product_name_snapshot:'Synthetic labels',tag_type:'lost',ownership_status:'unclaimed',public_status:'unactivated',revision:2,activated_at:null,can_activate:true};
const second={...first,logical_item_id:id(4),qr_id:id(5),product_name_snapshot:'Synthetic emergency',tag_type:'ice'};
async function mount(page:any,ur=false){
 await page.route('https://owner.test/**',(r:any)=>r.request().resourceType()!=='document'?r.fallback():r.fulfill({contentType:'text/html',body:'<!doctype html><html><head><style>*{box-sizing:border-box}body{padding:16px;margin:0;font:16px sans-serif}label{display:block;margin:8px 0}section,article{min-width:0;overflow-wrap:anywhere}button{max-width:100%}</style></head><body><div id="root"></div></body></html>'}));
 await page.goto('https://owner.test/');await page.evaluate((ur:boolean)=>{(window as any).qaProps={ur};},ur);await page.addScriptTag({content:bundle({componentPath:'../components/independent-qr.tsx',exportName:'IndependentQRs'})});
}
test('one delivered identity activates with explicit confirmation; uncertain retry keeps key',async({page})=>{
 let active=false,confirmations=0;const writes:any[]=[];
 await page.route('**/independent-qr/api**',r=>{
  if(r.request().method()==='GET')return r.fulfill({json:{items:[active?{...first,ownership_status:'active',public_status:'active',revision:3,can_activate:false}:first,second],next_cursor:null,activation_released:true}});
  const input=r.request().postDataJSON();writes.push(input);
  if(input.action==='begin')return r.fulfill({status:201,json:{intent_id:id(6),logical_item_id:first.logical_item_id,qr_id:first.qr_id,expires_at:'2026-10-22T10:00:00Z',method:'delivered_purchaser'}});
  if(++confirmations===1)return r.fulfill({status:503,json:{error:{code:'PRIVATE_CANARY'}}});active=true;return r.fulfill({status:201,json:{status:'active'}});
 });
 await mount(page);await page.getByRole('button',{name:'Begin activation',exact:true}).first().click();
 await expect(page.getByRole('button',{name:'Confirm activation',exact:true})).toBeDisabled();await page.getByLabel('I am the purchaser and want to activate this QR.',{exact:true}).check();
 await page.getByRole('button',{name:'Confirm activation',exact:true}).click();await expect(page.getByRole('status')).toContainText('uncertain');await page.getByRole('button',{name:'Confirm activation',exact:true}).click();
 await expect(page.getByRole('link',{name:'Edit this profile'})).toHaveCount(1);await expect(page.getByRole('button',{name:'Begin activation',exact:true})).toHaveCount(1);
 expect(writes[1].key).toBe(writes[2].key);expect(writes[1].body).toEqual({intent_id:id(6),confirmed:true});expect(JSON.stringify(writes)).not.toContain('public_token');expect(await page.evaluate(()=>[localStorage.length,sessionStorage.length])).toEqual([0,0]);expect(await page.locator('body').innerText()).not.toContain('PRIVATE_CANARY');
});
test('public availability changes only the selected identity; denied refresh clears rows',async({page})=>{
 let disabled=false,denied=false;const writes:any[]=[];
 await page.route('**/independent-qr/api**',r=>{
  if(r.request().method()==='GET')return r.fulfill({status:denied?403:200,json:denied?{error:{code:'PRIVATE_CANARY'}}:{items:[{...first,ownership_status:'active',public_status:disabled?'owner_disabled':'active',revision:disabled?4:3,can_activate:false},second],next_cursor:null,activation_released:true}});
  writes.push(r.request().postDataJSON());disabled=true;return r.fulfill({json:{}});
 });
 await mount(page);await expect(page.getByRole('button',{name:'Disable public access',exact:true})).toBeDisabled();await page.getByLabel('I reviewed the effect on public access for this QR.',{exact:true}).check();await page.getByRole('button',{name:'Disable public access',exact:true}).click();await expect(page.getByRole('button',{name:'Resume public access'})).toBeVisible();expect(writes[0].qr_id).toBe(first.qr_id);expect(writes[0].body.expected_revision).toBe(3);
 denied=true;await page.getByRole('button',{name:'Refresh identities'}).click();await expect(page.getByRole('link',{name:'Edit this profile'})).toHaveCount(0);expect(await page.locator('body').innerText()).not.toContain('PRIVATE_CANARY');
});
test('Urdu mobile keeps unreleased activation disabled and explains account entitlement',async({page},info)=>{
 await page.setViewportSize({width:375,height:900});await page.route('**/independent-qr/api**',r=>r.fulfill({json:{items:[{...first,can_activate:false},{...second,can_activate:false}],next_cursor:null,activation_released:false}}));
 await mount(page,true);await expect(page.getByRole('button',{name:'فعال کرنا شروع کریں'}).first()).toBeDisabled();await expect(page.locator('section[lang="ur"]').first()).toHaveAttribute('dir','rtl');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('independent-qr-ur-mobile.png'),fullPage:true});
});
