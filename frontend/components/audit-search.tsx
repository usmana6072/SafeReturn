"use client";
import { useState } from "react";
type Event = { id: string; occurred_at: string; actor_kind: string; actor_user_id: string | null; action: string; target_type: string; target_id: string | null };
const targets = ["user_profile", "qr", "tag_pair", "order", "shipment", "payment_attempt", "payment_evidence", "print_artifact", "print_job", "support_case", "privacy_export", "finance_sheet_sync", "audit_search"];
export function AuditSearch({ ur }: { ur: boolean }) {
  const [filters, setFilters] = useState({ actor_id: "", target_id: "", target_type: "", action: "", start: "", end: "" });
  const [active, setActive] = useState(""), [cursor, setCursor] = useState<string | null>(null), [rows, setRows] = useState<Event[]>([]);
  const [busy, setBusy] = useState(false), [notice, setNotice] = useState(""), [loaded, setLoaded] = useState(false);
  const t = (en: string, translated: string) => ur ? translated : en;
  async function search(next = false) {
    setBusy(true); setNotice("");
    try {
      let query = active;
      if (!next) {
        const end = filters.end ? new Date(filters.end).toISOString() : new Date().toISOString();
        const start = filters.start ? new Date(filters.start).toISOString() : new Date(Date.parse(end) - 7 * 86400000).toISOString();
        const params = new URLSearchParams({ limit: "20", start, end });
        for (const k of ["actor_id", "target_id", "target_type", "action"] as const) if (filters[k]) params.set(k, filters[k]);
        query = params.toString(); setActive(query);
      }
      const response = await fetch("/admin/audit/api?" + query + (next && cursor ? "&cursor=" + encodeURIComponent(cursor) : ""), { cache: "no-store" });
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json(); setRows(data.items); setCursor(data.next_cursor); setLoaded(true);
    } catch (e) {
      setRows([]); setCursor(null); setLoaded(false);
      setNotice(e instanceof Error && e.message === "403" ? t("Recent sign-in and explicit security-admin access are required.", "تازہ لاگ اِن اور مجاز حفاظتی کردار درکار ہے۔") : t("Search could not be completed. Check the filters and retry.", "تلاش مکمل نہیں ہوئی۔ فلٹر دیکھ کر دوبارہ کوشش کریں۔"));
    } finally { setBusy(false); }
  }
  return <>
    <h1>{t("Restricted audit search", "محدود آڈٹ تلاش")}</h1>
    <p>{t("Security metadata only. Reasons, details, payloads, private URLs and profile content are excluded. Unreviewed event labels are restricted. Contextual access for other roles and superadmin delegation are not enabled.", "صرف حفاظتی معلومات۔ وجوہات، تفصیل، نجی روابط اور ذاتی مواد شامل نہیں۔ دیگر کرداروں کی رسائی فعال نہیں۔")}</p>
    <p>{t("Requires a sign-in within five minutes. Search up to 31 days, newest first; default seven days. Every search is audited. Event references do not grant access to the linked resource.", "پانچ منٹ کے اندر لاگ اِن درکار ہے۔ زیادہ سے زیادہ 31 دن، تازہ پہلے؛ عام تلاش سات دن۔ ہر تلاش ریکارڈ ہوتی ہے۔ حوالہ کسی دوسرے وسیلے کی رسائی نہیں دیتا۔")}</p>
    <form onSubmit={e => { e.preventDefault(); search(); }}>
      {([['actor_id', t('Actor UUID', 'فاعل کی شناخت')], ['target_id', t('Target UUID', 'ہدف کی شناخت')], ['action', t('Exact approved action', 'منظور شدہ کارروائی')], ['start', t('Start time', 'ابتدائی وقت')], ['end', t('End time', 'اختتامی وقت')]] as const).map(([key, label]) => <label key={key}>{label}<input style={{ display: "block", width: "100%", maxWidth: "40rem", border: "1px solid #bdd6d4", padding: ".7rem", marginBlock: ".3rem 1rem", borderRadius: ".4rem" }} type={key === "start" || key === "end" ? "datetime-local" : "text"} maxLength={100} value={filters[key]} onChange={e => { setFilters({ ...filters, [key]: e.target.value }); setCursor(null); }}/></label>)}
      <label>{t("Target type", "ہدف کی قسم")}<select style={{ display: "block", padding: ".7rem", marginBlockEnd: "1rem" }} value={filters.target_type} onChange={e => { setFilters({ ...filters, target_type: e.target.value }); setCursor(null); }}><option value="">{t("All approved types", "تمام منظور شدہ اقسام")}</option>{targets.map(x => <option key={x}>{x}</option>)}</select></label>
      <button className="button" disabled={busy}>{t("Search events", "واقعات تلاش کریں")}</button>
    </form>
    <p role="status" aria-live="polite">{notice}</p>
    {loaded && !rows.length && <p>{t("No matching events.", "کوئی متعلقہ واقعہ نہیں۔")}</p>}
    {rows.map(row => <section key={row.id} style={{ paddingBlock: "1rem", borderBlockStart: "1px solid #bdd6d4", overflowWrap: "anywhere" }}><h2>{row.action}</h2><p><time dir="ltr">{row.occurred_at}</time></p><p>{t("Event", "واقعہ")}: <bdi>{row.id}</bdi></p><p>{t("Actor", "فاعل")}: {row.actor_kind} · <bdi>{row.actor_user_id ?? "—"}</bdi></p><p>{t("Target", "ہدف")}: {row.target_type} · <bdi>{row.target_id ?? "—"}</bdi></p></section>)}
    {cursor && <button className="button secondary" disabled={busy} onClick={() => search(true)}>{t("Next page", "اگلا صفحہ")}</button>}
  </>;
}
