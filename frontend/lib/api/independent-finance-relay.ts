import {NextRequest,NextResponse} from 'next/server';
import {verifiedSession} from '../auth/server';
import {staffState} from '../auth/staff';
import {authConfig} from '../auth/config';
import {validateOrigin} from './transport';
import {guardedBackendFetch} from './quarantine';
import {parseFinance} from '../independent-finance';
const uuid=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const headers={'Cache-Control':'private, no-store'};

/** Prepared transport. Not called by the closed production route. Even if called,
 * original quarantine checks still block all three upstream operations. */
export async function independentFinanceRelay(request:NextRequest){
 const fail=(status:number)=>NextResponse.json({error:{code:status===401?'AUTH_REQUIRED':status===403?'FORBIDDEN':status===422?'VALIDATION_ERROR':'INDEPENDENT_FINANCE_UNAVAILABLE'}},{status,headers});
 try{
  if(request.headers.get('origin')!==authConfig().origin)return fail(403);
  const session=await verifiedSession();if(!session)return fail(401);
  const state=await staffState(session.token);
  if(!state.mfa_verified||!state.roles.includes('finance')||!state.capabilities.includes('payments.review'))return fail(403);
  const raw=await request.text();if(raw.length>8000)return fail(422);
  const c=JSON.parse(raw);let path:string,body:unknown,method='POST';
  if(c.action==='read'&&uuid.test(c.order_id)&&Object.keys(c).sort().join(',')==='action,order_id'){
   path='/admin/finance/reconciliation?order_id='+c.order_id;method='GET';
  }else if(c.action==='review'&&uuid.test(c.attempt_id)&&Object.keys(c).sort().join(',')==='action,attempt_id,body,key'){
   const b=c.body;if(!b||!['verify','reject','request_more_info'].includes(b.decision)||typeof b.bank_verified!=='boolean'||typeof b.reason!=='string'||b.reason.trim().length<4||b.reason.length>1000||Object.keys(b).some(k=>!['decision','bank_verified','bank_match_reference','settled_amount','settled_currency','reason'].includes(k)))return fail(422);
   if(b.decision==='verify'&&(b.bank_verified!==true||typeof b.bank_match_reference!=='string'||b.bank_match_reference.trim().length<4||b.bank_match_reference.length>120||!/^\d{1,10}\.\d{2}$/.test(b.settled_amount)||b.settled_currency!=='PKR'))return fail(422);
   if(b.decision!=='verify'&&(b.bank_verified||b.bank_match_reference!=null||b.settled_amount!=null||b.settled_currency!=null))return fail(422);
   path=`/admin/payment-attempts/${c.attempt_id}/reviews`;body=b;
  }else if(c.action==='retry'&&uuid.test(c.order_id)&&Object.keys(c).sort().join(',')==='action,key,order_id'){
   path=`/admin/orders/${c.order_id}/qr-allocation/retry`;body={confirmed:true};
  }else return fail(422);
  if(method==='POST'&&(typeof c.key!=='string'||! /^[A-Za-z0-9._:-]{8,160}$/.test(c.key)))return fail(422);
  const result=await guardedBackendFetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN??'')}/api/v1${path}`,{method,redirect:'error',cache:'no-store',signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${session.token}`,Origin:authConfig().origin,...(method==='POST'?{'Content-Type':'application/json','Idempotency-Key':c.key}:{})},...(body?{body:JSON.stringify(body)}:{})});
  if(!result.ok)return fail([401,403,404,409,422,429].includes(result.status)?result.status:503);
  const reader=result.body?.getReader();if(!reader)return fail(503);
  let size=0;const chunks:Uint8Array[]=[];
  try{for(;;){const chunk=await reader.read();if(chunk.done)break;size+=chunk.value.byteLength;if(size>1000000)return fail(503);chunks.push(chunk.value);}}finally{await reader.cancel();}
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  const value=JSON.parse(new TextDecoder().decode(bytes));
  if(c.action==='read')return NextResponse.json(parseFinance(value),{headers});
  // Only safe confirmation identifiers; refresh authoritative state afterwards.
  if(!uuid.test(value.order_id)||c.action==='review'&&!uuid.test(value.review_id))return fail(503);
  return NextResponse.json({order_id:value.order_id,...(c.action==='review'?{review_id:value.review_id}:{})},{headers});
 }catch{return fail(503);}
}
