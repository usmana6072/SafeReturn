import { ApiError } from "../../../../lib/api/transport";
import { changeMessage } from "../../../inbox-actions";
import Link from "next/link";
import { ownerApi, ownerSession } from "../../../../lib/qr-server";
import { getLanguage } from "../../../../lib/i18n";
import { Unavailable } from "../../../../components/customer";

type Message = {
  tag_type: string;
  finder_name: string | null;
  finder_email: string | null;
  finder_phone: string | null;
  message: string;
  status: string;
  submitted_at: string;
  location: { latitude: number; longitude: number; accuracy_m: number | null; maps_url: string } | null;
};

export default async function FinderMessagePage({ params, searchParams }: { params: Promise<{ messageId: string }>; searchParams: Promise<{ result?: string }> }) {
  const ur = await getLanguage() === "ur";
  const session = await ownerSession();
  const { messageId } = await params;
  const result = (await searchParams).result;
  let message: Message;
  try { message = await ownerApi(session.token)<Message>(`/me/finder-messages/${encodeURIComponent(messageId)}`); }
  catch (error) { return <><h1>{ur ? "فائنڈر پیغام" : "Finder message"}</h1>
    {error instanceof ApiError && error.status === 404 ? <p role="status">{ur ? "یہ پیغام دستیاب نہیں ہے۔" : "This message is no longer available."}</p> : <Unavailable ur={ur} />}
    <Link className="text-link" href="/inbox">{ur ? "واپس اِن باکس" : "Back to inbox"}</Link></>; }
  return <>
    <p><Link className="text-link" href="/inbox">{ur ? "واپس اِن باکس" : "Back to inbox"}</Link></p>
    <h1>{ur ? "فائنڈر پیغام" : "Finder message"}</h1>
    {result && <p role="status">{result === "saved" ? (ur ? "محفوظ ہو گیا۔" : "Changes saved.") : (ur ? "تبدیلی محفوظ نہیں ہوئی۔ دوبارہ کوشش کریں۔" : "Changes could not be saved. Confirm deletion if requested and try again.")}</p>}
    <article className="qr-card">
      <p className="eyebrow"><bdi>{message.tag_type}</bdi></p>
      <h2>{message.finder_name || (ur ? "نامعلوم فائنڈر" : "Anonymous finder")}</h2>
      <p>{message.message}</p>
      {message.finder_email && <p>{ur ? "ای میل" : "Email"}: <bdi>{message.finder_email}</bdi></p>}
      {message.finder_phone && <p>{ur ? "فون" : "Phone"}: <bdi>{message.finder_phone}</bdi></p>}
      {message.location && <p><a className="text-link" href={message.location.maps_url} rel="noreferrer">
        {ur ? "نقشے میں مقام دیکھیں" : "View consented location on map"}
      </a></p>}
      <p>{ur ? "حالت" : "Status"}: <bdi>{message.status}</bdi></p>
      <form action={changeMessage.bind(null, messageId)}>
        <label htmlFor="message-status">{ur ? "پیغام کی حالت" : "Message status"}</label>
        <select id="message-status" name="status" defaultValue={message.status === "new" ? "viewed" : message.status}>
          <option value="viewed">{ur ? "دیکھا گیا" : "Viewed"}</option>
          <option value="archived">{ur ? "محفوظ شدہ" : "Archived"}</option>
          <option value="flagged">{ur ? "رپورٹ کیا گیا" : "Flagged"}</option>
        </select><button className="button">{ur ? "محفوظ کریں" : "Save status"}</button>
      </form>
      <form action={changeMessage.bind(null, messageId)}>
        <input type="hidden" name="status" value="deleted" />
        <p>{ur ? "پیغام اِن باکس سے ہٹ جائے گا۔ قانونی اور تحفظ کی پالیسی کے تحت ریکارڈ برقرار رہ سکتا ہے۔" : "Deletion removes this message from your inbox. Records may remain under retention or legal obligations."}</p>
        <label><input type="checkbox" name="confirm" required /> {ur ? "میں یہ پیغام حذف کرنا چاہتا ہوں۔" : "I want to delete this message."}</label>
        <button className="button secondary">{ur ? "پیغام حذف کریں" : "Delete message"}</button>
      </form>
    </article>
  </>;
}
