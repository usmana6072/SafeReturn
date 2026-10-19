"use client";
import Script from "next/script";
import { useEffect, useRef, useState } from "react";

type Widget = {render:(element:HTMLElement,options:Record<string,unknown>)=>string;remove:(id:string)=>void};
declare global { interface Window { turnstile?:Widget } }
export function ContactChallenge({siteKey,action,binding,ur,onToken}:{siteKey:string;action:string;binding:string;ur:boolean;onToken:(value:string)=>void}) {
  const container=useRef<HTMLDivElement>(null), widget=useRef<string | undefined>(undefined);
  const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);
  useEffect(()=>{
    if(!ready || !container.current || !window.turnstile)return;
    widget.current=window.turnstile.render(container.current,{sitekey:siteKey,action,cData:binding,language:ur?"auto":"en",size:"compact","response-field":false,callback:onToken,"expired-callback":()=>onToken(""),"error-callback":()=>{onToken("");setFailed(true);}});
    return ()=>{if(widget.current && window.turnstile)window.turnstile.remove(widget.current);};
  },[ready,siteKey,action,binding,ur,onToken]);
  return <><Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" onReady={()=>setReady(true)} onError={()=>setFailed(true)} />
    <div ref={container} aria-label={ur?"رابطے کی تصدیق":"Contact verification"}/>
    {failed && <p role="alert">{ur?"تصدیق دستیاب نہیں۔ دوبارہ کوشش کریں۔":"Verification is unavailable. Please try again."}</p>}
  </>;
}
