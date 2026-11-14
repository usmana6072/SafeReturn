/* Synthetic parser/relay/actual-component browser harness. No HTTP listener. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const ts=require('typescript'),{NextRequest}=require('next/server'),{chromium,expect}=require('@playwright/test');
const root=path.resolve(__dirname,'..'),out=path.resolve(root,'../output/task57c/browser');fs.mkdirSync(out,{recursive:true});
const origin='https://users.synthetic.invalid',upstream='https://users-api.synthetic.invalid',privateCanary='PRIVATE_USERS_CONSOLE_CANARY',uid='00000000-0000-0000-0000-000000000001',cid='00000000-0000-0000-0000-000000000002',eid='00000000-0000-0000-0000-000000000003';
let checks=0;const check=(name,fn)=>{fn();checks++;};
function compile(file,requireImpl,globals={}){const sandbox={exports:{},require:requireImpl,...globals};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,sandbox);return sandbox.exports;}
const contract=compile(path.join(root,'lib/users-contract.ts'),()=>{throw Error('Unexpected import');});
const user={user_id:uid,registered_at:new Date().toISOString(),email_verified:true,provider_access:'not_banned'};
const filters={user_id:null,email_verified:null,provider_access:null};
const page=()=>({as_of:new Date().toISOString(),items:[user],next_cursor:null});
const total=()=>({as_of:new Date().toISOString(),definition:'retained_nonanonymous_auth_registrations_v1',filters,count:{value:1000,is_exact:false}});
const detail=(state='active',revision=1,enabled=true)=>({as_of:new Date().toISOString(),user,application_suspension:{status:'ready',state,revision,as_of:new Date().toISOString(),commands_available:enabled}});
const body={case_id:cid,expected_revision:1,reason_code:'security_review',confirmed:true};
const receipt=()=>({user_id:uid,case_id:cid,action:'suspend',revision:2,event_id:eid,occurred_at:new Date().toISOString(),state:'suspended',fresh_sign_in_required:true});
function parsers(){
 check('page',()=>assert.equal(contract.parsePage(page(),20).items.length,1));check('detail',()=>assert.equal(contract.parseDetail(detail(),uid).application_suspension.revision,1));check('count',()=>assert.equal(contract.parseTotal(total(),filters).count.is_exact,false));
 const fail=(name,v,fn)=>check(name,()=>assert.throws(()=>fn(v)));
 for(const [name,make]of [['extra',v=>({...v,private:privateCanary})],['private nested',v=>({...v,user:{...user,email:privateCanary}})],['wrong subject',v=>({...v,user:{...user,user_id:cid}})],['unknown state',v=>({...v,application_suspension:{status:'unavailable',reason_code:'NOT_IMPLEMENTED'}})],['string revision',v=>({...v,application_suspension:{...v.application_suspension,revision:'1'}})],['invalid date',v=>({...v,as_of:'2026-02-30T10:00:00Z'})]])fail(name,make(detail()),v=>contract.parseDetail(v,uid));
 fail('duplicate ids',{...page(),items:[user,user]},v=>contract.parsePage(v,20));fail('false exact cap',{...total(),count:{value:1000,is_exact:true}},v=>contract.parseTotal(v,filters));fail('count wrong filters',{...total(),filters:{...filters,user_id:cid}},v=>contract.parseTotal(v,filters));
 for(const v of [{...body,confirmed:1},{...body,email:privateCanary},{...body,expected_revision:true},{...body,reason_code:'bad'}])fail('closed command',v,x=>contract.parseCommand(x,'suspend'));
 check('receipt',()=>assert.equal(contract.parseReceipt(receipt(),'suspend',uid,body).event_id,eid));fail('wrong receipt revision',{...receipt(),revision:3},v=>contract.parseReceipt(v,'suspend',uid,body));
 const nav=compile(path.join(root,'lib/auth/staff-contract.ts'),()=>{}),mfa=compile(path.join(root,'lib/auth/mfa-return.ts'),()=>{});
 check('users nav',()=>assert.equal(nav.permittedModules({roles:['security_admin'],mfa_verified:true,capabilities:['users.manage']})[0].path,'/admin/users'));
 check('MFA exact return',()=>assert.equal(mfa.mfaReturn('/admin/users'),'/admin/users'));
 for(const p of ['/admin/users/'+uid,'/admin/users?returnTo=https://evil.invalid','https://evil.invalid','//evil.invalid'])check('reject unsafe return',()=>assert.equal(mfa.mfaReturn(p),'/account'));
 console.log('PASS '+checks+' contract/navigation checks');
}
async function relays(){
 let session=null,mfa=true,roles=['security_admin'],mode='valid',calls=[],staffFailure=0;
 class StaffAccessError extends Error{constructor(status){super('safe');this.status=status;}}
 const relay=compile(path.join(root,'lib/api/users-relay.ts'),name=>{
  if(name==='server-only')return{};if(name==='next/server')return require(name);
  if(name==='../auth/server')return{verifiedSession:async()=>session};
  if(name==='../auth/staff')return{StaffAccessError,staffState:async()=>{if(staffFailure)throw new StaffAccessError(staffFailure);return{roles,mfa_verified:mfa};}};
  if(name==='../auth/config')return{authConfig:()=>({origin})};if(name==='./transport')return{validateOrigin:v=>{assert.equal(v,upstream);return v;}};if(name==='../users-contract')return contract;throw Error(name);
 },{AbortSignal,TextDecoder,URLSearchParams,process:{env:{SAFERETURN_API_ORIGIN:upstream}},fetch:async(url,options)=>{
  calls.push({url,options});const u=new URL(url);let data=options.method==='POST'?receipt():u.pathname.endsWith('/count')?total():u.pathname.endsWith(uid)?detail():page();
  if(options.method==='POST'){const b=JSON.parse(options.body);if(u.pathname.endsWith('/restorations'))data={...receipt(),action:'restore',state:'active',revision:b.expected_revision+1};if(u.pathname.endsWith('/recovery-escalations')){data={user_id:uid,case_id:cid,action:'recovery_escalated',revision:b.expected_revision+1,event_id:eid,occurred_at:new Date().toISOString(),status:'referred'};}}
  if(mode==='network')throw Error(privateCanary);if(mode==='private')data.private=privateCanary;
  if(mode==='revoke')roles=['finance'];
  return new Response(mode==='oversize'?'x'.repeat(65537):JSON.stringify(mode==='denied'?{error:{code:'REAUTH_REQUIRED',message:privateCanary}}:data),{status:mode==='denied'?403:mode==='down'?503:options.method==='POST'&&u.pathname.endsWith('/recovery-escalations')?202:200,headers:{'Content-Type':mode==='mime'?'text/html':'application/json'}});
 }}).usersRelay;
 const req=(q='kind=list',method='GET',data,headers={})=>new NextRequest(origin+'/admin/users/api?'+q,{method,headers:{...(method==='POST'?{'Origin':origin,'Content-Type':'application/json','Idempotency-Key':'synthetic-command-key'}:{}),...headers},...(data!==undefined?{body:typeof data==='string'?data:JSON.stringify(data)}:{})});
 assert.equal((await relay(req())).status,401);session={token:'synthetic-only-token'};
 for(const role of ['superadmin','support','operations','finance']){roles=[role];assert.equal((await relay(req())).status,403);}roles=['security_admin'];mfa=false;assert.equal((await relay(req())).status,403);mfa=true;
 for(const q of ['kind=list&url=https://evil.invalid','kind=list&kind=count','kind=../other','kind=list&user_id=bad','kind=list&limit=101','kind=count&cursor=c2','kind=detail','kind=detail&user_id='+uid+'&include=anything'])assert.equal((await relay(req(q))).status,422);
 assert.equal(calls.length,0);
 let r=await relay(req());assert.equal(r.status,200);assert.equal(r.headers.get('cache-control'),'private, no-store');assert.equal(calls.at(-1).options.redirect,'error');assert.equal(calls.at(-1).options.cache,'no-store');assert.equal(calls.at(-1).options.headers.Authorization,'Bearer synthetic-only-token');assert.equal((await r.text()).includes('synthetic-only-token'),false);
 r=await relay(req('kind=detail&user_id='+uid));assert.equal(r.status,200);assert.equal(calls.at(-1).url,upstream+'/api/v1/admin/users/'+uid+'?include=account_security');
 r=await relay(req('kind=count'));assert.equal(r.status,200);
 r=await relay(req('kind=suspend&user_id='+uid,'POST',body));assert.equal(r.status,200);assert.equal(calls.at(-1).options.headers.Origin,origin);assert.equal(calls.at(-1).options.headers['Idempotency-Key'],'synthetic-command-key');assert.equal(calls.at(-1).url,upstream+'/api/v1/admin/users/'+uid+'/suspensions');
 r=await relay(req('kind=restore&user_id='+uid,'POST',{...body,expected_revision:2,reason_code:'review_cleared'}));assert.equal(r.status,200);assert(calls.at(-1).url.endsWith('/restorations'));
 r=await relay(req('kind=recovery&user_id='+uid,'POST',{...body,expected_revision:2,reason_code:'factor_loss'}));assert.equal(r.status,202);assert(calls.at(-1).url.endsWith('/recovery-escalations'));
 for(const raw of [{...body,confirmed:false},{...body,private:privateCanary},'x'.repeat(2049)])assert.equal((await relay(req('kind=suspend&user_id='+uid,'POST',raw))).status,422);
 assert.equal((await relay(req('kind=suspend&user_id='+uid,'POST',body,{Origin:'https://evil.invalid'}))).status,403);
 assert.equal((await relay(req('kind=suspend&user_id='+uid,'POST',body,{'Idempotency-Key':'bad'}))).status,400);
 for(const fault of ['private','network','oversize','mime','down']){mode=fault;r=await relay(req());assert.equal(r.status,503);assert.equal((await r.text()).includes(privateCanary),false);}
 mode='denied';r=await relay(req());assert.equal(r.status,403);assert.equal((await r.json()).error.code,'REAUTH_REQUIRED');
 mode='revoke';r=await relay(req());assert.equal(r.status,403);roles=['security_admin'];mode='valid';
 for(const status of [401,403]){staffFailure=status;assert.equal((await relay(req())).status,status);}staffFailure=0;
 console.log('PASS relay: fixed targets, auth/MFA/role/recheck, Origin, UUID/query/body limits, idempotency, redirect/cache/DTO/error/canaries');
}
async function serverRendering(){
 const React=require('react'),{renderToString}=require('react-dom/server');
 const Component=compile(path.join(root,'components/user-directory.tsx'),name=>{
  if(name==='next/link')return{default:({href,children})=>React.createElement('a',{href},children),__esModule:true};
  if(name==='../lib/users-contract')return contract;if(name.endsWith('.css'))return{console:'console'};return require(name);
 },{fetch:()=>{throw Error('No SSR account fetch allowed');}}).UserDirectory;
 const html=renderToString(React.createElement(Component,{id:uid,ur:false}));assert.equal(html.includes(privateCanary),false);assert.equal(html.includes('synthetic-only-token'),false);assert.equal(html.includes('disabled'),true);
 let roles=[],mfa=true;
 const fakeAdmin={AdminPage:({children})=>mfa?children({roles,capabilities:['users.manage']},false):React.createElement('div',null,'Denied'),AdminNotice:()=>React.createElement('div',null,'Denied')};
 const pageModule=compile(path.join(root,'app/admin/users/[userId]/page.tsx'),name=>{
  if(name==='next/navigation')return{notFound:()=>{throw Error('not-found');}};
  if(name.endsWith('/admin-page'))return fakeAdmin;if(name.endsWith('/user-directory'))return{UserDirectory:()=>React.createElement('div',null,'CONSOLE')};if(name.endsWith('/users-contract'))return contract;return require(name);
 });
 for(const role of ['security_admin','superadmin','support','operations','finance']){roles=[role];const element=await pageModule.default({params:Promise.resolve({userId:uid})});assert.equal(renderToString(element).includes('CONSOLE'),role==='security_admin');}
 roles=['security_admin'];mfa=false;assert.equal(renderToString(await pageModule.default({params:Promise.resolve({userId:uid})})).includes('CONSOLE'),false);
 console.log('PASS server component projection: no SSR account fetch/token/private content; actual detail-page role branch and shared-shell MFA refusal (session shell simulated, integrated Next/Auth/RSC remains a gate)');
}
async function browserChecks(){
 const modules=path.join(root,'node_modules'),component=path.join(root,'components/user-directory').replaceAll('\\','/');
 fs.writeFileSync(path.join(out,'loader.cjs'),`const ts=require(${JSON.stringify(path.join(modules,'typescript'))});module.exports=source=>ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;`);
 fs.writeFileSync(path.join(out,'css-loader.cjs'),`module.exports=source=>'module.exports='+JSON.stringify(Object.fromEntries([...source.matchAll(/\\.([a-zA-Z][\\w-]*)/g)].map(m=>[m[1],m[1]])));`);
 fs.writeFileSync(path.join(out,'link.tsx'),`import React from'react';export default function Link({href,children,...props}){delete props.prefetch;return <a href={href} {...props}>{children}</a>}`);
 fs.writeFileSync(path.join(out,'entry.tsx'),`import React from'react';import{createRoot}from'react-dom/client';import{UserDirectory}from'${component}';const root=createRoot(document.getElementById('root'));let k=0;window.show=(ur=false,id)=>root.render(<UserDirectory key={++k} ur={ur} id={id} canAudit/>);window.show(false,location.pathname.match(/users\\/([0-9a-f-]{36})$/)?.[1]);`);
 const webpack=require('next/dist/compiled/webpack/webpack').webpack;
 await new Promise((resolve,reject)=>webpack({mode:'development',devtool:false,entry:path.join(out,'entry.tsx'),output:{path:out,filename:'bundle.js'},resolve:{extensions:['.tsx','.ts','.js'],modules:[modules],alias:{'next/link':path.join(out,'link.tsx')}},module:{rules:[{test:/\.tsx?$/,use:path.join(out,'loader.cjs')},{test:/\.css$/,use:path.join(out,'css-loader.cjs')}]}},(e,stats)=>e||stats.hasErrors()?reject(e||Error(stats.toString({all:false,errors:true}))):resolve()));
 const browser=await chromium.launch({headless:true});
 try{
  const p=await browser.newPage({viewport:{width:390,height:844}}),errors=[],writes=[],reads=[];p.setDefaultTimeout(12000);p.on('pageerror',e=>errors.push(e.message));
  let mode='ready',state='active',revision=1,listedId=uid,releaseRead=null,readHeld=false;
  await p.route('**/*',async route=>{const u=new URL(route.request().url());assert.equal(u.origin,origin);
   if(u.pathname==='/bundle.js')return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(out,'bundle.js'))});
   if(u.pathname==='/style.css')return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(root,'components/user-directory.module.css'))});
   if(u.pathname==='/admin/users/api'){
    const kind=u.searchParams.get('kind');
    if(route.request().method()==='POST'){
     const payload=route.request().postDataJSON();writes.push({key:route.request().headers()['idempotency-key'],payload});
     if(mode==='reauth')return route.fulfill({status:403,json:{error:{code:'REAUTH_REQUIRED'}}});
     state='suspended';revision=2;
     if(mode==='unknown')return route.fulfill({status:503,json:{error:{code:'SERVICE_UNAVAILABLE'},private:privateCanary}});
     return route.fulfill({json:receipt()});
    }
    reads.push(u.searchParams.toString());
    if(mode==='denied')return route.fulfill({status:403,json:{error:{code:'FORBIDDEN'}}});
    if(mode==='down')return route.fulfill({status:503,json:{error:{code:'SERVICE_UNAVAILABLE'}}});
    const v=kind==='detail'?detail(state,revision,mode!=='disabled'):kind==='count'?total():page();
    if(kind==='detail'&&mode==='unavailable')v.application_suspension={status:'unavailable',reason_code:'STATE_UNAVAILABLE'};
    if(kind==='list')v.items=v.items.map(u=>({...u,user_id:listedId}));
    if(mode==='empty'){if(kind==='list')v.items=[];if(kind==='count')v.count={value:0,is_exact:true};}
    if(kind==='list'&&mode==='slow'){readHeld=true;await new Promise(resolve=>releaseRead=resolve);return route.fulfill({json:v}).catch(()=>{});}
    if(kind==='list'&&mode==='private')v.items[0]={...user,email:privateCanary};
    return route.fulfill({json:v});
   }
   return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script src="/bundle.js"></script></body></html>'});
  });
  await p.goto(origin+'/admin/users');await expect(p.getByRole('heading',{name:'User directory',exact:true})).toBeVisible();await expect(p.getByText('1000+',{exact:true})).toBeVisible();await expect(p.getByRole('link',{name:'Review account',exact:true})).toHaveAttribute('href','/admin/users/'+uid);
  await p.getByLabel('Email verification filter').selectOption('true');await expect(p.getByText('1000+',{exact:true})).toHaveCount(0);
  // Return a matching count filter for subsequent independent parser checks.
  filters.email_verified=true;
  await p.getByRole('button',{name:'Search / reset paging',exact:true}).click();await expect(p.getByText('1000+',{exact:true})).toBeVisible();assert(reads.some(q=>q.includes('email_verified=true')));
  mode='private';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByRole('link',{name:'Review account',exact:true})).toHaveCount(0);assert.equal((await p.content()).includes(privateCanary),false);
  mode='empty';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByText('No accounts match these filters.',{exact:true})).toBeVisible();await expect(p.getByText('0',{exact:true})).toBeVisible();
  mode='down';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByText('0',{exact:true})).toHaveCount(0);
  mode='slow';await p.getByRole('button',{name:'Refresh account information'}).click();await expect.poll(()=>readHeld).toBe(true);mode='ready';listedId=cid;await p.getByLabel('Email verification filter').selectOption('false');filters.email_verified=false;await p.getByRole('button',{name:'Search / reset paging',exact:true}).click();await expect(p.getByRole('link',{name:'Review account',exact:true})).toHaveAttribute('href','/admin/users/'+cid);releaseRead();await p.waitForTimeout(50);await expect(p.getByRole('link',{name:'Review account',exact:true})).toHaveAttribute('href','/admin/users/'+cid);
  listedId=uid;mode='ready';await p.goto(origin+'/admin/users/'+uid);await expect(p.getByText('Active · Revision 1',{exact:true})).toBeVisible();await expect(p.getByRole('button',{name:'Submit confirmed request'})).toBeDisabled();
  mode='disabled';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByLabel('Case UUID')).toBeDisabled();mode='unavailable';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByLabel('Case UUID')).toBeDisabled();
  mode='ready';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByLabel('Case UUID')).toBeEnabled();
  await p.getByLabel('Case UUID').fill(cid);await p.getByLabel('Action',{exact:true}).selectOption('suspend');await p.getByLabel('Reason',{exact:true}).selectOption('security_review');await p.getByRole('checkbox').check();assert.equal(writes.length,0);
  mode='unknown';await p.getByRole('button',{name:'Submit confirmed request'}).click();await expect(p.getByRole('alert')).toContainText('Outcome unknown');assert.equal(writes.length,1);await expect(p.getByRole('button',{name:'Retry same confirmed request'})).toBeDisabled();
  mode='ready';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByText('Suspended · Revision 2',{exact:true})).toBeVisible();await p.getByRole('button',{name:'Retry same confirmed request'}).click();await expect(p.getByRole('heading',{name:'Operation receipt — not current state'})).toBeVisible();assert.equal(writes.length,2);assert.deepEqual(writes[0],writes[1]);await expect(p.getByLabel('Action',{exact:true})).toHaveValue('');await expect(p.getByLabel('Reason',{exact:true})).toHaveValue('');
  mode='denied';await p.getByRole('button',{name:'Refresh account information'}).click();await expect(p.getByRole('alert')).toContainText('Access denied');await expect(p.getByText(eid,{exact:true})).toHaveCount(0);assert.equal(await p.getByLabel('Case UUID').inputValue(),'');
  mode='ready';state='active';revision=1;await p.evaluate(id=>window.show(true,id),uid);await expect(p.getByRole('heading',{name:'اکاؤنٹ کا جائزہ',exact:true})).toBeVisible();await p.setViewportSize({width:320,height:844});await expect(p.locator('main')).toHaveAttribute('dir','rtl');assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await p.getByRole('button',{name:'اکاؤنٹ معلومات تازہ کریں'}).focus();assert.equal(await p.evaluate(()=>document.activeElement.tagName),'BUTTON');
  assert.deepEqual(await p.evaluate(()=>[localStorage.length,sessionStorage.length]),[0,0]);assert.equal((await p.content()).includes(privateCanary),false);await p.screenshot({path:path.join(out,'users-ur-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS actual component browser: filter clearing/count caps/private canary, disabled/unavailable state, explicit confirmation, uncertain outcome with same-key retry, receipt vs state, authorization clearing, Urdu/RTL320px/focus/no storage; all network intercepted, no listener');
 }finally{await browser.close();}
}
(async()=>{if(!process.argv.includes('--browser-only')){parsers();await relays();await serverRendering();}if(!process.argv.includes('--contract-only'))await browserChecks();})().catch(e=>{console.error(e);process.exitCode=1;});
