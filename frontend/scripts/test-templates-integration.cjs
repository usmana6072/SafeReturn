const assert=require('node:assert/strict'),path=require('node:path');
const {NextRequest}=require('next/server'),{createHarness,content,tid,rid,vid}=require('../tests/templates-fixture.cjs');
(async()=>{const h=createHarness(),s=h.state,c=h.load(path.resolve(__dirname,'../lib/admin-templates-contract.ts'));let checks=0;
const get=(p,q={})=>h.dispatch('https://templates.test/admin/templates/api?'+new URLSearchParams({path:p,...q}));
const send=(p,m,b,v,key='template-intent-0001')=>h.dispatch('https://templates.test/admin/templates/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,method:m,body:b,version:v,key})});
const status=async(p,n)=>{const r=await p;assert.equal(r.status,n);checks++;return r;},base='/admin/print-templates',rp=base+'/'+tid+'/revisions/'+rid;
s.authorized=false;await status(get(base),401);s.authorized=true;s.mfa=false;await status(get(base),403);s.mfa=true;s.role='support';await status(get(base),403);s.role='security_admin';await status(get(base),200);await status(send(base,'POST',{key:'test',name:'Test',purpose:'lost'}),403);s.role='operations';
await status(get(base),200);await status(get(base+'/'+tid),200);await status(get(base,{cursor:'opaque_next'}),200);
// Only synthetic inbound requests to the BFF: the following are rejected before upstream dispatch.
for(const p of ['/admin/qr-inventory/batches','/admin/qr-inventory/batches/'+tid,'/admin/qr-inventory/summary','/admin/qr-inventory/codes','/admin/qr-inventory/codes/'+tid,'/admin/orders/'+tid+'/qr-allocation','/admin/support-cases/'+tid+'/independent-qr','/admin/qr-batches','/admin/qr-pairs','/admin/reservations','/admin/assignments',rp+'/publish']){const before=s.calls.length;await status(get(p),422);await status(send(p,'POST',{},1),422);assert.equal(s.calls.length,before);}
for(const q of [{limit:'51'},{cursor:'../secret'},{search:'test'},{purpose:'pair'}])await status(get(base,q),422);
await status(h.relay.GET(new NextRequest('https://templates.test/admin/templates/api?path='+base+'&path='+base)),422);
await status(h.relay.POST(new NextRequest('https://templates.test/admin/templates/api',{method:'POST',headers:{Origin:'https://evil.test','Content-Type':'application/json'},body:'{}'})),403);
const b={key:'safe-design',name:'Safe design',purpose:'lost'};await status(send(base,'POST',b),201);await status(send(base,'POST',b),201);await status(send(base,'POST',{...b,name:'Changed'}),409);
await status(send(base,'POST',{...b,description:'unsupported'}),422);
for(const extra of [{renderer:'external'},{header:'https://unsafe.test'},{asset_set_id:'not-real'},{logo_mm:'8.00'},{urdu_lines:['Latin']}]){assert.throws(()=>c.design({...content(),...extra}));checks++;}
await status(send(base+'/'+tid+'/revisions','POST',{content:content(),version_note:'Initial draft',base_revision_id:null},1),201);
await status(send(rp,'PATCH',{content:content(),version_note:'Saved design'},1),200);
await status(send(rp+'/preview','POST',{expected_revision:1},2),422);
const pdf=await status(send(rp+'/preview','POST',{expected_revision:2},2),200);assert.equal(pdf.headers.get('content-type'),'application/pdf');assert.equal((await pdf.text()).slice(0,5),'%PDF-');
await status(send(rp+'/submit-qa','POST',{reason:'Ready for independent review'},2),200);
await status(send(rp+'/publish','POST',{approval_id:tid,confirmed:true},3),422);
await status(get('/admin/print-template-bindings',{variant_id:vid,tag_type:'lost'}),200);
await status(send('/admin/print-template-bindings','POST',{variant_id:vid,tag_type:'lost',revision_id:rid,expected_variant_version:1,expected_binding_id:null,confirmed:true},1),403);
await status(send(rp+'/retire','POST',{reason:'Retire requested',confirmed:true},3),403);
s.status=412;await status(send(rp,'PATCH',{content:content(),version_note:'Retained content'},3),412);s.status=403;const denied=await status(send(rp+'/preview','POST',{expected_revision:3},3),403);assert.equal((await denied.json()).error.code,'REAUTH_REQUIRED');s.status=503;await status(get(base),503);s.status=0;s.malformed=true;await status(get(base),503);s.malformed=false;
for(const call of s.calls){assert.doesNotMatch(call.path,/qr-inventory|qr-batches|qr-pairs|qr-allocation|independent-qr|reservation|assignment|credential|export|\/publish/);c.templateTarget(call.path,call.method);assert.equal(call.options.cache,'no-store');if(call.method!=='GET'){assert.equal(call.options.headers.Origin,'https://templates.test');assert.ok(call.options.headers['Idempotency-Key']);}}
console.log(`${checks} template relay/contract checks passed; ${s.calls.length} upstream requests strictly allowed; zero excluded requests.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
