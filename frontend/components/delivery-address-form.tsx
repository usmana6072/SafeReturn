"use client";
import {useId,type FormEvent} from "react";
import {addressFields,addressLimits,type AddressField,type ShippingAddress} from "../lib/shipping-addresses";
const labels:Record<AddressField,[string,string]>={recipient_name:["Full Name","پورا نام"],phone:["Phone Number","فون نمبر"],address:["House / Street Address","مکان / گلی کا پتہ"],city:["City","شہر"],province:["Province / Region","صوبہ / علاقہ"],postal_code:["Postal Code","پوسٹل کوڈ"]};
const autocomplete:Record<AddressField,string>={recipient_name:"shipping name",phone:"shipping tel",address:"shipping street-address",city:"shipping address-level2",province:"shipping address-level1",postal_code:"shipping postal-code"};
export function DeliveryAddressForm({value,isDefault,errors,busy,blocked,editing,ur,onChange,onBlur,onDefault,onSubmit,onCancel}:{value:ShippingAddress;isDefault:boolean;errors:Partial<Record<AddressField,string>>;busy:boolean;blocked:boolean;editing:boolean;ur:boolean;onChange:(key:AddressField,value:string)=>void;onBlur:(key:AddressField)=>void;onDefault:(value:boolean)=>void;onSubmit:(event:FormEvent<HTMLFormElement>)=>void;onCancel:()=>void}){
 const prefix=useId(),t=(en:string,u:string)=>ur?u:en;
 return <form className="address-form" onSubmit={onSubmit} noValidate><p className="address-form-note">{t("Fields marked * are required.","* والے خانے ضروری ہیں۔")}</p><fieldset disabled={busy}><div className="address-fields">
 {addressFields.map(field=>{const id=prefix+"-"+field,error=errors[field],optional=field==="province"||field==="postal_code";
 const props={id,name:field,value:value[field]??"",required:!optional,maxLength:addressLimits[field],autoComplete:autocomplete[field],onChange:(event:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement>)=>onChange(field,event.target.value),onBlur:()=>onBlur(field),"aria-invalid":!!error,"aria-describedby":[error?id+"-error":null,field==="phone"?id+"-help":null].filter(Boolean).join(" ")||undefined};
 return <div className={"address-field "+(field==="address"?"address-field-wide":"")} key={field}><label htmlFor={id}>{labels[field][ur?1:0]} {!optional&&<span aria-hidden="true">*</span>}{optional&&<small>{t("Optional","اختیاری")}</small>}</label>
 {field==="address"?<textarea {...props} rows={3}/>:<input {...props} type={field==="phone"?"tel":"text"} inputMode={field==="phone"?"tel":"text"} dir={field==="phone"?"ltr":undefined} placeholder={field==="phone"?"+923001234567":undefined} enterKeyHint="next"/>}
 {field==="phone"&&<p className="address-field-help" id={id+"-help"}>{t("Include the country code, for example +923001234567 or +447700900123.","ملک کا کوڈ شامل کریں، مثلاً +923001234567 یا +447700900123۔")}</p>}
 {error&&<p className="address-field-error" id={id+"-error"}>{error}</p>}</div>;})}
 </div><label className="address-default-check"><input type="checkbox" checked={isDefault} onChange={event=>onDefault(event.target.checked)}/><span>{t("Set as Default Address","ترجیحی پتہ مقرر کریں")}<small>{t("Use this address first at checkout.","چیک آؤٹ پر یہ پتہ پہلے منتخب ہوگا۔")}</small></span></label>
 <div className="address-form-actions"><button className="address-primary" disabled={blocked} type="submit">{busy?t("Saving Address…","پتہ محفوظ ہو رہا ہے…"):editing?t("Save Changes","تبدیلیاں محفوظ کریں"):t("Save Address","پتہ محفوظ کریں")}</button>
 <button className="address-secondary" type="button" onClick={onCancel}>{t("Cancel","منسوخ")}</button></div></fieldset></form>;
}

