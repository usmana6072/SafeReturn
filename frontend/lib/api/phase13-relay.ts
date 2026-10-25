import {guardedBackendFetch} from './quarantine';
import 'server-only';
import {NextRequest,NextResponse} from 'next/server';
import {verifiedSession} from '../auth/server';
import {staffState,StaffAccessError} from '../auth/staff';
import {authConfig} from '../auth/config';
import {validateOrigin} from './transport';
import {dashboardTrendsAdmitted,auditEventsAdmitted,currentStaffSecurityAdmitted,backendLivenessAdmitted} from '../phase13-gate';
import {phase13Query,parseAudit,parseOwnSecurity,parseTrends,parseLiveness,type Phase13Kind} from '../phase13-contract';
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
async function json(response:Response,max:number){if(response.status!==200||response.headers.has('content-disposition')||response.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json')throw Error();const reader=response.body?.getReader();if(!reader)throw Error();let size=0,body='';const decoder=new TextDecoder('utf-8',{fatal:true});try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>max)throw Error();body+=decoder.decode(value,{stream:true});}body+=decoder.decode();}finally{await reader.cancel();}return JSON.parse(body) as unknown;}
export async function phase13Relay(request:NextRequest,kind:Phase13Kind){
 const fail=(status:number,code?:string)=>NextResponse.json({error:{code:code??(status===401?'AUTH_REQUIRED':status===403?'REAUTH_OR_ACCESS_REQUIRED':status===422?'INVALID_QUERY':'METADATA_UNAVAILABLE')}},{status,headers});
 if(request.method!=='GET')return fail(405,'METHOD_NOT_ALLOWED');
 if(kind==='summary')return fail(503,'SUMMARY_QUARANTINED');
 const admitted={trends:dashboardTrendsAdmitted,audit:auditEventsAdmitted,security:currentStaffSecurityAdmitted,liveness:backendLivenessAdmitted};if(!admitted[kind]())return fail(503,'LIVE_INTEGRATION_NOT_ADMITTED');
 try{
 if(request.headers.get('sec-fetch-site')==='cross-site'||request.headers.has('origin')&&request.headers.get('origin')!==authConfig().origin)return fail(403);
 let q:URLSearchParams;try{if(request.body||(request.headers.get('content-length')??'0')!=='0'||request.headers.has('content-encoding')||request.headers.has('transfer-encoding'))throw Error();q=phase13Query(request.nextUrl.searchParams,kind);}catch{return fail(422);}
 const session=await verifiedSession();if(!session)return fail(401);
 // Own security permits the existing AAL1 bootstrap; never requires a role grant.
 const allowed=(s:Awaited<ReturnType<typeof staffState>>)=>kind==='security'||s.mfa_verified&&(kind==='audit'?s.roles.includes('security_admin')&&s.capabilities.includes('audit.search'):kind==='liveness'?s.roles.some(r=>['operations','security_admin'].includes(r))&&s.capabilities.includes('notifications.manage'):s.roles.some(r=>['operations','finance','support','security_admin','superadmin'].includes(r)));
 const before=kind==='security'?null:await staffState(session.token);if(before&&!allowed(before))return fail(403);
 const path={trends:'/api/v1/admin/dashboard/trends',audit:'/api/v1/admin/audit-events',security:'/api/v1/me/staff-security',liveness:'/api/v1/health/live'}[kind];
 const response=await guardedBackendFetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+path+(q.size?'?'+q:''),{method:'GET',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(kind==='liveness'?5000:10000),headers:{Accept:'application/json',...(kind==='liveness'?{}:{Authorization:'Bearer '+session.token})}});
 if(!response.ok)return fail([401,403,404,422,429].includes(response.status)?response.status:503);
 const raw=await json(response,kind==='trends'?64000:262144),after=kind==='security'?null:await staffState(session.token);if(after&&!allowed(after))return fail(403);
 const result=kind==='security'?parseOwnSecurity(raw):kind==='liveness'?parseLiveness(raw):kind==='audit'?parseAudit(raw,q):parseTrends(raw,q,after!.roles.filter(r=>before!.roles.includes(r)));
 return NextResponse.json(result,{headers});
 }catch(e){return fail(e instanceof StaffAccessError&&[401,403].includes(e.status)?e.status:503);}
}
