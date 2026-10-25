import { requestAccountDeletion } from "../../inbox-actions";
import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { Unavailable } from "../../../components/customer";
import Link from "next/link";
import { getLanguage } from "../../../lib/i18n";

type Consent = {id:string;purpose:string;version:string|null;timestamp:string;active:boolean;state_scope:"recorded_event"};
type History = {items:Consent[];has_more:boolean};

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ deletion?: string }> }) {
  const ur = await getLanguage() === "ur";
  const session=await ownerSession();
  const result=(await searchParams).deletion;
  let history: History | null=null;
  try { history=await ownerApi(session.token)<History>('/me/privacy-consents'); } catch { /* Render a safe retry state. */ }
  return <>
    <h1>{ur ? "ترتیبات" : "Settings"}</h1>
    <div className="qr-card">
      <h2>{ur ? "اکاؤنٹ" : "Account"}</h2>
      <p><Link className="text-link" href="/account">{ur ? "نام اور زبان تبدیل کریں" : "Change your name and language"}</Link></p>
      <h2>{ur ? "رازداری" : "Privacy"}</h2>
      <p>{ur ? "Finder messages صرف آپ کے اکاؤنٹ میں دکھائے جاتے ہیں۔ مقام صرف رضامندی کے ساتھ محفوظ کیا جاتا ہے۔" : "Finder messages are shown only in your account. Location is stored only with finder consent."}</p>
      <h2>{ur ? "QR رازداری اور رابطے" : "QR privacy and contacts"}</h2>
      <p><Link className="text-link" href="/my-qr">{ur ? "ہر QR کی اشاعت اور رابطے الگ تبدیل کریں" : "Manage publication and contacts separately for each QR"}</Link></p>
      <h2>{ur ? "آرڈرز" : "Orders"}</h2>
      <p><Link className="text-link" href="/orders">{ur ? "آرڈر اور ترسیل کی تفصیلات" : "View order and delivery details"}</Link></p>
      <h2>{ur ? "مدد" : "Support"}</h2>
      <p><Link className="text-link" href="/help">{ur ? "مدد دیکھیں" : "Read help"}</Link></p>
      <h2>{ur ? "رضامندی کی تاریخ" : "Consent history"}</h2>
      <p>{ur ? "تازہ ترین ۱۰۰ تاریخی واقعات؛ یہ موجودہ اجازت یا سابقہ رابطوں کی شناخت نہیں ہیں۔" : "Latest 100 recorded events. These historical states do not describe current permission or identify former contacts."}</p>
      {history===null ? <Unavailable ur={ur} /> : history.items.length===0 ? <p>{ur ? "کوئی ریکارڈ نہیں۔" : "No consent changes recorded."}</p> : <ul>{history.items.map(c=><li key={c.id}><bdi>{c.purpose.includes("whatsapp") ? (ur ? "واٹس ایپ کی رضامندی" : "WhatsApp disclosure") : c.purpose.includes("ice_contact") ? (ur ? "ہنگامی رابطے کی اشاعت" : "Emergency contact publication") : (ur ? "ہنگامی پروفائل کی اشاعت" : "Emergency profile publication")} · {c.version ?? "—"} · {c.timestamp}</bdi> {c.active ? (ur ? "اس وقت فعال درج تھا" : "Recorded as enabled then") : (ur ? "اس وقت غیر فعال درج تھا" : "Recorded as disabled then")}</li>)}</ul>}
      {history?.has_more && <p role="status">{ur ? "مزید تاریخی ریکارڈ موجود ہیں۔ پرانے ریکارڈ کے جائزے کے لیے مدد سے رجوع کریں؛ مکمل تاریخ یہاں دستیاب نہیں۔" : "More recorded events exist. Older history is not available here yet; ask support for a privacy review."} <Link href="/help">{ur ? "مدد" : "Privacy help"}</Link></p>}
      <h2>{ur ? "رازداری کی درخواستوں کی حالت" : "Privacy request status"}</h2>
      <p><Link className="text-link" href="/account/privacy/exports">{ur ? "محدود برآمد کی درخواست اور حالت" : "Limited export requests and status"}</Link></p>
      <p>{ur ? "برآمد کی حالت کے لیے اپنی درخواست کی شناخت درج کریں۔ یہ مکمل قانونی ریکارڈ نہیں ہے۔" : "Use your request ID to check a limited export. This is not a complete legal account record."}</p>
      <p>{ur ? "اکاؤنٹ حذف کرنے کی حالت یہاں دستیاب نہیں۔ زیرِ جائزہ، قانونی پابندی یا بند معاملے کے بارے میں معاونت سے رجوع کریں۔ درخواست یا معاملہ بند ہونا حذف ہونے کا ثبوت نہیں۔" : "Account-deletion status is not available here yet. Ask support about review, retention holds or a closed case. A request or case closure is not proof of erasure."} <Link href="/help">{ur ? "رازداری کی مدد" : "Get privacy help"}</Link></p>
      <h2>{ur ? "اکاؤنٹ حذف کرنے کی درخواست" : "Request account deletion"}</h2>
      <p>{ur ? "یہ درخواست جائزے کے لیے بھیجی جائے گی۔ آرڈرز، QR اور قانونی ریکارڈ فوراً حذف نہیں ہوں گے۔ درخواست سے پہلے دوبارہ لاگ اِن کریں۔" : "This opens a reviewed privacy request. Orders, QR identities and legal records are preserved. Sign in again before submitting."}</p>
      {result && <p role="status">{result==='requested' ? (ur ? "درخواست جائزے کے لیے محفوظ ہو گئی۔" : "Your request was saved for review.") : (ur ? "درخواست محفوظ نہیں ہوئی۔ دوبارہ لاگ اِن کریں اور تصدیق کریں۔" : "Your request could not be saved. Sign in again and confirm before retrying.")}</p>}
      <form action={requestAccountDeletion} className="account-form">
        <label>{ur ? "وجہ (اختیاری)" : "Reason (optional)"}<textarea name="reason" maxLength={1000} /></label>
        <label><input type="checkbox" name="confirm" required /> {ur ? "میں اکاؤنٹ حذف کرنے کا جائزہ چاہتا ہوں۔" : "I confirm that I want an account-deletion review."}</label>
        <button className="button secondary">{ur ? "درخواست بھیجیں" : "Submit deletion request"}</button>
      </form>
    </div>
  </>;
}
