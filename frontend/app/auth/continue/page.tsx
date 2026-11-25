import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { verifiedSession } from "../../../lib/auth/server";
import { staffState, StaffAccessError } from "../../../lib/auth/staff";
import { staffLanding } from "../../../lib/auth/staff-contract";
import { readTicket, type ScanTicket, type ActivationTicket } from "../../../lib/scan-ticket";
export const dynamic = "force-dynamic";
export default async function Continue() {
  let target: string;
  try {
    const session = await verifiedSession();
    if (!session) throw new StaffAccessError(401);
    const jar = await cookies();
    const activation = readTicket<ScanTicket>(jar.get("sr-scan")?.value, "scan") || readTicket<ActivationTicket>(jar.get("sr-activation")?.value, "activation");
    // Genuine activation intent keeps priority over the staff landing.
    if (activation) target = "/activate";
    else {
      try {
        const state = await staffState(session.token);
        if (state) {
          target = staffLanding(state);
        } else {
          const returnToCookie = jar.get("sr-return-to")?.value;
          const safeReturn = returnToCookie && returnToCookie.startsWith("/") && !returnToCookie.startsWith("//") ? returnToCookie : null;
          if (safeReturn) {
            jar.delete("sr-return-to");
            target = safeReturn;
          } else {
            target = staffLanding(null);
          }
        }
      } catch (error) {
        if (error instanceof StaffAccessError && error.status === 403) {
          const returnToCookie = jar.get("sr-return-to")?.value;
          const safeReturn = returnToCookie && returnToCookie.startsWith("/") && !returnToCookie.startsWith("//") ? returnToCookie : null;
          if (safeReturn) {
            jar.delete("sr-return-to");
            target = safeReturn;
          } else {
            target = staffLanding(null);
          }
        }
        else throw error;
      }
    }
  } catch (error) {
    if (error instanceof StaffAccessError && error.status === 401) redirect("/login");
    return <main className="container section"><h1>Sign-in could not continue</h1><p>Your access could not be checked. Please try again.</p><Link href="/auth/continue">Try again</Link></main>;
  }
  redirect(target);
}
