"use client";
import { useState } from "react";
import type { StaffSecurityState } from "../lib/auth/staff-contract";

type Row = { id: string; status?: string; order_id?: string; sheet_row_key?: string; last_export_version?: number; attempt_count?: number; last_error_code?: string; last_synced_at?: string; updated_at?: string; payment_status?: string; fulfillment_status?: string; total_pkr?: string; currency_code?: string; resource_type?: string; owner_id?: string; retention_until?: string; deleted_at?: string; on_hold?: boolean; format?: string; size_bytes?: number; sha256_hex?: string; cleanup_job?: { id: string; status: string; attempt_count: number; last_error_code?: string } };
const inputStyle = { display: "block", width: "100%", padding: ".6rem", border: "1px solid #bdd6d4", borderRadius: ".4rem", marginBlock: ".3rem 1rem" };
export function FinanceStorageAdmin({ storage = false, ur, security }: { storage?: boolean; ur: boolean; security: StaffSecurityState }) {
  const endpoint = storage ? "/admin/storage/api" : "/admin/finance/sheet-sync/api";
  const [rows, setRows] = useState<Row[]>([]), [loaded, setLoaded] = useState(false), [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(""), [asOf, setAsOf] = useState(""), [cursor, setCursor] = useState<string | null>(null);
  const [order, setOrder] = useState(""), [job, setJob] = useState(""), [kind, setKind] = useState("");
  const [status, setStatus] = useState(""), [hold, setHold] = useState("");
  const [pending, setPending] = useState<{ row: Row; action: string } | null>(null), [reason, setReason] = useState(""), [confirmed, setConfirmed] = useState(false);
  const canHold = security.capabilities.includes("storage.holds");
  async function load(next = false) {
    const params = new URLSearchParams({ limit: storage ? "100" : "20" });
    if (storage) { if (order) params.set("order_id", order); if (job) params.set("job_id", job); if (kind) params.set("resource_type", kind); }
    else if (next && cursor) params.set("cursor", cursor);
    const response = await fetch(endpoint + "?" + params, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json(); setRows(data.items); setCursor(data.next_cursor); setAsOf(data.as_of); setLoaded(true);
  }
  function message(error: unknown) {
    const code = error instanceof Error ? error.message : "503";
    return code === "403" ? (ur ? "موجودہ کردار یا تصدیق اس کارروائی کی اجازت نہیں دیتے۔" : "Current role or authentication does not permit this action.") : code === "409" ? (ur ? "حالت تبدیل ہو گئی یا کارروائی روک دی گئی۔ تازہ حالت دیکھیں۔" : "State changed or action is blocked. Review the refreshed state.") : code === "404" ? (ur ? "مجاز ریکارڈ نہیں ملا۔" : "Eligible record not found.") : (ur ? "خدمت دستیاب نہیں۔ دوبارہ کوشش کریں۔" : "Service unavailable. Please retry.");
  }
  async function refresh(next = false) { setBusy(true); setNotice(""); try { await load(next); } catch (e) { setNotice(message(e)); setLoaded(false); setRows([]); } finally { setBusy(false); setPending(null); setConfirmed(false); } }
  async function execute() {
    if (!pending || !confirmed) return;
    setBusy(true); setNotice("");
    try {
      const reasoned = ["hold", "recover"].includes(pending.action);
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: pending.row.id, action: pending.action, confirmed, ...(reasoned ? { reason_code: reason } : {}) }) });
      if (!response.ok) throw new Error(String(response.status));
      setNotice(ur ? "درخواست قبول ہو گئی۔ یہ بیرونی کارروائی کی تکمیل نہیں ہے۔" : "Request accepted. This does not confirm provider execution.");
      await load();
    } catch (e) { setNotice(message(e)); try { await load(); } catch { setRows([]); setLoaded(false); } }
    finally { setBusy(false); setPending(null); setConfirmed(false); setReason(""); }
  }
  const visible = rows.filter(r => (!status || (storage ? r.cleanup_job?.status ?? "none" : r.status) === status) && (!hold || String(!!r.on_hold) === hold));
  const text = (en: string, translated: string) => ur ? translated : en;
  return <>
    <h1>{storage ? text("Storage and retention", "ذخیرہ اور برقرار رکھنا") : text("Finance mirror", "مالیاتی آئینہ")}</h1>
    <p>{storage ? text("Metadata only. Deadlines do not prove policy approval. Policy versions, approval references and prior history are unavailable in this API; review the approved custody record before acting.", "صرف معلومات۔ آخری تاریخ پالیسی کی منظوری کا ثبوت نہیں۔ کارروائی سے پہلے منظور شدہ ریکارڈ کا جائزہ لیں۔") : text("Sheets is a masked reporting mirror. Database payment and fulfillment records remain authoritative; retrying never verifies a payment.", "شیٹس صرف محدود رپورٹ ہے۔ ادائیگی اور ترسیل کے لیے ڈیٹابیس معتبر ہے؛ دوبارہ کوشش ادائیگی کی تصدیق نہیں۔")}</p>
    <p>{text("Live Sheet configuration and retention activation remain separately gated. These controls cannot approve a policy or delete an object directly.", "اصل شیٹس اور برقرار رکھنے کی فعالیت کے لیے الگ منظوری درکار ہے۔ یہ کنٹرول پالیسی منظور یا فائل براہ راست حذف نہیں کرتے۔")}</p>
    {storage && <div><label>{text("Order ID", "آرڈر کی شناخت")}<input style={inputStyle} value={order} onChange={e => setOrder(e.target.value)} maxLength={36}/></label><label>{text("Print job ID", "پرنٹ کام کی شناخت")}<input style={inputStyle} value={job} onChange={e => setJob(e.target.value)} maxLength={36}/></label><label>{text("Resource type", "وسیلے کی قسم")}<select style={inputStyle} value={kind} onChange={e => setKind(e.target.value)}><option value="">{text("All", "سب")}</option><option value="print_artifact">Print artifact</option><option value="payment_evidence">Payment evidence</option></select></label></div>}
    <button className="button" disabled={busy} onClick={() => refresh()}>{text("Load metadata", "معلومات لوڈ کریں")}</button>
    {cursor && <button className="button secondary" disabled={busy} onClick={() => refresh(true)}>{text("Next page", "اگلا صفحہ")}</button>}
    {loaded && <><p>{text("Fetched at", "حاصل کرنے کا وقت")}: <time>{asOf}</time></p><p>{storage ? text("At most 100 records; narrow the order/job/type filters. This is not a complete object inventory.", "زیادہ سے زیادہ 100 ریکارڈ؛ فلٹر استعمال کریں۔ یہ مکمل فہرست نہیں۔") : text("Status filter applies to this page only; no global counts are claimed.", "حالت کا فلٹر صرف اس صفحے پر لاگو ہے۔")}</p></>}
    <label>{text("Status on loaded page", "لوڈ شدہ صفحے کی حالت")}<select style={inputStyle} value={status} onChange={e => setStatus(e.target.value)}><option value="">{text("All", "سب")}</option>{(storage ? ["none", "pending", "retry", "leased", "completed", "dead"] : ["pending", "retry", "synced", "failed"]).map(s => <option key={s}>{s}</option>)}</select></label>
    {storage && <label>{text("Hold on loaded page", "لوڈ شدہ صفحے پر پابندی")}<select style={inputStyle} value={hold} onChange={e => setHold(e.target.value)}><option value="">{text("All", "سب")}</option><option value="true">{text("On hold", "پابندی ہے")}</option><option value="false">{text("No hold", "پابندی نہیں")}</option></select></label>}
    <p role="status" aria-live="polite">{notice}</p>
    {loaded && !visible.length && <p>{text("No matching records on this page.", "اس صفحے پر متعلقہ ریکارڈ نہیں۔")}</p>}
    {visible.map(row => <section key={row.id} style={{ overflowWrap: "anywhere", borderBlockStart: "1px solid #bdd6d4", paddingBlock: "1rem" }}>
      <h2>{row.id}</h2>
      {storage ? <><p>{row.resource_type} · {row.format} · {row.size_bytes} bytes</p><p>{text("Parent reference", "بنیادی حوالہ")}: {row.owner_id}</p><p>SHA-256: {row.sha256_hex}</p><p>{text("Retention deadline", "برقرار رکھنے کی آخری تاریخ")}: {row.retention_until ?? text("Not set", "مقرر نہیں")}</p><p>{text("Hold", "پابندی")}: {row.on_hold ? text("Active, including inherited holds", "فعال، بنیادی پابندی سمیت") : text("None reported", "کوئی رپورٹ نہیں")}</p><p>{text("Deleted at", "حذف کرنے کا وقت")}: {row.deleted_at ?? "—"}</p><p>{text("Latest cleanup state", "تازہ صفائی کی حالت")}: {row.cleanup_job?.status ?? "none"} · {text("Attempts", "کوششیں")}: {row.cleanup_job?.attempt_count ?? 0} · {row.cleanup_job?.last_error_code ?? "—"}</p></> : <><p>{text("Order", "آرڈر")}: {row.order_id} · {row.total_pkr} {row.currency_code}</p><p>{text("Mirror status", "آئینے کی حالت")}: {row.status} · {text("Export version", "برآمد کا ورژن")}: {row.last_export_version} · {text("Attempts", "کوششیں")}: {row.attempt_count}</p><p>{text("Payment / fulfillment", "ادائیگی / ترسیل")}: {row.payment_status} / {row.fulfillment_status}</p><p>{text("Updated / last synced", "تازہ / آخری مطابقت")}: {row.updated_at} / {row.last_synced_at ?? "—"}</p><p>{text("Safe error", "محفوظ خرابی")}: {row.last_error_code ?? "—"}</p></>}
      {(!storage && ["failed", "retry"].includes(row.status ?? "") ? ["retry"] : storage && canHold && !row.deleted_at ? ["hold", ...(row.on_hold ? ["release"] : []), ...(row.cleanup_job?.status === "dead" ? ["recover"] : [])] : []).map(action => <button className="button secondary" key={action} disabled={busy} onClick={() => { setPending({ row, action }); setConfirmed(false); setReason(""); }}>{({ retry: text("Review sync retry", "مطابقت کی دوبارہ کوشش"), hold: text("Review hold", "پابندی کا جائزہ"), release: text("Review hold release", "پابندی ہٹانے کا جائزہ"), recover: text("Review cleanup recovery", "صفائی کی بحالی کا جائزہ") } as Record<string, string>)[action]}</button>)}
    </section>)}
    {pending && <section role="region" aria-label={text("Confirm action", "کارروائی کی تصدیق")} style={{ border: "2px solid #087f79", padding: "1rem", overflowWrap: "anywhere" }}><h2>{text("Confirm action", "کارروائی کی تصدیق")}: {pending.action}</h2><p>{pending.row.id}</p><p>{pending.action === "release" ? text("Releases all direct active hold reasons for this resource. Parent holds remain effective. Confirm legal/support authority outside this screen.", "اس وسیلے کی تمام براہ راست پابندیاں ہٹیں گی۔ بنیادی پابندیاں برقرار رہیں گی۔ قانونی اختیار کی تصدیق کریں۔") : pending.action === "recover" ? text("Rearms the existing cleanup job. Recovery may resume an already committed deletion intent; this is not a new policy approval. Review custody before confirming.", "موجودہ صفائی کا کام بحال ہو گا، پہلے سے منظور شدہ حذف کا ارادہ جاری ہو سکتا ہے۔ یہ نئی پالیسی کی منظوری نہیں۔") : text("The server rechecks current eligibility. This screen cannot approve policy, payment or provider configuration.", "سرور موجودہ اہلیت دوبارہ جانچتا ہے۔ یہ صفحہ پالیسی، ادائیگی یا فراہم کنندہ کی منظوری نہیں دیتا۔")}</p>
      {["hold", "recover"].includes(pending.action) && <label>{text("Reason code", "وجہ کا کوڈ")}<input style={inputStyle} value={reason} onChange={e => setReason(e.target.value)} maxLength={80} pattern="[A-Za-z0-9_.-]+"/></label>}
      <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={busy}/>{text("I reviewed the current record and authorize this action.", "میں نے موجودہ ریکارڈ دیکھا اور اس کارروائی کی اجازت دیتا ہوں۔")}</label>
      <button className="button" disabled={busy || !confirmed || ["hold", "recover"].includes(pending.action) && !/^[A-Za-z0-9_.-]{1,80}$/.test(reason)} onClick={execute}>{text("Confirm action", "کارروائی کی تصدیق")}</button><button className="button secondary" disabled={busy} onClick={() => setPending(null)}>{text("Cancel", "منسوخ کریں")}</button>
    </section>}
  </>;
}
