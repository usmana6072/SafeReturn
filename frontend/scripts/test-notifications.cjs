const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {createHarness,row,id,template,token}=require('../tests/notification-fixture.cjs');
(async()=>{
  let checks=0;
  const check=async(p,status)=>{const r=await p;assert.equal(r.status,status);assert.match(r.headers.get('cache-control'),/no-store/);checks++;return r;};
  const base='https://notifications.test/admin/notifications/api';
  const input={id:id(1),key:'synthetic-key-0001',body:{expected_attempt_count:3,reason:'provider_recovered',confirmed:true}};
  const post=(h,value=input,headers={})=>h.dispatch(base,{method:'POST',headers:{Origin:'https://notifications.test','Content-Type':'application/json',...headers},body:JSON.stringify(value)});
  const disabled=createHarness({admitted:false});
  for(const method of ['GET','POST','HEAD','OPTIONS','DELETE'])await check(disabled.dispatch(base+'?view=live&enabled=true',{method}),503);
  assert.equal(disabled.state.authCalls,0);assert.equal(disabled.state.staffCalls,0);assert.equal(disabled.state.calls.length,0);
  const retryDisabled=createHarness({retry:false});await check(post(retryDisabled),503);assert.equal(retryDisabled.state.authCalls,0);assert.equal(retryDisabled.state.calls.length,0);
  const h=createHarness(),s=h.state,c=h.load(path.resolve(__dirname,'../lib/admin-notification-contract.ts'));
  s.authorized=false;await check(h.dispatch(base),401);s.authorized=true;
  for(const roles of [['finance'],['support'],['superadmin'],[]]){s.roles=roles;await check(h.dispatch(base),403);await check(post(h),403);}s.roles=['operations'];
  s.mfa=false;await check(h.dispatch(base),403);s.mfa=true;s.capabilities=[];await check(post(h),403);s.capabilities=['notifications.manage'];
  for(const q of ['path=/admin/orders','channel=email','status=delivered','limit=0','limit=01','limit=101','limit=1&limit=2','id=DEMO-NTF-001','cursor=bad','attempt_before=2','id='+id(1)+'&status=dead','attempt_limit=1.1']){const n=s.calls.length;await check(h.dispatch(base+'?'+q),422);assert.equal(s.calls.length,n);}
  for(const q of ['status=dead','limit=100','cursor='+token,'id='+id(1),'id='+id(1)+'&attempt_before=2'])await check(h.dispatch(base+'?'+q),200);
  s.rows=[];const empty=await check(h.dispatch(base),200);assert.equal((await empty.json()).items.length,0);s.rows=[row(1),row(2),row(3)];
  for(const headers of [{Origin:'https://evil.test'},{'Sec-Fetch-Site':'cross-site'},{'Content-Encoding':'gzip'}])await check(h.dispatch(base,{headers}),headers['Content-Encoding']?422:403);
  for(const bad of [{...input,extra:true},{...input,id:'bad'},{...input,key:'short'},{...input,body:{...input.body,confirmed:false}},{...input,body:{...input.body,reason:'send_now'}},{...input,body:{...input.body,expected_attempt_count:0}},{...input,body:{...input.body,expected_attempt_count:'3'}},{...input,body:{...input.body,email:'NEVER_RENDER'}}]){const n=s.calls.length;await check(post(h,bad),422);assert.equal(s.calls.length,n);}
  await check(post(h,input,{Origin:'https://evil.test'}),403);await check(post(h,{...input,key:'x'.repeat(2200)}),422);
  for(const status of [400,401,403,404,409,412,422,429,500]){s.status=status;const r=await check(h.dispatch(base),status===500?503:status);assert.doesNotMatch(await r.text(),/NEVER_RENDER/);}s.status=0;
  s.malformed=true;const malformed=await check(h.dispatch(base),503);assert.doesNotMatch(await malformed.text(),/NEVER_RENDER/);s.malformed=false;
  s.oversized=true;await check(h.dispatch(base),503);s.oversized=false;
  s.network=true;await check(h.dispatch(base),503);s.network=false;
  s.wrongId=true;await check(h.dispatch(base+'?id='+id(1)),503);s.wrongId=false;
  await check(post(h,{...input,body:{...input.body,expected_attempt_count:2}}),412);
  await check(post(h),202);await check(post(h),202);assert.equal(s.receipts.size,1);
  await check(post(h,{...input,body:{...input.body,reason:'recipient_reverified'}}),409);
  s.revoke=true;await check(h.dispatch(base),403);s.revoke=false;s.roles=['operations'];
  for(const method of ['HEAD','OPTIONS','PUT','PATCH','DELETE'])await check(h.dispatch(base,{method}),405);
  for(const data of [{items:[{...row(),provider_message_id:'SECRET'}],next_cursor:null,current_template:template},{items:[row(),row()],next_cursor:null,current_template:template},{items:[row()],next_cursor:'bad',current_template:template}]){assert.throws(()=>c.notificationPage(data));checks++;}
  for(const call of s.calls){assert.match(new URL(call.url).pathname,/^\/api\/v1\/admin\/notification-outbox(?:\/[a-f0-9-]{36}\/retry)?$/);assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');if(call.options.method==='POST')assert.equal(call.options.headers['Idempotency-Key'],input.key);}
  const gate=h.load(path.resolve(__dirname,'../lib/notification-gate.ts'));assert.equal(gate.notificationReadAdmitted(),false);assert.equal(gate.notificationRetryAdmitted(),false);
  for(const file of ['app/admin/notifications/page.tsx','app/admin/notifications/[id]/page.tsx','components/admin-notifications.tsx'])assert.doesNotMatch(fs.readFileSync(path.resolve(__dirname,'..',file),'utf8'),/NotificationAdmin\b|admin-mock-data|localStorage|sessionStorage|view=live/);
  console.log(`${checks} isolated Notifications contract/relay checks passed; no real network, Auth, DB, provider or prohibited routes.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
