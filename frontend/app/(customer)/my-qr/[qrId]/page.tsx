import Link from "next/link";
import { notFound } from "next/navigation";
import { ownerApi, ownerSession } from "../../../../lib/qr-server";
import { Tag, Profile, Contacts, Preferences, uuid } from "../../../../lib/qr-contract";
import { ApiError } from "../../../../lib/api/transport";
import { getLanguage } from "../../../../lib/i18n";
import { Unavailable } from "../../../../components/customer";
import { ProfileEditor, ContactEditor, PreferenceEditor, PrivacyDisable } from "../../../../components/qr-forms";
export default async function Page({ params, searchParams }: { params: Promise<{qrId: string}>; searchParams: Promise<{saved?: string}> }) {
  const { qrId } = await params;
  if (!uuid(qrId)) notFound();
  const ur = await getLanguage() === "ur", session = await ownerSession(), api = ownerApi(session.token);
  let tag: Tag, profile: Profile | undefined, contacts: Contacts | undefined, prefs: Preferences | undefined;
  try {
    tag = await api<Tag>(`/me/qr/${qrId}`);
  } catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); return <Unavailable ur={ur} />; }
  // These owner-authorized sections are independent; load them concurrently and
  // retain the privacy-disable controls when an encryption dependency is down.
  const [profileResult, optionsResult] = await Promise.allSettled([
    api<Profile>(`/me/qr/${qrId}/${tag.tag_type === "lost" ? "lost-profile" : "ice-profile"}`),
    tag.tag_type === "ice" ? api<Contacts>(`/me/qr/${qrId}/ice-contacts`) : api<Preferences>(`/me/qr/${qrId}/contact-preferences`),
  ]);
  if (profileResult.status === "fulfilled") profile = profileResult.value;
  if (optionsResult.status === "fulfilled") {
    if (tag.tag_type === "ice") contacts = optionsResult.value as Contacts;
    else prefs = optionsResult.value as Preferences;
  }
  return <><Link className="text-link" href={tag.pair_id?`/kits/${tag.pair_id}`:"/independent-qr"}>{tag.pair_id?(ur ? "کٹ پر واپس" : "Back to kit"):(ur?"میرے الگ QR":"My independent QRs")}</Link>
    <h1>{tag.tag_type === "lost" ? (ur ? "Lost پروفائل میں ترمیم" : "Edit Lost profile") : (ur ? "ICE پروفائل میں ترمیم" : "Edit ICE profile")}</h1>
    <p className="form-help">QR: <bdi>{qrId}</bdi> · {ur ? "تمام پرنٹ کاپیاں یہی پروفائل استعمال کرتی ہیں۔" : "All printed copies share this profile."}</p>
    {(await searchParams).saved === "1" && <p role="status">{ur ? "تبدیلیاں محفوظ ہو گئیں۔" : "Changes saved."}</p>}
    {profile ? <ProfileEditor key={`profile-${profile.version}`} qrId={qrId} kind={tag.tag_type} profile={profile} ur={ur} /> : <><Unavailable ur={ur} />
      {tag.tag_type === "ice" && <PrivacyDisable qrId={qrId} scope="ice" version={tag.profile_version} ur={ur} />}</>}
    {!!tag.physical_products?.length && <section><h2>{ur ? "منسلک مصنوعات کی کاپیاں" : "Linked product copies"}</h2>{tag.physical_products.map((p, index) => <p key={index}>{p.product_name_snapshot} · {p.variant_name_snapshot} · {p.copies}</p>)}</section>}
    {tag.tag_type === "ice" ? <section><h2>{ur ? "ہنگامی رابطے" : "Emergency contacts"}</h2>
      {contacts ? <>{contacts.contacts.map(c => <ContactEditor key={`${c.contact_id}-${contacts!.version}`} qrId={qrId} version={contacts!.version} contact={c} ur={ur} />)}
        {contacts.contacts.length < 3 && <ContactEditor key={`new-${contacts.version}`} qrId={qrId} version={contacts.version} ur={ur} />}</> : <Unavailable ur={ur} />}</section>
      : prefs ? <PreferenceEditor key={`preferences-${prefs.version}`} qrId={qrId} preferences={prefs} ur={ur} /> : <><Unavailable ur={ur} /><PrivacyDisable qrId={qrId} scope="preferences" version={tag.preference_version} ur={ur} /></>}
  </>;
}
