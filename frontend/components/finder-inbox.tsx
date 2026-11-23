"use client";
import Link from "next/link";
import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { type FinderSummary,type FinderStatus,type InboxContext,inboxHref,inboxQuery,finderLabel,qrMessageName,finderDate } from "../lib/finder-inbox";
import { CustomerIcon } from "./customer-icon";
import { CustomerDialog } from "./customer-dialog";

export function FinderRetry({ur}:{ur:boolean}){
  const router=useRouter(),[pending,start]=useTransition();
  return <button className="finder-secondary" disabled={pending} onClick={()=>start(()=>router.refresh())}>{pending?(ur?"کوشش جاری ہے…":"Retrying…"):(ur?"دوبارہ کوشش کریں":"Retry")}</button>;
}
export function FinderSkeleton(){
  return <div className="finder-screen finder-loading" role="status" aria-busy="true"><span className="sr-only">Loading messages / پیغامات لوڈ ہو رہے ہیں</span><i className="finder-skeleton-title" aria-hidden="true"/>
    <div className="finder-rows" aria-hidden="true">{[0,1,2,3].map(i=><div key={i}><i/><div><i/><i/></div><i/></div>)}</div></div>;
}
export function FinderInbox({items,next,context,unread,failed,ur,result}:{items:FinderSummary[];next:string|null;context:InboxContext;unread:string|null;failed:boolean;ur:boolean;result?:string}){
  const [search,setSearch]=useState(""),input=useRef<HTMLInputElement>(null),t=(en:string,u:string)=>ur?u:en;
  const complete=!next&&!context.cursor;
  const term=search.trim().toLocaleLowerCase();
  const messages=items.filter(m=>!term||(qrMessageName(m,ur)+" "+(m.finder_name??"")).toLocaleLowerCase().includes(term));
  const filters:[FinderStatus|undefined,string,string][]=[[undefined,"All","تمام"],["new","Unread","نئے"],["viewed","Read","پڑھے گئے"],["archived","Archived","محفوظ"],["flagged","Flagged","نشان زدہ"]];
  const viewFiltered=!!context.status||!!context.qr_id||!!term||!!context.cursor;
  return <section className="finder-screen"><header className="finder-intro"><div><h1>{t("Finder Messages","فائنڈر پیغامات")}</h1><p>{t("Messages from people who scanned your QR codes.","ان لوگوں کے پیغامات جنہوں نے آپ کے QR کوڈز اسکین کیے۔")}</p></div>
    {unread!==null&&!context.qr_id&&<span className="finder-unread-count">{unread} {t("Unread","نئے")}</span>}</header>
    {result==="deleted"&&<p className="finder-feedback" role="status">{t("Message removed from your inbox.","پیغام اِن باکس سے ہٹا دیا گیا۔")}</p>}
    {context.qr_id&&<p className="finder-note">{t("Showing messages for one QR code.","ایک QR کوڈ کے پیغامات دکھائے جا رہے ہیں۔")} <Link href="/inbox">{t("View All Messages","تمام پیغامات دیکھیں")}</Link></p>}
    <nav className="finder-filters" aria-label={t("Filter messages","پیغامات فلٹر کریں")}>{filters.map(([status,en,u])=><Link key={en} href={inboxHref({...context,cursor:undefined,status})}
      className={context.status===status?"selected":""} aria-current={context.status===status?"page":undefined} prefetch={false}>{ur?u:en}</Link>)}</nav>
    {!failed&&items.length>0&&complete&&<><div className="finder-search"><CustomerIcon name="search"/><input ref={input} type="search" value={search} onChange={e=>setSearch(e.target.value)}
      autoComplete="off" enterKeyHint="search" placeholder={t("Search messages or QR codes","پیغامات یا QR کوڈز تلاش کریں")} aria-label={t("Search messages or QR codes","پیغامات یا QR کوڈز تلاش کریں")}/>
      {search&&<button aria-label={t("Clear search","تلاش صاف کریں")} onClick={()=>{setSearch("");input.current?.focus();}}><CustomerIcon name="close"/></button>}</div>
      <p className="finder-search-help">{t("Search QR names and finder names in this view.","اس منظر میں QR اور پیغام بھیجنے والوں کے نام تلاش کریں۔")}</p></>}
    {!complete&&<p className="finder-note">{t("Showing a page of messages. Use the filters to browse your inbox.","پیغامات کا ایک صفحہ دکھایا جا رہا ہے۔ اِن باکس دیکھنے کے لیے فلٹر استعمال کریں۔")}</p>}
    {failed?<div className="finder-empty" role="alert"><CustomerIcon name="inbox"/><h2>{t("Couldn’t Load Messages","پیغامات لوڈ نہیں ہو سکے")}</h2><p>{t("Please try again.","دوبارہ کوشش کریں۔")}</p><FinderRetry ur={ur}/></div>:
      !messages.length?<div className="finder-empty"><span className="finder-empty-icon"><CustomerIcon name="inbox"/></span><h2>{viewFiltered?t("No Matching Messages","کوئی مماثل پیغام نہیں"):t("No Finder Messages Yet","ابھی کوئی فائنڈر پیغام نہیں")}</h2>
        <p>{viewFiltered?t("Try another filter to view your messages.","پیغامات دیکھنے کے لیے فلٹر تبدیل کریں۔"):t("Messages from people who scan your QR codes will appear here.","آپ کے QR کوڈز اسکین کرنے والوں کے پیغامات یہاں دکھائی دیں گے۔")}</p>
        {term?<button className="finder-secondary" onClick={()=>setSearch("")}>{t("Clear Filters","فلٹر صاف کریں")}</button>:viewFiltered?<Link className="finder-secondary" href="/inbox">{t("Clear Filters","فلٹر صاف کریں")}</Link>:<Link className="finder-primary" href="/my-qr">{t("Manage My QR Codes","میرے QR کوڈز کا انتظام")}</Link>}</div>:
      <div className="finder-rows">{messages.map(m=>{
        const query=inboxQuery(context);
        return <Link className={"finder-row "+(m.status==="new"?"unread":"")} href={`/inbox/${m.id}`+(query.size?"?"+query:"")} key={m.id} prefetch={false}>
          <span className="finder-avatar" aria-hidden="true"><CustomerIcon name={m.tag_type==="ice"?"medical":"tag"}/></span>
          <div className="finder-row-content"><div className="finder-row-top"><h2><bdi>{qrMessageName(m,ur)}</bdi></h2><time dateTime={m.submitted_at}>{finderDate(m.submitted_at,ur,true)}</time></div>
            <p>{t("From","کی طرف سے")} <bdi>{m.finder_name||t("Anonymous Finder","نامعلوم فائنڈر")}</bdi></p>
            <span className="finder-read-state">{m.status==="new"&&<i aria-hidden="true"/>}{finderLabel(m.status,ur)}</span></div><CustomerIcon name="arrow"/>
        </Link>;
      })}</div>}
    <div className="finder-pagination">{context.cursor&&<Link className="finder-secondary" href={inboxHref({...context,cursor:undefined})}>{t("Latest Messages","تازہ ترین پیغامات")}</Link>}
      {next&&<Link className="finder-secondary" href={inboxHref({...context,cursor:next})}>{t("Older Messages","پرانے پیغامات")}</Link>}
      <Link className="finder-help" href="/help">{t("Support","مدد")}</Link></div>
  </section>;
}

