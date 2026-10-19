import { createHash } from "node:crypto";
import Link from "next/link";
import { ownerApi } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { changeScanLanguage } from "./scan-language";
import { ScanForm } from "../../../components/qr-forms";
import {
  ContactReveal,
  WhatsAppAction,
} from "../../../components/public-actions";
import { FinderMessageForm } from "../../../components/finder-message";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "SafeReturn QR scan",
  robots: { index: false, follow: false },
  referrer: "no-referrer" as const,
};

type PublicQR = {
  tag_type: "lost" | "ice";
  status:
    "unactivated" | "active" | "owner_disabled" | "admin_suspended" | "revoked";
  locale_options: ("en" | "ur")[];
  lost_item?: {
    label: string | null;
    description: string | null;
    reward_text: string | null;
  };
  features?: {
    finder_form_enabled: boolean;
    whatsapp_contact_enabled: boolean;
    location_sharing_available: boolean;
  };
  whatsapp_contact?: { action_available: boolean; disclosure_notice: string };
  ice?: {
    display_name: string | null;
    blood_group: string | null;
    medical_notes: null;
    contacts: {
      contact_id: string;
      relationship_label: string;
      display_name: string | null;
      reveal_available: boolean;
    }[];
    owner_information_disclaimer: string;
  };
};

const statusCopy = {
  en: {
    unavailable: "We could not verify this QR code.",
    unactivated: "This tag is not active yet.",
    owner_disabled: "This tag is currently unavailable.",
    admin_suspended: "This tag is temporarily unavailable.",
    revoked: "This QR code is no longer valid.",
    lost: "Found this item?",
    ice: "Emergency information",
    lostEmpty: "The owner has not published item details yet.",
    iceEmpty: "The owner has not published emergency details yet.",
    noPhone: "Contact numbers are not shown on the initial scan.",
    activate: "Activate QR",
    language: "اردو",
    home: "Back to website",
  },
  ur: {
    unavailable: "ہم اس کیو آر کوڈ کی تصدیق نہیں کر سکے۔",
    unactivated: "یہ ٹیگ ابھی فعال نہیں ہے۔",
    owner_disabled: "یہ ٹیگ فی الحال دستیاب نہیں ہے۔",
    admin_suspended: "یہ ٹیگ عارضی طور پر دستیاب نہیں ہے۔",
    revoked: "یہ کیو آر کوڈ اب درست نہیں ہے۔",
    lost: "کیا آپ کو یہ چیز ملی ہے؟",
    ice: "ہنگامی معلومات",
    lostEmpty: "مالک نے ابھی سامان کی معلومات شائع نہیں کیں۔",
    iceEmpty: "مالک نے ابھی ہنگامی معلومات شائع نہیں کیں۔",
    noPhone: "ابتدائی اسکین میں رابطہ نمبر ظاہر نہیں کیے جاتے۔",
    activate: "کیو آر فعال کریں",
    language: "English",
    home: "ویب سائٹ پر واپس",
  },
} as const;

