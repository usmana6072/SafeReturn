"use client";

import { useActionState, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { saveQR, prepareActivation, activatePair, beginScan, type QRState } from "../app/qr-actions";
import type { Profile, Contact, Preferences } from "../lib/qr-contract";

const initial: QRState = { status: "idle" };
export function ScanForm({ token, ur }: { token: string; ur: boolean }) {
  const [state, action, pending] = useActionState(beginScan.bind(null, token), initial);
  return <form action={action}><Notice state={state} ur={ur} /><button className="button" disabled={pending}>{ur ? "QR فعال کریں" : "Activate QR"}</button></form>;
}
function Notice({ state, ur }: { state: QRState; ur: boolean }) {
  if (state.status === "idle") return null;
  const messages = {
    stale: ur ? "معلومات بدل گئی ہیں۔ دوبارہ لوڈ کریں؛ آپ کی تبدیلی محفوظ نہیں ہوئی۔" : "This profile changed. Your changes were not saved. Reload before trying again.",
    denied: ur ? "اجازت نہیں ملی۔ ای میل کی تصدیق کریں یا دوبارہ لاگ اِن کریں۔" : "Action denied. Check email verification, sign in again for medical publication, or restart activation if it expired.",
    invalid: ur ? "معلومات اور اشاعت کی رضامندی چیک کریں۔" : "Check the fields and required publication consent.",
    limited: ur ? "کچھ دیر بعد دوبارہ کوشش کریں۔" : "Too many attempts. Please try again later.",
    unavailable: ur ? "سروس دستیاب نہیں۔ دوبارہ کوشش کریں۔" : "Service unavailable. Please retry. Your changes have not been confirmed.",
  };
  return <p role="alert" className="form-notice">{messages[state.reason ?? "unavailable"]}</p>;
}
function Check({ name, children, checked = false }: { name: string; children: ReactNode; checked?: boolean }) {
  return <label className="check-field"><input type="checkbox" name={name} defaultChecked={checked} />{children}</label>;
}
function Field({ name, label, value, max = 1000, multiline = false, required = false, phone = false }: {
  name: string; label: string; value?: string | null; max?: number; multiline?: boolean; required?: boolean; phone?: boolean;
}) {
  return <label>{label}{multiline ? <textarea name={name} defaultValue={value ?? ""} maxLength={max} rows={3} />
    : <input name={name} defaultValue={value ?? ""} maxLength={max} required={required} type={phone ? "tel" : "text"} autoComplete="off" dir={phone ? "ltr" : undefined} />}</label>;
}
function Editor({ qrId, kind, version, ur, children }: { qrId: string; kind: "lost" | "ice" | "preferences" | "contact" | "privacy";
  version: number; ur: boolean; children: ReactNode }) {
  const [state, action, pending] = useActionState(saveQR.bind(null, qrId, kind), initial);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!dirty || pending) return;
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const navigate = (event: MouseEvent) => {
      if ((event.target as HTMLElement).closest("a[href]") && !window.confirm(ur ? "غیر محفوظ تبدیلیاں چھوڑ دیں؟" : "Leave without saving your changes?")) {
        event.preventDefault(); event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", unload); document.addEventListener("click", navigate, true);
    return () => { window.removeEventListener("beforeunload", unload); document.removeEventListener("click", navigate, true); };
  }, [dirty, pending, ur]);
  return <form className="account-form qr-editor" action={action} onChange={() => setDirty(true)}
    onReset={event => event.preventDefault()}>
    <fieldset className="qr-fieldset" disabled={pending}><input type="hidden" name="version" value={version} />{children}
    {dirty && <p className="form-help">{ur ? "تبدیلیاں ابھی محفوظ نہیں ہوئیں۔" : "You have unsaved changes."}</p>}
    <Notice state={state} ur={ur} /><button className="button" disabled={pending}>{pending ? (ur ? "انتظار کریں…" : "Saving…") : (ur ? "تبدیلیاں محفوظ کریں" : "Save changes")}</button></fieldset>
  </form>;
}
export function PrivacyDisable({ qrId, scope, version, ur }: { qrId: string; scope: "ice" | "preferences"; version: number; ur: boolean }) {
  return <Editor qrId={qrId} kind="privacy" version={version} ur={ur}><input type="hidden" name="scope" value={scope} />
    <p>{ur ? "محفوظ نجی معلومات برقرار رکھتے ہوئے اشاعت بند کریں۔" : "Turn publication off while preserving saved private data."}</p></Editor>;
}
export function ProfileEditor({ qrId, kind, profile: p, ur }: { qrId: string; kind: "lost" | "ice"; profile: Profile; ur: boolean }) {
  const [preview, setPreview] = useState({ label: (kind === "lost" ? p.item_label : p.display_name) ?? "", description: kind === "lost" ? p.description ?? "" : p.emergency_instructions ?? "" });
  return <div onChange={event => {
    const element = event.target as HTMLInputElement;
    if (["item_label", "display_name"].includes(element.name)) setPreview(old => ({ ...old, label: element.value }));
    if (["description", "emergency_instructions"].includes(element.name)) setPreview(old => ({ ...old, description: element.value }));
  }}><Editor qrId={qrId} kind={kind} version={p.version} ur={ur}>
    {kind === "lost" ? <>
      <Field name="item_label" label={ur ? "چیز کا نام" : "Item label"} value={p.item_label} max={120} />
      <Field name="description" label={ur ? "تفصیل" : "Description"} value={p.description} multiline />
      <Field name="reward_text" label={ur ? "انعام (اختیاری)" : "Reward (optional)"} value={p.reward_text} max={200} />
      <Field name="return_instructions" label={ur ? "واپسی کی ہدایات" : "Return instructions"} value={p.return_instructions} multiline />
    </> : <>
      <Field name="display_name" label={ur ? "ظاہر ہونے والا نام" : "Display name or alias"} value={p.display_name} max={120} />
      <label>{ur ? "بلڈ گروپ" : "Blood group"}<select name="blood_group" defaultValue={p.blood_group ?? ""}><option value="">{ur ? "درج نہیں" : "Not specified"}</option>{["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(g => <option key={g}>{g}</option>)}</select></label>
      <Field name="emergency_instructions" label={ur ? "ہنگامی ہدایات" : "Emergency instructions"} value={p.emergency_instructions} multiline />
      <p>{p.medical_notes_redacted ? (ur ? "طبی نوٹس محفوظ ہیں لیکن ابھی پڑھے نہیں جا سکتے۔ خالی خانہ انہیں حذف نہیں کرے گا۔" : "Saved medical notes are currently unavailable. Leaving this field blank preserves them.")
        : p.medical_notes ? (ur ? "طبی نوٹس محفوظ ہیں۔ خالی چھوڑنے سے تبدیل نہیں ہوں گے۔" : "Medical notes are saved. Leave blank to keep them unchanged.") : (ur ? "طبی نوٹس اختیاری اور ابتدا میں نجی ہیں۔" : "Medical notes are optional and private by default.")}</p>
      <Field name="medical_notes" label={ur ? "نئے طبی نوٹس (اختیاری)" : "Replace medical notes (optional)"} multiline />
      <Check name="clear_medical_notes">{ur ? "محفوظ طبی نوٹس حذف کریں" : "Clear saved medical notes"}</Check>
      <Check name="show_medical_notes" checked={p.show_medical_notes}>{ur ? "طبی نوٹس عام کریں (تازہ لاگ اِن ضروری)" : "Publish medical notes (requires a fresh sign-in within five minutes)"}</Check>
      <Check name="consent">{ur ? "میں منتخب ICE معلومات عام کرنے پر رضامند ہوں۔" : "I explicitly consent to publishing the selected ICE information (ice-public-v1)."}</Check>
    </>}
    <Check name="published" checked={p.published}>{ur ? "منتخب معلومات QR اسکین کرنے والوں کے لیے شائع کریں" : "Publish selected information for QR scanners"}</Check>
    <p className="form-help">{ur ? "اشاعت بند کرنے سے نجی مسودہ محفوظ رہتا ہے۔ ذاتی پتے یا بچوں کے اسکول کی معلومات نہ لکھیں۔" : "Turning publication off keeps your private draft. Avoid home addresses and children’s school identifiers."}</p>
  </Editor><aside className="qr-card" aria-label={ur ? "مسودے کا پیش منظر" : "Draft preview"}><h3>{ur ? "مسودے کا پیش منظر" : "Draft preview"}</h3><strong>{preview.label}</strong><p className="plain-text">{preview.description}</p>
    <p className="form-help">{ur ? "یہ صرف مسودے کا خلاصہ ہے؛ مکمل نمبرز یہاں ظاہر نہیں ہوتے۔" : "Draft summary only; full contact numbers are never shown here."}</p></aside></div>;
}
export function ContactEditor({ qrId, version, contact: c, ur }: { qrId: string; version: number; contact?: Contact; ur: boolean }) {
  return <Editor qrId={qrId} kind="contact" version={version} ur={ur}>
    <h3>{c ? (ur ? "رابطے میں ترمیم" : "Edit contact") : (ur ? "نیا رابطہ" : "Add emergency contact")}</h3>
    {c && <><input type="hidden" name="contact_id" value={c.contact_id} /><p><bdi>{c.phone_masked ?? (ur ? "نمبر دستیاب نہیں" : "Number unavailable")}</bdi></p></>}
    <Field name="relationship_label" label={ur ? "رشتہ" : "Relationship"} value={c?.relationship_label} max={60} required />
    <Field name="display_name" label={ur ? "نام (اختیاری)" : "Name (optional)"} value={c?.display_name} max={120} />
    <Field name="phone" label={ur ? "بین الاقوامی نمبر (+92…)؛ خالی چھوڑنے سے محفوظ نمبر برقرار رہے گا" : "International phone (+92…); leave blank to keep an existing number"} max={16} phone />
    <label>{ur ? "ترتیب" : "Display order"}<input type="number" min={0} max={100} name="display_order" defaultValue={c?.display_order ?? 0} /></label>
    <Check name="published" checked={c?.published}>{ur ? "یہ رابطہ شائع کریں" : "Publish this contact"}</Check>
    <Check name="consent">{ur ? "مجھے اس نمبر کو محفوظ کرنے اور ظاہر کرنے کی اجازت ہے۔" : "I have permission to store this number and consent to its protected public reveal (ice-contact-v1)."}</Check>
    {c && <><Check name="remove">{ur ? "رابطہ ہٹائیں" : "Remove this contact"}</Check><Check name="confirm_remove">{ur ? "میں رابطہ ہٹانے کی تصدیق کرتا ہوں" : "I confirm removal of this contact"}</Check></>}
  </Editor>;
}
export function PreferenceEditor({ qrId, preferences: p, ur }: { qrId: string; preferences: Preferences; ur: boolean }) {
  return <Editor qrId={qrId} kind="preferences" version={p.version} ur={ur}><h2>{ur ? "واٹس ایپ کی ترجیح" : "WhatsApp preference"}</h2>
    <p>{ur ? "آن کرنے سے آپ کا نمبر QR اسکین کرنے والوں کو مل سکتا ہے۔ واٹس ایپ کی گفتگو SafeReturn میں محفوظ نہیں ہوتی۔" : "Enabling this allows QR scanners to obtain your selected number. WhatsApp conversations are external and are not saved by SafeReturn."}</p>
    <p><bdi>{p.whatsapp_phone_masked}</bdi></p>
    <Field name="whatsapp_phone" label={ur ? "نیا بین الاقوامی نمبر؛ خالی چھوڑنے سے موجودہ نمبر برقرار رہے گا" : "New international number; leave blank to keep the existing number"} max={16} phone />
    <Check name="whatsapp_enabled" checked={p.whatsapp_enabled}>{ur ? "واٹس ایپ فعال کریں" : "Enable WhatsApp preference"}</Check>
    <Check name="consent">{ur ? "میں منتخب نمبر عام کرنے پر رضامند ہوں۔" : "I consent to public disclosure of the selected number (wa-public-v1)."}</Check>
  </Editor>;
}
export function ActivationForm({ confirm, ur }: { confirm: boolean; ur: boolean }) {
  const [state, action, pending] = useActionState(confirm ? activatePair : prepareActivation, initial);
  return <form action={action} className="account-form">{confirm ? <>
    <p>{ur ? "اس کٹ کے دونوں Lost اور ICE QR آپ کے اکاؤنٹ کے ساتھ فعال ہوں گے۔ پروفائل ابتدا میں نجی رہیں گے۔" : "Both Lost and ICE QR tags in this kit will activate together for your account. Profile publication settings remain unchanged."}</p>
    <Check name="confirm">{ur ? "میں پوری کٹ فعال کرنے کی تصدیق کرتا ہوں" : "I confirm activation of the complete pair"}</Check>
  </> : <><p>{ur ? "خریداری کی اجازت چیک کریں، یا کٹ کے اندر موجود خفیہ کوڈ درج کریں۔" : "Check your purchase entitlement, or enter the concealed activation code supplied inside your kit."}</p>
    <label>{ur ? "خفیہ ایکٹیویشن کوڈ (اگر ضروری ہو)" : "Concealed activation code (if needed)"}<input type="password" name="activation_secret" autoComplete="off" maxLength={256} /></label></>}
    <Notice state={state} ur={ur} /><button className="button" disabled={pending}>{pending ? (ur ? "انتظار کریں…" : "Please wait…") : confirm ? (ur ? "دونوں QR فعال کریں" : "Activate both QR tags") : (ur ? "اجازت چیک کریں" : "Check eligibility")}</button>
  </form>;
}
