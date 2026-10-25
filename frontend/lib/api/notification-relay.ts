import {guardedBackendFetch} from './quarantine';
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { notificationReadAdmitted, notificationRetryAdmitted } from '../notification-gate';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
import { canReadNotifications, notificationPage, notificationQuery, notificationReceipt, notificationRetry, type RetryInput } from '../admin-notification-contract';
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
async function boundedJson(message:Request|Response,max:number):Promise<unknown>{
  if(message.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json')throw Error();
  const stream=message.body?.getReader();if(!stream)throw Error();
  let size=0,body='';const decoder=new TextDecoder('utf-8',{fatal:true});
  try{for(;;){const {done,value}=await stream.read();if(done)break;size+=value.byteLength;if(size>max)throw Error();body+=decoder.decode(value,{stream:true});}body+=decoder.decode();}finally{await stream.cancel();}
  return JSON.parse(body);
}
export async function notificationRelay(request:NextRequest){
  const fail=(status:number,code?:string)=>NextResponse.json({error:{code:code??({401:'AUTH_REQUIRED',403:'FORBIDDEN',404:'NOT_FOUND',409:'RETRY_CONFLICT',412:'STALE_ATTEMPT',422:'INVALID_REQUEST',429:'RATE_LIMITED'} as Record<number,string>)[status]??'NOTIFICATIONS_UNAVAILABLE'}},{status,headers});
  if(!notificationReadAdmitted())return fail(503,'NOTIFICATIONS_NOT_ADMITTED');
  if(!['GET','POST'].includes(request.method))return fail(405,'METHOD_NOT_ALLOWED');
  if(request.method==='POST'&&!notificationRetryAdmitted())return fail(503,'NOTIFICATION_RETRY_NOT_ADMITTED');
  try{
    const post=request.method==='POST';
    if(request.headers.get('sec-fetch-site')==='cross-site'||(post||request.headers.has('origin'))&&request.headers.get('origin')!==authConfig().origin)return fail(403);
    let q:URLSearchParams,input:RetryInput|undefined;
    try{
      if(request.headers.has('content-encoding')||request.headers.has('transfer-encoding'))throw Error();
      if(post){if(request.nextUrl.search)throw Error();input=notificationRetry(await boundedJson(request,2048));q=new URLSearchParams();}
      else{if(request.body||(request.headers.get('content-length')??'0')!=='0')throw Error();q=notificationQuery(request.nextUrl.searchParams);}
    }catch{return fail(422);}
    const session=await verifiedSession();if(!session)return fail(401);
    const permitted=(s:Awaited<ReturnType<typeof staffState>>)=>s.mfa_verified&&canReadNotifications(s.roles)&&s.capabilities.includes('notifications.manage');
    if(!permitted(await staffState(session.token)))return fail(403);
    const path='/api/v1/admin/notification-outbox'+(post?'/'+input!.id+'/retry':q.size?'?'+q:'');
    const response=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+path,{method:request.method,cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:'Bearer '+session.token,Accept:'application/json',...(post?{'Content-Type':'application/json','Idempotency-Key':input!.key}:{})},...(post?{body:JSON.stringify(input!.body)}:{})});
    if(!response.ok)return fail([400,401,403,404,409,412,422,429].includes(response.status)?response.status:503);
    if(response.status!==(post?202:200))throw Error();
    const raw=await boundedJson(response,262144),result=post?notificationReceipt(raw,input!):notificationPage(raw,q);
    if(!permitted(await staffState(session.token)))return fail(403);
    return NextResponse.json(result,{status:post?202:200,headers});
  }catch(error){return fail(error instanceof StaffAccessError&&[401,403].includes(error.status)?error.status:503);}
}
