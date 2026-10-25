"use client";
import { useRef, useState } from "react";
import Link from "next/link";

type Category = { disposition: string; reason_code: string; source_count: number | null; schema_version: number; source_watermark: string };
type ExportStatus = { request_id: string; case_id: string; status: string; revision: number; scope_version?: string; categories?: Record<string, Category>; expires_at?: string };

export function PrivacyExports({ admin = false, ur = false }: { admin?: boolean; ur?: boolean }) {
  const endpoint = admin ? "/admin/privacy/exports/api" : "/account/privacy/exports/api";
  const [items, setItems] = useState<ExportStatus[]>([]);
  const [id, setId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const [choice, setChoice] = useState("approve");
  const [reason, setReason] = useState("scope_reviewed");
  const pending = useRef<{ signature: string; key: string } | null>(null);
  async function load(next = false, target = id) {
    const response = await fetch(endpoint + (admin ? "?limit=20" + (next && cursor ? "&cursor=" + encodeURIComponent(cursor) : "") : "?id=" + encodeURIComponent(target)), { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    setItems(admin ? data.items : [data]); setCursor(data.next_cursor ?? null);
  }
  async function perform(action: string, row?: ExportStatus) {
    setBusy(true); setNotice("");
    try {
      if (action === "load") { await load(); return; }
      if (action === "next") { await load(true); return; }
      const body = action === "request" ? { scope: "basic_v1", confirmed } : action === "decisions" ? { case_id: row!.case_id, expected_revision: row!.revision, decision: choice, scope_version: "basic_v1", reason_code: reason, confirmed } : { expected_revision: row!.revision, confirmed };
      const input = { action: action === "download" ? "download-grants" : action, id: row?.request_id, body };
      const signature = JSON.stringify(input);
      if (pending.current?.signature !== signature) pending.current = { signature, key: crypto.randomUUID() };
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...input, key: pending.current!.key }) });
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      pending.current = null;
      if (action === "download") {
        // Capability lives only in this function, never URL, cookie or web storage.
        const downloaded = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json", "X-Privacy-Grant": data.grant }, body: JSON.stringify({ action: "download", id: row!.request_id }) });
        if (!downloaded.ok) throw new Error(String(downloaded.status));
        const url = URL.createObjectURL(await downloaded.blob());
        const link = document.createElement("a"); link.href = url; link.download = "safereturn-basic-v1.json"; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        setNotice(ur ? "فائل منتقل ہو گئی۔" : "Export downloaded.");
      } else if (action === "request") { setId(data.request_id); await load(false, data.request_id); setNotice(ur ? "درخواست محفوظ ہو گئی۔" : "Request saved for review."); }
      else { await load(); setNotice(ur ? "فیصلہ محفوظ ہو گیا۔" : "Decision saved."); }
    } catch (error) {
      const status = error instanceof Error ? error.message : "503";
      if (["400", "403", "404", "409", "410", "412", "422"].includes(status)) pending.current = null;
      setNotice(status === "403" ? (ur ? "تازہ تصدیق اور مجاز رسائی درکار ہے۔" : "Recent authentication and authorized access are required.") : status === "404" ? (ur ? "درخواست نہیں ملی۔" : "Request not found.") : status === "410" ? (ur ? "اجازت ختم ہو گئی۔ دوبارہ کوشش کریں۔" : "Download authorization expired or was used. Request a new download.") : status === "412" ? (ur ? "درخواست تبدیل ہو گئی۔ دوبارہ لوڈ کریں۔" : "Request changed. Reload before deciding.") : (ur ? "درخواست مکمل نہیں ہوئی۔ دوبارہ کوشش کریں۔" : "Request could not be completed. Please retry."));
      if (status === "412") { try { await load(); } catch {} }
    } finally { setConfirmed(false); setBusy(false); }
  }
  return <>
    <h1>{ur ? "محدود ڈیٹا برآمد" : "Limited data export"}</h1>
    <p>{ur ? "basic_v1 صرف منظور شدہ ذاتی معلومات شامل کرتا ہے۔ یہ مکمل قانونی اکاؤنٹ ریکارڈ نہیں ہے۔" : "basic_v1 includes reviewed, allowlisted personal records. It is not a complete legal account dump."}</p>
    <p>{ur ? "دیگر افراد، طبی و رابطہ معلومات، پتے، نجی نوٹس اور حفاظتی راز خارج ہیں۔ وسیع درخواست کے لیے معاونت سے رجوع کریں۔" : "Third-party and medical/contact content, shipping identity, private notes and security secrets are excluded. Broader requests need individual privacy review."}</p>
    {admin ? <p>{ur ? "صرف مخصوص مجاز معاملات دکھائے جاتے ہیں۔" : "Only specifically authorized cases appear. Review identity evidence through the approved custody procedure before deciding."}</p> : <><nav aria-label={ur ? "رازداری" : "Privacy"}><Link href="/account">{ur ? "میرا اکاؤنٹ" : "My account"}</Link>{" · "}<Link href="/settings">{ur ? "رازداری کی تاریخ اور درخواستیں" : "Privacy history and requests"}</Link>{" · "}<Link href="/help">{ur ? "رازداری کی مدد" : "Privacy help"}</Link></nav><p>{ur ? "منظوری کے بعد فائل 24 گھنٹے دستیاب ہے۔" : "After generation, the file is available for 24 hours. Downloads require a recent sign-in and a one-use grant valid for up to five minutes."}</p><label>{ur ? "درخواست کی شناخت" : "Request ID"}<input value={id} onChange={e => setId(e.target.value)} maxLength={36} style={{ display: "block", width: "100%", maxWidth: "40rem", padding: ".75rem", marginBlock: ".5rem 1rem", border: "1px solid #bdd6d4", borderRadius: ".5rem", background: "white" }}/></label></>}
    <button className="button secondary" disabled={busy || !admin && !id} onClick={() => perform("load")}>{ur ? "حالت لوڈ کریں" : "Load status"}</button>
    {cursor && <button disabled={busy} onClick={() => perform("next")}>{ur ? "اگلا صفحہ" : "Next page"}</button>}
    <p role="status" aria-live="polite">{notice}</p>
    <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)}/>{ur ? "میں اس محدود کارروائی کی تصدیق کرتا ہوں۔" : "I confirm this limited action."}</label>
    {!admin && <button className="button" disabled={busy || !confirmed} onClick={() => perform("request")}>{ur ? "برآمد کی درخواست" : "Request basic_v1 export"}</button>}
    {admin && <><label>{ur ? "فیصلہ" : "Decision"}<select value={choice} onChange={e => setChoice(e.target.value)}><option value="approve">Approve</option><option value="reject">Reject</option><option value="escalate">Escalate</option></select></label><label>{ur ? "وجہ" : "Reason code"}<select value={reason} onChange={e => setReason(e.target.value)}>{["scope_reviewed", "scope_not_supported", "identity_review_failed", "requires_review"].map(r => <option key={r}>{r}</option>)}</select></label></>}
    {items.map(row => <section key={row.request_id} style={{ overflowWrap: "anywhere", marginBlock: "1.5rem" }}>
      <h2>{row.request_id}</h2><p>{row.status} · {ur ? "نظر ثانی" : "Revision"} {row.revision}</p>
      {admin && <p>{ur ? "معاملہ" : "Case"}: {row.case_id}</p>}
      {row.expires_at && <p>{ur ? "اختتام" : "Expires"}: {row.expires_at}</p>}
      {row.categories && <dl>{Object.entries(row.categories).map(([name, c]) => <div key={name}><dt>{name}</dt><dd>{c.disposition}: {c.reason_code} · {c.source_count ?? "—"}</dd></div>)}</dl>}
      {admin && ["requested", "reviewing"].includes(row.status) && <button className="button" disabled={busy || !confirmed} onClick={() => perform("decisions", row)}>{ur ? "فیصلہ محفوظ کریں" : "Save review decision"}</button>}
      {!admin && row.status === "ready" && <button className="button" disabled={busy || !confirmed} onClick={() => perform("download", row)}>{ur ? "محفوظ ڈاؤن لوڈ" : "Download reviewed export"}</button>}
    </section>)}
  </>;
}
