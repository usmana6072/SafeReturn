import Link from "next/link";
import { Suspense } from "react";
import { FinderActions,FinderRetry } from "./finder-inbox";
import { CustomerIcon } from "./customer-icon";
import { type FinderMessage,type FinderSummary,type InboxContext,inboxHref,qrMessageName,finderDate,finderLabel,finderEmailHref,finderPhoneHref,finderMapHref } from "../lib/finder-inbox";
type Summary=Promise<FinderSummary|null>;
async function FinderQrName({summary,message,ur}:{summary:Summary;message:FinderMessage;ur:boolean}){
 const value=await summary;
 return <bdi>{qrMessageName(value??message,ur)}</bdi>;
}
async function RelatedQr({summary,message,ur}:{summary:Summary;message:FinderMessage;ur:boolean}){
 const value=await summary,t=(en:string,u:string)=>ur?u:en;
 return <section className="finder-panel finder-related"><h2>{t("Related QR Code","متعلقہ QR کوڈ")}</h2>
 <div className="finder-related-name"><CustomerIcon name={message.tag_type==="ice"?"medical":"qr"}/><bdi>{qrMessageName(value??message,ur)}</bdi></div>
 {value?<Link className="finder-secondary" href={"/my-qr/"+value.qr_id}>{t("View QR Details","QR کی تفصیلات دیکھیں")}</Link>:<><p className="finder-note">{t("QR details are unavailable for this message.","اس پیغام کے لیے QR کی تفصیلات دستیاب نہیں ہیں۔")}</p><FinderRetry ur={ur}/></>}
 </section>;
}
export function FinderMessageDetails({message,summary,context,action,ur,result}:{message:FinderMessage;summary:Summary;context:InboxContext;action:(form:FormData)=>Promise<void>;ur:boolean;result?:string}){
 const t=(en:string,u:string)=>ur?u:en,email=finderEmailHref(message.finder_email),phone=finderPhoneHref(message.finder_phone),map=finderMapHref(message.location);
 return <section className="finder-screen"><Link className="finder-back" href={inboxHref(context)}><CustomerIcon name="arrow"/>{t("Back to Messages","پیغامات پر واپس")}</Link>
 <header className="finder-intro"><div><h1>{t("Message Details","پیغام کی تفصیلات")}</h1><p className="finder-detail-qr"><CustomerIcon name={message.tag_type==="ice"?"medical":"tag"}/><Suspense fallback={<bdi>{qrMessageName(message,ur)}</bdi>}><FinderQrName summary={summary} message={message} ur={ur}/></Suspense></p></div></header>
 {result&&<p className="finder-feedback" role="status">{result==="saved"?t("Changes saved.","تبدیلیاں محفوظ ہو گئیں۔"):t("Changes could not be saved. Please try again.","تبدیلیاں محفوظ نہیں ہو سکیں۔ دوبارہ کوشش کریں۔")}</p>}
 <div className="finder-detail-grid"><div className="finder-detail-main"><article className="finder-panel">
 <div className="finder-message-top"><span className="finder-avatar"><CustomerIcon name="inbox"/></span><div><h2><bdi>{message.finder_name||t("Anonymous Finder","نامعلوم فائنڈر")}</bdi></h2><time dateTime={message.submitted_at}>{finderDate(message.submitted_at,ur)}</time></div><span className={"finder-status "+(message.status==="new"?"unread":"")}>{finderLabel(message.status,ur)}</span></div>
 <div className="finder-message-body" dir="auto">{message.message}</div>
 <p className="finder-note">{t("This is a one-way message. Use the contact details below if the finder shared them.","یہ یک طرفہ پیغام ہے۔ جواب دینے کے لیے بھیجنے والے کی فراہم کردہ رابطے کی معلومات استعمال کریں۔")}</p>
 </article><section className="finder-panel"><h2>{t("Finder Contact","بھیجنے والے سے رابطہ")}</h2>
 {!message.finder_email&&!message.finder_phone?<p className="finder-note">{t("The finder did not share contact details.","بھیجنے والے نے رابطے کی معلومات فراہم نہیں کیں۔")}</p>:<div className="finder-contacts">
 {message.finder_email&&<div><span>{t("Email","ای میل")}</span><bdi>{message.finder_email}</bdi>{email&&<a className="finder-secondary" href={email}>{t("Email Finder","ای میل کریں")}</a>}</div>}
 {message.finder_phone&&<div><span>{t("Phone","فون")}</span><bdi>{message.finder_phone}</bdi>{phone&&<a className="finder-secondary" href={phone}>{t("Call Finder","کال کریں")}</a>}</div>}</div>}
 {message.preferred_contact&&<p className="finder-note">{t("Preferred contact: ","رابطے کی ترجیح: ")}{message.preferred_contact==="email"?t("Email","ای میل"):t("Phone","فون")}</p>}
 {map&&<a className="finder-secondary" href={map} target="_blank" rel="noopener noreferrer"><CustomerIcon name="pin"/>{t("View Shared Location","فراہم کردہ مقام دیکھیں")}</a>}
 </section></div><aside><Suspense fallback={<section className="finder-panel finder-related" aria-busy="true"><h2>{t("Related QR Code","متعلقہ QR کوڈ")}</h2><p className="finder-note" role="status">{t("Loading QR details…","QR کی تفصیلات لوڈ ہو رہی ہیں…")}</p></section>}><RelatedQr summary={summary} message={message} ur={ur}/></Suspense>
 <FinderActions key={message.status} action={action} context={context} status={message.status} ur={ur}/></aside></div>
 </section>;
}

