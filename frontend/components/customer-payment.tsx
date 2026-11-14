"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { OfficialPaymentInstructions } from "./item-checkout";
import type { PaymentInstructions } from "../lib/item-cart";
import { uuid } from "../lib/qr-contract";

type Attempt = {id:string;state:string};
type Upload = {identity:string;token:string;url:string;uploaded:boolean};
export function PaymentForm({orderId,language}:{orderId:string;language:string}) {
  const ur=language==="ur", t=(en:string,u:string)=>ur?u:en;
  const [attempt,setAttempt]=useState<Attempt|null>(null),[instructions,setInstructions]=useState<PaymentInstructions|null>(null);
  const [busy,setBusy]=useState(false),[loaded,setLoaded]=useState(false),[status,setStatus]=useState("");
  const keys=useRef(new Map<string,string>()),pending=useRef<Upload|null>(null),running=useRef(false);
  const failure=(error:unknown)=>{
    const code=error instanceof Error?error.message:"";
    setStatus(code==="401"||code==="403"?t("Sign in again or check your permission before retrying.","دوبارہ لاگ اِن کریں یا اپنی اجازت چیک کریں۔")
      :code==="FILE_INVALID"?t("Choose a PNG, JPEG or PDF up to 5 MB.","۵ ایم بی تک PNG، JPEG یا PDF منتخب کریں۔")
      :code==="409"||code==="412"?t("Payment state changed. Refresh before retrying.","ادائیگی کی حالت بدل گئی۔ دوبارہ کوشش سے پہلے تازہ کریں۔")
      :code==="422"||code==="400"?t("Check the payment details and try again.","ادائیگی کی تفصیلات چیک کر کے دوبارہ کوشش کریں۔")
      :code==="429"?t("Too many requests. Please try later.","درخواستیں زیادہ ہیں۔ کچھ دیر بعد کوشش کریں۔")
      :t("Request not confirmed. Please retry; evidence is not payment verification.","درخواست کی تصدیق نہیں ہوئی۔ دوبارہ کوشش کریں؛ ثبوت ادائیگی کی تصدیق نہیں۔"));
  };
  async function read(path:string) {
    const response=await fetch('/payments/api?path='+encodeURIComponent(path),{cache:'no-store'});
    if(!response.ok)throw Error(String(response.status));
    return response.json();
  }
  async function load() {
    setBusy(true);setLoaded(false);setStatus("");setAttempt(null);setInstructions(null);
    const results=await Promise.allSettled([read(`/me/orders/${orderId}/payment-attempts`),read(`/me/orders/${orderId}/payment-instructions`)]);
    try {
      if(results[0].status==='rejected')throw results[0].reason;
      const data=results[0].value;
      if(!Array.isArray(data.items)||data.items.some((a:Attempt)=>!uuid(a.id)||typeof a.state!=="string"))throw Error();
      setAttempt(data.items.find((a:Attempt)=>['initiated','submitted','under_review','verified','disputed'].includes(a.state))??null);
      setLoaded(true);
    }catch(error){failure(error);}
    if(results[1].status==='fulfilled') {
      const value=results[1].value;
      if(value?.currency_code==='PKR'&&['bank_name','account_title','account_number','raast_id','instructions_en','instructions_ur'].every(k=>typeof value[k]==='string'))setInstructions(value);
    }
    setBusy(false);
  }
  useEffect(()=>{void load();},[orderId]);
  async function command(path:string,body:unknown) {
    const signature=JSON.stringify({path,body});
    if(!keys.current.has(signature))keys.current.set(signature,crypto.randomUUID());
    const response=await fetch('/payments/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,body,key:keys.current.get(signature)})});
    if(!response.ok) { if(response.status===401||response.status===403){setAttempt(null);setInstructions(null);setLoaded(false);pending.current=null;} throw Error(String(response.status)); }
    return response.json();
  }
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();if(running.current||!loaded)return;running.current=true;setBusy(true);setStatus("");
    try {
      const form=new FormData(event.currentTarget);
      const result=await command(`/me/orders/${orderId}/payment-attempts`,{sender_account:form.get('account'),sender_holder_name:form.get('holder')});
      if(!uuid(result.attempt_id)||result.state!=='under_review')throw Error();
      setAttempt({id:result.attempt_id,state:result.state});setStatus(t('Payment is under review. Evidence does not confirm settlement.','ادائیگی زیر جائزہ ہے۔ ثبوت رقم موصول ہونے کی تصدیق نہیں۔'));
    }catch(error){failure(error);}finally{running.current=false;setBusy(false);}
  }
  async function evidence(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();if(running.current||!attempt)return;running.current=true;setBusy(true);setStatus("");
    try {
      const file=new FormData(event.currentTarget).get('file') as File;
      if(!file?.size||file.size>5000000||!['image/png','image/jpeg','application/pdf'].includes(file.type))throw Error('FILE_INVALID');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))).map(x=>x.toString(16).padStart(2,'0')).join('');
      let upload=pending.current;
      if(!upload||upload.identity!==attempt.id+hash) {
        const grant=await command(`/me/payment-attempts/${attempt.id}/evidence-uploads`,{filename:file.name,content_type:file.type,bytes_size:file.size,sha256:hash});
        if(typeof grant.upload_token!=='string'||typeof grant.upload_url!=='string'||new URL(grant.upload_url).protocol!=='https:')throw Error();
        upload={identity:attempt.id+hash,token:grant.upload_token,url:grant.upload_url,uploaded:false};pending.current=upload;
      }
      if(!upload.uploaded) {
        const response=await fetch(upload.url,{method:'PUT',headers:{'Content-Type':file.type,'x-upsert':'false'},body:file});
        if(!response.ok&&response.status!==409)throw Error();upload.uploaded=true;
      }
      const result=await command(`/me/payment-attempts/${attempt.id}/evidence-finalize`,{upload_token:upload.token,sha256:hash});
      if(result.received!==true)throw Error();
      setStatus(t('Evidence received. Payment remains under review.','ثبوت موصول ہو گیا۔ ادائیگی ابھی زیر جائزہ ہے۔'));
    }catch(error){failure(error);}finally{running.current=false;setBusy(false);}
  }
  const canUpload=attempt&&['initiated','submitted','under_review'].includes(attempt.state);
  return <section aria-busy={busy}><h1>{t('Payment review','ادائیگی کا جائزہ')}</h1><p className="lead">{t('Finance must independently verify bank settlement before approval.','منظوری سے پہلے مالیاتی ٹیم بینک میں رقم موصول ہونے کی الگ تصدیق کرے گی۔')}</p>
    <button disabled={busy} onClick={()=>void load()}>{t('Refresh payment','ادائیگی تازہ کریں')}</button>
    {instructions?<div className="card"><OfficialPaymentInstructions value={instructions} ur={ur}/></div>:<p>{t('Official bank/Raast instructions are unavailable. Contact support before transferring.','ادائیگی کی سرکاری ہدایات دستیاب نہیں۔ رقم بھیجنے سے پہلے مدد حاصل کریں۔')}</p>}
    {loaded&&!attempt&&<form className="card" onSubmit={submit}><label>{t('Sender holder name','بھیجنے والے کا نام')}<input name="holder" required maxLength={160}/></label><label>{t('Sender account','بھیجنے والے کا اکاؤنٹ')}<input name="account" required minLength={4} maxLength={80} autoComplete="off"/></label><button disabled={busy}>{t('Submit for review','جائزے کے لیے جمع کریں')}</button></form>}
    {canUpload&&<form className="card" onSubmit={evidence}><label>{t('Optional private evidence','اختیاری نجی ثبوت')}<input name="file" type="file" required accept="image/png,image/jpeg,application/pdf"/></label><p>{t('PNG, JPEG, PDF; maximum 5 MB','PNG، JPEG، PDF؛ زیادہ سے زیادہ ۵ ایم بی')}</p><button disabled={busy}>{t('Upload evidence','ثبوت اپ لوڈ کریں')}</button></form>}
    {attempt&&!canUpload&&<p>{t('This payment is not accepting evidence. View your order for its current status.','اس ادائیگی کے لیے ثبوت قبول نہیں ہو رہا۔ موجودہ حالت آرڈر میں دیکھیں۔')}</p>}
    <p role="status">{status}</p><Link href={`/orders/${orderId}`}>{t('Back to order','آرڈر پر واپس')}</Link>
  </section>;
}
