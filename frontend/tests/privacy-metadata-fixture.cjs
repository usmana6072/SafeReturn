// No .env, services, Auth, DB, worker or storage. Exact read-only route budget.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const id=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0'),stamp='2026-10-24T00:00:00Z';
const cursor=Buffer.from(JSON.stringify([stamp,id(2)])).toString('base64url');
const row=(n=1)=>({request_id:id(n),case_id:id(100+n),status:n===2?'ready':n===3?'rejected':'requested',revision:n,scope_version:'basic_v1',manifest_version:'basic_v1:1',manifest_id:id(200+n),categories:{private_payload:{name:'NEVER_RENDER',download:'https://private.invalid/NEVER_RENDER'},pairs:{source_count:999}},created_at:stamp,ready_at:n===2?stamp:null,expires_at:n===2?'2026-10-25T00:00:00Z':null});
function createHarness({admitted=true}={}){
  const state={admitted,authorized:true,roles:['security_admin'],mfa:true,capabilities:['privacy.exports'],authCalls:0,staffCalls:0,calls:[],rows:[row(1),row(2),row(3)],status:0,malformed:false,oversized:false,network:false,attachment:false,revoke:false};
  const cache=new Map();
  function load(file){
    file=path.resolve(file);if(cache.has(file))return cache.get(file).exports;
    const module={exports:{}};cache.set(file,module);
    const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Uint8Array,Date,JSON,Set,Map,atob,process:{env:{SAFERETURN_API_ORIGIN:'https://api.privacy.invalid'}},require(name){
      if(name==='server-only')return {};
      if(name==='next/server')return require(name);
      if(name.endsWith('/privacy-metadata-gate'))return {privacyMetadataAdmitted:()=>state.admitted};
      if(name.endsWith('/auth/server'))return {verifiedSession:async()=>{state.authCalls++;return state.authorized?{token:'synthetic-only'}:null;}};
      if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>{state.staffCalls++;return {roles:state.roles,mfa_verified:state.mfa,capabilities:state.capabilities};}};}
      if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://privacy.test'})};
      if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');
      throw Error('Unexpected import '+name);
    },fetch:upstream};
    vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;
  }
  async function upstream(url,options){
    const u=new URL(url);if(u.origin!=='https://api.privacy.invalid'||u.pathname!=='/api/v1/admin/privacy/exports'||options.method!=='GET')throw Error('Prohibited request');
    state.calls.push({url,options});if(state.revoke)state.roles=[];
    if(state.network)throw Error('NEVER_RENDER private exception');
    if(state.status)return Response.json({private:'NEVER_RENDER'},{status:state.status});
    if(state.oversized)return new Response(' '.repeat(262145),{headers:{'Content-Type':'application/json'}});
    const q=u.searchParams,offset=q.has('cursor')?2:0,limit=Math.min(Number(q.get('limit')??20),2);
    const result={items:structuredClone(state.rows.slice(offset,offset+limit)),next_cursor:state.rows.length>offset+limit?cursor:null};
    if(state.malformed)result.items=[{...row(1),customer_email:'NEVER_RENDER'}];
    return Response.json(result,{headers:state.attachment?{'Content-Disposition':'attachment; filename="NEVER_RENDER.json"'}:{}});
  }
  const route=load(path.resolve(__dirname,'../app/admin/privacy/exports/api/route.ts'));
  async function dispatch(url='https://privacy.test/admin/privacy/exports/api',init={}){
    const method=init.method??'GET';if(!route[method])return new Response(null,{status:405});return route[method](new NextRequest(url,init));
  }
  return {state,load,dispatch};
}
module.exports={createHarness,id,row,cursor,stamp};
