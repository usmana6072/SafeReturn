export const cartKey = "safereturn-cart-v1";
export type CopyRow = { variant_id: string; lost: number; ice: number };
export function readCart(): CopyRow[] {
 try {const v:unknown=JSON.parse(localStorage.getItem(cartKey)??"[]");return Array.isArray(v)&&v.length<=25?v.filter((r):r is CopyRow=>typeof r==="object"&&r!==null&&typeof r.variant_id==="string"&&/^[a-f0-9-]{36}$/i.test(r.variant_id)&&Number.isInteger(r.lost)&&r.lost>=0&&r.lost<=100&&Number.isInteger(r.ice)&&r.ice>=0&&r.ice<=100):[];}catch{return [];}
}
export function cartLines(rows: CopyRow[]) {return rows.flatMap(row=>(["lost","ice"] as const).filter(tag=>row[tag]>0).map(tag=>({variant_id:row.variant_id,quantity:row[tag],qr_uses:[{mode:"new_pair",tag_type:tag,copies:row[tag],client_pair_group:"one-kit"}]})));}
