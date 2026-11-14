const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createHarness,id,row,event,token}=require('../tests/support-metadata-fixture.cjs');
(async()=>{
 let checks=0;const check=async(p,status)=>{const r=await p;assert.equal(r.status,status);assert.match(r.headers.get('cache-control'),/no-store/);checks++;return r;};
 const base='https://support.test/admin/support/metadata-api';
 const disabled=createHarness({admitted:false});
 for(const suffix of ['',`/${id(1)}`,`/${id(1)}/history`])for(const method of ['GET','HEAD','OPTIONS'])await check(disabled.dispatch(base+suffix+'?view=live&enabled=true',{method}),503);
 assert.equal(disabled.state.authCalls,0);assert.equal(disabled.state.staffCalls,0);assert.equal(disabled.state.calls.length,0);
 const h=createHarness(),s=h.state,c=h.load(path.resolve(__dirname,'../lib/admin-support-metadata.ts'));
 s.authorized=false;await check(h.dispatch(base),401);s.authorized=true;
 for(const roles of [['operations'],['finance'],['superadmin'],['security_admin'],[]]){s.roles=roles;await check(h.dispatch(base),403);}s.roles=['support'];
 s.mfa=false;await check(h.dispatch(base),403);s.mfa=true;s.capabilities=[];await check(h.dispatch(base),403);s.capabilities=['support.manage'];
 for(const q of ['path=/admin/support-cases','expand=content','event_limit=20','before_revision=2','limit=101','limit=01','limit=2&limit=3','status=unknown','priority=unknown','case_type=unknown','queue=other','case_id=bad','cursor=bad']){const n=s.calls.length;await check(h.dispatch(base+'?'+q),422);assert.equal(s.calls.length,n);}
 for(const q of ['case_type=privacy','status=closed','priority=urgent','queue=unassigned','queue=all','limit=100','case_id='+id(1),'cursor='+token])await check(h.dispatch(base+'?'+q),200);
 await check(h.dispatch(base+'/'+id(1)),200);await check(h.dispatch(base+'/'+id(1)+'/history'),200);await check(h.dispatch(base+'/'+id(2)+'/history'),404);await check(h.dispatch(base+'/'+id(999)),404);
 for(const suffix of ['',`/${id(1)}`,`/${id(1)}/history`]){s.malformed=true;const r=await check(h.dispatch(base+suffix),503);assert.doesNotMatch(await r.text(),/NEVER_RENDER/);s.malformed=false;}
 s.oversized=true;await check(h.dispatch(base),503);s.oversized=false;s.wrongId=true;await check(h.dispatch(base+'/'+id(1)),503);s.wrongId=false;
 for(const code of [400,401,403,404,409,422,429,500]){s.status=code;const r=await check(h.dispatch(base),code===500?503:code);assert.doesNotMatch(await r.text(),/NEVER_RENDER/);}s.status=0;
 for(const method of ['POST','PATCH','PUT','DELETE']){const r=await h.dispatch(base,{method});assert.equal(r.status,405);checks++;}
 for(const headers of [{Origin:'https://evil.test'},{'sec-fetch-site':'cross-site'},{'content-encoding':'gzip'}])await check(h.dispatch(base,{headers}),headers['content-encoding']?422:403);
 for(const suffix of ['?limit=1','?description=true'])await check(h.dispatch(base+'/'+id(1)+suffix),422);
 s.revoke=true;await check(h.dispatch(base),403);
 assert.throws(()=>c.supportDetail({...row(),content_available:true}));checks++;
 assert.throws(()=>c.supportHistory({case_id:id(1),case_revision:4,items:[event(2),event(4)],next_cursor:null}));checks++;
 assert.throws(()=>c.supportPage({as_of:'2026-10-24T00:00:00Z',items:[row(),row()],next_cursor:null}));checks++;
 for(const call of s.calls){assert.match(new URL(call.url).pathname,/^\/api\/v1\/admin\/support-case-metadata(?:\/[a-f0-9-]{36}(?:\/history)?)?$/);assert.equal(call.options.method,'GET');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');}
 const legacy=h.load(path.resolve(__dirname,'../app/admin/support/api/route.ts'));for(const method of ['GET','POST','PATCH','HEAD','OPTIONS'])await check(legacy[method](),503);
 for(const f of ['app/admin/support/page.tsx','app/admin/support/[caseId]/page.tsx','app/admin/support/new/page.tsx','components/admin-support-cases.tsx'])assert.doesNotMatch(fs.readFileSync(path.resolve(__dirname,'..',f),'utf8'),/SupportAdmin|admin-mock-data|localStorage|view=live/);
 console.log(`${checks} isolated Support metadata checks passed; disabled gate made zero auth/staff/upstream calls; no prohibited paths.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
