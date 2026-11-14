import {guardedBackendFetch} from './quarantine';
import 'server-only';
import {NextRequest,NextResponse} from 'next/server';
import {verifiedSession} from '../auth/server';
import {staffState,StaffAccessError} from '../auth/staff';
import {authConfig} from '../auth/config';
import {validateOrigin} from './transport';
import * as C from '../printing-contract';
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
async function bounded(response:Response):Promise<unknown>{if(response.headers.get('content-type')?.split(';')[0].trim()!=='application/json')throw Error();const reader=response.body?.getReader();if(!reader)throw Error();let size=0,text='';const decoder=new TextDecoder('utf-8',{fatal:true});try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>524288)throw Error();text+=decoder.decode(value,{stream:true});}text+=decoder.decode();}finally{await reader.cancel();}return JSON.parse(text);}
export async function printingRelay(request:NextRequest){
 const error=(status:number,code='SERVICE_UNAVAILABLE')=>NextResponse.json({error:{code}},{status,headers});
 try{
  if(request.method!=='GET')return error(405,'METHOD_NOT_ALLOWED');
  if(request.headers.get('sec-fetch-site')==='cross-site'||request.headers.has('origin')&&request.headers.get('origin')!==authConfig().origin)return error(403,'FORBIDDEN');
  const session=await verifiedSession();if(!session)return error(401,'AUTH_REQUIRED');
  const security=await staffState(session.token);if(!security.mfa_verified||!security.roles.includes('operations'))return error(403,'FORBIDDEN');
  const params=request.nextUrl.searchParams,kind=params.get('kind')??'';
  const keys:Record<string,readonly string[]>={list:[...C.filterKeys,'limit','sort','cursor'],counts:C.filterKeys,detail:['job_id']};
  if(!Object.hasOwn(keys,kind)||[...params.keys()].some(k=>(k!=='kind'&&!keys[kind].includes(k))||params.getAll(k).length!==1))return error(422,'INVALID_QUERY');
  let target='';const query=new URLSearchParams();
  try{for(const key of keys[kind]){if(!params.has(key))continue;const value=C.query(key,params.get(key)!);if(kind==='detail')target=value;else query.set(key,value);}if(kind==='detail'&&!target)throw Error();if(query.has('created_from')&&query.has('created_before')&&Date.parse(query.get('created_from')!)>=Date.parse(query.get('created_before')!))throw Error();}catch{return error(422,'INVALID_QUERY');}
  const targetPath=kind==='detail'?'/admin/print-jobs/'+target:kind==='counts'?'/admin/print-jobs/counts':'/admin/print-jobs';
  const response=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1'+targetPath+(query.size?'?'+query:''),{method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:`Bearer ${session.token}`,Accept:'application/json'}});
  if(!response.ok){const status=[401,403,404,409,410,422].includes(response.status)?response.status:503;return error(status,status===401?'AUTH_REQUIRED':status===403?'FORBIDDEN':status===404?'NOT_FOUND':status===422?'INVALID_QUERY':status===409?'CONFLICT':status===410?'UNAVAILABLE':'SERVICE_UNAVAILABLE');}
  if(response.status!==200)return error(503);
  const value=await bounded(response),result=kind==='detail'?C.detail(value,target):kind==='counts'?C.counts(value):C.page(value,Number(query.get('limit')??20));
  const final=await staffState(session.token);if(!final.mfa_verified||!final.roles.includes('operations'))return error(403,'FORBIDDEN');
  return NextResponse.json(result,{headers});
 }catch(e){const status=e instanceof StaffAccessError&&[401,403].includes(e.status)?e.status:503;return error(status,status===401?'AUTH_REQUIRED':status===403?'FORBIDDEN':'SERVICE_UNAVAILABLE');}
}
