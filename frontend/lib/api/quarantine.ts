import {quarantineOperations} from './quarantine-operations';
const rules=quarantineOperations.map(([method,path])=>({method,path:new RegExp('^'+path.split('/').map(part=>/^\{[a-z_]+\}$/.test(part)?'[^/]+':part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('/')+'$')}));
export class QuarantinedOperation extends Error {constructor(){super('Operation unavailable under the current security policy');}}
// Only canonical absolute backend paths are accepted. Reject encodings rather
// than guessing how another proxy/router will decode or normalize them.
export function assertBackendOperation(method:string,target:string):void{
 const path=target.split('?')[0];if(!['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'].includes(method)||!target.startsWith('/api/v1/')||/[\\%#\u0000-\u0020]/.test(path)||path.includes('//')||target.includes('#'))throw new QuarantinedOperation();
 if(path.split('/').some(p=>p==='.'||p==='..'))throw new QuarantinedOperation();
 const canonical=path.replace(/\/+$/,'');
 // Match the exact operation. HEAD also inherits GET's prohibition, as in HTTP.
 if(rules.some(r=>(r.method===method||method==='HEAD'&&r.method==='GET')&&r.path.test(canonical)))throw new QuarantinedOperation();
}
export function guardedBackendFetch(input:RequestInfo|URL,init?:RequestInit):Promise<Response>{
 const url=input instanceof Request?input.url:String(input),method=(init?.method??(input instanceof Request?input.method:'GET')).toUpperCase();
 // Check raw path before URL normalizes dot segments. Origins remain validated
 // by each existing adapter; no input path or new forwarding authority is added.
 const raw=url.match(/^https?:\/\/[^/]+(\/.*)$/)?.[1];if(!raw)throw new QuarantinedOperation();assertBackendOperation(method,raw);
 return fetch(input,{...init,redirect:'error'});
}
