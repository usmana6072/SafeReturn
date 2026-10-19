import {NextRequest,NextResponse} from "next/server";
import {verifiedSession} from "../../../../lib/auth/server";
import {authConfig} from "../../../../lib/auth/config";
import {validateOrigin} from "../../../../lib/api/transport";
const safe={"Cache-Control":"no-store"};
async function relay(request:NextRequest,method:"GET"|"POST"|"PATCH") {
 try {
 const session=await verifiedSession(); if(!session)return NextResponse.json({error:{code:"AUTH_REQUIRED"}},{status:401,headers:safe});
 if(method!=="GET"&&request.headers.get("origin")!==authConfig().origin)return NextResponse.json({error:{code:"FORBIDDEN"}},{status:403,headers:safe});
 const input=method==="GET"?{path:request.nextUrl.searchParams.get("path"),body:undefined,key:undefined}:await request.json();const {path,body,key}=input;
 const validGet=typeof path==='string'&&(()=>{const u=new URL(path,'http://local');if(u.origin!=='http://local'||u.hash||!path.startsWith('/admin/'))return false;const fields=u.pathname==='/admin/shipments'?['limit','cursor','sort','order_id','order_number','status','carrier','tracking_reference','requires_review','created_from','created_before']:/^\/admin\/shipments\/[a-f0-9-]{36}$/.test(u.pathname)?['pair_limit','pair_cursor']:u.pathname==='/admin/orders/ready-to-ship'?['limit','cursor','status']:[];return fields.length>0&&[...u.searchParams.keys()].every(k=>fields.includes(k)&&u.searchParams.getAll(k).length===1);})();
 if(typeof path!=="string"||!(method==="GET"?(validGet||/^\/admin\/orders\/[a-f0-9-]{36}$/.test(path)):method==="POST"?path==='/admin/shipments':/^\/admin\/shipments\/[a-f0-9-]{36}$/.test(path))||method!=="GET"&&(typeof key!=="string"||!/^[A-Za-z0-9._:-]{8,160}$/.test(key)))return NextResponse.json({error:{code:"VALIDATION_ERROR"}},{status:400,headers:safe});
 const r=await fetch(validateOrigin(process.env.SAFERETURN_API_ORIGIN??"")+"/api/v1"+path,{method,cache:"no-store",redirect:"error",signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,...(method!=="GET"?{"Content-Type":"application/json","Idempotency-Key":key}:{})},...(method!=="GET"?{body:JSON.stringify(body)}:{})});
 return NextResponse.json(await r.json(),{status:r.status,headers:safe});
 }catch{return NextResponse.json({error:{code:"PROVIDER_UNAVAILABLE"}},{status:503,headers:safe});}
}
export const GET=(r:NextRequest)=>relay(r,"GET");export const POST=(r:NextRequest)=>relay(r,"POST");export const PATCH=(r:NextRequest)=>relay(r,"PATCH");
