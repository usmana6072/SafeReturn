// Synthetic exact-route harness. No environment files, database, provider or worker.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const id=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0'),stamp='2026-10-24T00:00:00Z';
const cursor=Buffer.from(JSON.stringify([stamp,id(2)])).toString('base64url');
const sync=(n=1)=>({id:id(n),order_id:id(100+n),sheet_row_key:'PRIVATE_CANARY',last_export_version:1,status:n===1?'failed':n===2?'synced':'pending',attempt_count:2,last_error_code:'PRIVATE_CANARY',last_synced_at:null,updated_at:stamp,payment_status:'paid',fulfillment_status:'pending',currency_code:'PKR',total_pkr:'120.00'});
const artifact=(n=1)=>({id:id(n),resource_type:n===1?'print_artifact':'payment_evidence',owner_id:id(200+n),bucket:'PRIVATE_CANARY',object_key:'PRIVATE_CANARY',format:'pdf',sha256_hex:'PRIVATE_CANARY',size_bytes:120,retention_until:stamp,deletion_hold_reason:'PRIVATE_CANARY',deleted_at:null,on_hold:n===1,cleanup_job:{id:id(300+n),status:'dead',attempt_count:3,last_error_code:'PRIVATE_CANARY'}});
function createHarness(){
 const state={read:true,retry:true,authorized:true,roles:['security_admin'],mfa:true,capabilities:['finance.mirror','storage.metadata'],authCalls:0,calls:[],status:0,network:false,malformed:false,attachment:false,revoke:false};const cache=new Map();
 function load(file){file=path.resolve(file);if(cache.has(file))return cache.get(file).exports;const module={exports:{}};cache.set(file,module);
 const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Uint8Array,Date,JSON,Set,Map,atob,process:{env:{SAFERETURN_API_ORIGIN:'https://api.metadata.invalid'}},require(name){
 if(name==='server-only')return {};if(name==='next/server')return require(name);
 if(name.endsWith('/finance-storage-gate'))return {financeSyncReadAdmitted:()=>state.read,storageReadAdmitted:()=>state.read,financeSyncRetryAdmitted:()=>state.retry};
 if(name.endsWith('/auth/server'))return {verifiedSession:async()=>{state.authCalls++;return state.authorized?{token:'synthetic-only'}:null;}};
 if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>({roles:state.roles,mfa_verified:state.mfa,capabilities:state.capabilities})};}
 if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://metadata.test'})};
 if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');throw Error('Unexpected import '+name);
 },fetch:upstream};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;}
 async function upstream(url,options){const u=new URL(url),finance='/api/v1/admin/finance/sheet-sync',storage='/api/v1/admin/storage/artifacts';if(u.origin!=='https://api.metadata.invalid'||!(options.method==='GET'&&[finance,storage].includes(u.pathname)||options.method==='POST'&&u.pathname===finance+'/'+id(1)+'/retry'))throw Error('Forbidden fixture request');state.calls.push({url,options});if(state.revoke)state.roles=[];if(state.network)throw Error('PRIVATE_CANARY');if(state.status)return Response.json({detail:'PRIVATE_CANARY'},{status:state.status});
 let result;if(options.method==='POST')result={id:id(1),order_id:id(101),status:'retry'};else if(u.pathname===finance)result={items:u.searchParams.has('cursor')?[sync(3)]:[sync(1),sync(2)],next_cursor:u.searchParams.has('cursor')?null:cursor};else result={items:[artifact(1),artifact(2)].filter(r=>!u.searchParams.has('resource_type')||r.resource_type===u.searchParams.get('resource_type'))};
 if(state.malformed)result={...result,private:'PRIVATE_CANARY'};if(state.oversized)return new Response(' '.repeat(262145),{headers:{'Content-Type':'application/json'}});return Response.json(result,{status:options.method==='POST'?202:200,headers:state.attachment?{'Content-Disposition':'attachment'}:{}});}
 const finance=load(path.resolve(__dirname,'../app/admin/finance/sheet-sync/api/route.ts')),storage=load(path.resolve(__dirname,'../app/admin/storage/api/route.ts'));
 async function dispatch(storageMode=false,init={},query=''){const method=init.method??'GET';return (storageMode?storage:finance)[method](new NextRequest('https://metadata.test/admin/'+(storageMode?'storage':'finance/sheet-sync')+'/api'+query,init));}
 return {state,load,dispatch};
}
module.exports={createHarness,id,sync,artifact,cursor};
