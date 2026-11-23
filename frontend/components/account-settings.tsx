"use client";
import Link from "next/link";
import {useActionState,useEffect,useRef,useState,useTransition,type ReactNode} from "react";
import {useFormStatus} from "react-dom";
import {useRouter} from "next/navigation";
import type {Account} from "../lib/auth/server";
import type {FormState} from "../app/auth/actions";
import {accountCopy,accountInitials} from "../lib/account-copy";
import {CustomerDialog} from "./customer-dialog";
import {CustomerIcon,type CustomerIconName} from "./customer-icon";

type SaveAction=(previous:FormState,form:FormData)=>Promise<FormState>;
export function AccountRetry({ur,label}:{ur:boolean;label?:string}){const c=accountCopy(ur),router=useRouter(),[pending,start]=useTransition();return <button type="button" className="settings-secondary" disabled={pending} onClick={()=>start(()=>router.refresh())}>{pending?c.retrying:label??c.retry}</button>;}
export function AccountSkeleton(){return <section className="settings-screen settings-loading" role="status" aria-busy="true"><span className="sr-only">Loading account settings / اکاؤنٹ کی ترتیبات لوڈ ہو رہی ہیں</span><i className="settings-skeleton-title" aria-hidden="true"/><div className="settings-profile" aria-hidden="true"><i/><div><i/><i/></div></div><div className="settings-grid" aria-hidden="true">{[0,1,2,3].map(n=><div className="settings-card" key={n}><i/><i/><i/></div>)}</div></section>;}
export function SettingsRow({icon,title,description,href,onClick,value}:{icon:CustomerIconName;title:string;description?:string;href?:string;onClick?:()=>void;value?:string}){
 const body=<><span className="settings-icon"><CustomerIcon name={icon}/></span><span className="settings-row-copy"><strong>{title}</strong>{description&&<small>{description}</small>}</span>{value&&<span className="settings-current">{value}</span>}<CustomerIcon name="arrow"/></>;
 return href?<Link className="settings-row" href={href} prefetch={false}>{body}</Link>:<button className="settings-row" onClick={onClick}>{body}</button>;
}
function LogoutButton({ur}:{ur:boolean}){const {pending}=useFormStatus(),c=accountCopy(ur);return <button className="settings-logout" disabled={pending}><CustomerIcon name="logout"/>{pending?c.loggingOut:c.logout}</button>;}
function AccountEditor({mode,account,name,email,ur,action,onClose}:{mode:"profile"|"language";account:Account;name:string;email:string;ur:boolean;action:SaveAction;onClose:()=>void}){
 const c=accountCopy(ur),[value,setValue]=useState(name),[locale,setLocale]=useState(ur?"ur":"en"),[invalid,setInvalid]=useState(""),[discard,setDiscard]=useState(false);
 const [state,submit,pending]=useActionState(action,{status:"idle"} as FormState),guard=useRef(false),postedVersion=useRef(account.version),input=useRef<HTMLInputElement>(null),dirtyRef=useRef(false),pendingRef=useRef(false);
 const dirty=mode==="profile"?value!==name:locale!==(ur?"ur":"en");dirtyRef.current=dirty;pendingRef.current=pending;
 const blocked=state.status==="error"&&state.reason==="stale"&&postedVersion.current===account.version;
 useEffect(()=>{if(!pending)guard.current=false;},[pending,state]);
 useEffect(()=>{
  history.pushState({...history.state,safeReturnAccountEditor:true},"",location.href);
  function pop(){if(pendingRef.current||dirtyRef.current){history.pushState({...history.state,safeReturnAccountEditor:true},"",location.href);if(!pendingRef.current)setDiscard(true);}else onClose();}
  function leave(event:BeforeUnloadEvent){if(dirtyRef.current){event.preventDefault();event.returnValue="";}}
  window.addEventListener("popstate",pop);window.addEventListener("beforeunload",leave);
  return ()=>{window.removeEventListener("popstate",pop);window.removeEventListener("beforeunload",leave);};
 },[]);
 function close(){if(pending)return;if(dirty)setDiscard(true);else finish();}
 function finish(){if(history.state?.safeReturnAccountEditor)history.back();onClose();}
 return <CustomerDialog title={discard?c.discard:mode==="profile"?c.edit:c.language} ur={ur} busy={pending} onClose={()=>discard?setDiscard(false):close()}><div className="settings-editor">
 {discard?<><p>{c.discardText}</p><div className="settings-dialog-actions"><button className="settings-secondary" onClick={()=>setDiscard(false)}>{c.keep}</button><button className="settings-primary" onClick={finish}>{c.discardAction}</button></div></>:<form className="settings-form" action={submit} noValidate onReset={event=>event.preventDefault()} onSubmit={event=>{
  if(guard.current||blocked){event.preventDefault();return;}
  const trimmed=value.trim();
  if(mode==="profile"&&(!trimmed||trimmed.length>120||/[\x00-\x1f\x7f]/.test(trimmed))){event.preventDefault();setInvalid(!trimmed?c.requiredName:c.invalidName);input.current?.focus();return;}
  guard.current=true;postedVersion.current=account.version;
 }}>
 <input type="hidden" name="version" value={account.version}/>
 <fieldset disabled={pending}>
 {mode==="profile"?<><label htmlFor="account-display-name">{c.name}</label><input ref={input} id="account-display-name" name="display_name" autoComplete="name" value={value} maxLength={120} required aria-invalid={!!invalid} aria-describedby={invalid?"account-name-error":"account-name-help"} onChange={event=>{setValue(event.target.value);setInvalid("");}}/>
 {invalid&&<p className="settings-field-error" id="account-name-error" role="alert">{invalid}</p>}<p className="settings-note" id="account-name-help">{c.nameHelp}</p>
 <input type="hidden" name="preferred_locale" value={ur?"ur":"en"}/>
 <div className="settings-readonly"><span>{c.email}</span><bdi>{email||"—"}</bdi><small>{c.readonlyHelp}</small></div></>:<fieldset className="settings-language"><legend className="sr-only">{c.language}</legend>{[["en","English"],["ur","اردو"]].map(([language,label])=><label key={language} lang={language} className={locale===language?"selected":""}><span><CustomerIcon name="language"/>{label}</span><input type="radio" name="preferred_locale" value={language} checked={locale===language} onChange={()=>setLocale(language)}/></label>)}</fieldset>}
 {state.status==="error"&&<div className="settings-feedback error" role="alert"><p>{blocked?c.stale:state.reason==="stale"?c.review:c.profileFailed}</p>{state.reason==="stale"&&<><p>{c.currentName}: <bdi>{account.display_name||"—"}</bdi></p><AccountRetry ur={ur} label={c.refresh}/></>}</div>}
 <div className="settings-dialog-actions"><button className="settings-primary" disabled={blocked||mode==="language"&&!dirty} type="submit">{pending?c.saving:c.save}</button><button className="settings-secondary" type="button" onClick={close}>{c.cancel}</button></div>
 </fieldset></form>}</div></CustomerDialog>;
}
export function AccountSettings({account,email,initialName,ur,saved,logoutFailed,saveAction,languageAction,logoutAction}:{account:Account;email:string;initialName:string;ur:boolean;saved:boolean;logoutFailed:boolean;saveAction:SaveAction;languageAction:SaveAction;logoutAction:()=>Promise<void>}){
 const c=accountCopy(ur),name=account.display_name??initialName,[editor,setEditor]=useState<"profile"|"language"|null>(null),trigger=useRef<HTMLElement|null>(null);
 function open(mode:"profile"|"language"){trigger.current=document.activeElement as HTMLElement;setEditor(mode);}
 function close(){setEditor(null);requestAnimationFrame(()=>trigger.current?.focus());}
 const sections:[string,ReactNode][]=[
 [c.personal,<><button className="settings-info-row" onClick={()=>open("profile")}><span>{c.name}</span><strong><bdi>{name||"—"}</bdi></strong><CustomerIcon name="arrow"/></button><div className="settings-info-row"><span>{c.email}</span><bdi>{email||"—"}</bdi></div>{account.masked_contact?.phone&&<div className="settings-info-row"><span>{c.phone}</span><bdi>{account.masked_contact.phone}</bdi></div>}</>],
 [c.security,<><SettingsRow icon="check" title={c.password} description={c.passwordHelp} href="/auth/forgot-password"/>{!account.email_verified&&<SettingsRow icon="inbox" title={c.verify} href="/auth/verify-email"/>}</>],
 [c.preferences,<SettingsRow icon="language" title={c.language} description={c.languageHelp} value={ur?"اردو":"English"} onClick={()=>open("language")}/>],
 [c.privacy,<><SettingsRow icon="box" title={c.download} description={c.downloadHelp} href="/account/privacy/exports"/><SettingsRow icon="account" title={c.requests} description={c.requestsHelp} href="/settings"/><SettingsRow icon="pending" title={c.history} description={c.historyHelp} href="/settings#privacy-history"/></>],
 [c.support,<><SettingsRow icon="pin" title={c.addresses} description={c.addressesHelp} href="/account/shipping-addresses"/><SettingsRow icon="help" title={c.help} description={c.helpText} href="/help"/></>]
 ];
 return <section className="settings-screen"><header className="settings-intro"><h1>{c.title}</h1><p>{c.subtitle}</p></header>
 {saved&&<p className="settings-feedback" role="status">{c.saved}</p>}{logoutFailed&&<p className="settings-feedback error" role="alert">{c.logoutFailed}</p>}
 <section className="settings-profile" aria-label={c.personal}><span className="settings-avatar" aria-hidden="true">{accountInitials(name)}</span><div><h2><bdi>{name||c.customer}</bdi></h2>{email&&<p><bdi>{email}</bdi></p>}<span className={"settings-verification "+(account.email_verified?"verified":"")}><CustomerIcon name={account.email_verified?"check":"inbox"}/>{account.email_verified?c.verified:c.unverified}</span></div><button className="settings-secondary" onClick={()=>open("profile")}>{c.edit}</button></section>
 <div className="settings-grid">{sections.map(([title,content])=><section className="settings-group" key={title}><h2>{title}</h2><div className="settings-card">{content}</div></section>)}</div>
 <form className="settings-logout-form" action={logoutAction}><LogoutButton ur={ur}/></form>
 {editor&&<AccountEditor mode={editor} key={editor} account={account} name={name} email={email} ur={ur} action={editor==="profile"?saveAction:languageAction} onClose={close}/>}</section>;
}

