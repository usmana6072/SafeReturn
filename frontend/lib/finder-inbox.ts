import { uuid } from "./qr-contract";

export type FinderStatus = "new"|"viewed"|"archived"|"flagged";
export type InboxContext = {status?:FinderStatus;cursor?:string;qr_id?:string};
export type FinderSummary = {id:string;qr_id:string;qr_label:string|null;finder_name:string|null;tag_type:"lost"|"ice";status:FinderStatus;submitted_at:string;notification_status:string|null};
export type FinderMessage = {id:string;finder_name:string|null;finder_email:string|null;finder_phone:string|null;tag_type:"lost"|"ice";status:FinderStatus;submitted_at:string;
  preferred_contact:"email"|"phone"|null;message:string;location:{latitude:number;longitude:number;maps_url:string;accuracy_m:number|null}|null};
export const finderStatuses:FinderStatus[]=["new","viewed","archived","flagged"];
const isDate=(value:unknown):value is string=>typeof value==="string"&&Number.isFinite(Date.parse(value));
const optionalString=(value:unknown)=>value===null||typeof value==="string";

export function inboxContext(params:Record<string,unknown>):InboxContext{
  const context:InboxContext={};
  if(params.status!==undefined&&params.status!==""){
    if(typeof params.status!=="string"||!finderStatuses.includes(params.status as FinderStatus))throw Error("Unavailable");
    context.status=params.status as FinderStatus;
  }
  if(params.cursor!==undefined&&params.cursor!==""){
    if(typeof params.cursor!=="string"||params.cursor.length>256)throw Error("Unavailable");
    context.cursor=params.cursor;
  }
  if(params.qr_id!==undefined&&params.qr_id!==""){
    if(typeof params.qr_id!=="string"||!uuid(params.qr_id))throw Error("Unavailable");
    context.qr_id=params.qr_id;
  }
  return context;
}
export function inboxQuery(context:InboxContext){
  const query=new URLSearchParams();
  if(context.status)query.set("status",context.status);
  if(context.cursor)query.set("cursor",context.cursor);
  if(context.qr_id)query.set("qr_id",context.qr_id);
  return query;
}
export function inboxHref(context:InboxContext={},result?:string){
  const query=inboxQuery(context);if(result)query.set("result",result);
  return "/inbox"+(query.size?"?"+query:"");
}
export function finderPage(value:unknown):{items:FinderSummary[];next_cursor:string|null}{
  if(!value||typeof value!=="object")throw Error("Unavailable");
  const page=value as {items:FinderSummary[];next_cursor:string|null};
  if(!Array.isArray(page.items)||page.items.length>100||!(page.next_cursor===null||typeof page.next_cursor==="string"))throw Error("Unavailable");
  const items=page.items.map(m=>{
    if(!m||!uuid(m.id)||!uuid(m.qr_id)||!["lost","ice"].includes(m.tag_type)||!finderStatuses.includes(m.status)||!isDate(m.submitted_at)||
      ![m.qr_label,m.finder_name,m.notification_status].every(optionalString))throw Error("Unavailable");
    return {id:m.id,qr_id:m.qr_id,qr_label:m.qr_label,finder_name:m.finder_name,tag_type:m.tag_type,status:m.status,submitted_at:m.submitted_at,notification_status:m.notification_status};
  });
  return {items,next_cursor:page.next_cursor};
}
export function finderDetail(value:unknown):FinderMessage{
  if(!value||typeof value!=="object")throw Error("Unavailable");
  const m=value as FinderMessage;
  if(!uuid(m.id)||!["lost","ice"].includes(m.tag_type)||!finderStatuses.includes(m.status)||!isDate(m.submitted_at)||typeof m.message!=="string"||
    ![m.finder_name,m.finder_email,m.finder_phone].every(optionalString)||![null,"email","phone"].includes(m.preferred_contact))throw Error("Unavailable");
  return {id:m.id,tag_type:m.tag_type,status:m.status,submitted_at:m.submitted_at,message:m.message,finder_name:m.finder_name,
    finder_email:m.finder_email,finder_phone:m.finder_phone,preferred_contact:m.preferred_contact,location:m.location??null};
}
export function finderLabel(status:FinderStatus,ur:boolean){
  return ({new:["Unread","نیا"],viewed:["Read","پڑھا گیا"],archived:["Archived","محفوظ شدہ"],flagged:["Flagged","نشان زدہ"]} as const)[status][ur?1:0];
}
export function qrMessageName(message:{qr_label?:string|null;tag_type:string},ur:boolean){
  return message.qr_label||(message.tag_type==="ice"?(ur?"ہنگامی QR":"Emergency QR"):(ur?"گمشدہ QR":"Lost QR"));
}
export function finderDate(stamp:string,ur:boolean,compact=false){
  return new Intl.DateTimeFormat(ur?"ur-PK":"en-GB",{dateStyle:compact?"short":"medium",...(compact?{}:{timeStyle:"short" as const}),timeZone:"Asia/Karachi"}).format(new Date(stamp));
}
export function finderEmailHref(value:string|null){
  if(!value||value.length>254||!/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(value))return null;
  return "mailto:"+encodeURIComponent(value).replace("%40","@");
}
export function finderPhoneHref(value:string|null){
  return value&&/^\+[1-9][0-9]{7,14}$/.test(value)?"tel:"+value:null;
}
export function finderMapHref(location:FinderMessage["location"]){
  if(!location||!Number.isFinite(location.latitude)||!Number.isFinite(location.longitude)||Math.abs(location.latitude)>90||Math.abs(location.longitude)>180)return null;
  try{
    const url=new URL(location.maps_url);
    return url.origin==="https://www.google.com"&&url.pathname==="/maps"&&url.searchParams.get("q")===location.latitude+","+location.longitude?url.href:null;
  }catch{return null;}
}
