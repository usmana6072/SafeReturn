const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {createHarness,id,row,cursor}=require('../tests/privacy-metadata-fixture.cjs');
(async()=>{
  let checks=0;const check=async(p,status)=>{const r=await p;assert.equal(r.status,status);assert.match(r.headers.get('cache-control'),/no-store/);checks++;return r;};
  const base='https://privacy.test/admin/privacy/exports/api';
  const disabled=createHarness({admitted:false});await check(disabled.dispatch(base+'?view=live&enabled=true'),503);
  for(const method of ['POST','PUT','PATCH','DELETE','HEAD','OPTIONS'])await check(disabled.dispatch(base,{method}),405);
  assert.equal(disabled.state.authCalls,0);assert.equal(disabled.state.staffCalls,0);assert.equal(disabled.state.calls.length,0);
  const h=createHarness(),s=h.state,c=h.load(path.resolve(__dirname,'../lib/admin-privacy-metadata.ts'));
  s.authorized=false;await check(h.dispatch(base),401);s.authorized=true;
  for(const roles of [['operations'],['support'],['finance'],['superadmin'],[]]){s.roles=roles;await check(h.dispatch(base),403);}s.roles=['security_admin'];
  s.mfa=false;await check(h.dispatch(base),403);s.mfa=true;s.capabilities=[];await check(h.dispatch(base),403);s.capabilities=['privacy.exports'];
  for(const query of ['status=ready','id='+id(1),'case_id='+id(2),'path=/admin/support-cases','action=decisions','download=true','view=live','limit=0','limit=01','limit=101','limit=1&limit=2','cursor=bad','limit=1.1','cursor='+('a'.repeat(201))]){const n=s.calls.length;await check(h.dispatch(base+'?'+query),422);assert.equal(s.calls.length,n);}
  for(const query of ['','?limit=1','?limit=100','?cursor='+cursor]){const r=await check(h.dispatch(base+query),200),text=await r.text();assert.doesNotMatch(text,/NEVER_RENDER|categories|manifest_id|source_count|private_payload/);}
  s.rows=[];const empty=await check(h.dispatch(base),200);assert.equal((await empty.json()).items.length,0);s.rows=[row(1),row(2),row(3)];
  for(const decision of ['approve','reject','escalate','invalid'])for(const revision of [0,1,2147483647]){const n=s.calls.length;await check(h.dispatch(base,{method:'POST',headers:{Origin:'https://privacy.test','Content-Type':'application/json'},body:JSON.stringify({action:'decisions',id:id(1),body:{decision,expected_revision:revision,confirmed:true}})}),405);assert.equal(s.calls.length,n);}
  for(const headers of [{Origin:'https://evil.test'},{'Sec-Fetch-Site':'cross-site'},{'Content-Encoding':'gzip'},{'Content-Length':'1'}])await check(h.dispatch(base,{headers}),headers['Content-Encoding']||headers['Content-Length']?422:403);
  for(const code of [400,401,403,404,409,412,422,429,500]){s.status=code;const r=await check(h.dispatch(base),[409,412,500].includes(code)?503:code);assert.doesNotMatch(await r.text(),/NEVER_RENDER/);}s.status=0;
  for(const flag of ['malformed','oversized','network','attachment']){s[flag]=true;const r=await check(h.dispatch(base),503);assert.doesNotMatch(await r.text(),/NEVER_RENDER/);s[flag]=false;}
  s.revoke=true;await check(h.dispatch(base),403);s.revoke=false;s.roles=['security_admin'];
  const projected=c.projectExportPage({items:[row()],next_cursor:null});assert.equal(Object.keys(projected.items[0]).length,8);assert.throws(()=>c.exportPage({items:[row()],next_cursor:null}));checks+=2;
  for(const change of [{status:'complete'},{revision:0},{revision:1.5},{scope_version:'all_data'},{created_at:'bad'},{case_id:'bad'}]){assert.throws(()=>c.projectExportPage({items:[{...row(),...change}],next_cursor:null}));checks++;}
  assert.throws(()=>c.projectExportPage({items:[row(),row()],next_cursor:null}));checks++;
  for(const call of s.calls){assert.equal(new URL(call.url).pathname,'/api/v1/admin/privacy/exports');assert.equal(call.options.method,'GET');assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');}
  const gate=h.load(path.resolve(__dirname,'../lib/privacy-metadata-gate.ts'));assert.equal(gate.privacyMetadataAdmitted(),false);
  for(const file of ['app/admin/privacy/exports/page.tsx','app/admin/privacy/exports/[requestId]/page.tsx','app/admin/privacy/exports/api/route.ts','components/admin-privacy-requests.tsx'])assert.doesNotMatch(fs.readFileSync(path.resolve(__dirname,'..',file),'utf8'),/\bPrivacyExports\b|privacy-export-relay|admin-mock-data|localStorage|sessionStorage|view=live/);
  console.log(`${checks} isolated Privacy metadata checks passed; API-327 and all other mutations blocked with zero upstream calls.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
