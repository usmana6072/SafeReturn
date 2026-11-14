export const notificationStatuses = ['pending', 'leased', 'retry', 'sent', 'dead'] as const;
export const retryReasons = ['provider_recovered', 'recipient_reverified'] as const;
export type NotificationStatus = typeof notificationStatuses[number];
export type RetryReason = typeof retryReasons[number];
export type NotificationAttempt = {attempt_number:number; outcome:'success'|'transient_failure'|'permanent_failure'|'unknown'; attempted_at:string; finished_at:string|null; error_code:string|null};
export type OutboxEvent = {id:string; event_type:'finder_message.created'|'unsupported'; status:NotificationStatus; attempt_count:number; created_at:string; next_attempt_at:string; lease_until:string|null; sent_at:string|null; last_error_code:string|null; first_attempt_at:string|null; due_lag_seconds:number|null; retry_blocked_reason:string|null; attempts:NotificationAttempt[]|null; next_attempt_before:number|null};
export type NotificationPage = {items:OutboxEvent[]; next_cursor:string|null; current_template:{identifier:'finder-message/v1'; fingerprint:string; historical_version:'not_recorded'; review:'4.4C_pending'}};
export type RetryInput = {id:string; key:string; body:{expected_attempt_count:number; reason:RetryReason; confirmed:true}};
const codes = ['provider_network','provider_invalid_response','provider_not_configured','recipient_unavailable','recipient_decryption_failed','invalid_recipient','attempts_exhausted','idempotency_window_expired','provider_failure'];
const blocks = ['not_dead','unsupported_event','attempt_budget_exhausted','manual_review_required','already_accepted','recipient_unavailable'];
const outcomes = ['success','transient_failure','permanent_failure','unknown'];
function deny(): never { throw Error('Invalid notification contract'); }
function object(value:unknown, keys:readonly string[]):Record<string,unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return deny();
  const row=value as Record<string,unknown>;
  if (Object.keys(row).length!==keys.length || keys.some(key=>!Object.hasOwn(row,key))) return deny();
  return row;
}
export function notificationId(value:unknown):string {
  if (typeof value!=='string' || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value)) return deny();
  return value.toLowerCase();
}
function integer(value:unknown,min=0,max=2147483647):number { if(typeof value!=='number'||!Number.isSafeInteger(value)||value<min||value>max)return deny();return value; }
function timestamp(value:unknown):string { if(typeof value!=='string'||value.length>40||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(value)||!Number.isFinite(Date.parse(value)))return deny();return value; }
function optionalTime(value:unknown):string|null { return value===null?null:timestamp(value); }
function member<T extends string>(value:unknown,values:readonly T[]):T { if(typeof value!=='string'||!values.includes(value as T))return deny();return value as T; }
function safeCode(value:unknown):string|null { if(value===null)return null;if(typeof value!=='string'||!(codes.includes(value)||/^provider_http_[1-5][0-9]{2}$/.test(value)))return deny();return value; }
function cursor(value:unknown):string|null {
  if(value===null)return null;
  if(typeof value!=='string'||value.length>200||!value.length||!/^[A-Za-z0-9_-]+$/.test(value))return deny();
  try { const decoded:unknown=JSON.parse(atob(value.replace(/-/g,'+').replace(/_/g,'/')));if(!Array.isArray(decoded)||decoded.length!==2)return deny();timestamp(decoded[0]);notificationId(decoded[1]); }catch{return deny();}
  return value;
}
export function notificationQuery(input:URLSearchParams):URLSearchParams {
  if(input.toString().length>1024)return deny();
  const result=new URLSearchParams();
  for(const [key,value] of input){
    if(!['limit','cursor','status','id','attempt_limit','attempt_before'].includes(key)||input.getAll(key).length!==1)return deny();
    if(key==='id')result.set(key,notificationId(value));
    else if(key==='status')result.set(key,member(value,notificationStatuses));
    else if(key==='cursor')result.set(key,cursor(value)!);
    else {if(!/^[1-9]\d{0,9}$/.test(value))return deny();result.set(key,String(integer(Number(value),1,key==='attempt_before'?2147483647:100)));}
  }
  if((result.has('attempt_limit')||result.has('attempt_before'))&&!result.has('id'))return deny();
  if(result.has('id')&&(result.has('status')||result.has('cursor')))return deny();
  return result;
}
function parseAttempt(value:unknown):NotificationAttempt {
  const a=object(value,['attempt_number','outcome','attempted_at','finished_at','error_code']);
  return {attempt_number:integer(a.attempt_number,1),outcome:member(a.outcome,outcomes) as NotificationAttempt['outcome'],attempted_at:timestamp(a.attempted_at),finished_at:optionalTime(a.finished_at),error_code:safeCode(a.error_code)};
}
function parseEvent(value:unknown,detail:boolean,attemptLimit:number):OutboxEvent {
  const e=object(value,['id','event_type','status','attempt_count','created_at','next_attempt_at','lease_until','sent_at','last_error_code','first_attempt_at','due_lag_seconds','retry_blocked_reason','attempts','next_attempt_before']);
  let attempts:NotificationAttempt[]|null=null;
  if(detail){if(!Array.isArray(e.attempts)||e.attempts.length>attemptLimit)return deny();attempts=e.attempts.map(parseAttempt);if(attempts.some((a,i)=>a.attempt_number>Number(e.attempt_count)||i>0&&a.attempt_number>=attempts![i-1].attempt_number))return deny();}
  else if(e.attempts!==null||e.next_attempt_before!==null)return deny();
  const next=e.next_attempt_before===null?null:integer(e.next_attempt_before,1);
  if(next!==null&&(!attempts?.length||next!==attempts.at(-1)!.attempt_number))return deny();
  return {id:notificationId(e.id),event_type:member(e.event_type,['finder_message.created','unsupported']),status:member(e.status,notificationStatuses),attempt_count:integer(e.attempt_count),created_at:timestamp(e.created_at),next_attempt_at:timestamp(e.next_attempt_at),lease_until:optionalTime(e.lease_until),sent_at:optionalTime(e.sent_at),last_error_code:safeCode(e.last_error_code),first_attempt_at:optionalTime(e.first_attempt_at),due_lag_seconds:e.due_lag_seconds===null?null:integer(e.due_lag_seconds,0,Number.MAX_SAFE_INTEGER),retry_blocked_reason:e.retry_blocked_reason===null?null:member(e.retry_blocked_reason,blocks),attempts,next_attempt_before:next};
}
export function notificationPage(value:unknown,query=new URLSearchParams()):NotificationPage {
  const p=object(value,['items','next_cursor','current_template']),q=notificationQuery(query),detail=q.has('id');
  if(!Array.isArray(p.items)||p.items.length>Number(q.get('limit')??20)||detail&&p.items.length>1)return deny();
  const items=p.items.map(v=>parseEvent(v,detail,Number(q.get('attempt_limit')??20)));
  if(new Set(items.map(i=>i.id)).size!==items.length||detail&&items.some(i=>i.id!==q.get('id'))||q.has('status')&&items.some(i=>i.status!==q.get('status')))return deny();
  const t=object(p.current_template,['identifier','fingerprint','historical_version','review']);
  if(t.identifier!=='finder-message/v1'||t.historical_version!=='not_recorded'||t.review!=='4.4C_pending'||typeof t.fingerprint!=='string'||!/^[a-f0-9]{64}$/.test(t.fingerprint))return deny();
  const next=cursor(p.next_cursor);if(next!==null&&(!items.length||detail))return deny();
  return {items,next_cursor:next,current_template:{identifier:t.identifier,fingerprint:t.fingerprint,historical_version:t.historical_version,review:t.review}};
}
export function notificationRetry(value:unknown):RetryInput {
  const v=object(value,['id','key','body']),b=object(v.body,['expected_attempt_count','reason','confirmed']);
  if(typeof v.key!=='string'||!/^[A-Za-z0-9._:-]{8,160}$/.test(v.key)||b.confirmed!==true)return deny();
  return {id:notificationId(v.id),key:v.key,body:{expected_attempt_count:integer(b.expected_attempt_count,1),reason:member(b.reason,retryReasons),confirmed:true}};
}
export function notificationReceipt(value:unknown,input:RetryInput) {
  const r=object(value,['id','status','expected_attempt_count']);
  if(notificationId(r.id)!==input.id||r.status!=='retry'||r.expected_attempt_count!==input.body.expected_attempt_count)return deny();
  return {id:input.id,status:'retry' as const,expected_attempt_count:input.body.expected_attempt_count};
}
export const canReadNotifications=(roles:readonly string[])=>roles.some(r=>r==='operations'||r==='security_admin');
export const outboxChannel=(event:OutboxEvent)=>event.event_type==='finder_message.created'?'email':'unavailable';
