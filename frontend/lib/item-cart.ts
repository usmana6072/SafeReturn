export const itemCartKey="safereturn-item-cart-v2";
export type ItemCart={product_id:string;identity_group:string|null;sizes:{variant_id:string;copies:number}[]};
const uuid=/^[a-f0-9-]{36}$/i;
export function readItemCart():ItemCart[]{
 try{
  const value:unknown=JSON.parse(localStorage.getItem(itemCartKey)??"[]");
  if(!Array.isArray(value)||value.length>50)return [];
  if(!value.every(i=>i&&typeof i==="object"&&uuid.test(i.product_id)&&
   (i.identity_group===null||(typeof i.identity_group==="string"&&/^[A-Za-z0-9_-]{1,80}$/.test(i.identity_group)))&&
   Array.isArray(i.sizes)&&i.sizes.length>0&&i.sizes.length<=50&&i.sizes.every((s:ItemCart["sizes"][number])=>s&&uuid.test(s.variant_id)&&Number.isInteger(s.copies)&&s.copies>=1&&s.copies<=100)))return [];
  // Discard unknown browser fields, including prices and public tokens.
  return value.map(i=>({product_id:i.product_id,identity_group:i.identity_group,sizes:i.sizes.map((s:ItemCart["sizes"][number])=>({variant_id:s.variant_id,copies:s.copies}))}));
 }catch{return [];}
}
export function mergeItemCart(cart:ItemCart[],incoming:ItemCart):ItemCart[]{
 const old=cart.find(i=>i.product_id===incoming.product_id&&i.identity_group===incoming.identity_group);
 const copies=new Map<string,number>();
 for(const size of [...(old?.sizes??[]),...incoming.sizes])copies.set(size.variant_id,(copies.get(size.variant_id)??0)+size.copies);
 const merged={...incoming,sizes:[...copies].map(([variant_id,copies])=>({variant_id,copies}))};
 return old?cart.map(i=>i===old?merged:i):[...cart,merged];
}
export type PaymentInstructions={version:string;bank_name:string;account_title:string;account_number:string;raast_id:string;instructions_en:string;instructions_ur:string;currency_code:"PKR"};
