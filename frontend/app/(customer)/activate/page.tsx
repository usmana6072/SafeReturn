import Link from "next/link";
import { cookies } from "next/headers";
import { ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { ActivationTicket, ScanTicket, readTicket } from "../../../lib/scan-ticket";
import { ActivationForm } from "../../../components/qr-forms";
import { restartActivation } from "../../qr-actions";
export default async function Page() {
  const ur = await getLanguage() === "ur", session = await ownerSession(), jar = await cookies();
  const pending = readTicket<ActivationTicket>(jar.get("sr-activation")?.value, "activation");
  const scan = readTicket<ScanTicket>(jar.get("sr-scan")?.value, "scan");
  return <><h1>{ur ? "اپنی QR کٹ فعال کریں" : "Activate your QR kit"}</h1>
    <p><Link href="/independent-qr">{ur?"نئے الگ QR کو ترسیل کے بعد اپنے اکاؤنٹ سے فعال کریں۔":"New independent QRs: activate from your purchaser account after delivery."}</Link></p>
    {!scan && !(pending && pending.actor === session.user.id) ? <p>{ur ? "اپنی کٹ کا QR اسکین کریں۔ پچھلا سیشن ختم ہو چکا ہو تو دوبارہ اسکین کریں۔" : "Scan a QR on your kit to start. If your previous scan expired, scan it again."}</p>
      : !session.user.email_confirmed_at ? <p><Link href="/auth/verify-email">{ur ? "پہلے ای میل کی تصدیق کریں، پھر یہاں واپس آئیں۔" : "Confirm your email first, then return here."}</Link></p>
        : <><ActivationForm confirm={!!pending && pending.actor === session.user.id} ur={ur} />
          {pending && <form action={restartActivation}><button className="button secondary">{ur ? "اجازت دوبارہ چیک کریں" : "Check eligibility again"}</button></form>}</>}</>;
}
