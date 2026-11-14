/* Real Next relay -> loopback HTTP -> actual FastAPI router/DTOs.
 * Auth and SQL dependencies are synthetic; no real customer or database writes. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),ts=require('typescript');
const {NextRequest}=require('next/server');
const root=path.resolve(__dirname,'..');
function compile(file,require,globals={}){const scope={exports:{},require,...globals};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,scope);return scope.exports;}
async function main(){
 const child=spawn(path.join(root,'../backend/.venv/Scripts/python.exe'),['-u',path.join(root,'tests/customer-backend-fixture.py')],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
 try {
  const port=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(Error('Fixture startup timeout')),15000);child.on('error',reject);child.stderr.on('data',data=>{output+=data;});child.on('exit',code=>reject(Error('Fixture exited '+code+' '+output)));child.stdout.on('data',data=>{const match=String(data).match(/PORT=(\d+)/);if(match){clearTimeout(timer);resolve(match[1]);}});});
  const upstream='http://127.0.0.1:'+port,origin='https://customer.synthetic.invalid';
  for(let i=0;i<40;i++){try{await fetch(upstream+'/openapi.json');break;}catch{await new Promise(r=>setTimeout(r,100));}}
  const inventory=compile('lib/inventory-contract.ts',()=>{throw Error();});
  const contract=compile('lib/independent-qr.ts',()=>inventory);
  const quarantine=require('../tests/load-quarantine.cjs')(fetch);
  let authenticated=true;
  const dependencies=name=>{
   if(name==='next/server')return require(name);
   if(name.endsWith('/api/quarantine'))return quarantine;
   if(name.endsWith('/auth/server'))return {verifiedSession:async()=>authenticated?{token:'synthetic-customer'}:null};
   if(name.endsWith('/auth/config'))return {authConfig:()=>({origin})};
   if(name.endsWith('/api/transport'))return {validateOrigin:value=>{assert.equal(value,upstream);return value;}};
   if(name.endsWith('/independent-qr'))return contract;
   throw Error(name);
  };
  const globals={process:{env:{SAFERETURN_API_ORIGIN:upstream}},TextDecoder,AbortSignal,fetch};
  const relay=compile('app/independent-qr/api/route.ts',dependencies,globals);
  const request=(body)=>new NextRequest(origin+'/independent-qr/api',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify(body)});
  const get=()=>relay.GET(new NextRequest(origin+'/independent-qr/api'));
  authenticated=false;assert.equal((await get()).status,401);authenticated=true;
  assert.equal((await fetch(upstream+'/api/v1/me/independent-qr')).status,401);
  let response=await get();assert.equal(response.status,200);let data=await response.json();const item=data.items[0];assert.equal(item.can_activate,true);
  response=await relay.POST(request({action:'begin',body:{logical_item_id:item.logical_item_id,owner_user_id:item.qr_id}}));assert.equal(response.status,422);
  response=await relay.POST(request({action:'begin',body:{logical_item_id:item.logical_item_id}}));assert.equal(response.status,201);const intent=await response.json();assert(Date.parse(intent.expires_at)>Date.now());
  const confirm={action:'confirm',key:'synthetic-confirm-key',body:{intent_id:intent.intent_id,confirmed:true}};
  for(let i=0;i<2;i++){response=await relay.POST(request(confirm));assert.equal(response.status,201);assert.equal((await response.json()).qr_id,item.qr_id);}
  data=await (await get()).json();assert.equal(data.items.length,1);assert.equal(data.items[0].can_activate,false);
  response=await relay.POST(request({action:'availability',qr_id:item.qr_id,key:'synthetic-availability-key',body:{public_status:'owner_disabled',expected_revision:2,confirmed:true}}));assert.equal(response.status,200);assert.equal((await response.json()).public_status,'owner_disabled');
  response=await relay.POST(request({action:'history',qr_id:item.qr_id,body:{}}));assert.equal(response.status,200);assert.equal((await response.json()).items[0].event_type,'activated');
  const checkout=compile('app/checkout/api/route.ts',dependencies,globals);
  response=await checkout.POST(new NextRequest(origin+'/checkout/api',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({path:'/me/checkout/item-quotes',key:'synthetic-quote-key',body:{commerce_model:'single_qr',price_per_copy:'0.01',items:[]}})}));assert.equal(response.status,422);
  assert.throws(()=>quarantine.assertBackendOperation('PUT','/api/v1/me/qr/'+item.qr_id+'/ice-profile'));
  console.log('PASS real relay/FastAPI HTTP: auth denial, closed DTOs, intent expiry, confirm/replay, identity count, availability/history, price tampering rejection; synthetic Auth/SQL only.');
 } finally {child.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
