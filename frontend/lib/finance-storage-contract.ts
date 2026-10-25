export type MetadataMode='finance'|'storage';
export const syncStates=['pending','synced','retry','failed'] as const;
export const artifactTypes=['print_artifact','payment_evidence'] as const;
const jobStates=['pending','leased','retry','completed','dead'] as const;
const failureCodes=['provider_unavailable','provider_failure','provider_auth_failure','provider_read_failed','google_sheets_not_configured','google_sheets_invalid_credentials','google_sheets_not_approved','sheet_columns_not_approved','sheet_row_key_mismatch','duplicate_sheet_rows','sheet_version_conflict','policy_not_approved','on_hold','no_retention_policy','retention_period_not_elapsed','object_delete_failed','attempts_exhausted','unrecognized_failure'] as const;
export type SyncRecord={id:string;order_id:string;last_export_version:number;status:typeof syncStates[number];attempt_count:number;last_error_code:string|null;last_synced_at:string|null;updated_at:string};
export type CleanupMetadata={id:string;status:typeof jobStates[number];attempt_count:number;last_error_code:string|null};
export type ArtifactRecord={id:string;resource_type:typeof artifactTypes[number];owner_id:string;format:string;size_bytes:number|null;retention_until:string|null;deleted_at:string|null;on_hold:boolean;cleanup_job:CleanupMetadata|null};
export type SyncPage={items:SyncRecord[];next_cursor:string|null};
export type ArtifactPage={items:ArtifactRecord[]};
const syncFields=['id','order_id','last_export_version','status','attempt_count','last_error_code','last_synced_at','updated_at'];
const artifactFields=['id','resource_type','owner_id','format','size_bytes','retention_until','deleted_at','on_hold','cleanup_job'];
function deny():never{throw Error('Invalid finance/storage contract');}
function object(value:unknown,keys:readonly string[]):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value))return deny();const row=value as Record<string,unknown>;if(Object.keys(row).length!==keys.length||keys.some(k=>!Object.hasOwn(row,k)))return deny();return row;}
export function metadataId(value:unknown):string{if(typeof value!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value))return deny();return value.toLowerCase();}
function integer(value:unknown,max=2147483647):number{if(typeof value!=='number'||!Number.isSafeInteger(value)||value<0||value>max)return deny();return value;}
function timestamp(value:unknown):string{if(typeof value!=='string'||value.length>40||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(value)||!Number.isFinite(Date.parse(value)))return deny();return value;}
function optionalTime(value:unknown):string|null{return value===null?null:timestamp(value);}
function member<T extends string>(value:unknown,values:readonly T[]):T{if(typeof value!=='string'||!values.includes(value as T))return deny();return value as T;}
function safeFailure(value:unknown):string|null{if(value===null)return null;if(typeof value!=='string')return deny();return failureCodes.includes(value as typeof failureCodes[number])?value:'unrecognized_failure';}
function cursor(value:unknown):string|null{if(value===null)return null;if(typeof value!=='string'||!value.length||value.length>200||!/^[A-Za-z0-9_-]+$/.test(value))return deny();try{const pair:unknown=JSON.parse(atob(value.replace(/-/g,'+').replace(/_/g,'/')));if(!Array.isArray(pair)||pair.length!==2)return deny();timestamp(pair[0]);metadataId(pair[1]);}catch{return deny();}return value;}
export function metadataQuery(input:URLSearchParams,mode:MetadataMode):URLSearchParams{
  if(input.toString().length>1024)return deny();const q=new URLSearchParams();
  for(const [key,value] of input){if(!(mode==='storage'?['limit','resource_type','order_id','job_id']:['limit','cursor']).includes(key)||input.getAll(key).length!==1)return deny();
    if(key==='limit'){if(!/^[1-9]\d{0,2}$/.test(value)||Number(value)>100)return deny();q.set(key,value);}
    else if(key==='cursor')q.set(key,cursor(value)!);
    else if(key==='resource_type')q.set(key,member(value,artifactTypes));
    else q.set(key,metadataId(value));
  }return q;
}
function syncRecord(value:unknown,upstream:boolean):SyncRecord{
  const r=object(value,upstream?[...syncFields,'sheet_row_key','payment_status','fulfillment_status','currency_code','total_pkr']:syncFields);
  return {id:metadataId(r.id),order_id:metadataId(r.order_id),last_export_version:integer(r.last_export_version),status:member(r.status,syncStates),attempt_count:integer(r.attempt_count),last_error_code:safeFailure(r.last_error_code),last_synced_at:optionalTime(r.last_synced_at),updated_at:timestamp(r.updated_at)};
}
function artifactRecord(value:unknown,upstream:boolean):ArtifactRecord{
  const r=object(value,upstream?[...artifactFields,'bucket','object_key','sha256_hex','deletion_hold_reason']:artifactFields);
  if(typeof r.on_hold!=='boolean'||typeof r.format!=='string')return deny();
  let cleanup:CleanupMetadata|null=null;
  if(r.cleanup_job!==null){const j=object(r.cleanup_job,['id','status','attempt_count','last_error_code']);cleanup={id:metadataId(j.id),status:member(j.status,jobStates),attempt_count:integer(j.attempt_count),last_error_code:safeFailure(j.last_error_code)};}
  const format=['pdf','svg','other_approved','application/pdf','image/png','image/jpeg','image/webp','unavailable'].includes(r.format)?r.format:'unavailable';
  return {id:metadataId(r.id),resource_type:member(r.resource_type,artifactTypes),owner_id:metadataId(r.owner_id),format,size_bytes:r.size_bytes===null?null:integer(r.size_bytes,Number.MAX_SAFE_INTEGER),retention_until:optionalTime(r.retention_until),deleted_at:optionalTime(r.deleted_at),on_hold:r.on_hold,cleanup_job:cleanup};
}
export function syncPage(value:unknown,q=new URLSearchParams(),upstream=false):SyncPage{
  const p=object(value,['items','next_cursor']);metadataQuery(q,'finance');if(!Array.isArray(p.items)||p.items.length>Number(q.get('limit')??50))return deny();const items=p.items.map(r=>syncRecord(r,upstream));if(new Set(items.map(r=>r.id)).size!==items.length)return deny();const next=cursor(p.next_cursor);if(next!==null&&!items.length)return deny();return {items,next_cursor:next};
}
export function artifactPage(value:unknown,q=new URLSearchParams(),upstream=false):ArtifactPage{
  const p=object(value,['items']);metadataQuery(q,'storage');if(!Array.isArray(p.items)||p.items.length>Number(q.get('limit')??50))return deny();const items=p.items.map(r=>artifactRecord(r,upstream));if(new Set(items.map(r=>r.id)).size!==items.length||q.has('resource_type')&&items.some(r=>r.resource_type!==q.get('resource_type')))return deny();return {items};
}
export function syncRetryInput(value:unknown):{id:string;confirmed:true}{const r=object(value,['id','confirmed']);if(r.confirmed!==true)return deny();return {id:metadataId(r.id),confirmed:true};}
export function syncRetryReceipt(value:unknown,id:string){const r=object(value,['id','order_id','status']);if(metadataId(r.id)!==id||r.status!=='retry')return deny();return {id,order_id:metadataId(r.order_id),status:'retry' as const};}
export const canReadSync=(roles:readonly string[])=>roles.some(r=>['finance','security_admin','superadmin'].includes(r));
export const canReadArtifacts=(roles:readonly string[])=>roles.some(r=>['operations','finance','security_admin','superadmin'].includes(r));
