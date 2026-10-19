import { notFound, redirect } from "next/navigation";
import { ownerApi, ownerSession } from "../lib/qr-server";
import { Pair, uuid } from "../lib/qr-contract";
import { ApiError } from "../lib/api/transport";
import { Unavailable } from "./customer";
import { getLanguage } from "../lib/i18n";
export async function KitRedirect({ pairId, section }: {pairId: string; section: string}) {
  if (!uuid(pairId) || !["lost", "ice", "contact-options"].includes(section)) notFound();
  const session = await ownerSession();
  let pair: Pair;
  try { pair = await ownerApi(session.token)<Pair>(`/me/tag-pairs/${pairId}`); }
  catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); return <Unavailable ur={await getLanguage() === "ur"} />; }
  const tag = pair.tags.find(t => t.tag_type === (section === "ice" ? "ice" : "lost"));
  if (!tag) notFound();
  redirect(`/my-qr/${tag.qr_id}`);
}
