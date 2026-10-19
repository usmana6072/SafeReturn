import "server-only";
import { redirect } from "next/navigation";
import { verifiedSession } from "./server";
import { validateOrigin } from "../api/transport";
import { parseStaffSecurity, type Capability } from "./staff-contract";
import { mfaReturn } from "./mfa-return";
export class StaffAccessError extends Error {
  constructor(public status: number) { super("Staff access unavailable"); }
}
export async function staffState(token: string) {
  const response = await fetch(`${validateOrigin(process.env.SAFERETURN_API_ORIGIN ?? "")}/api/v1/me/staff-security`, {
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(8000),
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new StaffAccessError(response.status);
  return parseStaffSecurity(await response.json());
}
export async function staffSecurity() {
  const session = await verifiedSession();
  if (!session) throw new StaffAccessError(401);
  return { ...session, security: await staffState(session.token) };
}
export async function staffMfaSession(returnTo: string, capability?: Capability) {
  let session;
  try { session = await staffSecurity(); }
  catch (error) {
    if (error instanceof StaffAccessError && error.status === 401) redirect("/login");
    throw error;
  }
  if (!session.security.mfa_verified) redirect(`/admin/security/mfa?returnTo=${encodeURIComponent(mfaReturn(returnTo))}`);
  if (capability && !session.security.capabilities.includes(capability)) throw new StaffAccessError(403);
  return session;
}
