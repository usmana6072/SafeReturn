import { NextRequest, NextResponse } from "next/server";
import { verifiedSession } from "../../../lib/auth/server";
import { authConfig } from "../../../lib/auth/config";
import { validateOrigin } from "../../../lib/api/transport";
export async function POST(request:NextRequest){
 const session=await verifiedSession();if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401});
 if(request.headers.get("origin")!==authConfig().origin)return NextResponse.json({error:{code:"FORBIDDEN"}},{status:403});
 try{const {path,body,key}=await request.json();if(typeof path!=="string"||!/^\/me\/checkout\/quotes(?:\/[a-f0-9-]{36}\/confirm)?$/.test(path)||typeof key!=="string"||! /^[A-Za-z0-9._:-]{8,160}$/.test(key))return NextResponse.json({error:{code:"VALIDATION_ERROR"}},{status:400});
 const response=await fetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??"")}/api/v1${path}`,{method:"POST",cache:"no-store",redirect:"error",signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,"Content-Type":"application/json","Idempotency-Key":key},body:JSON.stringify(body)});
 return NextResponse.json(await response.json(),{status:response.status,headers:{"Cache-Control":"no-store"}});
 }catch{return NextResponse.json({error:{code:"PROVIDER_UNAVAILABLE"}},{status:503,headers:{"Cache-Control":"no-store"}});}
}
