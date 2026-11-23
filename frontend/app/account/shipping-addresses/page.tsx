import { redirect } from "next/navigation";
import { verifiedSession } from "../../../lib/auth/server";
import { getLanguage } from "../../../lib/i18n";
import { ShippingAddresses } from "../../../components/shipping-addresses";
import { Unavailable, CustomerShell } from "../../../components/customer";
export const dynamic = "force-dynamic";
export const metadata = { title: "Delivery Addresses | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default async function Page() {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await verifiedSession(); } catch { return <CustomerShell ur={ur}><Unavailable ur={ur}/></CustomerShell>; }
  if (!session) redirect("/login");
  return <CustomerShell ur={ur}><ShippingAddresses ur={ur}/></CustomerShell>;
}
