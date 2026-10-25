/* Actual TypeScript contracts/relay under synthetic Auth/transport, no listener. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const {NextRequest}=require('next/server');
function compile(file,req,globals={}){const s={exports:{},require:req,...globals};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,s);return s.exports;}
const I=compile('lib/inventory-contract.ts',()=>{throw Error();}),C=compile('lib/independent-qr.ts',n=>{if(n==='./inventory-contract')return I;throw Error(n);});
const id='00000000-0000-4000-8000-000000000001',origin='https://owner.synthetic.invalid',upstream='https://api.synthetic.invalid';
const item={logical_item_id:id,qr_id:id,order_id:id,product_name_snapshot:'Synthetic',tag_type:'lost',ownership_status:'unclaimed',public_status:'unactivated',revision:2,activated_at:null,can_activate:true};
const page={items:[item],next_cursor:null,activation_released:true};
assert.equal(C.collection(page).items[0].can_activate,true);
for(const bad of [{...page,public_token:'PRIVATE_CANARY'},{...page,items:[item,item]},{...page,activation_released:false},{...page,items:[{...item,owner_user_id:id}]},{...page,items:[{...item,ownership_status:'active'}]}])assert.throws(()=>C.collection(bad));
assert.throws(()=>C.commandResult('begin',{intent_id:id,logical_item_id:id,qr_id:id,expires_at:'2026-10-22T10:00:00Z',method:'concealed_credential'}));
let authorized=true,down=false,calls=[],payload=page;
const relay=compile('app/independent-qr/api/route.ts',n=>{
 if(n==='next/server')return require(n);
 if(n.endsWith('/auth/server'))return{verifiedSession:async()=>{if(down)throw Error('PRIVATE_CANARY');return authorized?{token:'synthetic-token'}:null;}};
 if(n.endsWith('/auth/config'))return{authConfig:()=>({origin})};
 if(n.endsWith('/api/transport'))return{validateOrigin:x=>{assert.equal(x,upstream);return x;}};
 if(n.endsWith('/independent-qr'))return C;
 throw Error(n);
},{process:{env:{SAFERETURN_API_ORIGIN:upstream}},TextDecoder,AbortSignal,fetch:async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(payload),{headers:{'Content-Type':'application/json'}});}});
const get=q=>new NextRequest(origin+'/independent-qr/api'+(q?'?'+q:''));
const post=(value,source=origin)=>new NextRequest(origin+'/independent-qr/api',{method:'POST',headers:{Origin:source,'Content-Type':'application/json'},body:JSON.stringify(value)});
(async()=>{
 authorized=false;assert.equal((await relay.GET(get())).status,401);assert.equal(calls.length,0);authorized=true;
 assert.equal((await relay.POST(post({action:'begin',body:{logical_item_id:id}},'https://other.invalid'))).status,403);
 const beforeLarge=calls.length;assert.equal((await relay.POST(post({action:'begin',body:{logical_item_id:id,oversized:'x'.repeat(8193)}}))).status,413);assert.equal(calls.length,beforeLarge);
 for(const q of ['path=https://untrusted.invalid','after=bad','limit=101','limit=1&limit=2'])assert.equal((await relay.GET(get(q))).status,422);
 const result=await relay.GET(get());assert.equal(result.status,200);assert.match(result.headers.get('cache-control'),/no-store/);assert.equal(calls.at(-1).options.redirect,'error');assert.equal(calls.at(-1).options.headers.Authorization,'Bearer synthetic-token');
 payload={intent_id:id,logical_item_id:id,qr_id:id,expires_at:'2026-10-22T10:00:00Z',method:'delivered_purchaser'};
 assert.equal((await relay.POST(post({action:'begin',body:{logical_item_id:id}}))).status,200);assert(calls.at(-1).url.endsWith('/me/independent-qr/activation-intents'));
 assert.equal((await relay.POST(post({action:'confirm',body:{intent_id:id,confirmed:true},key:'short'}))).status,422);
 payload={qr_id:id,logical_item_id:id,status:'active',revision:3,activated_at:'2026-10-22T10:00:00Z'};
 assert.equal((await relay.POST(post({action:'confirm',body:{intent_id:id,confirmed:true},key:'synthetic-key'}))).status,200);assert.equal(calls.at(-1).options.headers['Idempotency-Key'],'synthetic-key');
 payload={...payload,public_token:'PRIVATE_CANARY'};const unsafe=await relay.POST(post({action:'confirm',body:{intent_id:id,confirmed:true},key:'synthetic-key'}));assert.equal(unsafe.status,503);assert(!JSON.stringify(await unsafe.json()).includes('PRIVATE_CANARY'));
 down=true;assert.equal((await relay.GET(get())).status,503);
 console.log('PASS independent QR closed contracts, account-only actions, origin/session denial, bounded queries, guarded relay targets, retries and canary rejection');
})().catch(e=>{console.error(e);process.exitCode=1;});
