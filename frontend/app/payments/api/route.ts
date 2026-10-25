import {guardedBackendFetch} from '../../../lib/api/quarantine';
import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";
const safeHeaders={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"};
export async function POST(request:NextRequest){
 try{
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401,headers:safeHeaders});
 if(request.headers.get("origin")!==authConfig().origin)return NextResponse.json({error:{code:"FORBIDDEN"}},{status:403,headers:safeHeaders});
 const {path,body,key}=await request.json();if(typeof path!=="string"||!/^\/(?:me\/orders\/[a-f0-9-]{36}\/payment-attempts|me\/payment-attempts\/[a-f0-9-]{36}\/(?:evidence-uploads|evidence-finalize)|admin\/payment-attempts\/[a-f0-9-]{36}\/reviews|admin\/orders\/[a-f0-9-]{36}\/qr-allocation\/retry)$/.test(path)||typeof key!=="string"||! /^[A-Za-z0-9._:-]{8,160}$/.test(key))return NextResponse.json({error:{code:"VALIDATION_ERROR"}},{status:400,headers:safeHeaders});
 const response=await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??"")}/api/v1${path}`,{method:"POST",cache:"no-store",redirect:"error",signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,"Content-Type":"application/json","Idempotency-Key":key},body:JSON.stringify(body)});
 return NextResponse.json(await response.json(),{status:response.status,headers:safeHeaders});
 }catch{return NextResponse.json({error:{code:"PROVIDER_UNAVAILABLE"}},{status:503,headers:safeHeaders});}
}

export async function GET(request:NextRequest){
 try{
 if(request.headers.get("sec-fetch-site")==="cross-site"||(request.headers.has("origin")&&request.headers.get("origin")!==authConfig().origin))return NextResponse.json({error:{code:"FORBIDDEN"}},{status:403,headers:safeHeaders});
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401,headers:safeHeaders});
 const path=request.nextUrl.searchParams.get('path')??'';
 if(!/^\/(?:(?:me|admin)\/orders\/[a-f0-9-]{36}\/payment-attempts|me\/orders\/[a-f0-9-]{36}\/payment-instructions|admin\/payment-evidence\/[a-f0-9-]{36}|admin\/orders\/[a-f0-9-]{36}\/qr-allocation)$/.test(path))return NextResponse.json({error:{code:'VALIDATION_ERROR'}},{status:400,headers:safeHeaders});
 const response=await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')}/api/v1${path}`,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`}});if(path.startsWith('/admin/payment-evidence/')&&response.ok)return new NextResponse(await response.arrayBuffer(),{headers:{...safeHeaders,'Content-Type':response.headers.get('Content-Type')??'application/octet-stream','Content-Disposition':'attachment; filename=payment-evidence','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});return NextResponse.json(await response.json(),{status:response.status,headers:safeHeaders});}catch{return NextResponse.json({error:{code:'PROVIDER_UNAVAILABLE'}},{status:503,headers:safeHeaders});}
}
