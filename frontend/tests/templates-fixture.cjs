// Synthetic metadata only. No network, app boot, production DB or approved evidence.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const tid='00000000-0000-0000-0000-000000000501',rid='00000000-0000-0000-0000-000000000502',vid='00000000-0000-0000-0000-000000000504',pid='00000000-0000-0000-0000-000000000505';
const content=()=>({schema_version:1,renderer:'safereturn-vector-v1',preset:'fixed-footer-v1',symbol_mm:'35.00',width_mm:'55.00',height_mm:'80.00',qr_x_mm:'10.00',qr_y_mm:'30.00',logo_mm:'4.00',min_pitch_mm:'0.40',font_pt:'9.00',header:'Synthetic Lost',english_lines:['Found this item?'],urdu_lines:['اسکین کریں'],asset_set_id:'00000000-0000-0000-0000-000000000503',material_codes:['synthetic-paper']});
const stamp='2026-10-23T00:00:00Z';
function createHarness(){
 const state={template:{template_id:tid,key:'synthetic-key',name:'Synthetic design',purpose:'lost',lifecycle_status:'draft',row_version:1,created_at:stamp},revisions:[],authorized:true,mfa:true,role:'operations',errorCode:null,status:0,malformed:false,calls:[],receipts:new Map(),conflict:false};
 const cache=new Map();
 function load(file){file=path.resolve(file);if(cache.has(file))return cache.get(file).exports;const module={exports:{}};cache.set(file,module);const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Uint8Array,Number,Set,Map,Date,JSON,process:{env:{SAFERETURN_API_ORIGIN:'https://api.templates.invalid'}},crypto:globalThis.crypto,require(name){if(name==='next/server')return require(name);if(name.endsWith('/auth/server'))return {verifiedSession:async()=>state.authorized?{token:'synthetic-token'}:null};if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>({mfa_verified:state.mfa,roles:[state.role],capabilities:['printing.manage']})};}if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://templates.test'})};if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');throw Error('Unapproved import '+name);},fetch:upstream};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;}
 async function upstream(url,options){const u=new URL(url),p=u.pathname.replace('/api/v1',''),m=options.method,c=load(path.resolve(__dirname,'../lib/admin-templates-contract.ts'));c.templateTarget(p,m);state.calls.push({path:p,method:m,options});
 if(state.status)return Response.json({error:{code:state.errorCode??(state.status===412?'VERSION_MISMATCH':state.status===403?'REAUTH_REQUIRED':'PROVIDER_UNAVAILABLE')},private:'NEVER_RENDER'},{status:state.status});if(state.malformed)return Response.json({private:'NEVER_RENDER'});
 if(m==='GET'){
 if(p==='/admin/print-templates')return Response.json({items:u.searchParams.has('cursor')?[]:[state.template],next_cursor:u.searchParams.has('cursor')?null:'opaque_next',as_of:stamp});
 if(p==='/admin/print-templates/'+tid)return Response.json({template:state.template,revisions:state.revisions,next_cursor:null},{headers:{ETag:'"'+state.template.row_version+'"'}});
 if(p==='/admin/print-template-bindings')return Response.json({items:[],next_cursor:null,as_of:stamp});
 if(p==='/admin/products')return Response.json({items:[product()],next_cursor:null});if(p==='/admin/products/'+pid)return Response.json(product());return Response.json({error:{code:'NOT_FOUND'}},{status:404});}
 const b=JSON.parse(options.body),key=m+p+options.headers['Idempotency-Key'],signature=JSON.stringify([b,options.headers['If-Match']]);
 if(state.receipts.has(key)){const r=state.receipts.get(key);return r.signature===signature?Response.json(r.value,{status:r.status}):Response.json({error:{code:'IDEMPOTENCY_KEY_REUSED'}},{status:409});}
 if(state.conflict){state.conflict=false;if(state.revisions[0])state.revisions[0].row_version++;state.template.row_version++;return Response.json({error:{code:'VERSION_MISMATCH'}},{status:412});}
 if(p.endsWith('/retire')||p==='/admin/print-template-bindings')return Response.json({error:{code:'FORBIDDEN'}},{status:403}); // No enrolled publisher or signed approval fabricated.
 if(p.endsWith('/preview'))return new Response('%PDF-1.4\nsynthetic proof fixture\n%%EOF',{headers:{'Content-Type':'application/pdf','X-Template-Fingerprint':'a'.repeat(64)}});
 let result,status=200;
 if(p==='/admin/print-templates'){state.template={...state.template,...b};result=state.template;status=201;}
 else if(p.endsWith('/submit-qa')){state.revisions[0]={...state.revisions[0],status:'pending_qa',row_version:state.revisions[0].row_version+1};result={revision:state.revisions[0],validation_status:'needs_independent_physical_qa'};}
 else if(m==='PATCH'){state.revisions[0]={...state.revisions[0],content:b.content,row_version:state.revisions[0].row_version+1};result=state.revisions[0];}
 else {const revision={revision_id:rid,template_id:tid,version:1,status:'draft',row_version:1,content:b.content,fingerprint_sha256:null,created_at:stamp,published_at:null};state.revisions=[revision];state.template.row_version++;result={template:state.template,revision};status=201;}
 const value={command_id:'00000000-0000-0000-0000-000000000599',result};state.receipts.set(key,{signature,value:JSON.parse(JSON.stringify(value)),status});return Response.json(value,{status});
 }
 const relay=load(path.resolve(__dirname,'../app/admin/templates/api/route.ts'));
 async function dispatch(url,init={}){return relay[init.method??'GET'](new NextRequest(url,{...init,headers:{...init.headers,...(init.method==='POST'?{Origin:'https://templates.test'}:{})}}));}
 return {state,load,relay,dispatch};
}
function product(){return {id:pid,name:'Synthetic product',slug:'synthetic-product',description:null,category_id:null,qr_type:'lost',commerce_model:'single_qr',price_per_copy:'10.00',max_order_copies:100,lifecycle_status:'draft',is_featured:false,featured_sort_order:0,catalog_version:1,images:[],variants:[{id:vid,sku:'SYNTHETIC',name:'Synthetic variant',size_mm:'35.00',material:'synthetic-paper',color:null,currency_code:'PKR',unit_price:'10.00',fulfillment_method:'manual',template_key:'synthetic-key',template_version:1,is_active:false,sort_order:0,catalog_version:1}]};}
module.exports={createHarness,content,tid,rid,vid,pid};