export function FinderActions({action,status,context,ur}:{action:(form:FormData)=>Promise<void>;status:FinderStatus;context:InboxContext;ur:boolean}){
  const [selected,setSelected]=useState<string>(status==="new"?"viewed":status),[open,setOpen]=useState(false),[busy,setBusy]=useState(false);
  const running=useRef(false),trigger=useRef<HTMLButtonElement>(null),t=(en:string,u:string)=>ur?u:en;
  async function submit(form:FormData){
    if(running.current)return;
    running.current=true;setBusy(true);
    try{await action(form);}finally{running.current=false;setBusy(false);}
  }
  const hidden=<>{context.status&&<input type="hidden" name="return_status" value={context.status}/>}
    {context.cursor&&<input type="hidden" name="return_cursor" value={context.cursor}/>}
    {context.qr_id&&<input type="hidden" name="return_qr_id" value={context.qr_id}/>}</>;
  function close(){setOpen(false);requestAnimationFrame(()=>trigger.current?.focus());}
  return <section className="finder-panel finder-actions"><h2>{t("Manage Message","پیغام کا انتظام")}</h2>
    <form action={submit}>{hidden}<fieldset disabled={busy}><label>{t("Message Status","پیغام کی حالت")}<select name="status" aria-label={t("Message Status","پیغام کی حالت")} value={selected} onChange={e=>setSelected(e.target.value)}>
      <option value="viewed">{t("Read","پڑھا گیا")}</option><option value="archived">{t("Archived","محفوظ شدہ")}</option><option value="flagged">{t("Flagged","نشان زدہ")}</option></select></label>
      <p className="finder-note">{t("Messages stay unread until you mark them as read.","آپ کے پڑھا گیا نشان لگانے تک پیغامات نئے رہتے ہیں۔")}</p>
      <button className="finder-primary" type="submit">{busy?t("Saving…","محفوظ ہو رہا ہے…"):selected==="viewed"&&status==="new"?t("Mark as Read","پڑھا گیا نشان لگائیں"):t("Save Status","حالت محفوظ کریں")}</button>
      <button ref={trigger} className="finder-delete" type="button" onClick={()=>setOpen(true)}>{t("Delete Message","پیغام حذف کریں")}</button>
    </fieldset></form>
    {open&&<CustomerDialog title={t("Delete This Message?","یہ پیغام حذف کریں؟")} ur={ur} busy={busy} onClose={close}>
      <p>{t("This removes the message from your inbox. Records may remain under retention or legal obligations.","پیغام آپ کے اِن باکس سے ہٹ جائے گا۔ قانونی یا ریکارڈ برقرار رکھنے کی پالیسی کے تحت ریکارڈ محفوظ رہ سکتا ہے۔")}</p>
      <form action={submit}>{hidden}<input type="hidden" name="status" value="deleted"/><input type="hidden" name="confirm" value="on"/>
        <div className="finder-dialog-actions"><button className="finder-secondary" type="button" disabled={busy} onClick={close}>{t("Keep Message","پیغام رکھیں")}</button>
        <button className="finder-primary" type="submit" disabled={busy}>{busy?t("Deleting…","حذف ہو رہا ہے…"):t("Delete Message","پیغام حذف کریں")}</button></div></form>
    </CustomerDialog>}
  </section>;
}

