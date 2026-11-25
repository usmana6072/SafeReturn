"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { collection, type IndependentQR } from "../lib/independent-qr";
import { CustomerDialog } from "./customer-dialog";
import { CustomerIcon } from "./customer-icon";
import { QRCard, QRLibrarySkeleton, canEdit, qrType, statusOf, statuses, translate, type FinderHints, type QRAction } from "./qr-library-cards";

type Page = ReturnType<typeof collection> & { labels: Record<string, string> };
type Intent = { intent_id: string; qr_id: string; logical_item_id: string; expires_at: string; method: string };
type Event = { event_id: string; event_type: "activated" | "owner_enabled" | "owner_disabled"; created_at: string };
type Sheet = { kind: QRAction; item: IndependentQR } | { kind: "filters" };
type History = { qr_id: string; items: Event[]; next_revision: number | null };
const endpoint = "/independent-qr/api";

async function request(url: string, options?: RequestInit) {
  const response = await fetch(url, { cache: "no-store", ...options });
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}
async function getPage(after: string | null, signal?: AbortSignal): Promise<Page> {
  const query = new URLSearchParams({ view: "cards" });
  if (after) query.set("after", after);
  const { labels = {}, ...raw } = await request(endpoint + "?" + query, { signal });
  const page = collection(raw);
  const safeLabels: Record<string, string> = {};
  for (const item of page.items) {
    const label = labels?.[item.qr_id];
    if (typeof label === "string") safeLabels[item.qr_id] = label;
  }
  return { ...page, labels: safeLabels };
}
function dateLabel(date: string, ur: boolean) {
  return new Intl.DateTimeFormat(ur ? "ur-PK" : "en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));
}

export function IndependentQRs({ ur, finder = {} }: { ur: boolean; finder?: FinderHints }) {
  const t = translate(ur);
  const [page, setPage] = useState<Page | null>(null);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [busy, setBusy] = useState(true), [failed, setFailed] = useState(false);
  const [notice, setNotice] = useState(""), [issue, setIssue] = useState("");
  const [query, setQuery] = useState(""), [status, setStatus] = useState("all"), [type, setType] = useState("all");
  const [sort, setSort] = useState("original"), [sheet, setSheet] = useState<Sheet | null>(null);
  const [intent, setIntent] = useState<Intent | null>(null), [confirmed, setConfirmed] = useState(false), [expired, setExpired] = useState(false);
  const [history, setHistory] = useState<History | null>(null);
  const keys = useRef(new Map<string, string>()), locked = useRef(false);
  const opener = useRef<HTMLElement | null>(null), search = useRef<HTMLInputElement>(null);
  const after = cursors[cursors.length - 1];
  useEffect(() => {
    const controller = new AbortController();
    async function initial() {
      if (controller.signal.aborted) return;
      try {
        const data = await getPage(null, controller.signal);
        if (!controller.signal.aborted) setPage(data);
      } catch { if (!controller.signal.aborted) setFailed(true); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    }
    queueMicrotask(initial);
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!intent) return;
    const timeout = setTimeout(() => setExpired(true), Math.max(0, Date.parse(intent.expires_at) - Date.now()));
    return () => clearTimeout(timeout);
  }, [intent]);
  function close() {
    setSheet(null); setIntent(null); setHistory(null); setConfirmed(false); setIssue("");
    requestAnimationFrame(() => opener.current?.focus({ preventScroll: true }));
  }
  async function task(work: () => Promise<void>, error: string) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setIssue(""); setNotice("");
    try { await work(); }
    catch (cause) {
      if (cause instanceof Error && ["401", "403"].includes(cause.message)) {
        close(); setPage(null); setCursors([null]); setFailed(true); keys.current.clear();
      } else setIssue(error);
    } finally { locked.current = false; setBusy(false); }
  }
  async function reload(stack = cursors) {
    try {
      const data = await getPage(stack[stack.length - 1]);
      setPage(data); setCursors(stack); setFailed(false);
    } catch (cause) {
      setPage(null); setCursors(stack); setFailed(true); throw cause;
    }
  }
  const load = (stack = cursors) => task(() => reload(stack), t("Your QR codes couldn’t be loaded.", "QR کوڈز لوڈ نہیں ہو سکے۔"));
  async function command(action: string, body: object, qr_id?: string) {
    const signature = JSON.stringify({ action, body, qr_id });
    let key = keys.current.get(signature);
    if (!key) { key = crypto.randomUUID(); keys.current.set(signature, key); }
    return request(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, body, qr_id, key }) });
  }
  function begin(item: IndependentQR) {
    if (!page?.activation_released || !item.can_activate) return;
    void task(async () => {
      const result: Intent = await command("begin", { logical_item_id: item.logical_item_id });
      if (result.qr_id !== item.qr_id || result.logical_item_id !== item.logical_item_id || result.method !== "delivered_purchaser" || !Number.isFinite(Date.parse(result.expires_at))) throw Error();
      setConfirmed(false); setExpired(Date.parse(result.expires_at) <= Date.now()); setIntent(result);
    }, t("Activation couldn’t start. Check your order or try again.", "QR فعال کرنے کی درخواست شروع نہیں ہو سکی۔ آرڈر چیک کریں یا دوبارہ کوشش کریں۔"));
  }
  function activate() {
    if (!intent || !confirmed || Date.parse(intent.expires_at) <= Date.now()) return;
    void task(async () => {
      await command("confirm", { intent_id: intent.intent_id, confirmed: true });
      close(); await reload(); setNotice(t("QR activated. You can now edit its profile.", "QR فعال ہو گیا۔ اب پروفائل میں ترمیم کریں۔"));
    }, t("Activation is uncertain. You can retry this confirmation.", "فعال ہونے کی تصدیق نہیں ہو سکی۔ دوبارہ تصدیق کریں۔"));
  }
  function change(item: IndependentQR) {
    if (item.ownership_status !== "active" || !["active", "owner_disabled"].includes(item.public_status)) return;
    const enable = item.public_status === "owner_disabled";
    void task(async () => {
      await command("availability", { public_status: enable ? "active" : "owner_disabled", expected_revision: item.revision, confirmed: true }, item.qr_id);
      close(); await reload(); setNotice(enable ? t("Public access is on.", "عوامی رسائی بحال ہے۔") : t("Public access is off.", "عوامی رسائی بند ہے۔"));
    }, t("The access change wasn’t confirmed. Refresh your QR codes before trying again.", "تبدیلی کی تصدیق نہیں ہو سکی۔ دوبارہ کوشش سے پہلے QR کوڈز تازہ کریں۔"));
  }
  function readHistory(item: IndependentQR, cursor?: number) {
    void task(async () => {
      const result: History = await command("history", cursor ? { after_revision: cursor } : {}, item.qr_id);
      if (result.qr_id !== item.qr_id || !Array.isArray(result.items) || result.items.some(e => !Number.isFinite(Date.parse(e.created_at)))) throw Error();
      setHistory(previous => ({ ...result, items: cursor ? [...(previous?.items ?? []), ...result.items] : result.items }));
    }, t("Activity couldn’t be loaded.", "سرگرمیاں لوڈ نہیں ہو سکیں۔"));
  }
  function open(kind: QRAction, item: IndependentQR) {
    if (busy) return;
    if (!sheet) opener.current = document.activeElement as HTMLElement;
    setSheet({ kind, item }); setIssue(""); setIntent(null); setConfirmed(false); setHistory(null);
    if (kind === "activation") begin(item);
    if (kind === "history") readHistory(item);
  }
  function reset() { setQuery(""); setStatus("all"); setType("all"); setSort("original"); }
  const items = page?.items ?? [], term = query.trim().toLocaleLowerCase();
  const name = (item: IndependentQR) => page?.labels[item.qr_id] || item.product_name_snapshot || qrType(item, ur);
  const visible = items.filter(item => (type === "all" || type === item.tag_type) &&
    (status === "all" || (status === "pending" ? item.ownership_status === "unclaimed" : statusOf(item) === status)) &&
    [name(item), item.product_name_snapshot, item.qr_id, qrType(item, ur)].some(s => s.toLocaleLowerCase().includes(term)));
  if (sort === "name") visible.sort((a, b) => name(a).localeCompare(name(b), ur ? "ur" : "en"));
  const activeFilters = Number(status !== "all") + Number(type !== "all") + Number(sort !== "original");
  const selected = sheet && "item" in sheet ? sheet.item : null;
  const enable = selected?.public_status === "owner_disabled";
  const titles = {
    menu: selected ? name(selected) : "", filters: t("Filter", "فلٹر"), activation: t("Activate QR", "QR فعال کریں"),
    history: t("Activity History", "سرگرمیوں کی تاریخ"), product: t("Linked Product", "منسلک پروڈکٹ"),
    status: t("QR Status", "QR کی حالت"), access: enable ? t("Enable Public Access?", "عوامی رسائی بحال کریں؟") : t("Turn Off This QR Code?", "اس QR کو بند کریں؟"),
  };
  const message = <>{issue && <p role="alert" className="lib-error">{issue}</p>}</>;
  if (busy && !page && !failed) return <QRLibrarySkeleton ur={ur}/>;
  return <section className="qr-library" dir={ur ? "rtl" : "ltr"} lang={ur ? "ur" : "en"}>
    <header className="lib-intro"><div><h1>{t("My QR Codes", "میرے QR کوڈز")}</h1>
      <p>{t("Manage the QR codes that help protect your belongings.", "اپنے سامان کی حفاظت کرنے والے QR کوڈز کا انتظام کریں۔")}</p></div>
      <button className="lib-round" disabled={busy} aria-label={t("Refresh QR Codes", "QR کوڈز تازہ کریں")} title={t("Refresh QR Codes", "QR کوڈز تازہ کریں")} onClick={() => load()}><CustomerIcon name="refresh"/></button>
    </header>
    {notice && <p className="lib-feedback" role="status">{notice}</p>}
    {!sheet && !failed && message}
    {failed && <div className="lib-empty"><CustomerIcon name="refresh"/><h2>{t("Your QR codes couldn’t be loaded.", "QR کوڈز لوڈ نہیں ہو سکے۔")}</h2>
      <button className="lib-secondary" disabled={busy} onClick={() => load()}>{t("Retry", "دوبارہ کوشش کریں")}</button></div>}
    {page && <>
      {items.length > 0 && <>
        <dl className="lib-overview">{([
          [t("Active", "فعال"), items.filter(i => statusOf(i) === "active").length],
          [t("Pending Activation", "فعال ہونے کا انتظار"), items.filter(i => i.ownership_status === "unclaimed").length],
          [t("Ready to Activate", "فعال کرنے کے لیے تیار"), items.filter(i => i.can_activate).length],
        ] as const).map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{count}</dd></div>)}</dl>
      </>}
      {(after || page.next_cursor) && <p className="lib-note">{t("Counts, search and filters apply to this page.", "تعداد، تلاش اور فلٹر اسی صفحے کے لیے ہیں۔")}</p>}
      {!page.activation_released && <p className="lib-note" role="status">{t("QR activation is currently unavailable.", "QR فعال کرنا فی الحال دستیاب نہیں۔")}</p>}
      {items.length > 0 && <><div className="lib-tools"><div className="lib-search"><CustomerIcon name="search"/>
        <input ref={search} type="search" enterKeyHint="search" autoComplete="off" aria-label={t("Search your QR codes", "اپنے QR کوڈز تلاش کریں")}
          placeholder={t("Search your QR codes", "اپنے QR کوڈز تلاش کریں")} value={query} onChange={e => setQuery(e.target.value)}/>
        {query && <button className="lib-clear" aria-label={t("Clear search", "تلاش صاف کریں")} onClick={() => { setQuery(""); search.current?.focus(); }}><CustomerIcon name="close"/></button>}
        </div><button className="lib-filter" aria-haspopup="dialog" onClick={e => { opener.current = e.currentTarget; setSheet({ kind: "filters" }); }}><CustomerIcon name="filter"/>{t("Filter", "فلٹر")}{activeFilters > 0 && <span>{activeFilters}</span>}</button>
        </div>{(activeFilters > 0 || term) && <div className="lib-results"><span role="status">{visible.length} {t("matching QR codes", "مماثل QR کوڈز")}</span>
          {visible.length > 0 && <button onClick={reset}>{t("Clear Filters", "فلٹر صاف کریں")}</button>}</div>}</>}
      {visible.length ? <div className="lib-grid">{visible.map(item => <QRCard key={item.qr_id} ur={ur} item={item} name={page.labels[item.qr_id]} released={page.activation_released}
        hint={finder[item.qr_id]} busy={busy} act={open}/>)}</div> :
        <div className="lib-empty"><span className="lib-empty-icon"><CustomerIcon name={items.length ? "search" : "tag"}/></span>
          <h2>{items.length ? t("No Matching QR Codes", "کوئی مماثل QR کوڈ نہیں") : after ? t("No More QR Codes", "مزید QR کوڈز نہیں") : t("No QR Codes Yet", "ابھی کوئی QR کوڈ نہیں")}</h2>
          <p>{items.length ? t("Try a different search or filter.", "تلاش یا فلٹر تبدیل کریں۔") : after ? t("Return to the previous page to see your tags.", "اپنے ٹیگ دیکھنے کے لیے پچھلے صفحے پر جائیں۔") : t("Start protecting your belongings with a SafeReturn QR tag.", "اپنے سامان کی حفاظت SafeReturn QR ٹیگ سے شروع کریں۔")}</p>
          {items.length ? <button className="lib-secondary" onClick={reset}>{t("Clear Filters", "فلٹر صاف کریں")}</button>
            : !after && <Link className="lib-primary" href="/portal/shop">{t("Shop QR Tags", "QR ٹیگز خریدیں")}</Link>}</div>}
      {(after || page.next_cursor) && <div className="lib-pager"><button disabled={busy || !after} onClick={() => load(cursors.slice(0, -1))}>{t("Previous", "پچھلا")}</button>
        <span>{t("Page", "صفحہ")} {cursors.length}</span><button disabled={busy || !page.next_cursor} onClick={() => load([...cursors, page.next_cursor])}>{t("Next", "اگلا")}</button></div>}
    </>}
    {sheet && <CustomerDialog title={titles[sheet.kind]} ur={ur} busy={busy} dismissOnBackdrop onClose={close}>
      {sheet.kind === "filters" && <div className="lib-filter-fields">
        <label>{t("Status", "حالت")}<select aria-label={t("Status", "حالت")} value={status} onChange={e => setStatus(e.target.value)}><option value="all">{t("All QR Codes", "تمام QR کوڈز")}</option>
          {Object.entries(statuses).map(([key, text]) => <option key={key} value={key}>{text[ur ? 1 : 0]}</option>)}</select></label>
        <label>{t("Tag type", "ٹیگ کی قسم")}<select aria-label={t("Tag type", "ٹیگ کی قسم")} value={type} onChange={e => setType(e.target.value)}><option value="all">{t("All types", "تمام اقسام")}</option>
          <option value="lost">{t("Lost", "گمشدہ")}</option><option value="ice">{t("Emergency", "ہنگامی")}</option></select></label>
        <label>{t("Sort by", "ترتیب")}<select aria-label={t("Sort by", "ترتیب")} value={sort} onChange={e => setSort(e.target.value)}><option value="original">{t("Original order", "اصل ترتیب")}</option><option value="name">{t("Name A–Z", "نام کے لحاظ سے")}</option></select></label>
        <div className="lib-sheet-actions"><button className="lib-secondary" onClick={reset}>{t("Clear Filters", "فلٹر صاف کریں")}</button>
          <button className="lib-primary" onClick={close}>{t("Done", "مکمل")}</button></div></div>}
      {selected && <>
        {sheet.kind !== "menu" && <p className="lib-sheet-context"><bdi>{name(selected)}</bdi> · <bdi>{selected.qr_id.slice(-8).toUpperCase()}</bdi></p>}
        {sheet.kind === "menu" && <div className="lib-menu">
          {canEdit(selected) && <Link href={`/my-qr/${selected.qr_id}`} prefetch={false} onClick={close}><CustomerIcon name="tag"/>{t("Edit QR Profile", "QR پروفائل میں ترمیم")}</Link>}
          <button onClick={() => open("product", selected)}><CustomerIcon name="box"/>{t("View Linked Product", "منسلک پروڈکٹ دیکھیں")}</button>
          {selected.ownership_status === "active" && <button onClick={() => open("history", selected)}><CustomerIcon name="pending"/>{titles.history}</button>}
          {(selected.ownership_status === "active" || finder[selected.qr_id]) && <Link href={`/inbox?qr_id=${selected.qr_id}`} prefetch={false} onClick={close}><CustomerIcon name="inbox"/>{t("View Finder Messages", "فائنڈر پیغامات دیکھیں")}</Link>}
          {selected.ownership_status === "active" && (selected.public_status === "active" || enable && page?.activation_released) && <button onClick={() => open("access", selected)}><CustomerIcon name="qr"/>{enable ? t("Enable Public Access", "عوامی رسائی بحال کریں") : t("Turn Off Public Access", "عوامی رسائی بند کریں")}</button>}
        </div>}
        {sheet.kind === "product" && <><h3><bdi>{selected.product_name_snapshot}</bdi></h3><p>{qrType(selected, ur)}</p>
          <Link className="lib-secondary" href={`/orders/${selected.order_id}`}>{t("View Purchase", "خریداری دیکھیں")}<CustomerIcon name="arrow"/></Link></>}
        {sheet.kind === "status" && <><span className={"lib-badge is-" + statusOf(selected)}>{statuses[statusOf(selected)][ur ? 1 : 0]}</span>
          <p>{statusOf(selected) === "pending" ? t("Activation becomes available after payment verification when your print file is ready.", "ادائیگی کی تصدیق اور پرنٹ فائل تیار ہونے پر QR فعال کیا جا سکے گا۔")
            : t("This QR’s current status limits the actions available.", "اس QR کی موجودہ حالت میں اقدامات محدود ہیں۔")}</p>
          <Link className="lib-secondary" href={`/orders/${selected.order_id}`}>{t("View Purchase", "خریداری دیکھیں")}</Link></>}
        {sheet.kind === "activation" && <>
          {intent && <><p>{t("Confirm that you purchased this tag to activate it for your account.", "اپنے اکاؤنٹ میں ٹیگ فعال کرنے کے لیے خریداری کی تصدیق کریں۔")}</p>
            <p className="lib-note">{t("Confirmation expires", "تصدیق کی میعاد")} <time dateTime={intent.expires_at}>{dateLabel(intent.expires_at, ur)}</time></p>
            {expired && <p role="alert">{t("This confirmation has expired. Start activation again.", "تصدیق کی میعاد ختم ہو گئی۔ دوبارہ درخواست کریں۔")}</p>}
            <label className="lib-check"><input type="checkbox" disabled={busy || expired} checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>{t("I am the purchaser and want to activate this QR.", "میں خریدار ہوں اور یہ QR فعال کرنا چاہتا ہوں۔")}</label></>}
          {busy && !intent && <p role="status">{t("Checking activation…", "فعال کرنے کی اہلیت چیک ہو رہی ہے…")}</p>}{message}
          {intent && <button className="lib-primary" disabled={busy || !confirmed || expired} onClick={activate}>{t("Confirm Activation", "فعال کرنے کی تصدیق")}</button>}
          {(!intent && !busy || expired) && <button className="lib-secondary" disabled={busy} onClick={() => begin(selected)}>{t("Start Again", "دوبارہ شروع کریں")}</button>}</>}
        {sheet.kind === "access" && <><p>{enable ? t("People who scan this tag can access the information you’ve chosen to publish.", "ٹیگ اسکین کرنے والے آپ کی شائع کردہ معلومات دیکھ سکیں گے۔")
          : t("People who scan this tag may no longer be able to view its public page or contact you. Your profile and history stay saved.", "ٹیگ اسکین کرنے والے اس کا عوامی صفحہ دیکھنے یا آپ سے رابطہ کرنے سے محروم ہو سکتے ہیں۔ آپ کا پروفائل اور تاریخ محفوظ رہیں گے۔")}</p>{message}
          <div className="lib-sheet-actions"><button className="lib-secondary" disabled={busy} onClick={close}>{enable ? t("Cancel", "منسوخ") : t("Keep QR Active", "QR فعال رکھیں")}</button>
            <button className="lib-primary" disabled={busy} onClick={() => change(selected)}>{enable ? t("Enable Public Access", "عوامی رسائی بحال کریں") : t("Turn Off Access", "رسائی بند کریں")}</button></div></>}
        {sheet.kind === "history" && <>
          {busy && <p role="status">{t("Loading activity…", "سرگرمیاں لوڈ ہو رہی ہیں…")}</p>}{message}
          {history && (history.items.length ? <ol className="lib-timeline">{history.items.map(e => <li key={e.event_id}><CustomerIcon name={e.event_type === "activated" ? "check" : "pending"}/>
            <div><strong>{e.event_type === "activated" ? t("QR activated", "QR فعال ہو گیا") : e.event_type === "owner_disabled" ? t("Public access turned off", "عوامی رسائی بند ہوئی") : t("Public access restored", "عوامی رسائی بحال ہوئی")}</strong>
              <time dateTime={e.created_at}>{dateLabel(e.created_at, ur)}</time></div></li>)}</ol> :
            <><h3>{t("No Activity Yet", "ابھی کوئی سرگرمی نہیں")}</h3><p>{t("Updates for this QR code will appear here.", "اس QR کوڈ کی سرگرمیاں یہاں دکھائی دیں گی۔")}</p></>)}
          {(issue || history?.next_revision) && <button className="lib-secondary" disabled={busy} onClick={() => readHistory(selected, history?.next_revision ?? undefined)}>{issue ? t("Retry", "دوبارہ کوشش کریں") : t("Older Activity", "پرانی سرگرمیاں")}</button>}
        </>}
      </>}
    </CustomerDialog>}
  </section>;
}
