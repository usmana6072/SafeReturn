"use server";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { authConfig } from "../../../../lib/auth/config";
import { staffSecurity } from "../../../../lib/auth/staff";
import { runMfa, type MfaState } from "../../../../lib/auth/mfa-flow";
export type { MfaState } from "../../../../lib/auth/mfa-flow";
export async function mfaAction(previous: MfaState, form: FormData): Promise<MfaState> {
  const result = await runMfa(previous, form, (await headers()).get("origin"), authConfig().origin, staffSecurity);
  if (result.destination) redirect(result.destination);
  return result;
}
