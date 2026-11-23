"use client";
import {useEffect,useRef,useState,type FormEvent} from "react";
import {CustomerDialog} from "./customer-dialog";
import {CustomerIcon} from "./customer-icon";
import {DeliveryAddressForm} from "./delivery-address-form";
import {addressEndpoint,addressOnly,addressErrors,blankAddress,parseAddressBook,type AddressBook,type AddressField,type SavedAddress,type ShippingAddress} from "../lib/shipping-addresses";
export {SavedAddressSelector} from "./saved-address-selector";
export type {SavedAddress,ShippingAddress} from "../lib/shipping-addresses";

type Editor={source:SavedAddress|null;bookVersion:number;original:string;ids:string[]};
type Notice={error:boolean;text:string}|null;
class AddressMutationError extends Error{}
const snapshot=(value:ShippingAddress,isDefault:boolean)=>JSON.stringify({address:addressOnly(value),is_default:isDefault});
export function AddressSkeleton(){
 return <div className="address-screen address-loading" role="status" aria-busy="true"><span className="sr-only">Loading addresses / پتے لوڈ ہو رہے ہیں</span><i className="address-skeleton-title" aria-hidden="true"/><div className="address-grid" aria-hidden="true">{[0,1].map(i=><div className="address-card" key={i}><i/><i/><i/><i/></div>)}</div></div>;
}
export function ShippingAddresses({ur}:{ur:boolean}){
 const t=(en:string,u:string)=>ur?u:en;
 const [book,setBook]=useState<AddressBook|null>(null),[loadError,setLoadError]=useState(false),[refreshing,setRefreshing]=useState(false),[stale,setStale]=useState(false);
 const [editor,setEditor]=useState<Editor|null>(null),[form,setForm]=useState<ShippingAddress>({...blankAddress}),[isDefault,setDefault]=useState(false),[errors,setErrors]=useState<Partial<Record<AddressField,string>>>({});
 const [deleting,setDeleting]=useState<SavedAddress|null>(null),[discard,setDiscard]=useState<"close"|"latest"|null>(null),[pending,setPending]=useState<string|null>(null),[notice,setNotice]=useState<Notice>(null);
 const running=useRef(false),alive=useRef(true),request=useRef<Promise<AddressBook>|null>(null),controller=useRef<AbortController|null>(null),add=useRef<HTMLButtonElement>(null),trigger=useRef<HTMLElement|null>(null);
 const editorRef=useRef(editor),dirtyRef=useRef(false);editorRef.current=editor;
 const dirty=!!editor&&snapshot(form,isDefault)!==editor.original;dirtyRef.current=dirty;
 const latest=editor?.source?book?.items.find(a=>a.id===editor.source!.id):null;
 const outdated=!!editor?.source&&!!book&&latest?.version!==editor.source.version;
 const possibleSaved=editor&&!editor.source&&book?.items.some(a=>!editor.ids.includes(a.id)&&snapshot(a,a.is_default)===snapshot(form,isDefault));
 async function readBook(){
  if(request.current)return request.current;
  controller.current=new AbortController();
  const work=(async()=>{
   const response=await fetch(addressEndpoint,{cache:"no-store",signal:controller.current!.signal});if(!response.ok)throw Error("Unavailable");
   const data=parseAddressBook(await response.json());
   if(alive.current){setBook(data);setLoadError(false);setStale(false);}
   return data;
  })();
  request.current=work;
  try{return await work;}finally{if(request.current===work)request.current=null;}
 }
 useEffect(()=>{
  let active=true;alive.current=true;void readBook().catch(()=>{if(active)setLoadError(true);});
  return ()=>{active=false;alive.current=false;controller.current?.abort();request.current=null;};
 },[]);
 useEffect(()=>{
  if(!editor)return;
  function beforeUnload(event:BeforeUnloadEvent){if(dirtyRef.current){event.preventDefault();event.returnValue="";}}
  function pop(){
   if(!editorRef.current)return;
   if(running.current){history.pushState({...history.state,safeReturnAddressEditor:true},"",location.href);return;}
   if(dirtyRef.current){history.pushState({...history.state,safeReturnAddressEditor:true},"",location.href);setDiscard("close");}
   else finishEditor(false);
  }
  window.addEventListener("beforeunload",beforeUnload);window.addEventListener("popstate",pop);
  return ()=>{window.removeEventListener("beforeunload",beforeUnload);window.removeEventListener("popstate",pop);};
 // Mutable refs keep the navigation guard current without adding history entries.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[!!editor]);
 function restoreFocus(){requestAnimationFrame(()=>{(trigger.current?.isConnected?trigger.current:add.current)?.focus();});}
 function finishEditor(removeHistory=true){
  editorRef.current=null;setEditor(null);setDiscard(null);setErrors({});setNotice(current=>stale?current:null);
  if(removeHistory&&history.state?.safeReturnAddressEditor)history.back();
  restoreFocus();
 }
 function openEditor(address:SavedAddress|null,event?:React.MouseEvent<HTMLButtonElement>){
  if(!book||running.current||stale)return;
  trigger.current=event?.currentTarget??add.current;
  const value=address?addressOnly(address):{...blankAddress},defaultValue=address?.is_default??false;
  setForm(value);setDefault(defaultValue);setErrors({});setNotice(null);setDiscard(null);
  setEditor({source:address,bookVersion:book.book_version,original:snapshot(value,defaultValue),ids:book.items.map(a=>a.id)});
  history.pushState({...history.state,safeReturnAddressEditor:true},"",location.href);
 }
 function requestClose(){if(running.current)return;if(dirty)setDiscard("close");else finishEditor();}
 function useLatest(){
  if(!editor||!latest||!book)return;
  const value=addressOnly(latest);
  setEditor({...editor,source:latest,bookVersion:book.book_version,original:snapshot(value,latest.is_default)});
  setForm(value);setDefault(latest.is_default);setErrors({});setNotice(null);setDiscard(null);
 }
 async function refresh(){
  if(running.current||request.current)return;
  setRefreshing(true);
  try{
   const data=await readBook(),current=editorRef.current;
   setDeleting(current=>current?data.items.find(a=>a.id===current.id)??null:null);
   if(current&&(!current.source||data.items.some(a=>a.id===current.source!.id&&a.version===current.source!.version)))setEditor({...current,bookVersion:data.book_version});
   setNotice({error:false,text:t("Addresses refreshed. Review your saved details before trying again.","پتے تازہ کر دیے گئے۔ دوبارہ کوشش سے پہلے تفصیلات دیکھ لیں۔")});
  }catch{setLoadError(true);setStale(true);setNotice({error:true,text:t("Couldn’t Load Addresses. Please try again.","پتے لوڈ نہیں ہو سکے۔ دوبارہ کوشش کریں۔")});}
  finally{setRefreshing(false);}
 }
 async function mutate(operation:string,method:string,payload:unknown){
  if(running.current||stale)return;
  running.current=true;setPending(operation);setNotice(null);
  let acknowledged=false;
  try{
   const response=await fetch(addressEndpoint,{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
   if(!response.ok){
    const message=response.status===409?t("This address may have changed or may be in use by an order. Refresh your addresses before trying again. Addresses used by orders cannot be edited or deleted.","یہ پتہ تبدیل ہو چکا ہے یا کسی آرڈر میں استعمال ہو رہا ہے۔ دوبارہ کوشش سے پہلے پتے تازہ کریں۔ آرڈر میں استعمال ہونے والا پتہ تبدیل یا حذف نہیں ہو سکتا۔"):
    response.status===401?t("Please sign in again to manage your addresses.","پتوں کے انتظام کے لیے دوبارہ سائن ان کریں۔"):
    response.status===403?t("You don’t have permission to change this address.","آپ کو یہ پتہ تبدیل کرنے کی اجازت نہیں۔"):
    response.status===404?t("This address is no longer available. Refresh your addresses.","یہ پتہ اب دستیاب نہیں۔ پتے تازہ کریں۔"):
    t("Address Couldn’t Be Saved. Check your information and refresh addresses before trying again.","پتہ محفوظ نہیں ہو سکا۔ معلومات چیک کریں اور دوبارہ کوشش سے پہلے پتے تازہ کریں۔");
    throw new AddressMutationError(message);
   }
   acknowledged=true;
   if(editorRef.current)finishEditor();
   setDeleting(null);
   await readBook();
   setNotice({error:false,text:operation.startsWith("delete")?t("Address deleted. Past order addresses are unchanged.","پتہ حذف کر دیا گیا۔ پچھلے آرڈرز کے پتے محفوظ ہیں۔"):operation.startsWith("default")?t("Default address updated.","ترجیحی پتہ تبدیل کر دیا گیا۔"):t("Address saved.","پتہ محفوظ ہو گیا۔")});
   if(operation.startsWith("delete"))requestAnimationFrame(()=>add.current?.focus());
  }catch(error){
   setStale(true);
   if(acknowledged){setLoadError(true);setNotice({error:true,text:t("Your change was saved, but addresses couldn’t be refreshed. Retry to see the updated list.","تبدیلی محفوظ ہو گئی، لیکن فہرست تازہ نہیں ہو سکی۔ تازہ فہرست کے لیے دوبارہ کوشش کریں۔")});}
   else setNotice({error:true,text:error instanceof AddressMutationError?error.message:t("The change wasn’t confirmed. Your entries are preserved. Refresh addresses to check before trying again.","تبدیلی کی تصدیق نہیں ہوئی۔ درج معلومات محفوظ ہیں۔ دوبارہ کوشش سے پہلے پتے تازہ کر کے دیکھ لیں۔")});
  }finally{running.current=false;setPending(null);}
 }
 function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(!editor||pending||stale||outdated||possibleSaved)return;
  const validation=addressErrors(form,ur);setErrors(validation);
  if(Object.keys(validation).length){const element=event.currentTarget;requestAnimationFrame(()=>{const input=element.querySelector<HTMLElement>('[aria-invalid="true"]');input?.focus();input?.scrollIntoView({block:"center",behavior:"instant"});});return;}
  const address=addressOnly(form);
  void mutate(editor.source?"update":"create",editor.source?"PATCH":"POST",editor.source?{id:editor.source.id,body:{address,is_default:isDefault,expected_version:editor.source.version,expected_book_version:editor.bookVersion}}:{...address,is_default:isDefault,expected_book_version:editor.bookVersion});
 }
 const message=notice&&<div className={"address-feedback "+(notice.error?"error":"")} role={notice.error?"alert":"status"}><p>{notice.text}</p>{stale&&<button className="address-secondary" disabled={refreshing||!!pending} onClick={()=>void refresh()}>{refreshing?t("Refreshing…","تازہ ہو رہا ہے…"):t("Refresh Addresses","پتے تازہ کریں")}</button>}</div>;
 return <section className="address-screen"><header className="address-intro"><div><h1>{t("Delivery Addresses","ترسیل کے پتے")}</h1><p>{t("Manage where your SafeReturn orders are delivered.","اپنے SafeReturn آرڈرز کی ترسیل کے پتوں کا انتظام کریں۔")}</p></div>
 <button className="address-refresh" aria-label={t("Refresh Addresses","پتے تازہ کریں")} disabled={refreshing||!!pending} onClick={()=>void refresh()}><CustomerIcon name="refresh"/></button></header>
 {!editor&&!deleting&&message}
 {!book&&!loadError?<AddressSkeleton/>:loadError&&!book?<div className="address-empty" role="alert"><CustomerIcon name="pin"/><h2>{t("Couldn’t Load Addresses","پتے لوڈ نہیں ہو سکے")}</h2><p>{t("Please try again.","دوبارہ کوشش کریں۔")}</p><button className="address-secondary" disabled={refreshing} onClick={()=>void refresh()}>{refreshing?t("Retrying…","کوشش جاری ہے…"):t("Retry","دوبارہ کوشش کریں")}</button></div>:book&&<>
 {!book.items.length?<div className="address-empty"><span className="address-empty-icon"><CustomerIcon name="pin"/></span><h2>{t("No Saved Addresses","کوئی محفوظ پتہ نہیں")}</h2><p>{t("Save a delivery address to make checkout faster.","چیک آؤٹ کو آسان بنانے کے لیے ترسیل کا پتہ محفوظ کریں۔")}</p></div>:
 <div className="address-grid">{[...book.items].sort((a,b)=>Number(b.is_default)-Number(a.is_default)).map(a=><article className={"address-card "+(a.is_default?"is-default":"")} key={a.id}>
 <div className="address-card-top"><span className="address-pin"><CustomerIcon name="pin"/></span><h2><bdi>{a.recipient_name}</bdi></h2>{a.is_default&&<span className="address-badge"><CustomerIcon name="check"/>{t("Default Address","ترجیحی پتہ")}</span>}</div>
 <address><bdi className="address-phone">{a.phone}</bdi><p dir="auto">{a.address}</p><p><bdi>{[a.city,a.province,a.postal_code].filter(Boolean).join(" · ")}</bdi></p></address>
 <div className="address-card-actions"><button className="address-secondary" disabled={!!pending||stale} onClick={e=>openEditor(a,e)}>{t("Edit Address","پتے میں ترمیم")}</button>
 {!a.is_default&&<button className="address-text" disabled={!!pending||stale} onClick={()=>void mutate("default:"+a.id,"PATCH",{id:a.id,body:{address:addressOnly(a),is_default:true,expected_version:a.version,expected_book_version:book.book_version}})}>{pending==="default:"+a.id?t("Updating…","تبدیل ہو رہا ہے…"):t("Set as Default","ترجیحی مقرر کریں")}</button>}
 <button className="address-delete" disabled={!!pending||stale} aria-label={t("Delete address for ","پتہ حذف کریں: ")+a.recipient_name} onClick={e=>{trigger.current=e.currentTarget;setDeleting(a);setNotice(null);}}>{t("Delete","حذف کریں")}</button></div></article>)}</div>}
 <button ref={add} className="address-primary address-add" disabled={!!pending||stale||book.items.length>=100} onClick={e=>openEditor(null,e)}><span aria-hidden="true" className="address-plus">+</span>{t("Add New Address","نیا پتہ شامل کریں")}</button>
 {book.items.length>=100&&<p className="address-note">{t("Your address book is full. Remove an unused address before adding another.","پتوں کی فہرست مکمل ہے۔ نیا پتہ شامل کرنے سے پہلے غیر استعمال شدہ پتہ ہٹائیں۔")}</p>}
 <p className="address-history-note"><CustomerIcon name="check"/>{t("Addresses on past orders stay unchanged.","پچھلے آرڈرز کے پتے تبدیل نہیں ہوں گے۔")}</p></>}
 {editor&&<CustomerDialog title={discard?t("Discard Your Changes?","تبدیلیاں ختم کریں؟"):editor.source?t("Edit Delivery Address","ترسیل کے پتے میں ترمیم"):t("Add Delivery Address","ترسیل کا پتہ شامل کریں")} ur={ur} busy={!!pending} onClose={()=>discard?setDiscard(null):requestClose()}>
 <div className="address-editor">{discard?<><p>{t("Your unsaved changes will be lost.","غیر محفوظ شدہ تبدیلیاں ختم ہو جائیں گی۔")}</p><div className="address-dialog-actions"><button className="address-secondary" onClick={()=>setDiscard(null)}>{t("Keep Editing","ترمیم جاری رکھیں")}</button><button className="address-primary" onClick={()=>discard==="latest"?useLatest():finishEditor()}>{t("Discard Changes","تبدیلیاں ختم کریں")}</button></div></>:<>
 {message}
 {outdated&&<div className="address-feedback error" role="alert"><p>{latest?t("This address changed since you opened it. Load the latest address before editing again. Your draft is still here.","یہ پتہ کھولنے کے بعد تبدیل ہوا ہے۔ دوبارہ ترمیم سے پہلے تازہ پتہ لوڈ کریں۔ آپ کا مسودہ ابھی موجود ہے۔"):t("This address is no longer saved. Close this form and review your addresses.","یہ پتہ اب محفوظ نہیں ہے۔ فارم بند کریں اور پتوں کی فہرست دیکھیں۔")}</p>{latest&&<button className="address-secondary" onClick={()=>dirty?setDiscard("latest"):useLatest()}>{t("Load Latest Address","تازہ پتہ لوڈ کریں")}</button>}</div>}
 {possibleSaved&&<p className="address-feedback" role="status">{t("An address with these details is now saved. Close this form to review it before adding another.","ان تفصیلات والا پتہ محفوظ ہو چکا ہے۔ دوسرا شامل کرنے سے پہلے فارم بند کر کے اسے دیکھ لیں۔")}</p>}
 <DeliveryAddressForm value={form} isDefault={isDefault} errors={errors} busy={!!pending} blocked={stale||outdated||!!possibleSaved||refreshing} editing={!!editor.source} ur={ur}
 onChange={(key,value)=>{setForm(current=>({...current,[key]:value}));setErrors(current=>({...current,[key]:undefined}));}}
 onBlur={key=>setErrors(current=>({...current,[key]:addressErrors(form,ur)[key]}))} onDefault={setDefault} onSubmit={submit} onCancel={requestClose}/></>}</div></CustomerDialog>}
 {deleting&&book&&<CustomerDialog title={t("Delete This Address?","یہ پتہ حذف کریں؟")} ur={ur} busy={!!pending} onClose={()=>{setDeleting(null);setNotice(null);restoreFocus();}}><div className="address-delete-dialog">
 <p>{t("This address will be removed from your saved delivery addresses.","یہ پتہ آپ کے محفوظ ترسیلی پتوں سے ہٹا دیا جائے گا۔")}</p><p className="address-delete-summary"><bdi>{deleting.recipient_name}</bdi><span><bdi>{deleting.city}</bdi></span></p>{deleting.is_default&&<p className="address-note">{t("You’ll have no default address until you choose another.","دوسرا پتہ منتخب کرنے تک کوئی ترجیحی پتہ نہیں ہوگا۔")}</p>}
 {message}<div className="address-dialog-actions"><button className="address-secondary" disabled={!!pending} onClick={()=>{setDeleting(null);setNotice(null);restoreFocus();}}>{t("Keep Address","پتہ رکھیں")}</button><button className="address-primary address-danger" disabled={!!pending||stale} onClick={()=>void mutate("delete:"+deleting.id,"DELETE",{id:deleting.id,expected_version:deleting.version,expected_book_version:book.book_version})}>{pending?t("Deleting…","حذف ہو رہا ہے…"):t("Delete Address","پتہ حذف کریں")}</button></div></div></CustomerDialog>}
 </section>;
}
