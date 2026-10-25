// Isolated, in-memory catalog only. No app boot, credentials, DB, worker or legacy fixture.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const id='10000000-0000-4000-8000-000000000001',cat='20000000-0000-4000-8000-000000000001',vid='30000000-0000-4000-8000-000000000001',img='40000000-0000-4000-8000-000000000001';
const baseProduct=()=>({id,name:'SafeReturn Sticker',slug:'sticker',description:'Catalog fixture',category_id:cat,qr_type:'lost',commerce_model:'single_qr',price_per_copy:'12.50',max_order_copies:100,lifecycle_status:'draft',is_featured:false,featured_sort_order:0,catalog_version:1,variants:[],images:[]});
function createHarness(){
 const state={product:baseProduct(),categories:[{id:cat,name:'Stickers',slug:'qr-stickers',sort_order:0,is_active:true,catalog_version:1}],authorized:true,mfa:true,role:'operations',status:0,malformed:false,calls:[],receipts:new Map(),conflict:false,delay:0};
 const cache=new Map();
 const load=file=>{file=path.resolve(file);if(cache.has(file))return cache.get(file).exports;const module={exports:{}};cache.set(file,module);
 const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Number,Set,Map,Date,JSON,process:{env:{SAFERETURN_API_ORIGIN:'https://api.products.invalid'}},crypto:globalThis.crypto,
 require(name){
 if(name==='next/server')return require(name);
 if(name.endsWith('/auth/server'))return {verifiedSession:async()=>state.authorized?{token:'synthetic-only-token'}:null};
 if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>({mfa_verified:state.mfa,roles:[state.role],capabilities:['catalog.manage']})};}
 if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://products.test'})};
 if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');
 throw Error('Unapproved import '+name);
 },fetch:upstream};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;};
 async function upstream(url,options){const u=new URL(url),p=u.pathname,m=options.method;state.calls.push({path:p,method:m,options});
 // Any unrelated API is a test failure before a request can be dispatched.
 const c=load(path.resolve(__dirname,'../lib/admin-products-contract.ts'));c.target(p.replace('/api/v1',''),m);
 if(state.delay)await new Promise(r=>setTimeout(r,state.delay));
 if(state.status)return Response.json({detail:{code:state.status===412?'VERSION_MISMATCH':'PRIVATE_PROVIDER_TEXT'},private:'DO_NOT_RENDER'},{status:state.status});
 if(state.malformed)return Response.json({untrusted:'DO_NOT_RENDER'});
 if(m==='GET'){
 if(p.endsWith('/approved-templates'))return Response.json({as_of:'2026-10-23T00:00:00Z',items:[{template_key:'approved-template',template_version:1}]});
 if(p.endsWith('/categories'))return Response.json({items:state.categories});
 if(p==='/api/v1/admin/products')return Response.json({items:u.searchParams.has('cursor')?[]:[state.product],next_cursor:u.searchParams.has('cursor')?null:id});
 if(p.endsWith('/'+state.product.id))return Response.json(state.product);
 return Response.json({},{status:404});
 }
 const key=options.headers['Idempotency-Key'],body=options.body?JSON.parse(options.body):undefined,receiptKey=m+p+(u.search||'')+key,hash=JSON.stringify([body,options.headers['If-Match']]);
 if(state.receipts.has(receiptKey)){const receipt=state.receipts.get(receiptKey);return receipt.hash===hash?Response.json(receipt.result,{status:receipt.status}):Response.json({detail:{code:'IDEMPOTENCY_KEY_REUSED'}},{status:409});}
 if(state.conflict){state.conflict=false;state.product.catalog_version++;state.product.description='Changed by another admin';return Response.json({detail:{code:'VERSION_MISMATCH'}},{status:412});}
 let result,status=m==='POST'?201:200;
 if(p.includes('/images')&&u.searchParams.get('authorize_upload')==='true'){status=201;result={id:state.product.id,catalog_version:state.product.catalog_version,public_id:'safereturn/catalog/'+state.product.id+'/asset',upload_url:'https://api.cloudinary.com/v1_1/synthetic/image/upload',upload_params:{timestamp:String(Math.floor(Date.now()/1000)),public_id:'safereturn/catalog/'+state.product.id+'/asset',overwrite:'false',allowed_formats:'png,jpg,jpeg,webp,avif',type:'upload',upload_preset:'catalog',signature:'a'.repeat(64),api_key:'123456'},expires_at:Math.floor(Date.now()/1000)+3600};}
 else if(p.includes('/images')){const prior=state.product.images.find(i=>p.endsWith('/'+i.id));result={...(prior??{id:img,verified_public_url:'https://res.cloudinary.com/synthetic/image/upload/v1/catalog/photo.png'}),...body};if(m==='DELETE')state.product.images=state.product.images.filter(i=>i.id!==result.id);else state.product.images=[...state.product.images.filter(i=>i.id!==result.id),result];state.product.catalog_version++;}
 else if(p.includes('/variants')||p.includes('/product-variants/')){const prior=state.product.variants.find(v=>p.endsWith('/'+v.id));result={...(prior??{id:vid,currency_code:'PKR',catalog_version:0}),...body,unit_price:state.product.price_per_copy,catalog_version:(prior?.catalog_version??0)+1};state.product.variants=[...state.product.variants.filter(v=>v.id!==result.id),result];state.product.catalog_version++;}
 else if(p.includes('/categories')){const prior=state.categories.find(c=>p.endsWith('/'+c.id));result={id:prior?.id??'20000000-0000-4000-8000-000000000002',...body,catalog_version:(prior?.catalog_version??0)+1};state.categories=[...state.categories.filter(c=>c.id!==result.id),result];}
 else{state.product={...state.product,...body,catalog_version:m==='POST'?1:state.product.catalog_version+1};result=state.product;}
 state.receipts.set(receiptKey,{hash,result:JSON.parse(JSON.stringify(result)),status});return Response.json(result,{status});
 }
 const relay=load(path.resolve(__dirname,'../app/admin/catalog-api/route.ts'));
 async function dispatch(url,init={}){const req=new NextRequest(url,{...init,headers:{...init.headers,...(init.method==='POST'?{Origin:'https://products.test'}:{})}});return relay[init.method??'GET'](req);}
 return {state,relay,dispatch,load,id,cat,vid,img};
}
module.exports={createHarness,baseProduct,id,cat,vid,img};
