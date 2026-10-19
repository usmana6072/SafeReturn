import { requestAccountDeletion } from "../../inbox-actions";
import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { Unavailable } from "../../../components/customer";
import Link from "next/link";
import { getLanguage } from "../../../lib/i18n";

type Consent = {id:string;purpose:string;version:string|null;timestamp:string;active:boolean};

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ deletion?: string }> }) {
  const ur = await getLanguage() === "ur";
  const session=await ownerSession();
  const result=(await searchParams).deletion;
  let consents: Consent[] | null=null;
  try { consents=(await ownerApi(session.token)<{items:Consent[]}>('/me/privacy-consents')).items; } catch { /* Render a safe retry state. */ }
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
      <p>{ur ? "تازہ ترین ۱۰۰ ریکارڈ؛ حالت درج کیے جانے کے وقت کی ہے۔" : "Latest 100 records; states reflect when each event was recorded."}</p>
      {consents===null ? <Unavailable ur={ur} /> : consents.length===0 ? <p>{ur ? "کوئی ریکارڈ نہیں۔" : "No consent changes recorded."}</p> : <ul>{consents.map(c=><li key={c.id}><bdi>{c.purpose.includes("whatsapp") ? (ur ? "واٹس ایپ کی رضامندی" : "WhatsApp disclosure") : c.purpose.includes("ice_contact") ? (ur ? "ہنگامی رابطے کی اشاعت" : "Emergency contact publication") : (ur ? "ہنگامی پروفائل کی اشاعت" : "Emergency profile publication")} · {c.version ?? "—"} · {c.timestamp}</bdi> {c.active ? (ur ? "فعال" : "Enabled") : (ur ? "غیر فعال" : "Disabled")}</li>)}</ul>}
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
