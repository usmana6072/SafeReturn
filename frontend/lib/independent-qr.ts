import {obj,id,int,str} from './inventory-contract';
const bad=():never=>{throw Error('Unavailable');};
const bool=(x:unknown):boolean=>typeof x==='boolean'?x:bad();
export type IndependentQR={logical_item_id:string;qr_id:string;order_id:string;product_name_snapshot:string;tag_type:'lost'|'ice';ownership_status:string;public_status:string;revision:number;activated_at:string|null;can_activate:boolean};
export function collection(x:unknown):{items:IndependentQR[];next_cursor:string|null;activation_released:boolean}{
 const v=obj(x,['items','next_cursor','activation_released']);if(!Array.isArray(v.items)||v.items.length>100)bad();
 const items=(v.items as unknown[]).map(raw=>{const r=obj(raw,['logical_item_id','qr_id','order_id','product_name_snapshot','tag_type','ownership_status','public_status','revision','activated_at','can_activate']);
  if(!['lost','ice'].includes(String(r.tag_type))||!['unclaimed','active','revoked'].includes(String(r.ownership_status))||!['unactivated','active','owner_disabled','admin_suspended','revoked'].includes(String(r.public_status)))bad();
  const can_activate=bool(r.can_activate);if(can_activate&&(r.ownership_status!=='unclaimed'||r.public_status!=='unactivated'||!v.activation_released))bad();
  return{logical_item_id:id(r.logical_item_id),qr_id:id(r.qr_id),order_id:id(r.order_id),product_name_snapshot:str(r.product_name_snapshot,500),tag_type:r.tag_type as 'lost'|'ice',ownership_status:String(r.ownership_status),public_status:String(r.public_status),revision:int(r.revision,1),activated_at:r.activated_at===null?null:str(r.activated_at,64),can_activate};});
 if(new Set(items.map(i=>i.qr_id)).size!==items.length||new Set(items.map(i=>i.logical_item_id)).size!==items.length)bad();
 return{items,next_cursor:v.next_cursor===null?null:id(v.next_cursor),activation_released:bool(v.activation_released)};
}
export function commandResult(action:string,x:unknown):unknown{
 if(action==='begin'){const r=obj(x,['intent_id','logical_item_id','qr_id','expires_at','method']);if(r.method!=='delivered_purchaser')bad();return{intent_id:id(r.intent_id),logical_item_id:id(r.logical_item_id),qr_id:id(r.qr_id),expires_at:str(r.expires_at,64),method:r.method};}
 if(action==='confirm'){const r=obj(x,['qr_id','logical_item_id','status','revision','activated_at']);if(r.status!=='active')bad();return{qr_id:id(r.qr_id),logical_item_id:id(r.logical_item_id),status:r.status,revision:int(r.revision,1),activated_at:str(r.activated_at,64)};}
 if(action==='availability'){const r=obj(x,['qr_id','public_status','revision']);if(!['active','owner_disabled'].includes(String(r.public_status)))bad();return{qr_id:id(r.qr_id),public_status:r.public_status,revision:int(r.revision,1)};}
 if(action==='history'){const r=obj(x,['qr_id','items','next_revision']);if(!Array.isArray(r.items)||r.items.length>100)bad();const items=(r.items as unknown[]).map(raw=>{const e=obj(raw,['event_id','event_type','state_revision','created_at']);if(!['activated','owner_disabled','owner_enabled'].includes(String(e.event_type)))bad();return{event_id:id(e.event_id),event_type:e.event_type,state_revision:int(e.state_revision,1),created_at:str(e.created_at,64)};});return{qr_id:id(r.qr_id),items,next_revision:r.next_revision===null?null:int(r.next_revision,1)};}
 return bad();
}
