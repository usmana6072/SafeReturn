"use client";
import {useEffect,useRef,useState} from "react";
import {addressEndpoint,parseAddressBook,type AddressBook,type SavedAddress} from "../lib/shipping-addresses";
export function SavedAddressSelector({ur,onSelect,disabled}:{ur:boolean;onSelect:(address:SavedAddress|null)=>void;disabled:boolean}){
 const [book,setBook]=useState<AddressBook|null>(null),[selected,setSelected]=useState(""),[failed,setFailed]=useState(false);
 const selection=useRef<SavedAddress|null>(null),initialized=useRef(false),userSelected=useRef(false);
 const notify=useRef(onSelect);notify.current=onSelect;
 useEffect(()=>{
  let active=true,controller:AbortController|null=null,loading=false;
  async function load(){
   if(loading)return;loading=true;controller=new AbortController();
   try{
    const response=await fetch(addressEndpoint,{cache:"no-store",signal:controller.signal});if(!response.ok)throw Error("Unavailable");
    const next=parseAddressBook(await response.json());if(!active)return;
    setBook(next);setFailed(false);
    const previous=selection.current;
    const value=!initialized.current&&!userSelected.current?next.items.find(a=>a.is_default)??null:previous?next.items.find(a=>a.id===previous.id)??null:null;
    initialized.current=true;
    selection.current=value;setSelected(value?.id??"");
    if(value?.id!==previous?.id||value?.version!==previous?.version)notify.current(value);
   }catch(error){
    if(!active||(error instanceof Error&&error.name==="AbortError"))return;
    setFailed(true);setBook(null);
    // An unverified stale selection must never be submitted with a quote.
    if(selection.current){selection.current=null;setSelected("");notify.current(null);}
   }finally{loading=false;}
  }
  function resume(){if(document.visibilityState==="visible")void load();}
  function pageshow(event:PageTransitionEvent){if(event.persisted)void load();}
  void load();window.addEventListener("focus",resume);window.addEventListener("pageshow",pageshow);document.addEventListener("visibilitychange",resume);
  return ()=>{active=false;controller?.abort();window.removeEventListener("focus",resume);window.removeEventListener("pageshow",pageshow);document.removeEventListener("visibilitychange",resume);};
 },[]);
 return <fieldset className="account-form qr-fieldset" disabled={disabled}><legend>{ur?"محفوظ پتہ":"Saved address"}</legend>
 <label>{ur?"ترسیل کا پتہ منتخب کریں":"Choose shipping address"}<select value={selected} onChange={event=>{
  userSelected.current=true;const value=book?.items.find(a=>a.id===event.target.value)??null;
  selection.current=value;setSelected(value?.id??"");notify.current(value);
 }}><option value="">{ur?"نیا پتہ درج کریں":"Enter a new address"}</option>{book?.items.map(a=><option key={a.id} value={a.id}>{a.city} · ••••{a.phone.slice(-4)}{a.is_default?(ur?" · ترجیحی":" · default"):""}</option>)}</select></label>
 {!book&&<p role="status">{failed?(ur?"محفوظ پتے دستیاب نہیں؛ نیا پتہ درج کریں۔":"Saved addresses unavailable; enter a new address."):(ur?"پتے لوڈ ہو رہے ہیں…":"Loading addresses…")}</p>}
 <a href="/account/shipping-addresses">{ur?"پتوں کا انتظام":"Manage addresses"}</a></fieldset>;
}

