import Link from "next/link";
import {requestAccountDeletion} from "../../inbox-actions";
import {ownerApi,ownerSession} from "../../../lib/qr-server";
import {getLanguage} from "../../../lib/i18n";
import {accountCopy} from "../../../lib/account-copy";
import {SettingsRow,AccountRetry} from "../../../components/account-settings";
import {CustomerSubmit} from "../../../components/customer-submit";
import {CustomerIcon} from "../../../components/customer-icon";
import "../../../components/account-settings.css";
type Consent={id:string;purpose:string;version:string|null;timestamp:string;active:boolean;state_scope:"recorded_event"};
export const metadata={title:"Privacy & Data | SafeReturn",robots:{index:false,follow:false}};
export default async function PrivacyPage({searchParams}:{searchParams:Promise<{deletion?:string}>}){
 const ur=await getLanguage()==="ur",c=accountCopy(ur),session=await ownerSession(),result=(await searchParams).deletion;
 let history:{items:Consent[];has_more:boolean}|null=null;
 try{
  const value=await ownerApi(session.token)<{items:Consent[];has_more:boolean}>("/me/privacy-consents");
  if(!Array.isArray(value.items)||value.items.length>100||typeof value.has_more!=="boolean"||value.items.some(item=>!item||typeof item.id!=="string"||typeof item.purpose!=="string"||typeof item.active!=="boolean"||!Number.isFinite(Date.parse(item.timestamp))||item.state_scope!=="recorded_event"||!(item.version===null||typeof item.version==="string")))throw Error("Unavailable");
  history=value;
 }catch{}
 return <section className="settings-screen settings-privacy"><Link className="settings-back" href="/account">{c.back}</Link><header className="settings-intro"><h1>{c.requests}</h1><p>{c.privacySubtitle}</p></header>
 {result&&<p className={"settings-feedback "+(result==="requested"?"":"error")} role="status">{result==="requested"?c.deletionSent:c.deletionFailed}</p>}
 <div className="settings-grid"><section className="settings-group"><h2>{c.privacy}</h2><div className="settings-card"><SettingsRow icon="box" title={c.download} description={c.downloadHelp} href="/account/privacy/exports"/><SettingsRow icon="qr" title={c.qrPrivacy} description={c.qrPrivacyText} href="/my-qr"/><SettingsRow icon="help" title={c.help} description={c.helpText} href="/help"/></div></section>
 <section className="settings-panel"><h2>{c.statusHeading}</h2><p className="settings-note">{c.noRequestHistory}</p><Link className="settings-secondary" href="/help">{c.help}</Link></section></div>
 <section className="settings-panel settings-history" id="privacy-history"><h2>{c.recorded}</h2><p className="settings-note">{c.recordedText}</p>
 {history===null?<div className="settings-empty" role="alert"><p>{c.consentFailed}</p><AccountRetry ur={ur}/></div>:history.items.length===0?<div className="settings-empty"><span className="settings-feature-icon"><CustomerIcon name="pending"/></span><h3>{c.noChoices}</h3><p>{c.noChoicesText}</p></div>:<details className="settings-disclosure" open={history.items.length<=3}><summary>{c.history} <span>({history.items.length}{history.has_more?"+":""})</span></summary><ul className="settings-events">{history.items.map(item=><li key={item.id}><div><strong>{item.purpose.includes("whatsapp")?c.whatsapp:item.purpose.includes("ice_contact")?c.iceContact:c.iceProfile}</strong><time dateTime={item.timestamp}>{new Intl.DateTimeFormat(ur?"ur-PK":"en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Karachi"}).format(new Date(item.timestamp))}</time></div><span className="settings-event-state">{item.active?c.enabled:c.disabled}</span>{item.version&&<small><bdi>{item.version}</bdi></small>}</li>)}</ul></details>}
 {history?.has_more&&<p className="settings-note">{c.recordedMore} <Link href="/help">{c.help}</Link></p>}</section>
 <section className="settings-panel settings-deletion"><details className="settings-disclosure"><summary>{c.deletion}</summary><p className="settings-note">{c.deletionText}</p>
 <form className="settings-form settings-request-form" action={requestAccountDeletion}><label htmlFor="privacy-deletion-reason">{c.reason}</label><textarea id="privacy-deletion-reason" name="reason" maxLength={1000} rows={3}/><label className="settings-check"><input type="checkbox" name="confirm" required/><span>{c.deletionConfirm}</span></label><CustomerSubmit ur={ur} secondary>{c.submitRequest}</CustomerSubmit></form></details></section>
 </section>;
}
