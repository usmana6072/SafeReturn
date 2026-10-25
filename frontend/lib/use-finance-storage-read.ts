"use client";
import {useCallback,useEffect,useRef,useState} from 'react';
import {metadataId,metadataQuery} from './finance-storage-contract';
export function useFinanceStorageRead<T>(storage:boolean,parse:(value:unknown,q:URLSearchParams)=>T,id?:string){
  const [data,setData]=useState<T|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const generation=useRef(0),active=useRef<AbortController|null>(null),query=useRef(new URLSearchParams());
  const clear=useCallback(()=>{generation.current++;active.current?.abort();setData(null);setBusy(false);},[]);
  const load=useCallback(async(q:URLSearchParams)=>{
    const n=++generation.current;active.current?.abort();const controller=new AbortController();active.current=controller;setData(null);setError('');setBusy(true);
    try{const safe=metadataQuery(q,storage?'storage':'finance');query.current=safe;
      const response=await fetch((storage?'/admin/storage/api':'/admin/finance/sheet-sync/api')+(safe.size?'?'+safe:''),{method:'GET',cache:'no-store',redirect:'error',signal:controller.signal});
      if(!response.ok)throw Error(String(response.status));const result=parse(await response.json(),safe);
      if(n===generation.current&&!controller.signal.aborted)setData(result);
    }catch(e){if(n===generation.current&&!controller.signal.aborted)setError(e instanceof Error&&['401','403'].includes(e.message)?'Access denied. A permitted staff role and verified MFA are required.':'Metadata unavailable. Refresh to try again.');}
    finally{if(n===generation.current)setBusy(false);}
  },[storage,parse]);
  useEffect(()=>{
    try{if(id)metadataId(id);void load(metadataQuery(new URLSearchParams(location.search),storage?'storage':'finance'));}catch{setError('Invalid record reference or filters.');return;}
    const visibility=()=>{if(document.hidden)clear();else void load(query.current);};document.addEventListener('visibilitychange',visibility);
    return ()=>{generation.current++;active.current?.abort();document.removeEventListener('visibilitychange',visibility);};
  },[id,storage,load,clear]);
  return {data,error,busy,load,query,clear};
}
