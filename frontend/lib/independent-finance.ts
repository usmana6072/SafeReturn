import {parseAllocation} from "./allocation";
export type FinanceDecision = {decision:'verify'|'reject'|'request_more_info';bank_verified:boolean;bank_match_reference?:string;settled_amount?:string;settled_currency?:string;reason:string};
export type FinanceSnapshot = {
 order_id:string;order_number:string;order_status:string;payment_status:string;fulfillment_status:string;amount_due:string;currency:'PKR';can_review:boolean;
 allocation:{state:'awaiting_verified_payment'|'reconciliation_pending'|'allocated';reason_code:string|null;requested_count:number;allocated_count:number};
 signals:string[];unavailable_checks:string[];history_limit:100;
 attempts:{attempt_id:string;state:string;amount:string;currency_code:string;sender_account:string|null;sender_holder:{holder?:string|null;transfer_reference?:string|null};evidence:{id:string;content_type:string;bytes_size:number}[]}[];
 reviews:{review_id:string;attempt_id:string;decision:string;bank_verified:boolean;reason:string;reviewed_at:string;settled_amount:string|null;settled_currency:string|null;settlement_reference_recorded:boolean}[];
};
const id=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const money=/^\d{1,10}\.\d{2}$/;
export function parseFinance(value:unknown):FinanceSnapshot {
 const v=value as FinanceSnapshot;
 if(!v||!id.test(v.order_id)||typeof v.order_number!=='string'||!money.test(v.amount_due)||v.currency!=='PKR'||typeof v.can_review!=='boolean'||v.history_limit!==100||!Array.isArray(v.attempts)||v.attempts.length>100||!Array.isArray(v.reviews)||v.reviews.length>100||!Array.isArray(v.signals)||!v.signals.every(s=>typeof s==='string')||!Array.isArray(v.unavailable_checks)||!v.unavailable_checks.every(s=>typeof s==='string'))throw Error('Invalid finance response');
 const exact=(o:object,keys:string[])=>{if(Object.keys(o).some(k=>!keys.includes(k)))throw Error('Unexpected finance field');};
 exact(v,['order_id','order_number','order_status','payment_status','fulfillment_status','amount_due','currency','can_review','allocation','signals','unavailable_checks','history_limit','attempts','reviews']);
 parseAllocation(v.allocation);
 for(const key of ['order_status','payment_status','fulfillment_status'] as const)if(typeof v[key]!=='string')throw Error('Invalid status');
 const a=v.allocation;
 if(!a||!['awaiting_verified_payment','reconciliation_pending','allocated'].includes(a.state)||!Number.isSafeInteger(a.requested_count)||!Number.isSafeInteger(a.allocated_count)||a.requested_count<0||a.allocated_count<0||(a.state==='allocated'?a.allocated_count!==a.requested_count:a.allocated_count!==0))throw Error('Invalid allocation response');
 for(const p of v.attempts)if(!id.test(p.attempt_id)||!money.test(p.amount)||typeof p.state!=='string'||typeof p.currency_code!=='string'||!p.sender_holder||!Array.isArray(p.evidence))throw Error('Invalid attempt response');
 for(const r of v.reviews)if(!id.test(r.review_id)||!id.test(r.attempt_id)||typeof r.reason!=='string'||typeof r.bank_verified!=='boolean'||!Number.isFinite(Date.parse(r.reviewed_at))||r.settled_amount!==null&&!money.test(r.settled_amount))throw Error('Invalid review response');
 for(const p of v.attempts){
  exact(p,['attempt_id','state','amount','currency_code','sender_account','sender_holder','evidence']);
  exact(p.sender_holder,['holder','transfer_reference']);
  if(p.sender_account!==null&&typeof p.sender_account!=='string'||Object.values(p.sender_holder).some(x=>x!==null&&typeof x!=='string')||p.evidence.length>1000)throw Error('Invalid private metadata');
  for(const e of p.evidence){exact(e,['id','content_type','bytes_size']);if(!id.test(e.id)||!['image/png','image/jpeg','application/pdf'].includes(e.content_type)||!Number.isSafeInteger(e.bytes_size)||e.bytes_size<1||e.bytes_size>5000000)throw Error('Invalid evidence');}
 }
 for(const r of v.reviews){exact(r,['review_id','attempt_id','decision','bank_verified','reason','reviewed_at','settled_amount','settled_currency','settlement_reference_recorded']);if(!['verify','reject','request_more_info'].includes(r.decision)||typeof r.settlement_reference_recorded!=='boolean'||r.settled_currency!==null&&typeof r.settled_currency!=='string')throw Error('Invalid review');}
 return v;
}

// No release switch, alternate backend URL, or bypass of guardedBackendFetch.
export async function financeCommand(command:{action:'read';order_id:string}|{action:'review';attempt_id:string;body:FinanceDecision;key:string}|{action:'retry';order_id:string;key:string}) {
 const response=await fetch('/admin/payments/finance-api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(command)});
 if(!response.ok)throw Error(response.status===401?'Sign in again.':response.status===403?'Finance permission and recent MFA are required.':'Independent finance remains unavailable. No success is assumed.');
 return response.json();
}
