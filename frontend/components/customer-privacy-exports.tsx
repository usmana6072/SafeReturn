"use client";
import Link from "next/link";
import {useState} from "react";
import type {ExportStatus} from "./privacy-exports";
import {CustomerIcon} from "./customer-icon";
import {accountCopy} from "../lib/account-copy";
import {uuid} from "../lib/qr-contract";
export function CustomerPrivacyExports({ur,items,id,setId,confirmed,setConfirmed,busy,notice,perform}:{ur:boolean;items:ExportStatus[];id:string;setId:(value:string)=>void;confirmed:boolean;setConfirmed:(value:boolean)=>void;busy:boolean;notice:string;perform:(action:string,row?:ExportStatus)=>Promise<void>}){
 const c=accountCopy(ur),[invalid,setInvalid]=useState(false),[copy,setCopy]=useState("");
 async function copyReference(value:string){try{await navigator.clipboard.writeText(value);setCopy(c.copied);}catch{setCopy(c.copyFailed);}}
 return <section className="settings-screen settings-export"><Link className="settings-back" href="/account"><CustomerIcon name="arrow"/>{c.back}</Link><header className="settings-intro"><h1>{c.exportTitle}</h1><p>{c.exportIntro}</p></header>
 <div className="settings-grid"><section className="settings-panel"><span className="settings-feature-icon"><CustomerIcon name="box"/></span><h2>{c.exportRequest}</h2><p className="settings-note">{c.exportTiming}</p>
 <label className="settings-check"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event=>setConfirmed(event.target.checked)}/><span>{c.exportConfirm}</span></label>
 <button className="settings-primary" disabled={busy||!confirmed} onClick={()=>void perform("request")}>{busy?c.working:c.exportRequest}</button>
 <details className="settings-disclosure"><summary>{ur?"کون سی معلومات شامل ہیں؟":"What’s included?"}</summary><p className="settings-note">{c.exportScope}</p></details>
 </section><section className="settings-panel"><h2>{c.checkStatus}</h2><form className="settings-form" noValidate onSubmit={event=>{event.preventDefault();if(!uuid(id)){setInvalid(true);return;}void perform("load");}}>
 <label htmlFor="export-reference">{c.reference}</label><input id="export-reference" value={id} disabled={busy} onChange={event=>{setId(event.target.value.trim().toLowerCase());setInvalid(false);}} maxLength={36} autoComplete="off" spellCheck={false} dir="ltr" aria-invalid={invalid} aria-describedby={invalid?"export-reference-error":"export-reference-help"}/>
 <p className="settings-note" id="export-reference-help">{c.referenceHelp}</p>{invalid&&<p className="settings-field-error" id="export-reference-error" role="alert">{c.referenceInvalid}</p>}<button className="settings-secondary" disabled={busy} type="submit">{busy?c.working:c.checkStatus}</button></form>
 </section></div>
 {notice&&<p className="settings-feedback" role="status">{notice}</p>}
 <section className="settings-panel settings-export-status"><h2>{c.statusHeading}</h2>{items.length===0?<div className="settings-empty"><CustomerIcon name="pending"/><h3>{c.noExport}</h3><p>{c.noExportText}</p></div>:items.map(row=>{
 const states=c.exportStates as Record<string,string>,label=states[row.status]??(ur?"معاونت سے حالت معلوم کریں":"Contact Support for Status"),expired=!!row.expires_at&&Date.parse(row.expires_at)<=Date.now();
 return <article className="settings-export-result" key={row.request_id}><span className={"settings-verification "+(row.status==="ready"&&!expired?"verified":"")}><CustomerIcon name={row.status==="ready"?"check":"pending"}/>{label}</span>
 <p className="settings-note">{c.requestAgain}</p><div className="settings-reference"><code dir="ltr">{row.request_id}</code><button className="settings-secondary" onClick={()=>void copyReference(row.request_id)}><CustomerIcon name="copy"/>{c.copy}</button></div>
 {copy&&<p className="settings-note" role="status">{copy}</p>}
 {row.expires_at&&Number.isFinite(Date.parse(row.expires_at))&&<p className="settings-note">{c.expires}: <time dateTime={row.expires_at}>{new Intl.DateTimeFormat(ur?"ur-PK":"en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Karachi"}).format(new Date(row.expires_at))}</time></p>}
 {row.status==="ready"&&<button className="settings-primary" disabled={busy||!confirmed||expired} onClick={()=>void perform("download",row)}>{busy?c.working:c.downloadReady}</button>}
 {row.categories&&<details className="settings-disclosure"><summary>{ur?"برآمد کی تفصیلات":"Export Details"}</summary><dl className="settings-export-details">{Object.entries(row.categories).map(([name,category])=><div key={name}><dt>{name.replace(/_/g," ")}</dt><dd>{category.disposition.replace(/_/g," ")} · {category.reason_code.replace(/_/g," ")}{category.source_count!==null&&<> · {category.source_count}</>}</dd></div>)}</dl></details>}
 </article>;
 })}</section><p className="settings-note">{c.exportNote}</p><Link className="settings-help-link" href="/settings">{c.requests}</Link>
 </section>;
}

