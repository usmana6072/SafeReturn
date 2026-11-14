"use client";
import { useRef, useState } from "react";

export type CancellationSummary = { request_id: string; request_status: string; request_revision: number };
const labels: Record<string, [string, string]> = { requested: ["Requested", "درخواست موصول"], investigating: ["Under review", "جائزہ جاری"], approved: ["Approved for controlled execution", "اجرا کے لیے منظور"], rejected: ["Declined", "درخواست مسترد"], escalated: ["Specialist review required", "خصوصی جائزہ درکار"], completed: ["Cancellation completed", "منسوخی مکمل"] };
export function CancellationRequest({ orderId, revision, summary, ur }: { orderId: string; revision?: number; summary?: CancellationSummary | null; ur: boolean }) {
  const [reason, setReason] = useState("no_longer_needed"), [confirmed, setConfirmed] = useState(false), [busy, setBusy] = useState(false), [notice, setNotice] = useState("");
  const [current, setCurrent] = useState<Pick<CancellationSummary, "request_status"> | null>(summary ?? null);
  const retry = useRef<{ signature: string; key: string } | null>(null);
  const active = current && !["rejected", "completed"].includes(current.request_status);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (!revision || !confirmed) return;
    const body = { expected_revision: revision, reason_code: reason, confirmed: true }, signature = JSON.stringify(body);
    if (retry.current?.signature !== signature) retry.current = { signature, key: crypto.randomUUID() };
    setBusy(true); setNotice("");
    try {
      const r = await fetch("/orders/cancellation-api", { method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ order_id: orderId, body, key: retry.current.key }) });
      if (!r.ok) throw Error();
      const result = await r.json();
      setCurrent({ request_status: result.request_status });
      setConfirmed(false);
      setNotice(ur ? "درخواست جائزے کے لیے محفوظ ہو گئی۔" : "Request saved for review.");
    } catch { setNotice(ur ? "درخواست کی تصدیق نہیں ہو سکی۔ حالت دوبارہ لوڈ کریں یا وہی درخواست دوبارہ بھیجیں۔" : "Request not confirmed. Reload the status or retry the same request."); }
    finally { setBusy(false); }
  }
  return <section className="qr-card" aria-busy={busy} aria-label={ur ? "منسوخی کا جائزہ" : "Cancellation review"}><h2>{ur ? "منسوخی کی درخواست" : "Request cancellation"}</h2><p>{ur ? "درخواست کے بعد بھی آرڈر جائزے تک برقرار رہتا ہے۔ رقم واپسی یا فوری منسوخی کی ضمانت نہیں۔" : "Your order remains subject to review. This request does not promise a refund or immediate cancellation."}</p>{current && <p>{ur ? "درخواست کی حالت" : "Request status"}: {labels[current.request_status]?.[ur ? 1 : 0] ?? (ur ? "حالت دوبارہ لوڈ کریں" : "Reload status")}</p>}<p role="status">{notice}</p>{!revision ? <p>{ur ? "منسوخی کا جائزہ فی الحال دستیاب نہیں۔" : "Cancellation review is currently unavailable."}</p> : !active && current?.request_status !== "completed" && <form className="account-form" onSubmit={submit}><label>{ur ? "وجہ" : "Reason"}<select value={reason} disabled={busy} onChange={e => { setReason(e.target.value); setConfirmed(false); }}><option value="no_longer_needed">{ur ? "اب ضرورت نہیں" : "No longer needed"}</option><option value="ordered_by_mistake">{ur ? "غلطی سے آرڈر ہوا" : "Ordered by mistake"}</option><option value="other">{ur ? "دیگر" : "Other"}</option></select></label><label className="check-field"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)}/>{ur ? "میں جائزے کے لیے منسوخی کی درخواست کی تصدیق کرتا ہوں۔" : "I confirm this cancellation request for review."}</label><button className="button" disabled={busy || !confirmed}>{ur ? "درخواست بھیجیں" : "Request review"}</button></form>}<button className="button secondary" disabled={busy} onClick={() => location.reload()}>{ur ? "حالت دوبارہ لوڈ کریں" : "Reload status"}</button></section>;
}
