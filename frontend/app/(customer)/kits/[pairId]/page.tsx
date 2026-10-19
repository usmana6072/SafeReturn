import { notFound } from "next/navigation";
import { ownerApi, ownerSession } from "../../../../lib/qr-server";
import { Pair, uuid } from "../../../../lib/qr-contract";
import { ApiError } from "../../../../lib/api/transport";
import { PairCard, Unavailable } from "../../../../components/customer";
import { getLanguage } from "../../../../lib/i18n";
export default async function Page({ params, searchParams }: { params: Promise<{pairId: string}>; searchParams: Promise<{activated?: string}> }) {
  const { pairId } = await params;
  if (!uuid(pairId)) notFound();
  const ur = await getLanguage() === "ur", session = await ownerSession();
  let pair: Pair;
  try { pair = await ownerApi(session.token)<Pair>(`/me/tag-pairs/${pairId}`); }
  catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); return <Unavailable ur={ur} />; }
  return <>{(await searchParams).activated === "1" && <p role="status">{ur ? "دونوں QR فعال ہو گئے۔ ہر پروفائل الگ تیار کریں۔" : "Both QR tags are active. Set up each profile separately."}</p>}<PairCard pair={pair} ur={ur} /></>;
}
