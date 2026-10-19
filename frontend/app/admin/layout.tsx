import type { ReactNode } from "react";
export const dynamic = "force-dynamic";
export const metadata = { title: "Staff | SafeReturn", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
// Each page authenticates before rendering its module. MFA remains reachable at AAL1.
export default function Layout({ children }: { children: ReactNode }) { return children; }
