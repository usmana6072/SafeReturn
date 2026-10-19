"use client";
import { useActionState, useEffect, useState } from "react";
import { openWhatsApp, revealContact } from "../app/q/[token]/public-actions";
import { ContactChallenge } from "./contact-challenge";

type State={status:"idle"|"revealed"|"ready"|"unavailable"|"limited";phone?:string;tel_uri?:string;url?:string};
function parse(raw:string):State {try{return JSON.parse(raw) as State;}catch{return {status:"unavailable"};}}
function ContactAction({token,contactId,ur,siteKey,binding}:{token:string;contactId?:string;ur:boolean;siteKey:string;binding:string}) {
  const action=contactId?revealContact:openWhatsApp;
  const [raw,submit,pending]=useActionState(action.bind(null,token),JSON.stringify({status:"idle"}));
  const state=parse(raw),[requested,setRequested]=useState(false),[proof,setProof]=useState("");
  useEffect(()=>setProof(""),[raw]);
  const label=contactId?(ur?"نمبر دکھائیں":"Reveal contact number"):(ur?"واٹس ایپ کھولیں":"Open WhatsApp");
  return <form action={submit} className="public-action">
    {contactId && <input type="hidden" name="contact_id" value={contactId}/>}
    <input type="hidden" name="cf-turnstile-response" value={proof}/>
    {!contactId && <p>{ur?"واٹس ایپ کھولنے سے مالک کا منتخب کردہ نمبر ظاہر ہوگا۔ گفتگو SafeReturn ان باکس میں محفوظ نہیں ہوتی۔":"Opening WhatsApp reveals the owner's chosen number. Chats happen outside SafeReturn and are not saved in its inbox."}</p>}
    {state.status==="revealed"?<p role="status"><a className="button" href={state.tel_uri}>{ur?"ابھی کال کریں":"Call now"}</a> <bdi dir="ltr">{state.phone}</bdi></p>
    :state.status==="ready"?<p role="status"><a className="button" href={state.url} target="_blank" rel="noopener noreferrer">{ur?"واٹس ایپ میں جاری رکھیں":"Continue in WhatsApp"}</a></p>
    :<>
      {!requested?<button className="button secondary" type="button" onClick={()=>setRequested(true)}>{label}</button>
      :!siteKey?<p role="alert">{ur?"تصدیق فی الحال دستیاب نہیں۔":"Contact verification is currently unavailable."}</p>
      :<><ContactChallenge key={raw} siteKey={siteKey} action={contactId?"ice_reveal":"whatsapp"} binding={binding} ur={ur} onToken={setProof}/>
        <button className="button secondary" disabled={!proof || pending}>{pending?(ur?"تصدیق ہو رہی ہے…":"Checking…"):(ur?"تصدیق کر کے جاری رکھیں":"Verify and continue")}</button></>}
      {state.status==="limited" && <p role="alert">{ur?"تصدیق ناکام یا درخواستیں بہت زیادہ ہیں۔ بعد میں کوشش کریں۔":"Verification failed or too many requests. Please try again later."}</p>}
      {state.status==="unavailable" && <p role="alert">{ur?"یہ رابطہ فی الحال دستیاب نہیں۔":"This contact is currently unavailable."}</p>}
    </>}
    <noscript><p>{ur?"محفوظ رابطے کی تصدیق کے لیے جاوا اسکرپٹ درکار ہے۔":"JavaScript is required for protected contact verification."}</p></noscript>
  </form>;
}
export function ContactReveal(props:{token:string;contactId:string;ur:boolean;siteKey:string;binding:string}) {return <ContactAction {...props}/>;}
export function WhatsAppAction(props:{token:string;ur:boolean;siteKey:string;binding:string}) {return <ContactAction {...props}/>;}
