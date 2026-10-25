import {parseDashboardTrends,type Trends} from './dashboard-contract';
import {parseStaffSecurity,type StaffSecurityState} from './auth/staff-contract';
export type Phase13Kind='summary'|'trends'|'audit'|'security'|'liveness';
export const auditActions=['account.profile.update','account.deletion.requested','profile.updated','support_case.created','support_case.changed','support_case.read','privacy.export.requested','privacy.export.decided','privacy.export.granted','privacy.export.consumed','privacy.export.ready','privacy.export.generation_failed','storage.retention_hold_placed','storage.retention_hold_released','storage.cleanup_retry','storage.deletion_authorized','storage.artifact_deleted','finance.sheet_sync_retry','payment.evidence.read','payment.finance.read','shipment.created','shipment.updated','audit.search'] as const;
export const auditTargets=['user_profile','qr','tag_pair','order','shipment','payment_attempt','payment_evidence','print_artifact','print_job','support_case','privacy_export','finance_sheet_sync','audit_search'] as const;
export type AuditEvent={id:string;occurred_at:string;actor_kind:string;actor_user_id:string|null;action:string;target_type:string;target_id:string|null};
export type AuditPage={items:AuditEvent[];next_cursor:string|null;scope:'security_metadata'};
function bad():never{throw Error('Invalid metadata');}
function object(v:unknown,keys:readonly string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))return bad();return v as Record<string,unknown>;}
export function metadataId(v:unknown):string{if(typeof v!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v))return bad();return v.toLowerCase();}
export function metadataTime(v:unknown):string{if(typeof v!=='string'||v.length>40||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(v)||!Number.isFinite(Date.parse(v)))return bad();return v;}
function cursor(v:unknown):string|null{if(v===null)return null;if(typeof v!=='string'||!v.length||v.length>200||!/^[A-Za-z0-9_-]+$/.test(v))return bad();try{const p=JSON.parse(atob(v.replace(/-/g,'+').replace(/_/g,'/')));if(!Array.isArray(p)||p.length!==2)return bad();metadataTime(p[0]);metadataId(p[1]);}catch{return bad();}return v;}
export function phase13Query(input:URLSearchParams,kind:Phase13Kind):URLSearchParams{
 if(input.toString().length>2048)return bad();const q=new URLSearchParams();
 for(const [key,v] of input){if(input.getAll(key).length!==1||!(kind==='trends'?['display_timezone']:kind==='audit'?['actor_id','target_id','target_type','action','start','end','limit','cursor']:[]).includes(key))return bad();
 if(key==='display_timezone'){if(!['UTC','Asia/Karachi'].includes(v))return bad();}
 else if(key==='limit'){if(!/^[1-9]\d{0,2}$/.test(v)||Number(v)>100)return bad();}
 else if(key==='cursor')cursor(v);
 else if(key==='start'||key==='end')metadataTime(v);
 else if(key==='actor_id'||key==='target_id')metadataId(v);
 else if(key==='action'){if(!(auditActions as readonly string[]).includes(v))return bad();}
 else if(!(auditTargets as readonly string[]).includes(v))return bad();q.set(key,v);}
 if(kind==='audit'&&(q.has('start')||q.has('end'))){const end=q.has('end')?Date.parse(q.get('end')!):Date.now(),start=q.has('start')?Date.parse(q.get('start')!):end-7*86400000;if(end<=start||end-start>31*86400000)return bad();}return q;
}
export function parseAudit(v:unknown,q=new URLSearchParams()):AuditPage{phase13Query(q,'audit');const p=object(v,['items','next_cursor','scope']);if(p.scope!=='security_metadata'||!Array.isArray(p.items)||p.items.length>Number(q.get('limit')??20))return bad();const items=p.items.map(value=>{const r=object(value,['id','occurred_at','actor_kind','actor_user_id','action','target_type','target_id']);if(!['customer','staff','system','anonymous'].includes(r.actor_kind as string))return bad();return {id:metadataId(r.id),occurred_at:metadataTime(r.occurred_at),actor_kind:r.actor_kind as string,actor_user_id:r.actor_user_id===null?null:metadataId(r.actor_user_id),action:(auditActions as readonly unknown[]).includes(r.action)?r.action as string:'restricted_event',target_type:(auditTargets as readonly unknown[]).includes(r.target_type)?r.target_type as string:'restricted',target_id:r.target_id===null?null:metadataId(r.target_id)};});if(new Set(items.map(r=>r.id)).size!==items.length)return bad();const next=cursor(p.next_cursor);if(!items.length&&next)return bad();return {items,next_cursor:next,scope:'security_metadata'};}
export function parseOwnSecurity(v:unknown):StaffSecurityState{object(v,['roles','mfa_verified','capabilities']);return parseStaffSecurity(v);}
export function parseLiveness(v:unknown):{status:'ok'}{const r=object(v,['status']);if(r.status!=='ok')return bad();return {status:'ok'};}
export function parseTrends(v:unknown,q:URLSearchParams,roles:readonly string[]):Trends{return parseDashboardTrends(v,roles,q.get('display_timezone')??'UTC');}
