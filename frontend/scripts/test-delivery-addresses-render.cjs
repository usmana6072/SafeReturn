const {chromium,expect}=require('@playwright/test');
const {spawn}=require('node:child_process'),http=require('node:http'),assert=require('node:assert/strict');
const {setTimeout:delay}=require('node:timers/promises');
const base='http://127.0.0.1:3487',id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const user={id:id(1),email:'addresses@fixture.test',role:'authenticated',aud:'authenticated',app_metadata:{},user_metadata:{},created_at:'2026-01-01T00:00:00Z',email_confirmed_at:'2026-01-01T00:00:00Z'};
const token=[{alg:'HS256',typ:'JWT'},{sub:user.id,aud:'authenticated',role:'authenticated',exp:Math.floor(Date.now()/1000)+3600}].map(o=>Buffer.from(JSON.stringify(o)).toString('base64url')).concat('synthetic').join('.');
let bookVersion=2,items=[
 {id:id(11),version:1,is_default:true,recipient_name:'Amina Khan',phone:'+923001234567',address:'House 24, Street 6\nGarden Town',city:'Lahore',province:'Punjab',postal_code:'00540'},
 {id:id(12),version:1,is_default:false,recipient_name:'Muhammad Usman · '+'Long Recipient Name '.repeat(3),phone:'+447700900123',address:'Apartment 35, Building 42, '+ 'A very long street address near the main intersection '.repeat(3),city:'London',province:null,postal_code:'SW1A 0AA'}
],mode='ok',slow=false,writes=[],reads=0,nextId=30;
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost'),p=url.pathname;
 const reply=(data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(status===204?'':JSON.stringify(data))};
 if(p==='/auth/v1/token')return reply({user,access_token:token,refresh_token:'fixture-refresh',token_type:'bearer',expires_in:3600});
 if(req.headers.authorization!=='Bearer '+token)return reply({},401);
 if(p==='/auth/v1/user')return reply(user);
 if(p==='/api/v1/me')return reply({user_id:user.id,display_name:'Amina',preferred_locale:'en',version:'1',email_verified:true,masked_contact:{phone:null}});
 if(p==='/api/v1/me/shipping-addresses'&&req.method==='GET'){
  reads++;if(slow)await delay(1300);if(mode==='load-error'||mode==='ack-refresh-error')return reply({error:{code:'PRIVATE_CANARY'}},503);
  return reply({book_version:bookVersion,items:mode==='empty'?[]:items});
 }
 if(p.startsWith('/api/v1/me/shipping-addresses')&&req.method!=='GET'){
  if(req.headers.origin!==base)return reply({},403);
  let raw='';for await(const c of req)raw+=c;const data=raw?JSON.parse(raw):null;writes.push({method:req.method,data,url:req.url});
  if(slow)await delay(1300);
  if(mode==='in-use')return reply({error:{code:'CONFLICT',message:'PRIVATE_CANARY'}},409);
  if(mode==='save-error')return reply({error:{code:'PRIVATE_CANARY'}},503);
  const version=req.method==='DELETE'?+url.searchParams.get('expected_book_version'):data.expected_book_version;
  if(version!==bookVersion)return reply({},409);
  if(req.method==='POST'){
   const {expected_book_version,...address}=data;const row={...address,id:id(nextId++),version:1};
   if(row.is_default)items.forEach(a=>{if(a.is_default){a.is_default=false;a.version++;}});
   items.push(row);bookVersion++;return reply({book_version:bookVersion,item:row},201);
  }
  const row=items.find(a=>p.endsWith(a.id));if(!row)return reply({},404);
  if((req.method==='DELETE'?+url.searchParams.get('expected_version'):data.expected_version)!==row.version)return reply({},409);
  if(req.method==='DELETE'){items=items.filter(a=>a!==row);bookVersion++;return reply(null,204);}
  if(data.is_default)items.forEach(a=>{if(a!==row&&a.is_default){a.is_default=false;a.version++;}});
  Object.assign(row,data.address,{is_default:data.is_default,version:row.version+1});bookVersion++;
  if(mode==='ack-then-fail')mode='ack-refresh-error';
  return reply({book_version:bookVersion,item:row});
 }
 return reply({},404);
});
(async()=>{let child,browser;
 try{
 await new Promise((r,j)=>server.once('error',j).listen(8115,'127.0.0.1',r));
 child=spawn(process.execPath,['--require','./tests/qr-fixture-fetch.cjs','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3487'],{windowsHide:true,stdio:['ignore','inherit','inherit'],env:{...process.env,SAFERETURN_API_ORIGIN:'http://127.0.0.1:8115',SAFERETURN_WEB_ORIGIN:base,SAFERETURN_SUPABASE_URL:'https://fixture.test',SAFERETURN_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_fixture',NEXT_TELEMETRY_DISABLED:'1'}});
 for(let i=0;i<60;i++){try{if((await fetch(base+'/login')).ok)break}catch{}await delay(200);}
 browser=await chromium.launch();
 const ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await ctx.newPage();
 page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(base+'/account/shipping-addresses');await expect(page).toHaveURL(/login/);
 await page.getByLabel('Email address').fill(user.email);await page.locator('input[name=password]').fill('fixture-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).not.toHaveURL(/login$/);
 reads=0;await page.goto(base+'/account/shipping-addresses');await expect(page.locator('.address-card')).toHaveCount(2);await page.waitForLoadState('networkidle');assert.equal(reads,1);
 const snap=name=>page.screenshot({path:'test-results/addresses-'+name+'.png',fullPage:true});
 for(const lang of ['en','ur']){
  await ctx.addCookies([{name:'safereturn-language',value:lang,url:base}]);await page.goto(base+'/account/shipping-addresses');await expect(page.locator('.address-card')).toHaveCount(2);await page.waitForLoadState('networkidle');
  for(const width of [320,360,375,390,412,430,768,1024,1440]){
   await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'list overflow '+lang+width);
   if([320,390,768,1440].includes(width))await snap(lang+'-'+width);
   await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
   if(width<800){const last=await page.locator('.address-history-note').boundingBox(),nav=await page.locator('.portal-nav').boundingBox();assert(last.y+last.height<=nav.y,'bottom clearance '+width);}
  }
  const add=page.getByRole('button',{name:lang==='en'?'Add New Address':'نیا پتہ شامل کریں',exact:true});await add.click();
  for(const width of [320,360,375,390,412,430,768,1024,1440]){
   await page.setViewportSize({width,height:844});const dialog=await page.getByRole('dialog').boundingBox();assert(dialog.x>=-1&&dialog.x+dialog.width<=width+1,'sheet width '+lang+width);
   assert(await page.evaluate(()=>{const d=document.querySelector('dialog');return d.scrollWidth<=d.clientWidth+1}),'sheet overflow '+lang+width);
   if(width===390)await snap('add-'+lang+'-390');
  }
  await page.getByRole('button',{name:lang==='en'?'Cancel':'منسوخ',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 }
 await ctx.addCookies([{name:'safereturn-language',value:'en',url:base}]);await page.setViewportSize({width:390,height:844});await page.goto(base+'/account/shipping-addresses');await expect(page.locator('.address-card')).toHaveCount(2);
 await page.getByRole('button',{name:'Add New Address',exact:true}).click();await page.getByRole('button',{name:'Save Address',exact:true}).click();await expect(page.getByText('Please enter your full name.',{exact:true})).toBeVisible();assert.equal(writes.length,0);await snap('validation');
 for(const [label,value]of [['Full Name','New Customer'],['Phone Number','03001234567'],['House / Street Address','12 Example Street'],['City','Karachi'],['Postal Code','00123']])await page.getByLabel(label,{exact:false}).fill(value);
 await page.getByRole('button',{name:'Save Address',exact:true}).click();await expect(page.getByText('Enter a valid phone number with its country code.')).toBeVisible();assert.equal(writes.length,0);
 await page.getByLabel('Phone Number',{exact:false}).fill('+923009876543');await page.getByRole('checkbox',{name:'Set as Default Address',exact:false}).check();
 slow=true;await page.getByRole('button',{name:'Save Address',exact:true}).click();await expect(page.getByRole('button',{name:'Saving Address…'})).toBeDisabled();await snap('saving');slow=false;
 await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.address-card')).toHaveCount(3);assert.equal(writes.length,1);
 assert.deepEqual(Object.keys(writes[0].data).sort(),['recipient_name','phone','address','city','province','postal_code','is_default','expected_book_version'].sort());assert.equal(items.filter(a=>a.is_default).length,1);assert.equal(items.find(a=>a.recipient_name==='New Customer').postal_code,'00123');
 const newCard=page.locator('.address-card').filter({has:page.getByRole('heading',{name:'New Customer',exact:true})});await expect(newCard.locator('.address-badge')).toHaveText('Default Address');
 await newCard.getByRole('button',{name:'Edit Address'}).click();await expect(page.getByRole('checkbox',{name:'Set as Default Address',exact:false})).toBeChecked();await expect(page.getByLabel('Postal Code',{exact:false})).toHaveValue('00123');
 await page.getByLabel('City',{exact:false}).fill('Islamabad');await snap('edit-en-390');await page.setViewportSize({width:390,height:430});await page.getByLabel('Postal Code',{exact:false}).focus();await page.getByRole('button',{name:'Save Changes',exact:true}).scrollIntoViewIfNeeded();const save=await page.getByRole('button',{name:'Save Changes',exact:true}).boundingBox();assert(save.y>=0&&save.y+save.height<=430,'short viewport save');
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);assert.equal(writes[1].method,'PATCH');assert.equal(writes[1].data.expected_version,1);assert.equal(writes[1].data.is_default,true);
 await newCard.getByRole('button',{name:'Edit Address'}).click();await page.getByLabel('City',{exact:false}).fill('Unsaved city');await page.getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByRole('heading',{name:'Discard Your Changes?'})).toBeVisible();await page.getByRole('button',{name:'Keep Editing'}).click();await expect(page.getByLabel('City',{exact:false})).toHaveValue('Unsaved city');
 await page.goBack();await expect(page.getByRole('heading',{name:'Discard Your Changes?'})).toBeVisible();await page.getByRole('button',{name:'Discard Changes'}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 mode='in-use';await newCard.getByRole('button',{name:'Edit Address'}).click();await page.getByLabel('City',{exact:false}).fill('Blocked edit');await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.locator('.address-feedback[role=alert]')).toContainText('in use by an order');await expect(page.getByLabel('City',{exact:false})).toHaveValue('Blocked edit');await expect(page.locator('body')).not.toContainText('PRIVATE_CANARY');
 mode='ok';await page.getByRole('dialog').getByRole('button',{name:'Refresh Addresses',exact:true}).click();await page.getByRole('button',{name:'Cancel',exact:true}).click();await page.getByRole('button',{name:'Discard Changes'}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 const other=page.locator('.address-card').filter({has:page.getByRole('heading',{name:'Amina Khan',exact:true})});await other.getByRole('button',{name:'Set as Default'}).click();await expect(other.locator('.address-badge')).toHaveText('Default Address');assert.equal(items.filter(a=>a.is_default).length,1);
 await page.getByRole('button',{name:'Delete address for New Customer',exact:true}).click();await snap('delete-dialog');await page.getByRole('button',{name:'Keep Address'}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 mode='in-use';await page.getByRole('button',{name:'Delete address for New Customer',exact:true}).click();await page.getByRole('button',{name:'Delete Address',exact:true}).click();await expect(page.locator('.address-feedback[role=alert]')).toContainText('in use by an order');assert.equal(items.length,3);mode='ok';await page.getByRole('dialog').getByRole('button',{name:'Refresh Addresses',exact:true}).click();await page.getByRole('button',{name:'Delete Address',exact:true}).click();await expect(page.locator('.address-card')).toHaveCount(2);
 await page.reload();await expect(page.locator('.address-card')).toHaveCount(2);await expect(other.locator('.address-badge')).toHaveText('Default Address');
 mode='ack-then-fail';await other.getByRole('button',{name:'Edit Address'}).click();await page.getByLabel('City',{exact:false}).fill('Peshawar');await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.address-feedback[role=alert]')).toContainText('Your change was saved');mode='ok';await page.getByRole('button',{name:'Refresh Addresses',exact:true}).last().click();await expect(other).toContainText('Peshawar');
 mode='load-error';await page.reload();await expect(page.getByRole('heading',{name:'Couldn’t Load Addresses'})).toBeVisible();await snap('error');mode='empty';await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.getByRole('heading',{name:'No Saved Addresses'})).toBeVisible();await snap('empty');
 mode='ok';items=items.slice(0,1);await page.reload();await expect(page.locator('.address-card')).toHaveCount(1);await snap('one-address');slow=true;await page.reload({waitUntil:'commit'});await expect(page.locator('.address-loading')).toBeVisible();await snap('loading');await expect(page.locator('.address-card')).toHaveCount(1);slow=false;
 await page.setViewportSize({width:320,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'large text');
 assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);assert.deepEqual(errors,[]);
 console.log('PASS production addresses: 18 list and 18 form EN/Urdu responsive layouts; exact-schema create/edit/default/delete with revisions, inline validation, country-code phones, leading postal zeros, unsaved Cancel/Back guards, blocked referenced addresses, confirmed save plus failed refresh, persistence, auth redirect, loading/error/empty/one/long states, bottom clearance and short keyboard-sized viewport. Isolated authenticated HTTP fixtures.');
 }finally{await browser?.close();child?.kill();server.close();server.closeAllConnections();}
})().catch(e=>{console.error(e);process.exitCode=1});

