import { redirect } from "next/navigation";
import { verifiedSession } from "../../../lib/auth/server";
import { getLanguage } from "../../../lib/i18n";
import { ShippingAddresses } from "../../../components/shipping-addresses";
import { Unavailable } from "../../../components/customer";
export const dynamic = "force-dynamic";
export const metadata = { title: "Shipping addresses | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default async function Page() {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await verifiedSession(); } catch { return <main className="container section"><Unavailable ur={ur}/></main>; }
  if (!session) redirect("/login");
  return <main className="container section"><ShippingAddresses ur={ur}/></main>;
}
