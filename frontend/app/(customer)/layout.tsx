import { redirect } from "next/navigation";
import { Suspense } from "react";
import { customerSession, unreadMessages } from "../../lib/customer-dashboard";
import { CustomerShell, Unavailable } from "../../components/customer";
import { getLanguage } from "../../lib/i18n";

export const dynamic = "force-dynamic";
export const viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };
async function UnreadIndicator({ token, ur }: { token: string; ur: boolean }) {
  try {
    if (!(await unreadMessages(token)).items.length) return null;
    return <span className="unread-dot"><span className="sr-only">{ur ? "نئے پیغامات ہیں" : "Unread messages available"}</span></span>;
  } catch { return null; }
}
export const metadata = { title: "My QR | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default async function Layout({ children }: { children: React.ReactNode }) {
  const ur = await getLanguage() === "ur";
  let session;
  try { session = await customerSession(); } catch { return <CustomerShell ur={ur}><Unavailable ur={ur} /></CustomerShell>; }
  if (!session) redirect("/login");
  const unread = <Suspense fallback={null}><UnreadIndicator token={session.token} ur={ur}/></Suspense>;
  return <CustomerShell ur={ur} unread={unread}>{children}</CustomerShell>;
}
