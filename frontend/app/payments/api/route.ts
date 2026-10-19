import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";
export async function POST(request:NextRequest){
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401});
 if(request.headers.get("origin")!==authConfig().origin)return NextResponse.json({error:{code:"FORBIDDEN"}},{status:403});
 try{const {path,body,key}=await request.json();if(typeof path!=="string"||!/^\/(?:me\/orders\/[a-f0-9-]{36}\/payment-attempts|me\/payment-attempts\/[a-f0-9-]{36}\/(?:evidence-uploads|evidence-finalize)|admin\/payment-attempts\/[a-f0-9-]{36}\/reviews)$/.test(path)||typeof key!=="string"||! /^[A-Za-z0-9._:-]{8,160}$/.test(key))return NextResponse.json({error:{code:"VALIDATION_ERROR"}},{status:400});
 const response=await fetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??"")}/api/v1${path}`,{method:"POST",cache:"no-store",redirect:"error",signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,"Content-Type":"application/json","Idempotency-Key":key},body:JSON.stringify(body)});
 return NextResponse.json(await response.json(),{status:response.status,headers:{"Cache-Control":"no-store"}});
 }catch{return NextResponse.json({error:{code:"PROVIDER_UNAVAILABLE"}},{status:503,headers:{"Cache-Control":"no-store"}});}
}

export async function GET(request:NextRequest){
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401});
 const path=request.nextUrl.searchParams.get('path')??'';
 if(!/^\/(?:(?:me|admin)\/orders\/[a-f0-9-]{36}\/payment-attempts|admin\/payment-evidence\/[a-f0-9-]{36})$/.test(path))return NextResponse.json({error:{code:'VALIDATION_ERROR'}},{status:400});
 try{const response=await fetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')}/api/v1${path}`,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`}});if(path.startsWith('/admin/payment-evidence/')&&response.ok)return new NextResponse(await response.arrayBuffer(),{headers:{'Content-Type':response.headers.get('Content-Type')??'application/octet-stream','Content-Disposition':'attachment; filename=payment-evidence','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});return NextResponse.json(await response.json(),{status:response.status,headers:{'Cache-Control':'no-store'}});}catch{return NextResponse.json({error:{code:'PROVIDER_UNAVAILABLE'}},{status:503});}
}
