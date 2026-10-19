import Link from "next/link";
import { getLanguage } from "../../lib/i18n";

export default async function HelpPage() {
  const ur = await getLanguage() === "ur";
  return <main className="container customer-main" id="main-content">
    <p><Link href="/">SafeReturn</Link></p>
    <h1>{ur ? "مدد" : "Help"}</h1>
    <div className="qr-card">
      <h2>{ur ? "QR کوڈ کیسے کام کرتا ہے؟" : "How does a QR code work?"}</h2>
      <p>{ur ? "فائنڈر آپ کے شائع شدہ Lost یا ICE صفحے سے رابطہ کر سکتا ہے۔ نجی معلومات صرف مجاز کارروائی کے بعد ظاہر ہوتی ہیں۔" : "A finder can contact you through your published Lost or ICE page. Private information is only revealed through an authorized action."}</p>
      <h2>{ur ? "پیغام کہاں ملے گا؟" : "Where do messages appear?"}</h2>
      <p><Link className="text-link" href="/inbox">{ur ? "فائنڈر اِن باکس کھولیں" : "Open your finder inbox"}</Link></p>
      <h2>{ur ? "رازداری اور پیغام حذف کرنا" : "Privacy and message deletion"}</h2>
      <p>{ur ? "مقام دینا اختیاری ہے۔ پیغام حذف کرنے سے وہ اِن باکس سے ہٹ جاتا ہے؛ قانونی یا تحفظ کی ضروریات کے تحت ریکارڈ برقرار رہ سکتا ہے۔ حذف کرنے کی مدت ابھی منظور نہیں ہوئی۔" : "Sharing location is optional. Deleting a message removes it from the inbox; records may remain for retention or legal obligations. An erasure period has not yet been approved."}</p>
      <h2>{ur ? "ہنگامی صورت حال" : "In an emergency"}</h2>
      <p>{ur ? "SafeReturn ہنگامی سروس نہیں ہے۔ فوری خطرے میں مقامی ہنگامی خدمات سے رابطہ کریں۔" : "SafeReturn is not an emergency service. Contact local emergency services if someone is in immediate danger."}</p>
      <h2>{ur ? "اکاؤنٹ کی مدد" : "Account help"}</h2>
      <p><Link className="text-link" href="/account">{ur ? "اکاؤنٹ کی ترتیبات دیکھیں" : "Open account settings"}</Link></p>
    </div>
  </main>;
}
