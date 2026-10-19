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
      try { target = staffLanding(await staffState(session.token)); }
      catch (error) {
        if (error instanceof StaffAccessError && error.status === 403) target = staffLanding(null);
        else throw error;
      }
    }
  } catch (error) {
    if (error instanceof StaffAccessError && error.status === 401) redirect("/login");
    return <main className="container section"><h1>Sign-in could not continue</h1><p>Your access could not be checked. Please try again.</p><Link href="/auth/continue">Try again</Link></main>;
  }
  redirect(target);
}
