/* Actual TS parsers/relay, synthetic memory/session only. No environment writes. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const {NextRequest}=require('next/server'),root=path.resolve(__dirname,'..');
function compile(file,require,globals={}){const box={exports:{},require,...globals};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{fileName:file,compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText,box);return box.exports;}
const returns=compile('lib/auth/mfa-return.ts',()=>{throw Error();});assert.equal(returns.mfaReturn('/admin/payments/review'),'/admin/payments/review');assert.equal(returns.mfaReturn('https://other.invalid'),'/account');
const A=compile('lib/allocation.ts',()=>{throw Error();});
const pending={state:'reconciliation_pending',reason_code:'stock_shortage',requested_count:2,allocated_count:0};
assert.equal(A.parseAllocation(pending).state,'reconciliation_pending');
for(const bad of [{...pending,allocated_count:1},{...pending,reason_code:null},{...pending,public_token:'PRIVATE_CANARY'},{...pending,requested_count:'2'},{...pending,state:'allocated'},{...pending,state:'awaiting_verified_payment'}])assert.throws(()=>A.parseAllocation(bad));
assert.equal(A.parseAllocation({state:'allocated',reason_code:null,requested_count:2,allocated_count:2}).allocated_count,2);
const origin='https://allocation.synthetic.invalid',upstream='https://api.synthetic.invalid',oid='00000000-0000-4000-8000-000000000001';
let authorized=true,unavailable=false,calls=[];
const relay=compile('app/payments/api/route.ts',name=>{
 if(name==='next/server')return require(name);
 if(name.endsWith('/auth/server'))return{verifiedSession:async()=>{if(unavailable)throw Error('PRIVATE_CANARY');return authorized?{token:'synthetic-token'}:null;}};
 if(name.endsWith('/auth/config'))return{authConfig:()=>({origin})};
 if(name.endsWith('/api/transport'))return{validateOrigin:v=>{assert.equal(v,upstream);return v;}};
 throw Error(name);
},{process:{env:{SAFERETURN_API_ORIGIN:upstream}},AbortSignal,fetch:async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(pending),{status:200,headers:{'Content-Type':'application/json'}});}});
const get=path=>new NextRequest(origin+'/payments/api?'+new URLSearchParams({path}));
const post=(path,source=origin)=>new NextRequest(origin+'/payments/api',{method:'POST',headers:{Origin:source,'Content-Type':'application/json'},body:JSON.stringify({path,key:'synthetic-key',body:{confirmed:true}})});
async function main(){
 authorized=false;assert.equal((await relay.GET(get(`/admin/orders/${oid}/qr-allocation`))).status,401);assert.equal(calls.length,0);authorized=true;
 assert.equal((await relay.POST(post(`/admin/orders/${oid}/qr-allocation/retry`,'https://other.invalid'))).status,403);
 const response=await relay.GET(get(`/admin/orders/${oid}/qr-allocation`));assert.equal(response.status,200);assert.match(response.headers.get('cache-control'),/no-store/);
 assert.equal((await relay.POST(post(`/admin/orders/${oid}/qr-allocation/retry`))).status,200);assert.equal(calls.at(-1).options.headers.Authorization,'Bearer synthetic-token');assert.equal(calls.at(-1).options.headers['Idempotency-Key'],'synthetic-key');assert.equal(calls.at(-1).options.redirect,'error');
 for(const p of [`/me/orders/${oid}/payment-attempts`,`/me/orders/${oid}/payment-instructions`,`/admin/orders/${oid}/payment-attempts`])assert.equal((await relay.GET(get(p))).status,200);
 assert.equal((await relay.POST(post('/admin/qr-inventory'))).status,400);unavailable=true;const unavailableResponse=await relay.GET(get(`/admin/orders/${oid}/qr-allocation`));assert.equal(unavailableResponse.status,503);assert(!JSON.stringify(await unavailableResponse.json()).includes('PRIVATE_CANARY'));
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');let roles=['finance'];
 const I=compile('lib/inventory-contract.ts',()=>{throw Error();});
 const page=compile('app/admin/payments/review/page.tsx',name=>{
  if(name==='react/jsx-runtime')return require(name);
  if(name.endsWith('/admin-page'))return{AdminPage:({path,capability,children})=>{assert.equal(path,'/admin/payments/review');assert.equal(capability,'payments.review');return children({roles},false);},AdminNotice:()=>React.createElement('p',null,'DENIED')};
  if(name.endsWith('/payments'))return{FinanceForm:({orderId,attemptId})=>React.createElement('p',null,'REVIEW '+orderId+' '+attemptId)};
  if(name.endsWith('/orders-contract'))return I;throw Error(name);
 });
 assert.match(renderToStaticMarkup(await page.default({searchParams:Promise.resolve({orderId:oid,attemptId:oid})})),/REVIEW/);
 roles=['operations'];assert.match(renderToStaticMarkup(await page.default({searchParams:Promise.resolve({})})),/DENIED/);
 roles=['finance'];assert.match(renderToStaticMarkup(await page.default({searchParams:Promise.resolve({attemptId:'PRIVATE_CANARY'})})),/DENIED/);
 console.log('PASS allocation states/invariants, finance review page and real payment relay: sessions, origin, legacy/new targets, bearer/retry key, no-store, safe failure');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
