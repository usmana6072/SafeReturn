import type { staffSecurity } from "./staff";
import { mfaFailure } from "./mfa-error";
import { mfaReturn } from "./mfa-return";
export type MfaState = { error?: string; factor?: string; secret?: string };
export async function runMfa(previous: MfaState, form: FormData, origin: string | null, expectedOrigin: string, authenticate: typeof staffSecurity): Promise<MfaState & { destination?: string }> {
  let destination: string | undefined;
  try {
    if (origin !== expectedOrigin) throw new Error();
    const session = await authenticate();
    const factors = await session.client.auth.mfa.listFactors();
    if (factors.error) throw new Error();
    const mode = form.get("mode");
    if (mode === "enroll") {
      // Explicit user interaction only. Never remove existing factors automatically.
      if (factors.data.all.some(f => f.factor_type === "totp")) return { error: "An authenticator already exists. Verify it, or use recovery guidance." };
      const result = await session.client.auth.mfa.enroll({ factorType: "totp", friendlyName: "SafeReturn staff" });
      if (result.error) throw new Error();
      return { factor: result.data.id, secret: result.data.totp.secret };
    }
    if (mode !== "verify") throw new Error();
    const factorId = String(form.get("factor") ?? "");
    if (!factors.data.all.some(f => f.id === factorId && f.factor_type === "totp")) throw new Error();
    const code = String(form.get("code") ?? "");
    if (!/^\d{6}$/.test(code)) return { factor: previous.factor, secret: previous.secret, error: "Enter a six-digit authenticator code." };
    const result = await session.client.auth.mfa.challengeAndVerify({ factorId, code });
    if (result.error) {
      const failure = mfaFailure(result.error);
      console.info(`MFA verification rejected: category=${failure.reason}`);
      return { factor: previous.factor, secret: previous.secret, error: failure.message };
    }
    // Provider success alone is insufficient: recheck signed token + live AAL and roles.
    const fresh = await authenticate();
    if (!fresh.security.mfa_verified) throw new Error();
    destination = mfaReturn(form.get("returnTo"));
  } catch { return { error: "Verification unavailable or access denied. Sign in again or contact your security owner." }; }
  if (destination) return { destination };
  return { error: "Access denied." };
}
