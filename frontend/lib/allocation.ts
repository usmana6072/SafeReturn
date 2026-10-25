export type Allocation={state:"awaiting_verified_payment"|"reconciliation_pending"|"allocated";reason_code:null|"stock_shortage"|"financial_review"|"cancellation_review"|"template_review";requested_count:number;allocated_count:number};
export function parseAllocation(value:unknown):Allocation{
 if(!value||typeof value!=="object"||Array.isArray(value))throw Error("Unavailable");
 const v=value as Record<string,unknown>;
 if(Object.keys(v).sort().join(",")!=="allocated_count,reason_code,requested_count,state"||
  !["awaiting_verified_payment","reconciliation_pending","allocated"].includes(String(v.state))||
  !Number.isInteger(v.requested_count)||Number(v.requested_count)<1||Number(v.requested_count)>50||
  !Number.isInteger(v.allocated_count)||Number(v.allocated_count)<0||Number(v.allocated_count)>50||
  (v.state==="allocated"?(v.allocated_count!==v.requested_count||v.reason_code!==null):v.allocated_count!==0)||
  (v.state==="reconciliation_pending"?!["stock_shortage","financial_review","cancellation_review","template_review"].includes(String(v.reason_code)):v.reason_code!==null))throw Error("Unavailable");
 return v as Allocation;
}
