const {chromium,expect}=require('@playwright/test');
const {spawn}=require('node:child_process'),http=require('node:http'),assert=require('node:assert/strict');
const {setTimeout:delay}=require('node:timers/promises');
const base='http://127.0.0.1:3487',id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const user={id:id(1),email:'inbox@fixture.test',role:'authenticated',aud:'authenticated',app_metadata:{},user_metadata:{},created_at:'2026-01-01T00:00:00Z',email_confirmed_at:'2026-01-01T00:00:00Z'};
const token=[{alg:'HS256',typ:'JWT'},{sub:user.id,aud:'authenticated',role:'authenticated',exp:Math.floor(Date.now()/1000)+3600}].map(o=>Buffer.from(JSON.stringify(o)).toString('base64url')).concat('synthetic').join('.');
const messages=[
 {id:id(21),qr_id:id(11),qr_label:'Canvas Backpack · '+'Long personal QR name '.repeat(3),finder_name:'Ali Ahmed',tag_type:'lost',status:'new',submitted_at:'2026-11-22T10:42:00Z',notification_status:'sent'},
 {id:id(22),qr_id:id(12),qr_label:null,finder_name:null,tag_type:'ice',status:'viewed',submitted_at:'2026-11-21T10:00:00Z',notification_status:null},
 {id:id(23),qr_id:id(11),qr_label:'Everyday Keys',finder_name:'Sara',tag_type:'lost',status:'archived',submitted_at:'2026-11-20T10:00:00Z',notification_status:'sent'}
];
const body='<script>window.finderInjected=true</script>\nI found your bag.\n'+'LongMessageWithoutSpaces'.repeat(30);
let mode='ok',slow=false,calls=[],mutations=0;
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost'),p=url.pathname;
 const reply=(data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data))};
 if(p==='/auth/v1/token')return reply({user,access_token:token,refresh_token:'fixture-refresh',token_type:'bearer',expires_in:3600});
 if(req.headers.authorization!=='Bearer '+token)return reply({},401);
 if(p==='/auth/v1/user')return reply(user);
 if(p==='/api/v1/me')return reply({user_id:user.id,display_name:'Amina',preferred_locale:'en',version:'1',email_verified:true,masked_contact:{phone:null}});
 calls.push(req.method+' '+p+url.search);
 if(slow)await delay(900);
 if(p==='/api/v1/me/finder-messages'){
  const limit=+(url.searchParams.get('limit')||25);
  if(mode==='failed'&&limit===100)return reply({},503);
  let items=mode==='empty'?[]:messages.filter(m=>m.status!=='deleted'&&(!url.searchParams.get('status')||m.status===url.searchParams.get('status'))&&(!url.searchParams.get('qr_id')||m.qr_id===url.searchParams.get('qr_id')));
  return reply({items:items.slice(0,limit),next_cursor:mode==='pages'&&limit===100&&!url.searchParams.has('cursor')?'older-page':null});
 }
 if(p.startsWith('/api/v1/me/finder-messages/')){
  const m=messages.find(m=>p.endsWith(m.id)&&m.status!=='deleted');if(!m)return reply({},404);
  if(req.method==='PATCH'||req.method==='DELETE'){
   mutations++;if(mode==='mutation-failed')return reply({},503);
   if(req.method==='DELETE'){m.status='deleted';return reply({});}
   let data='';for await(const c of req)data+=c;m.status=JSON.parse(data).status;return reply({id:m.id,status:m.status});
  }
  return reply({...m,message:body,finder_email:m.finder_name?'ali@example.test':null,finder_phone:m.finder_name?'+923001234567':null,preferred_contact:m.finder_name?'email':null,location:m.finder_name?{latitude:31.5,longitude:74.3,accuracy_m:20,maps_url:'https://www.google.com/maps?q=31.5,74.3',consent_at:'2026-11-22T10:42:00Z'}:null});
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
 await page.goto(base+'/inbox');await expect(page).toHaveURL(/login/);
 await page.getByLabel('Email address').fill(user.email);await page.locator('input[name=password]').fill('fixture-password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).not.toHaveURL(/login$/);
 calls=[];await page.goto(base+'/inbox');await expect(page.locator('.finder-row')).toHaveCount(3);await page.waitForLoadState('networkidle');
 assert.equal(calls.filter(c=>c.includes('/me/finder-messages?')&&c.includes('limit=100')).length,1);
 assert.equal(calls.filter(c=>c.includes('/me/finder-messages?')&&c.includes('limit=5')).length,1);
 await expect(page.locator('.finder-unread-count')).toHaveText('1 Unread');await expect(page.locator('.header-bell .unread-dot')).toHaveCount(1);
 const snap=name=>page.screenshot({path:'test-results/inbox-'+name+'.png',fullPage:true});
 for(const lang of ['en','ur']){
  await ctx.addCookies([{name:'safereturn-language',value:lang,url:base}]);await page.goto(base+'/inbox');await expect(page.locator('.finder-row')).toHaveCount(3);await page.waitForLoadState('networkidle');
  for(const width of [320,360,375,390,412,430,768,1024,1440]){
   await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'inbox overflow '+lang+width);
   if([320,390,768,1440].includes(width))await snap(lang+'-'+width);
   assert.equal(await page.locator('.portal-nav a[href="/orders"]').getAttribute('aria-current'),null);
   await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
   if(width<800){const last=await page.locator('.finder-pagination').boundingBox(),nav=await page.locator('.portal-nav').boundingBox();assert(last.y+last.height<=nav.y,'bottom clearance '+width);}
  }
  await page.goto(base+'/inbox/'+id(21));await expect(page.locator('.finder-message-body')).toHaveText(body);await page.waitForLoadState('networkidle');
  for(const width of [320,360,375,390,412,430,768,1440]){
   await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'detail overflow '+lang+width);
   if([390,1440].includes(width)){await expect(page.locator('.finder-message-body')).toBeVisible();await snap('detail-'+lang+'-'+width);}
  }
 }
 await ctx.addCookies([{name:'safereturn-language',value:'en',url:base}]);await page.setViewportSize({width:390,height:844});await page.goto(base+'/inbox?status=new&qr_id='+id(11));
 await page.locator('.finder-row').click();await expect(page).toHaveURL(/status=new&qr_id=/);
 assert.equal(mutations,0,'opening details must not mutate read state');
 await expect(page.locator('a[href="mailto:ali@example.test"]')).toBeVisible();await expect(page.locator('a[href="tel:+923001234567"]')).toBeVisible();
 await expect(page.getByRole('link',{name:'View Shared Location'})).toHaveAttribute('href','https://www.google.com/maps?q=31.5,74.3');
 await expect(page.getByRole('link',{name:'View QR Details'})).toHaveAttribute('href','/my-qr/'+id(11));
 await expect(page.locator('.finder-detail-qr')).toContainText(messages[0].qr_label);assert.equal(await page.evaluate(()=>window.finderInjected),undefined);assert.equal(await page.locator('.finder-message-body script').count(),0);
 await page.getByRole('button',{name:'Mark as Read',exact:true}).click();await expect(page.getByRole('status')).toContainText('Changes saved');assert.equal(messages[0].status,'viewed');assert.equal(mutations,1);
 await page.getByRole('link',{name:'Back to Messages'}).click();await expect(page).toHaveURL(/status=new&qr_id=/);await expect(page.getByRole('heading',{name:'No Matching Messages'})).toBeVisible();
 await page.goto(base+'/inbox');await expect(page.locator('.finder-unread-count')).toHaveText('0 Unread');await expect(page.locator('.header-bell .unread-dot')).toHaveCount(0);
 await page.getByRole('link',{name:'Read',exact:true}).click();await expect(page.locator('.finder-row')).toHaveCount(2);
 await page.locator('.finder-row').first().click();await expect(page).toHaveURL(/status=viewed/);
 await page.getByLabel('Message Status',{exact:true}).selectOption('flagged');await page.getByRole('button',{name:'Save Status',exact:true}).click();await expect(page.getByRole('status')).toContainText('Changes saved');assert.equal(messages[0].status,'flagged');
 mode='mutation-failed';await page.getByLabel('Message Status',{exact:true}).selectOption('archived');await page.getByRole('button',{name:'Save Status',exact:true}).click();await expect(page.getByRole('status')).toContainText('could not be saved');assert.equal(messages[0].status,'flagged');
 mode='ok';await page.getByLabel('Message Status',{exact:true}).selectOption('archived');await page.getByRole('button',{name:'Save Status',exact:true}).click();await expect(page.getByRole('status')).toContainText('Changes saved');assert.equal(messages[0].status,'archived');
 await page.getByRole('button',{name:'Delete Message',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await snap('delete-dialog');
 await page.getByRole('button',{name:'Keep Message',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);assert.equal(messages[0].status,'archived');
 await page.getByRole('button',{name:'Delete Message',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Delete Message',exact:true}).click();await expect(page).toHaveURL(/status=viewed&result=deleted/);assert.equal(messages[0].status,'deleted');
 await page.goto(base+'/inbox/'+id(22));await expect(page.getByRole('heading',{name:'Anonymous Finder'})).toBeVisible();await expect(page.getByText('The finder did not share contact details.')).toBeVisible();await expect(page.locator('a[href^="mailto:"],a[href^="tel:"]')).toHaveCount(0);
 await page.goto(base+'/inbox/'+id(999));await expect(page.getByRole('heading',{name:'Message Unavailable'})).toBeVisible();await expect(page.locator('.finder-message-body')).toHaveCount(0);
 await page.goto(base+'/inbox/'+id(22)+'?qr_id='+id(999));await expect(page.getByRole('link',{name:'View QR Details'})).toHaveCount(0);mode='failed';await page.goto(base+'/inbox');await expect(page.getByRole('heading',{name:'Couldn’t Load Messages'})).toBeVisible();await snap('error');mode='empty';await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.getByRole('heading',{name:'No Finder Messages Yet'})).toBeVisible();await snap('empty');
 mode='pages';await page.reload();await expect(page.locator('.finder-row')).toHaveCount(2);await expect(page.getByRole('searchbox')).toHaveCount(0);await page.getByRole('link',{name:'Older Messages'}).click();await expect(page).toHaveURL(/cursor=older-page/);
 mode='ok';await page.goto(base+'/inbox');await page.getByRole('searchbox').fill('sara');await expect(page.locator('.finder-row')).toHaveCount(1);
 slow=true;await page.goto(base+'/inbox?cold=1',{waitUntil:'commit'});await expect(page.locator('.finder-loading')).toBeVisible();await snap('loading');await expect(page.locator('.finder-row')).toHaveCount(2);slow=false;
 await page.setViewportSize({width:320,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'large text overflow');
 assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
 assert.deepEqual(errors,[]);
 console.log('PASS production inbox: 18 inbox and 16 detail English/Urdu responsive layouts; auth redirect; one shared unread fetch; filters/search/pagination; manual read, flag/archive/delete and mutation failure; retained filters, unread refresh, safe contacts/consented map, escaped long content, missing contact/name, missing message, loading/error/retry/empty, bottom clearance and 200% text. Isolated authenticated HTTP fixtures, not live backend isolation.');
 }finally{await browser?.close();child?.kill();server.close();server.closeAllConnections();}
})().catch(e=>{console.error(e);process.exitCode=1});


