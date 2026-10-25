// In-memory only: no environment files, real auth, server, database or network.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const stamp='2026-10-24T00:00:00Z',token='A'.repeat(40),oldToken='B'.repeat(40);
const id=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0');
const row=(n=1)=>({case_id:id(n),case_type:'other',status:'open',priority:'normal',case_revision:4,created_at:stamp,assignment:n===2?'unassigned':'mine',assigned_to_me:n!==2});
const event=(n=4)=>({event_id:id(100+n),case_revision:n,event_type:'updated',from_status:'open',to_status:'investigating',priority:'normal',created_at:stamp});
function createHarness({admitted=true}={}) {
 const state={admitted,authorized:true,mfa:true,roles:['support'],capabilities:['support.manage'],revoke:false,status:0,malformed:false,oversized:false,wrongId:false,authCalls:0,staffCalls:0,calls:[],rows:[row(1),row(2),row(3)],history:[event(4),event(2),event(1)]};
 const cache=new Map();
 function load(file) {
  file=path.resolve(file); if(cache.has(file))return cache.get(file).exports;
  const module={exports:{}};cache.set(file,module);
  const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Uint8Array,Set,Map,Date,JSON,process:{env:{SAFERETURN_API_ORIGIN:'https://api.support.invalid'}},require(name){
   if(name==='server-only')return {};
   if(name==='next/server')return require(name);
   if(name.endsWith('/support-metadata-gate')&&state.admitted)return {supportMetadataAdmitted:()=>true};
   if(name.endsWith('/auth/server'))return {verifiedSession:async()=>{state.authCalls++;return state.authorized?{token:'synthetic-test-token'}:null;}};
   if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>{state.staffCalls++;return {mfa_verified:state.mfa,roles:state.roles,capabilities:state.capabilities};}};}
   if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://support.test'})};
   if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');
   throw Error('Unexpected import '+name);
  },fetch:upstream};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;
 }
 async function upstream(url,options){
  const u=new URL(url),match=u.pathname.match(/^\/api\/v1\/admin\/support-case-metadata(?:\/([a-f0-9-]{36})(\/history)?)?$/);
  if(u.origin!=='https://api.support.invalid'||!match||options.method!=='GET')throw Error('Prohibited request');
  state.calls.push({url,options});if(state.revoke)state.roles=[];
  if(state.status)return Response.json({private:'NEVER_RENDER'},{status:state.status});
  if(state.oversized)return new Response(' '.repeat(262145),{headers:{'Content-Type':'application/json'}});
  const kind=match[2]?'history':match[1]?'detail':'list';
  load(path.resolve(__dirname,'../lib/admin-support-metadata.ts')).supportQuery(u.searchParams,kind);
  let result;
  if(kind==='list') {
   let rows=state.rows.filter(r=>['case_id','case_type','status','priority'].every(k=>!u.searchParams.has(k)||r[k]===u.searchParams.get(k))).filter(r=>!u.searchParams.has('queue')||u.searchParams.get('queue')==='all'||r.assignment===u.searchParams.get('queue'));
   const offset=u.searchParams.has('cursor')?1:0;result={as_of:stamp,items:rows.slice(offset,offset+1),next_cursor:rows.length>offset+1?token:null};
  }else{
   const found=state.rows.find(r=>r.case_id===match[1]);if(!found||kind==='history'&&!found.assigned_to_me)return Response.json({},{status:404});
   if(kind==='detail')result={...found,content_available:false};
   else{const offset=u.searchParams.has('cursor')?2:0;result={case_id:found.case_id,case_revision:4,items:state.history.slice(offset,offset+2),next_cursor:state.history.length>offset+2?oldToken:null};}
  }
  if(state.malformed)result=kind==='detail'?{...result,description:'NEVER_RENDER'}:kind==='history'?{...result,items:[{...event(),actor_staff_id:'NEVER_RENDER'}]}:{...result,items:[{...row(),customer_name:'NEVER_RENDER'}]};
  if(state.wrongId&&kind!=='list')result.case_id=id(999);
  return Response.json(result);
 }
 const routes={list:load(path.resolve(__dirname,'../app/admin/support/metadata-api/route.ts')),detail:load(path.resolve(__dirname,'../app/admin/support/metadata-api/[caseId]/route.ts')),history:load(path.resolve(__dirname,'../app/admin/support/metadata-api/[caseId]/history/route.ts'))};
 async function dispatch(url,init={}){const u=new URL(url),match=u.pathname.match(/^\/admin\/support\/metadata-api(?:\/([^/]+)(\/history)?)?$/);if(!match)throw Error('Unexpected relay path');const kind=match[2]?'history':match[1]?'detail':'list';const method=init.method??'GET';if(!routes[kind][method])return new Response(null,{status:405});return routes[kind][method](new NextRequest(url,init),{params:Promise.resolve({caseId:match[1]})});}
 return {state,load,dispatch};
}
module.exports={createHarness,row,event,id,token};
