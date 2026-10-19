import { redirect } from "next/navigation";
import { verifiedSession } from "../../lib/auth/server";
import { CustomerShell, Unavailable } from "../../components/customer";
import { getLanguage } from "../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = { title: "My QR | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default async function Layout({ children }: { children: React.ReactNode }) {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await verifiedSession(); } catch { return <CustomerShell ur={ur}><Unavailable ur={ur} /></CustomerShell>; }
  if (!session) redirect("/login");
  return <CustomerShell ur={ur}>{children}</CustomerShell>;
}
