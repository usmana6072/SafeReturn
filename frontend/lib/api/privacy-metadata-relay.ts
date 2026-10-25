import {guardedBackendFetch} from './quarantine';
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { privacyMetadataAdmitted } from '../privacy-metadata-gate';
import { canReviewPrivacy, exportQuery, projectExportPage } from '../admin-privacy-metadata';
import { verifiedSession } from '../auth/server';
import { staffState, StaffAccessError } from '../auth/staff';
import { authConfig } from '../auth/config';
import { validateOrigin } from './transport';
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
export async function privacyMetadataRelay(request:NextRequest){
  const fail=(status:number,code?:string)=>NextResponse.json({error:{code:code??({401:'AUTH_REQUIRED',403:'FORBIDDEN',404:'NOT_FOUND',422:'INVALID_QUERY',429:'RATE_LIMITED'} as Record<number,string>)[status]??'PRIVACY_METADATA_UNAVAILABLE'}},{status,headers});
  // Never parse/forward decisions, including reject/escalate and stale revisions.
  if(request.method!=='GET')return fail(405,'PRIVACY_ACTION_NOT_ALLOWED');
  if(!privacyMetadataAdmitted())return fail(503,'PRIVACY_METADATA_NOT_ADMITTED');
  try{
    if(request.headers.get('sec-fetch-site')==='cross-site'||request.headers.has('origin')&&request.headers.get('origin')!==authConfig().origin)return fail(403);
    let query:URLSearchParams;
    try{
      if(request.body||request.headers.has('content-encoding')||request.headers.has('transfer-encoding')||(request.headers.get('content-length')??'0')!=='0')throw Error();
      query=exportQuery(request.nextUrl.searchParams);
    }catch{return fail(422);}
    const session=await verifiedSession();if(!session)return fail(401);
    const permitted=(s:Awaited<ReturnType<typeof staffState>>)=>s.mfa_verified&&canReviewPrivacy(s.roles)&&s.capabilities.includes('privacy.exports');
    if(!permitted(await staffState(session.token)))return fail(403);
    const response=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1/admin/privacy/exports'+(query.size?'?'+query:''),{method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:'Bearer '+session.token,Accept:'application/json'}});
    if(!response.ok)return fail([400,401,403,404,422,429].includes(response.status)?response.status:503);
    if(response.status!==200||response.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json'||response.headers.has('content-disposition'))throw Error();
    const reader=response.body?.getReader();if(!reader)throw Error();let body='',size=0;const decoder=new TextDecoder('utf-8',{fatal:true});
    try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>262144)throw Error();body+=decoder.decode(value,{stream:true});}body+=decoder.decode();}finally{await reader.cancel();}
    const result=projectExportPage(JSON.parse(body),query);
    if(!permitted(await staffState(session.token)))return fail(403);
    return NextResponse.json(result,{headers});
  }catch(error){return fail(error instanceof StaffAccessError&&[401,403].includes(error.status)?error.status:503);}
}
