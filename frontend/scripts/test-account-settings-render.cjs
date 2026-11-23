const {chromium,expect}=require('@playwright/test');
const {spawn}=require('node:child_process'),http=require('node:http'),assert=require('node:assert/strict');
const {setTimeout:delay}=require('node:timers/promises');
const base='http://127.0.0.1:3487',id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const user={id:id(1),email:'amina.'+'longaccount'.repeat(7)+'@example.test',role:'authenticated',aud:'authenticated',app_metadata:{},user_metadata:{},created_at:'2026-01-01T00:00:00Z',email_confirmed_at:'2026-01-01T00:00:00Z'};
const token=[{alg:'HS256',typ:'JWT'},{sub:user.id,aud:'authenticated',role:'authenticated',exp:Math.floor(Date.now()/1000)+3600}].map(o=>Buffer.from(JSON.stringify(o)).toString('base64url')).concat('synthetic').join('.');
let account={user_id:user.id,display_name:'Amina '+'LongFamilyName '.repeat(5),preferred_locale:'en',email_verified:true,masked_contact:{phone:'••••'},version:'0'},mode='ok',active=true,slow=false,historyMode='ok',exportStage='requested',grantActive=false,revision=0,calls=[],writes=[],logoutScope=null;
const events=[{id:id(41),purpose:'profile.whatsapp.updated',version:'wa-public-v1',timestamp:'2026-11-20T10:00:00Z',active:true,state_scope:'recorded_event'},{id:id(42),purpose:'profile.ice_contact.published',version:null,timestamp:'2026-11-19T10:00:00Z',active:false,state_scope:'recorded_event'}];
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost'),p=url.pathname;
 const reply=(data,status=200,extra={})=>{res.writeHead(status,{'content-type':'application/json',...extra});res.end(status===204?'':JSON.stringify(data))};
 if(p==='/auth/v1/token'){active=true;return reply({user,access_token:token,refresh_token:'fixture-refresh',token_type:'bearer',expires_in:3600});}
 if(p==='/auth/v1/recover'||p==='/auth/v1/resend'){calls.push(p);return reply({});}
 if(req.headers.authorization!=='Bearer '+token||!active)return reply({},401);
 if(p==='/auth/v1/user')return reply(user);
 if(p==='/auth/v1/logout'){logoutScope=url.searchParams.get('scope');if(mode==='logout-error')return reply({msg:'PRIVATE_CANARY'},503);active=false;return reply(null,204);}
 if(p==='/api/v1/me/staff-security')return reply({},403);
 calls.push(req.method+' '+p+url.search);
 let raw='';for await(const c of req)raw+=c;const body=raw?JSON.parse(raw):{};
 if(slow)await delay(1300);
 if(p==='/api/v1/me'){
  if(mode==='profile-error')return reply({message:'PRIVATE_CANARY'},503);
  if(req.method==='PATCH'){
   writes.push({body,version:req.headers['if-match']});
   if(mode==='stale'){account={...account,display_name:'Changed Elsewhere',version:'1700000000.'+String(++revision).padStart(6,'0')};mode='ok';return reply({},412);}
   if(req.headers['if-match']!=='"'+account.version+'"')return reply({},412);
   account={...account,...body,version:'1700000000.'+String(++revision).padStart(6,'0')};
  }
  return reply(account);
 }
 if(p==='/api/v1/me/finder-messages')return reply({items:[],next_cursor:null});
 if(p==='/api/v1/me/shipping-addresses')return reply({book_version:0,items:[]});
 if(p==='/api/v1/me/privacy-consents')return historyMode==='error'?reply({message:'PRIVATE_CANARY'},503):reply({items:historyMode==='empty'?[]:events,has_more:false});
 if(p==='/api/v1/me/account-deletion-requests'){if(body.confirm!==true)return reply({},403);writes.push({deletion:body});return reply({request_id:id(50)},202);}
 if(p==='/api/v1/me/privacy/exports'&&req.method==='POST'){if(body.scope!=='basic_v1'||body.confirmed!==true||!req.headers['idempotency-key'])return reply({},400);writes.push({export:body});exportStage='requested';return reply({request_id:id(60)},202);}
 if(p.startsWith('/api/v1/me/privacy/exports/')){
  if(!p.includes(id(60)))return reply({error:{code:'NOT_FOUND'}},404);
  if(p.endsWith('/download-grants')){if(body.confirmed!==true||body.expected_revision!==2)return reply({},409);grantActive=true;return reply({grant:'FIXTURE-ONE-USE-GRANT'});}
  if(p.endsWith('/download')){if(!grantActive||req.headers['x-privacy-grant']!=='FIXTURE-ONE-USE-GRANT')return reply({},410);grantActive=false;return reply({profile:{display_name:account.display_name}},200,{'content-disposition':'attachment; filename="safereturn-basic-v1.json"'});}
  return reply({request_id:id(60),case_id:id(61),status:exportStage,revision:exportStage==='ready'?2:1,...(exportStage==='ready'?{expires_at:new Date(Date.now()+86400000).toISOString()}:{}),categories:{profile:{disposition:'included',reason_code:'within_scope',source_count:1,schema_version:1,source_watermark:'fixture'}}});
 }
 return reply({},404);
});
(async()=>{let child,browser;
 try{
 await new Promise((r,j)=>server.once('error',j).listen(8115,'127.0.0.1',r));
 child=spawn(process.execPath,['--require','./tests/qr-fixture-fetch.cjs','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3487'],{windowsHide:true,stdio:['ignore','inherit','inherit'],env:{...process.env,SAFERETURN_API_ORIGIN:'http://127.0.0.1:8115',SAFERETURN_WEB_ORIGIN:base,SAFERETURN_SUPABASE_URL:'https://fixture.test',SAFERETURN_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_fixture',NEXT_TELEMETRY_DISABLED:'1'}});
 for(let i=0;i<60;i++){try{if((await fetch(base+'/login')).ok)break}catch{}await delay(200);}
 browser=await chromium.launch();const ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await ctx.newPage();
 page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(base+'/account');await expect(page).toHaveURL(/login/);await page.getByLabel('Email address').fill(user.email);await page.locator('input[name=password]').fill('fixture-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(base+'/account');
 calls=[];await page.goto(base+'/account');await expect(page.locator('section.settings-profile')).toBeVisible();await page.waitForLoadState('networkidle');assert.equal(calls.filter(p=>p==='GET /api/v1/me').length,1);
 const snap=name=>page.screenshot({path:'test-results/account-'+name+'.png',fullPage:true});
 for(const lang of ['en','ur']){
  await ctx.addCookies([{name:'safereturn-language',value:lang,url:base}]);await page.goto(base+'/account');await expect(page.locator('section.settings-profile')).toBeVisible();await page.waitForLoadState('networkidle');
  for(const width of [320,360,375,390,412,430,768,1024,1440]){
   await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'account overflow '+lang+width);
   await expect(page.locator('a[href^="/admin"]')).toHaveCount(0);
   if([320,390,768,1440].includes(width))await snap(lang+'-'+width);
   await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
   if(width<800){const last=await page.locator('.settings-logout-form').boundingBox(),nav=await page.locator('.portal-nav').boundingBox();assert(last.y+last.height<=nav.y,'bottom clearance '+width);}
  }
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:lang==='en'?'Edit Profile':'پروفائل میں ترمیم',exact:true}).click();await snap('edit-'+lang+'-390');await page.getByRole('button',{name:lang==='en'?'Cancel':'منسوخ',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button',{name:new RegExp(lang==='en'?'App Language':'ایپ کی زبان')}).click();await snap('language-'+lang+'-390');await page.getByRole('button',{name:lang==='en'?'Cancel':'منسوخ',exact:true}).click();
  for(const route of ['settings','account/privacy/exports']){
   await page.goto(base+'/'+route);await expect(page.locator('.settings-intro h1')).toBeVisible();await page.waitForLoadState('networkidle');
   for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'privacy overflow '+route+lang+width);if(width===390)await snap(route==='settings'?'privacy-'+lang:'export-'+lang);}
  }
 }
 await ctx.addCookies([{name:'safereturn-language',value:'en',url:base}]);await page.setViewportSize({width:390,height:844});await page.goto(base+'/account');
 await page.getByRole('button',{name:'Edit Profile',exact:true}).click();await page.getByLabel('Your Name',{exact:true}).fill(' ');await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByText('Please enter your name.',{exact:true})).toBeVisible();assert.equal(writes.length,0);
 await page.getByLabel('Your Name',{exact:true}).fill('Updated Amina');slow=true;await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('button',{name:'Saving Changes…'})).toBeDisabled();slow=false;
 await expect(page).toHaveURL(/saved=1/);await expect(page.locator('.settings-profile h2')).toHaveText('Updated Amina');assert.deepEqual(writes[0].body,{display_name:'Updated Amina',preferred_locale:'en'});assert.equal(writes[0].version,'"0"');
 await page.getByRole('button',{name:'Edit Profile',exact:true}).click();await page.getByLabel('Your Name').fill('Draft after conflict');mode='stale';await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('button',{name:'Refresh Profile'})).toBeVisible();await expect(page.getByLabel('Your Name')).toHaveValue('Draft after conflict');await expect(page.getByRole('button',{name:'Save Changes',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Refresh Profile'}).click();await expect(page.locator('.settings-feedback[role=alert]')).toContainText('Current saved name: Changed Elsewhere');await expect(page.getByLabel('Your Name')).toHaveValue('Draft after conflict');await expect(page.getByRole('button',{name:'Save Changes',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);assert.equal(account.display_name,'Draft after conflict');
 await page.getByRole('button',{name:/App Language/}).click();await page.getByRole('radio',{name:'اردو',exact:true}).check();await page.getByRole('button',{name:'Save Changes',exact:true}).click();await expect(page.locator('.customer-portal:not(:has(.settings-loading))')).toHaveAttribute('dir','rtl');assert.deepEqual(writes.at(-1).body,{preferred_locale:'ur'});assert.equal(account.display_name,'Draft after conflict');
 await page.goto(base+'/account/shipping-addresses');await expect(page.locator('.customer-portal:not(:has(.settings-loading))')).toHaveAttribute('dir','rtl');
 await ctx.addCookies([{name:'safereturn-language',value:'en',url:base}]);await page.goto(base+'/account');await page.getByRole('link',{name:/Change Password/}).click();await page.getByLabel('Email address',{exact:true}).fill(user.email);await page.getByRole('button',{name:'Send reset link',exact:true}).click();await expect(page.getByRole('status')).toContainText('link will be emailed');assert(calls.includes('/auth/v1/recover'));
 account.email_verified=false;await page.goto(base+'/account');await expect(page.getByText('Email Not Verified',{exact:true})).toBeVisible();await page.getByRole('link',{name:'Verify Email',exact:true}).click();await page.getByLabel('Email address',{exact:true}).fill(user.email);await page.getByRole('button',{name:'Resend confirmation',exact:true}).click();await expect(page.getByRole('status')).toContainText('link will be emailed');account.email_verified=true;
 await page.goto(base+'/settings');await expect(page.locator('.settings-events li')).toHaveCount(2);await expect(page.getByText(/historical consent events/)).toBeVisible();await page.locator('.settings-deletion summary').click();await page.getByLabel('Reason (Optional)',{exact:true}).fill('Synthetic privacy review');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Submit Privacy Request',exact:true}).click();await expect(page.locator('.settings-feedback')).toContainText('saved for review');assert.deepEqual(writes.at(-1).deletion,{confirm:true,reason:'Synthetic privacy review'});
 historyMode='empty';await page.reload();await expect(page.getByRole('heading',{name:'No Privacy Changes Recorded'})).toBeVisible();historyMode='error';await page.reload();await expect(page.getByText('Privacy history couldn’t be loaded. Please try again.')).toBeVisible();historyMode='ok';await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.locator('.settings-events li')).toHaveCount(2);
 await page.goto(base+'/account/privacy/exports');await page.getByRole('button',{name:'Check Request Status',exact:true}).click();await expect(page.getByText('Enter a valid request reference.')).toBeVisible();
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Request My Data',exact:true}).click();await expect(page.locator('.settings-export-result')).toContainText('Requested');await expect(page.getByRole('button',{name:'Download Reviewed Data'})).toHaveCount(0);
 exportStage='ready';await page.getByRole('button',{name:'Check Request Status',exact:true}).click();await expect(page.locator('.settings-export-result')).toContainText('Ready to Download');await page.getByRole('checkbox').check();const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Download Reviewed Data'}).click();assert.equal((await downloading).suggestedFilename(),'safereturn-basic-v1.json');assert.equal(grantActive,false);assert(!page.url().includes('GRANT'));await expect(page.locator('body')).not.toContainText('FIXTURE-ONE-USE-GRANT');
 assert.equal((await page.request.get(base+'/account/privacy/exports/api?id='+id(999))).status(),404);assert.equal((await page.request.post(base+'/account/privacy/exports/api',{headers:{Origin:'https://hostile.invalid'},data:{action:'request',key:'synthetic-key',body:{scope:'basic_v1',confirmed:true}}})).status(),403);
 mode='profile-error';await page.goto(base+'/account');await expect(page.getByRole('heading',{name:'Couldn’t Load Account'})).toBeVisible();await snap('error');await expect(page.locator('body')).not.toContainText('PRIVATE_CANARY');mode='ok';await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.locator('section.settings-profile')).toBeVisible();
 slow=true;await page.goto(base+'/account?cold=1',{waitUntil:'commit'});await expect(page.locator('.settings-loading')).toBeVisible();await snap('loading');await expect(page.locator('.settings-profile h2')).toBeVisible();slow=false;
 await page.setViewportSize({width:320,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'large text overflow');await page.reload();await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>{localStorage.setItem('cart-canary','keep');sessionStorage.setItem('unrelated-canary','keep');});mode='logout-error';await page.getByRole('button',{name:'Log Out',exact:true}).click();
 await expect.poll(()=>new URL(page.url()).pathname==='/login'||new URL(page.url()).searchParams.get('logout')==='failed',{timeout:15000}).toBe(true);
 if(new URL(page.url()).pathname==='/login'){
  await expect(page.locator('section.settings-profile')).toHaveCount(0);
  mode='ok';await page.getByLabel('Email address').fill(user.email);await page.locator('input[name=password]').fill('fixture-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(base+'/account');
 }else await expect(page.locator('.settings-feedback.error')).toContainText('Log out couldn’t be completed');
 mode='ok';await page.goto(base+'/account?logout=failed');await expect(page.locator('.settings-feedback.error')).toContainText('Log out couldn’t be completed');
 mode='ok';await page.getByRole('button',{name:'Log Out',exact:true}).click();await expect(page).toHaveURL(/login$/);assert.equal(logoutScope,'global');assert.equal(active,false);await page.goto(base+'/account');await expect(page).toHaveURL(/login$/);assert.equal((await page.request.get(base+'/account/privacy/exports/api?id='+id(60))).status(),401);
 assert.deepEqual(await page.evaluate(()=>[localStorage.getItem('cart-canary'),sessionStorage.getItem('unrelated-canary')]),['keep','keep']);assert.deepEqual(errors,[]);
 console.log('PASS production account: 18 account plus 16 privacy/export EN/Urdu layouts; profile name validation, saving, If-Match conflict/review/retry, locale-only updates and shared RTL persistence, recovery/resend entry points, actual reviewed deletion request, consent history empty/error/retry, export request/status/one-use download, foreign ID and CSRF rejection, account skeleton/error, 200% text, global logout failure/success and preserved unrelated storage. Isolated authenticated HTTP fixtures, no live provider emails or real database.');
 }finally{await browser?.close();child?.kill();server.close();server.closeAllConnections();}
})().catch(e=>{console.error(e);process.exitCode=1});

