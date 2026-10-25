/* Execute real TS contracts/relay with synthetic memory state; no environment edits. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const {NextRequest}=require('next/server'),root=path.resolve(__dirname,'..');
function compile(file,require,globals={}){const box={exports:{},require,...globals};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,box);return box.exports;}
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),pid=id(1),vid=id(2),iid=id(3),oid=id(4);
let stored='[]';const cart=compile('lib/item-cart.ts',()=>{throw Error();},{localStorage:{getItem:()=>stored}});
stored=JSON.stringify([{product_id:pid,identity_group:null,price_per_copy:'0.01',public_token:'PRIVATE_CANARY',sizes:[{variant_id:vid,copies:2,unit_price:'0.01'}]}]);
const clean=cart.readItemCart();assert(!JSON.stringify(clean).includes('price'));assert(!JSON.stringify(clean).includes('PRIVATE_CANARY'));
assert.equal(cart.mergeItemCart(clean,{product_id:pid,identity_group:null,sizes:[{variant_id:vid,copies:3}]}).length,1);
assert.equal(cart.mergeItemCart(clean,{product_id:pid,identity_group:'separate',sizes:[{variant_id:vid,copies:3}]}).length,2);
for(const copies of [true,'1',0,101]){stored=JSON.stringify([{...clean[0],sizes:[{variant_id:vid,copies}]}]);assert.equal(cart.readItemCart().length,0);}
const I=compile('lib/inventory-contract.ts',()=>{throw Error();});
const O=compile('lib/orders-contract.ts',name=>{if(name==='./allocation')return compile('lib/allocation.ts',()=>{throw Error();});if(name==='./inventory-contract')return I;throw Error(name);});
const detail={id:oid,order_number:'SYNTHETIC',order_status:'placed',payment_status:'under_review',fulfillment_status:'unallocated',currency_code:'PKR',total_pkr:'24.60',created_at:'2026-10-22T00:00:00Z',placed_at:'2026-10-22T00:00:00Z',commerce_model:'single_qr',identity_count:1,items:[],qr_uses:[],pair_units:[],pair_count:0,print_status:'restricted',logical_items:[{id:iid,product_id:pid,identity_group:null,product_name_snapshot:'Synthetic',qr_type_snapshot:'lost',quantity:2,unit_price_snapshot:'12.30',line_total:'24.60',currency_code:'PKR',sizes:[{id:id(5),logical_item_id:iid,variant_id:vid,variant_name_snapshot:'35 mm',sku_snapshot:'SYNTHETIC',size_mm_snapshot:'35.00',material_snapshot:null,copies:2}]}]};
const parsed=O.detail(detail,oid,false);assert.equal(parsed.copy_count,2);assert.equal(parsed.line_count,1);assert.equal(parsed.identity_count,1);assert.equal(O.browserDetail(parsed,oid).identity_count,1);assert.throws(()=>O.browserDetail({...parsed,identity_count:2},oid));assert(!JSON.stringify(parsed).includes('sku_snapshot'));
assert.throws(()=>O.detail({...detail,identity_count:2},oid,false));assert.throws(()=>O.detail({...detail,logical_items:[{...detail.logical_items[0],quantity:3}]},oid,false));
const origin='https://checkout.synthetic.invalid',upstream='https://api.synthetic.invalid';let authorized=true,unavailable=false,calls=[];
const relay=compile('app/checkout/api/route.ts',name=>{
 if(name==='next/server')return require(name);
 if(name.endsWith('/auth/server'))return{verifiedSession:async()=>{if(unavailable)throw Error('PRIVATE_CANARY');return authorized?{token:'synthetic-token'}:null;}};
 if(name.endsWith('/auth/config'))return{authConfig:()=>({origin})};
 if(name.endsWith('/api/transport'))return{validateOrigin:value=>{assert.equal(value,upstream);return value;}};throw Error(name);
},{process:{env:{SAFERETURN_API_ORIGIN:upstream}},AbortSignal,fetch:async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify({quote_id:oid}),{status:201,headers:{'Content-Type':'application/json'}});}});
const request=(path,source=origin)=>new NextRequest(origin+'/checkout/api',{method:'POST',headers:{Origin:source,'Content-Type':'application/json'},body:JSON.stringify({path,key:'synthetic-key',body:{commerce_model:'single_qr'}})});
async function main(){
 authorized=false;assert.equal((await relay.POST(request('/me/checkout/item-quotes'))).status,401);assert.equal(calls.length,0);authorized=true;
 assert.equal((await relay.POST(request('/me/checkout/item-quotes','https://other.invalid'))).status,403);assert.equal(calls.length,0);
 for(const target of ['/me/checkout/item-quotes','/me/checkout/item-quotes/'+oid+'/confirm','/me/checkout/quotes'])assert.equal((await relay.POST(request(target))).status,201);
 assert.equal(calls[0].options.headers.Authorization,'Bearer synthetic-token');assert.equal(calls[0].options.headers['Idempotency-Key'],'synthetic-key');assert.equal(calls[0].url,upstream+'/api/v1/me/checkout/item-quotes');
 assert.equal((await relay.POST(request('/admin/qr-inventory'))).status,400);unavailable=true;const response=await relay.POST(request('/me/checkout/item-quotes'));assert.equal(response.status,503);assert(!JSON.stringify(await response.json()).includes('PRIVATE_CANARY'));
 console.log('PASS item cart, typed order summaries and checkout relay: merge/separation, no price fields, counts, session/origin, retry key, safe failures');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