export default async function Page({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params,
    ur = (await getLanguage()) === "ur";
  const language = ur ? "ur" : "en";
  const t = statusCopy[language];
  const siteKey = process.env.NEXT_PUBLIC_SAFERETURN_TURNSTILE_SITE_KEY ?? "";
  const binding = (action: string, contact = "") => createHash("sha256").update(`${action}:${token}:${contact}`).digest("hex");
  let profile: PublicQR | null = null;
  if (/^[A-Za-z0-9_-]{20,80}$/.test(token)) {
    try {
      profile = await ownerApi()<PublicQR>(`/public/qr/${token}`);
    } catch {
      /* Render the non-disclosing unavailable state. */
    }
  }
  return (
    <main id="main-content" tabIndex={-1} className="container public-scan">
      <div className="public-qr-header">
        <Link className="text-link" href="/">
          {t.home}
        </Link>
        <form action={changeScanLanguage}>
          <input type="hidden" name="token" value={token} />
          <input type="hidden" name="language" value={ur ? "en" : "ur"} />
          <button className="language-button" lang={ur ? "en" : "ur"}>
            {t.language}
          </button>
        </form>
      </div>
      {!profile ? (
        <>
          <h1>{t.unavailable}</h1>
          <p>
            {ur
              ? "براہ کرم کوڈ دوبارہ اسکین کریں یا بعد میں کوشش کریں۔"
              : "Please scan the code again or try again later."}
          </p>
        </>
      ) : profile.status !== "active" ? (
        <>
          <h1>{t[profile.status]}</h1>
          <p>
            {ur
              ? "اس صفحے پر مالک یا آرڈر کی نجی معلومات موجود نہیں ہیں۔"
              : "No owner or order information is shown on this page."}
          </p>
          {profile.status === "unactivated" && (
            <ScanForm token={token} ur={ur} />
          )}
        </>
      ) : profile.tag_type === "lost" ? (
        <>
          <h1>{t.lost}</h1>
          {profile.lost_item?.label ||
          profile.lost_item?.description ||
          profile.lost_item?.reward_text ? (
            <section className="public-qr-card" aria-labelledby="qr-item">
              <h2 id="qr-item">
                {profile.lost_item.label ?? (ur ? "گم شدہ سامان" : "Lost item")}
              </h2>
              {profile.lost_item.description && (
                <p className="plain-text">{profile.lost_item.description}</p>
              )}
              {profile.lost_item.reward_text && (
                <p>
                  <strong>{ur ? "انعام:" : "Reward:"}</strong>{" "}
                  {profile.lost_item.reward_text}
                </p>
              )}
            </section>
          ) : (
            <p>{t.lostEmpty}</p>
          )}
          {profile.features?.finder_form_enabled && (
            <FinderMessageForm token={token} ur={ur} siteKey={siteKey} binding={binding("finder_message")} />
          )}
          {profile.features?.whatsapp_contact_enabled && (
            <WhatsAppAction token={token} ur={ur} siteKey={siteKey} binding={binding("whatsapp")} />
          )}
        </>
      ) : (
        <>
          <h1>{t.ice}</h1>
          {profile.ice && (profile.ice.display_name || profile.ice.blood_group || profile.ice.contacts.length > 0) ? (
            <section className="public-qr-card" aria-labelledby="qr-ice">
              <h2 id="qr-ice">
                {profile.ice.display_name ??
                  (ur ? "ہنگامی پروفائل" : "Emergency profile")}
              </h2>
              {profile.ice.blood_group && (
                <p>
                  <strong>{ur ? "بلڈ گروپ:" : "Blood group:"}</strong>{" "}
                  <bdi>{profile.ice.blood_group}</bdi>
                </p>
              )}
              {profile.ice.contacts.length > 0 && (
                <div>
                  <h3>{ur ? "رابطے" : "Contacts"}</h3>
                  <ul>
                    {profile.ice.contacts.map((contact) => (
                      <li key={contact.contact_id}>
                        {contact.relationship_label}
                        {contact.display_name
                          ? ` — ${contact.display_name}`
                          : ""}{" "}
                        {contact.reveal_available && (
                          <ContactReveal
                            token={token}
                            contactId={contact.contact_id}
                            siteKey={siteKey}
                            binding={binding("ice_reveal", contact.contact_id)}
                            ur={ur}
                          />
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p>{ur ? "یہ معلومات مالک کی فراہم کردہ ہیں؛ ان کی طبی تصدیق نہیں کی گئی۔" : profile.ice.owner_information_disclaimer}</p>
            </section>
          ) : (
            <p>{t.iceEmpty}</p>
          )}
          <p>{t.noPhone}</p>
        </>
      )}
          <aside className="public-critical" aria-label="English / اردو">
        <p lang="en" dir="ltr">{profile?.tag_type === "ice"
          ? "Emergency information is provided by the owner and is not medically verified. Contact numbers require a deliberate reveal."
          : "Found this item? Share only the information you choose. A scan does not give ownership of this tag."}</p>
        <p lang="ur" dir="rtl">{profile?.tag_type === "ice"
          ? "ہنگامی معلومات مالک نے فراہم کی ہیں اور ان کی طبی تصدیق نہیں کی گئی۔ رابطہ نمبر دیکھنے کے لیے خود بٹن دبائیں۔"
          : "کیا آپ کو یہ چیز ملی ہے؟ صرف اپنی منتخب کردہ معلومات شیئر کریں۔ اسکین کرنے سے اس ٹیگ کی ملکیت نہیں ملتی۔"}</p>
      </aside>
    </main>
  );
}
