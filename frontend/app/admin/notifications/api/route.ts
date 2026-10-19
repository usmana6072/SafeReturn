import {NextRequest,NextResponse} from "next/server";
import {verifiedSession} from "../../../../lib/auth/server";
import {authConfig} from "../../../../lib/auth/config";
import {validateOrigin} from "../../../../lib/api/transport";
const headers={"Cache-Control":"private, no-store"};
async function relay(request:NextRequest,method:"GET"|"POST"){
 try{
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401,headers});
 let path='/admin/notification-outbox',body,key;
 if(method==='GET'){
 const allowed=['limit','cursor','status','id','attempt_limit','attempt_before'];
 if([...request.nextUrl.searchParams.keys()].some(k=>!allowed.includes(k)||request.nextUrl.searchParams.getAll(k).length!==1))return NextResponse.json({error:{code:'INVALID_QUERY'}},{status:400,headers});
 path+='?'+request.nextUrl.searchParams.toString();
 }else{
 if(request.headers.get('origin')!==authConfig().origin)return NextResponse.json({error:{code:'FORBIDDEN'}},{status:403,headers});
 const input=await request.json();if(typeof input.id!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(input.id)||typeof input.key!=='string'||!/^[A-Za-z0-9._:-]{8,160}$/.test(input.key))return NextResponse.json({error:{code:'INVALID_REQUEST'}},{status:400,headers});
 path+='/'+input.id+'/retry';body=input.body;key=input.key;
 }
 const r=await fetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1'+path,{method,cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,...method==='POST'?{'Content-Type':'application/json','Idempotency-Key':key}:{}},...method==='POST'?{body:JSON.stringify(body)}:{}});
 return NextResponse.json(await r.json(),{status:r.status,headers});
 }catch{return NextResponse.json({error:{code:'OPERATIONS_UNAVAILABLE'}},{status:503,headers});}
}
export const GET=(r:NextRequest)=>relay(r,'GET');export const POST=(r:NextRequest)=>relay(r,'POST');
