// Isolated contract transport only. Never loads .env, real Auth, DB or providers.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const {NextRequest}=require('next/server');
const stamp='2026-10-24T00:00:00Z',id=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0');
const token=Buffer.from(JSON.stringify([stamp,id(2)])).toString('base64url');
const attempt=n=>({attempt_number:n,outcome:'transient_failure',attempted_at:stamp,finished_at:stamp,error_code:'provider_network'});
const row=(n=1)=>({id:id(n),event_type:n===3?'unsupported':'finder_message.created',status:n===2?'sent':'dead',attempt_count:3,created_at:stamp,next_attempt_at:stamp,lease_until:null,sent_at:n===2?stamp:null,last_error_code:n===2?null:'provider_network',first_attempt_at:stamp,due_lag_seconds:null,retry_blocked_reason:n===2?'not_dead':n===3?'unsupported_event':null,attempts:null,next_attempt_before:null});
const template={identifier:'finder-message/v1',fingerprint:'a'.repeat(64),historical_version:'not_recorded',review:'4.4C_pending'};
function createHarness({admitted=true,retry=true}={}){
  const state={admitted,retry,authorized:true,mfa:true,roles:['operations'],capabilities:['notifications.manage'],authCalls:0,staffCalls:0,calls:[],status:0,malformed:false,oversized:false,wrongId:false,revoke:false,network:false,rows:[row(1),row(2),row(3)],receipts:new Map(),attempts:[attempt(3),attempt(2),attempt(1)]};
  const cache=new Map();
  function load(file){
    file=path.resolve(file);if(cache.has(file))return cache.get(file).exports;
    const module={exports:{}};cache.set(file,module);
    const sandbox={module,exports:module.exports,URL,URLSearchParams,AbortSignal,TextDecoder,TextEncoder,Request,Response,Uint8Array,Date,JSON,Set,Map,atob,process:{env:{SAFERETURN_API_ORIGIN:'https://api.notifications.invalid'}},require(name){
      if(name==='server-only')return {};
      if(name==='next/server')return require(name);
      if(name.endsWith('/notification-gate'))return {notificationReadAdmitted:()=>state.admitted,notificationRetryAdmitted:()=>state.retry};
      if(name.endsWith('/auth/server'))return {verifiedSession:async()=>{state.authCalls++;return state.authorized?{token:'synthetic-token'}:null;}};
      if(name.endsWith('/auth/staff')){class StaffAccessError extends Error{}return {StaffAccessError,staffState:async()=>{state.staffCalls++;return {roles:state.roles,mfa_verified:state.mfa,capabilities:state.capabilities};}};}
      if(name.endsWith('/auth/config'))return {authConfig:()=>({origin:'https://notifications.test'})};
      if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name)+'.ts');
      throw Error('Unexpected import: '+name);
    },fetch:upstream};
    vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,sandbox,{filename:file});return module.exports;
  }
  async function upstream(url,options){
    const u=new URL(url),match=u.pathname.match(/^\/api\/v1\/admin\/notification-outbox(?:\/([a-f0-9-]{36})\/retry)?$/);
    if(u.origin!=='https://api.notifications.invalid'||!match||(match[1]?'POST':'GET')!==options.method)throw Error('Prohibited backend request');
    state.calls.push({url,options});if(state.revoke)state.roles=[];
    if(state.network)throw Error('NEVER_RENDER private transport');
    if(state.status)return Response.json({private:'NEVER_RENDER'},{status:state.status});
    if(state.oversized)return new Response(' '.repeat(262145),{headers:{'Content-Type':'application/json'}});
    let result;
    if(match[1]){
      const body=JSON.parse(options.body),key=options.headers['Idempotency-Key'];
      const old=state.receipts.get(key),fingerprint=JSON.stringify({id:match[1],body});
      if(old){if(old.fingerprint!==fingerprint)return Response.json({private:'NEVER_RENDER'},{status:409});result=old.result;}
      else{const event=state.rows.find(r=>r.id===match[1]);if(!event)return Response.json({},{status:404});if(event.attempt_count!==body.expected_attempt_count)return Response.json({},{status:412});result={id:match[1],status:'retry',expected_attempt_count:body.expected_attempt_count};state.receipts.set(key,{fingerprint,result});event.status='retry';event.retry_blocked_reason='not_dead';}
    }else{
      const q=u.searchParams;let rows=state.rows.filter(r=>(!q.has('id')||q.get('id')===r.id)&&(!q.has('status')||q.get('status')===r.status));
      const offset=q.has('cursor')?2:0,limit=Math.min(Number(q.get('limit')??20),2);const more=rows.length>offset+limit;rows=structuredClone(rows.slice(offset,offset+limit));
      if(q.has('id'))for(const event of rows){const before=Number(q.get('attempt_before')??2147483647);event.attempts=state.attempts.filter(a=>a.attempt_number<before).slice(0,2);event.next_attempt_before=event.attempts.length===2?event.attempts.at(-1).attempt_number:null;}
      result={items:rows,next_cursor:more?token:null,current_template:template};
    }
    if(state.malformed)result=match[1]?{...result,email:'NEVER_RENDER'}:{...result,items:[{...row(),recipient_email:'NEVER_RENDER'}]};
    if(state.wrongId){if(match[1])result.id=id(999);else if(result.items.length)result.items[0].id=id(999);}
    if(match[1]&&state.commitThenFailOnce){state.commitThenFailOnce=false;throw Error('synthetic lost response after commit');}
    return Response.json(result,{status:match[1]?202:200});
  }
  const route=load(path.resolve(__dirname,'../app/admin/notifications/api/route.ts'));
  async function dispatch(url='https://notifications.test/admin/notifications/api',init={}){
    const method=init.method??'GET';if(!route[method])return new Response(null,{status:405});
    return route[method](new NextRequest(url,init));
  }
  return {state,load,dispatch};
}
module.exports={createHarness,row,attempt,id,stamp,token,template};
