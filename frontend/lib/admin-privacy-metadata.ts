// API-330 only. No decision, customer export, grant or download contract.
export const exportStates = ['requested','reviewing','approved','building','ready','expired','rejected','escalated','held','retry'] as const;
export type ExportState = typeof exportStates[number];
export type ExportMetadata = {request_id:string;case_id:string;status:ExportState;revision:number;scope_version:'basic_v1';created_at:string;ready_at:string|null;expires_at:string|null};
export type ExportPage = {items:ExportMetadata[];next_cursor:string|null};
const fields = ['request_id','case_id','status','revision','scope_version','created_at','ready_at','expires_at'];
const upstreamFields = [...fields,'manifest_version','manifest_id','categories'];
function deny():never {throw Error('Invalid privacy metadata contract');}
function object(value:unknown,keys:readonly string[]):Record<string,unknown>{
  if(!value||typeof value!=='object'||Array.isArray(value))return deny();
  const row=value as Record<string,unknown>;
  if(Object.keys(row).length!==keys.length||keys.some(k=>!Object.hasOwn(row,k)))return deny();
  return row;
}
export function exportId(value:unknown):string{
  if(typeof value!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value))return deny();
  return value.toLowerCase();
}
function timestamp(value:unknown):string{
  if(typeof value!=='string'||value.length>40||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(value)||!Number.isFinite(Date.parse(value)))return deny();
  return value;
}
function optionalTime(value:unknown):string|null{return value===null?null:timestamp(value);}
function cursor(value:unknown):string|null{
  if(value===null)return null;
  if(typeof value!=='string'||value.length>200||!value.length||!/^[A-Za-z0-9_-]+$/.test(value))return deny();
  try{const pair:unknown=JSON.parse(atob(value.replace(/-/g,'+').replace(/_/g,'/')));if(!Array.isArray(pair)||pair.length!==2)return deny();timestamp(pair[0]);exportId(pair[1]);}catch{return deny();}
  return value;
}
export function exportQuery(input:URLSearchParams):URLSearchParams{
  if(input.toString().length>1024)return deny();const result=new URLSearchParams();
  for(const [key,value] of input){
    if(!['limit','cursor'].includes(key)||input.getAll(key).length!==1)return deny();
    if(key==='cursor')result.set(key,cursor(value)!);
    else{if(!/^[1-9]\d{0,2}$/.test(value)||Number(value)>100)return deny();result.set(key,value);}
  }
  return result;
}
function metadata(value:unknown,upstream:boolean):ExportMetadata{
  const r=object(value,upstream?upstreamFields:fields);
  if(typeof r.status!=='string'||!exportStates.includes(r.status as ExportState)||typeof r.revision!=='number'||!Number.isSafeInteger(r.revision)||r.revision<1||r.revision>2147483647||r.scope_version!=='basic_v1')return deny();
  if(upstream){
    if(r.manifest_version!=='basic_v1:1')return deny();exportId(r.manifest_id);
    if(r.categories!==null&&(!r.categories||typeof r.categories!=='object'||Array.isArray(r.categories)))return deny();
    // Deliberately never copy/traverse category counts, manifest or payload data.
  }
  return {request_id:exportId(r.request_id),case_id:exportId(r.case_id),status:r.status as ExportState,revision:r.revision,scope_version:r.scope_version,created_at:timestamp(r.created_at),ready_at:optionalTime(r.ready_at),expires_at:optionalTime(r.expires_at)};
}
function page(value:unknown,query:URLSearchParams,upstream:boolean):ExportPage{
  const p=object(value,['items','next_cursor']),q=exportQuery(query);
  if(!Array.isArray(p.items)||p.items.length>Number(q.get('limit')??20))return deny();
  const items=p.items.map(row=>metadata(row,upstream));
  if(new Set(items.map(r=>r.request_id)).size!==items.length)return deny();
  const next=cursor(p.next_cursor);if(next!==null&&!items.length)return deny();
  return {items,next_cursor:next};
}
export const projectExportPage=(value:unknown,query=new URLSearchParams())=>page(value,query,true);
export const exportPage=(value:unknown,query=new URLSearchParams())=>page(value,query,false);
export const canReviewPrivacy=(roles:readonly string[])=>roles.includes('security_admin');
