"use server";
import { headers } from "next/headers";
import { authConfig } from "../../../lib/auth/config";
import { supportOnboardingSession } from "../../../lib/auth/support-onboarding";

export type OnboardingState = { error?: string; factor?: string; qr?: string; verified?: boolean };

export async function onboardingAction(_previous: OnboardingState, form: FormData): Promise<OnboardingState> {
  try {
    if ((await headers()).get("origin") !== authConfig().origin) throw new Error();
    const session = await supportOnboardingSession();
    const factors = await session.client.auth.mfa.listFactors();
    if (factors.error) throw new Error();
    const mode = form.get("mode");
    if (mode === "enroll") {
      if (factors.data.all.some(f => f.factor_type === "totp")) {
        return { error: "An authenticator already exists. Verify it; no factor will be removed." };
      }
      const result = await session.client.auth.mfa.enroll({ factorType: "totp", friendlyName: "SafeReturn development Support" });
      if (result.error || !result.data.totp.qr_code.startsWith("data:image/svg+xml;utf-8,")) throw new Error();
      // Official provider enrollment image goes only to this authenticated browser.
      // Never return/log the raw seed, URI, token, password or recovery codes.
      return { factor: result.data.id, qr: result.data.totp.qr_code };
    }
    const factorId = String(form.get("factor") ?? "");
    const code = String(form.get("code") ?? "");
    if (mode !== "verify" || !/^\d{6}$/.test(code)
      || !factors.data.all.some(f => f.id === factorId && f.factor_type === "totp")) throw new Error();
    const verified = await session.client.auth.mfa.challengeAndVerify({ factorId, code });
    if (verified.error) throw new Error();
    const fresh = await supportOnboardingSession();
    const assurance = await fresh.client.auth.mfa.getAuthenticatorAssuranceLevel();
    if (assurance.error || assurance.data.currentLevel !== "aal2") throw new Error();
    return { verified: true };
  } catch {
    return { error: "Verification unavailable. Sign in again and use a fresh code in your own browser. No staff permission has been granted." };
  }
}
