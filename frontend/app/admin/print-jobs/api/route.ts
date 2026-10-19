import {NextRequest,NextResponse} from 'next/server';
import {verifiedSession} from '../../../../lib/auth/server';
import {authConfig} from '../../../../lib/auth/config';
import {validateOrigin} from '../../../../lib/api/transport';
const safe={ 'Cache-Control':'no-store' };
async function relay(request:NextRequest,method:'GET'|'POST'){
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:'AUTH_REQUIRED'}},{status:401,headers:safe});
 if(method==='POST'&&request.headers.get('origin')!==authConfig().origin)return NextResponse.json({error:{code:'FORBIDDEN'}},{status:403,headers:safe});
 try{const input=method==='POST'?await request.json():{path:request.nextUrl.searchParams.get('path')};const {path,body,key}=input;
 const allowed=method==='GET'?/^\/admin\/(?:orders\/[a-f0-9-]{36}\/print-jobs|print-jobs\/[a-f0-9-]{36})$/:/^\/admin\/(?:orders\/[a-f0-9-]{36}\/print-jobs|print-artifacts\/[a-f0-9-]{36}\/download-grants|print-jobs\/[a-f0-9-]{36}\/qa|print-downloads)$/;
 if(typeof path!=='string'||!allowed.test(path)||method==='POST'&&(typeof key!=='string'||!/^[A-Za-z0-9._:-]{8,160}$/.test(key)))return NextResponse.json({error:{code:'VALIDATION_ERROR'}},{status:400,headers:safe});
 const r=await fetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')+'/api/v1'+path,{method,cache:'no-store',redirect:'error',signal:AbortSignal.timeout(30000),headers:{Authorization:`Bearer ${session.token}`,...(method==='POST'?{'Content-Type':'application/json','Idempotency-Key':key}:{})},...(method==='POST'?{body:JSON.stringify(body)}:{})});
 if(path==='/admin/print-downloads'&&r.ok)return new NextResponse(await r.arrayBuffer(),{headers:{...safe,'Content-Type':'application/pdf','Content-Disposition':'attachment; filename=SR-print.pdf','X-Content-Type-Options':'nosniff'}});
 return NextResponse.json(await r.json(),{status:r.status,headers:safe});
 }catch{return NextResponse.json({error:{code:'PROVIDER_UNAVAILABLE'}},{status:503,headers:safe});}
}
export const POST=(r:NextRequest)=>relay(r,'POST');export const GET=(r:NextRequest)=>relay(r,'GET');
