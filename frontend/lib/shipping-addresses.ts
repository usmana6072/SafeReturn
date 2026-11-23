import {uuid} from "./qr-contract";
export type ShippingAddress={recipient_name:string;phone:string;address:string;city:string;province:string|null;postal_code:string|null};
export type SavedAddress=ShippingAddress&{id:string;version:number;is_default:boolean};
export type AddressBook={book_version:number;items:SavedAddress[]};
export type AddressField=keyof ShippingAddress;
export const addressEndpoint="/account/shipping-addresses/api";
export const blankAddress:ShippingAddress={recipient_name:"",phone:"",address:"",city:"",province:"",postal_code:""};
export const addressFields:AddressField[]=["recipient_name","phone","address","city","province","postal_code"];
export const addressLimits:Record<AddressField,number>={recipient_name:160,phone:16,address:500,city:100,province:100,postal_code:20};
export function addressOnly(value:ShippingAddress):ShippingAddress{
 return {recipient_name:value.recipient_name,phone:value.phone,address:value.address,city:value.city,province:value.province||null,postal_code:value.postal_code||null};
}
export function parseAddressBook(value:unknown):AddressBook{
 if(!value||typeof value!=="object")throw Error("Unavailable");
 const b=value as AddressBook;
 if(!Number.isInteger(b.book_version)||b.book_version<0||!Array.isArray(b.items)||b.items.length>100)throw Error("Unavailable");
 const ids=new Set<string>();let defaults=0;
 const items=b.items.map(a=>{
  if(!a||typeof a.id!=="string"||!uuid(a.id)||ids.has(a.id)||!Number.isInteger(a.version)||a.version<1||typeof a.is_default!=="boolean")throw Error("Unavailable");
  ids.add(a.id);if(a.is_default)defaults++;
  for(const field of addressFields){
   const data=a[field];
   if((field==="province"||field==="postal_code")&&data===null)continue;
   if(typeof data!=="string"||data.length>addressLimits[field]||(!["province","postal_code"].includes(field)&&!data.length))throw Error("Unavailable");
  }
  if(!/^\+[1-9][0-9]{7,14}$/.test(a.phone))throw Error("Unavailable");
  return {id:a.id,version:a.version,is_default:a.is_default,...addressOnly(a)};
 });
 if(defaults>1)throw Error("Unavailable");
 return {book_version:b.book_version,items};
}
export function addressErrors(value:ShippingAddress,ur:boolean):Partial<Record<AddressField,string>>{
 const errors:Partial<Record<AddressField,string>>={};
 const required:Partial<Record<AddressField,[string,string]>>={
 recipient_name:["Please enter your full name.","اپنا پورا نام درج کریں۔"],address:["Please enter your delivery address.","ترسیل کا پتہ درج کریں۔"],city:["Please enter your city.","اپنا شہر درج کریں۔"]};
 for(const field of addressFields){
  const v=value[field]??"";
  if(required[field]&&!v.trim())errors[field]=required[field]![ur?1:0];
  else if(v.length>addressLimits[field])errors[field]=ur?"یہ معلومات بہت طویل ہیں۔":"This entry is too long.";
 }
 if(!/^\+[1-9][0-9]{7,14}$/.test(value.phone))errors.phone=ur?"ملک کے کوڈ کے ساتھ درست فون نمبر درج کریں۔":"Enter a valid phone number with its country code.";
 return errors;
}

