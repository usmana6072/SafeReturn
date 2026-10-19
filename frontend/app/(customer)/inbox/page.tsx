import Link from "next/link";
import { ownerApi, ownerSession } from "../../../lib/qr-server";
import { getLanguage } from "../../../lib/i18n";
import { Unavailable } from "../../../components/customer";

type MessageSummary = {
  id: string;
  qr_id: string;
  qr_label: string | null;
  notification_status: string | null;
  tag_type: "lost" | "ice";
  finder_name: string | null;
  status: string;
  submitted_at: string;
};

export default async function InboxPage({ searchParams }: { searchParams: Promise<{ cursor?: string; status?: string; result?: string }> }) {
  const ur = await getLanguage() === "ur";
  const session = await ownerSession();
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.cursor) query.set("cursor", params.cursor);
  if (["new", "viewed", "archived", "flagged"].includes(params.status ?? "")) query.set("status", params.status!);
  let nextCursor: string | null = null;
  let messages: MessageSummary[] = [];
  try {
    const response = await ownerApi(session.token)<{ items: MessageSummary[]; next_cursor: string | null }>(
      `/me/finder-messages?${query}`
    );
    messages = response.items;
    nextCursor = response.next_cursor;
  } catch {
    return <><h1>{ur ? "فائنڈر اِن باکس" : "Finder inbox"}</h1><Unavailable ur={ur} /></>;
  }
  return <>
    <div className="customer-heading">
      <h1>{ur ? "فائنڈر اِن باکس" : "Finder inbox"}</h1>
      <Link className="button secondary" href="/help">{ur ? "مدد" : "Help"}</Link>
    </div>
    <p className="form-help">
      {ur ? "آپ کے QR کوڈز کے ذریعے آنے والے پیغامات۔" : "Messages sent through your QR codes."}
    </p>
    {params.result === "deleted" && <p role="status">{ur ? "پیغام اِن باکس سے ہٹا دیا گیا۔" : "Message removed from your inbox."}</p>}
    <form method="get"><label htmlFor="inbox-filter">{ur ? "حالت کے مطابق" : "Filter by status"}</label>
      <select id="inbox-filter" name="status" defaultValue={params.status ?? ""}>
        <option value="">{ur ? "تمام" : "All"}</option><option value="new">{ur ? "نئے" : "New"}</option>
        <option value="viewed">{ur ? "دیکھے گئے" : "Viewed"}</option><option value="archived">{ur ? "محفوظ شدہ" : "Archived"}</option>
        <option value="flagged">{ur ? "رپورٹ شدہ" : "Flagged"}</option>
      </select><button className="button secondary">{ur ? "دکھائیں" : "Apply filter"}</button>
    </form>
    {messages.length === 0 ? <div className="empty-state">
      <p>{ur ? "ابھی کوئی پیغام نہیں۔" : "No finder messages yet."}</p>
    </div> : <div className="order-list">{messages.map(message => <article className="qr-card" key={message.id}>
      <p className="eyebrow"><bdi>{message.tag_type === "ice" ? "ICE" : "LOST"}</bdi></p>
      <p>{ur ? "QR" : "QR"}: <bdi>{message.qr_label || message.qr_id}</bdi></p>
      <p className="form-help">{ur ? "ای میل اطلاع" : "Email notification"}: <bdi>{message.notification_status ?? (ur ? "دستیاب نہیں" : "unavailable")}</bdi></p>
      <h2>{message.finder_name || (ur ? "نامعلوم فائنڈر" : "Anonymous finder")}</h2>
      <p>{ur ? "حالت" : "Status"}: <bdi>{message.status}</bdi></p>
      <p className="form-help"><bdi>{new Date(message.submitted_at).toLocaleString(ur ? "ur-PK" : "en-PK")}</bdi></p>
      <Link className="button secondary" href={`/inbox/${message.id}`}>
        {ur ? "پیغام دیکھیں" : "View message"}
      </Link>
    </article>)}</div>}
    {nextCursor && <Link className="button secondary" href={`/inbox?${new URLSearchParams({ cursor: nextCursor, ...(params.status ? { status: params.status } : {}) })}`}>{ur ? "مزید پیغامات" : "Older messages"}</Link>}
  </>;
}
