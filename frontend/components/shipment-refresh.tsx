"use client";
import { useEffect, useRef, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CustomerIcon } from "./customer-icon";

export function ShipmentRefresh({ ur, automatic=true, retry=false }: { ur:boolean;automatic?:boolean;retry?:boolean }) {
  const router=useRouter(),[pending,start]=useTransition(),running=useRef(false);
  function refresh(){
    if(running.current||document.hidden)return;
    running.current=true;start(()=>router.refresh());
  }
  useEffect(()=>{if(!pending)running.current=false;},[pending]);
  useEffect(()=>{
    if(pending||!automatic)return;
    // Refresh recorded shipment data while visible. No direct courier connection is implied.
    const timer=window.setInterval(refresh,60000);
    document.addEventListener("visibilitychange",refresh);
    return()=>{window.clearInterval(timer);document.removeEventListener("visibilitychange",refresh);};
  },[router,pending,automatic]);
  const label=retry?(ur?"دوبارہ کوشش کریں":"Retry"):(ur?"ترسیلات تازہ کریں":"Refresh Shipments");
  return <><button className={retry?"ship-secondary":"ship-refresh"} type="button" disabled={pending} aria-label={label} title={label} onClick={refresh}><CustomerIcon name="refresh"/>{retry&&label}</button>
    {pending&&<span className="sr-only" role="status">{ur?"ترسیلات تازہ ہو رہی ہیں":"Refreshing shipments"}</span>}</>;
}
